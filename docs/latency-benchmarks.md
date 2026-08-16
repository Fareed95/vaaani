# Latency Benchmarks

Generated `20260816T194358Z` from 5 successful dataset queries using an in-process local smoke run.

| Stage | P50 | P70 | P100 |
|---|---:|---:|---:|
| stt | 0.0 ms | 0.0 ms | 0.0 ms |
| query_classify | 0.0 ms | 0.1 ms | 0.7 ms |
| query_rewrite | 0.0 ms | 0.0 ms | 0.0 ms |
| retrieve | 11.2 ms | 11.4 ms | 19.4 ms |
| rerank | 0.9 ms | 1.0 ms | 1.2 ms |
| confidence_gate | 0.0 ms | 0.0 ms | 0.0 ms |
| generate | 0.4 ms | 0.5 ms | 0.9 ms |
| groundedness_check | 0.3 ms | 0.3 ms | 0.5 ms |
| tts | 150.7 ms | 150.8 ms | 151.0 ms |
| response | 0.0 ms | 0.0 ms | 0.0 ms |
| total | 162.8 ms | 163.3 ms | 173.5 ms |
| refuse | 0.0 ms | 0.0 ms | 0.0 ms |

Generation latency is intentionally separate from retrieval latency; the under-200 ms target applies only to retrieval in a same-region deployment.

This smoke run used feature-hash embeddings, extractive generation, lexical groundedness, in-memory Qdrant, and an unavailable TTS adapter. It validates instrumentation and is not a cloud latency claim.
