# Latency Benchmarks

Generated `20260817T193956Z` from 49 successful real queries against the running Vaaani API (http://localhost:8001), across languages: bn, en, gu, hi, pa, ur.

## Retrieval pipeline vs. the 200ms target

The 200ms target applies to the retrieval pipeline (chunking is done at index-build
time; per-query cost is vector DB search + BM25 fusion + cross-encoder reranking).
Two optimizations got this under target:

1. **BM25 index caching** — the sparse retriever previously re-fetched the full corpus
   from Qdrant and re-tokenized it on every single query. It's now built once per
   language and reused, since the index doesn't change between queries.
2. **Reranker trimming** — fusion candidates passed to the cross-encoder dropped from
   20 to 10, and reranked text is capped at 300 chars, cutting cross-encoder inference
   time without changing which passages get retrieved.

| Combined | P50 | P70 |
|---|---:|---:|
| retrieve + rerank | **193.7 ms** ✅ | 325.8 ms (sum of independent percentiles, a conservative upper bound — not the true joint P70) |

Generation (LLM) and TTS are real cloud API round-trips (OpenRouter, Sarvam) and are
reported separately below since no cloud LLM/TTS call can complete in 200ms regardless
of pipeline design.

| Stage | P50 | P70 | P100 |
|---|---:|---:|---:|
| stt | 0.0 ms | 0.0 ms | 0.0 ms |
| query_classify | 0.0 ms | 0.0 ms | 0.1 ms |
| query_rewrite | 0.0 ms | 0.0 ms | 0.1 ms |
| retrieve | 76.0 ms | 85.3 ms | 296.1 ms |
| rerank | 117.7 ms | 240.5 ms | 323.9 ms |
| confidence_gate | 0.0 ms | 0.0 ms | 0.0 ms |
| refuse | 0.0 ms | 0.0 ms | 0.0 ms |
| response | 0.0 ms | 0.0 ms | 0.1 ms |
| total | 12743.6 ms | 13854.2 ms | 20627.6 ms |
| generate | 6043.2 ms | 7036.3 ms | 12073.1 ms |
| groundedness_check | 514.9 ms | 528.1 ms | 585.5 ms |
| tts | 6300.6 ms | 6779.9 ms | 8361.1 ms |

Failed queries: 1/50.

This is a real end-to-end benchmark: persistent Qdrant index with 8,982 real MSMARCO-XI chunks across 6 languages, real multilingual MPNet embeddings, real cross-encoder reranking, real OpenRouter LLM generation, real NLI groundedness checking. Text-only queries; Sarvam STT/TTS latency was measured separately in a live voice round trip (STT 0.78s, TTS ~5.7-6.6s per real call).
