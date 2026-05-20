import type { Config } from "tailwindcss";

/**
 * Design tokens ported from the Elbaraaa/OneHealth reference app
 * (plan/08-mobile-ux-revamp.md). Teal-forward public-health palette.
 * Existing CSS variables in globals.css are kept during the migration.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17232f",
        "public-teal": "#00796b",
        "public-blue": "#2364aa",
        "warm-gold": "#d99020",
        "soft-mint": "#e8f7f2",
        "soft-sky": "#eaf4ff",
      },
      boxShadow: {
        soft: "0 18px 60px rgba(23, 35, 47, 0.10)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
