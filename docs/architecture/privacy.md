# Privacy contract

!!! info "Source"
    The privacy contract is encoded in code (`agents/src/onehealth_agents/validation.py`)
    and in `api/openapi.yaml` schema constraints — not just docs. The
    canonical narrative is the "Privacy contract" section of
    [`CLAUDE.md`](https://github.com/tyson-swetnam/epihack-2026/blob/main/CLAUDE.md).

The contract is load-bearing — PRs touching `agents/`,
`mcp/<server>/`, or `schema/deep/*.sql` must walk the privacy checklist
at the bottom of [`CONTRIBUTING.md`](../about/contributing.md) or are
blocked regardless of code review.

## Six rules

1. **No precise lat/lon over the wire.** `CoarseLocation` accepts `zip`
   or `grid_id` (1 km cell) only. Client coarsens via
   `app/src/lib/coarse-geo.ts`; server re-coarsens before persisting.

2. **EXIF GPS stripped before upload** by
   `app/src/lib/exif-stripper.ts`; server rejects with
   `photo_exif_gps_present` (422) if it slips through.

3. **Tribal data is suppressed by default.** Opt-in lives in
   `consent_profile` rows in the kg, consulted by ValidationAgent at
   write time.

4. **Triage is routing, not diagnosis.** A regex output-guard on the
   server rejects `you have …`, `you may have …`, `diagnos*`. The
   client renders only the `next_action` enum, never free-form LLM copy
   as a verdict.

5. **Audit log stores SHA-256 digests** of canonicalized JSON, never
   raw observations. No PII in `agent_run` rows.

6. **Cluster output uses ZCTA-week / ZCTA-2h aggregations**, never
   individual observations.

## Where it's enforced

| Rule | Enforcement |
|---|---|
| 1 | `validation.py:CoarseLocation`, `api/openapi.yaml#/components/schemas/CoarseLocation` |
| 2 | `app/src/lib/exif-stripper.ts`, `validation.py:_reject_exif_gps` |
| 3 | `agents/src/onehealth_agents/validation.py:_check_tribal_consent` |
| 4 | `validation.py:_check_triage_output_guard` (regex) |
| 5 | `agents/src/onehealth_agents/audit.py` |
| 6 | `agents/src/onehealth_agents/cluster.py` |
