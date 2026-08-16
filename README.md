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

Full documentation lives in [`docs/`](docs/index.md) and is built with MkDocs Material. Hosted docs: **deployment URL to be added after publishing**. Live application: **deployment URL to be added after publishing**.

## Data and models

- Dataset: `ai4bharat/MSMARCO-XI`
- Embeddings: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Groundedness: `cross-encoder/nli-deberta-v3-small`
- Speech: Sarvam AI STT and TTS

See [decisions](docs/decisions.md) for offline fallbacks and assumptions. No secrets belong in source control.

## License

MIT
