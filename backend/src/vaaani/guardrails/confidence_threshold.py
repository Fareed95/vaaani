from dataclasses import dataclass

from vaaani.retrieval.dense import SearchHit


@dataclass(frozen=True, slots=True)
class ConfidenceDecision:
    passed: bool
    score: float
    threshold: float
    reason: str


def check_confidence(hits: list[SearchHit], threshold: float) -> ConfidenceDecision:
    if not hits:
        return ConfidenceDecision(False, 0.0, threshold, "no_retrieval_results")
    top = hits[0].score
    supporting = sum(hit.score for hit in hits[:3]) / min(3, len(hits))
    score = round(0.7 * top + 0.3 * supporting, 4)
    return ConfidenceDecision(
        passed=score >= threshold,
        score=score,
        threshold=threshold,
        reason="retrieval_confidence_sufficient"
        if score >= threshold
        else "retrieval_confidence_low",
    )
