import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    // The CLI checker uses detached child processes, which are unavailable in
    // restricted build environments. The TypeScript compiler API performs the
    // same validation without requiring a local IPC port.
    useTypeScriptCli: false,
  },
};

export default nextConfig;
