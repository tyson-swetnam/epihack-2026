/**
 * Hand-written placeholder shapes for the OpenAPI types.
 *
 * `npm run gen:api` regenerates ./api-types.ts from ../api/openapi.yaml
 * with the full generated tree. This file exists so the project type-
 * checks before that command runs (fresh clone, CI step ordering, etc.).
 *
 * If you change ../api/openapi.yaml, the generated types are the
 * source of truth — this file should track them.
 */

export type ReportType = 'human' | 'animal' | 'environmental';

export interface CoarseLocation {
  zip?: string;
  grid_id?: string;
  resolution_m?: number;
}

export type EventClass =
  | 'human.fever_chills'
  | 'human.heat_distress'
  | 'human.respiratory'
  | 'human.gastrointestinal'
  | 'human.rash_or_bite'
  | 'human.exposure_water'
  | 'human.exposure_animal'
  | 'human.animal_bite_scratch'
  | 'animal.dead_wildlife'
  | 'animal.dead_livestock'
  | 'animal.sick_unusual_behaviour'
  | 'animal.mass_die_off'
  | 'animal.unusual_species_sighting'
  | 'animal.pet_sick'
  | 'animal.malnourishment'
  | 'env.sewage'
  | 'env.smoke_or_burn'
  | 'env.standing_water'
  | 'env.water_quality'
  | 'env.air_quality'
  | 'env.illegal_dumping'
  | 'env.food_safety';

export type SeverityIcon = 'grin' | 'neutral' | 'frown' | 'alarm';

export type SymptomCategory =
  | 'fever'
  | 'chills'
  | 'headache'
  | 'muscle_aches'
  | 'cough'
  | 'shortness_of_breath'
  | 'nausea_vomiting'
  | 'diarrhea'
  | 'rash'
  | 'dizziness'
  | 'confusion'
  | 'heat_cramps';

export interface ReportPayload {
  report_type: ReportType;
  event_class: EventClass;
  coarse_location: CoarseLocation;
  event_date?: string;
  severity?: SeverityIcon;
  count?: number;
  species?: string;
  symptoms?: SymptomCategory[];
  notes?: string;
}

export type NextAction =
  | 'self_care'
  | 'see_clinician_routine'
  | 'see_clinician_urgent'
  | 'call_211'
  | 'report_to_agency'
  | 'mail_in_specimen';

export interface CitedSource {
  name: string;
  url: string;
  mcp?: string;
}

export interface TriageOutcome {
  next_action: NextAction;
  urgency?: 'none' | 'routine' | 'urgent' | 'emergent';
  copy?: string;
  sources: CitedSource[];
}

export interface ContextSignal {
  class: 'vbd' | 'heat' | 'wildlife' | 'environment';
  headline: string;
  severity_tier?: 'info' | 'advisory' | 'watch' | 'warning';
  valid_through?: string;
  source: CitedSource;
}

export interface ContextEnvelope {
  coarse_location: CoarseLocation;
  signals: ContextSignal[];
}

export interface ReportAck {
  observation_id: string;
  claim_token: string;
  status_url: string;
  triage?: TriageOutcome;
  context?: ContextEnvelope;
  queued?: boolean;
}

export interface ReportStatus {
  observation_id: string;
  state: 'received' | 'triaged' | 'notified' | 'archived' | 'withdrawn';
  triage?: TriageOutcome;
  context?: ContextEnvelope;
  profile_attached?: boolean;
}

export interface ContactChannel {
  email?: string;
  sms_phone?: string;
}

export interface ProfilePatch {
  home_zip?: string;
  precise_location_consent?: boolean;
  contact_about_my_reports?: ContactChannel;
  contact_about_nearby_events?: ContactChannel;
  share_photo_gps_animal_env?: boolean;
  share_photo_gps_human?: boolean;
  age_band?: '<18' | '18-29' | '30-44' | '45-64' | '65+';
  sex_at_birth?: 'female' | 'male' | 'intersex' | 'prefer_not_to_say';
  gender_identity?: string;
  race_ethnicity?: string[];
  primary_language?: string;
  accessibility_needs?: string[];
  household_size?: number;
  has_pets?: boolean;
  works_outdoors?: boolean;
}
