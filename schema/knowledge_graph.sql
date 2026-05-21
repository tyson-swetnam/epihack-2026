-- ============================================================================
-- EpiHack Arizona 2026 -- Knowledge Graph Seed Schema
--
-- Target stack:
--   * DuckLake catalog backed by Postgres  (metadata + ACID transactions)
--   * DuckDB                                (query engine, file-format
--                                            agnostic Parquet on object store)
--
-- Bootstrapping example (run in DuckDB):
--
--   INSTALL ducklake;          INSTALL postgres;
--   LOAD ducklake;             LOAD postgres;
--
--   ATTACH 'ducklake:postgres:dbname=epihack host=localhost user=epihack'
--     AS epihack
--     (DATA_PATH 's3://epihack/ducklake/');
--
--   USE epihack;
--   .read schema/knowledge_graph.sql
--
-- The schema below is a property-graph encoding (nodes + edges + property
-- bags) chosen because the EpiHack frameworks are inherently relational
-- (parameters belong to categories, milestones precede other milestones,
-- lifecycle steps precede other steps, etc).
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS kg;

-- ---------------------------------------------------------------------------
-- Nodes (entities): every concept in the knowledge graph
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kg.node (
    node_id     VARCHAR     PRIMARY KEY,   -- stable slug, e.g. 'milestone.detect'
    node_type   VARCHAR     NOT NULL,      -- e.g. 'parameter', 'category',
                                           --      'milestone', 'lifecycle_step',
                                           --      'sector', 'system'
    label       VARCHAR     NOT NULL,
    description VARCHAR,
    source_fig  VARCHAR,                   -- e.g. 'fig-02-data-parameters'
    created_at  TIMESTAMP   DEFAULT current_timestamp
);

-- ---------------------------------------------------------------------------
-- Edges (typed relationships)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kg.edge (
    edge_id     BIGINT      PRIMARY KEY,
    subject_id  VARCHAR     NOT NULL REFERENCES kg.node(node_id),
    predicate   VARCHAR     NOT NULL,      -- e.g. 'belongsTo', 'precedes',
                                           --      'hasMilestone', 'measures'
    object_id   VARCHAR     NOT NULL REFERENCES kg.node(node_id),
    source_fig  VARCHAR
);

-- ---------------------------------------------------------------------------
-- Free-form property bag (typed columns for the common case)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kg.property (
    node_id     VARCHAR     NOT NULL REFERENCES kg.node(node_id),
    key         VARCHAR     NOT NULL,
    value_text  VARCHAR,
    value_num   DOUBLE,
    PRIMARY KEY (node_id, key)
);

-- ===========================================================================
-- SEED: Figure 1 -- Purpose for a One Health Participatory System
-- ===========================================================================
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('system.one_health_participatory',
     'system', 'One Health Participatory System',
     'Community-engaged surveillance system spanning humans, animals, and environment.',
     'fig-01-purpose'),
  ('goal.early_signal_detection',
     'goal',   'Earliest Signal Detection',
     'Detect the earliest signal of a potential epidemic or pandemic threat.',
     'fig-01-purpose'),
  ('sector.humans',      'sector', 'Humans',      NULL, 'fig-01-purpose'),
  ('sector.animals',     'sector', 'Animals',     NULL, 'fig-01-purpose'),
  ('sector.environment', 'sector', 'Environment', NULL, 'fig-01-purpose'),
  ('actor.community',    'actor',  'Community',
     'The population whose direct engagement powers the system.',
     'fig-01-purpose')
ON CONFLICT DO NOTHING;

INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (101, 'system.one_health_participatory', 'hasPurpose',  'goal.early_signal_detection', 'fig-01-purpose'),
  (102, 'goal.early_signal_detection',     'emanatesFrom','sector.humans',               'fig-01-purpose'),
  (103, 'goal.early_signal_detection',     'emanatesFrom','sector.animals',              'fig-01-purpose'),
  (104, 'goal.early_signal_detection',     'emanatesFrom','sector.environment',          'fig-01-purpose'),
  (105, 'system.one_health_participatory', 'engages',     'actor.community',             'fig-01-purpose')
