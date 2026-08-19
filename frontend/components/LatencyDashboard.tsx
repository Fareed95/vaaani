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

// The 200ms target covers the whole pipeline — safety gate, context rewrite,
// vector DB search, reranking, confidence, groundedness. Generation (LLM) and
// voice synthesis are real cloud API calls measured separately, since no
// provider completes those in 200ms regardless of pipeline design.
const PIPELINE_TARGET_MS = 200;

// Provider round-trips. Never timed in the trace — progress only.
const DEFERRED_STAGES = ["generate", "tts"] as const;

export function LatencyDashboard({
  timings,
  liveStages = [],
  running = false,
}: {
  timings: StageTiming[];
  total?: number;
  liveStages?: string[];
  running?: boolean;
}) {
  // Only the server knows how long a stage actually took. Client-side gaps
  // between stage events measure network and queueing too, so while the
  // request is in flight the trace shows which stages have finished and no
  // numbers at all — a wrong number that later corrects itself is worse than
  // no number.
  const settled = timings.length > 0;
  const rows: Array<{ stage: string; duration_ms: number | null; status: string; key: string }> = settled
    ? timings.map((timing) => ({
        stage: timing.stage,
        duration_ms: timing.duration_ms,
        status: timing.status,
        key: `${timing.stage}-${timing.started_at}`,
      }))
    : liveStages.map((stage, index) => ({
        stage,
        duration_ms: null,
        status: "ok",
        key: `${stage}-${index}`,
      }));

  const pipelineRows = rows.filter((row) => !isDeferred(row.stage));

  if (!pipelineRows.length) {
    return (
      <aside className="latency-panel empty-panel">
        <Gauge size={18} />
        <p>{running ? "Running the retrieval pipeline…" : "Stage timings will appear here after your first question."}</p>
      </aside>
    );
  }

  const max = Math.max(...pipelineRows.map((row) => row.duration_ms ?? 0), 1);
  const pipelineMs = settled
    ? pipelineRows.reduce((sum, row) => sum + (row.duration_ms ?? 0), 0)
    : null;
  const underTarget = (pipelineMs ?? 0) <= PIPELINE_TARGET_MS;

  return (
    <aside className="latency-panel" data-live={!settled}>
      <header>
        <div><Gauge size={18} /><span>Pipeline trace</span></div>
        <strong>{pipelineMs === null ? "measuring…" : `${pipelineMs.toFixed(1)} ms`}</strong>
      </header>
      {pipelineMs === null ? null : (
        <div className={`retrieval-target ${underTarget ? "is-under" : "is-over"}`}>
          {underTarget ? <CheckCircle2 size={15} /> : <TriangleAlert size={15} />}
          <span>
            Full pipeline: <b>{pipelineMs.toFixed(1)} ms</b> {underTarget ? "— under the 200ms target" : "— over the 200ms target"}
          </span>
        </div>
      )}
      <div className="timing-list">
        {pipelineRows.map((row) => (
          <div className="timing-row" key={row.key}>
            <div>
              <span>{labels[row.stage] ?? row.stage}</span>
              {row.duration_ms === null ? <em className="stage-done">done</em> : <b>{row.duration_ms.toFixed(1)} ms</b>}
            </div>
            <div className="timing-track">
              <i
                style={{ width: row.duration_ms === null ? "100%" : `${Math.max(2, row.duration_ms / max * 100)}%` }}
                data-status={row.status}
              />
            </div>
          </div>
        ))}
      </div>
      <div className="deferred-list">
        {DEFERRED_STAGES.map((stage) => {
          const done = rows.some((row) => row.stage === stage);
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
      <p>
        Generation and voice synthesis are provider round-trips and sit outside the pipeline budget, so they are not timed here.
        {settled ? null : " Stage times arrive with the server trace once the request completes."}
      </p>
    </aside>
  );
}

function isDeferred(stage: string): boolean {
  return (DEFERRED_STAGES as readonly string[]).includes(stage);
}
