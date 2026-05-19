/**
 * Landing page — the three-button report picker.
 *
 * Anonymity defaults per plan/06-mobile-app.md:
 *   - human:         anonymous by default, opt-in clinician contact via profile
 *   - animal:        FULLY anonymous (workplace whistleblower scenarios)
 *   - environmental: FULLY anonymous (workplace whistleblower scenarios)
 */
import Link from 'next/link';

type ReportType = 'human' | 'animal' | 'environmental';

interface PickerCard {
  type: ReportType;
  emoji: string;
  label: string;
  sub: string;
  ariaLabel: string;
}

const cards: PickerCard[] = [
  {
    type: 'human',
    emoji: '🤒',
    label: 'Person',
    sub: 'Illness, heat, exposure',
    ariaLabel: 'Report a human health event (illness, heat distress, exposure)',
  },
  {
    type: 'animal',
    emoji: '🦌',
    label: 'Animal',
    sub: 'Sick, dead, unusual',
    ariaLabel: 'Report a sick, dead, or unusual animal — fully anonymous',
  },
  {
    type: 'environmental',
    emoji: '🪣',
    label: 'Environment',
    sub: 'Sewage, burn, smoke, water',
    ariaLabel:
      'Report an environmental hazard (sewage, burn, smoke, water) — fully anonymous',
  },
];

export default function HomePage() {
  return (
    <>
      <section className="hero">
        <h1>What did you see?</h1>
        <p>No login. No name. Just tap one.</p>
      </section>

      <div className="picker" role="group" aria-label="Report type picker">
        {cards.map((card) => (
          <Link
            key={card.type}
            href={`/report/${card.type}`}
            className="picker-btn"
            aria-label={card.ariaLabel}
          >
            <span className="picker-emoji" aria-hidden="true">
              {card.emoji}
            </span>
            <span className="picker-label">{card.label}</span>
            <span className="picker-sub">{card.sub}</span>
          </Link>
        ))}
      </div>

      <p className="muted small privacy-stamp">
        <span aria-hidden="true">🛡️ </span>
        Animal and Environment reports stay fully anonymous. Person reports
        are anonymous by default — you choose later whether to share contact
        details with a clinician.
      </p>

      <hr className="rule" />

      <section className="legacy-flows">
        <h2>Other flows (legacy prototype)</h2>
        <p className="muted small">
          The Phase-0/1 vanilla flows are preserved while they&apos;re ported
          to React. Each link below is one of the original demo paths.
        </p>
        <ul>
          <li>
            <a href="/epihack-2026/app/legacy/tick/">Submit a tick</a>
            <span className="muted small"> · VBD · Phase 0</span>
          </li>
          <li>
            <a href="/epihack-2026/app/legacy/heat/check-in/">
              Heat check-in (CHW)
            </a>
            <span className="muted small"> · Heat · Phase 1</span>
          </li>
          <li>
            <a href="/epihack-2026/app/legacy/heat/self-report/">
              Heat self-report
            </a>
            <span className="muted small"> · Heat · Phase 1</span>
          </li>
          <li>
            <a href="/epihack-2026/app/legacy/heat/cool-off/">
              Where can I cool off?
            </a>
            <span className="muted small"> · Heat · Phase 1</span>
          </li>
        </ul>
      </section>

      <p className="meta">
        Cross-references:{' '}
        <a href="/epihack-2026/map/index.html">map of AZ</a> ·{' '}
        <a href="/epihack-2026/graph/index.html">pathogen graph</a> ·{' '}
        <a href="/epihack-2026/plan/index.html">plan</a> ·{' '}
        <a href="/epihack-2026/plan/06-mobile-app.html">plan 06 (this app)</a>
      </p>
    </>
  );
}
