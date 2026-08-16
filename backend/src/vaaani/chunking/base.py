from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class Document:
    text: str
    passage_id: str
    language: str
    source_lang: str | None = None
    target_lang: str | None = None
    query: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Chunk:
    id: str
    text: str
    passage_id: str
    language: str
    source_lang: str | None
    target_lang: str | None
    strategy: str
    position: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "passage_id": self.passage_id,
            "language": self.language,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "chunk_strategy": self.strategy,
            "position": self.position,
            **self.metadata,
        }


class Chunker(Protocol):
    name: str

    def chunk(self, document: Document) -> list[Chunk]: ...