ON CONFLICT DO NOTHING;

-- ===========================================================================
-- SEED: Figure 2 -- Minimum Set of Key Data Parameters
-- ===========================================================================
INSERT INTO kg.node (node_id, node_type, label, source_fig) VALUES
  ('category.general',         'parameter_category', 'General',         'fig-02-data-parameters'),
  ('category.human',           'parameter_category', 'Human',           'fig-02-data-parameters'),
  ('category.severity_marker', 'parameter_category', 'Severity Marker', 'fig-02-data-parameters'),
  ('category.exposure',        'parameter_category', 'Exposure',        'fig-02-data-parameters'),
  ('category.auxiliary',       'parameter_category', 'Auxiliary',       'fig-02-data-parameters'),
  ('category.environmental',   'parameter_category', 'Environmental',   'fig-02-data-parameters'),
  ('category.livestock',       'parameter_category', 'Livestock',       'fig-02-data-parameters'),
  ('category.wildlife',        'parameter_category', 'Wildlife',        'fig-02-data-parameters')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('category.general',       'color', '#5BA3D0'),
  ('category.human',         'color', '#1F3A93'),
  ('category.severity_marker','color','#1F3A93'),
  ('category.exposure',      'color', '#E84A7A'),
  ('category.auxiliary',     'color', '#E6C36A'),
  ('category.environmental', 'color', '#4CAF50'),
  ('category.livestock',     'color', '#C2185B'),
  ('category.wildlife',      'color', '#6A1B9A')
ON CONFLICT DO NOTHING;

INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (201, 'category.severity_marker', 'subCategoryOf', 'category.human', 'fig-02-data-parameters')
ON CONFLICT DO NOTHING;

