from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class QueryRequest(BaseModel):
    query: str | None = Field(default=None, max_length=4000)
    audio_base64: str | None = None
    audio_mime_type: str = "audio/webm"
    language: str = Field(default="en-IN", min_length=2, max_length=16)
    conversation: list[ConversationTurn] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def has_input(self) -> "QueryRequest":
        if not (self.query and self.query.strip()) and not self.audio_base64:
            raise ValueError("Provide query text or audio_base64")
        return self


class Citation(BaseModel):
    rank: int
    passage_id: str
    text: str
    score: float
    language: str
    source_lang: str | None = None
    target_lang: str | None = None
    chunk_strategy: str


class StageTiming(BaseModel):
    stage: str
    started_at: datetime
    ended_at: datetime
    duration_ms: float
    status: Literal["ok", "error", "skipped"] = "ok"


class GuardrailDecision(BaseModel):
    guardrail: str
    passed: bool
    reason: str
    details: dict[str, str | float | bool | None] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    request_id: str
    transcript: str
    answer: str
    audio_base64: str | None = None
    audio_mime_type: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = 0
    refused: bool = False
    refusal_reason: str | None = None
    guardrails: list[GuardrailDecision] = Field(default_factory=list)
    timings: list[StageTiming] = Field(default_factory=list)
    total_duration_ms: float = 0
    degraded_services: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    version: str
    indexed_chunks: int
    vector_db: str
    stt_provider: str = "Sarvam AI"
    tts_provider: str = "Sarvam AI"
    retrieval_mode: str = "dense + BM25 + RRF + rerank"
    languages: list[str]
