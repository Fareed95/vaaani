# API reference

Interactive OpenAPI documentation is available at `/docs` on every API deployment.

## `GET /health`

Returns service status, indexed chunk count, language configuration, voice providers, and retrieval mode. `degraded` means the API is usable but a cloud credential or heavyweight local model is unavailable.

## `POST /query`

Accepts JSON with one of `query` or base64 `audio_base64`, plus `language`, optional `audio_mime_type`, and up to 12 conversation turns.

```json
{
  "query": "Where is the Gateway of India?",
  "language": "en-IN",
  "conversation": []
}
```

The response includes transcript, answer, optional WAV audio, top-five citations, confidence, refusal reason, all guardrail decisions, stage timings, total duration, and degraded service names.

## `POST /query/stream`

Accepts the same body and responds as `text/event-stream`:

- `metadata`: transcript, citations, guardrails, and timings
- `token`: one answer token for progressive rendering
- `audio`: base64 audio and MIME type when Sarvam TTS succeeds
- `done`: request ID
- `error`: a safe error message

Audio is limited to 20 MB at the API boundary and 30 seconds in the recorder, matching the real-time speech endpoint’s intended use.
