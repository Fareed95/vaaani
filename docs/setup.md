# Setup and deployment

## Local development

Install Docker, Node.js 20+, npm, and uv. Then:

```bash
cp .env.example .env
make setup
make docker-up
make build-index
```

For a lightweight process without Docker, `make dev` defaults Qdrant to in-memory storage. That index lasts only for the API process, so use Docker for ingestion and durable development.

Set `VAAANI_DATASET_LIMIT=100` for a quick first index. Set `VAAANI_ENABLE_ML_MODELS=true` to download and use the configured Sentence Transformers models; keep it false for deterministic, low-resource smoke tests.

## Credentials

`VAAANI_SARVAM_API_KEY` enables both speech directions. `VAAANI_LLM_API_KEY` enables generative answers. `VAAANI_QDRANT_API_KEY` is required only for authenticated Qdrant Cloud. Never expose these as `NEXT_PUBLIC_*` values.

## Production

1. Create a Qdrant Cloud cluster near the backend and set its URL/key.
2. Deploy the backend container to Railway with the environment contract from `.env.example`.
3. Run `make build-index` from an authenticated one-off worker.
4. Deploy `frontend/` to Vercel and set `NEXT_PUBLIC_API_URL` to the HTTPS API origin.
5. Set `VAAANI_CORS_ORIGINS` to the deployed web origin.
6. Run `make benchmark` against the production API and publish the rebuilt docs.

The `deploy-backend` and `deploy-frontend` Make targets validate their CLIs and invoke the corresponding deployment commands.
