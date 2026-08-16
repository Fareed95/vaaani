import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GuardrailBanner } from "@/components/GuardrailBanner";
import { AnswerCard } from "@/components/AnswerCard";
import { LanguageSelector } from "@/components/LanguageSelector";
import { LatencyDashboard } from "@/components/LatencyDashboard";
import { SampleQueryButtons } from "@/components/SampleQueryButtons";

describe("Vaaani interface", () => {
  it("exposes multilingual choices", () => {
    const onChange = vi.fn();
    render(<LanguageSelector value="en-IN" onChange={onChange} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "hi-IN" } });
    expect(onChange).toHaveBeenCalledWith("hi-IN");
    expect(screen.getByText(/বাংলা/)).toBeInTheDocument();
  });

  it("fills a sample query without submitting implicitly", () => {
    const onSelect = vi.fn();
    render(<SampleQueryButtons onSelect={onSelect} />);
    fireEvent.click(screen.getByText(/monsoon rainfall/i));
    expect(onSelect).toHaveBeenCalledOnce();
  });

  it("shows a specific confidence refusal", () => {
    render(
      <GuardrailBanner
        refused
        reason="retrieval_confidence_low"
        guardrails={[{
          guardrail: "confidence_threshold",
          passed: false,
          reason: "retrieval_confidence_low",
          details: { confidence_score: 0.31, threshold: 0.55 },
        }]}
      />,
    );
    expect(screen.getByText(/retrieval confidence low/)).toBeInTheDocument();
    expect(screen.getByText(/Confidence 31% · required 55%/)).toBeInTheDocument();
  });

  it("labels generation separately from retrieval", () => {
    render(
      <LatencyDashboard
        total={130}
        timings={[
          { stage: "retrieve", started_at: "a", ended_at: "b", duration_ms: 20, status: "ok" },
          { stage: "generate", started_at: "b", ended_at: "c", duration_ms: 110, status: "ok" },
        ]}
      />,
    );
    expect(screen.getByText("Hybrid retrieval")).toBeInTheDocument();
    expect(screen.getByText("Generation")).toBeInTheDocument();
  });

  it("opens cited evidence from an inline reference", () => {
    render(
      <AnswerCard
        answer="Mumbai is on the Arabian Sea. [1]"
        loading={false}
        citations={[{
          rank: 1,
          passage_id: "p1",
          text: "Mumbai overlooks the Arabian Sea.",
          score: 0.9,
          language: "en",
          chunk_strategy: "metadata",
        }]}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Toggle source 1" }));
    expect(document.querySelector("#source-1")).toHaveAttribute("open");
  });
});
