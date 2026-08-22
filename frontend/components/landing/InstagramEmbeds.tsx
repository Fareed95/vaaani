"use client";

import { useEffect } from "react";

declare global {
  interface Window {
    instgrm?: { Embeds: { process: () => void } };
  }
}

const REELS = [
  "https://www.instagram.com/reel/DcWV242IOWv/",
  "https://www.instagram.com/reel/DcWTwNUAUB7/",
];

export function InstagramEmbeds({ className }: { className?: string }) {
  useEffect(() => {
    if (window.instgrm) {
      window.instgrm.Embeds.process();
      return;
    }
    const script = document.createElement("script");
    script.src = "https://www.instagram.com/embed.js";
    script.async = true;
    document.body.appendChild(script);
  }, []);

  return (
    <div className={className}>
      {REELS.map((url) => (
        <blockquote
          key={url}
          className="instagram-media"
          data-instgrm-permalink={url}
          data-instgrm-version="14"
          style={{ background: "#FFF", border: 0, borderRadius: 8, margin: 0, minWidth: 326, width: "100%" }}
        />
      ))}
    </div>
  );
}
