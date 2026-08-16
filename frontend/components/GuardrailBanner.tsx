import { ShieldAlert, ShieldCheck } from "lucide-react";
import type { GuardrailDecision } from "@/lib/api-client";

export function GuardrailBanner({ refused, reason, guardrails }: { refused: boolean; reason?: string; guardrails: GuardrailDecision[] }) {
  if (!guardrails.length) return null;
  const failed = guardrails.find((guardrail) => !guardrail.passed);
  if (!refused && !failed) {
    return (
      <div className="guardrail-banner passed"><ShieldCheck size={18} /><span>Answer passed topic, confidence, and evidence checks.</span></div>
    );
  }
  const details = failed?.details ?? {};
  return (
    <div className="guardrail-banner refused" role="alert">
      <ShieldAlert size={19} />
      <div>
        <strong>Answer withheld: {reason?.replaceAll("_", " ")}</strong>
        {typeof details.confidence_score === "number" && (
          <span>Confidence {(details.confidence_score * 100).toFixed(0)}% · required {(Number(details.threshold) * 100).toFixed(0)}%</span>
        )}
      </div>
    </div>
  );
}
