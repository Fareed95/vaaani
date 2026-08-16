"use client";

import { Languages } from "lucide-react";
import type { LanguageCode } from "@/lib/api-client";

const languages: Array<{ code: LanguageCode; label: string; native: string }> = [
  { code: "en-IN", label: "English", native: "English" },
  { code: "hi-IN", label: "Hindi", native: "हिन्दी" },
  { code: "bn-IN", label: "Bengali", native: "বাংলা" },
  { code: "ta-IN", label: "Tamil", native: "தமிழ்" },
  { code: "mr-IN", label: "Marathi", native: "मराठी" },
  { code: "te-IN", label: "Telugu", native: "తెలుగు" },
];

export function LanguageSelector({ value, onChange }: { value: LanguageCode; onChange: (value: LanguageCode) => void }) {
  return (
    <label className="language-select">
      <Languages size={16} aria-hidden="true" />
      <span className="sr-only">Question language</span>
      <select value={value} onChange={(event) => onChange(event.target.value as LanguageCode)}>
        {languages.map((language) => (
          <option key={language.code} value={language.code}>
            {language.native} · {language.label}
          </option>
        ))}
      </select>
    </label>
  );
}
