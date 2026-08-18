# Decisions and assumptions

## Provider modes

The intended production path uses multilingual MPNet, MiniLM reranking, DeBERTa NLI, an OpenAI-compatible LLM, Qdrant, and Sarvam, and this is what runs locally by default. Model loading fails explicitly when a configured embedding or reranking model is unavailable; it does not silently replace production retrieval.

The live deployment runs with `VAAANI_ENABLE_ML_MODELS=false`: real MPNet + reranker + NLI need roughly 1.7GB RAM once loaded, which exceeds the 1GB ceiling on every free hosting tier tried (Render, Railway). In that mode, retrieval uses normalized Unicode feature hashing and reranking/groundedness use lexical coverage instead of the neural models. The selected fallback mode is surfaced in `degraded_services`. The trade-off is retrieval quality — particularly cross-lingual matching, which feature hashing cannot do — not pipeline structure, chunking, latency instrumentation, harnessing, or guardrail presence, all of which are unaffected.

## Current Sarvam models

Saaras v3 and Bulbul v3 are the defaults. Saarika v2.5 remains configurable but is no longer chosen because Sarvam documents it as legacy. The implementation uses the REST endpoints so the complete response—text, citations, guardrails, timing, and audio—has one request ID.

## Language representation

The UI and Sarvam use BCP-47 codes such as `hi-IN`; Qdrant filters use compact dataset configs such as `hi`. The retrieval node performs that conversion. English data is read from MSMARCO-XI’s parallel `Eng_Query` and `English_passages` fields using the Hindi subset, avoiding a nonexistent English subset. Ingestion maps these codes to the repository's current ISO-639-3 Parquet filenames (for example `hi` → `hintrain.parquet`) rather than relying on deprecated remote dataset scripts.

## Scope of the early gate

MSMARCO-XI is general knowledge, so “off topic” means unsafe instructions or input with no informational content. A narrow keyword allow-list would reject valid cross-domain benchmark questions and encode an undocumented domain assumption.

## Streaming

Answer delivery uses SSE. The provider response is validated and guarded before tokens are emitted, which prioritizes safety over earliest-token latency. The UI still renders the accepted answer token by token. Provider-level speculative streaming is intentionally excluded because a failed post-generation groundedness check must never leak unsupported text.

## Conversation state

The browser supplies the most recent 12 turns. The deterministic rewriter attaches recent context only when the new query contains a likely anaphor. This keeps standalone queries untouched and leaves room for a provider-backed rewrite later without changing graph state.

## Benchmark honesty

The under-200 ms goal applies only to retrieval with a warmed model and same-region Qdrant. STT, generation, groundedness, and TTS are always measured separately. No cloud latency claim is published from a local or fallback-mode run.
