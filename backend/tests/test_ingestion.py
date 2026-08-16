from vaaani.ingestion import load_msmarco_xi


def sample_row() -> dict:
    return {
        "source_lang": "eng_Latn",
        "target_lang": "hin_Deva",
        "query": "भारत का प्रवेश द्वार कहाँ है?",
        "Answer": "मुंबई",
        "query_id": 42,
        "query_type": "LOCATION",
        "passages": {
            "is_selected": [1, 0],
            "English_passages": ["The Gateway is in Mumbai.", "Another passage."],
            "Translated_passages": ["गेटवे मुंबई में है।", "एक अन्य अनुच्छेद।"],
        },
        "Eng_Query": "Where is the Gateway?",
        "Eng_Answer": "Mumbai",
    }


def test_record_preserves_translation_and_relevance_metadata() -> None:
    record = load_msmarco_xi.record_from_row(sample_row(), "hi")
    assert record.documents[0].metadata["is_selected"] is True
    assert record.documents[0].passage_id == "hi:42:0"
    assert record.documents[0].source_lang == "eng_Latn"
    assert record.documents[0].target_lang == "hin_Deva"


def test_loader_uses_current_parquet_language_filename(monkeypatch) -> None:
    captured = {}

    def fake_load_dataset(kind, **kwargs):  # type: ignore[no-untyped-def]
        captured["kind"] = kind
        captured.update(kwargs)
        return [sample_row()]

    monkeypatch.setattr(load_msmarco_xi, "load_dataset", fake_load_dataset)
    records = list(load_msmarco_xi.load_records("ai4bharat/MSMARCO-XI", ["hi"], limit=1))
    assert len(records) == 1
    assert captured["kind"] == "parquet"
    assert captured["data_files"]["train"].endswith("/train/hintrain.parquet")
