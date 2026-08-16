from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx
from datasets import load_dataset

from vaaani.chunking.base import Document

FILE_LANGUAGE_CODES = {
    "as": "asm",
    "bn": "ben",
    "gu": "guj",
    "hi": "hin",
    "kn": "kan",
    "ml": "mal",
    "mr": "mar",
    "ne": "nep",
    "or": "ori",
    "pa": "pan",
    "sa": "san",
    "ta": "tam",
    "te": "tel",
    "ur": "urd",
}


@dataclass(frozen=True, slots=True)
class DatasetRecord:
    query: str
    language: str
    answer: str
    documents: list[Document]


def record_from_row(row: dict[str, Any], language: str) -> DatasetRecord:
    query_id = str(row.get("query_id", "unknown"))
    passages = row.get("passages") or {}
    english = language == "en"
    texts = passages.get("English_passages" if english else "Translated_passages", []) or []
    selected = passages.get("is_selected", []) or []
    query = str(row.get("Eng_Query" if english else "query", ""))
    answer = str(row.get("Eng_Answer" if english else "Answer", ""))
    documents = [
        Document(
            text=str(text),
            passage_id=f"{language}:{query_id}:{position}",
            language=language,
            source_lang=str(row.get("source_lang") or "eng_Latn"),
            target_lang="eng_Latn" if english else str(row.get("target_lang") or language),
            query=query,
            metadata={
                "query_id": query_id,
                "query_type": str(row.get("query_type", "")),
                "is_selected": bool(selected[position]) if position < len(selected) else False,
            },
        )
        for position, text in enumerate(texts)
        if str(text).strip()
    ]
    return DatasetRecord(query=query, language=language, answer=answer, documents=documents)


def load_records(
    dataset_name: str,
    languages: list[str],
    split: str = "train",
    limit: int = 1000,
) -> Iterator[DatasetRecord]:
    """Stream balanced language subsets; English is read from the parallel Hindi records."""
    per_language = max(1, limit // max(1, len(languages)))
    for language in languages:
        config = "hi" if language == "en" else language
        file_code = FILE_LANGUAGE_CODES.get(config, config)
        suffix = "train" if split == "train" else "val"
        filename = f"{file_code}{suffix}.parquet"
        data_file = f"hf://datasets/{dataset_name}/{split}/{filename}"
        dataset = load_dataset(
            "parquet",
            data_files={split: data_file},
            split=split,
            streaming=True,
        )
        emitted = 0
        for row in dataset:
            record = record_from_row(dict(row), language)
            if record.query and record.documents:
                yield record
                emitted += 1
            if emitted >= per_language:
                break


async def load_preview_records(dataset_name: str, count: int) -> list[DatasetRecord]:
    """Fetch small public preview samples without downloading full Parquet shards."""
    url = "https://datasets-server.huggingface.co/first-rows"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(
            url,
            params={"dataset": dataset_name, "config": "default", "split": "validation"},
        )
        response.raise_for_status()
    language_codes = {value: key for key, value in FILE_LANGUAGE_CODES.items()}
    records = []
    for item in response.json().get("rows", [])[:count]:
        row = item.get("row", {})
        target = str(row.get("target_lang", "as")).split("_")[0]
        language = language_codes.get(target, target[:2])
        records.append(record_from_row(row, language))
    return [record for record in records if record.query and record.documents]
