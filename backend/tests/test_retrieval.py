from vaaani.retrieval.dense import SearchHit
from vaaani.retrieval.fusion import reciprocal_rank_fusion
from vaaani.retrieval.sparse_bm25 import SparseBM25Retriever


def hit(identifier: str, text: str, score: float = 0) -> SearchHit:
    return SearchHit(identifier, text, identifier, "en", "metadata", score)


def test_bm25_prioritizes_lexical_match() -> None:
    corpus = [hit("1", "the moon orbits earth"), hit("2", "mango trees grow in summer")]
    ranked = SparseBM25Retriever().rank("which body orbits earth", corpus)
    assert ranked[0].id == "1"
    assert ranked[0].score > 0


def test_rrf_rewards_items_seen_by_both_rankers() -> None:
    a, b, c = hit("a", "A"), hit("b", "B"), hit("c", "C")
    fused = reciprocal_rank_fusion([[a, b], [c, a]])
    assert fused[0].id == "a"
    assert fused[0].score == 1
