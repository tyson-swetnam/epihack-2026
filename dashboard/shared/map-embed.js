/* dashboard/shared/map-embed.js
 *
 * Lazy-loads MapLibre GL from the same CDN as map/index.html and
 * renders an Arizona-bounded basemap with the pins for whichever
 * GeoJSON payload the caller hands in. Pins click through to the
 * source kg_node_id and, when present, an MCP receipt URL.
 *
 * Lazy-loaded so that audience landing pages don't pay the MapLibre
 * cost until the analyst scrolls or expands the map.
 */

const MAPLIBRE_JS  = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js';
const MAPLIBRE_CSS = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css';
const BASEMAP_STYLE = 'https://tiles.openfreemap.org/styles/positron';
const AZ_BOUNDS = [[-117, 30.5], [-106, 38]];
const AZ_CENTER = [-111.7, 34.3];

let runtimeLoad = null;

function loadMapLibre() {
  if (runtimeLoad) return runtimeLoad;
  runtimeLoad = new Promise((resolve, reject) => {
    if (window.maplibregl) { resolve(window.maplibregl); return; }
    const css = document.createElement('link');
    css.rel = 'stylesheet';
    css.href = MAPLIBRE_CSS;
    document.head.appendChild(css);

    const js = document.createElement('script');
    js.src = MAPLIBRE_JS;
    js.async = true;
    js.onload  = () => resolve(window.maplibregl);
    js.onerror = () => reject(new Error('MapLibre runtime failed to load'));
    document.head.appendChild(js);
  });
  return runtimeLoad;
}

/**
 * Mount the map into a container with a deferred-render placeholder.
 *
 * @param {HTMLElement} mount      .map-shell container
 * @param {object} opts
 * @param {object} opts.geojson    FeatureCollection of points
 * @param {string} [opts.colorBy]  property to color by ("severity"|"pathogen"|...)
 * @param {string} [opts.center]   focus on a feature: "kg.node.<id>"
 * @param {number} [opts.zoom]
 * @returns {Promise<object>}      MapLibre Map instance (or null on failure)
 */
export async function mountMapEmbed(mount, opts) {
  if (!mount) return null;
  opts = opts || {};
  mount.innerHTML = '';

  // ---- Pre-render placeholder + lazy-trigger button -------------------
  const placeholder = document.createElement('div');
  placeholder.className = 'map-pending';
  const note = document.createElement('div');
  const featureCount = opts.geojson && opts.geojson.features
    ? opts.geojson.features.length : 0;
  note.textContent =
    `MapLibre map of ${featureCount} observation pins (AZ-bounded). ` +
    `Click below to load the map runtime from the CDN.`;
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'btn secondary';
  btn.textContent = 'Load map';
  placeholder.appendChild(note);
  placeholder.appendChild(btn);
  mount.appendChild(placeholder);

  // Auto-load if the page already cleared the lazy flag (e.g. analyst
  // opted-in via the URL hash).
  if (window.location.hash === '#map') {
    queueMicrotask(() => btn.click());
  }

  return new Promise((resolve) => {
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      btn.textContent = 'Loading…';
      try {
        const maplibregl = await loadMapLibre();
        mount.removeChild(placeholder);

        const mapEl = document.createElement('div');
        mapEl.style.position = 'absolute';
        mapEl.style.inset = '0';
        mount.appendChild(mapEl);

        const toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'map-panel-toggle';
        toggle.setAttribute('aria-label', 'Toggle fullscreen map');
        toggle.title = 'Toggle fullscreen map';
        toggle.textContent = '⛶';
        toggle.addEventListener('click', () => {
          mount.classList.toggle('fullscreen');
          setTimeout(() => map && map.resize(), 250);
        });
        mount.appendChild(toggle);

        const map = new maplibregl.Map({
          container: mapEl,
          style: BASEMAP_STYLE,
          center: AZ_CENTER,
          zoom: 6,
          maxBounds: AZ_BOUNDS,
          cooperativeGestures: false
        });
        map.addControl(new maplibregl.NavigationControl({showCompass:false}), 'top-right');
        map.addControl(new maplibregl.ScaleControl({maxWidth:120, unit:'imperial'}), 'bottom-left');

        map.on('load', () => {
          const gj = opts.geojson || { type: 'FeatureCollection', features: [] };
          map.addSource('obs', { type: 'geojson', data: gj });
          map.addLayer({
            id: 'obs-pts',
            source: 'obs',
            type: 'circle',
            paint: {
              'circle-radius': ['interpolate', ['linear'], ['zoom'], 5, 6, 10, 11],
              'circle-color': colorExpression(opts.colorBy),
              'circle-stroke-color': '#fff',
              'circle-stroke-width': 1.5,
              'circle-opacity': 0.9
            }
          });
          map.on('click', 'obs-pts', (e) => popup(maplibregl, map, e));
          map.on('mouseenter', 'obs-pts', () => map.getCanvas().style.cursor = 'pointer');
          map.on('mouseleave', 'obs-pts', () => map.getCanvas().style.cursor = '');
        });

        new ResizeObserver(() => map.resize()).observe(mount);
        resolve(map);
      } catch (err) {
        placeholder.innerHTML = '';
        placeholder.textContent = `Map runtime failed to load: ${err.message}`;
        resolve(null);
      }
    });
  });
}

function colorExpression(colorBy) {
  if (colorBy === 'severity') {
    return ['match', ['get', 'severity'],
      'urgent', '#C0392B',
      'alert',  '#E84A2B',
      'watch',  '#E6A038',
      /* default */ '#1F3A93'
    ];
  }
  if (colorBy === 'pathogen') {
    return ['match', ['get', 'pathogen'],
      'hantavirus', '#6A1B9A',
      'plague',     '#4A148C',
      'wnv',        '#1F6FB0',
      'slev',       '#1F3A93',
      'heat',       '#E84A2B',
      'hpai',       '#2C5F2D',
      /* default */ '#555'
    ];
  }
  return '#1F3A93';
}

function popup(maplibregl, map, e) {
  const f = e.features[0];
  const p = f.properties || {};
  const rows = [];
  if (p.label)       rows.push(`<div class="popup-kv">${escape(p.label)}</div>`);
  if (p.pathogen)    rows.push(`<div class="popup-kv">Pathogen: ${escape(p.pathogen)}</div>`);
  if (p.county)      rows.push(`<div class="popup-kv">County: ${escape(p.county)}</div>`);
  if (p.severity)    rows.push(`<div class="popup-kv">Severity: ${escape(p.severity)}</div>`);
  if (p.detected_at) rows.push(`<div class="popup-kv">Detected: ${escape(p.detected_at)}</div>`);
  if (p.kg_node_id)  rows.push(`<div class="popup-kv"><code>${escape(p.kg_node_id)}</code></div>`);
  const link = p.kg_node_id
    ? `<a class="popup-link" href="../../map/index.html#${encodeURIComponent(p.kg_node_id)}">Open in main map</a>`
    : '';
  const html = `<div class="popup-title">${escape(p.title || p.label || 'Observation')}</div>` +
               rows.join('') + link;
  new maplibregl.Popup({ offset: 12, maxWidth: '300px' })
    .setLngLat(e.lngLat)
    .setHTML(html)
    .addTo(map);
}

function escape(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}
