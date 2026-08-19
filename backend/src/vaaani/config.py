from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VAAANI_", env_file=(".env", "../.env"), extra="ignore"
    )

    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    qdrant_url: str = ":memory:"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "vaaani_passages"

    embedding_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    nli_model: str = "cross-encoder/nli-deberta-v3-small"
    enable_ml_models: bool = True
    chunk_strategy: Literal["fixed", "semantic", "metadata"] = "metadata"
    chunk_size: int = 256
    chunk_overlap: float = Field(default=0.2, ge=0, lt=1)
    confidence_threshold: float = Field(default=0.4, ge=0, le=1)
    languages: Annotated[list[str], NoDecode] = ["en", "hi"]
    dataset_name: str = "ai4bharat/MSMARCO-XI"
    dataset_split: str = "train"
    dataset_limit: int = 1000

    voice_provider: Literal["sarvam", "elevenlabs"] = "sarvam"

    sarvam_api_key: str | None = None
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_stt_model: str = "saaras:v3"
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_tts_speaker: str = "shubh"

    # Comma-separated: rotates to the next key when one hits 401/402
    # (exhausted free-tier quota or a revoked key).
    elevenlabs_api_keys: Annotated[list[str], NoDecode] = []
    elevenlabs_base_url: str = "https://api.elevenlabs.io/v1"
    elevenlabs_stt_model: str = "scribe_v1"
    elevenlabs_tts_model: str = "eleven_multilingual_v2"
    elevenlabs_voice_id: str = "pNInz6obpgDQGcFmaJgB"

    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4.1-mini"

    @field_validator("cors_origins", "languages", "elevenlabs_api_keys", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
