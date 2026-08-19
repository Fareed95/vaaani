import base64
import binascii
import uuid
from dataclasses import dataclass
from typing import Any

from vaaani.api.schemas import Citation, QueryRequest, QueryResponse
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
    """Retrieval result, streamed before generation starts."""

    transcript: str
    confidence: float
    refused: bool
    citations: list[Citation]


@dataclass(slots=True)
class AnswerPreview:
    """Verified answer text, streamed before voice synthesis starts."""

    answer: str


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
        }

    async def query(self, request: QueryRequest) -> QueryResponse:
        initial = self._build_initial_state(request)
        result: GraphState = await self.graph.ainvoke(initial)
        return self._build_response(result)

    async def query_stages(self, request: QueryRequest):  # type: ignore[no-untyped-def]
        """Yield each pipeline stage name as it completes, plus two early
        payloads so the client isn't blocked on the slow provider calls:
        EvidencePreview once retrieval has settled (while the LLM works) and
        AnswerPreview once groundedness passes (while TTS runs). The final
        QueryResponse comes last."""
        initial = self._build_initial_state(request)
        last_state: GraphState = initial
        evidence_sent = False
        answer_sent = False
        async for update in self.graph.astream(initial, stream_mode="updates"):
            for partial in update.values():
                last_state = {**last_state, **partial}
                if not partial.get("timings"):
                    continue
                stage = partial["timings"][-1]["stage"]
                yield stage

                if not evidence_sent and stage in {"confidence_gate", "refuse"}:
                    evidence_sent = True
                    yield EvidencePreview(
                        transcript=last_state["transcript"],
                        confidence=last_state["confidence"],
                        refused=last_state["refused"],
                        citations=_build_citations(last_state),
                    )

                # The graph is driven by this loop, so yielding here means the
                # answer reaches the browser before the tts node even starts.
                if not answer_sent and stage in {"groundedness_check", "refuse"}:
                    if last_state["answer"]:
                        answer_sent = True
                        yield AnswerPreview(answer=last_state["answer"])
        yield self._build_response(last_state)

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
