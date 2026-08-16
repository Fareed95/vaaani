import re
import uuid
from collections.abc import Callable

import numpy as np

from vaaani.chunking.base import Chunk, Document


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?।])\s+", text) if part.strip()]


class SemanticChunker:
    name = "semantic"

    def __init__(
        self,
        embed: Callable[[list[str]], list[list[float]]] | None = None,
        threshold: float = 0.48,
        max_sentences: int = 5,
    ) -> None:
        self.embed = embed
        self.threshold = threshold
        self.max_sentences = max_sentences

    @staticmethod
    def _lexical_vectors(sentences: list[str]) -> list[list[float]]:
        vocabulary = sorted(
            {word.casefold() for sentence in sentences for word in sentence.split()}
        )
        if not vocabulary:
            return [[0.0] for _ in sentences]
        index = {word: i for i, word in enumerate(vocabulary)}
        vectors: list[list[float]] = []
        for sentence in sentences:
            vector = [0.0] * len(vocabulary)
            for word in sentence.split():
                vector[index[word.casefold()]] += 1
            vectors.append(vector)
        return vectors

    def chunk(self, document: Document) -> list[Chunk]:
        sentences = _sentences(document.text)
        if not sentences:
            return []
        vectors = np.asarray(
            self.embed(sentences) if self.embed else self._lexical_vectors(sentences), dtype=float
        )
        groups: list[list[str]] = [[sentences[0]]]
        for index in range(1, len(sentences)):
            left, right = vectors[index - 1], vectors[index]
            denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
            similarity = float(np.dot(left, right) / denominator) if denominator else 0.0
            if similarity < self.threshold or len(groups[-1]) >= self.max_sentences:
                groups.append([])
            groups[-1].append(sentences[index])
        return [
            Chunk(
                id=str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"{document.passage_id}:{self.name}:{position}",
                    )
                ),
                text=" ".join(group),
                passage_id=document.passage_id,
                language=document.language,
                source_lang=document.source_lang,
                target_lang=document.target_lang,
                strategy=self.name,
                position=position,
                metadata=document.metadata,
            )
            for position, group in enumerate(groups)
        ]
