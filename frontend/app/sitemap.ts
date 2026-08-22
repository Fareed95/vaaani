import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://vaaani.co.in";
  return [
    { url: `${base}/`, changeFrequency: "weekly", priority: 1 },
    { url: `${base}/vaaani`, changeFrequency: "weekly", priority: 0.9 },
  ];
}