-- Parameters
INSERT INTO kg.node (node_id, node_type, label, source_fig) VALUES
  -- General
  ('param.age',                    'parameter','Age',                    'fig-02-data-parameters'),
  ('param.sex',                    'parameter','Sex',                    'fig-02-data-parameters'),
  ('param.email',                  'parameter','Email',                  'fig-02-data-parameters'),
  ('param.unique_id',              'parameter','Unique ID',              'fig-02-data-parameters'),
  ('param.occupation',             'parameter','Occupation',             'fig-02-data-parameters'),
  ('param.date_of_report',         'parameter','Date of report',         'fig-02-data-parameters'),
  ('param.postal_code',            'parameter','Postal code',            'fig-02-data-parameters'),
  ('param.phone_number',           'parameter','Phone number',           'fig-02-data-parameters'),
  ('param.household_member_id',    'parameter','Household member ID',    'fig-02-data-parameters'),
  ('param.geographical_coordinates','parameter','Geographical coordinates','fig-02-data-parameters'),
  -- Human
  ('param.no_symptoms',            'parameter','No symptoms',            'fig-02-data-parameters'),
  ('param.symptoms',               'parameter','Symptoms',               'fig-02-data-parameters'),
  ('param.date_of_illness',        'parameter','Date of illness',        'fig-02-data-parameters'),
  ('param.cough_congestion',       'parameter','Cough / congestion',     'fig-02-data-parameters'),
  ('param.nausea_vomiting',        'parameter','Nausea / vomiting',      'fig-02-data-parameters'),
  ('param.difficulty_breathing',   'parameter','Difficulty breathing',   'fig-02-data-parameters'),
  ('param.sore_throat',            'parameter','Sore throat',            'fig-02-data-parameters'),
  ('param.rash',                   'parameter','Rash',                   'fig-02-data-parameters'),
  ('param.fever',                  'parameter','Fever',                  'fig-02-data-parameters'),
  ('param.chills',                 'parameter','Chills',                 'fig-02-data-parameters'),
  ('param.diarrhea',               'parameter','Diarrhea',               'fig-02-data-parameters'),
  ('param.bleeding_body_openings', 'parameter','Bleeding from body openings','fig-02-data-parameters'),
  ('param.red_eyes',               'parameter','Red eyes',               'fig-02-data-parameters'),
  ('param.muscle_body_aches',      'parameter','Muscle or body aches and pains','fig-02-data-parameters'),
  ('param.discolored_bloody_urine','parameter','Discolored or bloody urine','fig-02-data-parameters'),
  ('param.loss_smell_taste',       'parameter','Loss of smell or taste', 'fig-02-data-parameters'),
  ('param.yellow_skin_eyes',       'parameter','Yellow skin / yellow eyes','fig-02-data-parameters'),
  ('param.absent_work',            'parameter','Absent from work',       'fig-02-data-parameters'),
  ('param.absent_school',          'parameter','Absent from school',     'fig-02-data-parameters'),
  ('param.sought_health_care',     'parameter','Did you seek health care or treatment','fig-02-data-parameters'),
  -- Exposure
  ('param.mass_gathering',         'parameter','Attending a recent mass gathering','fig-02-data-parameters'),
  ('param.tick_insect_bite',       'parameter','Tick or insect bite',    'fig-02-data-parameters'),
  ('param.animal_bite',            'parameter','Animal bite',            'fig-02-data-parameters'),
  ('param.history_of_travel',      'parameter','History of travel',      'fig-02-data-parameters'),
  ('param.contact_live_animals',   'parameter','Contact with live animals','fig-02-data-parameters'),
  ('param.contact_dead_sick_animals','parameter','Contact with dead or sick animals','fig-02-data-parameters'),
  ('param.contact_sick_case',      'parameter','Contact with sick individual / confirmed case','fig-02-data-parameters'),
  -- Auxiliary
  ('param.digital_biomarker',      'parameter','Digital biomarker signal','fig-02-data-parameters'),
  ('param.photo',                  'parameter','Photo',                  'fig-02-data-parameters'),
  ('param.diagnostic_lab',         'parameter','Diagnostic / lab confirmation','fig-02-data-parameters'),
  -- Environmental
  ('param.date_env_incident',      'parameter','Date of environmental incident','fig-02-data-parameters'),
  ('param.location_vector_spotting','parameter','Location of vector spotting','fig-02-data-parameters'),
  ('param.unusual_vectors',        'parameter','Unusual presence of vectors','fig-02-data-parameters'),
  ('param.vector_density',         'parameter','Density or number of vectors','fig-02-data-parameters'),
  ('param.flooding',               'parameter','Flooding',               'fig-02-data-parameters'),
  ('param.water_contamination',    'parameter','Water contamination',    'fig-02-data-parameters'),
  -- Livestock
  ('param.date_livestock_incident','parameter','Date of livestock incident','fig-02-data-parameters'),
  ('param.location_livestock_incident','parameter','Location of livestock incident','fig-02-data-parameters'),
  ('param.livestock_sick_count',   'parameter','Number of sick animals (livestock)','fig-02-data-parameters'),
  ('param.livestock_dead_count',   'parameter','Number of dead animals (livestock)','fig-02-data-parameters'),
  ('param.livestock_species',      'parameter','Species (livestock)',    'fig-02-data-parameters'),
  -- Wildlife
  ('param.date_wildlife_incident', 'parameter','Date of wildlife incident','fig-02-data-parameters'),
  ('param.location_wildlife_incident','parameter','Location of wildlife incident','fig-02-data-parameters'),
  ('param.wildlife_species',       'parameter','Species (wildlife)',     'fig-02-data-parameters'),
  ('param.wildlife_dead_count',    'parameter','Number of dead animals (wildlife)','fig-02-data-parameters')
ON CONFLICT DO NOTHING;

