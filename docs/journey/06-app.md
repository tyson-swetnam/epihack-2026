# 06 · Ship the app

!!! note "Stub"
    Authored in Phase 3. Source: `plan/06-mobile-app.md`,
    `plan/08-mobile-ux-revamp.md`, `plan/07-auth.md`, `app/src/`.

## What we wanted

A mobile-first reporting app that *feels* anonymous (no required login)
but lets motivated users opt into a profile that improves the relevance of
the advisories they get back — without ever sending PII to a server that
can't be coarsened or anonymised.

## What we built

- **Next.js 16 + React 19 + TypeScript + Tailwind**, statically exported.
- Three primary report flows: **tick** (VBD), **heat** (extreme heat),
  **cool-off** (cooling-center finder).
- **EXIF GPS stripping** on the client (`app/src/lib/exif-stripper.ts`),
  with server-side rejection at 422 if it slips through.
- **ZIP / 1 km coarsening** (`app/src/lib/coarse-geo.ts`).
- **Offline retry queue** for low-connectivity reporting.
- **`X-Client-Channel`** header routing.
- Optional **profile enrichment** (household size, pets, outdoor work).
- A **personal dashboard** with local weather, active alerts, a community
  leaderboard, engagement rewards, and a weekly-email opt-in.

## What it looks like

_Screenshots land here from Phase 5._

## Decisions & trade-offs

To be authored.

## Where to go next

[07 · Vibe-coding history →](07-vibe-coding.md) — how the whole thing got
made with Claude Code.
