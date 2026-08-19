import { Layers } from "lucide-react";
import type { Citation } from "@/lib/api-client";

/**
 * The reranked chunks, shown in the rail as soon as retrieval settles — well
 * before generation finishes — so there is something to read during the wait.
 * This is the only place chunks are listed; inline [n] markers in the answer
 * expand the matching entry here.
 */
export function RetrievedChunks({
  chunks,
  running,
  expanded = [],
  onToggle,
}: {
  chunks: Citation[];
  running: boolean;
  expanded?: number[];
  onToggle?: (rank: number, open: boolean) => void;
}) {
  if (!chunks.length) {
    return running ? (
      <section className="chunk-list is-waiting" aria-live="polite">
        <header><Layers size={16} /><span>Top chunks</span></header>
        <p>Searching the index…</p>
      </section>
    ) : null;
  }

  return (
    <section className="chunk-list" aria-label="Retrieved chunks">
      <header>
        <div><Layers size={16} /><span>Top chunks</span></div>
        <strong>{chunks.length} ranked</strong>
      </header>
      <ol>
        {chunks.map((chunk) => (
          <li key={`${chunk.passage_id}-${chunk.rank}`}>
            <details
              id={`chunk-${chunk.rank}`}
              open={expanded.includes(chunk.rank)}
              onToggle={(event) => onToggle?.(chunk.rank, event.currentTarget.open)}
            >
              <summary>
                <span className="chunk-rank">{chunk.rank}</span>
                <small>{chunk.language.toUpperCase()} · {chunk.chunk_strategy}</small>
                <b>{(chunk.score * 100).toFixed(0)}%</b>
              </summary>
              <p>{chunk.text}</p>
            </details>
          </li>
        ))}
      </ol>
    </section>
  );
}
