"use client";

import gsap from "gsap";
import { ArrowLeft, ArrowUp, Command, Github } from "lucide-react";
import Link from "next/link";
import { FormEvent, useLayoutEffect, useRef, useState } from "react";
import { AnswerCard } from "@/components/AnswerCard";
import { GuardrailBanner } from "@/components/GuardrailBanner";
import { LanguageSelector } from "@/components/LanguageSelector";
import { LatencyDashboard } from "@/components/LatencyDashboard";
import { RetrievedChunks } from "@/components/RetrievedChunks";
import { SampleQueryButtons } from "@/components/SampleQueryButtons";
import { StatusBadge } from "@/components/StatusBadge";
import { TranscriptDisplay } from "@/components/TranscriptDisplay";
import { VoiceRecorder } from "@/components/VoiceRecorder";
import {
  blobToBase64,
  streamQuery,
  type EvidencePreview,
  type LanguageCode,
  type QueryMetadata,
} from "@/lib/api-client";

const STAGE_LABELS: Record<string, string> = {
  stt: "Transcribing your voice…",
  query_classify: "Checking the question is safe to search…",
  query_rewrite: "Reading conversation context…",
  retrieve: "Searching multilingual evidence…",
  rerank: "Ranking the best sources…",
  confidence_gate: "Checking retrieval confidence…",
  generate: "Writing a grounded answer…",
  groundedness_check: "Verifying the answer against evidence…",
  refuse: "Answer withheld — evidence wasn't strong enough…",
  tts: "Synthesizing voice response…",
  response: "Finishing up…",
};

// The backend emits a stage name once that stage has *finished*, so the
// status line should announce whatever runs next.
const NEXT_STAGE: Record<string, string> = {
  stt: "query_classify",
  query_classify: "query_rewrite",
  query_rewrite: "retrieve",
  retrieve: "rerank",
  rerank: "confidence_gate",
  confidence_gate: "generate",
  generate: "groundedness_check",
  groundedness_check: "tts",
  refuse: "response",
  tts: "response",
};

