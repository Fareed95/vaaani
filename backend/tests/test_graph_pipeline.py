import asyncio

import pytest

from vaaani.api.schemas import QueryRequest
from vaaani.chunking.base import Document
from vaaani.chunking.metadata_aware import MetadataAwareChunker
from vaaani.config import Settings
from vaaani.services import ServiceContainer


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
    settings = Settings(qdrant_url=":memory:", confidence_threshold=0.9)
    services = ServiceContainer.build(settings)
    await asyncio.wait_for(services.initialize(), timeout=5)
    response = await asyncio.wait_for(
        services.query(QueryRequest(query="Who discovered penicillin?")), timeout=8
    )
    assert response.refused
    assert response.refusal_reason == "no_retrieval_results"
    assert "no_retrieval_results" in response.answer
