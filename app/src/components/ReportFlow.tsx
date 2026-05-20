'use client';

/**
 * <ReportFlow> — multi-step shell for filing a Human / Animal /
 * Environmental report.
 *
 * Logic (EXIF strip, location coarsening, typed createReport submit) is
 * unchanged; the presentation is the teal design system ported from
 * Elbaraaa/OneHealth (plan/08 Phase 2). The done step renders the server's
 * triage `next_action` only — never a diagnosis or score (privacy contract).
 */
import { useCallback, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Camera,
  Check,
  CircleCheck,
  ListChecks,
  Loader2,
  MapPin,
  Navigation,
  ShieldCheck,
} from 'lucide-react';

import { createReport, type ReportType } from '@/lib/api-client';
import { stripExif } from '@/lib/exif-stripper';
import { coarsenLatLon, normaliseZip } from '@/lib/coarse-geo';
import type {
  CoarseLocation,
  EventClass,
  NextAction,
  ReportAck,
  ReportPayload,
} from '@/lib/api-shapes';

type Step = 'photo' | 'class' | 'where' | 'consent' | 'submitting' | 'done';

const STEP_ORDER: Step[] = ['photo', 'class', 'where', 'consent'];

const eventClassesByType: Record<
  ReportType,
  { value: EventClass; label: string; emoji: string }[]
> = {
  human: [
    { value: 'human.fever_chills', label: 'Fever or chills', emoji: '🥶' },
    { value: 'human.heat_distress', label: 'Heat distress', emoji: '🥵' },
    { value: 'human.respiratory', label: 'Respiratory', emoji: '😷' },
    { value: 'human.gastrointestinal', label: 'Stomach / GI', emoji: '🤢' },
    { value: 'human.rash_or_bite', label: 'Rash or bite', emoji: '🦟' },
    { value: 'human.exposure_water', label: 'Water exposure', emoji: '🌊' },
    { value: 'human.exposure_animal', label: 'Animal exposure', emoji: '🐀' },
  ],
  animal: [
    { value: 'animal.dead_wildlife', label: 'Dead wildlife', emoji: '🦌' },
    { value: 'animal.dead_livestock', label: 'Dead livestock', emoji: '🐄' },
    { value: 'animal.sick_unusual_behaviour', label: 'Sick / odd behaviour', emoji: '🦝' },
    { value: 'animal.mass_die_off', label: 'Mass die-off', emoji: '⚠️' },
    { value: 'animal.unusual_species_sighting', label: 'Unusual species', emoji: '🦂' },
  ],
  environmental: [
    { value: 'env.sewage', label: 'Sewage', emoji: '🪣' },
    { value: 'env.smoke_or_burn', label: 'Smoke / burn', emoji: '🔥' },
    { value: 'env.standing_water', label: 'Standing water', emoji: '💧' },
    { value: 'env.water_quality', label: 'Water quality', emoji: '🚱' },
    { value: 'env.air_quality', label: 'Air quality', emoji: '🌫️' },
    { value: 'env.illegal_dumping', label: 'Illegal dumping', emoji: '🗑️' },
  ],
};

// Routing copy for the result card. This is *routing*, not diagnosis — there
// is deliberately no score or condition here (privacy contract §4).
const NEXT_ACTION_COPY: Record<NextAction, { title: string; hint: string }> = {
  self_care: {
    title: 'Self-care for now',
    hint: 'Rest and monitor. Seek care if things get worse.',
  },
  see_clinician_routine: {
    title: 'See a clinician soon',
    hint: 'Book a routine visit with a healthcare provider.',
  },
  see_clinician_urgent: {
    title: 'See a clinician urgently',
    hint: "Don't wait — seek care today.",
  },
  call_211: {
    title: 'Call 2-1-1',
    hint: 'Local resources and guidance are available by phone.',
  },
  report_to_agency: {
    title: 'Shared with the right agency',
    hint: 'This was routed to the relevant public-health partner.',
  },
  mail_in_specimen: {
    title: 'Mail-in specimen suggested',
    hint: 'A specimen kit may help confirm what you saw.',
  },
};