-- parameter -> category edges
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 1000 + row_number() OVER (), subject_id, 'belongsTo', object_id, 'fig-02-data-parameters'
FROM (VALUES
  ('param.age','category.general'),
  ('param.sex','category.general'),
  ('param.email','category.general'),
  ('param.unique_id','category.general'),
  ('param.occupation','category.general'),
  ('param.date_of_report','category.general'),
  ('param.postal_code','category.general'),
  ('param.phone_number','category.general'),
  ('param.household_member_id','category.general'),
  ('param.geographical_coordinates','category.general'),
  ('param.no_symptoms','category.human'),
  ('param.symptoms','category.human'),
  ('param.date_of_illness','category.human'),
  ('param.cough_congestion','category.human'),
  ('param.nausea_vomiting','category.human'),
  ('param.difficulty_breathing','category.human'),
  ('param.sore_throat','category.human'),
  ('param.rash','category.human'),
  ('param.fever','category.human'),
  ('param.chills','category.human'),
  ('param.diarrhea','category.human'),
  ('param.bleeding_body_openings','category.severity_marker'),
  ('param.red_eyes','category.human'),
  ('param.muscle_body_aches','category.human'),
  ('param.discolored_bloody_urine','category.severity_marker'),
  ('param.loss_smell_taste','category.human'),
  ('param.yellow_skin_eyes','category.severity_marker'),
  ('param.absent_work','category.human'),
  ('param.absent_school','category.human'),
  ('param.sought_health_care','category.human'),
  ('param.mass_gathering','category.exposure'),
  ('param.tick_insect_bite','category.exposure'),
  ('param.animal_bite','category.exposure'),
  ('param.history_of_travel','category.exposure'),
  ('param.contact_live_animals','category.exposure'),
  ('param.contact_dead_sick_animals','category.exposure'),
  ('param.contact_sick_case','category.exposure'),
  ('param.digital_biomarker','category.auxiliary'),
  ('param.photo','category.auxiliary'),
  ('param.diagnostic_lab','category.auxiliary'),
  ('param.date_env_incident','category.environmental'),
  ('param.location_vector_spotting','category.environmental'),
  ('param.unusual_vectors','category.environmental'),
  ('param.vector_density','category.environmental'),
  ('param.flooding','category.environmental'),
  ('param.water_contamination','category.environmental'),
  ('param.date_livestock_incident','category.livestock'),
  ('param.location_livestock_incident','category.livestock'),
  ('param.livestock_sick_count','category.livestock'),
  ('param.livestock_dead_count','category.livestock'),
  ('param.livestock_species','category.livestock'),
  ('param.date_wildlife_incident','category.wildlife'),
  ('param.location_wildlife_incident','category.wildlife'),
  ('param.wildlife_species','category.wildlife'),
  ('param.wildlife_dead_count','category.wildlife')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ===========================================================================
-- SEED: Figure 3 -- Outbreak Timeliness Metrics
-- ===========================================================================
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('milestone.predict',  'milestone','Predict','Date a reliable and valid predictive alert is available.','fig-03-timeliness'),
  ('milestone.prevent',  'milestone','Prevent','Date enhanced surveillance / intervention is initiated in response to a predictive alert.','fig-03-timeliness'),
  ('milestone.detect',   'milestone','Detect','Date symptom onset, death, or other evidence of pathogen circulation is observed or suspected.','fig-03-timeliness'),
  ('milestone.notify',   'milestone','Notify','Date an outbreak is officially reported to relevant authorities.','fig-03-timeliness'),
  ('milestone.verify',   'milestone','Verify','Date outbreak is confirmed by field investigation or other valid method.','fig-03-timeliness'),
  ('milestone.lab_confirm','milestone','Diagnostic Test / Lab Confirmation','Date outbreak is confirmed by diagnostic or laboratory test.','fig-03-timeliness'),
  ('milestone.respond',  'milestone','Respond','Date an intervention to control or manage the outbreak is initiated.','fig-03-timeliness'),
  ('milestone.public_comm','milestone','Public Communication','Date of official release of information to the public.','fig-03-timeliness'),
  ('milestone.outbreak_start','milestone','Outbreak Start','Date symptom onset or death occurs in the earliest epidemiologically-linked case.','fig-03-timeliness'),
  ('milestone.outbreak_end','milestone','Outbreak End','Date outbreak is declared closed by a responsible authority.','fig-03-timeliness'),
  ('milestone.aar',      'milestone','After Action Review','Date after action review is jointly conducted by relevant One Health authorities.','fig-03-timeliness')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_num) VALUES
  ('milestone.predict',         'ordinal',  1),
  ('milestone.prevent',         'ordinal',  2),
  ('milestone.detect',          'ordinal',  3),
  ('milestone.notify',          'ordinal',  4),
  ('milestone.verify',          'ordinal',  5),
  ('milestone.lab_confirm',     'ordinal',  6),
  ('milestone.respond',         'ordinal',  7),
  ('milestone.public_comm',     'ordinal',  8),
  ('milestone.outbreak_start',  'ordinal',  9),
  ('milestone.outbreak_end',    'ordinal', 10),
  ('milestone.aar',             'ordinal', 11)
