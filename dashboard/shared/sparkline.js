/* dashboard/shared/sparkline.js
 *
 * Pure-SVG sparkline component for the analyst case-count tables.
 * No dependencies; renders into a fixed-size inline <svg>. The host
 * stylesheet (dashboard/shared/style.css) supplies the colours.
 *
 * Usage:
 *
 *   import { renderSparkline } from '../shared/sparkline.js';
 *   const td = row.querySelector('td.spark');
 *   td.appendChild(renderSparkline([1, 3, 2, 4, 6, 5, 8]));
 */

const W = 110;
const H = 28;
const PAD_X = 2;
const PAD_Y = 3;

/**
 * Render a sparkline SVG for the given numeric series.
 *
 * @param {number[]} values    must contain >= 2 finite numbers
 * @param {object} [opts]
 * @param {string} [opts.title]
 * @returns {SVGSVGElement}
 */
export function renderSparkline(values, opts) {
  opts = opts || {};
  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('preserveAspectRatio', 'none');
  svg.classList.add('sparkline');
  svg.setAttribute('role', 'img');

  const clean = (values || []).map(v => Number(v)).filter(v => Number.isFinite(v));
  if (clean.length < 2) {
    svg.classList.add('flat');
    const t = document.createElementNS(svgNS, 'title');
    t.textContent = opts.title || 'Insufficient data';
    svg.appendChild(t);
    const line = document.createElementNS(svgNS, 'path');
    line.setAttribute('class', 'spark-line');
    line.setAttribute('d', `M${PAD_X},${H/2} L${W-PAD_X},${H/2}`);
    svg.appendChild(line);
    return svg;
  }

  const min = Math.min.apply(null, clean);
  const max = Math.max.apply(null, clean);
  const range = (max - min) || 1;

  const n = clean.length;
  const dx = (W - 2 * PAD_X) / (n - 1);

  // Trend classification for stroke colour.
  const first = clean[0];
  const last  = clean[n - 1];
  const delta = last - first;
  const trend = Math.abs(delta) / (range || 1) < 0.05 ? 'flat'
              : delta > 0 ? 'up' : 'down';
  svg.classList.add(trend);

  const points = clean.map((v, i) => {
    const x = PAD_X + i * dx;
    const y = H - PAD_Y - ((v - min) / range) * (H - 2 * PAD_Y);
    return [x, y];
  });

  const linePath = points.map((p, i) =>
    (i === 0 ? 'M' : 'L') + p[0].toFixed(2) + ',' + p[1].toFixed(2)
  ).join(' ');

  const areaPath = linePath
    + ` L${(W - PAD_X).toFixed(2)},${(H - PAD_Y).toFixed(2)}`
    + ` L${PAD_X.toFixed(2)},${(H - PAD_Y).toFixed(2)} Z`;

  const area = document.createElementNS(svgNS, 'path');
  area.setAttribute('class', 'spark-area');
  area.setAttribute('d', areaPath);
  svg.appendChild(area);

  const line = document.createElementNS(svgNS, 'path');
  line.setAttribute('class', 'spark-line');
  line.setAttribute('d', linePath);
  svg.appendChild(line);

  const lastPt = points[points.length - 1];
  const dot = document.createElementNS(svgNS, 'circle');
  dot.setAttribute('class', 'spark-last');
  dot.setAttribute('cx', lastPt[0].toFixed(2));
  dot.setAttribute('cy', lastPt[1].toFixed(2));
  dot.setAttribute('r', '2.2');
  svg.appendChild(dot);

  const title = document.createElementNS(svgNS, 'title');
  title.textContent = opts.title
    || `min=${min}, max=${max}, latest=${last} (${trend})`;
  svg.appendChild(title);

  return svg;
}
