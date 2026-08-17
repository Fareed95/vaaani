import hashlib
import re
from functools import cached_property

import numpy as np


class MultilingualEncoder:
    """Lazy sentence-transformer with a deterministic offline feature-hash fallback."""

    def __init__(
        self, model_name: str, enable_model: bool = True, fallback_size: int = 384
    ) -> None:
        self.model_name = model_name
        self.enable_model = enable_model
        self.fallback_size = fallback_size
        self.degraded = not enable_model

    @cached_property
    def model(self):  # type: ignore[no-untyped-def]
        if not self.enable_model:
            return None
        try:
            from sentence_transformers import SentenceTransformer

            return SentenceTransformer(self.model_name)
        except Exception as exc:
            raise RuntimeError(f"embedding_model_unavailable:{self.model_name}") from exc

    @property
    def dimension(self) -> int:
        if self.model is not None:
            return int(self.model.get_embedding_dimension())
        return self.fallback_size

    def _feature_hash(self, text: str) -> list[float]:
        vector = np.zeros(self.fallback_size, dtype=np.float32)
        tokens = re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest, "big") % self.fallback_size
            sign = 1 if digest[0] & 1 else -1
            vector[bucket] += sign
        norm = np.linalg.norm(vector)
        if norm:
            vector /= norm
        return vector.tolist()

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.model is not None:
            values = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return np.asarray(values, dtype=np.float32).tolist()
        return [self._feature_hash(text) for text in texts]