ON CONFLICT DO NOTHING;

-- ===========================================================================
-- SEED: Figure 4 -- Designing & Launching Participatory Surveillance
-- ===========================================================================
INSERT INTO kg.node (node_id, node_type, label, source_fig) VALUES
  ('step.01_assess_needs',          'lifecycle_step','Assess Needs of Community',         'fig-04-design-launch'),
  ('step.02_determine_purpose',     'lifecycle_step','Determine Purpose of System',       'fig-04-design-launch'),
  ('step.03_identify_stakeholders', 'lifecycle_step','Identify Stakeholders',             'fig-04-design-launch'),
  ('step.04_ascertain_resources',   'lifecycle_step','Ascertain Resources',               'fig-04-design-launch'),
  ('step.05_co_design',             'lifecycle_step','Co-Design System',                  'fig-04-design-launch'),
  ('step.06_test_prototypes',       'lifecycle_step','Test Prototypes & Finalize Product','fig-04-design-launch'),
  ('step.07_launch',                'lifecycle_step','Launch the System',                 'fig-04-design-launch'),
  ('step.08_validate_data',         'lifecycle_step','Validate Data',                     'fig-04-design-launch'),
  ('step.09_awareness',             'lifecycle_step','Create Awareness Campaigns',        'fig-04-design-launch'),
  ('step.10_train_recruiters',      'lifecycle_step','Train Recruiters',                  'fig-04-design-launch'),
  ('step.11_incentivize_retain',    'lifecycle_step','Incentivize & Retain Users',        'fig-04-design-launch'),
  ('step.12_monitor_evaluate',      'lifecycle_step','Monitor, Evaluate & Adapt System',  'fig-04-design-launch')
ON CONFLICT DO NOTHING;

INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 4000 + row_number() OVER (), subject_id, 'precedes', object_id, 'fig-04-design-launch'
FROM (VALUES
  ('step.01_assess_needs',          'step.02_determine_purpose'),
  ('step.02_determine_purpose',     'step.03_identify_stakeholders'),
  ('step.03_identify_stakeholders', 'step.04_ascertain_resources'),
  ('step.04_ascertain_resources',   'step.05_co_design'),
  ('step.05_co_design',             'step.06_test_prototypes'),
  ('step.06_test_prototypes',       'step.07_launch'),
  ('step.07_launch',                'step.08_validate_data'),
  ('step.08_validate_data',         'step.09_awareness'),
  ('step.09_awareness',             'step.10_train_recruiters'),
  ('step.10_train_recruiters',      'step.11_incentivize_retain'),
  ('step.11_incentivize_retain',    'step.12_monitor_evaluate')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;
