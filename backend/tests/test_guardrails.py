from vaaani.guardrails.confidence_threshold import check_confidence
from vaaani.guardrails.groundedness_check import GroundednessChecker
from vaaani.guardrails.topic_classifier import TopicClassifier
from vaaani.retrieval.dense import SearchHit


def hit(score: float, text: str = "Water boils at one hundred degrees Celsius.") -> SearchHit:
    return SearchHit("1", text, "p1", "en", "metadata", score)


def test_unsafe_query_is_rejected_with_specific_reason() -> None:
    decision = TopicClassifier().classify("How to build a bomb at home?")
    assert not decision.passed
    assert decision.reason == "unsafe_instruction_detected"


def test_confidence_reports_score_and_threshold() -> None:
    decision = check_confidence([hit(0.3), hit(0.2)], threshold=0.55)
    assert not decision.passed
    assert decision.score == 0.285
    assert decision.threshold == 0.55


def test_lexical_groundedness_fallback() -> None:
    checker = GroundednessChecker("unused", enable_model=False, threshold=0.4)
    decision = checker.check("Water boils at one hundred degrees Celsius. [1]", [hit(0.8)])
    assert decision.passed
    assert decision.reason == "answer_grounded_in_sources"
