import json

import httpx
import pytest

from vaaani.generation.answer_generator import AnswerGenerator
from vaaani.retrieval.dense import SearchHit

HIT = SearchHit(
    id="gateway-0",
    passage_id="gateway",
    text="The Gateway of India is a monument in Mumbai.",
    score=0.9,
    language="en",
    source_lang="eng_Latn",
    target_lang="eng_Latn",
    strategy="metadata",
)


def _chunk(content: str) -> bytes:
    payload = {"choices": [{"delta": {"content": content}}]}
    return f"data: {json.dumps(payload)}\n\n".encode()


@pytest.mark.asyncio
async def test_stream_emits_pieces_as_the_provider_sends_them(monkeypatch) -> None:
    body = b"".join([_chunk("Mumbai "), _chunk("hosts it. "), _chunk("[1]"), b"data: [DONE]\n\n"])

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(200, content=body)

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def patched(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched)

    generator = AnswerGenerator("key", "https://llm.example", "test-model")
    pieces = [piece async for piece in generator.stream("Where is it?", [HIT], "en-IN")]

    assert pieces == ["Mumbai ", "hosts it. ", "[1]"]
    assert not generator.degraded


@pytest.mark.asyncio
async def test_stream_falls_back_to_extractive_when_the_provider_fails(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"boom")

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def patched(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched)

    generator = AnswerGenerator("key", "https://llm.example", "test-model")
    pieces = [piece async for piece in generator.stream("Where is it?", [HIT], "en-IN")]

    assert generator.degraded
    assert len(pieces) == 1
    assert "Mumbai" in pieces[0]


@pytest.mark.asyncio
async def test_stream_without_a_key_returns_the_extractive_answer() -> None:
    generator = AnswerGenerator(None, "https://llm.example", "test-model")
    pieces = [piece async for piece in generator.stream("Where is it?", [HIT], "en-IN")]
    assert len(pieces) == 1
    assert "Mumbai" in pieces[0]
