import os

import numpy as np
import pytest

from vaaani.config import Settings
from vaaani.embeddings.multilingual_encoder import MultilingualEncoder
from vaaani.retrieval.dense import SearchHit
from vaaani.retrieval.reranker import CrossEncoderReranker

pytestmark = pytest.mark.skipif(
    os.getenv("VAAANI_RUN_MODEL_TESTS") != "1",
    reason="set VAAANI_RUN_MODEL_TESTS=1 to download and exercise production retrieval models",
)


def cosine(left: list[float], right: list[float]) -> float:
    return float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right)))


def hit(identifier: str, text: str) -> SearchHit:
    return SearchHit(identifier, text, identifier, "en", "metadata", 0.5)


def test_real_multilingual_embeddings_and_cross_encoder_reranking() -> None:
    settings = Settings()
    assert settings.enable_ml_models is True

    encoder = MultilingualEncoder(settings.embedding_model, enable_model=True)
    query, relevant, unrelated = encoder.encode(
        [
            "भारत की राजधानी क्या है?",
            "नई दिल्ली भारत की राजधानी है।",
            "व्हेल समुद्र में रहने वाले विशाल स्तनधारी हैं।",
        ]
    )
    relevant_similarity = cosine(query, relevant)
    unrelated_similarity = cosine(query, unrelated)
    print(
        f"mpnet_dimension={encoder.dimension} "
        f"relevant_similarity={relevant_similarity:.6f} "
        f"unrelated_similarity={unrelated_similarity:.6f}"
    )
    assert encoder.model is not None
    assert encoder.degraded is False
    assert encoder.dimension == 768
    assert relevant_similarity > unrelated_similarity + 0.15

    reranker = CrossEncoderReranker(settings.reranker_model, enable_model=True)
    ranked = reranker.rerank(
        "What is the capital of India?",
        [
            hit("unrelated", "Whales are large mammals that live in the ocean."),
            hit("relevant", "New Delhi is the capital of India."),
        ],
        limit=2,
    )
    print(
        "reranker_scores="
        + ",".join(f"{item.id}:{item.score:.6f}" for item in ranked)
    )
    assert reranker.model is not None
    assert reranker.degraded is False
    assert ranked[0].id == "relevant"
    assert ranked[0].score > ranked[1].score
