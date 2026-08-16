# Architecture

Vaaani separates orchestration from providers. Each LangGraph node accepts and returns the typed `GraphState`; provider adapters handle Qdrant, Sarvam, and the OpenAI-compatible generation endpoint. A node is retried twice after its first attempt. If all attempts fail, the node emits a degraded service or a specific refusal instead of leaking an exception to the interface.

```mermaid
flowchart LR
    A[Voice or text] --> B[STT\nSarvam Saaras v3]
    B --> C{Topic gate}
    C -->|allowed| D[Context rewrite]
    C -->|unsafe / empty| R[Specific refusal]
    D --> E[Dense retrieval\nmultilingual MPNet + Qdrant]
    D --> F[BM25 retrieval]
    E --> G[RRF top 20]
    F --> G
    G --> H[Cross-encoder\ntop 5]
    H --> I{Confidence ≥ threshold?}
    I -->|no| R
    I -->|yes| J[Grounded generation]
    J --> K{NLI entailment?}
    K -->|no| R
    K -->|yes| L[TTS\nSarvam Bulbul v3]
    L --> M[Cited API response]
    R --> M
    T[(Timing telemetry)] -. every stage .-> M
```

## State and routing

`GraphState` contains inputs, conversation history, transcript, rewritten query, retrieval candidates, reranked evidence, guardrail decisions, answer/audio, service degradation, and timings. Conditional edges are based only on `refused`, so refusal paths are deterministic and easy to test.

## Deployment topology

The browser talks only to FastAPI. The API and Qdrant should share a region to keep retrieval below the 200 ms target. Sarvam and the generation provider are external network calls; their timings are reported independently. ML models load lazily so health checks and container startup do not wait for model downloads.

## Failure behavior

- Missing Sarvam STT on an audio-only request returns `sarvam_api_key_missing`.
- Missing or unreachable Qdrant becomes `no_retrieval_results` after the retrieval stage records degradation.
- Missing LLM credentials selects an extractive answer assembled only from retrieved evidence.
- Missing TTS credentials retains the text answer and identifies `sarvam_tts` as degraded.
- Low confidence and failed entailment produce visible, machine-readable refusal details.
