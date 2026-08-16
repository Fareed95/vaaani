import argparse
import asyncio

from vaaani.chunking.fixed_size import FixedSizeChunker
from vaaani.chunking.metadata_aware import MetadataAwareChunker
from vaaani.chunking.semantic import SemanticChunker
from vaaani.config import get_settings
from vaaani.embeddings.multilingual_encoder import MultilingualEncoder
from vaaani.ingestion.index_builder import IndexBuilder
from vaaani.ingestion.load_msmarco_xi import load_records
from vaaani.vectorstore.qdrant_client import QdrantVectorStore


def arguments() -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Build the Vaaani Qdrant index")
    parser.add_argument(
        "--strategy", choices=["fixed", "semantic", "metadata"], default=settings.chunk_strategy
    )
    parser.add_argument("--limit", type=int, default=settings.dataset_limit)
    parser.add_argument("--languages", default=",".join(settings.languages))
    return parser.parse_args()


async def main() -> None:
    args = arguments()
    settings = get_settings()
    encoder = MultilingualEncoder(settings.embedding_model, settings.enable_ml_models)
    chunkers = {
        "fixed": FixedSizeChunker(settings.chunk_size, settings.chunk_overlap),
        "semantic": SemanticChunker(embed=encoder.encode),
        "metadata": MetadataAwareChunker(),
    }
    store = QdrantVectorStore(
        settings.qdrant_url, settings.qdrant_collection, settings.qdrant_api_key
    )
    records = load_records(
        settings.dataset_name,
        args.languages.split(","),
        settings.dataset_split,
        args.limit,
    )
    stats = await IndexBuilder(store, encoder, chunkers[args.strategy]).build(records)
    print(
        f"Indexed {stats.chunks} chunks from {stats.documents} passages / "
        f"{stats.records} records using {args.strategy}."
    )


if __name__ == "__main__":
    asyncio.run(main())
