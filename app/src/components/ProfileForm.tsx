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
}

const initial: FormState = {
  home_zip: '',
  precise_location_consent: false,
  contact_email: '',
  contact_sms: '',
  share_photo_gps_animal_env: false,
  share_photo_gps_human: false,
};

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
    if (state.home_zip) patch.home_zip = state.home_zip;
    if (state.precise_location_consent) patch.precise_location_consent = true;
    if (state.contact_email || state.contact_sms) {
      patch.contact_about_my_reports = {
        ...(state.contact_email ? { email: state.contact_email } : {}),
        ...(state.contact_sms ? { sms_phone: state.contact_sms } : {}),
      };
    }
    if (state.share_photo_gps_animal_env)
      patch.share_photo_gps_animal_env = true;
    if (state.share_photo_gps_human) patch.share_photo_gps_human = true;

    try {
      await attachProfile(observationId, claimToken, patch);
      setStatus('saved');
    } catch (err) {
      setStatus('error');
      setError((err as Error).message);
    }
  };

  return (
    <form onSubmit={onSubmit} className="profile-form">
      <label className="field">
        Home ZIP (optional)
        <input
          type="text"
          inputMode="numeric"
          maxLength={5}
          value={state.home_zip}
          onChange={(e) => setState({ ...state, home_zip: e.target.value })}
          autoComplete="postal-code"
        />
      </label>

      <fieldset>
        <legend>Contact about my reports</legend>
        <label className="field">
          Email
          <input
            type="email"
            value={state.contact_email}
            onChange={(e) =>
              setState({ ...state, contact_email: e.target.value })
            }
          />
        </label>
        <label className="field">
          SMS / phone
          <input
            type="tel"
            value={state.contact_sms}
            onChange={(e) =>
              setState({ ...state, contact_sms: e.target.value })
            }
          />
        </label>
      </fieldset>

      <fieldset>
        <legend>Share precise location with verified agencies?</legend>
        <label className="toggle">
          <input
            type="checkbox"
            checked={state.precise_location_consent}
            onChange={(e) =>
              setState({
                ...state,
                precise_location_consent: e.target.checked,
              })
            }
          />
          Allow agencies to read the precise GPS captured with my reports
        </label>
        <label className="toggle">
          <input
            type="checkbox"
            checked={state.share_photo_gps_animal_env}
            onChange={(e) =>
              setState({
                ...state,
                share_photo_gps_animal_env: e.target.checked,
              })
            }
          />
          Keep photo GPS on animal &amp; environment reports
        </label>
        <label className="toggle">
          <input
            type="checkbox"
            checked={state.share_photo_gps_human}
            onChange={(e) =>
              setState({ ...state, share_photo_gps_human: e.target.checked })
            }
          />
          Keep photo GPS on person reports
        </label>
      </fieldset>

      <div className="actions">
        <button type="submit" className="btn" disabled={status === 'saving'}>
          {status === 'saving' ? 'Saving…' : 'Save profile'}
        </button>
      </div>

      {status === 'saved' && (
        <p role="status" className="muted small">
          ✅ Profile attached to your most recent report.
        </p>
      )}
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
    </form>
  );
}
