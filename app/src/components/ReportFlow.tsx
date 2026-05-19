'use client';

/**
 * <ReportFlow> — multi-step shell for filing a Human / Animal /
 * Environmental report.
 *
 * This commit lands the SCAFFOLD: the steps render, the privacy
 * primitives (EXIF strip, location coarsening) are wired through
 * the API client, and the submit posts to the typed
 * `createReport()`. The icon grids per type and the post-submit
 * profile interstitial are stubbed pending UX review (the icons
 * are intentionally placeholders so we don't ship icon choices
 * that haven't been workshopped).
 */
import { useCallback, useMemo, useState } from 'react';
import Link from 'next/link';

import { createReport, type ReportType } from '@/lib/api-client';
import { stripExif } from '@/lib/exif-stripper';
import { coarsenLatLon, normaliseZip } from '@/lib/coarse-geo';
import type {
  CoarseLocation,
  EventClass,
  ReportPayload,
} from '@/lib/api-shapes';

type Step = 'photo' | 'class' | 'where' | 'consent' | 'submitting' | 'done';

const eventClassesByType: Record<ReportType, { value: EventClass; label: string; emoji: string }[]> = {
  human: [
    { value: 'human.fever_chills',    label: 'Fever or chills',   emoji: '🥶' },
    { value: 'human.heat_distress',   label: 'Heat distress',     emoji: '🥵' },
    { value: 'human.respiratory',     label: 'Respiratory',       emoji: '😷' },
    { value: 'human.gastrointestinal',label: 'Stomach / GI',      emoji: '🤢' },
    { value: 'human.rash_or_bite',    label: 'Rash or bite',      emoji: '🦟' },
    { value: 'human.exposure_water',  label: 'Water exposure',    emoji: '🌊' },
    { value: 'human.exposure_animal', label: 'Animal exposure',   emoji: '🐀' },
  ],
  animal: [
    { value: 'animal.dead_wildlife',           label: 'Dead wildlife',      emoji: '🦌' },
    { value: 'animal.dead_livestock',          label: 'Dead livestock',     emoji: '🐄' },
    { value: 'animal.sick_unusual_behaviour',  label: 'Sick / odd behaviour', emoji: '🦝' },
    { value: 'animal.mass_die_off',            label: 'Mass die-off',       emoji: '⚠️' },
    { value: 'animal.unusual_species_sighting',label: 'Unusual species',    emoji: '🦂' },
  ],
  environmental: [
    { value: 'env.sewage',          label: 'Sewage', emoji: '🪣' },
    { value: 'env.smoke_or_burn',   label: 'Smoke / burn', emoji: '🔥' },
    { value: 'env.standing_water',  label: 'Standing water', emoji: '💧' },
    { value: 'env.water_quality',   label: 'Water quality', emoji: '🚱' },
    { value: 'env.air_quality',     label: 'Air quality', emoji: '🌫️' },
    { value: 'env.illegal_dumping', label: 'Illegal dumping', emoji: '🗑️' },
  ],
};