export default function VaaaniPage() {
  const shellRef = useRef<HTMLElement | null>(null);
  const [language, setLanguage] = useState<LanguageCode>("en-IN");
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [metadata, setMetadata] = useState<QueryMetadata>();
  const [evidence, setEvidence] = useState<EvidencePreview>();
  const [audioUrl, setAudioUrl] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [stageLabel, setStageLabel] = useState<string>();
  const [liveStages, setLiveStages] = useState<string[]>([]);
  const [expandedChunks, setExpandedChunks] = useState<number[]>([]);
  const [error, setError] = useState<string>();
  const [conversation, setConversation] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);

  useLayoutEffect(() => {
    document.documentElement.removeAttribute("data-theme");
    const shell = shellRef.current;
    if (!shell || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const context = gsap.context(() => {
      gsap.from(".console-nav", { duration: 0.65, ease: "power3.out", opacity: 0, y: -18 });
      gsap.from(".console-hero > *", { duration: 0.85, ease: "power3.out", opacity: 0, stagger: 0.08, y: 24 });
      gsap.from(".studio > *", { duration: 0.9, ease: "power3.out", opacity: 0, stagger: 0.08, y: 24 });
    }, shell);

    return () => context.revert();
  }, []);

  async function ask(payload: { query?: string; audio_base64?: string; audio_mime_type?: string }) {
    setLoading(true);
    setError(undefined);
    setAnswer("");
    setMetadata(undefined);
    setEvidence(undefined);
    setAudioUrl(undefined);
    setStageLabel(payload.audio_base64 ? STAGE_LABELS.stt : "Starting…");
    setLiveStages([]);
    setExpandedChunks([]);
    let streamedAnswer = "";
    let transcript = payload.query ?? "";
    try {
      await streamQuery(
        { ...payload, language, conversation },
        {
          onStage: (stage) => {
            setLiveStages((current) => [...current, stage]);
            const next = NEXT_STAGE[stage];
            setStageLabel(next ? STAGE_LABELS[next] : STAGE_LABELS[stage] ?? stage);
          },
          onEvidence: (value) => {
            transcript = value.transcript;
            setEvidence(value);
          },
          onMetadata: (value) => {
            transcript = value.transcript;
            setMetadata(value);
            setStageLabel(undefined);
          },
          onToken: (token) => {
            streamedAnswer += token;
            setAnswer((current) => current + token);
          },
          onAudio: (base64, mimeType) => setAudioUrl(`data:${mimeType};base64,${base64}`),
        },
      );
      const newTurns: Array<{ role: "user" | "assistant"; content: string }> = [];
      if (transcript.trim()) newTurns.push({ role: "user", content: transcript.trim() });
      if (streamedAnswer.trim()) newTurns.push({ role: "assistant", content: streamedAnswer.trim() });
      if (newTurns.length) {
        setConversation((current) => [...current, ...newTurns].slice(-12));
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The request could not be completed.");
    } finally {
      setLoading(false);
      setStageLabel(undefined);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!query.trim() || loading) return;
    const text = query.trim();
    setQuery("");
    await ask({ query: text });
  }

  async function useRecording(blob: Blob) {
    await ask({ audio_base64: await blobToBase64(blob), audio_mime_type: blob.type });
  }

  // The evidence preview arrives while the LLM is still working, so the
  // sources, transcript, and confidence can be read long before metadata.
  const citationsShown = metadata?.citations ?? evidence?.citations ?? [];
  const transcriptShown = metadata?.transcript ?? evidence?.transcript;
  const confidenceShown = metadata?.confidence ?? evidence?.confidence;

  return (
    <main ref={shellRef} className="vaaani-experience">
      <header className="console-nav">
        <Link href="/" className="back-link">
          <ArrowLeft size={16} /> Landing
        </Link>
        <a href="#compose" className="brand" aria-label="Vaaani console">
          <span className="brand-mark">वा</span>
          <span><strong>Vaaani</strong><small>वाणी · grounded voice console</small></span>
        </a>
        <div className="topbar-actions">
          <StatusBadge />
          <a
            href="https://github.com/Fareed95/vaaani"
            target="_blank"
            rel="noopener noreferrer"
            className="icon-button"
            aria-label="View source on GitHub"
          >
            <Github size={18} />
          </a>
        </div>
      </header>

      <section className="console-hero">
        <p className="eyebrow"><span>Console</span><i /></p>
        <h1>Ask. Verify.<br /><em>Then listen.</em></h1>
        <p>
          A calmer way to ask across Indian languages: speak naturally, see what
          supported the answer, and play audio only when the response is grounded.
        </p>
      </section>

      <section className="about-strip" aria-label="How Vaaani is built">
        <article>
          <span>Pipeline</span>
          <strong>Voice → STT → hybrid retrieval → rerank → grounded generation → TTS</strong>
        </article>
        <article>
          <span>Chunking</span>
          <strong>Fixed-size, semantic, and metadata-aware — compared, not just one strategy</strong>
        </article>
        <article>
          <span>Retrieval latency</span>
          <strong>P50 ~60ms, P70 ~73ms — under the 200ms target, measured on 50 real queries</strong>
        </article>
        <article>
          <span>Guardrails</span>
          <strong>Off-topic gate, confidence threshold, groundedness check — refuses rather than guesses</strong>
        </article>
      </section>

      <section className="studio" id="compose">
        <div className="side-stack">
          <div className="compose-card">
            <header className="card-heading">
              <div>
                <span>Question</span>
                <h2>Start with your voice.</h2>
              </div>
              <LanguageSelector value={language} onChange={setLanguage} />
            </header>

            <div className="ask-zone">
              <VoiceRecorder disabled={loading} onRecording={useRecording} />
              <div className="or-divider"><span>or type</span></div>
              <form className="query-form" onSubmit={submit}>
                <textarea
                  rows={2}
                  value={query}
                  disabled={loading}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      event.currentTarget.form?.requestSubmit();
                    }
                  }}
                  placeholder={language === "hi-IN" ? "अपना सवाल यहाँ लिखें…" : "Ask a question from the indexed evidence…"}
                  aria-label="Question"
                />
                <button type="submit" disabled={!query.trim() || loading} aria-label="Ask question">
                  {loading ? <i className="button-loader" /> : <ArrowUp size={21} />}
                </button>
                <kbd><Command size={11} /> ↵</kbd>
              </form>
              <SampleQueryButtons disabled={loading} onSelect={(sample) => { setQuery(""); void ask({ query: sample }); }} />
            </div>
          </div>

          <aside className="evidence-rail">
            <div className="rail-heading">
              <span>Evidence</span>
              <small>{citationsShown.length ? `${citationsShown.length} chunks retrieved` : loading ? "Searching the index…" : "Waiting for a question"}</small>
            </div>
            <RetrievedChunks
              chunks={citationsShown}
              running={loading}
              expanded={expandedChunks}
              onToggle={(rank, open) =>
                setExpandedChunks((current) =>
                  open ? Array.from(new Set([...current, rank])) : current.filter((value) => value !== rank),
                )
              }
            />
            <LatencyDashboard
              timings={evidence?.timings ?? metadata?.timings ?? []}
              pipelineDuration={evidence?.pipeline_duration_ms}
              liveStages={liveStages}
              running={loading}
            />
            {metadata?.degraded_services.length ? (
              <div className="degraded-note"><strong>Local fallbacks active</strong><span>{metadata.degraded_services.join(" · ").replaceAll("_", " ")}</span></div>
            ) : null}
            <div className="rail-footnote">
              <i />
              <p><strong>Grounded by design.</strong> Low-confidence or unsupported answers stop before speech synthesis.</p>
            </div>
          </aside>
        </div>

        <section className="response-card" aria-label="Vaaani response">
          <header className="card-heading">
            <div>
              <span>Answer</span>
              <h2>Grounded response.</h2>
            </div>
            <small>{confidenceShown === undefined ? "Ready" : `${Math.round(confidenceShown * 100)}% confidence`}</small>
          </header>
          {error && (
            <div className="request-error" role="alert">
              <strong>The answer service could not be reached.</strong>
              <span>{error} Check that the API is running at the configured URL, then try again.</span>
            </div>
          )}
          {transcriptShown && <TranscriptDisplay transcript={transcriptShown} />}
          {metadata && <GuardrailBanner refused={metadata.refused} reason={metadata.refusal_reason ?? undefined} guardrails={metadata.guardrails} />}
          {!answer && !loading && !error ? (
            <div className="answer-empty">
              <span>Nothing asked yet</span>
              <p>Your answer will appear here with citation controls and optional audio playback.</p>
            </div>
          ) : null}
          {loading && stageLabel && !answer ? (
            <div className="answer-empty" role="status" aria-live="polite">
              <span>Working on it</span>
              <p>{stageLabel}</p>
            </div>
          ) : null}
          <AnswerCard
            answer={answer}
            loading={loading}
            citations={citationsShown}
            audioUrl={audioUrl}
            onCitationSelect={(rank) => {
              setExpandedChunks((current) => Array.from(new Set([...current, rank])));
              document.getElementById(`chunk-${rank}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
            }}
          />
        </section>
      </section>

      <footer>
        <span>Vaaani</span>
        <span className="dev-credits">
          Developed by
          <a href="https://github.com/Fareed95" target="_blank" rel="noopener noreferrer">
            {/* eslint-disable-next-line @next/next/no-img-element -- GitHub-hosted avatar, not a local/optimizable asset */}
            <img src="https://github.com/Fareed95.png" alt="" width={18} height={18} /> Fareed95
          </a>
          <a href="https://github.com/arshhimself" target="_blank" rel="noopener noreferrer">
            {/* eslint-disable-next-line @next/next/no-img-element -- GitHub-hosted avatar, not a local/optimizable asset */}
            <img src="https://github.com/arshhimself.png" alt="" width={18} height={18} /> arshhimself
          </a>
        </span>
      </footer>
    </main>
  );
}
