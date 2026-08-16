import uuid

from vaaani.chunking.base import Chunk, Document


class FixedSizeChunker:
    name = "fixed"

    def __init__(self, size: int = 256, overlap: float = 0.2) -> None:
        if size < 2:
            raise ValueError("size must be at least 2 tokens")
        if not 0 <= overlap < 1:
            raise ValueError("overlap must be between 0 and 1")
        self.size = size
        self.overlap = overlap

    def chunk(self, document: Document) -> list[Chunk]:
        words = document.text.split()
        if not words:
            return []
        step = max(1, self.size - round(self.size * self.overlap))
        chunks: list[Chunk] = []
        for position, start in enumerate(range(0, len(words), step)):
            text = " ".join(words[start : start + self.size])
            if not text:
                break
            identifier = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"{document.passage_id}:{self.name}:{position}")
            )
            chunks.append(
                Chunk(
                    id=identifier,
                    text=text,
                    passage_id=document.passage_id,
                    language=document.language,
                    source_lang=document.source_lang,
                    target_lang=document.target_lang,
                    strategy=self.name,
                    position=position,
                    metadata={**document.metadata, "token_start": start},
                )
            )
            if start + self.size >= len(words):
                break
        return chunks
