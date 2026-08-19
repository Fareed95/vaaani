export type LanguageCode = "en-IN" | "hi-IN" | "bn-IN" | "ta-IN" | "mr-IN" | "te-IN";

export interface ConversationTurn {
  role: "user" | "assistant";
  content: string;
}

export interface QueryRequest {
  query?: string;
  audio_base64?: string;
  audio_mime_type?: string;
  language: LanguageCode;
  conversation: ConversationTurn[];
}

export interface Citation {
  rank: number;
  passage_id: string;
  text: string;
  score: number;
  language: string;
  source_lang?: string | null;
  target_lang?: string | null;
  chunk_strategy: string;
}

export interface StageTiming {
  stage: string;
  started_at: string;
  ended_at: string;
  duration_ms: number;
  status: "ok" | "error" | "skipped";
}

/** Retrieval result, delivered while the LLM is still generating. */
export interface EvidencePreview {
  transcript: string;
  confidence: number;
  refused: boolean;
  citations: Citation[];
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
  refusal_reason?: string | null;
  guardrails: GuardrailDecision[];
  timings: StageTiming[];
  total_duration_ms: number;
  degraded_services: string[];
  audio_mime_type?: string | null;
}

export interface HealthStatus {
  status: "healthy" | "degraded";
  version: string;
  indexed_chunks: number;
  vector_db: string;
  stt_provider: string;
  tts_provider: string;
  retrieval_mode: string;
  languages: string[];
}

interface StreamHandlers {
  onStage?: (stage: string) => void;
  onEvidence?: (evidence: EvidencePreview) => void;
  onMetadata?: (metadata: QueryMetadata) => void;
  onToken?: (token: string) => void;
  onAudio?: (base64: string, mimeType: string) => void;
  onDone?: (requestId: string) => void;
}

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export async function getHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const message = await readErrorMessage(response);
    throw new Error(message || `Health check failed with status ${response.status}.`);
  }

  return response.json() as Promise<HealthStatus>;
}

export function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Could not read audio recording."));
    reader.onloadend = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("Audio recording could not be encoded."));
        return;
      }
      resolve(result.split(",", 2)[1] ?? "");
    };
    reader.readAsDataURL(blob);
  });
}

export async function streamQuery(payload: QueryRequest, handlers: StreamHandlers = {}): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/query/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await readErrorMessage(response);
    throw new Error(message || `Request failed with status ${response.status}.`);
  }

  if (!response.body) {
    throw new Error("The answer service did not return a stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const events = buffer.split(/\r?\n\r?\n/);
    buffer = events.pop() ?? "";

    for (const eventBlock of events) {
      handleEvent(eventBlock, handlers);
    }

    if (done) {
      if (buffer.trim()) handleEvent(buffer, handlers);
      break;
    }
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown; message?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (typeof body.message === "string") return body.message;
  } catch {
    const text = await response.text().catch(() => "");
    if (text) return text;
  }
  return "";
}

function handleEvent(eventBlock: string, handlers: StreamHandlers): void {
  const lines = eventBlock.split(/\r?\n/);
  let event = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice("event:".length).trim();
    if (line.startsWith("data:")) dataLines.push(line.slice("data:".length).trimStart());
  }

  if (!dataLines.length) return;
  const data = JSON.parse(dataLines.join("\n")) as unknown;

  switch (event) {
    case "stage":
      handlers.onStage?.((data as { stage: string }).stage);
      break;
    case "evidence":
      handlers.onEvidence?.(data as EvidencePreview);
      break;
    case "metadata":
      handlers.onMetadata?.(data as QueryMetadata);
      break;
    case "token":
      handlers.onToken?.((data as { token: string }).token);
      break;
    case "audio": {
      const audio = data as { base64: string; mime_type?: string | null };
      handlers.onAudio?.(audio.base64, audio.mime_type ?? "audio/wav");
      break;
    }
    case "done":
      handlers.onDone?.((data as { request_id: string }).request_id);
      break;
    case "error":
      throw new Error((data as { message?: string }).message ?? "The answer service returned an error.");
  }
}
