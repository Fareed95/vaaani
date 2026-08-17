"use client";

import { CheckCircle2, Radio } from "lucide-react";
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
    return <div className="status-badge is-loading"><i /><span>Preparing evidence…</span></div>;
  }
  return (
    <div className="status-badge" title={`Voice provider: ${health.stt_provider}`}>
      <CheckCircle2 size={14} />
      <span>{health.status === "healthy" ? "Evidence ready" : "Evidence limited"}</span>
      <i className={health.status === "healthy" ? "healthy" : "degraded"} />
    </div>
  );
}
