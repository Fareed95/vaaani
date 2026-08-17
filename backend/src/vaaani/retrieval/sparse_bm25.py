import re

import numpy as np
from rank_bm25 import BM25Okapi

from vaaani.retrieval.dense import SearchHit


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


class SparseBM25Retriever:
    """BM25 over a corpus snapshot. Callers may pin a `cache_key` (e.g. language)
    so the tokenized index is built once and reused across requests instead of
    re-tokenizing the whole corpus on every query."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[list[SearchHit], BM25Okapi | None]] = {}

    def is_cached(self, cache_key: str) -> bool:
        return cache_key in self._cache

    def warm(self, cache_key: str, corpus: list[SearchHit]) -> None:
        tokenized = [tokenize(hit.text) for hit in corpus]
        bm25 = BM25Okapi(tokenized) if any(tokenized) else None
        self._cache[cache_key] = (corpus, bm25)

    def rank(
        self,
        query: str,
        corpus: list[SearchHit] | None = None,
        limit: int = 50,
        cache_key: str | None = None,
    ) -> list[SearchHit]:
        if cache_key is not None and cache_key in self._cache:
            corpus, bm25 = self._cache[cache_key]
        else:
            if not corpus:
                return []
            tokenized = [tokenize(hit.text) for hit in corpus]
            bm25 = BM25Okapi(tokenized) if any(tokenized) else None
            if cache_key is not None:
                self._cache[cache_key] = (corpus, bm25)
        if not corpus or bm25 is None:
            return []
        raw_scores = bm25.get_scores(tokenize(query))
        maximum = float(np.max(raw_scores)) if len(raw_scores) else 0.0
        if maximum <= 0:
            query_terms = set(tokenize(query))
            raw_scores = np.asarray(
                [
                    len(query_terms & set(tokenize(hit.text))) / max(1, len(query_terms))
                    for hit in corpus
                ]
            )
            maximum = float(np.max(raw_scores)) if len(raw_scores) else 0.0
        order = np.argsort(raw_scores)[::-1][:limit]
        return [
            corpus[int(index)].with_score(
                float(raw_scores[int(index)] / maximum) if maximum else 0.0
            )
            for index in order
            if raw_scores[int(index)] > 0
        ]
