-- ============================================================================
-- EpiHack Arizona 2026 -- Cluster-detection followups
--
-- Closes the eight historical-outbreak gaps the cluster-detection
-- calibration sub-agent itemised in `plan/CLUSTER-CALIBRATION.md`.
-- Concretely, this seed marks the small set of pathogens for which one
-- confirmed case constitutes a Detect event regardless of the spatio-
-- temporal count threshold. The detector reads this flag at runtime
-- (see ClusterDetectionAgent Tier A in agents/src/onehealth_agents/
-- cluster.py).
--
-- Conventions
--   * Property key:    `single_case_alertable` (stored as value_num=1
--                      because schema.knowledge_graph.kg.property only has
--                      text + numeric columns; convention 1 == true).
--   * Edge ID range:   50000 .. 50999  (reserved for this seed)
--   * source_fig:      'deep-cluster-followups'
--   * All inserts idempotent (ON CONFLICT DO NOTHING).
--
-- Run order
--   .read schema/knowledge_graph.sql         (must run first - kg tables)
--   .read schema/deep/pathogens.sql          (sibling - pathogen.* nodes)
--   .read schema/deep/outbreaks.sql          (sibling - historical record)
--   .read schema/deep/cluster_followups.sql  (this file)
--
-- Why these five pathogens?
--   * pathogen.yersinia_pestis    -- plague. CFR ~50% untreated; one
--                                    case (Coconino 2025) is a Detect
--                                    event. Closes coconino_plague_2025.
--   * pathogen.snv                -- Sin Nombre / hantavirus. CFR ~38%;
--                                    historically Detect-on-first-case in
--                                    AZ public-health practice (cf. ADHS
--                                    HAN advisory 2024-07-08). Helps with
--                                    az_hantavirus_2023 / _2024 alongside
--                                    Tier B county scan.
--   * pathogen.rabies_lyssavirus  -- human rabies. CFR ~100%; AZ
--                                    statute requires per-case
--                                    investigation.
--   * pathogen.francisella_tularensis -- tularaemia; bioterrorism Cat A;
--                                    very rare in AZ so any confirmed
--                                    human case is a Detect event.
--   * pathogen.rickettsia_rickettsii -- RMSF. NOT a true single-case
--                                    alert in the wider US, but in AZ
--                                    tribal communities the chronic
--                                    endemic baseline + tribal-data
--                                    suppression mean a single non-MOU
--                                    case warrants escalation. See the
--                                    Tier C chronic-baseline drift
--                                    detector for the complementary
--                                    rule.
-- Anthrax (pathogen.bacillus_anthracis) is intentionally omitted -- the
-- node is not present in schema/deep/pathogens.sql. If it is added later,
-- a follow-up seed should mark it single_case_alertable too.
-- ============================================================================

INSERT INTO kg.property (node_id, key, value_num) VALUES
  ('pathogen.yersinia_pestis',        'single_case_alertable', 1),
  ('pathogen.snv',                    'single_case_alertable', 1),
  ('pathogen.rabies_lyssavirus',      'single_case_alertable', 1),
  ('pathogen.francisella_tularensis', 'single_case_alertable', 1),
  ('pathogen.rickettsia_rickettsii',  'single_case_alertable', 1)
ON CONFLICT DO NOTHING;

-- Rationale strings (free-text key) so an analyst querying the kg can
-- see *why* each pathogen is flagged without reading this file.
INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('pathogen.yersinia_pestis',
     'single_case_alertable_rationale',
     'Pneumonic plague CFR ~50% untreated; locally enzootic in N. AZ '
     '(prairie dogs, deer mice). Detect-on-first-case per Coconino HHS '
     'practice (2025-07 case).'),
  ('pathogen.snv',
     'single_case_alertable_rationale',
     'Hantavirus pulmonary syndrome CFR ~38%. ADHS HAN advisory '
     '2024-07-08 treats each lab-confirmed case as a Detect event.'),
  ('pathogen.rabies_lyssavirus',
     'single_case_alertable_rationale',
     'Human rabies CFR ~100% once symptomatic. AZ statute requires '
     'per-case investigation.'),
  ('pathogen.francisella_tularensis',
     'single_case_alertable_rationale',
     'Tularaemia is a CDC Category-A select agent. AZ averages <3 '
     'human cases/year; any confirmed case is a Detect event.'),
  ('pathogen.rickettsia_rickettsii',
     'single_case_alertable_rationale',
     'RMSF in AZ has CFR ~6%, far above the US average. Tribal-data '
     'suppression caps the conventional cluster signal, so a single '
     'confirmed non-MOU case is treated as Detect-worthy.')
ON CONFLICT DO NOTHING;

-- Edge: each pathogen --has--> reusable cluster-rule node, so an
-- analyst can ask "what rules apply to pathogen.X?" via a kg query.
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('cluster_rule.single_case_high_cfr',
     'cluster_rule',
     'Single-case high-CFR alert',
     'Emit a ClusterAlert (cluster_kind="single_case", '
     'rule_tripped="single_case_high_cfr") whenever a confirmed '
     'observation in the trailing 30 days is linked to a pathogen '
     'flagged single_case_alertable=true. Bypasses the count and '
     'posterior thresholds.',
     'deep-cluster-followups'),
  ('cluster_rule.county_poisson_scan',
     'cluster_rule',
     'County x week Poisson scan',
     'Run the same Tier-1 / Tier-2 Poisson logic the ZCTA-week scan '
     'uses, but at county granularity. Tunable separately '
     '(theta_county=2.0, k_county=3). Catches small-denominator '
     'multi-county clusters (hantavirus 2023/2024, WNV 2003).',
     'deep-cluster-followups'),
  ('cluster_rule.chronic_baseline_drift',
     'cluster_rule',
     'Chronic-baseline drift detector',
     'For pathogens with documented chronic endemic baselines, compare '
     'the trailing 12-month rate against the historical 10-year rate; '
     'emit when trailing > 1.25 x historical. Sensitivity capped by '
     'tribal-data suppression (cf. RMSF tribal outbreak).',
     'deep-cluster-followups'),
  ('cluster_rule.travel_import_cluster',
     'cluster_rule',
     'Travel-import cluster detector',
     'When >= 5 observations in a trailing 30-day window list a '
     'history_of_travel exposure and a shared destination country '
     '(or all imported, in the absence of destination data), emit '
     'cluster_kind="travel_import_cluster". Catches travel-imported '
     'scatter such as az_chikungunya_2014.',
     'deep-cluster-followups')
ON CONFLICT DO NOTHING;

INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 50000 + row_number() OVER (), subject_id, 'governedBy', object_id,
       'deep-cluster-followups'
FROM (VALUES
  ('pathogen.yersinia_pestis',        'cluster_rule.single_case_high_cfr'),
  ('pathogen.snv',                    'cluster_rule.single_case_high_cfr'),
  ('pathogen.rabies_lyssavirus',      'cluster_rule.single_case_high_cfr'),
  ('pathogen.francisella_tularensis', 'cluster_rule.single_case_high_cfr'),
  ('pathogen.rickettsia_rickettsii',  'cluster_rule.single_case_high_cfr'),
  -- Chronic-baseline rule applies only to the endemic RMSF.
  ('pathogen.rickettsia_rickettsii',  'cluster_rule.chronic_baseline_drift'),
  -- Travel-import rule is most directly relevant to imported arboviruses.
  ('pathogen.chikv',                  'cluster_rule.travel_import_cluster'),
  ('pathogen.denv',                   'cluster_rule.travel_import_cluster'),
  ('pathogen.zikv',                   'cluster_rule.travel_import_cluster')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;
