-- ============================================================================
-- EpiHack Arizona 2026 -- MCP servers
--
-- Encodes Model Context Protocol servers (and their underlying APIs) as
-- nodes in the knowledge graph so that they can be discovered via the same
-- queries that surface data resources, datasets, and standards.
--
-- Run after schema/knowledge_graph.sql, schema/wildlife_vectors.sql, and
-- schema/deep/datasets_apis.sql.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- VectorSurv (the upstream API the MCP server wraps)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('resource.vectorsurv',
     'resource_org',
     'VectorSurv (UCD DART)',
     'National vector-borne disease surveillance platform; mosquito and tick collections, pooled testing, arbovirus results. Operated by UC Davis DART (Davis Arbovirus Research and Training).',
     'mcp-vectorsurv'),
  ('api.vectorsurv',
     'api',
     'VectorSurv REST API',
     'OpenAPI 3.0 REST API at api.vectorsurv.org (spec v1.0.44). HTTP Bearer (JWT). Endpoints include /login, /version, /v1/agency, /v1/agency-region-intersect, /v1/site, /v1/region, /v1/arthropod/collection, /v1/tick/collection, /v1/arthropod/pool, /v1/tick/pool, /v1/arthropod/pool/are-positive, /v1/arthropod/abundance/flat, /v1/case-count, /v1/test/target, /v1/test/method, /v1/tick/calculation/abundance. Tokens expire hourly. Filters use Mongoose-style query[field][$gte]/[$lte]/[$in] operators.',
     'mcp-vectorsurv')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('resource.vectorsurv', 'url',          'https://vectorsurv.org/'),
  ('resource.vectorsurv', 'jurisdiction', 'national_research_consortium'),
  ('api.vectorsurv',      'url',          'https://api.vectorsurv.org'),
  ('api.vectorsurv',      'docs_url',     'https://docs.api.vectorsurv.org/'),
  ('api.vectorsurv',      'auth',         'bearer-token (token expires 1 hour)'),
  ('api.vectorsurv',      'format',       'json'),
  ('api.vectorsurv',      'license_or_terms', 'agency-data; access via VectorSurv Gateway account'),
  ('api.vectorsurv',      'auth_required',    'gateway-account')
ON CONFLICT DO NOTHING;

INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (16000, 'api.vectorsurv',      'operatedBy', 'resource.vectorsurv', 'mcp-vectorsurv'),
  (16001, 'resource.vectorsurv', 'informs',    'wv.q1',                'mcp-vectorsurv'),
  (16002, 'resource.vectorsurv', 'informs',    'wv.q2',                'mcp-vectorsurv'),
  (16003, 'resource.vectorsurv', 'informs',    'wv.q4',                'mcp-vectorsurv'),
  -- Maricopa County Vector Control reports to VectorSurv
  (16004, 'resource.mcdph_mcesd','reportsTo',  'resource.vectorsurv', 'mcp-vectorsurv')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- The MCP server itself
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('mcp.vectorsurv',
     'mcp_server',
     'vectorsurv-mcp',
     'Model Context Protocol server that exposes the VectorSurv API as MCP tools an LLM can call. Built for EpiHack Arizona 2026.',
     'mcp-vectorsurv')
ON CONFLICT DO NOTHING;

INSERT INTO kg.property (node_id, key, value_text) VALUES
  ('mcp.vectorsurv', 'language',  'python'),
  ('mcp.vectorsurv', 'transport', 'stdio (default); streamable-http available'),
  ('mcp.vectorsurv', 'path',      'mcp/vectorsurv/'),
  ('mcp.vectorsurv', 'package',   'vectorsurv-mcp'),
  ('mcp.vectorsurv', 'license',   'MIT')
ON CONFLICT DO NOTHING;

INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig) VALUES
  (16010, 'mcp.vectorsurv', 'wraps',  'api.vectorsurv',     'mcp-vectorsurv'),
  (16011, 'mcp.vectorsurv', 'informs','wv.q1',               'mcp-vectorsurv'),
  (16012, 'mcp.vectorsurv', 'informs','wv.q2',               'mcp-vectorsurv'),
  (16013, 'mcp.vectorsurv', 'informs','wv.q3',               'mcp-vectorsurv'),
  (16014, 'mcp.vectorsurv', 'informs','wv.q4',               'mcp-vectorsurv')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- The tools exposed by the MCP server (one node per tool)
