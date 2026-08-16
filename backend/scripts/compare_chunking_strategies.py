import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from vaaani.chunking.fixed_size import FixedSizeChunker
from vaaani.chunking.metadata_aware import MetadataAwareChunker
from vaaani.chunking.semantic import SemanticChunker
from vaaani.config import get_settings
from vaaani.embeddings.multilingual_encoder import MultilingualEncoder
from vaaani.ingestion.index_builder import IndexBuilder
from vaaani.ingestion.load_msmarco_xi import load_preview_records, load_records
from vaaani.retrieval.dense import DenseRetriever
from vaaani.vectorstore.qdrant_client import QdrantVectorStore

ROOT = Path(__file__).resolve().parents[2]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Vaaani chunking strategies")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Use public dataset-server preview rows for a quick comparison",
    )
    args = parser.parse_args()
    settings = get_settings()
    records = (
        await load_preview_records(settings.dataset_name, args.count)
        if args.preview
        else list(load_records(settings.dataset_name, settings.languages, "validation", args.count))
    )
    encoder = MultilingualEncoder(settings.embedding_model, settings.enable_ml_models)
    chunkers = {
        "fixed": FixedSizeChunker(settings.chunk_size, settings.chunk_overlap),
        "semantic": SemanticChunker(embed=encoder.encode),
        "metadata": MetadataAwareChunker(),
    }
    results = {}
    for name, chunker in chunkers.items():
        store = QdrantVectorStore(":memory:", f"comparison_{name}")
        stats = await IndexBuilder(store, encoder, chunker).build(records)
        retriever = DenseRetriever(store, encoder)
        latencies = []
        relevant = 0
        for record in records:
            started = perf_counter()
            hits = await retriever.search(record.query, language=record.language, limit=5)
            latencies.append((perf_counter() - started) * 1000)
            if any(bool(hit.metadata.get("is_selected")) for hit in hits):
                relevant += 1
        ordered = sorted(latencies)
        results[name] = {
            "chunks": stats.chunks,
            "precision_at_5_proxy": round(relevant / max(1, len(records)), 4),
            "latency_p50_ms": round(ordered[len(ordered) // 2], 3),
            "latency_p100_ms": round(max(ordered, default=0), 3),
        }
    output = (
        ROOT
        / "benchmarks"
        / "results"
        / (f"chunking-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    asyncio.run(main())
