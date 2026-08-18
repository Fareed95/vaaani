---
title: Vaaani API
emoji: 🎙️
colorFrom: indigo
colorTo: orange
sdk: docker
app_port: 8080
pinned: false
---

# Vaaani API

Voice-enabled multilingual RAG backend. See the [project README](../README.md)
for the full architecture. This Space serves the FastAPI backend only — the
Next.js frontend is deployed separately (e.g. Vercel).

## Required Space secrets

Set these under **Settings → Repository secrets** (never commit them):

| Secret | Purpose |
|---|---|
| `VAAANI_SARVAM_API_KEY` | Sarvam STT/TTS |
| `VAAANI_LLM_API_KEY` | LLM generation (OpenRouter/OpenAI-compatible) |
| `VAAANI_LLM_BASE_URL` | e.g. `https://openrouter.ai/api/v1` |
| `VAAANI_LLM_MODEL` | e.g. `anthropic/claude-sonnet-4.5` |
| `VAAANI_QDRANT_URL` | Qdrant Cloud cluster URL |
| `VAAANI_QDRANT_API_KEY` | Qdrant Cloud API key |
| `VAAANI_CORS_ORIGINS` | Your deployed frontend origin, e.g. `https://your-app.vercel.app` |
| `HF_TOKEN` | Optional — raises Hugging Face model-download rate limits |
