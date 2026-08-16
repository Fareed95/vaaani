from dataclasses import dataclass, field, replace
from typing import Any

from vaaani.embeddings.multilingual_encoder import MultilingualEncoder
from vaaani.vectorstore.qdrant_client import QdrantVectorStore


@dataclass(frozen=True, slots=True)
class SearchHit:
    id: str
    text: str
    passage_id: str
    language: str
    strategy: str
    score: float
    source_lang: str | None = None
    target_lang: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_score(self, score: float) -> "SearchHit":
        return replace(self, score=score)


class DenseRetriever:
    def __init__(self, store: QdrantVectorStore, encoder: MultilingualEncoder) -> None:
        self.store = store
        self.encoder = encoder

    async def search(
        self, query: str, language: str | None = None, limit: int = 50
    ) -> list[SearchHit]:
        vector = self.encoder.encode([query])[0]
        return await self.store.search(vector, language=language, limit=limit)
