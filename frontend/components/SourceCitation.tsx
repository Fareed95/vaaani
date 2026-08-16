import { ChevronDown, FileText } from "lucide-react";
import type { Citation } from "@/lib/api-client";

export function SourceCitation({
  citation,
  expanded,
  onToggle,
}: {
  citation: Citation;
  expanded?: boolean;
  onToggle?: (expanded: boolean) => void;
}) {
  return (
    <details
      className="source-citation"
      id={`source-${citation.rank}`}
      open={expanded}
      onToggle={(event) => onToggle?.(event.currentTarget.open)}
    >
      <summary>
        <span className="source-rank">{citation.rank}</span>
        <span>
          <strong>Passage {citation.passage_id}</strong>
          <small>{citation.language.toUpperCase()} · {citation.chunk_strategy} · {(citation.score * 100).toFixed(0)}% match</small>
        </span>
        <ChevronDown size={16} className="chevron" />
      </summary>
      <div className="source-text">
        <FileText size={15} />
        <p>{citation.text}</p>
      </div>
    </details>
  );
}
