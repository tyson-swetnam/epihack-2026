-- ============================================================================
-- EpiHack Arizona 2026 -- Deep dive: Application runtime (Observation node type
-- and its supporting taxonomy)
--
-- Adds the per-report "observation" node type that the mobile / SMS / voice
-- intake clients, the MCP pulls (VectorSurv, NWS HeatRisk, etc.), and the
-- agency-case backfills all land in, plus the small taxonomy that surrounds
-- it: heat-vertical symptoms, heat- and VBD-vertical exposure factors,
-- consent profiles that govern field suppression, wearable / digital
-- biomarker metrics, and the triage-class enumeration that grading writes to.
--
-- This file does NOT seed any actual observations -- those are runtime data.
-- It only seeds the *types* and *enumeration members* (symptom.*, exposure.*,
-- consent.*, wearable.*, tc.*) that observations are wired up against, plus a
-- handful of skeleton AZ region nodes used by the colocatedWith predicate.
--
-- Depends on (run first, in this order):
--   schema/knowledge_graph.sql         -- kg.node / kg.edge / kg.property and
--                                         the param.* nodes the consent
--                                         profiles suppress.
--   schema/wildlife_vectors.sql        -- focus.* (VBD) and resource.* nodes.
--   schema/heat.sql                    -- focus.heat_* nodes.
--   schema/deep/pathogens.sql          -- pathogen.* / disease.* targets of
--                                         reportsAbout edges.
--   schema/deep/standards.sql          -- code.icd10.t67* and
--                                         code.snomed.heatstroke that the
--                                         heat symptoms cross-reference.
--   schema/deep/counties.sql           -- county.* targets of colocatedWith.
--   schema/deep/tribes.sql             -- tribe.* targets of colocatedWith.
--   schema/deep/outbreaks.sql          -- outbreak.* targets of reportsAbout.
--
-- New predicates introduced here (alongside ones from prior seeds):
--   reportsAbout     observation       -> pathogen | disease | focus_area |
--                                         outbreak | reservoir
--   colocatedWith    observation       -> county | tribe | region
--   gradedAs         observation       -> triage_class
--   suppressesField  consent_profile   -> parameter   (reuses param.*)
--   permitsField     consent_profile   -> parameter   (reuses param.*)
--   measures         wearable_metric   -> symptom | exposure_factor
--   crossReferences  symptom           -> icd10_code | snomed_concept
--                                          (cross-vocabulary anchor for
--                                          heat-specific symptoms not in
--                                          Figure 2)
--
-- edge_id range reserved for this file: 20000 - 20999
-- source_fig = 'plan-application' for all rows added here.
-- All inserts use ON CONFLICT DO NOTHING (idempotent re-run).
--
-- The Observation node itself is intentionally NOT seeded as a single concept
-- row; instead each runtime observation is a kg.node row of node_type =
-- 'observation' with a uuid node_id. The Figure-2 fields are stored as
-- kg.property rows (key = 'age', 'sex', 'reported_at', 'lat', 'lon',
-- 'postal_code', 'vertical', 'source', 'kind', ...). The convenience view
-- kg.v_observation_summary at the bottom of this file pivots that bag back
-- into a wide row per observation.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. TRIAGE CLASS enumeration (gradedAs targets)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('tc.self_care',
     'triage_class', 'Self-care at home',
     'No clinician contact recommended; user receives self-care guidance only (hydration, rest, monitor symptoms).',
     'plan-application'),
  ('tc.see_clinician',
     'triage_class', 'See a clinician within 24-48h',
     'Non-urgent clinician follow-up: tele-health, primary care, or community clinic.',
     'plan-application'),
  ('tc.urgent_care',
     'triage_class', 'Go to urgent care today',
     'Same-day urgent care recommended (e.g. moderate heat exhaustion not responding to rest + hydration, suspected RMSF rash).',
     'plan-application'),
  ('tc.call_911',
     'triage_class', 'Call 911 / emergency services',
     'Life-threatening: heat stroke (confusion, hot dry skin, T >= 104 degF), severe difficulty breathing, bleeding from body openings, severe altered mental status.',
     'plan-application'),
  ('tc.report_to_azgfd',
     'triage_class', 'Report to AZGFD wildlife',
     'Wildlife mortality / sick-animal observation routed to Arizona Game & Fish Department.',
     'plan-application'),
  ('tc.mail_to_walker_lab',
     'triage_class', 'Mail tick to the Walker Lab',
     'Tick mail-in submission flow (Great AZ Tick Check, UA Walker Lab).',
     'plan-application'),
  ('tc.go_to_cooling_center',
     'triage_class', 'Go to nearest cooling center',
     'Heat vertical: routed to nearest open cooling center / hydration station; map link + transit info delivered.',
     'plan-application'),
  ('tc.dispatch_chw',
     'triage_class', 'Dispatch Community Health Worker',
     'CHW / outreach team dispatched (typical for unsheltered heat check-ins or follow-up on isolated elder).',
     'plan-application'),
  ('tc.check_in_only',
     'triage_class', 'Wellness check-in only',
     'No action required beyond logging; observation recorded for surveillance / trend detection.',
     'plan-application'),
  ('tc.drink_water_advisory',
     'triage_class', 'Hydration advisory',
     'Lightweight hydration nudge (e.g. issued from wearable-only signal or borderline HeatRisk level).',
     'plan-application')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('tc.self_care',             'severity','low'),
  ('tc.check_in_only',         'severity','low'),
  ('tc.drink_water_advisory',  'severity','low'),
  ('tc.see_clinician',         'severity','moderate'),
  ('tc.go_to_cooling_center',  'severity','moderate'),
  ('tc.mail_to_walker_lab',    'severity','moderate'),
  ('tc.dispatch_chw',          'severity','moderate'),
  ('tc.report_to_azgfd',       'severity','moderate'),
  ('tc.urgent_care',           'severity','high'),
  ('tc.call_911',              'severity','critical'),
  ('tc.self_care',             'vertical','both'),
  ('tc.see_clinician',         'vertical','both'),
  ('tc.urgent_care',           'vertical','both'),
  ('tc.call_911',              'vertical','both'),
  ('tc.check_in_only',         'vertical','both'),
  ('tc.report_to_azgfd',       'vertical','vbd'),
  ('tc.mail_to_walker_lab',    'vertical','vbd'),
  ('tc.go_to_cooling_center',  'vertical','heat'),
  ('tc.dispatch_chw',          'vertical','heat'),
  ('tc.drink_water_advisory',  'vertical','heat')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. SYMPTOM nodes (heat-specific extensions to Figure 2; VBD-specific
--    severity markers already live as param.* in knowledge_graph.sql)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('symptom.confusion',
     'symptom', 'Confusion / altered mental status',
     'Critical heat-stroke indicator; differentiates heat stroke from heat exhaustion when paired with core temp >= 104 degF.',
     'plan-application'),
  ('symptom.hot_dry_skin',
     'symptom', 'Hot dry skin / stopped sweating',
     'Classic heat-stroke sign; anhidrotic presentation.',
     'plan-application'),
  ('symptom.heavy_sweating',
     'symptom', 'Heavy sweating',
     'Heat-exhaustion-typical; differentiates from anhidrotic heat stroke.',
     'plan-application'),
  ('symptom.headache',
     'symptom', 'Headache',
     'Common across heat exhaustion and early heat stroke.',
     'plan-application'),
  ('symptom.dizziness',
     'symptom', 'Dizziness / fainting',
     'Heat syncope marker (ICD-10 T67.1XXA).',
     'plan-application'),
  ('symptom.muscle_cramps',
     'symptom', 'Muscle cramps',
     'Heat cramp marker (ICD-10 T67.2XXA); often in outdoor workers.',
     'plan-application'),
  ('symptom.core_temp_elevated',
     'symptom', 'Core body temperature elevated (>= 104 degF / 40 degC)',
     'Numeric value collected when measured; >=104 degF is the heat-stroke threshold.',
     'plan-application')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('symptom.confusion',          'vertical','heat'),
  ('symptom.hot_dry_skin',       'vertical','heat'),
  ('symptom.heavy_sweating',     'vertical','heat'),
  ('symptom.headache',           'vertical','heat'),
  ('symptom.dizziness',          'vertical','heat'),
  ('symptom.muscle_cramps',      'vertical','heat'),
  ('symptom.core_temp_elevated', 'vertical','heat'),
  ('symptom.core_temp_elevated', 'unit',         'degF'),
  ('symptom.core_temp_elevated', 'threshold_f',  '104'),
  ('symptom.dizziness',          'severity_marker','heat_syncope'),
  ('symptom.muscle_cramps',      'severity_marker','heat_cramp'),
  ('symptom.confusion',          'severity_marker','heat_stroke'),
  ('symptom.hot_dry_skin',       'severity_marker','heat_stroke'),
  ('symptom.heavy_sweating',     'severity_marker','heat_exhaustion')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3. EXPOSURE FACTOR nodes (heat- and VBD-specific extensions to Figure 2)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  -- Heat-specific
  ('exposure.outdoor_time_24h',
     'exposure_factor', 'Time spent outdoors in last 24h',
     'Hours outdoors; heat dose proxy. Outdoor workers and unsheltered cohort skew high.',
     'plan-application'),
  ('exposure.ac_access',
     'exposure_factor', 'Working AC at home',
     'Binary / categorical; absence of working AC is the single strongest indoor heat-mortality predictor in Maricopa County reviews.',
     'plan-application'),
  ('exposure.energy_insecurity',
     'exposure_factor', 'Energy / utility insecurity',
     'Any past 30d disconnect notices or affordability concerns; proxies AC underutilization even when present.',
     'plan-application'),
  ('exposure.sheltered_status',
     'exposure_factor', 'Currently sheltered?',
     'Sheltered | unsheltered | precariously-housed. Unsheltered cohort dominates AZ heat-mortality statistics.',
     'plan-application'),
  ('exposure.thermo_meds',
     'exposure_factor', 'Medications affecting thermoregulation',
     'Antipsychotics, anticholinergics, diuretics, beta-blockers, stimulants; meaningful heat-stroke risk amplifier.',
     'plan-application'),
  ('exposure.transport_access',
     'exposure_factor', 'Vehicle / transport access',
     'Affects ability to reach a cooling center; gates the dispatch_chw vs go_to_cooling_center triage branch.',
     'plan-application'),
  -- VBD-specific
  ('exposure.bite_location',
     'exposure_factor', 'Bite location on body',
     'Anatomic location of a tick / insect bite; informs RMSF risk (scalp, behind ear, beltline most common in AZ children).',
     'plan-application'),
  ('exposure.bite_attached_duration',
     'exposure_factor', 'Bite / attachment duration',
     'Hours a tick was attached prior to removal; >= 24h substantially elevates pathogen transmission risk.',
     'plan-application'),
  ('exposure.standing_water_nearby',
     'exposure_factor', 'Standing water within X meters',
     'Distance to standing water (proxy for mosquito breeding habitat) and recent rainfall in mm.',
     'plan-application')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('exposure.outdoor_time_24h',       'vertical','heat'),
  ('exposure.ac_access',              'vertical','heat'),
  ('exposure.energy_insecurity',      'vertical','heat'),
  ('exposure.sheltered_status',       'vertical','heat'),
  ('exposure.thermo_meds',            'vertical','heat'),
  ('exposure.transport_access',       'vertical','heat'),
  ('exposure.bite_location',          'vertical','vbd'),
  ('exposure.bite_attached_duration', 'vertical','vbd'),
  ('exposure.standing_water_nearby',  'vertical','vbd'),
  ('exposure.outdoor_time_24h',       'unit','hours'),
  ('exposure.bite_attached_duration', 'unit','hours'),
  ('exposure.standing_water_nearby',  'unit','meters'),
  ('exposure.ac_access',              'value_type','categorical (yes | yes_broken | no | unknown)'),
  ('exposure.sheltered_status',       'value_type','categorical (sheltered | unsheltered | precariously_housed)'),
  ('exposure.thermo_meds',            'value_type','boolean'),
  ('exposure.transport_access',       'value_type','categorical (own_vehicle | rideshare | transit | none)')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. CONSENT PROFILE nodes (suppression-rule anchors)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('consent.anonymous_heat',
     'consent_profile', 'Anonymous heat check-in',
     'Used by unsheltered-outreach flows. Suppresses Email, Occupation, Household member ID, Absent from work/school. Keeps coarse ZIP, vital signs, sheltered status.',
     'plan-application'),
  ('consent.tick_mailin',
     'consent_profile', 'Tick mail-in submission',
     'Suppresses Human-class symptom fields unless submitter has been bitten. Keeps shipping address, species photo, tick attachment metadata.',
     'plan-application'),
  ('consent.wearable_only',
     'consent_profile', 'Wearable-only alert',
     'Records only the digital biomarker parameter and a coarse geo (ZIP). Suppresses name, contact, household, occupation.',
     'plan-application'),
  ('consent.full_followup',
     'consent_profile', 'Full follow-up consent',
     'User consents to be contacted for clinician follow-up; all Figure-2 fields collectable.',
     'plan-application')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('consent.anonymous_heat', 'default_vertical','heat'),
  ('consent.tick_mailin',    'default_vertical','vbd'),
  ('consent.wearable_only',  'default_vertical','heat'),
  ('consent.full_followup',  'default_vertical','both'),
  ('consent.anonymous_heat', 'audit_required','yes'),
  ('consent.tick_mailin',    'audit_required','yes'),
  ('consent.wearable_only',  'audit_required','yes'),
  ('consent.full_followup',  'audit_required','no')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 5. WEARABLE METRIC nodes (digital biomarker codes)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('wearable.skin_temp_c',
     'wearable_metric', 'Skin temperature (degC)',
     'Wrist / chest skin temperature in degrees Celsius. Primary heat-vertical biomarker (lead indicator before core temp rise).',
     'plan-application'),
  ('wearable.hrv_ms',
     'wearable_metric', 'Heart rate variability (RMSSD, ms)',
     'Root mean square of successive RR-interval differences in milliseconds. Drops in early heat stress.',
     'plan-application'),
  ('wearable.heart_rate_bpm',
     'wearable_metric', 'Heart rate (bpm)',
     'Beats per minute from PPG. Resting tachycardia is an early-warning sign in both heat illness and VBD acute febrile illness.',
     'plan-application'),
  ('wearable.sweat_rate_g_h',
     'wearable_metric', 'Sweat rate (g/h)',
     'Sweat output rate; specialty patch sensors (e.g. Epicore, Nix). Drop-off indicates anhidrotic heat stroke.',
     'plan-application'),
  ('wearable.steps_24h',
     'wearable_metric', 'Steps in last 24h',
     'Activity-load proxy that, combined with ambient temp, yields a heat-exposure index for outdoor workers.',
     'plan-application')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('wearable.skin_temp_c',    'unit','degC'),
  ('wearable.hrv_ms',         'unit','ms'),
  ('wearable.heart_rate_bpm', 'unit','bpm'),
  ('wearable.sweat_rate_g_h', 'unit','g/h'),
  ('wearable.steps_24h',      'unit','steps'),
  -- LOINC codes where a clean published code exists; sweat_rate and skin
  -- temperature do not yet have a single canonical LOINC for wrist-derived
  -- continuous monitoring -- flagged as 'pending'.
  ('wearable.heart_rate_bpm', 'loinc_code','8867-4 (Heart rate)'),
  ('wearable.skin_temp_c',    'loinc_code','8310-5 (Body temperature) -- skin-site qualifier needed'),
  ('wearable.hrv_ms',         'loinc_code','80404-7 (R-R interval by EKG) -- closest available; no dedicated RMSSD LOINC'),
  ('wearable.sweat_rate_g_h', 'loinc_code','pending (no canonical LOINC as of 2024)'),
  ('wearable.steps_24h',      'loinc_code','55423-8 (Number of steps in unspecified time Pedometer)'),
  ('wearable.skin_temp_c',    'vertical','heat'),
  ('wearable.hrv_ms',         'vertical','both'),
  ('wearable.heart_rate_bpm', 'vertical','both'),
  ('wearable.sweat_rate_g_h', 'vertical','heat'),
  ('wearable.steps_24h',      'vertical','heat')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 6. REGION nodes (skeleton -- a few AZ regions used by colocatedWith when
--    a finer county / tribe target isn't appropriate). A future seed should
--    expand this set; for now we add only the ones the application emits.
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('region.maricopa_metro',
     'region', 'Phoenix metro (Maricopa County core)',
     'Phoenix metropolitan urbanized core; spans most of Maricopa County. Primary heat-mortality region in AZ.',
     'plan-application'),
  ('region.tucson_metro',
     'region', 'Tucson metro (Pima County core)',
     'Tucson metropolitan urbanized core in Pima County.',
     'plan-application'),
  ('region.colorado_plateau',
     'region', 'Colorado Plateau (Coconino / Apache / Navajo)',
     'Northern AZ high plateau spanning Coconino, Apache, and Navajo counties; plague / hantavirus endemic zone.',
     'plan-application'),
  ('region.border_corridor',
     'region', 'AZ-Mexico border corridor (Yuma, Pima, Santa Cruz, Cochise)',
     'Southern AZ border counties; relevant for cross-border dengue, migrant heat exposure.',
     'plan-application'),
  ('region.statewide',
     'region', 'Statewide (Arizona)',
     'Arizona statewide fallback used when an observation cannot be resolved to a finer geography.',
     'plan-application')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 7. EDGES  (edge_id range: 20000 - 20999)
-- ---------------------------------------------------------------------------

-- 7a. symptom -> code  (crossReferences)  range 20000-20049
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 20000 + row_number() OVER (), subject_id, 'crossReferences', object_id, 'plan-application'
FROM (VALUES
  -- Heat stroke cluster
  ('symptom.confusion',          'code.icd10.t670xxa'),
  ('symptom.confusion',          'code.snomed.heatstroke'),
  ('symptom.hot_dry_skin',       'code.icd10.t670xxa'),
  ('symptom.hot_dry_skin',       'code.snomed.heatstroke'),
  ('symptom.core_temp_elevated', 'code.icd10.t670xxa'),
  ('symptom.core_temp_elevated', 'code.snomed.heatstroke'),
  -- Heat exhaustion / cramp / syncope cluster
  ('symptom.heavy_sweating',     'code.icd10.t675xxa'),
  ('symptom.muscle_cramps',      'code.icd10.t672xxa'),
  ('symptom.dizziness',          'code.icd10.t671xxa'),
  -- Headache: no T67-specific subcode; map to generic "other effects of heat"
  ('symptom.headache',           'code.icd10.t678xxa')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- 7b. consent_profile -> param  (suppressesField)  range 20050-20149
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 20050 + row_number() OVER (), subject_id, 'suppressesField', object_id, 'plan-application'
FROM (VALUES
  -- Anonymous heat check-in suppresses identifying / employer fields
  ('consent.anonymous_heat', 'param.email'),
  ('consent.anonymous_heat', 'param.occupation'),
  ('consent.anonymous_heat', 'param.household_member_id'),
  ('consent.anonymous_heat', 'param.absent_work'),
  ('consent.anonymous_heat', 'param.absent_school'),
  ('consent.anonymous_heat', 'param.phone_number'),
  -- Tick mail-in suppresses Human-class symptom fields by default
  ('consent.tick_mailin',    'param.no_symptoms'),
  ('consent.tick_mailin',    'param.symptoms'),
  ('consent.tick_mailin',    'param.date_of_illness'),
  ('consent.tick_mailin',    'param.cough_congestion'),
  ('consent.tick_mailin',    'param.nausea_vomiting'),
  ('consent.tick_mailin',    'param.difficulty_breathing'),
  ('consent.tick_mailin',    'param.sore_throat'),
  ('consent.tick_mailin',    'param.rash'),
  ('consent.tick_mailin',    'param.fever'),
  ('consent.tick_mailin',    'param.chills'),
  ('consent.tick_mailin',    'param.diarrhea'),
  ('consent.tick_mailin',    'param.bleeding_body_openings'),
  ('consent.tick_mailin',    'param.red_eyes'),
  ('consent.tick_mailin',    'param.muscle_body_aches'),
  ('consent.tick_mailin',    'param.discolored_bloody_urine'),
  ('consent.tick_mailin',    'param.loss_smell_taste'),
  ('consent.tick_mailin',    'param.yellow_skin_eyes'),
  ('consent.tick_mailin',    'param.sought_health_care'),
  -- Wearable-only suppresses everything except digital biomarker + coarse geo
  ('consent.wearable_only',  'param.email'),
  ('consent.wearable_only',  'param.phone_number'),
  ('consent.wearable_only',  'param.occupation'),
  ('consent.wearable_only',  'param.household_member_id'),
  ('consent.wearable_only',  'param.geographical_coordinates'),
  ('consent.wearable_only',  'param.symptoms'),
  ('consent.wearable_only',  'param.no_symptoms'),
  ('consent.wearable_only',  'param.date_of_illness'),
  ('consent.wearable_only',  'param.absent_work'),
  ('consent.wearable_only',  'param.absent_school'),
  ('consent.wearable_only',  'param.sought_health_care'),
  ('consent.wearable_only',  'param.mass_gathering'),
  ('consent.wearable_only',  'param.tick_insect_bite'),
  ('consent.wearable_only',  'param.animal_bite'),
  ('consent.wearable_only',  'param.history_of_travel'),
  ('consent.wearable_only',  'param.contact_live_animals'),
  ('consent.wearable_only',  'param.contact_dead_sick_animals'),
  ('consent.wearable_only',  'param.contact_sick_case')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- 7c. consent_profile -> param  (permitsField)  range 20150-20249
-- Explicit positive-permission lattice for the most restrictive profiles so
-- the intake agent can validate against either side of the suppression rule.
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 20150 + row_number() OVER (), subject_id, 'permitsField', object_id, 'plan-application'
FROM (VALUES
  -- Anonymous heat keeps coarse geo + Human/Aux/Env essentials
  ('consent.anonymous_heat', 'param.age'),
  ('consent.anonymous_heat', 'param.sex'),
  ('consent.anonymous_heat', 'param.postal_code'),
  ('consent.anonymous_heat', 'param.date_of_report'),
  ('consent.anonymous_heat', 'param.symptoms'),
  ('consent.anonymous_heat', 'param.no_symptoms'),
  ('consent.anonymous_heat', 'param.digital_biomarker'),
  -- Tick mail-in keeps Auxiliary (photo, lab) + Environmental
  ('consent.tick_mailin',    'param.photo'),
  ('consent.tick_mailin',    'param.diagnostic_lab'),
  ('consent.tick_mailin',    'param.date_env_incident'),
  ('consent.tick_mailin',    'param.location_vector_spotting'),
  ('consent.tick_mailin',    'param.postal_code'),
  ('consent.tick_mailin',    'param.email'),
  -- Wearable-only keeps biomarker and coarse postal code
  ('consent.wearable_only',  'param.digital_biomarker'),
  ('consent.wearable_only',  'param.postal_code'),
  ('consent.wearable_only',  'param.date_of_report')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- 7d. wearable_metric -> symptom | exposure_factor  (measures)  20250-20299
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 20250 + row_number() OVER (), subject_id, 'measures', object_id, 'plan-application'
FROM (VALUES
  ('wearable.skin_temp_c',    'symptom.core_temp_elevated'),
  ('wearable.skin_temp_c',    'symptom.hot_dry_skin'),
  ('wearable.sweat_rate_g_h', 'symptom.heavy_sweating'),
  ('wearable.sweat_rate_g_h', 'symptom.hot_dry_skin'),
  ('wearable.heart_rate_bpm', 'symptom.dizziness'),
  ('wearable.hrv_ms',         'symptom.confusion'),
  ('wearable.steps_24h',      'exposure.outdoor_time_24h')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 8. CONVENIENCE VIEW
--
-- kg.v_observation_summary pivots the kg.property bag back into a wide row
-- per observation node, plus a JSON-shaped breakdown of outbound edge counts
-- grouped by predicate. The summary is intentionally tolerant of missing
-- property keys (LEFT JOIN on every pivoted column).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW kg.v_observation_summary AS
WITH obs AS (
  SELECT node_id, label, description, source_fig, created_at
  FROM kg.node
  WHERE node_type = 'observation'
),
prop AS (
  SELECT
    node_id,
    MAX(CASE WHEN key = 'vertical'      THEN value_text END) AS vertical,
    MAX(CASE WHEN key = 'source'        THEN value_text END) AS source,
    MAX(CASE WHEN key = 'kind'          THEN value_text END) AS kind,
    MAX(CASE WHEN key = 'reported_at'   THEN value_text END) AS reported_at,
    MAX(CASE WHEN key = 'lat'           THEN value_num  END) AS lat,
    MAX(CASE WHEN key = 'lon'           THEN value_num  END) AS lon,
    MAX(CASE WHEN key = 'age'           THEN value_num  END) AS age,
    MAX(CASE WHEN key = 'sex'           THEN value_text END) AS sex,
    MAX(CASE WHEN key = 'postal_code'   THEN value_text END) AS postal_code,
    MAX(CASE WHEN key = 'occupation'    THEN value_text END) AS occupation,
    MAX(CASE WHEN key = 'contact_email' THEN value_text END) AS contact_email,
    MAX(CASE WHEN key = 'contact_phone' THEN value_text END) AS contact_phone,
    MAX(CASE WHEN key = 'consent_profile' THEN value_text END) AS consent_profile_id
  FROM kg.property
  GROUP BY node_id
),
edge_counts AS (
  SELECT
    subject_id,
    COUNT(*)                                                            AS edges_out_total,
    COUNT(*) FILTER (WHERE predicate = 'reportsAbout')                  AS edges_reports_about,
    COUNT(*) FILTER (WHERE predicate = 'colocatedWith')                 AS edges_colocated_with,
    COUNT(*) FILTER (WHERE predicate = 'gradedAs')                      AS edges_graded_as,
    COUNT(*) FILTER (WHERE predicate = 'measures')                      AS edges_measures,
    COUNT(*) FILTER (WHERE predicate NOT IN
        ('reportsAbout','colocatedWith','gradedAs','measures'))         AS edges_other
  FROM kg.edge
  GROUP BY subject_id
)
SELECT
  o.node_id                          AS observation_id,
  o.label,
  p.kind,
  p.vertical,
  p.source,
  p.reported_at,
  p.lat,
  p.lon,
  p.age,
  p.sex,
  p.postal_code,
  p.occupation,
  p.contact_email,
  p.contact_phone,
  p.consent_profile_id,
  COALESCE(ec.edges_out_total,      0) AS edges_out_total,
  COALESCE(ec.edges_reports_about,  0) AS edges_reports_about,
  COALESCE(ec.edges_colocated_with, 0) AS edges_colocated_with,
  COALESCE(ec.edges_graded_as,      0) AS edges_graded_as,
  COALESCE(ec.edges_measures,       0) AS edges_measures,
  COALESCE(ec.edges_other,          0) AS edges_other,
  o.source_fig,
  o.created_at
FROM obs o
LEFT JOIN prop p        ON p.node_id    = o.node_id
LEFT JOIN edge_counts ec ON ec.subject_id = o.node_id;
