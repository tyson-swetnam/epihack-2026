# Reporting-app pages tour

!!! note "Stub"
    Authored in Phase 3. Screenshots from Phase 5.

The Next.js 16 app has these top-level routes (in `app/src/app/`):

| Route | Purpose | Phase |
|---|---|---|
| `/` | Anonymous landing — "Report a sighting" + "Find a cool-off spot" | 0 |
| `/report/tick` | Tick mail-in flow | 1 |
| `/report/heat` | Heat / heat-strain report | 1 |
| `/report/animal` | Unusual animal-health event | 1 |
| `/report/environmental` | Standing water / vector-habitat report | 1 |
| `/cool-off` | Cooling-center finder | 0 |
| `/sign-in` | Supabase magic-link sign-in (optional) | 1 |
| `/profile` | Profile enrichment (household, pets, outdoor work) | 1 |
| `/account` | Account management | 1 |
| `/dashboard` | Personal dashboard | 1 |

See [Privacy & EXIF stripping](privacy.md) and [Offline retry queue](offline.md)
for the cross-cutting behaviours.
