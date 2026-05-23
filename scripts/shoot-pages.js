#!/usr/bin/env node
// scripts/shoot-pages.js — Phase 5 of plan/10-archival-and-docs.md.
//
// Walk every page of the published Jekyll site, the local-build new
// `index.html`, and the published Next.js app, taking full-page PNG
// screenshots into docs/_screenshots/. The screenshots are then
// referenced from the journey pages.
//
// Usage:
//   node scripts/shoot-pages.js [--quick]
//
// Requires playwright; the script resolves it from the npx cache so we
// don't need to add it as a repo dep.

const path = require("path");
const fs = require("fs");

// Find a usable playwright install — prefer the npx cache so we don't
// add it as a repo dep.
function loadPlaywright() {
  const home = process.env.HOME;
  const cache = path.join(home, ".npm", "_npx");
  if (fs.existsSync(cache)) {
    for (const ent of fs.readdirSync(cache)) {
      const cand = path.join(cache, ent, "node_modules", "playwright");
      if (fs.existsSync(path.join(cand, "package.json"))) {
        return require(cand);
      }
    }
  }
  return require("playwright");
}

const { chromium } = loadPlaywright();

const REPO = path.resolve(__dirname, "..");
const OUT = path.join(REPO, "docs", "_screenshots");
fs.mkdirSync(OUT, { recursive: true });

const PAGES = [
  // The redesigned trailhead — local file:// since gh-pages still has the
  // old layout until deploy-jekyll fires on the merge.
  { slug: "index",            url: "file://" + path.join(REPO, "index.html") },

  // Jekyll-published pages on the live site (gh-pages).
  { slug: "site-figures",     url: "https://tyson-swetnam.github.io/epihack-2026/figures/" },
  { slug: "site-wildlife",    url: "https://tyson-swetnam.github.io/epihack-2026/wildlife/" },
  { slug: "site-heat",        url: "https://tyson-swetnam.github.io/epihack-2026/heat/" },
  { slug: "site-plan",        url: "https://tyson-swetnam.github.io/epihack-2026/plan/" },
  { slug: "site-today",       url: "https://tyson-swetnam.github.io/epihack-2026/today/" },
  { slug: "site-dashboard",   url: "https://tyson-swetnam.github.io/epihack-2026/dashboard/" },
  { slug: "site-map",         url: "https://tyson-swetnam.github.io/epihack-2026/map/",   wait: 2000 },
  { slug: "site-graph",       url: "https://tyson-swetnam.github.io/epihack-2026/graph/", wait: 2000 },
  { slug: "site-query",       url: "https://tyson-swetnam.github.io/epihack-2026/query/", wait: 3000 },

  // Live Next.js app on Jetstream2.
  { slug: "app-home",         url: "http://epihack-test.cis240692.projects.jetstream-cloud.org/" },
  { slug: "app-sign-in",      url: "http://epihack-test.cis240692.projects.jetstream-cloud.org/sign-in" },
  { slug: "app-report",       url: "http://epihack-test.cis240692.projects.jetstream-cloud.org/report" },
  { slug: "app-dashboard",    url: "http://epihack-test.cis240692.projects.jetstream-cloud.org/dashboard" },
  { slug: "app-profile",      url: "http://epihack-test.cis240692.projects.jetstream-cloud.org/profile" },
  { slug: "app-account",      url: "http://epihack-test.cis240692.projects.jetstream-cloud.org/account" },
];

const QUICK = process.argv.includes("--quick");
const subset = QUICK ? PAGES.filter(p => p.slug === "index") : PAGES;

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    userAgent: "epihack-archive-screenshot-bot/1.0 (+https://github.com/tyson-swetnam/epihack-2026)",
  });
  const results = [];
  for (const p of subset) {
    const out = path.join(OUT, p.slug + ".png");
    const start = Date.now();
    try {
      const page = await ctx.newPage();
      await page.goto(p.url, { waitUntil: "networkidle", timeout: 25000 });
      if (p.wait) await page.waitForTimeout(p.wait);
      await page.screenshot({ path: out, fullPage: true });
      await page.close();
      const ms = Date.now() - start;
      console.log(`OK  ${p.slug.padEnd(20)} ${ms.toString().padStart(5)}ms  ${out}`);
      results.push({ slug: p.slug, url: p.url, status: "OK", ms });
    } catch (err) {
      const ms = Date.now() - start;
      console.log(`ERR ${p.slug.padEnd(20)} ${ms.toString().padStart(5)}ms  ${err.message}`);
      results.push({ slug: p.slug, url: p.url, status: "ERR", error: err.message, ms });
    }
  }
  await browser.close();
  fs.writeFileSync(
    path.join(OUT, "manifest.json"),
    JSON.stringify({ generated: new Date().toISOString(), results }, null, 2)
  );
  const ok = results.filter(r => r.status === "OK").length;
  const err = results.length - ok;
  console.log(`\n${ok}/${results.length} pages captured, ${err} failed.`);
  process.exit(err === 0 ? 0 : 1);
})();
