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

// Everything after the confidence gate waits on a provider round-trip, so it
// is reported as progress only. The 200ms target covers the stages above it,
// and that score is final the moment the evidence arrives.
const PIPELINE_STAGES = [
  "query_classify",
  "query_rewrite",
  "retrieve",
  "rerank",
  "confidence_gate",
  "refuse",
];
// Speech recognition is a provider round trip like generation and voice
// synthesis — reported as progress, never charged to the pipeline budget.
const AFTER_PIPELINE = ["stt", "generate", "groundedness_check", "tts", "response"] as const;
const PIPELINE_TARGET_MS = 200;

export function LatencyDashboard({
  timings,
  pipelineDuration,
  liveStages = [],
  running = false,
}: {
  timings: StageTiming[];
  pipelineDuration?: number;
  liveStages?: string[];
  running?: boolean;
}) {
  // `timings` may be the early evidence payload (pipeline stages only) or the
  // final metadata (every stage) if the backend predates the evidence event —
  // filter either way so the score means the same thing.
  const rows = timings.filter((timing) => PIPELINE_STAGES.includes(timing.stage));

  if (!rows.length) {
    return (
      <aside className="latency-panel empty-panel">
        <Gauge size={18} />
        <p>{running ? "Running the retrieval pipeline…" : "Stage timings will appear here after your first question."}</p>
      </aside>
    );
  }

  const max = Math.max(...rows.map((timing) => timing.duration_ms), 1);
  // Always sum the rows actually shown rather than trusting the server total.
  // A backend that still counts a provider stage (speech recognition, say) in
  // `pipeline_duration_ms` would otherwise print a headline number that the
  // stages below it don't add up to. Once the backend excludes the same stages
  // the two agree, and this stays correct either way. The server value is only
  // a fallback for a payload that carries a total but no per-stage timings.
  const total = rows.length
    ? rows.reduce((sum, timing) => sum + timing.duration_ms, 0)
    : (pipelineDuration ?? 0);
  const underTarget = total <= PIPELINE_TARGET_MS;

  return (
    <aside className="latency-panel">
      <header>
        <div><Gauge size={18} /><span>Pipeline trace</span></div>
        <strong>{total.toFixed(1)} ms</strong>
      </header>
      <div className={`retrieval-target ${underTarget ? "is-under" : "is-over"}`}>
        {underTarget ? <CheckCircle2 size={15} /> : <TriangleAlert size={15} />}
        <span>
          Full pipeline: <b>{total.toFixed(1)} ms</b> {underTarget ? "(under the 200ms target)" : "(over the 200ms target)"}
        </span>
      </div>
      <div className="timing-list">
        {rows.map((timing) => (
          <div className="timing-row" key={`${timing.stage}-${timing.started_at}`}>
            <div><span>{labels[timing.stage] ?? timing.stage}</span><b>{timing.duration_ms.toFixed(1)} ms</b></div>
            <div className="timing-track"><i style={{ width: `${Math.max(2, timing.duration_ms / max * 100)}%` }} data-status={timing.status} /></div>
          </div>
        ))}
      </div>
      <div className="deferred-list">
        {AFTER_PIPELINE.map((stage) => {
          const done = liveStages.includes(stage);
          const state = done ? "done" : running ? "running" : "skipped";
          return (
            <div className="deferred-row" key={stage} data-state={state}>
              <span>{labels[stage]}</span>
              {state === "running" ? (
                <em><i className="deferred-loader" />working</em>
              ) : (
                <em>{state === "done" ? "done" : "not run"}</em>
              )}
            </div>
          );
        })}
      </div>
      <p>Stages below the line wait on external providers, so they are reported as progress and left out of the pipeline budget.</p>
    </aside>
  );
}
