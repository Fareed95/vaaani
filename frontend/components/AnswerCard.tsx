"use client";

import { AudioLines, BookOpenText, Volume2 } from "lucide-react";
import { Fragment, useState } from "react";
import type { Citation } from "@/lib/api-client";
import { SourceCitation } from "./SourceCitation";

interface AnswerCardProps {
  answer: string;
  citations: Citation[];
  loading: boolean;
  audioUrl?: string;
}

export function AnswerCard({ answer, citations, loading, audioUrl }: AnswerCardProps) {
  const [expandedSources, setExpandedSources] = useState<number[]>([]);
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
                  aria-controls={`source-${rank}`}
                  aria-expanded={expandedSources.includes(rank)}
                  key={`${part}-${index}`}
                  onClick={() => setExpandedSources((current) =>
                    current.includes(rank)
                      ? current.filter((value) => value !== rank)
                      : [...current, rank]
                  )}
                >
                  {part}
                </button>
              );
            })
          : "Finding the strongest evidence…"}
      </div>
      {audioUrl && <audio className="audio-player" controls src={audioUrl}>Your browser cannot play this answer.</audio>}
      {citations.length > 0 && (
        <section className="sources">
          <h2><BookOpenText size={17} /> Evidence used <span>{citations.length}</span></h2>
          {citations.map((citation) => (
            <SourceCitation
              key={`${citation.passage_id}-${citation.rank}`}
              citation={citation}
              expanded={expandedSources.includes(citation.rank)}
              onToggle={(expanded) => setExpandedSources((current) =>
                expanded
                  ? Array.from(new Set([...current, citation.rank]))
                  : current.filter((value) => value !== citation.rank)
              )}
            />
          ))}
        </section>
      )}
    </article>
  );
}
