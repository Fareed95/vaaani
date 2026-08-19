import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GuardrailBanner } from "@/components/GuardrailBanner";
import { AnswerCard } from "@/components/AnswerCard";
import { LanguageSelector } from "@/components/LanguageSelector";
import { LatencyDashboard } from "@/components/LatencyDashboard";
import { RetrievedChunks } from "@/components/RetrievedChunks";
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
    fireEvent.click(screen.getByText(/corporation/i));
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

  it("scores the pipeline as soon as evidence lands, with the rest as progress", () => {
    const { container } = render(
      <LatencyDashboard
        pipelineDuration={20}
        running
        liveStages={["retrieve", "confidence_gate"]}
        timings={[
          { stage: "retrieve", started_at: "a", ended_at: "b", duration_ms: 20, status: "ok" },
        ]}
      />,
    );
    const panel = within(container);
    expect(panel.getByText("Hybrid retrieval")).toBeInTheDocument();
    expect(panel.getAllByText("20.0 ms").length).toBeGreaterThan(0);
    expect(panel.getByText(/under the 200ms target/)).toBeInTheDocument();
    // Generation, evidence check, voice synthesis, response — progress only.
    expect(panel.getAllByText("working")).toHaveLength(4);
    expect(panel.getByText("Generation")).toBeInTheDocument();
  });

  it("waits for the server trace instead of guessing a number", () => {
    const { container } = render(<LatencyDashboard timings={[]} running liveStages={["retrieve"]} />);
    const panel = within(container);
    expect(panel.getByText(/Running the retrieval pipeline/)).toBeInTheDocument();
    expect(panel.queryByText(/ms/)).not.toBeInTheDocument();
  });

  it("routes an inline reference to the chunk in the rail", () => {
    const onCitationSelect = vi.fn();
    render(
      <AnswerCard
        answer="Mumbai is on the Arabian Sea. [1]"
        loading={false}
        onCitationSelect={onCitationSelect}
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
    // The answer card no longer lists sources — the rail is the only listing.
    expect(screen.queryByText(/Evidence used/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Toggle source 1" }));
    expect(onCitationSelect).toHaveBeenCalledWith(1);
  });

  it("shows retrieved chunks while the answer is still generating", () => {
    const { container } = render(
      <RetrievedChunks
        running
        chunks={[{
          rank: 1,
          passage_id: "p1",
          text: "A corporation is a company authorized to act as a single entity.",
          score: 0.87,
          language: "en",
          chunk_strategy: "metadata",
        }]}
      />,
    );
    const panel = within(container);
    expect(panel.getByText(/single entity/)).toBeInTheDocument();
    expect(panel.getByText("87%")).toBeInTheDocument();
    expect(panel.getByText("1 ranked")).toBeInTheDocument();
  });
});
