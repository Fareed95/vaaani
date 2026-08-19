// These match records actually present in the indexed corpus so they
// return grounded answers instead of a low-confidence refusal. The current
// production index runs feature-hash fallback embeddings (see docs/decisions.md),
// which don't support cross-lingual semantic matching, so samples are English.
const samples = [
  "What is a corporation?",
  "Honesty or integrity definition",
  "Does medical marijuana help with PTSD?",
  "Why did Rachel Carson write an obligation to endure?",
];

export function SampleQueryButtons({ onSelect, disabled }: { onSelect: (query: string) => void; disabled?: boolean }) {
  return (
    <div className="sample-queries" aria-label="Sample questions">
      <span>Try asking</span>
      <div>
        {samples.map((sample) => (
          <button type="button" key={sample} onClick={() => onSelect(sample)} disabled={disabled}>
            {sample}
          </button>
        ))}
      </div>
    </div>
  );
}
