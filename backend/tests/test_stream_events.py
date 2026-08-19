import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from vaaani.api.routes_query import router as query_router
from vaaani.api.schemas import Citation, QueryResponse, StageTiming
from vaaani.services import AnswerPreview, EvidencePreview

TIMING = StageTiming(
    stage="retrieve",
    started_at="2026-08-20T00:00:00Z",
    ended_at="2026-08-20T00:00:00.012Z",
    duration_ms=11.6,
    status="ok",
)

CITATION = Citation(
    rank=1,
    passage_id="gateway",
    text="The Gateway of India is a monument in Mumbai.",
    score=0.91,
    language="en",
    chunk_strategy="metadata",
)


class _ScriptedServices:
    """Stands in for ServiceContainer so the wire format can be checked
    without loading embedding models."""

    async def query_stages(self, payload):  # type: ignore[no-untyped-def]
        yield "retrieve"
        yield EvidencePreview(
            transcript="Where is the Gateway of India?",
            confidence=0.82,
            refused=False,
            citations=[CITATION],
            timings=[TIMING],
            pipeline_duration_ms=12.0,
        )
        yield "confidence_gate"
        yield AnswerPreview(answer="It is in Mumbai.")
        yield "tts"
        yield QueryResponse(
            request_id="req-1",
            transcript="Where is the Gateway of India?",
            answer="It is in Mumbai.",
            audio_base64="YXVkaW8=",
            audio_mime_type="audio/wav",
            citations=[CITATION],
            confidence=0.82,
        )


def _event_names(body: str) -> list[str]:
    return re.findall(r"^event: (\w+)$", body, flags=re.MULTILINE)


def test_stream_orders_evidence_and_answer_ahead_of_the_provider_stages() -> None:
    app = FastAPI()
    app.include_router(query_router)
    app.state.services = _ScriptedServices()

    with TestClient(app) as client:
        response = client.post("/query/stream", json={"query": "Where is the Gateway of India?"})

    assert response.status_code == 200
    names = _event_names(response.text)

    assert names.index("evidence") < names.index("token")
    assert names.index("token") < names.index("audio")
    assert names[-1] == "done"
    # The answer is streamed once, from the preview — not again from the final
    # response.
    assert response.text.count('"token"') == len("It is in Mumbai.".split())
    assert '"passage_id": "gateway"' in response.text
    # The pipeline score ships with the evidence, not with the final metadata.
    assert '"pipeline_duration_ms": 12.0' in response.text
