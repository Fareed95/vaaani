# Chunking strategies

All strategies produce the same `Chunk` contract and Qdrant payload fields, so a strategy can be selected with `VAAANI_CHUNK_STRATEGY` or `--strategy` without changing retrieval code.

| Strategy | Boundary | Strength | Trade-off |
|---|---|---|---|
| Fixed | 256 whitespace tokens, 20% overlap | Predictable index size and recall | Can cut through semantic boundaries |
| Semantic | Sentence cosine similarity breakpoint | Keeps related sentences together | Embedding pass increases ingestion time |
| Metadata-aware | Native MSMARCO-XI query/passage/language record | Preserves relevance labels and translation provenance | Long passages remain a single unit |

Metadata-aware is the default because MSMARCO-XI already supplies meaningful query-passage boundaries and selection labels. Its payload stores `language`, `passage_id`, `source_lang`, `target_lang`, `chunk_strategy`, `query_id`, `query_type`, and `is_selected`.

Run a controlled comparison:

```bash
uv run --project backend python backend/scripts/compare_chunking_strategies.py --count 30
```

The JSON report in `benchmarks/results/` includes chunk count, dense retrieval latency, and precision@5 proxy: the proportion of queries for which a native `is_selected` passage appears in the first five results. This is a retrieval proxy, not answer accuracy.

## Measured smoke comparison

The committed `chunking-20260816T194439Z.json` report used five real public MSMARCO-XI preview records, local feature-hash embeddings, and in-memory Qdrant. It verifies the comparison path; a larger ML-model run should drive the strategy choice for deployment.

| Strategy | Chunks | Precision@5 proxy | P50 | P100 |
|---|---:|---:|---:|---:|
| Fixed | 50 | 0.40 | 1.70 ms | 4.86 ms |
| Semantic | 104 | 0.60 | 2.47 ms | 2.72 ms |
| Metadata-aware | 50 | 0.40 | 1.93 ms | 2.20 ms |
