// today/shared/geo-strip.js
// Auto-detect a coarse Arizona county from navigator.geolocation, with a
// no-network fallback using a small list of county centroids and rough
// bounding boxes. The page degrades gracefully:
//
//   1. If geolocation succeeds AND the point falls in a known county's
//      bbox, the hero card swaps "Arizona" for that county name.
//   2. If geolocation is denied / unsupported / times out, the page
//      stays in statewide mode (the default for the noscript fallback
//      and the first paint).
//   3. The user can override at any time via the <select> dropdown.
//
// We deliberately do NOT call a remote geocoder -- this page is a
// public, no-PII surface, and shipping the user's lat/lon to a third
// party would betray the privacy promise in the page footer.

import { requestLocation } from '../../app/shared/geo.js';

// Approximate centroids + axis-aligned bounding boxes for the 15 AZ
// counties. Boxes are intentionally generous so a point inside the
// county polygon will always match; boxes overlap on the edges but
// since we test in the same order each time, the result is stable.
// Source: US Census TIGER county bbox, rounded to 2 decimals.
export const AZ_COUNTIES = [
  { id: 'maricopa',  name: 'Maricopa County',  bbox: [-113.34, 32.50, -111.04, 34.05], lat: 33.45, lon: -112.07 },
  { id: 'pima',      name: 'Pima County',      bbox: [-113.34, 31.42, -110.45, 32.51], lat: 32.22, lon: -110.97 },
  { id: 'pinal',     name: 'Pinal County',     bbox: [-112.04, 32.43, -110.45, 33.65], lat: 32.90, lon: -111.34 },
  { id: 'yuma',      name: 'Yuma County',      bbox: [-114.82, 32.50, -113.33, 33.78], lat: 32.73, lon: -114.62 },
  { id: 'mohave',    name: 'Mohave County',    bbox: [-114.82, 34.26, -113.33, 37.00], lat: 35.19, lon: -114.05 },
  { id: 'coconino',  name: 'Coconino County',  bbox: [-113.34, 34.26, -111.06, 37.00], lat: 35.19, lon: -111.65 },
  { id: 'navajo',    name: 'Navajo County',    bbox: [-111.07, 34.00, -109.78, 37.00], lat: 35.27, lon: -110.32 },
  { id: 'apache',    name: 'Apache County',    bbox: [-109.78, 33.78, -109.04, 37.00], lat: 35.40, lon: -109.49 },
  { id: 'yavapai',   name: 'Yavapai County',   bbox: [-113.34, 33.78, -111.65, 35.06], lat: 34.54, lon: -112.47 },
  { id: 'gila',      name: 'Gila County',      bbox: [-111.65, 33.10, -110.45, 34.41], lat: 33.80, lon: -110.81 },
  { id: 'graham',    name: 'Graham County',    bbox: [-110.46, 32.42, -109.21, 33.41], lat: 32.93, lon: -109.89 },
  { id: 'greenlee',  name: 'Greenlee County',  bbox: [-109.50, 32.42, -109.04, 33.78], lat: 33.10, lon: -109.24 },
  { id: 'cochise',   name: 'Cochise County',   bbox: [-110.46, 31.32, -109.04, 32.43], lat: 31.73, lon: -109.96 },
  { id: 'santa_cruz',name: 'Santa Cruz County',bbox: [-111.36, 31.32, -110.45, 31.79], lat: 31.52, lon: -110.81 },
  { id: 'la_paz',    name: 'La Paz County',    bbox: [-114.62, 33.31, -113.33, 34.27], lat: 33.73, lon: -113.95 },
];

const AZ_BBOX = [-114.82, 31.32, -109.04, 37.00];

const STORAGE_KEY = 'today.county';

export function isInArizona(lat, lon) {
  const [w, s, e, n] = AZ_BBOX;
  return lon >= w && lon <= e && lat >= s && lat <= n;
}

export function countyForPoint(lat, lon) {
  if (!isInArizona(lat, lon)) return null;
  for (const c of AZ_COUNTIES) {
    const [w, s, e, n] = c.bbox;
    if (lon >= w && lon <= e && lat >= s && lat <= n) return c;
  }
  return null;
}

