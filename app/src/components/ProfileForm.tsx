'use client';

import { useState } from 'react';
import { attachProfile } from '@/lib/api-client';
import type { ProfilePatch } from '@/lib/api-shapes';

interface FormState {
  home_zip: string;
  precise_location_consent: boolean;
  contact_email: string;
  contact_sms: string;
  share_photo_gps_animal_env: boolean;
  share_photo_gps_human: boolean;
  household_size: string;
  has_pets: boolean;
  works_outdoors: boolean;
}

const initial: FormState = {
  home_zip: '',
  precise_location_consent: false,
  contact_email: '',
  contact_sms: '',
  share_photo_gps_animal_env: false,
  share_photo_gps_human: false,
  household_size: '',
  has_pets: false,
  works_outdoors: false,
};

const fieldClass =
  'focus-ring w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-normal';

export function ProfileForm() {
  const [state, setState] = useState<FormState>(initial);
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('saving');
    setError(null);

    const observationId = window.localStorage.getItem('lastObservationId');
    const claimToken = window.localStorage.getItem('lastClaimToken');
    if (!observationId || !claimToken) {
      setStatus('error');
      setError('No recent report found. File a report first.');
      return;
    }

    const patch: ProfilePatch = {};
    if (state.home_zip) {
      patch.home_zip = state.home_zip;
      // Let the personal dashboard localize to this ZIP.
      window.localStorage.setItem('homeZip', state.home_zip);
    }
    if (state.precise_location_consent) patch.precise_location_consent = true;
    if (state.contact_email || state.contact_sms) {
      patch.contact_about_my_reports = {
        ...(state.contact_email ? { email: state.contact_email } : {}),
        ...(state.contact_sms ? { sms_phone: state.contact_sms } : {}),
      };
    }
    if (state.share_photo_gps_animal_env) patch.share_photo_gps_animal_env = true;
    if (state.share_photo_gps_human) patch.share_photo_gps_human = true;
    if (state.household_size) patch.household_size = Number(state.household_size);
    if (state.has_pets) patch.has_pets = true;
    if (state.works_outdoors) patch.works_outdoors = true;

    try {
      await attachProfile(observationId, claimToken, patch);
      setStatus('saved');
    } catch (err) {
      setStatus('error');
      setError((err as Error).message);
    }
  };

  const toggle = (key: keyof FormState, label: string) => (
    <label className="choice-row cursor-pointer">
      <input
        type="checkbox"
        checked={state[key] as boolean}
        onChange={(e) => setState({ ...state, [key]: e.target.checked })}
        className="mt-0.5 size-4 shrink-0 accent-public-teal"
      />
      <span className="flex-1 text-sm text-ink">{label}</span>
    </label>
  );

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <label className="flex flex-col gap-1 text-sm font-semibold text-ink">
        Home ZIP (optional)
        <input
          type="text"
          inputMode="numeric"
          maxLength={5}
          value={state.home_zip}
          onChange={(e) => setState({ ...state, home_zip: e.target.value })}
          autoComplete="postal-code"
          className={fieldClass}
        />
      </label>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-xs font-bold uppercase tracking-wide text-public-teal">
          About my household
        </legend>
        <p className="text-xs leading-4 text-slate-500">
          Optional — helps us tailor which alerts are actually relevant to you.
        </p>
        <label className="flex flex-col gap-1 text-sm font-semibold text-ink">
          People in my household
          <input
            type="number"
            inputMode="numeric"
            min={1}
            max={20}
            value={state.household_size}
            onChange={(e) => setState({ ...state, household_size: e.target.value })}
            className={fieldClass}
          />
        </label>
        {toggle('has_pets', 'I have pets (tailors tick / zoonotic advisories)')}
        {toggle('works_outdoors', 'I work outdoors (raises heat & vector relevance)')}
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-xs font-bold uppercase tracking-wide text-public-teal">
          Contact about my reports
        </legend>
        <label className="flex flex-col gap-1 text-sm font-semibold text-ink">
          Email
          <input
            type="email"
            value={state.contact_email}
            onChange={(e) => setState({ ...state, contact_email: e.target.value })}
            className={fieldClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-semibold text-ink">
          SMS / phone
          <input
            type="tel"
            value={state.contact_sms}
            onChange={(e) => setState({ ...state, contact_sms: e.target.value })}
            className={fieldClass}
          />
        </label>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-xs font-bold uppercase tracking-wide text-public-teal">
          Share precise location with verified agencies?
        </legend>
        {toggle(
          'precise_location_consent',
          'Allow agencies to read the precise GPS captured with my reports'
        )}
        {toggle(
          'share_photo_gps_animal_env',
          'Keep photo GPS on animal & environment reports'
        )}
        {toggle('share_photo_gps_human', 'Keep photo GPS on person reports')}
      </fieldset>

      <button type="submit" className="app-button" disabled={status === 'saving'}>
        {status === 'saving' ? 'Saving…' : 'Save profile'}
      </button>

      {status === 'saved' && (
        <p
          role="status"
          className="rounded-md border border-teal-200 bg-soft-mint px-3 py-2 text-sm text-public-teal"
        >
          ✓ Profile attached to your most recent report.
        </p>
      )}
      {error && (
        <p
          role="alert"
          className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700"
        >
          {error}
        </p>
      )}
    </form>
  );
}
