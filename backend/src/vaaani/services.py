import asyncio
import base64
import binascii
import uuid
from dataclasses import dataclass
from typing import Any

from vaaani.api.schemas import Citation, QueryRequest, QueryResponse, StageTiming
from vaaani.config import Settings
from vaaani.embeddings.multilingual_encoder import MultilingualEncoder
from vaaani.generation.answer_generator import AnswerGenerator
from vaaani.graph.nodes import PipelineNodes
from vaaani.graph.pipeline import build_pipeline
from vaaani.graph.state import GraphState
from vaaani.guardrails.groundedness_check import GroundednessChecker
from vaaani.guardrails.topic_classifier import TopicClassifier
from vaaani.retrieval.dense import DenseRetriever
from vaaani.retrieval.reranker import CrossEncoderReranker
from vaaani.retrieval.sparse_bm25 import SparseBM25Retriever
from vaaani.stt.elevenlabs_stt import ElevenLabsSTT
from vaaani.stt.sarvam_stt import SarvamSTT
from vaaani.tts.elevenlabs_tts import ElevenLabsTTS
from vaaani.tts.sarvam_tts import SarvamTTS
from vaaani.vectorstore.qdrant_client import QdrantVectorStore


@dataclass(slots=True)
class EvidencePreview:
    """Retrieval result plus the settled pipeline timings, streamed before
    generation starts. The pipeline budget is spent by this point, so the
    score is final here — nothing after this belongs to it."""

    transcript: str
    confidence: float
    refused: bool
    citations: list[Citation]
    timings: list[StageTiming]
    pipeline_duration_ms: float


@dataclass(slots=True)
class AnswerPreview:
    """Verified answer text, streamed before voice synthesis starts. Only used
    when the provider can't stream — otherwise TokenChunk carries the answer."""

    answer: str


@dataclass(slots=True)
class TokenChunk:
    """A piece of the answer, emitted as the LLM produces it."""

    text: str


# Speech recognition is a provider round trip, so it sits outside the pipeline
# budget alongside generation and voice synthesis.
PROVIDER_STAGES = frozenset({"stt", "generate", "tts"})


def _build_citations(state: GraphState) -> list[Citation]:
    return [
        Citation(
            rank=rank,
            passage_id=hit.passage_id,
            text=hit.text,
            score=hit.score,
            language=hit.language,
            source_lang=hit.source_lang,
            target_lang=hit.target_lang,
            chunk_strategy=hit.strategy,
        )
        for rank, hit in enumerate(state["reranked"], start=1)
    ]


