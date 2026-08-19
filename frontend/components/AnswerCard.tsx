"use client";

import { AudioLines, Volume2 } from "lucide-react";
import { Fragment } from "react";
import type { Citation } from "@/lib/api-client";

interface AnswerCardProps {
  answer: string;
  citations: Citation[];
  loading: boolean;
  audioUrl?: string;
  /** Chunks live in the rail, so an inline marker opens them there. */
  onCitationSelect?: (rank: number) => void;
}

export function AnswerCard({ answer, citations, loading, audioUrl, onCitationSelect }: AnswerCardProps) {
  if (!answer && !loading) return null;
  const answerParts = answer.split(/(\[\d+\])/g);
  return (
    <article className="answer-card" aria-live="polite">
      <header>
        <div><AudioLines size={17} /><span>Grounded answer</span></div>
        {audioUrl && (
          <a href={audioUrl} className="audio-link" aria-label="Play spoken answer">
            <Volume2 size={16} /> Listen
          </a>
        )}
      </header>
      <div className={`answer-copy ${loading ? "is-streaming" : ""}`}>
        {answer
          ? answerParts.map((part, index) => {
              const match = part.match(/^\[(\d+)\]$/);
              if (!match) return <Fragment key={`${part}-${index}`}>{part}</Fragment>;
              const rank = Number(match[1]);
              if (!citations.some((citation) => citation.rank === rank)) return part;
              return (
                <button
                  type="button"
                  className="inline-citation"
                  aria-label={`Toggle source ${rank}`}
                  aria-controls={`chunk-${rank}`}
                  key={`${part}-${index}`}
                  onClick={() => onCitationSelect?.(rank)}
                >
                  {part}
                </button>
              );
            })
          : "Finding the strongest evidence…"}
      </div>
      {audioUrl && <audio className="audio-player" controls src={audioUrl}>Your browser cannot play this answer.</audio>}
    </article>
  );
}
