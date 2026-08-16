const samples = [
  "भारत में हरित क्रांति का क्या प्रभाव पड़ा?",
  "How does monsoon rainfall shape Indian agriculture?",
  "মহাকাশে প্রথম ভারতীয় কে ছিলেন?",
  "தமிழ்நாட்டின் முக்கிய ஆறுகள் யாவை?",
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
