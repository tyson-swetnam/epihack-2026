// EpiHack Arizona 2026 — pre-written queries for the DuckDB-WASM viewer.
//
// These run in the browser against the *public reference* knowledge graph
// (kg.node / kg.edge / kg.property) loaded from schema/*.sql + schema/deep/*.sql
// — the same property-graph the read-only knowledge-graph-mcp serves. They do
// NOT touch individual reports/observations (those live in the Mongo mobile
// store and the DuckLake operational tables, never shipped to the public site).
//
// Each query is intentionally a single SELECT/WITH statement so it round-trips
// through the SELECT-only guard in app.js, mirroring the kg_sql escape hatch.
// Slugs and predicates were validated against the seeds; see CLAUDE.md.

window.EPIHACK_QUERIES = [
  // ---------------------------------------------------------------- Overview
  {
    category: "Overview",
    name: "Node inventory by type",
    desc: "How many entities of each kind are in the graph.",
    sql: `SELECT node_type, COUNT(*) AS nodes
FROM kg.node
GROUP BY node_type
ORDER BY nodes DESC;`,
  },
  {
    category: "Overview",
    name: "Edge predicate frequency",
    desc: "Which typed relationships are most common.",
    sql: `SELECT predicate, COUNT(*) AS edges
FROM kg.edge
GROUP BY predicate
ORDER BY edges DESC;`,
  },
  {
    category: "Overview",
    name: "Search nodes by label",
    desc: "Free-text search over labels + descriptions. Edit the term.",
    sql: `SELECT node_id, node_type, label
FROM kg.node
WHERE label ILIKE '%tick%' OR description ILIKE '%tick%'
ORDER BY node_type, label;`,
  },
  {
    category: "Overview",
    name: "All properties for one node",
    desc: "The full property bag for a single slug. Edit node_id.",
    sql: `SELECT key,
       COALESCE(value_text, CAST(value_num AS VARCHAR)) AS value
FROM kg.property
WHERE node_id = 'pathogen.wnv'
ORDER BY key;`,
  },

  // -------------------------------------------------------- Pathogens & vectors
  {
    category: "Pathogens & vectors",
    name: "Notifiable pathogens (ICD-10 + class)",
    desc: "AZ/NNDSS-reportable pathogens with their classification.",
    sql: `SELECT n.label AS pathogen,
       MAX(CASE WHEN p.key='pathogen_class'  THEN p.value_text END) AS class,
       MAX(CASE WHEN p.key='icd10'           THEN p.value_text END) AS icd10,
       MAX(CASE WHEN p.key='endemic_in_az'   THEN p.value_text END) AS endemic_in_az
FROM kg.node n
JOIN kg.property p USING (node_id)
WHERE n.node_type = 'pathogen'
  AND n.node_id IN (
        SELECT node_id FROM kg.property
        WHERE key='notifiable' AND value_text ILIKE 'yes%')
GROUP BY n.label
ORDER BY pathogen;`,
  },
  {
    category: "Pathogens & vectors",
    name: "Pathogen → vector transmission",
    desc: "Which vectors transmit which pathogens.",
    sql: `SELECT s.label AS pathogen, o.label AS vector
FROM kg.edge e
JOIN kg.node s ON s.node_id = e.subject_id
JOIN kg.node o ON o.node_id = e.object_id
WHERE e.predicate = 'transmittedBy'
ORDER BY pathogen, vector;`,
  },
  {
    category: "Pathogens & vectors",
    name: "Pathogen → disease it causes",
    desc: "Clinical syndrome each pathogen is mapped to.",
    sql: `SELECT s.label AS pathogen, o.label AS disease
FROM kg.edge e
JOIN kg.node s ON s.node_id = e.subject_id AND s.node_type='pathogen'
JOIN kg.node o ON o.node_id = e.object_id  AND o.node_type='disease'
WHERE e.predicate = 'causes'
ORDER BY pathogen;`,
  },
  {
    category: "Pathogens & vectors",
    name: "Who surveils each pathogen",
    desc: "Agencies / labs / programs that surveil each pathogen.",
    sql: `SELECT s.label AS pathogen, o.label AS surveilled_by, o.node_type AS org_kind
FROM kg.edge e
JOIN kg.node s ON s.node_id = e.subject_id AND s.node_type='pathogen'
JOIN kg.node o ON o.node_id = e.object_id
WHERE e.predicate = 'surveilledBy'
ORDER BY pathogen, surveilled_by;`,
  },

  // ------------------------------------------------------------------- Outbreaks
  {
    category: "Outbreaks",
    name: "Historical outbreaks by location",
    desc: "Recorded outbreaks and where they occurred, newest first.",
    sql: `SELECT o.label AS outbreak,
       loc.label AS location,
       MAX(CASE WHEN pr.key='start_date' THEN pr.value_text END) AS start_date,
       MAX(CASE WHEN pr.key='total_cases' THEN pr.value_num END) AS total_cases
FROM kg.edge e
JOIN kg.node o   ON o.node_id = e.subject_id AND o.node_type='outbreak'
JOIN kg.node loc ON loc.node_id = e.object_id
LEFT JOIN kg.property pr ON pr.node_id = o.node_id
WHERE e.predicate = 'occurredIn'
GROUP BY o.label, loc.label
ORDER BY start_date DESC NULLS LAST;`,
  },

  // ------------------------------------------------------------------- Geography
  {
    category: "Geography",
    name: "Counties: population, FIPS, seat",
    desc: "All 15 Arizona counties, largest population first.",
    sql: `SELECT n.label AS county,
       MAX(CASE WHEN p.key='fips'             THEN p.value_text END) AS fips,
       MAX(CASE WHEN p.key='county_seat'      THEN p.value_text END) AS county_seat,
       MAX(CASE WHEN p.key='population_approx' THEN p.value_num END)  AS population
FROM kg.node n
LEFT JOIN kg.property p USING (node_id)
WHERE n.node_type = 'county'
GROUP BY n.label
ORDER BY population DESC NULLS LAST;`,
  },
  {
    category: "Geography",
    name: "Tribal nations (public reference)",
    desc: "Federally recognized nations in the graph by enrolled membership. Suppressed health attributes are never published here.",
    sql: `SELECT n.label AS nation,
       MAX(CASE WHEN p.key='enrolled_membership_approx' THEN p.value_num END) AS enrolled_members
FROM kg.node n
LEFT JOIN kg.property p USING (node_id)
WHERE n.node_type = 'tribal_nation'
GROUP BY n.label
ORDER BY enrolled_members DESC NULLS LAST;`,
  },

  // ------------------------------------------------------------ Data & systems
  {
    category: "Data & systems",
    name: "Datasets & APIs inventory",
    desc: "Upstream data sources with cadence, auth, and link.",
    sql: `SELECT n.node_type,
       n.label,
       MAX(CASE WHEN p.key='update_cadence' THEN p.value_text END) AS cadence,
       MAX(CASE WHEN p.key='auth_required'  THEN p.value_text END) AS auth,
       MAX(CASE WHEN p.key='url'            THEN p.value_text END) AS url
FROM kg.node n
LEFT JOIN kg.property p USING (node_id)
WHERE n.node_type IN ('dataset','api')
GROUP BY n.node_type, n.label
ORDER BY n.node_type, n.label;`,
  },
  {
    category: "Data & systems",
    name: "MCP servers & their tools",
    desc: "Each MCP tool and the server that exposes it.",
    sql: `SELECT srv.label AS server, tool.label AS tool
FROM kg.edge e
JOIN kg.node tool ON tool.node_id = e.subject_id AND tool.node_type='mcp_tool'
JOIN kg.node srv  ON srv.node_id  = e.object_id  AND srv.node_type='mcp_server'
WHERE e.predicate = 'exposedBy'
ORDER BY server, tool;`,
  },

  // ---------------------------------------------------- Standards & privacy
  {
    category: "Standards & privacy",
    name: "Standards crosswalk (codes)",
    desc: "ICD-10 / SNOMED / LOINC codes mapped to graph entities.",
    sql: `SELECT s.label AS entity, e.predicate, o.node_type AS code_system, o.label AS code
FROM kg.edge e
JOIN kg.node s ON s.node_id = e.subject_id
JOIN kg.node o ON o.node_id = e.object_id
WHERE e.predicate IN ('mappedTo','identifiedBy','crossReferences')
  AND o.node_type IN ('icd10_code','snomed_concept','loinc_concept')
ORDER BY entity
LIMIT 100;`,
  },
  {
    category: "Standards & privacy",
    name: "Consent profiles: suppressed fields",
    desc: "Privacy contract — which parameters each consent profile suppresses at write time.",
    sql: `SELECT cp.label AS consent_profile, prm.label AS suppressed_parameter
FROM kg.edge e
JOIN kg.node cp  ON cp.node_id = e.subject_id AND cp.node_type='consent_profile'
JOIN kg.node prm ON prm.node_id = e.object_id
WHERE e.predicate = 'suppressesField'
ORDER BY consent_profile, suppressed_parameter;`,
  },
  {
    category: "Standards & privacy",
    name: "Triage classes (routing, not diagnosis)",
    desc: "The next-action routing classes by severity.",
    sql: `SELECT n.label AS triage_class,
       MAX(CASE WHEN p.key='severity' THEN p.value_text END) AS severity,
       MAX(CASE WHEN p.key='vertical' THEN p.value_text END) AS vertical
FROM kg.node n
LEFT JOIN kg.property p USING (node_id)
WHERE n.node_type = 'triage_class'
GROUP BY n.label
ORDER BY severity, triage_class;`,
  },
];
