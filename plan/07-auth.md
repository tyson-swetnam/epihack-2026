---
title: "Plan 07 — Authentication (account + Google / Facebook / Apple OAuth)"
---

# 07 — Authentication

Optional account system layered **on top of** the anonymous-first
reporting flow from
[plan/06-mobile-app.md](./06-mobile-app.html). Users can:

1. **File reports without an account** — the anonymous path stays
   the default and is never gated by sign-in.
2. **Create an email-password account** for cross-device profile
   storage and report history.
3. **Use a common OAuth provider** — Google, Facebook, or Apple —
   to sign up / sign in with one tap.

## Hard rules (don't break these)

These are non-negotiable; every later decision derives from them.

1. **Anonymous reporting NEVER requires authentication.** The
   three-button picker on the landing page works whether the user is
   signed in or signed out. The OpenAPI spec enforces this — `POST
   /v1/reports` accepts an unauthenticated request and returns a
   one-time `claim_token`.
2. **Linking a report to an account is a per-report opt-in.** After
   submit, a signed-in user is *offered* "attach this report to my
   account" via `POST /v1/auth/claim`. The default is to not attach.
3. **OAuth identity is PII.** A Google / Facebook / Apple user's
   email + provider-id is personally identifying. It lands in
   `auth.users` (private) and never appears on `public.observation`
   or the public dashboard, even for reports the user has attached
   to their account.
4. **Sign in with Apple is required.** App Store Review Guideline
   4.8 says any app offering Google / Facebook social login MUST
   also offer Sign in with Apple, and it must appear at least as
   prominently. Apple's private-email-relay (`@privaterelay.appleid.com`)
   is a first-class email format we must support.
5. **Right to erasure is a real button.** `DELETE /v1/auth/me`
   removes the user record and detaches them from any reports they
   had previously linked (the report itself stays in the graph; the
   `user_id ↔ observation_id` edge is severed).
6. **No third-party tracking pixels.** No Google Analytics, no
   Facebook Pixel, no Meta SDK telemetry. The OAuth dance uses
   Google / Facebook / Apple's *identity* APIs only; nothing else.
7. **Every account control defaults conservative.** Email-marketing
   opt-in: off. Cross-device sync: off. "Show my reports on a public
   leaderboard": off. The toggles live next to the same consent
   surface from plan/06.

## Surfaces

| Route | Purpose |
|---|---|
| `/sign-in` | Email + password, magic-link, and three OAuth buttons (Google, Apple, Facebook — Apple first per Guideline 4.8). |
| `/sign-up` | Same component; just a toggle. Email-verification email goes out on submit. |
| `/auth/callback` | OAuth-provider redirect target. Reads `code` + `state` from the URL, hands off to the provider SDK. |
| `/account` | Authenticated profile: name (optional), home ZIP, contact channels, language, accessibility needs, consent toggles — all opt-in. |
| `/account/reports` | List of reports the user has *attached* to their account. The user can detach any one (severs the link, leaves the report intact). |
| `/account/delete` | Account deletion. Requires re-auth. Cascades to detach (not delete) attached reports. |

## Stack: Supabase Auth for the pilot

