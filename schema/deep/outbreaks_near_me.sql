-- ============================================================================
-- EpiHack Arizona 2026 -- Outbreaks Near Me (Boston Children's / HealthMap)
--
-- Adds the Outbreaks Near Me citizen-science participatory-surveillance
-- platform as a resource_org and dataset, with edges to the vector-borne
-- and zoonotic focus areas plus the Figure-3 Detect milestone (which is
-- the milestone OBNM most directly improves).
--
-- The full text rationale lives in wildlife/resources.md.
--
-- Run order: after schema/knowledge_graph.sql, schema/wildlife_vectors.sql,
-- and schema/deep/datasets_apis.sql.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Nodes
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('resource.outbreaks_near_me',
     'resource_org',
     'Outbreaks Near Me (Boston Children''s Hospital / HealthMap)',
     'US-wide participatory symptom-surveillance platform; successor to Flu Near You (2011-2022). Public self-reports fever, cough, GI signs, rashes, fatigue; aggregated to ZIP-code symptom-cluster map. Operated by Dr. John Brownstein''s team.',
     'plan-outbreaks-near-me'),
  ('api.outbreaks_near_me',
     'dataset',
     'Outbreaks Near Me public symptom-cluster feed',
     'Public-facing aggregated symptom-cluster reports by ZIP code. No documented machine-readable API at time of writing; the public site at outbreaksnearme.org is the integration surface and a future federation should go through the HealthMap team directly.',
     'plan-outbreaks-near-me')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('resource.outbreaks_near_me', 'url',          'https://outbreaksnearme.org/us/en-US'),
  ('resource.outbreaks_near_me', 'jurisdiction', 'national_citizen_science'),
  ('resource.outbreaks_near_me', 'operator',     'Boston Children''s Hospital / HealthMap'),
  ('resource.outbreaks_near_me', 'predecessor',  'Flu Near You (2011-2022)'),
  ('api.outbreaks_near_me',      'url',                  'https://outbreaksnearme.org/us/en-US'),
  ('api.outbreaks_near_me',      'format',               'web'),
  ('api.outbreaks_near_me',      'update_cadence',       'near-real-time (user self-report)'),
  ('api.outbreaks_near_me',      'license_or_terms',     'public-facing; partnership with HealthMap for federated access'),
  ('api.outbreaks_near_me',      'auth_required',        'none for public map; partnership required for raw feed')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Edges
-- ---------------------------------------------------------------------------
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (60001, 'api.outbreaks_near_me',      'operatedBy', 'resource.outbreaks_near_me', 'plan-outbreaks-near-me'),
  (60002, 'resource.outbreaks_near_me', 'informs',    'wv.q4',                       'plan-outbreaks-near-me'),
  (60003, 'resource.outbreaks_near_me', 'informs',    'heat.q4',                     'plan-outbreaks-near-me'),
  -- Symptom-side surveillance most directly improves the Figure-3 Detect
  -- milestone: a community report fires before any agency case report does.
  (60004, 'resource.outbreaks_near_me', 'improvesMilestone', 'milestone.detect',     'plan-outbreaks-near-me'),
  -- Cross-references to the focus areas it touches.
  (60005, 'resource.outbreaks_near_me', 'targetsFocusArea', 'focus.zoonotic',        'plan-outbreaks-near-me'),
  (60006, 'resource.outbreaks_near_me', 'targetsFocusArea', 'focus.vector_borne',    'plan-outbreaks-near-me'),
  -- Sibling / benchmark relationship to the AZ One Health Sentinel design.
  (60007, 'design.az_one_health_sentinel', 'inspiredBy', 'resource.outbreaks_near_me', 'plan-outbreaks-near-me')
ON CONFLICT DO NOTHING;
