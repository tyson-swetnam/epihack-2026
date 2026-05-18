-- ============================================================================
-- EpiHack Arizona 2026 -- System-design extension
--
-- Adds nodes for the breakout-session worksheet instances and the focus
-- areas they target. Run *after* schema/knowledge_graph.sql.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Focus areas (a worksheet targets one or more of these)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, source_fig) VALUES
  ('focus.animal_health',           'focus_area', 'Animal health events',                   'epihack-az-2026'),
  ('focus.zoonotic_surveillance',   'focus_area', 'Zoonotic surveillance',                  'epihack-az-2026'),
  ('focus.wildlife',                'focus_area', 'Wildlife',                               'epihack-az-2026'),
  ('focus.urban_wildlife_interface','focus_area', 'Urban-wildlife interface',               'epihack-az-2026'),
  ('focus.hobby_farms',             'focus_area', 'Hobby farms',                            'epihack-az-2026'),
  ('focus.unhoused',                'focus_area', 'Unhoused / people experiencing homelessness','epihack-az-2026'),
  ('focus.urban_public_health',     'focus_area', 'Urban public health',                    'epihack-az-2026')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Worksheet template (Figure 5) and its prompts
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, source_fig) VALUES
  ('template.worksheet_v1', 'worksheet_template', 'OH Participatory Surveillance Design Worksheet v1', 'fig-05-design-worksheet-template')
ON CONFLICT DO NOTHING;

INSERT INTO kg.node (node_id, node_type, label, source_fig) VALUES
  ('prompt.purpose',           'prompt', 'Purpose of system',          'fig-05-design-worksheet-template'),
  ('prompt.target_population', 'prompt', 'Target population',          'fig-05-design-worksheet-template'),
  ('prompt.bidirectionality',  'prompt', 'What given back (bi-dir)',   'fig-05-design-worksheet-template'),
  ('prompt.parameter_changes', 'prompt', 'Parameter add/remove',       'fig-05-design-worksheet-template'),
  ('prompt.access',            'prompt', 'Access / barriers',          'fig-05-design-worksheet-template'),
  ('prompt.frequency',         'prompt', 'Report frequency',           'fig-05-design-worksheet-template'),
  ('prompt.duration',          'prompt', 'Time per report',            'fig-05-design-worksheet-template'),
  ('prompt.partners',          'prompt', 'Key partners',               'fig-05-design-worksheet-template'),
  ('prompt.validation',        'prompt', 'Validation / verification',  'fig-05-design-worksheet-template'),
  ('prompt.elevator_pitch',    'prompt', 'Elevator pitch',             'fig-05-design-worksheet-template')
ON CONFLICT DO NOTHING;

