import re

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

    async def generate(self, query: str, hits: list[SearchHit], language: str) -> str:
        if not self.api_key:
            return self._extractive_answer(query, hits)
        context = "\n\n".join(f"[{rank}] {hit.text}" for rank, hit in enumerate(hits[:5], start=1))
        messages = [
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
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "messages": messages, "temperature": 0.1},
                )
                response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"]).strip()
        except (httpx.HTTPError, KeyError, IndexError, TypeError):
            self.degraded = True
            return self._extractive_answer(query, hits)
