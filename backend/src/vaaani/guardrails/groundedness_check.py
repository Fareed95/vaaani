import re
from dataclasses import dataclass
from functools import cached_property

from vaaani.retrieval.dense import SearchHit


@dataclass(frozen=True, slots=True)
class GroundednessDecision:
    passed: bool
    score: float
    threshold: float
    reason: str


class GroundednessChecker:
    def __init__(self, model_name: str, enable_model: bool = True, threshold: float = 0.45) -> None:
        self.model_name = model_name
        self.enable_model = enable_model
        self.threshold = threshold
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

    def check(self, answer: str, contexts: list[SearchHit]) -> GroundednessDecision:
        if not answer or not contexts:
            return GroundednessDecision(False, 0.0, self.threshold, "answer_has_no_evidence")
        evidence = " ".join(hit.text for hit in contexts)
        if self.model is not None:
            values = self.model.predict([(evidence[:12000], answer[:3000])])
            raw = float(values[0]) if not hasattr(values[0], "__len__") else float(max(values[0]))
            score = 1 / (1 + pow(2.718281828, -raw))
        else:
            answer_terms = set(re.findall(r"\w+", answer.casefold(), flags=re.UNICODE))
            evidence_terms = set(re.findall(r"\w+", evidence.casefold(), flags=re.UNICODE))
            content = {term for term in answer_terms if len(term) > 3}
            score = len(content & evidence_terms) / len(content) if content else 0.0
        score = round(float(score), 4)
        return GroundednessDecision(
            score >= self.threshold,
            score,
            self.threshold,
            "answer_grounded_in_sources"
            if score >= self.threshold
            else "groundedness_entailment_failed",
        )
