import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vaaani: Ask across languages",
  description: "A voice-first, evidence-grounded multilingual research assistant.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
