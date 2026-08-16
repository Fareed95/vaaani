"use client";

import { Database, Radio } from "lucide-react";
import { useEffect, useState } from "react";
import { getHealth, type HealthStatus } from "@/lib/api-client";

export function StatusBadge() {
  const [health, setHealth] = useState<HealthStatus>();
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setOffline(true));
  }, []);

  if (offline) {
    return <div className="status-badge is-offline"><Radio size={14} /><span>API offline</span></div>;
  }
  if (!health) {
    return <div className="status-badge is-loading"><i /><span>Checking the index…</span></div>;
  }
  return (
    <div className="status-badge" title={`${health.retrieval_mode} · STT: ${health.stt_provider}`}>
      <Database size={14} />
      <span>{health.vector_db}: {health.indexed_chunks.toLocaleString()} chunks</span>
      <i className={health.status === "healthy" ? "healthy" : "degraded"} />
    </div>
  );
}
