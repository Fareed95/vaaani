from collections.abc import Iterable
from dataclasses import dataclass

from vaaani.chunking.base import Chunker
from vaaani.embeddings.multilingual_encoder import MultilingualEncoder
from vaaani.ingestion.load_msmarco_xi import DatasetRecord
from vaaani.vectorstore.qdrant_client import QdrantVectorStore


@dataclass(frozen=True, slots=True)
class IndexStats:
    records: int
    documents: int
    chunks: int


class IndexBuilder:
    def __init__(
        self,
        store: QdrantVectorStore,
        encoder: MultilingualEncoder,
        chunker: Chunker,
        batch_size: int = 64,
    ) -> None:
        self.store = store
        self.encoder = encoder
        self.chunker = chunker
        self.batch_size = batch_size

    async def build(self, records: Iterable[DatasetRecord], recreate: bool = True) -> IndexStats:
        await self.store.ensure_collection(self.encoder.dimension, recreate=recreate)
        record_count = document_count = chunk_count = 0
        batch = []
        for record in records:
            record_count += 1
            for document in record.documents:
                document_count += 1
                batch.extend(self.chunker.chunk(document))
                if len(batch) >= self.batch_size:
                    vectors = self.encoder.encode([chunk.text for chunk in batch])
                    await self.store.upsert(batch, vectors)
                    chunk_count += len(batch)
                    batch = []
        if batch:
            vectors = self.encoder.encode([chunk.text for chunk in batch])
            await self.store.upsert(batch, vectors)
            chunk_count += len(batch)
        return IndexStats(record_count, document_count, chunk_count)
