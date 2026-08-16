import re
from functools import cached_property

from vaaani.retrieval.dense import SearchHit


class CrossEncoderReranker:
    def __init__(self, model_name: str, enable_model: bool = True) -> None:
        self.model_name = model_name
        self.enable_model = enable_model
        self.degraded = not enable_model

    @cached_property
    def model(self):  # type: ignore[no-untyped-def]
        if not self.enable_model:
            return None
        try:
            from sentence_transformers import CrossEncoder

            return CrossEncoder(self.model_name)
        except Exception:
            self.degraded = True
            return None

    @staticmethod
    def _lexical_score(query: str, passage: str) -> float:
        query_terms = set(re.findall(r"\w+", query.casefold(), flags=re.UNICODE))
        passage_terms = set(re.findall(r"\w+", passage.casefold(), flags=re.UNICODE))
        if not query_terms:
            return 0.0
        return len(query_terms & passage_terms) / len(query_terms)

    def rerank(self, query: str, hits: list[SearchHit], limit: int = 5) -> list[SearchHit]:
        if not hits:
            return []
        if self.model is not None:
            raw = self.model.predict([(query, hit.text) for hit in hits])
            scores = [1 / (1 + pow(2.718281828, -float(value))) for value in raw]
        else:
            scores = [
                0.65 * self._lexical_score(query, hit.text) + 0.35 * hit.score for hit in hits
            ]
        rescored = [hit.with_score(float(score)) for hit, score in zip(hits, scores, strict=True)]
        return sorted(rescored, key=lambda item: item.score, reverse=True)[:limit]
