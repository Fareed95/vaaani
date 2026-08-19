from typing import Any, TypedDict

from vaaani.retrieval.dense import SearchHit


class GraphState(TypedDict):
    request_id: str
    query: str
    language: str
    audio: bytes | None
    audio_mime_type: str
    conversation: list[dict[str, str]]
    transcript: str
    rewritten_query: str
    candidates: list[SearchHit]
    reranked: list[SearchHit]
    answer: str
    audio_base64: str | None
    audio_output_mime_type: str | None
    confidence: float
    refused: bool
    refusal_reason: str | None
    guardrails: list[dict[str, Any]]
    timings: list[dict[str, Any]]
    degraded_services: list[str]
    errors: list[str]
    # Optional callback the generate node pushes tokens into, so the answer
    # reaches the client as the LLM produces it instead of after it finishes.
    token_sink: Any | None
