"use client";

import { ArrowUp, Command, Moon, Sun } from "lucide-react";
import { FormEvent, useState } from "react";
import { AnswerCard } from "@/components/AnswerCard";
import { GuardrailBanner } from "@/components/GuardrailBanner";
import { LanguageSelector } from "@/components/LanguageSelector";
import { LatencyDashboard } from "@/components/LatencyDashboard";
import { SampleQueryButtons } from "@/components/SampleQueryButtons";
import { StatusBadge } from "@/components/StatusBadge";
import { TranscriptDisplay } from "@/components/TranscriptDisplay";
import { VoiceRecorder } from "@/components/VoiceRecorder";
import {
  blobToBase64,
  streamQuery,
  type LanguageCode,
  type QueryMetadata,
} from "@/lib/api-client";

export default function Home() {
  const [language, setLanguage] = useState<LanguageCode>("en-IN");
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [metadata, setMetadata] = useState<QueryMetadata>();
  const [audioUrl, setAudioUrl] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [dark, setDark] = useState(false);
  const [conversation, setConversation] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);

  function toggleTheme() {
    setDark((current) => {
      document.documentElement.dataset.theme = current ? "light" : "dark";
      return !current;
    });
  }

  async function ask(payload: { query?: string; audio_base64?: string; audio_mime_type?: string }) {
    setLoading(true);
    setError(undefined);
    setAnswer("");
    setMetadata(undefined);
    setAudioUrl(undefined);
    let streamedAnswer = "";
    let transcript = payload.query ?? "";
    try {
      await streamQuery(
        { ...payload, language, conversation },
        {
          onMetadata: (value) => {
            transcript = value.transcript;
            setMetadata(value);
          },
          onToken: (token) => {
            streamedAnswer += token;
            setAnswer((current) => current + token);
          },
          onAudio: (base64, mimeType) => setAudioUrl(`data:${mimeType};base64,${base64}`),
        },
      );
      setConversation((current) => [
        ...current,
        { role: "user", content: transcript },
        { role: "assistant", content: streamedAnswer.trim() },
      ].slice(-12) as Array<{ role: "user" | "assistant"; content: string }>);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The request could not be completed.");
    } finally {
      setLoading(false);
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

  return (
    <main className="app-shell">
      <header className="topbar">
        <a href="#main-workspace" className="brand" aria-label="Vaaani home">
          <span className="brand-mark">वा</span>
          <span><strong>Vaaani</strong><small>वाणी · evidence in every language</small></span>
        </a>
        <div className="topbar-actions">
          <StatusBadge />
          <button type="button" className="icon-button" onClick={toggleTheme} aria-label={dark ? "Use light theme" : "Use dark theme"}>
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </header>

      <section className="intro">
        <p className="eyebrow"><span>Voice-first research</span><i /></p>
        <h1>Ask naturally.<br /><em>Trace every answer.</em></h1>
        <p>Speak in the language you think in. Vaaani searches across multilingual evidence, checks what it finds, and answers with the source still attached.</p>
      </section>

      <div className="workspace" id="main-workspace">
        <section className="conversation-panel">
          <div className="ask-zone">
            <LanguageSelector value={language} onChange={setLanguage} />
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

          {error && (
            <div className="request-error" role="alert">
              <strong>The answer service could not be reached.</strong>
              <span>{error} Check that the API is running at the configured URL, then try again.</span>
            </div>
          )}
          {metadata && <TranscriptDisplay transcript={metadata.transcript} />}
          {metadata && <GuardrailBanner refused={metadata.refused} reason={metadata.refusal_reason} guardrails={metadata.guardrails} />}
          <AnswerCard answer={answer} loading={loading} citations={metadata?.citations ?? []} audioUrl={audioUrl} />
        </section>

        <aside className="evidence-rail">
          <div className="rail-heading">
            <span>Live evidence</span>
            <small>{metadata ? `${Math.round(metadata.confidence * 100)}% confidence` : "Waiting for a question"}</small>
          </div>
          <LatencyDashboard timings={metadata?.timings ?? []} total={metadata?.total_duration_ms ?? 0} />
          {metadata?.degraded_services.length ? (
            <div className="degraded-note"><strong>Local fallbacks active</strong><span>{metadata.degraded_services.join(" · ").replaceAll("_", " ")}</span></div>
          ) : null}
          <div className="rail-footnote">
            <i />
            <p><strong>Grounded by design.</strong> Low-confidence or unsupported answers stop before speech synthesis.</p>
          </div>
        </aside>
      </div>

      <footer>
        <span>Vaaani / HH Goa 2026</span>
        <span>Qdrant · LangGraph · Sarvam</span>
      </footer>
    </main>
  );
}
