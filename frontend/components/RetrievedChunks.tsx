import { Layers } from "lucide-react";
import type { Citation } from "@/lib/api-client";

/**
 * The reranked chunks, shown in the rail as soon as retrieval settles — well
 * before generation finishes — so there is something to read during the wait.
 */
export function RetrievedChunks({ chunks, running }: { chunks: Citation[]; running: boolean }) {
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
            <div>
              <span className="chunk-rank">{chunk.rank}</span>
              <small>{chunk.language.toUpperCase()} · {chunk.chunk_strategy}</small>
              <b>{(chunk.score * 100).toFixed(0)}%</b>
            </div>
            <p>{chunk.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