-- Prompt -> lifecycle step mapping (from Figure 4)
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 5000 + row_number() OVER (), subject_id, 'addresses', object_id, 'fig-05-design-worksheet-template'
FROM (VALUES
  ('prompt.purpose',           'step.02_determine_purpose'),
  ('prompt.target_population', 'step.02_determine_purpose'),
  ('prompt.bidirectionality',  'step.01_assess_needs'),
  ('prompt.parameter_changes', 'step.05_co_design'),
  ('prompt.access',            'step.09_awareness'),
  ('prompt.frequency',         'step.05_co_design'),
  ('prompt.duration',          'step.05_co_design'),
  ('prompt.partners',          'step.03_identify_stakeholders'),
  ('prompt.validation',        'step.08_validate_data'),
  ('prompt.elevator_pitch',    'step.09_awareness')
) AS t(subject_id, object_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- System designs (completed worksheet instances)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('design.animal_health_events',
     'system_design',
     'Unusual Animal Health Events as Early Warning Signal',
     'Capture unusual animal health events reported by animal owners and caretakers as an early-warning signal for human public health.',
     'design-01-animal-health-events'),
  ('design.desert_wildlife_interface',
     'system_design',
     'Desert Urban Wildlife & Hobby-Farm Interface',
     'Detect unusual disease changes in desert urban wildlife and hobby-farm animals at the urban-wildlife interface.',
     'design-02-desert-wildlife-interface'),
  ('design.unhoused_healthy_companions',
     'system_design_concept',
     'Unhoused: Healthy Companions / Heat Surveillance / Shelter App',
     'Brainstorm bundle for participatory surveillance with people experiencing homelessness in Maricopa County.',
     'note-01-unhoused')
ON CONFLICT DO NOTHING;

-- Designs target focus areas
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 5100 + row_number() OVER (), subject_id, 'targetsFocusArea', object_id, source_fig
FROM (VALUES
  ('design.animal_health_events',       'focus.animal_health',            'design-01-animal-health-events'),
  ('design.animal_health_events',       'focus.zoonotic_surveillance',    'design-01-animal-health-events'),
  ('design.desert_wildlife_interface',  'focus.wildlife',                 'design-02-desert-wildlife-interface'),
  ('design.desert_wildlife_interface',  'focus.urban_wildlife_interface', 'design-02-desert-wildlife-interface'),
  ('design.desert_wildlife_interface',  'focus.hobby_farms',              'design-02-desert-wildlife-interface'),
  ('design.unhoused_healthy_companions','focus.unhoused',                 'note-01-unhoused'),
  ('design.unhoused_healthy_companions','focus.urban_public_health',      'note-01-unhoused')
) AS t(subject_id, object_id, source_fig)
ON CONFLICT DO NOTHING;

-- Designs instantiate the template
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (5200, 'design.animal_health_events',      'instantiates', 'template.worksheet_v1', 'design-01-animal-health-events'),
  (5201, 'design.desert_wildlife_interface', 'instantiates', 'template.worksheet_v1', 'design-02-desert-wildlife-interface')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Worksheet answers as properties (one row per (design, prompt))
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kg.design_answer (
    design_id   VARCHAR     NOT NULL REFERENCES kg.node(node_id),
    prompt_id   VARCHAR     NOT NULL REFERENCES kg.node(node_id),
    answer      VARCHAR     NOT NULL,
    PRIMARY KEY (design_id, prompt_id)
);

INSERT INTO kg.design_answer (design_id, prompt_id, answer) VALUES
  ('design.animal_health_events', 'prompt.purpose',
     'Capture and track unusual animal health events as an early-warning signal for public health.'),
  ('design.animal_health_events', 'prompt.target_population',
     'Animal owners and caretakers.'),
  ('design.animal_health_events', 'prompt.frequency',
     'As often as you see something, say something; reports filtered by PH for action.'),
  ('design.animal_health_events', 'prompt.duration',
     '~10 minutes or less.'),
  ('design.animal_health_events', 'prompt.elevator_pitch',
     'Multi-disciplinary platform for animal owners/caretakers to report unusual animal health events; provides education and veterinary resources back; clustered events trigger PH or veterinary action.'),
  ('design.desert_wildlife_interface', 'prompt.purpose',
     'Detect unusual changes in wildlife and domestic animals that may signal disease emergence.'),
  ('design.desert_wildlife_interface', 'prompt.target_population',
     'Desert urban wildlife observers and hobby farmers at the urban-wildlife interface.'),
  ('design.desert_wildlife_interface', 'prompt.frequency',
     'Bi-monthly (low burden).'),
  ('design.desert_wildlife_interface', 'prompt.duration',
     '5-7 minutes per report.'),
  ('design.desert_wildlife_interface', 'prompt.elevator_pitch',
     'Early-warning system connecting farmers and veterinarians with human/animal health experts; community-protective.')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Convenience view: design answers as a wide table
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW kg.v_design_summary AS
SELECT
  d.node_id     AS design_id,
  d.label       AS design_label,
  d.description AS design_description,
  MAX(CASE WHEN a.prompt_id = 'prompt.purpose'           THEN a.answer END) AS purpose,
  MAX(CASE WHEN a.prompt_id = 'prompt.target_population' THEN a.answer END) AS target_population,
  MAX(CASE WHEN a.prompt_id = 'prompt.frequency'         THEN a.answer END) AS frequency,
  MAX(CASE WHEN a.prompt_id = 'prompt.duration'          THEN a.answer END) AS duration,
  MAX(CASE WHEN a.prompt_id = 'prompt.elevator_pitch'    THEN a.answer END) AS elevator_pitch
FROM kg.node d
LEFT JOIN kg.design_answer a ON a.design_id = d.node_id
WHERE d.node_type IN ('system_design','system_design_concept')
GROUP BY d.node_id, d.label, d.description;
