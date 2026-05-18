-- ============================================================================
-- EpiHack Arizona 2026 -- World Café notes
--
-- Captures the World Café Q4 cards as "engagement_example" nodes attached
-- to a "world_cafe_question" node, with focus-area links.
-- Run *after* schema/knowledge_graph.sql and schema/system_designs.sql.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- New focus areas surfaced in Q4 cards
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, source_fig) VALUES
  ('focus.extreme_heat',         'focus_area', 'Extreme heat',              'world-cafe-q4'),
  ('focus.environmental_health', 'focus_area', 'Environmental health',      'world-cafe-q4'),
  ('focus.information_flow',     'focus_area', 'Information flow',          'world-cafe-q4'),
  ('focus.public_communication', 'focus_area', 'Public communication',      'world-cafe-q4')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- The World Café question itself
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('wc.q4',
     'world_cafe_question',
     'World Café Q4',
     'What is an example of directly engaging with the public that was really successful?',
     'world-cafe-q4')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_num) VALUES
  ('wc.q4', 'question_number', 4)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- The three Q4 cards (engagement_example nodes)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, source_fig) VALUES
  ('wc.q4.heat',             'engagement_example', 'Heat (pink card)',                       'note-wc-q4-heat'),
  ('wc.q4.unhoused',         'engagement_example', 'Unhoused (blue card)',                   'note-wc-q4-unhoused'),
  ('wc.q4.information_flow', 'engagement_example', 'Information Flow (yellow card)',         'note-wc-q4-information-flow')
ON CONFLICT DO NOTHING;

-- Card -> question
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (6000, 'wc.q4.heat',             'answers', 'wc.q4', 'note-wc-q4-heat'),
  (6001, 'wc.q4.unhoused',         'answers', 'wc.q4', 'note-wc-q4-unhoused'),
  (6002, 'wc.q4.information_flow', 'answers', 'wc.q4', 'note-wc-q4-information-flow')
ON CONFLICT DO NOTHING;

-- Card -> focus area
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 6100 + row_number() OVER (), subject_id, 'targetsFocusArea', object_id, source_fig
FROM (VALUES
  ('wc.q4.heat',             'focus.extreme_heat',          'note-wc-q4-heat'),
  ('wc.q4.heat',             'focus.environmental_health',  'note-wc-q4-heat'),
  ('wc.q4.unhoused',         'focus.unhoused',              'note-wc-q4-unhoused'),
  ('wc.q4.unhoused',         'focus.urban_public_health',   'note-wc-q4-unhoused'),
  ('wc.q4.information_flow', 'focus.information_flow',      'note-wc-q4-information-flow'),
  ('wc.q4.information_flow', 'focus.public_communication',  'note-wc-q4-information-flow')
) AS t(subject_id, object_id, source_fig)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Individual engagement tactics within each card
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  -- Heat
  ('tactic.heat.community_event',   'engagement_tactic', 'Community Event → outreach',
     'Use community events as the on-ramp for outreach activities.', 'note-wc-q4-heat'),
  ('tactic.heat.train_the_trainer', 'engagement_tactic', 'Train-the-Trainer (Region 9, 12-year-old program)',
     'Train-the-trainer program through Western Regional Public Health (HHS Region 9); the program is 12 years old.', 'note-wc-q4-heat'),
  ('tactic.heat.media',             'engagement_tactic', 'Speak to media → syndication',
     'Single media appearance scaled through viral or national syndication.', 'note-wc-q4-heat'),
  ('tactic.heat.network_dissemination','engagement_tactic','Disseminate via existing networks (FFA)',
     'Lean on existing member-based networks (e.g. Future Farmers of America) rather than building new ones.', 'note-wc-q4-heat'),
  ('tactic.heat.canvassing',        'engagement_tactic', 'Targeted door-to-door canvassing',
     'Door-to-door canvassing informed by the prior year''s surveillance data.', 'note-wc-q4-heat'),
  ('tactic.heat.chw_assessment',    'engagement_tactic', 'Community Health Worker home heat-risk assessments',
     'CHWs perform in-home heat-risk assessments.', 'note-wc-q4-heat'),
  -- Unhoused
  ('tactic.unhoused.healthy_companions','engagement_tactic','Healthy Companions Program',
     'Pet vaccination + zoonotic-disease awareness; healthy owner ↔ healthy pet; cell-phone check as a public-housing on-ramp.', 'note-wc-q4-unhoused'),
  ('tactic.unhoused.heat_surveillance','engagement_tactic','Heat Surveillance (Maricopa Co.)',
     'Resource-allocation alignment for extreme-heat response in Maricopa County.', 'note-wc-q4-unhoused'),
  ('tactic.unhoused.shelter_app',   'engagement_tactic', 'Shelter App (location-based)',
     'Location-based shelter discovery and services.', 'note-wc-q4-unhoused'),
  -- Information Flow
  ('tactic.if.face_to_face',        'engagement_tactic', 'Face-to-face / go-to-them outreach',
     'Physical presence as highest-bandwidth engagement channel.', 'note-wc-q4-information-flow'),
  ('tactic.if.sms_reminders',       'engagement_tactic', 'SMS reminders via cell-phone network',
     'Leverage existing mobile network for reminders.', 'note-wc-q4-information-flow'),
  ('tactic.if.board_of_supervisors','engagement_tactic', 'Engage Board of Supervisors',
     'County political engagement unlocks downstream channels.', 'note-wc-q4-information-flow'),
  ('tactic.if.geo_alerts',          'engagement_tactic', 'Geolocated emergency health alerts',
     'Emergency health alerts targeted by geolocation.', 'note-wc-q4-information-flow'),
  ('tactic.if.emr_epic_tmc',        'engagement_tactic', 'EMR messaging (Epic in collaboration with TMC)',
     'Embed messaging in the EMR — Epic EMRs in collaboration with Tucson Medical Center.', 'note-wc-q4-information-flow'),
  ('tactic.if.dating_apps_sti',     'engagement_tactic', 'Dating apps ↔ STI services (exploratory)',
     'Partnership between dating apps and STI testing/treatment services; flagged as exploratory on the original card.', 'note-wc-q4-information-flow')
