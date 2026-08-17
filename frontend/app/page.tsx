import type { Metadata } from "next";
import { VaaaniLanding } from "@/components/landing/VaaaniLanding";

export const metadata: Metadata = {
  title: "Vaaani | Voice AI That Shows Its Work",
  description: "A premium landing page for Vaaani's multilingual, evidence-grounded voice AI console.",
};

export default function HomePage() {
  return <VaaaniLanding />;
}
