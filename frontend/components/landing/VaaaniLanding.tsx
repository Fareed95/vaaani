"use client";

/* eslint-disable @next/next/no-img-element -- fixed public art plates need raw layered image elements. */

import gsap from "gsap";
import { ArrowRight, BookOpenText, Github, Languages, Mic2, RotateCcw, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { InstagramEmbeds } from "./InstagramEmbeds";
import styles from "./VaaaniLanding.module.css";

type LayerDef = {
  file: string;
  name: string;
  initialScale: number;
  revealDelay: number;
  isLogo?: boolean;
  mobileScale?: number;
};

type PosterStyle = CSSProperties & Record<`--${string}`, string | number>;

const ASSET_BASE = "/assets/vaaani-poster";
const CANVAS_ASPECT = 2560 / 1440;

const POSTER_LAYERS: LayerDef[] = [
  { file: "05-backdrop.webp", name: "Backdrop", initialScale: 1.14, revealDelay: 0 },
  { file: "04-sunrise.webp", name: "Sunrise", initialScale: 1.23, revealDelay: 0.16 },
  { file: "06-table.webp", name: "Long table", initialScale: 1.31, revealDelay: 0.32 },
  { file: "02-village.webp", name: "Beach village", initialScale: 1.4, revealDelay: 0.48 },
  { file: "08-villa.webp", name: "Villa", initialScale: 1.4, revealDelay: 0.64 },
  { file: "01-palms.webp", name: "Palms", initialScale: 1.52, revealDelay: 0.8 },
  { file: "07-signpost.webp", name: "Signpost", initialScale: 1.52, revealDelay: 0.96 },
  { file: "03-umbrella.webp", name: "Beach umbrella", initialScale: 1.66, revealDelay: 1.12 },
  { file: "09-shack.webp", name: "Beach shack", initialScale: 1.66, revealDelay: 1.28 },
  { file: "12-wordmark.webp", name: "Poster wordmark", initialScale: 3.31, revealDelay: 1.5, isLogo: true, mobileScale: 0.5 },
  { file: "11-lockup.svg", name: "Hindi lockup", initialScale: 2.44, revealDelay: 1.76, mobileScale: 0.54 },
];

const LANGUAGE_MODES = ["English", "हिन्दी", "বাংলা", "தமிழ்", "मराठी", "తెలుగు"];

const FLOW_STEPS = [
  { icon: Mic2, title: "Speak naturally", detail: "Start with voice or text in the language you think in." },
  { icon: Languages, title: "Keep context", detail: "Vaaani carries the transcript into the right language mode." },
  { icon: BookOpenText, title: "Check sources", detail: "Relevant passages stay visible beside the generated answer." },
  { icon: ShieldCheck, title: "Stop when unsure", detail: "Unsupported answers are withheld instead of dressed up." },
];

const SOURCE_PREVIEW = [
  ["01", "Agriculture and monsoon patterns", "0.91"],
  ["02", "Regional policy note", "0.88"],
  ["03", "Historical context", "0.84"],
];

export function VaaaniLanding() {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const posterRef = useRef<HTMLDivElement | null>(null);
  const layerRefs = useRef<HTMLImageElement[]>([]);
  const ctaRef = useRef<HTMLDivElement | null>(null);
  const [box, setBox] = useState({ width: 0, height: 0, x: 0 });
  const [playKey, setPlayKey] = useState(0);

  useLayoutEffect(() => {
    const element = stageRef.current;
    if (!element) return;

    const update = () => {
      const bounds = element.getBoundingClientRect();
      const height = Math.max(bounds.width / CANVAS_ASPECT, bounds.height);
      const width = height * CANVAS_ASPECT;
      setBox({ width, height, x: (bounds.width - width) / 2 });
    };

    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useLayoutEffect(() => {
    const root = rootRef.current;
    const poster = posterRef.current;
    if (!root || !poster || box.height <= 0) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const context = gsap.context(() => {
      if (reduceMotion) {
        gsap.set([poster, ctaRef.current, ...layerRefs.current], {
          clearProps: "all",
          clipPath: "inset(0% 0% 0% 0%)",
          opacity: 1,
          scale: 1,
        });
        return;
      }

      const intro = gsap.timeline({ defaults: { ease: "power3.out" } });
      const isCompact = window.matchMedia("(max-width: 620px)").matches;
      gsap.set(poster, { opacity: 0, scale: 1.14 });
      gsap.set(ctaRef.current, { opacity: 0, y: 28 });
      intro.to(poster, { opacity: 1, scale: 1, duration: 3.2, ease: "power3.inOut" }, 0);

      layerRefs.current.forEach((layer, index) => {
        const layerDef = POSTER_LAYERS[index];
        const finalScale = isCompact && layerDef.mobileScale ? layerDef.mobileScale : 1;
        gsap.set(layer, {
          clipPath: layerDef.isLogo ? "inset(0% 0% 100% 0%)" : "inset(0% 0% 0% 0%)",
          filter: layerDef.isLogo ? "blur(4px)" : "none",
          opacity: layerDef.isLogo ? 1 : 0,
          scale: layerDef.initialScale,
        });
        intro.to(layer, { opacity: 1, duration: 0.65 }, layerDef.revealDelay);
        intro.to(layer, { scale: finalScale, duration: 3.35, ease: "expo.out" }, layerDef.revealDelay);
        if (layerDef.isLogo) {
          intro.to(layer, { clipPath: "inset(0% 0% 0% 0%)", filter: "blur(0px)", duration: 3.7, ease: "expo.out" }, layerDef.revealDelay);
        }
      });

      intro.to(ctaRef.current, { opacity: 1, y: 0, duration: 0.85 }, 2.15);
      gsap.to(poster, { duration: 5, ease: "sine.inOut", repeat: -1, scale: 1.018, yoyo: true });
    }, root);

    return () => context.revert();
  }, [box.height, playKey]);

  return (
    <div ref={rootRef} className={styles.page}>
      <main ref={stageRef} className={styles.stage} aria-label="Animated Vaaani poster">
        {box.height > 0 ? (
          <div
            key={playKey}
            ref={posterRef}
            className={styles.poster}
            style={
              {
                "--poster-width": `${box.width}px`,
                "--poster-height": `${box.height}px`,
                "--poster-x": `${box.x}px`,
              } as PosterStyle
            }
          >
            {POSTER_LAYERS.map((layer, index) => (
              <img
                key={layer.file}
                ref={(element) => {
                  if (element) layerRefs.current[index] = element;
                }}
                src={`${ASSET_BASE}/${layer.file}`}
                alt={layer.name}
                draggable={false}
                className={styles.layer}
                style={{ "--z-index": index } as PosterStyle}
              />
            ))}
          </div>
        ) : null}

        <div ref={ctaRef} className={styles.heroDock}>
          <p>Vaaani</p>
          <h1>Voice answers with proof attached.</h1>
          <span className={styles.heroTag}>Built at Hacker House Goa 2026 &middot; #RAGInGoa</span>
          <Link href="/vaaani" className={styles.heroAction}>
            Launch Vaaani <ArrowRight size={19} />
          </Link>
        </div>

        <button
          type="button"
          className={styles.replay}
          onClick={() => setPlayKey((key) => key + 1)}
          aria-label="Replay poster intro"
        >
          <RotateCcw size={17} aria-hidden="true" />
        </button>

        <a
          href="https://github.com/Fareed95/vaaani"
          target="_blank"
          rel="noopener noreferrer"
          className={styles.githubLink}
          aria-label="View source on GitHub"
        >
          <Github size={17} aria-hidden="true" />
        </a>
      </main>

      <section className={styles.productBand} aria-labelledby="landing-product-title">
        <div className={styles.bandCopy}>
          <p>Open the product</p>
          <h2 id="landing-product-title">Ask in your language. Check the evidence. Then listen.</h2>
          <span>
            Vaaani opens straight into the working console: voice input, language selection,
            cited answers, and a clean evidence trail.
          </span>
          <Link href="/vaaani" className={styles.primaryAction}>
            Go to Vaaani <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      <section className={styles.languageSection} aria-labelledby="landing-language-title">
        <div>
          <p>Language first</p>
          <h2 id="landing-language-title">The interface bends around how people actually ask.</h2>
        </div>
        <div className={styles.languageChips}>
          {LANGUAGE_MODES.map((language) => <span key={language}>{language}</span>)}
        </div>
      </section>

      <section className={styles.flowSection} aria-label="Vaaani flow">
        {FLOW_STEPS.map((step) => {
          const Icon = step.icon;
          return (
            <article key={step.title}>
              <Icon size={18} />
              <h3>{step.title}</h3>
              <p>{step.detail}</p>
            </article>
          );
        })}
      </section>

      <section className={styles.evidenceSection} aria-labelledby="landing-evidence-title">
        <div>
          <p>Evidence stays close</p>
          <h2 id="landing-evidence-title">No answer floats alone.</h2>
          <span>Every response can show what supported it, how strong the match was, and when the system chose not to answer.</span>
        </div>
        <div className={styles.sourcePreview}>
          {SOURCE_PREVIEW.map(([rank, title, score]) => (
            <article key={rank}>
              <small>{rank}</small>
              <strong>{title}</strong>
              <span>{score}</span>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.instaSection} aria-labelledby="landing-insta-title">
        <div>
          <p>Built in public</p>
          <h2 id="landing-insta-title">Follow the build from Hacker House Goa 2026.</h2>
          <span>The 72-hour process and the live demo, posted for #RAGInGoa.</span>
        </div>
        <InstagramEmbeds className={styles.instaGrid} />
      </section>

      <section className={styles.finalCta} aria-labelledby="landing-final-title">
        <p>Ready</p>
        <h2 id="landing-final-title">Open Vaaani and ask the first question.</h2>
        <Link href="/vaaani" className={styles.primaryAction}>
          Launch the console <ArrowRight size={18} />
        </Link>
      </section>

      <footer className={styles.landingFooter}>
        <span>Vaaani</span>
        <span className={styles.devCredits}>
          Developed by
          <a href="https://github.com/Fareed95" target="_blank" rel="noopener noreferrer">
            <img src="https://github.com/Fareed95.png" alt="" width={18} height={18} /> Fareed95
          </a>
          <a href="https://github.com/arshhimself" target="_blank" rel="noopener noreferrer">
            <img src="https://github.com/arshhimself.png" alt="" width={18} height={18} /> arshhimself
          </a>
        </span>
      </footer>
    </div>
  );
}
