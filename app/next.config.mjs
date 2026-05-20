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
    // 'web' (default) or 'mobile' (Capacitor build) — selects the server
    // write sink via the X-Client-Channel header. See plan/09.
    NEXT_PUBLIC_CLIENT_CHANNEL: process.env.NEXT_PUBLIC_CLIENT_CHANNEL ?? 'web',
    // Supabase Auth (plan/07-auth.md). When unset (default), the
    // auth UI renders in "configure-me" mode so the build still
    // succeeds on a fresh clone; sign-in is disabled until the real
    // project URL + anon key land in .env.local.
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL ?? '',
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '',
  },
};

export default nextConfig;