export function ReportFlow({ reportType }: { reportType: ReportType }) {
  const [step, setStep] = useState<Step>('photo');
  const [photo, setPhoto] = useState<{ blob: Blob; originalHadGps: boolean } | null>(null);
  const [eventClass, setEventClass] = useState<EventClass | null>(null);
  const [coarseLocation, setCoarseLocation] = useState<CoarseLocation | null>(null);
  const [consented, setConsented] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ack, setAck] = useState<ReportAck | null>(null);

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
        setCoarseLocation({ grid_id: cell.grid_id, resolution_m: cell.resolution_m });
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
      const result = await createReport(payload, photo?.blob ?? null);
      setAck(result);
      setStep('done');
    } catch (err) {
      setError((err as Error).message);
      setStep('consent');
    }
  }, [eventClass, coarseLocation, reportType, photo]);

  const progressPct =
    step === 'done' || step === 'submitting'
      ? 100
      : ((STEP_ORDER.indexOf(step) + 1) / STEP_ORDER.length) * 100;

  return (
    <div className="flex flex-col gap-4 px-4 pb-8 pt-4">
      {/* Progress + privacy line */}
      {step !== 'done' && (
        <div className="flex flex-col gap-2">
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progressPct}%` }} />
          </div>
          <p className="flex items-center gap-1 text-[11px] font-medium text-slate-500">
            <ShieldCheck className="size-3 text-public-teal" aria-hidden="true" />
            Anonymous · EXIF GPS stripped on your device
          </p>
        </div>
      )}

      {error && (
        <p
          className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700"
          role="alert"
        >
          {error}
        </p>
      )}

      {/* ----- Photo ------------------------------------------------------ */}
      {step === 'photo' && (
        <section className="flex flex-col gap-3">
          <h2 className="text-base font-extrabold text-ink">Add a photo (optional)</h2>
          <label className="focus-ring flex cursor-pointer flex-col items-center gap-2 rounded-md border-2 border-dashed border-teal-200 bg-white px-4 py-8 text-center text-sm text-slate-600 transition hover:border-public-teal">
            <Camera className="size-6 text-public-teal" aria-hidden="true" />
            {photo ? 'Photo ready — EXIF stripped ✓' : 'Tap to take or upload a photo'}
            <input
              type="file"
              accept="image/*"
              capture="environment"
              className="sr-only"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onPhotoSelected(f);
              }}
            />
          </label>
          {photo?.originalHadGps && (
            <p className="text-xs text-slate-500">
              Original photo had GPS — removed before upload.
            </p>
          )}
          <div className="mt-2 flex gap-2">
            <button className="app-button-secondary" onClick={() => setStep('class')}>
              Skip
            </button>
            <button className="app-button" onClick={() => setStep('class')}>
              Next
            </button>
          </div>
        </section>
      )}

      {/* ----- Class ------------------------------------------------------ */}
      {step === 'class' && (
        <section className="flex flex-col gap-3">
          <h2 className="text-base font-extrabold text-ink">What kind of event?</h2>
          <div className="flex flex-col gap-2" role="radiogroup">
            {classes.map((c) => {
              const selected = eventClass === c.value;
              return (
                <button
                  key={c.value}
                  role="radio"
                  aria-checked={selected}
                  className={`choice-row ${selected ? 'border-public-teal bg-soft-mint' : ''}`}
                  onClick={() => setEventClass(c.value)}
                >
                  <span className="text-xl" aria-hidden="true">
                    {c.emoji}
                  </span>
                  <span className="flex-1 text-sm font-semibold text-ink">{c.label}</span>
                  {selected && (
                    <Check className="size-4 text-public-teal" aria-hidden="true" />
                  )}
                </button>
              );
            })}
          </div>
          <div className="mt-2 flex gap-2">
            <button className="app-button-secondary" onClick={() => setStep('photo')}>
              <ArrowLeft className="size-4" aria-hidden="true" />
              Back
            </button>
            <button className="app-button" disabled={!eventClass} onClick={() => setStep('where')}>
              Next
            </button>
          </div>
        </section>
      )}

      {/* ----- Where ------------------------------------------------------ */}
      {step === 'where' && (
        <section className="flex flex-col gap-3">
          <h2 className="text-base font-extrabold text-ink">Where?</h2>
          <p className="text-xs text-slate-500">
            We round to about a 1 km square before saving — never a precise point.
          </p>
          <button className="app-button-secondary" onClick={onUseGps}>
            <Navigation className="size-4" aria-hidden="true" />
            Use my location
          </button>
          <div className="relative">
            <MapPin className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              type="text"
              inputMode="numeric"
              maxLength={10}
              placeholder="or enter a ZIP code"
              autoComplete="postal-code"
              className="focus-ring w-full rounded-md border border-slate-200 bg-white py-3 pl-9 pr-3 text-sm"
              onChange={(e) => onZipChange(e.target.value)}
            />
          </div>
          {coarseLocation && (
            <p className="flex items-center gap-1 text-xs text-public-teal">
              <CircleCheck className="size-3.5" aria-hidden="true" />
              Captured: <code>{coarseLocation.zip ?? coarseLocation.grid_id}</code>
            </p>
          )}
          <div className="mt-2 flex gap-2">
            <button className="app-button-secondary" onClick={() => setStep('class')}>
              <ArrowLeft className="size-4" aria-hidden="true" />
              Back
            </button>
            <button
              className="app-button"
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
        <section className="flex flex-col gap-3">
          <h2 className="text-base font-extrabold text-ink">Ready to submit?</h2>
          <ul className="flex flex-col gap-2 rounded-md bg-soft-mint p-3 text-sm text-ink">
            {[
              'Coarse location is kept (ZIP or ~1 km cell).',
              'Precise GPS is discarded.',
              'Photo (if any) is kept without its GPS tag.',
              'Your IP is hashed and dropped — never stored.',
              'No name, contact, or demographics are asked here.',
            ].map((line) => (
              <li key={line} className="flex items-start gap-2">
                <Check className="mt-0.5 size-4 shrink-0 text-public-teal" aria-hidden="true" />
                {line}
              </li>
            ))}
          </ul>
          <label className="choice-row cursor-pointer">
            <input
              type="checkbox"
              checked={consented}
              onChange={(e) => setConsented(e.target.checked)}
              className="size-4 accent-public-teal"
            />
            <span className="flex-1 text-sm text-ink">
              I understand and want to submit this anonymously.
            </span>
          </label>
          <div className="mt-2 flex gap-2">
            <button className="app-button-secondary" onClick={() => setStep('where')}>
              <ArrowLeft className="size-4" aria-hidden="true" />
              Back
            </button>
            <button className="app-button" disabled={!canSubmit} onClick={onSubmit}>
              Submit
            </button>
          </div>
        </section>
      )}

      {/* ----- Submitting ------------------------------------------------- */}
      {step === 'submitting' && (
        <section className="flex flex-col items-center gap-4 py-8" role="status" aria-live="polite">
          <Loader2 className="size-8 animate-spin text-public-teal" aria-hidden="true" />
          <p className="text-sm font-semibold text-ink">Sending your report…</p>
          <ol className="flex w-full flex-col gap-1.5 text-xs text-slate-500">
            {[
              'Intake — strip EXIF, coarsen location',
              'Geo-Enrichment — map to ZIP / 1 km cell',
              'Validation — no-PII / no-GPS check',
              'Triage — routing decision (not diagnosis)',
              'Enrichment — public-health context',
              'Notification — your response card',
            ].map((line) => (
              <li key={line} className="flex items-center gap-2">
                <ListChecks className="size-3 text-public-teal" aria-hidden="true" />
                {line}
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* ----- Done (result card, routing only — no diagnosis/score) ------ */}
      {step === 'done' && (
        <section className="flex flex-col items-center gap-4 py-6 text-center">
          <div className="grid size-16 place-items-center rounded-full bg-soft-mint">
            <CircleCheck className="size-8 text-public-teal" aria-hidden="true" />
          </div>
          <h2 className="text-lg font-extrabold text-ink">Thank you — report received</h2>

          {ack?.triage ? (
            <div className="w-full rounded-md border border-slate-200 bg-white p-4 text-left shadow-sm">
              <p className="text-[11px] font-bold uppercase tracking-wide text-public-teal">
                Suggested next step
              </p>
              <p className="mt-1 text-base font-extrabold text-ink">
                {NEXT_ACTION_COPY[ack.triage.next_action]?.title ?? 'Next step'}
              </p>
              <p className="mt-1 text-sm text-slate-600">
                {ack.triage.copy ??
                  NEXT_ACTION_COPY[ack.triage.next_action]?.hint}
              </p>
              {ack.triage.sources?.length > 0 && (
                <ul className="mt-3 flex flex-col gap-1 border-t border-slate-100 pt-2 text-xs">
                  {ack.triage.sources.map((s) => (
                    <li key={s.url}>
                      <a
                        href={s.url}
                        className="text-public-blue underline"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {s.name}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <p className="max-w-[280px] text-sm text-slate-600">
              This app does not diagnose. Public-health context for your area
              will appear here once the Enrichment Agent finishes its pull.
            </p>
          )}

          <p className="text-[11px] text-slate-400">
            Reference: <code>{ack?.observation_id ?? '—'}</code>
          </p>

          <div className="mt-2 flex w-full gap-2">
            <Link className="app-button-secondary" href="/report">
              File another
            </Link>
            <Link className="app-button" href="/profile">
              Save a profile
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
