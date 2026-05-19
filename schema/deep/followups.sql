-- ============================================================================
-- EpiHack Arizona 2026 -- Follow-ups for Phase 0 / Phase 1
--
-- Patches the small gaps that the Phase 0 sub-agents flagged in
-- plan/EXECUTION-STATUS.md. All inserts are ON CONFLICT DO NOTHING so this
-- file is idempotent and safe to run after every other deep/ seed.
--
-- Run order: after every other schema/deep/*.sql file.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Missing SNOMED CT codes for heat illness (catalog completion).
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('code.snomed.heat_exhaustion',
     'snomed_concept',
     'SNOMED CT 84362002 Heat exhaustion (disorder)',
     NULL,
     'deep-followups'),
  ('code.snomed.heat_cramp',
     'snomed_concept',
     'SNOMED CT 52613005 Heat cramps (disorder)',
     NULL,
     'deep-followups'),
  ('code.snomed.heat_syncope',
     'snomed_concept',
     'SNOMED CT 24079001 Heat syncope (disorder)',
     NULL,
     'deep-followups')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('code.snomed.heat_exhaustion','code','84362002'),
  ('code.snomed.heat_exhaustion','system','SNOMED CT'),
  ('code.snomed.heat_cramp',      'code','52613005'),
  ('code.snomed.heat_cramp',      'system','SNOMED CT'),
  ('code.snomed.heat_syncope',    'code','24079001'),
  ('code.snomed.heat_syncope',    'system','SNOMED CT')
ON CONFLICT DO NOTHING;

INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 30000 + row_number() OVER (), subject_id, predicate, object_id, 'deep-followups'
FROM (VALUES
  ('code.snomed.heat_exhaustion', 'definedIn', 'standard.snomed_ct'),
  ('code.snomed.heat_cramp',      'definedIn', 'standard.snomed_ct'),
  ('code.snomed.heat_syncope',    'definedIn', 'standard.snomed_ct'),
  ('code.snomed.heat_exhaustion', 'mappedTo',  'focus.heat_morbidity'),
  ('code.snomed.heat_cramp',      'mappedTo',  'focus.heat_morbidity'),
  ('code.snomed.heat_syncope',    'mappedTo',  'focus.heat_morbidity'),
  -- crossReferences from application.sql symptom nodes (defined in
  -- schema/deep/application.sql; this just adds the SNOMED side):
  ('symptom.heavy_sweating', 'crossReferences', 'code.snomed.heat_exhaustion'),
  ('symptom.dizziness',      'crossReferences', 'code.snomed.heat_syncope'),
  ('symptom.muscle_cramps',  'crossReferences', 'code.snomed.heat_cramp')
) AS t(subject_id, predicate, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. LOINC codes for wearable observations
--    (referenced by wearable_metric.* nodes in deep/application.sql).
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('code.loinc.heart_rate',
     'loinc_concept',
     'LOINC 8867-4 Heart rate',
     'Beats per minute, instantaneous.',
     'deep-followups'),
  ('code.loinc.body_temperature',
     'loinc_concept',
     'LOINC 8310-5 Body temperature',
     'Temperature in degrees Celsius or Fahrenheit.',
     'deep-followups'),
  ('code.loinc.skin_temperature',
     'loinc_concept',
     'LOINC 8328-7 Skin temperature',
     'Wearable-class skin-surface temperature.',
     'deep-followups'),
  ('code.loinc.heart_rate_variability_sdnn',
     'loinc_concept',
     'LOINC 80404-7 R-R interval SDNN (heart rate variability)',
     'Standard deviation of NN intervals.',
     'deep-followups'),
  ('code.loinc.steps_24h',
     'loinc_concept',
     'LOINC 41950-7 Number of steps in 24 hour Measured',
     '24-hour step count.',
     'deep-followups')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('code.loinc.heart_rate',                    'code','8867-4'),
  ('code.loinc.heart_rate',                    'system','LOINC'),
  ('code.loinc.body_temperature',              'code','8310-5'),
  ('code.loinc.body_temperature',              'system','LOINC'),
  ('code.loinc.skin_temperature',              'code','8328-7'),
  ('code.loinc.skin_temperature',              'system','LOINC'),
  ('code.loinc.heart_rate_variability_sdnn',   'code','80404-7'),
  ('code.loinc.heart_rate_variability_sdnn',   'system','LOINC'),
  ('code.loinc.steps_24h',                     'code','41950-7'),
  ('code.loinc.steps_24h',                     'system','LOINC')
ON CONFLICT DO NOTHING;

INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 30100 + row_number() OVER (), subject_id, predicate, object_id, 'deep-followups'
FROM (VALUES
  ('code.loinc.heart_rate',                  'definedIn','standard.loinc'),
  ('code.loinc.body_temperature',            'definedIn','standard.loinc'),
  ('code.loinc.skin_temperature',            'definedIn','standard.loinc'),
  ('code.loinc.heart_rate_variability_sdnn', 'definedIn','standard.loinc'),
  ('code.loinc.steps_24h',                   'definedIn','standard.loinc'),
  -- crossReferences from the wearable_metric nodes (defined in
  -- schema/deep/application.sql).
  ('wearable.heart_rate_bpm', 'crossReferences','code.loinc.heart_rate'),
  ('wearable.skin_temp_c',    'crossReferences','code.loinc.skin_temperature'),
  ('wearable.hrv_ms',         'crossReferences','code.loinc.heart_rate_variability_sdnn'),
  ('wearable.steps_24h',      'crossReferences','code.loinc.steps_24h')
) AS t(subject_id, predicate, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3. lat / lon properties for county.* and tribe.* nodes so that
--    knowledge-graph-mcp.kg_regions_at_point returns hits.
--    Source: map/data.js county-seat / reservation-centroid coordinates.
-- ---------------------------------------------------------------------------
INSERT INTO kg.property (node_id, key, value_num) VALUES
  -- Counties (county-seat coordinates from map/data.js).
  ('county.apache',      'lat',  34.50), ('county.apache',      'lon', -109.36),
  ('county.cochise',     'lat',  31.45), ('county.cochise',     'lon', -109.93),
  ('county.coconino',    'lat',  35.20), ('county.coconino',    'lon', -111.65),
  ('county.gila',        'lat',  33.39), ('county.gila',        'lon', -110.79),
  ('county.graham',      'lat',  32.83), ('county.graham',      'lon', -109.71),
  ('county.greenlee',    'lat',  33.05), ('county.greenlee',    'lon', -109.30),
  ('county.la_paz',      'lat',  34.15), ('county.la_paz',      'lon', -114.29),
  ('county.maricopa',    'lat',  33.45), ('county.maricopa',    'lon', -112.07),
  ('county.mohave',      'lat',  35.19), ('county.mohave',      'lon', -114.05),
  ('county.navajo',      'lat',  34.90), ('county.navajo',      'lon', -110.16),
  ('county.pima',        'lat',  32.22), ('county.pima',        'lon', -110.93),
  ('county.pinal',       'lat',  33.03), ('county.pinal',       'lon', -111.39),
  ('county.santa_cruz',  'lat',  31.34), ('county.santa_cruz',  'lon', -110.94),
  ('county.yavapai',     'lat',  34.54), ('county.yavapai',     'lon', -112.47),
  ('county.yuma',        'lat',  32.69), ('county.yuma',        'lon', -114.62),
  -- Tribes (reservation centroids from map/data.js).
  ('tribe.ak_chin',                  'lat', 32.95), ('tribe.ak_chin',                  'lon', -112.05),
  ('tribe.cocopah',                  'lat', 32.62), ('tribe.cocopah',                  'lon', -114.78),
  ('tribe.crit',                     'lat', 34.05), ('tribe.crit',                     'lon', -114.30),
  ('tribe.fort_mcdowell',            'lat', 33.62), ('tribe.fort_mcdowell',            'lon', -111.65),
  ('tribe.fort_mojave',              'lat', 35.05), ('tribe.fort_mojave',              'lon', -114.60),
  ('tribe.quechan',                  'lat', 32.74), ('tribe.quechan',                  'lon', -114.60),
  ('tribe.gila_river',               'lat', 33.20), ('tribe.gila_river',               'lon', -111.95),
  ('tribe.havasupai',                'lat', 36.25), ('tribe.havasupai',                'lon', -112.70),
  ('tribe.hopi',                     'lat', 35.95), ('tribe.hopi',                     'lon', -110.50),
  ('tribe.hualapai',                 'lat', 35.55), ('tribe.hualapai',                 'lon', -113.50),
  ('tribe.kaibab_paiute',            'lat', 36.95), ('tribe.kaibab_paiute',            'lon', -112.65),
  ('tribe.navajo',                   'lat', 36.30), ('tribe.navajo',                   'lon', -109.80),
  ('tribe.pascua_yaqui',             'lat', 32.15), ('tribe.pascua_yaqui',             'lon', -111.05),
  ('tribe.zuni',                     'lat', 34.30), ('tribe.zuni',                     'lon', -109.05),
  ('tribe.salt_river',               'lat', 33.55), ('tribe.salt_river',               'lon', -111.85),
  ('tribe.san_carlos_apache',        'lat', 33.40), ('tribe.san_carlos_apache',        'lon', -110.10),
  ('tribe.san_juan_southern_paiute', 'lat', 36.85), ('tribe.san_juan_southern_paiute', 'lon', -111.60),
  ('tribe.tohono_oodham',            'lat', 32.10), ('tribe.tohono_oodham',            'lon', -111.65),
  ('tribe.tonto_apache',             'lat', 34.21), ('tribe.tonto_apache',             'lon', -111.34),
  ('tribe.white_mountain_apache',    'lat', 33.85), ('tribe.white_mountain_apache',    'lon', -110.00),
  ('tribe.yavapai_apache',           'lat', 34.70), ('tribe.yavapai_apache',           'lon', -111.85),
  ('tribe.yavapai_prescott',         'lat', 34.55), ('tribe.yavapai_prescott',         'lon', -112.50)
ON CONFLICT DO NOTHING;
