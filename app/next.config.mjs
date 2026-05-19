/**
 * Next.js config — AZ One Health Sentinel reporting app.
 *
 * The pilot ships to GitHub Pages so we build with `output: 'export'`
 * (static HTML, no server runtime required). Capacitor wraps the same
 * static bundle into iOS / Android builds in a later phase
 * (plan/06-mobile-app.md § Delivery sequence).
 *
 * basePath = '/epihack-2026/app' so links resolve correctly under
 * https://tyson-swetnam.github.io/epihack-2026/app/. The build script
 * runs `next build && next export`; the `out/` directory drops into
 * GitHub Pages via the workflow at .github/workflows/deploy-app.yml.
 *
 * For local dev the basePath stays the same so links match production.
 * Override via NEXT_BASE_PATH if you're previewing in isolation.
 */
const basePath = process.env.NEXT_BASE_PATH ?? '/epihack-2026/app';

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  basePath,
  assetPrefix: basePath,
  trailingSlash: true,
  images: { unoptimized: true }, // static-export incompatible with image opt
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE ?? 'mock',
    NEXT_PUBLIC_BUILD: process.env.NEXT_PUBLIC_BUILD ?? 'dev',
  },
};

export default nextConfig;
