import json
import re
from collections.abc import AsyncIterator

import httpx

from vaaani.retrieval.dense import SearchHit


class AnswerGenerator:
    def __init__(self, api_key: str | None, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.degraded = not bool(api_key)

    @staticmethod
    def _extractive_answer(query: str, hits: list[SearchHit]) -> str:
        query_terms = set(re.findall(r"\w+", query.casefold(), flags=re.UNICODE))
        sentences: list[tuple[float, str, int]] = []
        for rank, hit in enumerate(hits[:5], start=1):
            for sentence in re.split(r"(?<=[.!?।])\s+", hit.text):
                terms = set(re.findall(r"\w+", sentence.casefold(), flags=re.UNICODE))
                overlap = len(query_terms & terms) / max(1, len(query_terms))
                sentences.append((overlap + hit.score * 0.2, sentence.strip(), rank))
        chosen = sorted(sentences, reverse=True)[:3]
        if not chosen:
            return (
                "The indexed evidence does not contain enough information to answer this question."
            )
        chosen.sort(key=lambda item: item[2])
        return " ".join(f"{sentence} [{rank}]" for _, sentence, rank in chosen if sentence)

    def _messages(self, query: str, hits: list[SearchHit], language: str) -> list[dict[str, str]]:
        context = "\n\n".join(f"[{rank}] {hit.text}" for rank, hit in enumerate(hits[:5], start=1))
        return [
            {
                "role": "system",
                "content": (
                    "Answer only from the supplied evidence. Preserve the user's language. "
                    "Cite factual sentences with bracketed source numbers. If evidence is "
                    "insufficient, state that directly. Do not invent citations."
                ),
            },
            {
                "role": "user",
                "content": f"Language: {language}\nQuestion: {query}\nEvidence:\n{context}",
            },
        ]

    async def generate(self, query: str, hits: list[SearchHit], language: str) -> str:
        if not self.api_key:
            return self._extractive_answer(query, hits)
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": self._messages(query, hits, language),
                        "temperature": 0.1,
                    },
                )
                response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"]).strip()
        except (httpx.HTTPError, KeyError, IndexError, TypeError):
            self.degraded = True
            return self._extractive_answer(query, hits)

    async def stream(self, query: str, hits: list[SearchHit], language: str) -> AsyncIterator[str]:
        """Yield answer text as the provider produces it. Falls back to the
        extractive answer only if nothing has been emitted yet — a mid-stream
        failure can't be undone on the client, so it ends the answer instead."""
        if not self.api_key:
            yield self._extractive_answer(query, hits)
            return

        emitted = False
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": self._messages(query, hits, language),
                        "temperature": 0.1,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        piece = _sse_delta(line)
                        if piece:
                            emitted = True
                            yield piece
        except (httpx.HTTPError, KeyError, IndexError, TypeError):
            self.degraded = True
            if not emitted:
                yield self._extractive_answer(query, hits)


def _sse_delta(line: str) -> str:
    if not line.startswith("data:"):
        return ""
    payload = line[len("data:") :].strip()
    if not payload or payload == "[DONE]":
        return ""
    try:
        choices = json.loads(payload)["choices"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return ""
    if not choices:
        return ""
    return str(choices[0].get("delta", {}).get("content") or "")
