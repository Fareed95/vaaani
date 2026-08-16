import uuid

from vaaani.chunking.base import Chunk, Document


class MetadataAwareChunker:
    """Preserve the native query/passage/language record as the retrieval boundary."""

    name = "metadata"

    def chunk(self, document: Document) -> list[Chunk]:
        if not document.text.strip():
            return []
        return [
            Chunk(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document.passage_id}:{self.name}")),
                text=document.text.strip(),
                passage_id=document.passage_id,
                language=document.language,
                source_lang=document.source_lang,
                target_lang=document.target_lang,
                strategy=self.name,
                position=0,
                metadata={**document.metadata, "native_query": document.query},
            )
        ]
