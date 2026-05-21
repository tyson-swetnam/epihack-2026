// today/shared/map-embed.js
// Lazy-loaded MapLibre wrapper that shows the wildlife-signals layer.
// We deliberately defer loading the MapLibre script + stylesheet until
// the host element scrolls into view, so phones on cellular don't pay
// the cost for users who never scroll past the heat panel.
//
// Public API:
//   mountMap(host, items, { intersect = true, lang = 'en' })
//   mountMap returns a Promise that resolves once the map has rendered.

const CDN_JS  = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js';
const CDN_CSS = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css';

const ICONS = {
  rodent:   '#7d4f1c',
  bird:     '#1f3a93',
  deer:     '#5d4037',
  tick:     '#962fbf',
  mosquito: '#2c5f2d',
  bat:      '#1a1a1a',
  bug:      '#c0392b',
  default:  '#e84a2b',
};

let _maplibrePromise = null;
function loadMapLibre() {
  if (_maplibrePromise) return _maplibrePromise;
  _maplibrePromise = new Promise((resolve, reject) => {
    if (typeof window !== 'undefined' && window.maplibregl) {
      resolve(window.maplibregl);
      return;
    }
    if (typeof document === 'undefined') {
      reject(new Error('no document'));
      return;
    }
    const link = document.createElement('link');
    link.rel  = 'stylesheet';
    link.href = CDN_CSS;
    document.head.appendChild(link);

    const s = document.createElement('script');
    s.src   = CDN_JS;
    s.async = true;
    s.onload  = () => resolve(window.maplibregl);
    s.onerror = () => reject(new Error('failed to load maplibre-gl'));
    document.head.appendChild(s);
  });
  return _maplibrePromise;
}

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}

function buildStyle() {
  // Plain raster style using OpenStreetMap tiles. Same style the
  // existing map/ folder uses for consistency.
  return {
    version: 8,
    sources: {
      osm: {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: '&copy; OpenStreetMap contributors',
      },
    },
    layers: [
      { id: 'osm', type: 'raster', source: 'osm', minzoom: 0, maxzoom: 19 },
    ],
  };
}

function fitBoundsTo(items, maplibregl) {
  const lats = items.map((i) => i.lat).filter(Number.isFinite);
  const lons = items.map((i) => i.lon).filter(Number.isFinite);
  if (!lats.length) return null;
  const minLat = Math.min(...lats), maxLat = Math.max(...lats);
  const minLon = Math.min(...lons), maxLon = Math.max(...lons);
  return new maplibregl.LngLatBounds([minLon, minLat], [maxLon, maxLat]);
}

/**
 * Mount the map. `host` must be a sized element; if not, we apply a
 * minimum height so the page never collapses to zero.
 */
export function mountMap(host, items, { intersect = true } = {}) {
  if (!host) return Promise.resolve();
  host.classList.add('today-map');
  if (!host.style.height && !host.offsetHeight) host.style.height = '280px';

  const draw = async () => {
    let maplibregl;
    try {
      maplibregl = await loadMapLibre();
    } catch (err) {
      host.innerHTML = `<p class="muted small">${escapeHtml(err.message)}. The list above is the data.</p>`;
      return;
    }
    const map = new maplibregl.Map({
      container: host,
      style: buildStyle(),
      center: [-111.65, 34.20],
      zoom: 5.5,
      attributionControl: true,
      cooperativeGestures: true,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');

    map.on('load', () => {
      const bounds = fitBoundsTo(items || [], maplibregl);
      if (bounds) map.fitBounds(bounds, { padding: 30, duration: 0, maxZoom: 8 });

      (items || []).forEach((it) => {
        if (!Number.isFinite(it.lat) || !Number.isFinite(it.lon)) return;
        const color = ICONS[it.icon] || ICONS.default;
        const el = document.createElement('button');
        el.type = 'button';
        el.className = 'today-marker';
        el.setAttribute('aria-label',
          `${it.label || it.species} in ${it.county || 'AZ'} on ${it.date}`);
        el.style.background = color;
        new maplibregl.Marker({ element: el })
          .setLngLat([it.lon, it.lat])
          .setPopup(new maplibregl.Popup({ offset: 12 }).setHTML(`
            <strong>${escapeHtml(it.label || it.species)}</strong><br>
            ${escapeHtml(it.species || '')}<br>
            <span style="color:#555">${escapeHtml(it.county || '')} &middot; ${escapeHtml(it.date || '')}</span>
            ${it.diagnosis ? `<br><em>${escapeHtml(it.diagnosis)}</em>` : ''}
          `))
          .addTo(map);
      });
    });
  };

  if (!intersect || typeof IntersectionObserver === 'undefined') {
    return draw();
  }
  return new Promise((resolve) => {
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting) {
          io.disconnect();
          draw().then(resolve);
          return;
        }
      }
    }, { rootMargin: '120px' });
    io.observe(host);
  });
}
