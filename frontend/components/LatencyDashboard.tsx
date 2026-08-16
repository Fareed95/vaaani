import { Gauge } from "lucide-react";
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
  return (
    <aside className="latency-panel">
      <header><div><Gauge size={18} /><span>Request trace</span></div><strong>{total.toFixed(0)} ms</strong></header>
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
