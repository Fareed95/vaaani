# Guardrails

Guardrails are observable decisions, not hidden string filters. The API returns `guardrail`, `passed`, `reason`, and quantitative `details` for each check.

## Topic and unsafe-content gate

A fast deterministic classifier runs before retrieval. It blocks known unsafe instruction categories and input with no searchable content. MSMARCO-XI is broad-domain, so informational questions are not restricted to a narrow topic taxonomy.

## Retrieval confidence

The gate combines the best reranker score (70%) with mean support from the top three (30%). The default threshold is `0.40` and is environment-configurable. With no hits, the score is exactly zero and the reason is `no_retrieval_results`.

## Groundedness

Production mode uses an NLI cross-encoder to test the answer against the concatenated top-five passages. Local lightweight mode uses content-token coverage; this is declared as a degraded service and is never represented as model-based entailment.

Example refusal metadata:

```json
{
  "guardrail": "confidence_threshold",
  "passed": false,
  "reason": "retrieval_confidence_low",
  "details": {"confidence_score": 0.31, "threshold": 0.55}
}
```