ON CONFLICT DO NOTHING;

-- Tactic -> card
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 6200 + row_number() OVER (), subject_id, 'partOf', object_id, source_fig
FROM (VALUES
  ('tactic.heat.community_event',       'wc.q4.heat',             'note-wc-q4-heat'),
  ('tactic.heat.train_the_trainer',     'wc.q4.heat',             'note-wc-q4-heat'),
  ('tactic.heat.media',                 'wc.q4.heat',             'note-wc-q4-heat'),
  ('tactic.heat.network_dissemination', 'wc.q4.heat',             'note-wc-q4-heat'),
  ('tactic.heat.canvassing',            'wc.q4.heat',             'note-wc-q4-heat'),
  ('tactic.heat.chw_assessment',        'wc.q4.heat',             'note-wc-q4-heat'),
  ('tactic.unhoused.healthy_companions','wc.q4.unhoused',         'note-wc-q4-unhoused'),
  ('tactic.unhoused.heat_surveillance', 'wc.q4.unhoused',         'note-wc-q4-unhoused'),
  ('tactic.unhoused.shelter_app',       'wc.q4.unhoused',         'note-wc-q4-unhoused'),
  ('tactic.if.face_to_face',            'wc.q4.information_flow', 'note-wc-q4-information-flow'),
  ('tactic.if.sms_reminders',           'wc.q4.information_flow', 'note-wc-q4-information-flow'),
  ('tactic.if.board_of_supervisors',    'wc.q4.information_flow', 'note-wc-q4-information-flow'),
  ('tactic.if.geo_alerts',              'wc.q4.information_flow', 'note-wc-q4-information-flow'),
  ('tactic.if.emr_epic_tmc',            'wc.q4.information_flow', 'note-wc-q4-information-flow'),
  ('tactic.if.dating_apps_sti',         'wc.q4.information_flow', 'note-wc-q4-information-flow')
) AS t(subject_id, object_id, source_fig)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Convenience view: all engagement tactics with their focus areas
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW kg.v_engagement_tactics AS
SELECT
  t.node_id     AS tactic_id,
  t.label       AS tactic,
  t.description AS detail,
  c.label       AS card,
  string_agg(f.label, ', ') AS focus_areas
FROM kg.node t
JOIN kg.edge te ON te.subject_id = t.node_id AND te.predicate = 'partOf'
JOIN kg.node c  ON c.node_id = te.object_id
LEFT JOIN kg.edge ce ON ce.subject_id = c.node_id AND ce.predicate = 'targetsFocusArea'
LEFT JOIN kg.node f  ON f.node_id = ce.object_id
WHERE t.node_type = 'engagement_tactic'
GROUP BY t.node_id, t.label, t.description, c.label;