export function ReportFlow({ reportType }: { reportType: ReportType }) {
  const [step, setStep] = useState<Step>('photo');
  const [photo, setPhoto] = useState<{ blob: Blob; originalHadGps: boolean } | null>(null);
  const [eventClass, setEventClass] = useState<EventClass | null>(null);
  const [coarseLocation, setCoarseLocation] = useState<CoarseLocation | null>(null);
  const [consented, setConsented] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [observationId, setObservationId] = useState<string | null>(null);

  const classes = eventClassesByType[reportType];

  const onPhotoSelected = useCallback(async (file: File) => {
    setError(null);
    try {
      const { blob, originalHadGps } = await stripExif(file);
      setPhoto({ blob, originalHadGps });
    } catch (err) {
      setError(`Couldn't read that photo. (${(err as Error).message})`);
    }
  }, []);

  const onUseGps = useCallback(() => {
    setError(null);
    if (!navigator.geolocation) {
      setError('GPS not available on this device. Enter a ZIP instead.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const cell = coarsenLatLon({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        setCoarseLocation({
          grid_id: cell.grid_id,
          resolution_m: cell.resolution_m,
        });
      },
      (err) => setError(`GPS denied: ${err.message}. Enter a ZIP instead.`),
      { maximumAge: 60000, timeout: 8000, enableHighAccuracy: false }
    );
  }, []);

  const onZipChange = useCallback((raw: string) => {
    const zip = normaliseZip(raw);
    if (zip) setCoarseLocation({ zip, resolution_m: 5000 });
    else if (raw === '') setCoarseLocation(null);
  }, []);

  const canSubmit = useMemo(
    () => Boolean(eventClass && coarseLocation && consented),
    [eventClass, coarseLocation, consented]
  );

  const onSubmit = useCallback(async () => {
    if (!eventClass || !coarseLocation) return;
    setStep('submitting');
    setError(null);
    try {
      const payload: ReportPayload = {
        report_type: reportType,
        event_class: eventClass,
        coarse_location: coarseLocation,
      };
      const ack = await createReport(payload, photo?.blob ?? null);
      setObservationId(ack.observation_id);
      setStep('done');
    } catch (err) {
      setError((err as Error).message);
      setStep('consent');
    }
  }, [eventClass, coarseLocation, reportType, photo]);

  return (
    <article className="report-flow" data-type={reportType}>
      <nav className="crumbs">
        <Link href="/">&laquo; Pick a different type</Link>
      </nav>

      <h2>{titleFor(reportType)}</h2>
      <p className="muted small">
        Anonymous report. No login. EXIF GPS is stripped from any photo
        before it leaves your device.
      </p>

      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}

      {/* ----- Photo ------------------------------------------------------ */}
      {step === 'photo' && (
        <section className="step">
          <h3>Photo (optional)</h3>
          <label className="photo-input">
            {photo ? '✅ Photo ready (EXIF stripped)' : 'Tap to take a photo or upload'}
            <input
              type="file"
              accept="image/*"
              capture="environment"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onPhotoSelected(f);
              }}
            />
          </label>
          {photo?.originalHadGps && (
            <p className="muted small">Original photo had GPS — removed before upload.</p>
          )}
          <div className="actions">
            <button className="btn ghost" onClick={() => setStep('class')}>
              Skip
            </button>
            <button className="btn" onClick={() => setStep('class')}>
              Next
            </button>
          </div>
        </section>
      )}

      {/* ----- Class ------------------------------------------------------ */}
      {step === 'class' && (
        <section className="step">
          <h3>What kind of event?</h3>
          <div className="icon-grid" role="radiogroup">
            {classes.map((c) => (
              <button
                key={c.value}
                role="radio"
                aria-checked={eventClass === c.value}
                className={`icon-btn${eventClass === c.value ? ' selected' : ''}`}
                onClick={() => setEventClass(c.value)}
              >
                <span className="icon" aria-hidden="true">
                  {c.emoji}
                </span>
                <span className="label">{c.label}</span>
              </button>
            ))}
          </div>
          <div className="actions">
            <button className="btn secondary" onClick={() => setStep('photo')}>
              Back
            </button>
            <button
              className="btn"
              disabled={!eventClass}
              onClick={() => setStep('where')}
            >
              Next
            </button>
          </div>
        </section>
      )}

      {/* ----- Where ------------------------------------------------------ */}
      {step === 'where' && (
        <section className="step">
          <h3>Where?</h3>
          <p className="muted small">We round to about a 1 km square before saving.</p>
          <div className="field-row">
            <button className="btn secondary" onClick={onUseGps}>
              Use my location
            </button>
            <input
              type="text"
              inputMode="numeric"
              maxLength={10}
              placeholder="or enter a ZIP"
              autoComplete="postal-code"
              onChange={(e) => onZipChange(e.target.value)}
            />
          </div>
          {coarseLocation && (
            <p className="muted small">
              Captured:{' '}
              <code>{coarseLocation.zip ?? coarseLocation.grid_id}</code>
            </p>
          )}
          <div className="actions">
            <button className="btn secondary" onClick={() => setStep('class')}>
              Back
            </button>
            <button
              className="btn"
              disabled={!coarseLocation}
              onClick={() => setStep('consent')}
            >
              Next
            </button>
          </div>
        </section>
      )}

      {/* ----- Consent ---------------------------------------------------- */}
      {step === 'consent' && (
        <section className="step">
          <h3>Ready to submit?</h3>
          <ul className="consent-list">
            <li>Coarse location is kept (ZIP or ~1 km cell).</li>
            <li>Precise GPS is discarded.</li>
            <li>Photo (if any) is kept without its GPS tag.</li>
            <li>Your IP is hashed and dropped — never stored.</li>
            <li>No name, contact, or demographics are asked for here.</li>
          </ul>
          <label className="consent">
            <input
              type="checkbox"
              checked={consented}
              onChange={(e) => setConsented(e.target.checked)}
            />
            I understand and want to submit this anonymously.
          </label>
          <div className="actions">
            <button className="btn secondary" onClick={() => setStep('where')}>
              Back
            </button>
            <button className="btn" disabled={!canSubmit} onClick={onSubmit}>
              Submit
            </button>
          </div>
        </section>
      )}

      {/* ----- Submitting ------------------------------------------------- */}
      {step === 'submitting' && (
        <section className="step" role="status" aria-live="polite">
          <p>Sending your report through the pipeline…</p>
          <ol className="agent-log">
            <li>Intake — strip EXIF, coarsen location</li>
            <li>Geo-Enrichment — map to ZIP / 1 km cell</li>
            <li>Validation — no-PII / no-GPS check</li>
            <li>Triage — routing decision (not diagnosis)</li>
            <li>Enrichment — public-health context</li>
            <li>Notification — your response card</li>
          </ol>
        </section>
      )}

      {/* ----- Done ------------------------------------------------------- */}
      {step === 'done' && (
        <section className="step">
          <h3>Thanks — report received</h3>
          <p>
            Reference: <code>{observationId ?? '—'}</code>
          </p>
          <p className="muted small">
            This app does not diagnose. Public-health context for your area
            will appear here once the Enrichment Agent finishes its pull.
          </p>
          <div className="actions">
            <Link className="btn ghost" href="/">
              File another
            </Link>
            <Link className="btn" href="/profile">
              Optional: save a profile
            </Link>
          </div>
        </section>
      )}
    </article>
  );
}

function titleFor(type: ReportType): string {
  return {
    human: 'Report a person',
    animal: 'Report an animal event',
    environmental: 'Report an environmental hazard',
  }[type];
}