export function countyById(id) {
  return AZ_COUNTIES.find((c) => c.id === id) || null;
}

export function savedCounty() {
  try {
    const id = localStorage.getItem(STORAGE_KEY);
    return id ? countyById(id) : null;
  } catch (_) { return null; }
}

export function saveCounty(id) {
  try { id ? localStorage.setItem(STORAGE_KEY, id)
           : localStorage.removeItem(STORAGE_KEY); }
  catch (_) {}
}

/**
 * Try to detect the user's county via the browser's geolocation API.
 * Resolves with { source, county } where source is one of:
 *   'gps' | 'manual' | 'saved' | 'denied' | 'unsupported' | 'outside-az'
 *
 * Honours a previously-saved manual override (returned with source='saved').
 */
export async function detectCounty({ skipGps = false } = {}) {
  const saved = savedCounty();
  if (saved) return { source: 'saved', county: saved };
  if (skipGps) return { source: 'denied', county: null };

  const loc = await requestLocation({ timeoutMs: 6000 });
  if (loc.source !== 'gps') return { source: loc.source, county: null };
  if (!isInArizona(loc.lat, loc.lon)) {
    return { source: 'outside-az', county: null };
  }
  const county = countyForPoint(loc.lat, loc.lon);
  return { source: 'gps', county };
}

/**
 * Mount the geo strip inside a container. Renders a <select> with all
 * 15 counties + a "Statewide" option, kicks off detection in the
 * background, and fires `onChange(county)` whenever the active county
 * changes (including when auto-detect succeeds).
 *
 * The container is expected to already contain a <select id> and a
 * status span. The select stays visible without JS so the noscript
 * fallback still lets people change county manually via the URL hash.
 */
export function mountGeoStrip({ select, status, onChange, labels }) {
  const L = Object.assign({
    statewide:  'Arizona (statewide)',
    detecting:  'Locating you…',
    detected:   'Showing {county}.',
    saved:      'Showing {county} (saved).',
    denied:     'Location not shared — showing statewide.',
    unsupported:'Location unavailable — showing statewide.',
    outside:    'You appear to be outside Arizona — showing statewide.',
    pick:       'Change county',
    cleared:    'Showing statewide.',
  }, labels || {});

  // Populate the select.
  select.innerHTML = '';
  const blank = document.createElement('option');
  blank.value = '';
  blank.textContent = L.statewide;
  select.appendChild(blank);
  for (const c of AZ_COUNTIES) {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = c.name;
    select.appendChild(opt);
  }

  const setStatus = (msg) => {
    if (status) status.textContent = msg;
  };

  const applyCounty = (county, src) => {
    select.value = county ? county.id : '';
    if (!county) {
      setStatus(L.cleared);
    } else if (src === 'gps') {
      setStatus(L.detected.replace('{county}', county.name));
    } else if (src === 'saved') {
      setStatus(L.saved.replace('{county}', county.name));
    } else {
      setStatus(L.detected.replace('{county}', county.name));
    }
    try { onChange && onChange(county, src); } catch (e) { console.error(e); }
  };

  select.addEventListener('change', () => {
    const id = select.value;
    if (id) {
      saveCounty(id);
      applyCounty(countyById(id), 'manual');
    } else {
      saveCounty(null);
      applyCounty(null, 'manual');
    }
  });

  // Kick off detection. We keep the page usable while we wait.
  setStatus(L.detecting);
  detectCounty().then((res) => {
    if (res.county) {
      // If we got a fresh GPS hit, don't overwrite an explicit saved choice.
      if (res.source === 'saved') {
        applyCounty(res.county, 'saved');
      } else {
        applyCounty(res.county, res.source);
      }
    } else if (res.source === 'outside-az') {
      setStatus(L.outside);
    } else if (res.source === 'unsupported') {
      setStatus(L.unsupported);
    } else {
      setStatus(L.denied);
    }
  }).catch(() => {
    setStatus(L.denied);
  });

  return { applyCounty };
}