@dataclass(slots=True)
class ServiceContainer:
    settings: Settings
    encoder: MultilingualEncoder
    store: QdrantVectorStore
    nodes: PipelineNodes
    graph: Any

    @classmethod
    def build(cls, settings: Settings) -> "ServiceContainer":
        encoder = MultilingualEncoder(settings.embedding_model, settings.enable_ml_models)
        store = QdrantVectorStore(
            settings.qdrant_url, settings.qdrant_collection, settings.qdrant_api_key
        )
        if settings.voice_provider == "elevenlabs":
            stt: SarvamSTT | ElevenLabsSTT = ElevenLabsSTT(
                settings.elevenlabs_api_keys,
                settings.elevenlabs_base_url,
                settings.elevenlabs_stt_model,
            )
            tts: SarvamTTS | ElevenLabsTTS = ElevenLabsTTS(
                settings.elevenlabs_api_keys,
                settings.elevenlabs_base_url,
                settings.elevenlabs_tts_model,
                settings.elevenlabs_voice_id,
            )
        else:
            stt = SarvamSTT(
                settings.sarvam_api_key, settings.sarvam_base_url, settings.sarvam_stt_model
            )
            tts = SarvamTTS(
                settings.sarvam_api_key,
                settings.sarvam_base_url,
                settings.sarvam_tts_model,
                settings.sarvam_tts_speaker,
            )
        nodes = PipelineNodes(
            stt=stt,
            tts=tts,
            topic=TopicClassifier(),
            dense=DenseRetriever(store, encoder),
            sparse=SparseBM25Retriever(),
            reranker=CrossEncoderReranker(settings.reranker_model, settings.enable_ml_models),
            generator=AnswerGenerator(
                settings.llm_api_key, settings.llm_base_url, settings.llm_model
            ),
            groundedness=GroundednessChecker(settings.nli_model, settings.enable_ml_models),
            store=store,
            confidence_threshold=settings.confidence_threshold,
        )
        return cls(
            settings=settings,
            encoder=encoder,
            store=store,
            nodes=nodes,
            graph=build_pipeline(nodes),
        )

    async def initialize(self) -> None:
        # Only touch encoder.dimension (which forces the embedding model to load)
        # when the collection doesn't exist yet. On a redeploy against an
        # already-built index, this keeps startup fast and avoids re-downloading
        # the model before the platform's health check window closes.
        if not await self.store.exists():
            await self.store.ensure_collection(self.encoder.dimension)

    def _build_initial_state(self, request: QueryRequest) -> GraphState:
        audio: bytes | None = None
        if request.audio_base64:
            try:
                audio = base64.b64decode(request.audio_base64, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise ValueError("audio_base64 is not valid base64") from exc
            if len(audio) > 20 * 1024 * 1024:
                raise ValueError("audio exceeds the 20MB request limit")

        return {
            "request_id": str(uuid.uuid4()),
            "query": request.query or "",
            "language": request.language,
            "audio": audio,
            "audio_mime_type": request.audio_mime_type,
            "conversation": [turn.model_dump() for turn in request.conversation],
            "transcript": "",
            "rewritten_query": "",
            "candidates": [],
            "reranked": [],
            "answer": "",
            "audio_base64": None,
            "audio_output_mime_type": None,
            "confidence": 0,
            "refused": False,
            "refusal_reason": None,
            "guardrails": [],
            "timings": [],
            "degraded_services": [],
            "errors": [],
            "token_sink": None,
        }

    async def query(self, request: QueryRequest) -> QueryResponse:
        initial = self._build_initial_state(request)
        result: GraphState = await self.graph.ainvoke(initial)
        return self._build_response(result)

    async def query_stages(self, request: QueryRequest):  # type: ignore[no-untyped-def]
        """Yield everything the client can act on the moment it exists:
        stage names as they complete, EvidencePreview once retrieval settles
        (while the LLM works), TokenChunks as the LLM writes them, and the
        final QueryResponse last.

        The graph runs as a task feeding a queue rather than being driven by
        this generator, so tokens produced *inside* the generate node can be
        forwarded without waiting for that node to return.
        """
        queue: asyncio.Queue[Any] = asyncio.Queue()
        done = object()

        # Set when the first token is queued, not when the consumer reads it —
        # otherwise the groundedness check could race ahead and also emit an
        # AnswerPreview, duplicating the answer.
        streamed = {"tokens": False}

        async def sink(piece: str) -> None:
            streamed["tokens"] = True
            await queue.put(TokenChunk(text=piece))

        initial = self._build_initial_state(request)
        initial["token_sink"] = sink

        async def run() -> None:
            last_state: GraphState = initial
            evidence_sent = False
            answer_sent = False
            try:
                async for update in self.graph.astream(initial, stream_mode="updates"):
                    for partial in update.values():
                        last_state = {**last_state, **partial}
                        if not partial.get("timings"):
                            continue
                        stage = partial["timings"][-1]["stage"]
                        await queue.put(stage)

                        if not evidence_sent and stage in {"confidence_gate", "refuse"}:
                            evidence_sent = True
                            timings = [StageTiming(**item) for item in last_state["timings"]]
                            await queue.put(
                                EvidencePreview(
                                    transcript=last_state["transcript"],
                                    confidence=last_state["confidence"],
                                    refused=last_state["refused"],
                                    citations=_build_citations(last_state),
                                    timings=timings,
                                    pipeline_duration_ms=round(
                                        sum(
                                            item.duration_ms
                                            for item in timings
                                            if item.stage not in PROVIDER_STAGES
                                        ),
                                        3,
                                    ),
                                )
                            )

                        # Covers the paths that never stream: a refusal, or a
                        # provider without streaming support.
                        if not answer_sent and stage in {"groundedness_check", "refuse"}:
                            answer_sent = True
                            if last_state["answer"] and not streamed["tokens"]:
                                await queue.put(AnswerPreview(answer=last_state["answer"]))
                await queue.put(self._build_response(last_state))
            except Exception as exc:  # surfaced to the caller below
                await queue.put(exc)
            finally:
                await queue.put(done)

        task = asyncio.create_task(run())
        try:
            while True:
                item = await queue.get()
                if item is done:
                    break
                if isinstance(item, Exception):
                    raise item
                yield item
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    def _build_response(self, result: GraphState) -> QueryResponse:
        citations = _build_citations(result)
        total = round(sum(float(item["duration_ms"]) for item in result["timings"]), 3)
        return QueryResponse(
            request_id=result["request_id"],
            transcript=result["transcript"],
            answer=result["answer"],
            audio_base64=result["audio_base64"],
            audio_mime_type=result["audio_output_mime_type"],
            citations=citations,
            confidence=result["confidence"],
            refused=result["refused"],
            refusal_reason=result["refusal_reason"],
            guardrails=result["guardrails"],
            timings=result["timings"],
            total_duration_ms=total,
            degraded_services=result["degraded_services"],
        )
