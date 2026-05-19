// shared/geo.js
// Promise wrapper around navigator.geolocation with a manual-entry
// fallback so flows still work when the user denies location.
//
// Usage:
//   import { requestLocation, isPlausibleZip } from '../shared/geo.js';
//   const loc = await requestLocation({ timeoutMs: 8000 });
//   // loc -> { source: 'gps', lat, lon, accuracy } or
//   //        { source: 'denied', error } or
//   //        { source: 'unsupported' }

export function requestLocation({ timeoutMs = 8000 } = {}) {
  return new Promise((resolve) => {
    if (!('geolocation' in navigator)) {
      resolve({ source: 'unsupported' });
      return;
    }
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      resolve(value);
    };

    const timer = setTimeout(
      () => finish({ source: 'denied', error: 'timeout' }),
      timeoutMs + 500
    );

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        clearTimeout(timer);
        finish({
          source: 'gps',
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy
        });
      },
      (err) => {
        clearTimeout(timer);
        finish({
          source: 'denied',
          error: err && err.message ? err.message : 'permission denied'
        });
      },
      { enableHighAccuracy: false, maximumAge: 60_000, timeout: timeoutMs }
    );
  });
}

// Loose Arizona-ZIP sanity check. AZ ZIPs are 850xx, 852xx, 853xx, 855xx,
// 856xx, 857xx, 859xx, 860xx — but we accept any 5-digit US ZIP and let
// the backend do the real validation.
export function isPlausibleZip(z) {
  return typeof z === 'string' && /^\d{5}(-\d{4})?$/.test(z.trim());
}
