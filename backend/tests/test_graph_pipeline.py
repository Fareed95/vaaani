import asyncio

import pytest

from vaaani.api.schemas import QueryRequest, QueryResponse
from vaaani.chunking.base import Document
from vaaani.chunking.metadata_aware import MetadataAwareChunker
from vaaani.config import Settings
from vaaani.services import AnswerPreview, EvidencePreview, ServiceContainer


@pytest.mark.asyncio
async def test_pipeline_returns_citations_guardrails_and_timings() -> None:
    settings = Settings(
        qdrant_url=":memory:",
        enable_ml_models=False,
        confidence_threshold=0.05,
        sarvam_api_key=None,
        llm_api_key=None,
    )
    services = ServiceContainer.build(settings)
    await asyncio.wait_for(services.initialize(), timeout=5)
    chunk = MetadataAwareChunker().chunk(
        Document(
            text="The Gateway of India is a monument in Mumbai overlooking the Arabian Sea.",
            passage_id="gateway",
            language="en",
            source_lang="eng_Latn",
            target_lang="eng_Latn",
        )
    )[0]
    await asyncio.wait_for(
        services.store.upsert([chunk], services.encoder.encode([chunk.text])), timeout=5
    )

    response = await asyncio.wait_for(
        services.query(QueryRequest(query="Where is the Gateway of India?", language="en-IN")),
        timeout=8,
    )

    assert not response.refused
    assert response.citations[0].passage_id == "gateway"
    assert {item.guardrail for item in response.guardrails} == {
        "topic_classifier",
        "confidence_threshold",
        "groundedness_entailment",
    }
    assert any(item.stage == "retrieve" for item in response.timings)
    assert "sarvam_tts" in response.degraded_services


@pytest.mark.asyncio
async def test_low_confidence_refusal_is_specific() -> None:
    settings = Settings(
        qdrant_url=":memory:", enable_ml_models=False, confidence_threshold=0.9
    )
    services = ServiceContainer.build(settings)
    await asyncio.wait_for(services.initialize(), timeout=5)
    response = await asyncio.wait_for(
        services.query(QueryRequest(query="Who discovered penicillin?")), timeout=8
    )
    assert response.refused
    assert response.refusal_reason == "no_retrieval_results"
    assert "no_retrieval_results" in response.answer


@pytest.mark.asyncio
async def test_groundedness_provider_failure_is_fail_closed_after_retries() -> None:
    settings = Settings(
        qdrant_url=":memory:",
        enable_ml_models=False,
        confidence_threshold=0.05,
        sarvam_api_key=None,
        llm_api_key=None,
    )
    services = ServiceContainer.build(settings)
    await services.initialize()
    chunk = MetadataAwareChunker().chunk(
        Document(
            text="The Gateway of India is a monument in Mumbai overlooking the Arabian Sea.",
            passage_id="gateway",
            language="en",
            source_lang="eng_Latn",
            target_lang="eng_Latn",
        )
    )[0]
    await services.store.upsert([chunk], services.encoder.encode([chunk.text]))

    attempts = 0

    def failing_check(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        nonlocal attempts
        attempts += 1
        raise RuntimeError("nli provider unavailable")

    services.nodes.groundedness.check = failing_check  # type: ignore[method-assign]
    response = await services.query(
        QueryRequest(query="Where is the Gateway of India?", language="en-IN")
    )

    assert attempts == 3
    assert response.refused is True
    assert response.refusal_reason == "groundedness_check_unavailable"
    assert "groundedness_check_unavailable" in response.answer
    assert "nli_groundedness" in response.degraded_services
    decision = next(
        item for item in response.guardrails if item.guardrail == "groundedness_entailment"
    )
    assert decision.passed is False
    assert decision.reason == "groundedness_check_unavailable"
    assert decision.details["error_type"] == "RuntimeError"
    timing = next(item for item in response.timings if item.stage == "groundedness_check")
    assert timing.status == "error"


@pytest.mark.asyncio
async def test_stream_sends_evidence_before_generation_and_answer_before_tts() -> None:
    settings = Settings(
        qdrant_url=":memory:",
        enable_ml_models=False,
        confidence_threshold=0.05,
        sarvam_api_key=None,
        llm_api_key=None,
    )
    services = ServiceContainer.build(settings)
    await asyncio.wait_for(services.initialize(), timeout=5)
    chunk = MetadataAwareChunker().chunk(
        Document(
            text="The Gateway of India is a monument in Mumbai overlooking the Arabian Sea.",
            passage_id="gateway",
            language="en",
            source_lang="eng_Latn",
            target_lang="eng_Latn",
        )
    )[0]
    await asyncio.wait_for(
        services.store.upsert([chunk], services.encoder.encode([chunk.text])), timeout=5
    )

    events = []
    async for item in services.query_stages(
        QueryRequest(query="Where is the Gateway of India?", language="en-IN")
    ):
        events.append(item)

    evidence_at = next(i for i, item in enumerate(events) if isinstance(item, EvidencePreview))
    answer_at = next(i for i, item in enumerate(events) if isinstance(item, AnswerPreview))
    generate_at = events.index("generate")
    tts_at = events.index("tts")

    assert evidence_at < generate_at, "evidence must reach the client before the LLM call"
    assert answer_at < tts_at, "answer must reach the client before voice synthesis"
    assert events[evidence_at].citations[0].passage_id == "gateway"
    assert events[answer_at].answer
    assert isinstance(events[-1], QueryResponse)
