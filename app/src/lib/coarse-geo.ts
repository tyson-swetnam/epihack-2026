/**
 * Location coarsening for the One Health reporting flows.
 *
 * Hard rule (plan/06-mobile-app.md): any value that hits
 * public.observation is coarsened to ZIP (≈ 5 km²) or a 1 km grid
 * cell, whichever is coarser. The Intake Agent re-runs the same
 * coarsening server-side — never trust the client.
 */

export interface CoarseCell {
  lat: number;
  lon: number;
  /** Stable id for the cell, e.g. 'g1km:33.45,-112.07'. */
  grid_id: string;
  resolution_m: number;
}

/**
 * Snap to a 1 km grid cell. We use a 0.01° latitude step (≈ 1.11 km)
 * and adjust the longitude step by cos(lat) so the cell stays
 * roughly square at AZ latitudes.
 */
export function coarsenLatLon({
  lat,
  lon,
}: {
  lat: number;
  lon: number;
}): CoarseCell {
  if (typeof lat !== 'number' || typeof lon !== 'number') {
    throw new Error('coarsenLatLon: lat/lon must be numbers');
  }
  const latStep = 0.01;
  const lonStep = 0.01 / Math.max(0.2, Math.cos((lat * Math.PI) / 180));
  const snapLat = Math.round(lat / latStep) * latStep;
  const snapLon = Math.round(lon / lonStep) * lonStep;
  const lat2 = Number(snapLat.toFixed(2));
  const lon2 = Number(snapLon.toFixed(2));
  return {
    lat: lat2,
    lon: lon2,
    grid_id: `g1km:${lat2},${lon2}`,
    resolution_m: 1000,
  };
}

/** Two-decimal display string. Never higher resolution than the snap. */
export function formatCoarse({
  lat,
  lon,
}: {
  lat: number;
  lon: number;
}): string {
  return `${lat.toFixed(2)}°, ${lon.toFixed(2)}°`;
}

/**
 * Normalise a US ZIP-code input. Accepts a 5-digit ZIP or ZIP+4 and
 * returns the 5-digit prefix; returns null for anything else.
 */
export function normaliseZip(raw: string): string | null {
  if (typeof raw !== 'string') return null;
  const m = raw.trim().match(/^(\d{5})(?:-?\d{4})?$/);
  return m && m[1] ? m[1] : null;
}