The pilot uses **[Supabase Auth](https://supabase.com/docs/guides/auth)**.

Why:

- **Open source + self-hostable.** The same `supabase-js` SDK works
  against the hosted service or against a self-hosted Supabase
  instance. The pilot uses the hosted service; v1 migrates to a
  self-hosted Postgres + Supabase Auth if data sovereignty needs
  demand it.
- **Postgres-native.** Auth.users lives in Postgres — same engine
  as our DuckLake catalog. Row-level security policies bridge
  cleanly into the `consent_profile` work from
  [`schema/deep/application.sql`](../schema/deep/application.sql).
- **All three providers + email built in.** Google, Facebook, and
  Apple (with private-relay-email handling) ship as configuration,
  not code.
- **Static-export friendly.** The Next.js app stays `output: 'export'`;
  the OAuth dance happens on Supabase's domain, and the React
  client only ever sees the resulting JWT.
- **Magic-link path for low-friction first-time use.** Email-only
  sign-in with a one-time link is well-suited to a public-health
  audience that may not want to manage another password.

Alternatives considered:

| Option | Why not |
|---|---|
| [Auth.js (NextAuth)](https://authjs.dev/) | Needs Next.js API routes (server runtime). Breaks `output: 'export'`. |
| [Clerk](https://clerk.com/) | Excellent DX but proprietary and costs money at scale. |
| [Auth0](https://auth0.com/) | Same — proprietary, paid. |
| Custom (PyJWT + Authlib + bcrypt) | Weeks of work to get OAuth + email-verify + password-reset + session-refresh right. Not worth it for the pilot. We can migrate later. |

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│  Next.js app (browser)                                         │
│                                                                │
│   @supabase/supabase-js  ←─── OAuth + email + magic link       │
│           │                                                    │
│           ▼                                                    │
│   Supabase JWT in HttpOnly cookie + memory                     │
│           │                                                    │
│           ▼                                                    │
│   fetch('/api/v1/...', { headers: { Authorization: 'Bearer …'}})│
└──────────────────────────────┬─────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────┐
│  FastAPI backend (agents/src/onehealth_agents/api/)            │
│                                                                │
│   • verify JWT against Supabase JWKS                          │
│   • look up user_id in auth.users (Postgres)                  │
│   • run the agent chain from plan/03                          │
│   • write observation to DuckLake (precise zone or public)    │
└────────────────────────────────────────────────────────────────┘
```

The React app **never** talks to our backend for sign-in. It uses
the Supabase JS SDK directly, which handles every flow (email +
password, magic-link, three OAuth providers, password reset, email
verify, session refresh). The resulting JWT is then attached to
every call to our backend.

The backend doesn't trust the client. It validates each JWT against
Supabase's published JWKS, extracts the `sub` claim (the user id),
and looks up the user in the same Postgres database (Supabase Auth
keeps `auth.users` rows alongside our `public.*` tables).

## Anonymous → authenticated transitions

The Intake API supports four transition flows:

1. **Anonymous submit, anonymous claim** *(default)*
   ```
   POST /v1/reports                  → { observation_id, claim_token }
   GET  /v1/reports/{id}             ← Authorization: Claim <token>
   PATCH /v1/reports/{id}/profile    ← Authorization: Claim <token>
   ```

2. **Anonymous submit, attach to account after sign-in**
   ```
   POST /v1/reports                  → { observation_id, claim_token }
   ... user later signs in ...
   POST /v1/auth/claim               { claim_token }
                                     → 204; observation_id is now linked
                                       to auth.user_id
   ```

3. **Authenticated submit, no attachment**
   ```
   POST /v1/reports                  ← Authorization: Bearer <jwt>
                                     payload includes { attach: false }
                                     → { observation_id, claim_token }
                                     ← observation has no user_id link
   ```
   This is the **workplace-whistleblower** case: a signed-in user
   files an Environmental report anonymously even though we know who
   they are. The server still returns a claim_token so they can
   manage the report later (e.g. add a photo) without ever having
   touched their account.

4. **Authenticated submit, attached to account**
   ```
   POST /v1/reports                  ← Authorization: Bearer <jwt>
                                     payload includes { attach: true }
                                     → { observation_id }
                                     ← observation.user_id = current user
   ```

## OAuth provider notes

### Google (Gmail)

- OAuth 2.0 + OIDC.
- We request the `email` + `openid` scopes only. No `profile.read`,
  no Drive, no Calendar, no Contacts.
- Email verification is implicit (Google verifies before issuing).

### Facebook

- OAuth 2.0.
- We request `email` only. No `public_profile` photo, no Friends
  list, no Pages.
- Email verification is implicit.

### Apple (Sign in with Apple)

- OAuth 2.0 + JWT.
- We support **private email relay** (`<random>@privaterelay.appleid.com`).
  These addresses are stored exactly like any other; relay forwarding
  is Apple's concern.
- Apple's flow only returns the user's name on the FIRST sign-in.
  We capture it then, optional. Subsequent sign-ins return only the
  sub-id and email.
- The button must appear at least as prominently as the other social
  buttons (Guideline 4.8). The sign-in page renders Apple first.

### Email + password

- Argon2id hashing (Supabase Auth default).
- Minimum 12 characters; no upper/lower/number/symbol theatre.
- Password-reset and email-verify use Supabase's transactional
  email sender (configurable to SendGrid / Resend / Postmark; ours
  defaults to Resend).

### Magic-link email

- One-time link, expires in 1 hour.
- Same email sender as password-reset.
- Useful for low-friction first-time use — the user enters their
  email, clicks the link, and is in.

## Data model

Supabase Auth gives us `auth.users` for free. We add a thin layer
on top in `public.profile`:

```sql
-- schema/deep/auth.sql (Phase 07.1 deliverable)
CREATE TABLE public.profile (
  user_id              uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name         text,
  home_zip             text CHECK (home_zip ~ '^[0-9]{5}$'),
  primary_language     text,
  accessibility_needs  text[],
  contact_email_opt_in    boolean NOT NULL DEFAULT false,
  contact_sms_phone       text,
  contact_sms_opt_in      boolean NOT NULL DEFAULT false,
  precise_location_consent boolean NOT NULL DEFAULT false,
  share_photo_gps_animal_env boolean NOT NULL DEFAULT false,
  share_photo_gps_human   boolean NOT NULL DEFAULT false,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- One-to-many: a user can attach many observations; an observation
-- has at most one user_id link. ON DELETE SET NULL preserves the
-- observation under right-to-erasure.
ALTER TABLE public.observation
  ADD COLUMN user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL;
```

Row-level security policies:

```sql
-- A user can read / update only their own profile row.
ALTER TABLE public.profile ENABLE ROW LEVEL SECURITY;
CREATE POLICY profile_self_read   ON public.profile FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY profile_self_update ON public.profile FOR UPDATE USING (auth.uid() = user_id);

-- A user can read only their own attached observations.
CREATE POLICY observation_self_read
  ON public.observation
  FOR SELECT
  USING (auth.uid() = user_id);
```

Agency dashboards (MCDPH, ADHS, etc.) get separate Postgres roles
that bypass RLS for governance-board-approved cohort queries; the
tribal-data row-level suppression from plan/02 stays in force.

## API surface added to the spec

[`api/openapi.yaml`](../api/openapi.yaml) gets a new `auth` tag with:

| Endpoint | Purpose |
|---|---|
| `GET /v1/auth/me` | Current user (JWT-authenticated). Returns the user and their `public.profile` row. |
| `PATCH /v1/auth/me` | Update the user's profile. Per-field consent toggles default off; setting a value implies opt-in. |
| `DELETE /v1/auth/me` | Right to erasure. Cascades to detach (NOT delete) attached observations. |
| `POST /v1/auth/sign-out` | Invalidate the current session. (The Supabase JS SDK handles the local clear; this endpoint exists so server-side audit logs see the event.) |
| `POST /v1/auth/claim` | Attach a `claim_token` (from a previously anonymous report) to the current user. Optional and idempotent. |

The sign-in / sign-up / OAuth dance itself is **not** in our spec —
the React client talks to Supabase directly for that. Our spec
documents only the part our backend serves.

## React UI scaffold

| Path | Component |
|---|---|
| `app/src/lib/auth.ts` | Supabase JS client + `useSession()` hook + `useUser()`. |
| `app/src/components/AuthProvider.tsx` | React context that subscribes to `supabase.auth.onAuthStateChange` and exposes the session to the rest of the app. |
| `app/src/app/sign-in/page.tsx` | Sign-in / sign-up page. Apple first, then Google, then Facebook. Email + magic-link below. |
| `app/src/app/auth/callback/page.tsx` | OAuth-callback handler. Reads the URL hash, calls `supabase.auth.getSession()`, redirects to `/` or to the `next` query param. |
| `app/src/app/account/page.tsx` | Authenticated settings page. |
| `app/src/app/account/reports/page.tsx` | Attached-reports list. |

The landing page (`/`) reads `useSession()` and shows a "Sign in"
button when signed out, or a small chip with the user's display
name when signed in. The three-button picker is unchanged either
way.

## Migration plan

- **07.1** (this commit): plan doc + OpenAPI auth endpoints + FastAPI
  backend scaffold + React sign-in / account / callback shell. The
  Supabase project is configured externally — Supabase URL + anon
  key land in `.env.local` (not committed).
- **07.2**: Wire `/v1/auth/me`, `/v1/auth/claim`, `/v1/auth/sign-out`
  to real Supabase JWT validation. Add `schema/deep/auth.sql` with
  the `public.profile` table and RLS policies. Apple-private-relay
  smoke test.
- **07.3**: Email-marketing opt-in (off by default), right-to-erasure
  audit log, tribal-data suppression policy applied to
  `public.observation` RLS.
- **07.4**: Self-hosted Supabase migration playbook (for v1 if needed).

## Open questions

1. **Magic-link rate-limiting.** What's the per-IP send budget that
   keeps email-sender costs bounded without blocking legitimate
   first-time users in noisy networks (NAT, mobile carriers)?
2. **Cross-device session.** Should a sign-in on a new device
   invalidate older sessions, or stay additive? The reporter audience
   skews "one phone forever" but CHWs may share tablets.
3. **Account merge.** If a user signs up with email, then later signs
   in with Google using the same address, do we merge? Default
   *yes* (Supabase Auth handles this via "linking"), but we should
   confirm the UX.
4. **App Store metadata.** Apple's review requires a demo account
   that can complete the full flow. Plan how that account looks
   (test data only, clearly marked).
