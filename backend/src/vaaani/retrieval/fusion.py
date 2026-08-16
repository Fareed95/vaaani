from collections import defaultdict

from vaaani.retrieval.dense import SearchHit


def reciprocal_rank_fusion(
    rankings: list[list[SearchHit]], limit: int = 20, k: int = 60
) -> list[SearchHit]:
    scores: dict[str, float] = defaultdict(float)
    hits: dict[str, SearchHit] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            scores[hit.id] += 1 / (k + rank)
            hits[hit.id] = hit
    ordered = sorted(scores, key=scores.get, reverse=True)[:limit]
    maximum = max((scores[identifier] for identifier in ordered), default=1.0)
    return [hits[identifier].with_score(scores[identifier] / maximum) for identifier in ordered]
