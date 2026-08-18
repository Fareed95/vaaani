# Vaaani

Vaaani is a voice-first, multilingual retrieval-augmented answer system built for Indian languages. A spoken or typed question moves through Sarvam speech recognition, hybrid dense + BM25 retrieval, cross-encoder reranking, explicit guardrails, grounded generation, and Sarvam speech synthesis. Every response carries citations, confidence, guardrail decisions, and stage-level latency.

## Quickstart

Requirements: Docker, Node.js 20+, npm, and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
make setup
make docker-up       # Qdrant + API, or run `make dev` for in-memory Qdrant
make build-index     # set DATASET_LIMIT for a small first index
```

Open the interface at `http://localhost:3000`, the API docs at `http://localhost:8000/docs`, and Qdrant at `http://localhost:6333/dashboard`.

The application is useful without paid credentials: typed queries, deterministic local embeddings, extractive grounded answers, and browser audio playback remain available. Configure Sarvam and an OpenAI-compatible LLM for the full production voice loop.

## Architecture

```text
voice/text → STT → topic gate → contextual rewrite → dense + BM25
           → RRF → cross-encoder rerank → confidence gate
           → grounded generation → entailment check → TTS → cited response
```

The backend is a typed LangGraph state machine. Qdrant payload indexes keep language, passage ID, source/target language, and chunk strategy filterable. Heavy ML models are lazy-loaded; health and startup stay fast.

## Commands

`make setup`, `make dev`, `make test`, `make lint`, `make build-index`, `make benchmark`, `make docs-serve`, `make docs-build`, `make docker-up`, `make deploy-backend`, and `make deploy-frontend` are the supported entrypoints.

Full documentation lives in [`docs/`](docs/index.md) and is built with MkDocs Material.

**Live application**: https://frontend-five-liard.vercel.app/vaaani
**Live API**: https://vaaani-api-production.up.railway.app

## Data and models

- Dataset: `ai4bharat/MSMARCO-XI`
- Embeddings: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` locally (`VAAANI_ENABLE_ML_MODELS=true`); the live deployment runs the feature-hash/lexical fallback (`VAAANI_ENABLE_ML_MODELS=false`) since the real models need ~1.7GB RAM, more than the free hosting tier's 1GB ceiling
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2` (same fallback note as above)
- Groundedness: `cross-encoder/nli-deberta-v3-small` (same fallback note as above)
- Speech: Sarvam AI STT and TTS (real in both local and deployed)

See [decisions](docs/decisions.md) for offline fallbacks and assumptions. No secrets belong in source control.

## Verification

Real numbers, not claims — every command below can be rerun to reproduce the same class of result.

| Check | Command | Last result |
|---|---|---|
| Backend tests | `uv run --project backend pytest backend/tests` | 14 passed, 1 skipped |
| Backend lint | `uv run --project backend ruff check backend/src` | clean |
| Frontend tests | `npm test` (in `frontend/`) | 5 passed |
| Frontend typecheck | `npx tsc --noEmit` (in `frontend/`) | clean |
| Frontend lint | `npx eslint .` (in `frontend/`) | clean |
| Real latency benchmark | `python backend/scripts/run_benchmark.py` against a running instance | see [`docs/latency-benchmarks.md`](docs/latency-benchmarks.md) — 50/50 real queries, 6 languages, 0 failures against the live deployment; retrieval pipeline (retrieve+rerank) **P50 59.6ms, P70 72.6ms**, under the 200ms target |

Raw benchmark artifacts (JSON + Markdown, one pair per run) are committed under [`benchmarks/results/`](benchmarks/results/).

## License

MIT
