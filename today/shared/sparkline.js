// today/shared/sparkline.js
// Pure-SVG sparkline. No dependencies. The dashboard/ folder doesn't
// exist yet (Phase 3 will ship it), so this is the canonical
// implementation -- once dashboard/shared/sparkline.js lands, both
// pages can import from one source.
//
// Usage:
//   import { renderSparkline } from './sparkline.js';
//   renderSparkline(hostEl, [3, 4, 7, 12], {
//     width: 120, height: 32, ariaLabel: 'WNV positivity trend'
//   });

const DEFAULTS = {
  width: 120,
  height: 32,
  stroke: '#C0392B',
  fill: 'rgba(192,57,43,.10)',
  pad: 2,
  showLast: true,
  ariaLabel: '',
};

export function renderSparkline(host, values, opts = {}) {
  const o = Object.assign({}, DEFAULTS, opts);
  if (!host) return;

  const xs = (values || []).map(Number).filter((v) => Number.isFinite(v));
  if (xs.length < 2) {
    host.innerHTML = `<span class="muted small">—</span>`;
    return;
  }

  const min = Math.min(...xs, 0);
  const max = Math.max(...xs, min + 1);
  const span = max - min || 1;
  const innerW = o.width  - o.pad * 2;
  const innerH = o.height - o.pad * 2;
  const step = innerW / (xs.length - 1);

  const pts = xs.map((v, i) => {
    const x = o.pad + i * step;
    const y = o.pad + innerH - ((v - min) / span) * innerH;
    return [x, y];
  });

  const path = pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
  const area = `${path} L${o.pad + innerW} ${o.pad + innerH} L${o.pad} ${o.pad + innerH} Z`;
  const [lx, ly] = pts[pts.length - 1];

  const dir = xs[xs.length - 1] > xs[0] ? 'up'
            : xs[xs.length - 1] < xs[0] ? 'down'
            : 'flat';

  const label = o.ariaLabel
    ? `${o.ariaLabel}: ${xs.join(', ')}; trend ${dir}.`
    : `Sparkline ${xs.join(', ')}; trend ${dir}.`;

  host.innerHTML = `
    <svg class="spark" width="${o.width}" height="${o.height}"
         viewBox="0 0 ${o.width} ${o.height}"
         role="img" aria-label="${escapeXml(label)}"
         data-trend="${dir}">
      <path d="${area}" fill="${o.fill}" stroke="none"></path>
      <path d="${path}" fill="none" stroke="${o.stroke}" stroke-width="1.5"
            stroke-linejoin="round" stroke-linecap="round"></path>
      ${o.showLast ? `<circle cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="2.4" fill="${o.stroke}"></circle>` : ''}
    </svg>
  `;
}

function escapeXml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}
