import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx

from vaaani.api.schemas import QueryRequest
from vaaani.chunking.metadata_aware import MetadataAwareChunker
from vaaani.config import get_settings
from vaaani.ingestion.index_builder import IndexBuilder
from vaaani.ingestion.load_msmarco_xi import (
    load_preview_records,
    load_records,
)
from vaaani.services import ServiceContainer
from vaaani.telemetry.latency_tracker import percentile_report

ROOT = Path(__file__).resolve().parents[2]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark a running Vaaani API")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--url", default=os.getenv("VAAANI_BENCHMARK_URL", "http://localhost:8000"))
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="Run a credential-free local smoke benchmark instead of calling an API URL",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Use public dataset-server preview rows instead of downloading language shards",
    )
    return parser.parse_args()


async def main() -> None:
    args = arguments()
    settings = get_settings()
    records = (
        await load_preview_records(settings.dataset_name, args.count)
        if args.preview
        else list(
            load_records(
                settings.dataset_name,
                settings.languages,
                split="validation",
                limit=args.count,
            )
        )
    )
    timings = []
    failures = []
    if args.in_process:
        local_settings = settings.model_copy(
            update={
                "qdrant_url": ":memory:",
                "enable_ml_models": False,
                "sarvam_api_key": None,
                "llm_api_key": None,
            }
        )
        services = ServiceContainer.build(local_settings)
        await IndexBuilder(services.store, services.encoder, MetadataAwareChunker()).build(records)
        for record in records:
            try:
                response = await services.query(
                    QueryRequest(query=record.query, language=f"{record.language}-IN")
                )
                timings.append([timing.model_dump(mode="json") for timing in response.timings])
            except Exception as exc:
                failures.append(str(exc))
    else:
        async with httpx.AsyncClient(timeout=120) as client:
            for record in records:
                try:
                    response = await client.post(
                        f"{args.url.rstrip('/')}/query",
                        json={"query": record.query, "language": f"{record.language}-IN"},
                    )
                    response.raise_for_status()
                    timings.append(response.json()["timings"])
                except Exception as exc:
                    failures.append(str(exc))
    if not timings:
        raise SystemExit(f"No successful requests. Is Vaaani running at {args.url}? {failures[:1]}")
    percentiles = percentile_report(timings)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = ROOT / "benchmarks" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": stamp,
        "api_url": "in-process local smoke" if args.in_process else args.url,
        "requested_queries": args.count,
        "successful_queries": len(timings),
        "failed_queries": len(failures),
        "languages": sorted({record.language for record in records}),
        "percentiles": percentiles,
        "note": "Retrieval and generation are reported as separate pipeline stages.",
    }
    (output_dir / f"{stamp}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Latency Benchmarks",
        "",
        f"Generated `{stamp}` from {len(timings)} successful dataset queries "
        f"using {'an in-process local smoke run' if args.in_process else args.url}.",
        "",
        "| Stage | P50 | P70 | P100 |",
        "|---|---:|---:|---:|",
    ]
    lines.extend(
        "| {} | {:.1f} ms | {:.1f} ms | {:.1f} ms |".format(
            stage,
            values["p50_ms"],
            values["p70_ms"],
            values["p100_ms"],
        )
        for stage, values in percentiles.items()
    )
    lines.extend(
        [
            "",
            "Generation latency is intentionally separate from retrieval latency; "
            "the under-200 ms target applies only to retrieval in a same-region deployment.",
        ]
    )
    if args.in_process:
        lines.extend(
            [
                "",
                "This smoke run used feature-hash embeddings, extractive generation, "
                "lexical groundedness, in-memory Qdrant, and an unavailable TTS adapter. "
                "It validates instrumentation and is not a cloud latency claim.",
            ]
        )
    markdown = "\n".join(lines) + "\n"
    (output_dir / f"{stamp}.md").write_text(markdown, encoding="utf-8")
    (ROOT / "docs" / "latency-benchmarks.md").write_text(markdown, encoding="utf-8")
    print(output_dir / f"{stamp}.json")


if __name__ == "__main__":
    asyncio.run(main())