-- ---------------------------------------------------------------------------
INSERT INTO kg.node (node_id, node_type, label, description, source_fig) VALUES
  ('mcp_tool.vs_version',                'mcp_tool', 'vectorsurv_version',                  'GET /version.',                                       'mcp-vectorsurv'),
  ('mcp_tool.vs_list_agencies',          'mcp_tool', 'vectorsurv_list_agencies',            'GET /v1/agency.',                                     'mcp-vectorsurv'),
  ('mcp_tool.vs_agency_region',          'mcp_tool', 'vectorsurv_agency_region_intersect',  'GET /v1/agency-region-intersect (geospatial).',       'mcp-vectorsurv'),
  ('mcp_tool.vs_list_regions',           'mcp_tool', 'vectorsurv_list_regions',             'GET /v1/region.',                                     'mcp-vectorsurv'),
  ('mcp_tool.vs_list_test_targets',      'mcp_tool', 'vectorsurv_list_test_targets',        'GET /v1/test/target (pathogen reference + ICD-10).',  'mcp-vectorsurv'),
  ('mcp_tool.vs_list_sites',             'mcp_tool', 'vectorsurv_list_sites',               'GET /v1/site.',                                       'mcp-vectorsurv'),
  ('mcp_tool.vs_get_collections',        'mcp_tool', 'vectorsurv_get_collections',          'GET /v1/arthropod/collection or /v1/tick/collection.','mcp-vectorsurv'),
  ('mcp_tool.vs_get_pools',              'mcp_tool', 'vectorsurv_get_pools',                'GET /v1/arthropod/pool with type=mosquito|tick|nontick.','mcp-vectorsurv'),
  ('mcp_tool.vs_pools_are_positive',     'mcp_tool', 'vectorsurv_pools_are_positive',       'GET /v1/arthropod/pool/are-positive (bulk pathogen status).','mcp-vectorsurv'),
  ('mcp_tool.vs_get_case_counts',        'mcp_tool', 'vectorsurv_get_case_counts',          'GET /v1/case-count (human/equine arbovirus cases).',  'mcp-vectorsurv'),
  ('mcp_tool.vs_calc_abundance',         'mcp_tool', 'vectorsurv_calculate_abundance',      'Client-side: total arthropods / trap-nights.',         'mcp-vectorsurv'),
  ('mcp_tool.vs_calc_ir',                'mcp_tool', 'vectorsurv_calculate_infection_rate', 'Client-side: MIR or bias-corrected MLE.',              'mcp-vectorsurv'),
  ('mcp_tool.vs_calc_vi',                'mcp_tool', 'vectorsurv_calculate_vector_index',   'Client-side: abundance × infection rate.',             'mcp-vectorsurv')
ON CONFLICT DO NOTHING;

-- Base bumped from 16100 to 16200 so a pre-existing partial seed (with
-- the old 7-tool list at 16100-16106) doesn't collide and shadow the
-- new edges via ON CONFLICT DO NOTHING.
INSERT INTO kg.edge (edge_id, subject_id, predicate, object_id, source_fig)
SELECT 16200 + row_number() OVER (), subject_id, 'exposedBy', 'mcp.vectorsurv', 'mcp-vectorsurv'
FROM (VALUES
  ('mcp_tool.vs_version'),
  ('mcp_tool.vs_list_agencies'),
  ('mcp_tool.vs_agency_region'),
  ('mcp_tool.vs_list_regions'),
  ('mcp_tool.vs_list_test_targets'),
  ('mcp_tool.vs_list_sites'),
  ('mcp_tool.vs_get_collections'),
  ('mcp_tool.vs_get_pools'),
  ('mcp_tool.vs_pools_are_positive'),
  ('mcp_tool.vs_get_case_counts'),
  ('mcp_tool.vs_calc_abundance'),
  ('mcp_tool.vs_calc_ir'),
  ('mcp_tool.vs_calc_vi')
) AS t(subject_id)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Convenience view: MCP servers + the APIs they wrap
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW kg.v_mcp_servers AS
SELECT
  s.node_id          AS mcp_id,
  s.label            AS mcp_label,
  s.description      AS mcp_description,
  pkg.value_text     AS package,
  api.node_id        AS api_id,
  api.label          AS api_label,
  url.value_text     AS api_url
FROM kg.node s
LEFT JOIN kg.property pkg ON pkg.node_id = s.node_id AND pkg.key = 'package'
LEFT JOIN kg.edge   w    ON w.subject_id = s.node_id AND w.predicate = 'wraps'
LEFT JOIN kg.node   api  ON api.node_id = w.object_id
LEFT JOIN kg.property url ON url.node_id = api.node_id AND url.key = 'url'
WHERE s.node_type = 'mcp_server';
