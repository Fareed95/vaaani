import { Quote } from "lucide-react";

export function TranscriptDisplay({ transcript }: { transcript: string }) {
  if (!transcript) return null;
  return (
    <div className="transcript">
      <Quote size={16} aria-hidden="true" />
      <div>
        <span>I heard</span>
        <p>{transcript}</p>
      </div>
    </div>
  );
}
