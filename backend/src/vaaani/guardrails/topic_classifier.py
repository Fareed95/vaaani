import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TopicDecision:
    passed: bool
    reason: str
    category: str


class TopicClassifier:
    """Fast early gate for unsafe requests and non-informational input."""

    unsafe_patterns = (
        r"\b(build|make|create)\s+(a\s+)?(bomb|explosive|malware|ransomware)\b",
        r"\bsteal\s+(passwords?|credentials?|credit cards?)\b",
        r"\b(bypass|disable)\s+(the\s+)?(safety|guardrail|authentication)\b",
        r"\bhow\s+to\s+(hurt|kill|poison)\b",
    )
    empty_noise = re.compile(r"^[\W_]+$", re.UNICODE)

    def classify(self, query: str) -> TopicDecision:
        normalized = query.casefold().strip()
        if len(normalized) < 2 or self.empty_noise.match(normalized):
            return TopicDecision(False, "query_has_no_searchable_content", "off_topic")
        if any(re.search(pattern, normalized) for pattern in self.unsafe_patterns):
            return TopicDecision(False, "unsafe_instruction_detected", "unsafe")
        return TopicDecision(True, "informational_query_allowed", "informational")
