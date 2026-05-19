// shared/coarse-geo.js
//
// Location coarsening helpers for the One Health reporting flows.
//
// Hard rule (plan/06-mobile-app.md): any value that hits public.observation
// is coarsened to ZIP (≈ 5 km²) or a 1 km grid cell, whichever is coarser.
// The original precise coordinates only ever live in precise.observation,
// gated by an explicit consent token.
//
// This module is a thin client-side helper; the Intake Agent re-runs the
// same coarsening server-side as defence in depth. Never trust the client.

/**
 * Coarsen a {lat, lon} to a 1 km grid cell. We snap to the nearest
 * 0.01° in latitude (≈ 1.11 km) and adjust the longitude step by
 * cos(lat) so the cell stays roughly square at AZ latitudes.
 *
 * Returns:
 *   { lat: number, lon: number,
 *     grid_id: string,                // 'g1km:33.45,-112.07' (stable for snap)
 *     resolution_m: number }
 */
export function coarsenLatLon({ lat, lon }) {
  if (typeof lat !== 'number' || typeof lon !== 'number') {
    throw new Error('coarsenLatLon: lat/lon must be numbers');
  }
  const latStep = 0.01;                            // ~1.11 km
  const lonStep = 0.01 / Math.max(0.2, Math.cos(lat * Math.PI / 180));
  const snapLat = Math.round(lat / latStep) * latStep;
  const snapLon = Math.round(lon / lonStep) * lonStep;
  // Round display to two decimals; underlying snap is exact.
  const lat2 = Number(snapLat.toFixed(2));
  const lon2 = Number(snapLon.toFixed(2));
  return {
    lat: lat2,
    lon: lon2,
    grid_id: `g1km:${lat2},${lon2}`,
    resolution_m: 1000,
  };
}

/**
 * Format a coarse location for the UI. We deliberately avoid leaking
 * extra decimal places onto the screen — users have been known to
 * screenshot the consent screen, and the screen shouldn't carry
 * higher resolution than what we'll persist.
 */
export function formatCoarse({ lat, lon }) {
  return `${lat.toFixed(2)}°, ${lon.toFixed(2)}°`;
}

/**
 * Normalise a US ZIP-code string (5-digit or ZIP+4) and return just the
 * 5-digit prefix. ZIP-level resolution averages ≈ 5 km² in AZ urban
 * areas (much larger in rural counties), which is coarser than the
 * 1 km grid above — so a user-supplied ZIP is always acceptable.
 *
 * Returns null for anything that doesn't parse as a US ZIP.
 */
export function normaliseZip(raw) {
  if (typeof raw !== 'string') return null;
  const m = raw.trim().match(/^(\d{5})(?:-?\d{4})?$/);
  return m ? m[1] : null;
}
