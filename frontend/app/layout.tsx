import type { Metadata } from "next";
import "./globals.css";

const SITE_URL = "https://vaaani.co.in";
const TITLE = "Vaaani — Voice-First RAG Built at Hacker House Goa 2026";
const DESCRIPTION =
  "Vaaani is a voice-first, evidence-grounded multilingual RAG assistant across 6 Indian languages, built by Fareed95 and arshhimself at Hacker House Goa 2026 (#RAGInGoa). Ask by voice, get a grounded answer with citations, hear it read back.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: TITLE,
    template: "%s · Vaaani",
  },
  description: DESCRIPTION,
  keywords: [
    "Hacker House Goa",
    "Hacker House Goa 2026",
    "HH Goa 2026",
    "#RAGInGoa",
    "voice RAG",
    "voice-enabled RAG",
    "multilingual RAG",
    "Indian languages AI",
    "retrieval augmented generation",
    "Vaaani",
  ],
  authors: [
    { name: "Fareed95", url: "https://github.com/Fareed95" },
    { name: "arshhimself", url: "https://github.com/arshhimself" },
  ],
  alternates: { canonical: SITE_URL },
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: "Vaaani",
    title: TITLE,
    description: DESCRIPTION,
    locale: "en_IN",
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
  },
  robots: { index: true, follow: true },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Vaaani",
  applicationCategory: "VoiceApplication",
  operatingSystem: "Web",
  url: SITE_URL,
  description: DESCRIPTION,
  offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
  creator: [
    { "@type": "Person", name: "Fareed95", url: "https://github.com/Fareed95" },
    { "@type": "Person", name: "arshhimself", url: "https://github.com/arshhimself" },
  ],
  isPartOf: {
    "@type": "Event",
    name: "Hacker House Goa 2026",
    alternateName: "HH Goa 2026",
    startDate: "2026-10-28",
    endDate: "2026-10-31",
    location: { "@type": "Place", name: "Goa, India" },
  },
  keywords: "Hacker House Goa, Hacker House Goa 2026, RAGInGoa, voice RAG, multilingual RAG",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
