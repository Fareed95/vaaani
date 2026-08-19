import { CheckCircle2, Gauge, TriangleAlert } from "lucide-react";
import type { StageTiming } from "@/lib/api-client";

const labels: Record<string, string> = {
  stt: "Speech recognition",
  query_classify: "Safety gate",
  query_rewrite: "Context rewrite",
  retrieve: "Hybrid retrieval",
  rerank: "Reranking",
  confidence_gate: "Confidence",
  generate: "Generation",
  groundedness_check: "Evidence check",
  tts: "Voice synthesis",
  refuse: "Refusal",
  response: "Response",
};

// The 200ms target applies to the retrieval pipeline specifically —
// chunking happens at index-build time, so per-query cost is the safety
// gate, context rewrite, vector DB search, and reranking. Generation (LLM)
// and voice synthesis are real cloud API calls measured separately, since
// no provider completes those in 200ms regardless of pipeline design.
const RETRIEVAL_STAGES = ["query_classify", "query_rewrite", "retrieve", "rerank", "confidence_gate"];
const RETRIEVAL_TARGET_MS = 200;

export function LatencyDashboard({ timings, total }: { timings: StageTiming[]; total: number }) {
  if (!timings.length) {
    return (
      <aside className="latency-panel empty-panel">
        <Gauge size={18} />
        <p>Stage timings will appear here after your first question.</p>
      </aside>
    );
  }
  const max = Math.max(...timings.map((timing) => timing.duration_ms), 1);
  const retrievalMs = timings
    .filter((timing) => RETRIEVAL_STAGES.includes(timing.stage))
    .reduce((sum, timing) => sum + timing.duration_ms, 0);
  const underTarget = retrievalMs <= RETRIEVAL_TARGET_MS;
  return (
    <aside className="latency-panel">
      <header><div><Gauge size={18} /><span>Request trace</span></div><strong>{total.toFixed(0)} ms</strong></header>
      <div className={`retrieval-target ${underTarget ? "is-under" : "is-over"}`}>
        {underTarget ? <CheckCircle2 size={15} /> : <TriangleAlert size={15} />}
        <span>
          Retrieval pipeline: <b>{retrievalMs.toFixed(1)} ms</b> {underTarget ? "— under the 200ms target" : "— over the 200ms target"}
        </span>
      </div>
      <div className="timing-list">
        {timings.map((timing) => (
          <div className="timing-row" key={`${timing.stage}-${timing.started_at}`}>
            <div><span>{labels[timing.stage] ?? timing.stage}</span><b>{timing.duration_ms.toFixed(1)} ms</b></div>
            <div className="timing-track"><i style={{ width: `${Math.max(2, timing.duration_ms / max * 100)}%` }} data-status={timing.status} /></div>
          </div>
        ))}
      </div>
      <p>Retrieval and generation are measured separately.</p>
    </aside>
  );
}
