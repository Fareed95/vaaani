export type LanguageCode = "en-IN" | "hi-IN" | "bn-IN" | "ta-IN" | "mr-IN" | "te-IN";

export interface Citation {
  rank: number;
  passage_id: string;
  text: string;
  score: number;
  language: string;
  source_lang?: string;
  target_lang?: string;
  chunk_strategy: string;
}

export interface StageTiming {
  stage: string;
  started_at: string;
  ended_at: string;
  duration_ms: number;
  status: "ok" | "error" | "skipped";
}

export interface GuardrailDecision {
  guardrail: string;
  passed: boolean;
  reason: string;
  details: Record<string, string | number | boolean | null>;
}

export interface QueryMetadata {
  request_id: string;
  transcript: string;
  citations: Citation[];
  confidence: number;
  refused: boolean;
  refusal_reason?: string;
  guardrails: GuardrailDecision[];
  timings: StageTiming[];
  total_duration_ms: number;
  degraded_services: string[];
  audio_mime_type?: string;
}

export interface HealthStatus {
  status: "healthy" | "degraded";
  indexed_chunks: number;
  vector_db: string;
  stt_provider: string;
  retrieval_mode: string;
}

interface StreamHandlers {
  onMetadata: (metadata: QueryMetadata) => void;
  onToken: (token: string) => void;
  onAudio: (base64: string, mimeType: string) => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function blobToBase64(blob: Blob): Promise<string> {
  const buffer = await blob.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 8192) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
  }
  return btoa(binary);
}

export async function streamQuery(
  payload: {
    query?: string;
    audio_base64?: string;
    audio_mime_type?: string;
    language: LanguageCode;
    conversation?: Array<{ role: "user" | "assistant"; content: string }>;
  },
  handlers: StreamHandlers,
): Promise<void> {
  const response = await fetch(`${API_URL}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok || !response.body) {
    const message = await response.text();
    throw new Error(message || `Query failed with status ${response.status}`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const messages = buffer.split("\n\n");
    buffer = messages.pop() ?? "";
    for (const message of messages) {
      const lines = message.split("\n");
      const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
      const data = lines.find((line) => line.startsWith("data:"))?.slice(5).trim();
      if (!event || !data) continue;
      const parsed = JSON.parse(data);
      if (event === "metadata") handlers.onMetadata(parsed as QueryMetadata);
      if (event === "token") handlers.onToken(parsed.token as string);
      if (event === "audio") handlers.onAudio(parsed.base64, parsed.mime_type);
      if (event === "error") throw new Error(parsed.message);
    }
    if (done) break;
  }
}

export async function getHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!response.ok) throw new Error("API health check failed");
  return response.json();
}
