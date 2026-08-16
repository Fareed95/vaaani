import re

import numpy as np
from rank_bm25 import BM25Okapi

from vaaani.retrieval.dense import SearchHit


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


class SparseBM25Retriever:
    def rank(self, query: str, corpus: list[SearchHit], limit: int = 50) -> list[SearchHit]:
        if not corpus:
            return []
        tokenized = [tokenize(hit.text) for hit in corpus]
        if not any(tokenized):
            return []
        raw_scores = BM25Okapi(tokenized).get_scores(tokenize(query))
        maximum = float(np.max(raw_scores)) if len(raw_scores) else 0.0
        if maximum <= 0:
            query_terms = set(tokenize(query))
            raw_scores = np.asarray(
                [len(query_terms & set(tokens)) / max(1, len(query_terms)) for tokens in tokenized]
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
