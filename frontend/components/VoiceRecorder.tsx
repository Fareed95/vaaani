"use client";

import { Mic, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface VoiceRecorderProps {
  disabled?: boolean;
  onRecording: (blob: Blob) => void | Promise<void>;
}

export function VoiceRecorder({ disabled = false, onRecording }: VoiceRecorderProps) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState<string>();
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    if (!recording) return;
    const timer = window.setInterval(() => {
      setSeconds((current) => {
        if (current >= 29) recorderRef.current?.stop();
        return current + 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [recording]);

  async function start() {
    setError(undefined);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        setRecording(false);
        setSeconds(0);
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        if (blob.size) await onRecording(blob);
      };
      recorderRef.current = recorder;
      recorder.start(250);
      setSeconds(0);
      setRecording(true);
    } catch {
      setError("Microphone access is blocked. Allow it in your browser, or type your question below.");
    }
  }

  function stop() {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  }

  return (
    <div className="voice-control">
      <div className={`voice-orbit ${recording ? "is-recording" : ""}`} aria-hidden="true">
        <div className="waveform">
          {[13, 25, 38, 22, 45, 31, 18, 35, 26, 42, 20, 30].map((height, index) => (
            <i key={index} style={{ "--bar-height": `${height}px`, "--bar-delay": `${index * -80}ms` } as React.CSSProperties} />
          ))}
        </div>
      </div>
      <button
        type="button"
        className={`record-button ${recording ? "is-recording" : ""}`}
        onClick={recording ? stop : start}
        disabled={disabled}
        aria-label={recording ? "Stop recording" : "Start recording"}
      >
        {recording ? <Square size={24} fill="currentColor" /> : <Mic size={28} />}
      </button>
      <div className="record-caption" aria-live="polite">
        <strong>{recording ? `Listening · 0:${seconds.toString().padStart(2, "0")}` : "Tap to speak"}</strong>
        <span>{recording ? "Tap when done" : "Voice or type below"}</span>
      </div>
      {error && <p className="field-error" role="alert">{error}</p>}
    </div>
  );
}
