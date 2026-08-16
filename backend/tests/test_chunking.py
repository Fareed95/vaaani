from vaaani.chunking import Document, FixedSizeChunker, MetadataAwareChunker, SemanticChunker


def document(text: str) -> Document:
    return Document(
        text=text,
        passage_id="p-1",
        language="hi",
        source_lang="eng_Latn",
        target_lang="hin_Deva",
        query="सवाल",
    )


def test_fixed_size_overlap_and_metadata() -> None:
    chunks = FixedSizeChunker(size=5, overlap=0.2).chunk(
        document("one two three four five six seven eight nine")
    )
    assert len(chunks) == 2
    assert chunks[0].text.split()[-1] == chunks[1].text.split()[0]
    assert chunks[0].language == "hi"
    assert chunks[0].strategy == "fixed"


def test_semantic_breaks_unrelated_sentences() -> None:
    chunks = SemanticChunker(threshold=0.2).chunk(
        document("Cats drink milk. Cats like warm milk. Rockets travel through space.")
    )
    assert len(chunks) == 2
    assert "Rockets" in chunks[-1].text


def test_metadata_chunk_preserves_native_boundary() -> None:
    chunks = MetadataAwareChunker().chunk(document("एक पूरा अनुच्छेद।"))
    assert len(chunks) == 1
    assert chunks[0].payload()["target_lang"] == "hin_Deva"
    assert chunks[0].payload()["native_query"] == "सवाल"
