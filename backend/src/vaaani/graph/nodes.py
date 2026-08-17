import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from time import perf_counter

from vaaani.generation.answer_generator import AnswerGenerator
from vaaani.graph.state import GraphState
from vaaani.guardrails.confidence_threshold import check_confidence
from vaaani.guardrails.groundedness_check import GroundednessChecker
from vaaani.guardrails.topic_classifier import TopicClassifier
from vaaani.retrieval.dense import DenseRetriever
from vaaani.retrieval.fusion import reciprocal_rank_fusion
from vaaani.retrieval.reranker import CrossEncoderReranker
from vaaani.retrieval.sparse_bm25 import SparseBM25Retriever
from vaaani.stt.sarvam_stt import SarvamSTT
from vaaani.tts.sarvam_tts import SarvamTTS
from vaaani.vectorstore.qdrant_client import QdrantVectorStore


class PipelineNodes:
    def __init__(
        self,
        stt: SarvamSTT,
        tts: SarvamTTS,
        topic: TopicClassifier,
        dense: DenseRetriever,
        sparse: SparseBM25Retriever,
        reranker: CrossEncoderReranker,
        generator: AnswerGenerator,
        groundedness: GroundednessChecker,
        store: QdrantVectorStore,
        confidence_threshold: float,
    ) -> None:
        self.stt = stt
        self.tts = tts
        self.topic = topic
        self.dense = dense
        self.sparse = sparse
        self.reranker = reranker
        self.generator = generator
        self.groundedness = groundedness
        self.store = store
        self.confidence_threshold = confidence_threshold

    async def _run(
        self,
        state: GraphState,
        stage: str,
        operation: Callable[[GraphState], Awaitable[GraphState]],
        fallback: Callable[[GraphState, Exception], GraphState],
    ) -> GraphState:
        started_at = datetime.now(UTC)
        started = perf_counter()
        status = "ok"
        working: GraphState = {
            **state,
            "conversation": [dict(turn) for turn in state["conversation"]],
            "candidates": list(state["candidates"]),
            "reranked": list(state["reranked"]),
            "guardrails": [dict(item) for item in state["guardrails"]],
            "timings": [dict(item) for item in state["timings"]],
            "degraded_services": list(state["degraded_services"]),
            "errors": list(state["errors"]),
        }
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                working = await operation(working)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(0.05 * (2**attempt))
        if last_error is not None:
            status = "error"
            working = fallback(working, last_error)
            working.setdefault("errors", []).append(f"{stage}:{type(last_error).__name__}")
        ended_at = datetime.now(UTC)
        working.setdefault("timings", []).append(
            {
                "stage": stage,
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_ms": round((perf_counter() - started) * 1000, 3),
                "status": status,
            }
        )
        return working

    async def stt_node(self, state: GraphState) -> GraphState:
        async def operation(current: GraphState) -> GraphState:
            if current["query"].strip():
                current["transcript"] = current["query"].strip()
            elif current["audio"]:
                current["transcript"] = await self.stt.transcribe(
                    current["audio"], current["audio_mime_type"], current["language"]
                )
            else:
                raise ValueError("query_or_audio_required")
            return current

        def fallback(current: GraphState, exc: Exception) -> GraphState:
            current["refused"] = True
            current["refusal_reason"] = str(exc)
            current["transcript"] = current["query"].strip()
            current["degraded_services"].append("sarvam_stt")
            return current

        return await self._run(state, "stt", operation, fallback)

    async def query_classify_node(self, state: GraphState) -> GraphState:
        async def operation(current: GraphState) -> GraphState:
            if current["refused"]:
                return current
            decision = self.topic.classify(current["transcript"])
            current["guardrails"].append(
                {
                    "guardrail": "topic_classifier",
                    "passed": decision.passed,
                    "reason": decision.reason,
                    "details": {"category": decision.category},
                }
            )
            if not decision.passed:
                current["refused"] = True
                current["refusal_reason"] = decision.reason
            return current

        return await self._run(state, "query_classify", operation, lambda current, _exc: current)

    async def query_rewrite_node(self, state: GraphState) -> GraphState:
        async def operation(current: GraphState) -> GraphState:
            query = current["transcript"].strip()
            pronouns = {"it", "that", "this", "they", "यह", "वह", "इसके", "उसके"}
            words = set(query.casefold().split())
            previous = [turn["content"] for turn in current["conversation"][-4:]]
            if previous and words & pronouns:
                context = " | ".join(previous)
                current["rewritten_query"] = f"{query}\nConversation context: {context}"
            else:
                current["rewritten_query"] = query
            return current

        return await self._run(state, "query_rewrite", operation, lambda current, _exc: current)

    async def retrieve_node(self, state: GraphState) -> GraphState:
        async def operation(current: GraphState) -> GraphState:
            language = current["language"].split("-")[0]
            dense_hits, corpus = await asyncio.gather(
                self.dense.search(current["rewritten_query"], language=language, limit=50),
                self.store.corpus(language=language, limit=2500),
            )
            sparse_hits = self.sparse.rank(current["rewritten_query"], corpus, limit=50)
            current["candidates"] = reciprocal_rank_fusion([dense_hits, sparse_hits], limit=20)
            return current

        def fallback(current: GraphState, _exc: Exception) -> GraphState:
            current["candidates"] = []
            current["degraded_services"].append("qdrant_retrieval")
            return current

        return await self._run(state, "retrieve", operation, fallback)

    async def rerank_node(self, state: GraphState) -> GraphState:
        async def operation(current: GraphState) -> GraphState:
            current["reranked"] = self.reranker.rerank(
                current["rewritten_query"], current["candidates"], limit=5
            )
            if self.reranker.degraded:
                current["degraded_services"].append("cross_encoder_reranker")
            return current

        return await self._run(state, "rerank", operation, lambda current, _exc: current)

    async def confidence_gate_node(self, state: GraphState) -> GraphState:
        async def operation(current: GraphState) -> GraphState:
            decision = check_confidence(current["reranked"], self.confidence_threshold)
            current["confidence"] = decision.score
            current["guardrails"].append(
                {
                    "guardrail": "confidence_threshold",
                    "passed": decision.passed,
                    "reason": decision.reason,
                    "details": {
                        "confidence_score": decision.score,
                        "threshold": decision.threshold,
                    },
                }
            )
            if not decision.passed:
                current["refused"] = True
                current["refusal_reason"] = decision.reason
            return current

        return await self._run(state, "confidence_gate", operation, lambda current, _exc: current)

    async def generate_node(self, state: GraphState) -> GraphState:
        async def operation(current: GraphState) -> GraphState:
            current["answer"] = await self.generator.generate(
                current["rewritten_query"], current["reranked"], current["language"]
            )
            if self.generator.degraded:
                current["degraded_services"].append("llm_generation")
            return current

        def fallback(current: GraphState, _exc: Exception) -> GraphState:
            current["refused"] = True
            current["refusal_reason"] = "generation_provider_unavailable"
            return current

        return await self._run(state, "generate", operation, fallback)

    async def groundedness_check_node(self, state: GraphState) -> GraphState:
        async def operation(current: GraphState) -> GraphState:
            decision = self.groundedness.check(current["answer"], current["reranked"])
            current["guardrails"].append(
                {
                    "guardrail": "groundedness_entailment",
                    "passed": decision.passed,
                    "reason": decision.reason,
                    "details": {
                        "entailment_score": decision.score,
                        "threshold": decision.threshold,
                    },
                }
            )
            if self.groundedness.degraded:
                current["degraded_services"].append("nli_groundedness")
            if not decision.passed:
                current["refused"] = True
                current["refusal_reason"] = decision.reason
            return current

        def fallback(current: GraphState, exc: Exception) -> GraphState:
            current["refused"] = True
            current["refusal_reason"] = "groundedness_check_unavailable"
            current["guardrails"].append(
                {
                    "guardrail": "groundedness_entailment",
                    "passed": False,
                    "reason": "groundedness_check_unavailable",
                    "details": {"error_type": type(exc).__name__},
                }
            )
            current["degraded_services"].append("nli_groundedness")
            return current

        return await self._run(state, "groundedness_check", operation, fallback)

    async def refuse_node(self, state: GraphState) -> GraphState:
        async def operation(current: GraphState) -> GraphState:
            reason = current["refusal_reason"] or "pipeline_error"
            current["refused"] = True
            current["answer"] = (
                f"I did not generate an answer because `{reason}`. "
                "Try a more specific informational question or index relevant passages first."
            )
            current["audio_base64"] = None
            return current

        return await self._run(state, "refuse", operation, lambda current, _exc: current)

    async def tts_node(self, state: GraphState) -> GraphState:
        async def operation(current: GraphState) -> GraphState:
            audio, mime = await self.tts.synthesize(current["answer"], current["language"])
            current["audio_base64"] = audio
            current["audio_output_mime_type"] = mime
            return current

        def fallback(current: GraphState, _exc: Exception) -> GraphState:
            current["audio_base64"] = None
            current["degraded_services"].append("sarvam_tts")
            return current

        return await self._run(state, "tts", operation, fallback)

    async def response_node(self, state: GraphState) -> GraphState:
        async def operation(current: GraphState) -> GraphState:
            current["degraded_services"] = list(dict.fromkeys(current["degraded_services"]))
            return current

        return await self._run(state, "response", operation, lambda current, _exc: current)
