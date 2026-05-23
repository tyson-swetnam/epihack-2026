# Privacy & EXIF stripping

!!! note "Stub"
    Authored in Phase 3. Source: `app/src/lib/exif-stripper.ts`,
    `app/src/lib/coarse-geo.ts`.

The mobile client is responsible for stripping EXIF GPS before upload
and coarsening lat/lon to ZIP or 1 km grid before submission. The
server re-validates on receipt:

- EXIF present → HTTP 422 with code `photo_exif_gps_present`.
- Precise lat/lon present → HTTP 422 with code `precise_geo_present`.

See the full [Privacy contract](../architecture/privacy.md).
