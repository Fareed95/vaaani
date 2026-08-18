import asyncio
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from vaaani.chunking.base import Chunk

if TYPE_CHECKING:
    from vaaani.retrieval.dense import SearchHit


class QdrantVectorStore:
    def __init__(self, url: str, collection: str, api_key: str | None = None) -> None:
        self.collection = collection
        self.local = url == ":memory:"
        self.client = (
            QdrantClient(location=":memory:")
            if self.local
            else QdrantClient(url=url, api_key=api_key, timeout=30)
        )

    async def _execute(self, operation):  # type: ignore[no-untyped-def]
        # QdrantLocal owns thread-affine locks; remote I/O belongs in a worker thread.
        return operation() if self.local else await asyncio.to_thread(operation)

    async def ensure_collection(self, vector_size: int, recreate: bool = False) -> None:
        def operation() -> None:
            existing = self.client.collection_exists(self.collection)
            if existing and recreate:
                self.client.delete_collection(self.collection)
                existing = False
            if not existing:
                self.client.create_collection(
                    self.collection,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
                payload_fields = (
                    ("language", PayloadSchemaType.KEYWORD),
                    ("chunk_strategy", PayloadSchemaType.KEYWORD),
                    ("passage_id", PayloadSchemaType.KEYWORD),
                    ("source_lang", PayloadSchemaType.KEYWORD),
                    ("target_lang", PayloadSchemaType.KEYWORD),
                )
                for field, schema in payload_fields if not self.local else ():
                    self.client.create_payload_index(
                        collection_name=self.collection, field_name=field, field_schema=schema
                    )

        await self._execute(operation)

    async def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have equal length")
        points = [
            PointStruct(id=chunk.id, vector=vector, payload=chunk.payload())
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        await self._execute(
            lambda: self.client.upsert(collection_name=self.collection, points=points, wait=True)
        )

    @staticmethod
    def _hit(identifier: Any, score: float, payload: dict[str, Any]) -> "SearchHit":
        from vaaani.retrieval.dense import SearchHit

        reserved = {
            "text",
            "passage_id",
            "language",
            "chunk_strategy",
            "source_lang",
            "target_lang",
        }
        return SearchHit(
            id=str(identifier),
            text=str(payload.get("text", "")),
            passage_id=str(payload.get("passage_id", identifier)),
            language=str(payload.get("language", "unknown")),
            strategy=str(payload.get("chunk_strategy", "unknown")),
            score=float(score),
            source_lang=payload.get("source_lang"),
            target_lang=payload.get("target_lang"),
            metadata={key: value for key, value in payload.items() if key not in reserved},
        )

    async def search(
        self, vector: list[float], language: str | None = None, limit: int = 50
    ) -> list["SearchHit"]:
        query_filter = None
        if language:
            query_filter = Filter(
                must=[FieldCondition(key="language", match=MatchValue(value=language))]
            )

        def operation():  # type: ignore[no-untyped-def]
            return self.client.query_points(
                collection_name=self.collection,
                query=vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            ).points

        points = await self._execute(operation)
        return [self._hit(point.id, point.score, point.payload or {}) for point in points]

    async def corpus(self, language: str | None = None, limit: int = 2500) -> list["SearchHit"]:
        query_filter = None
        if language:
            query_filter = Filter(
                must=[FieldCondition(key="language", match=MatchValue(value=language))]
            )

        def operation():  # type: ignore[no-untyped-def]
            return self.client.scroll(
                collection_name=self.collection,
                scroll_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )[0]

        points = await self._execute(operation)
        return [self._hit(point.id, 0.0, point.payload or {}) for point in points]

    async def count(self) -> int:
        try:
            result = await self._execute(
                lambda: self.client.count(collection_name=self.collection, exact=True)
            )
            return int(result.count)
        except Exception:
            return 0

    async def add_batches(
        self,
        batches: Iterable[tuple[list[Chunk], list[list[float]]]],
    ) -> int:
        total = 0
        for chunks, vectors in batches:
            await self.upsert(chunks, vectors)
            total += len(chunks)
        return total
