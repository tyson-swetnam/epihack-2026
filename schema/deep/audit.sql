-- ============================================================================
-- EpiHack Arizona 2026 -- Deep dive: Agent-runtime audit log
--
-- Purpose
--   One row per agent invocation, written by the orchestrator's audit sink
--   (agents/src/onehealth_agents/audit.py). Together with the per-observation
--   timeliness pivot view at the bottom of this file, the table is the
--   anchor for the Figure 3 timeliness milestones described in
--   figures/03-outbreak-timeliness-metrics.md and Phase 3 of plan/05-roadmap.md.
--
-- Run order
--   .read schema/knowledge_graph.sql          -- kg.node / kg.edge / kg.property
--   .read schema/deep/application.sql         -- observation node_type + tc.*
--   .read schema/deep/audit.sql               -- this file
--
-- Conventions
--   * Engine:        DuckDB (DuckLake-backed in production; in-memory in tests).
--   * Idempotency:   every INSERT in this file uses ON CONFLICT DO NOTHING.
--   * Edge IDs:      40000 .. 40999 reserved for any seeded edges here.
--   * source_fig:    'agent-runtime' for every row this file introduces.
--   * Outcome enum:  'success' / 'degraded' / 'error' (mirrors the AgentRun
--                    pydantic model; the audit sink maps the model's status
--                    Literal -- 'ok'/'degraded'/'failed' -- onto this enum).
--   * Agent-to-milestone mapping for the Figure-3 pivot view (see below):
--       intake        -> Detect      (community signal lands in the system)
--       validation    -> Notify      (system has accepted / flagged it for
--                                     downstream authorities)
--       triage        -> Verify      (PROVISIONAL: shifted-by-future-human-review;
--                                     the operational Figure-3 Verify milestone
--                                     is owned by ADHS field investigation and
--                                     this column should NOT be confused with it)
--       enrichment    -> Lab         (PROVISIONAL: only fully populated once
--                                     diagnostic / lab MCP edges hydrate;
--                                     ADHS lab confirmation is the canonical
--                                     Figure-3 Lab milestone)
--       notification  -> Respond     (the system-initiated response action --
--                                     user push, CHW dispatch, agency pin)
--
--   The Verify and Lab columns in kg.v_observation_timeliness are explicitly
--   marked "PROVISIONAL" because the corresponding Figure-3 milestones in
--   figures/03-outbreak-timeliness-metrics.md are owned by human authorities
--   (ADHS, AZGFD) rather than by the agent pipeline. Downstream evaluation
--   should treat them as a system-side proxy that is later overwritten or
--   joined with the human-confirmed timestamp.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. agent_run -- one row per agent invocation
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kg.agent_run (
    run_id                 VARCHAR    PRIMARY KEY,                -- uuid
    agent_name             VARCHAR    NOT NULL,                   -- matches the agent module name
    observation_id         VARCHAR,                               -- FK -> kg.node(node_id) where node_type = 'observation'
    started_at             TIMESTAMP  NOT NULL,
    ended_at               TIMESTAMP,
    duration_ms            DOUBLE,
    model_id               VARCHAR,                               -- e.g. 'claude-haiku-4-5', 'claude-sonnet-4-6'
    prompt_tokens          INTEGER,
    completion_tokens      INTEGER,
    cache_read_tokens      INTEGER,
    cache_creation_tokens  INTEGER,
    cost_usd               DOUBLE,
    outcome                VARCHAR,                               -- 'success' / 'degraded' / 'error'
    input_digest           VARCHAR,                               -- sha256 of canonical-JSON input
    output_digest          VARCHAR,                               -- sha256 of canonical-JSON output
    error_message          VARCHAR,
    source_fig             VARCHAR    DEFAULT 'agent-runtime'
);

-- Helpful secondary indexes -- DuckDB supports them on regular tables.
CREATE INDEX IF NOT EXISTS idx_agent_run_observation
    ON kg.agent_run (observation_id);
CREATE INDEX IF NOT EXISTS idx_agent_run_agent_name
    ON kg.agent_run (agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_run_started_at
    ON kg.agent_run (started_at);

-- ---------------------------------------------------------------------------
-- 2. kg.v_observation_timeliness -- pivot of agent_run rows into the
--    Figure-3 milestone timestamps and the interval-in-minutes columns
--    between adjacent milestones.
--
--    Agent -> milestone mapping (see header for caveats):
--        intake        -> Detect
--        validation    -> Notify
--        triage        -> Verify       (provisional / shifted-by-human-review)
--        enrichment    -> Lab          (provisional / shifted-by-human-review)
--        notification  -> Respond
--
--    Each milestone column takes the MIN(started_at) across runs of that
--    agent for the observation. Interval columns are NULL when either side
--    of the join is unobserved (e.g. a notification never went out because
--    validation rejected the report).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW kg.v_observation_timeliness AS
WITH per_obs AS (
    SELECT
        observation_id,
        MIN(CASE WHEN agent_name = 'intake'       THEN started_at END) AS detect_at,
        MIN(CASE WHEN agent_name = 'validation'   THEN started_at END) AS notify_at,
        MIN(CASE WHEN agent_name = 'triage'       THEN started_at END) AS verify_at_provisional,
        MIN(CASE WHEN agent_name = 'enrichment'   THEN started_at END) AS lab_at_provisional,
        MIN(CASE WHEN agent_name = 'notification' THEN started_at END) AS respond_at
    FROM kg.agent_run
    WHERE observation_id IS NOT NULL
    GROUP BY observation_id
)
SELECT
    observation_id,
    detect_at,
    notify_at,
    verify_at_provisional,
    lab_at_provisional,
    respond_at,
    -- Adjacent-milestone intervals (minutes).
    date_diff('minute', detect_at,              notify_at)             AS detect_to_notify_min,
    date_diff('minute', notify_at,              verify_at_provisional) AS notify_to_verify_min,
    date_diff('minute', verify_at_provisional,  lab_at_provisional)    AS verify_to_lab_min,
    date_diff('minute', lab_at_provisional,     respond_at)            AS lab_to_respond_min,
    -- End-to-end span (Detect -> Respond) as a convenience aggregate.
    date_diff('minute', detect_at,              respond_at)            AS detect_to_respond_min
FROM per_obs;

-- ---------------------------------------------------------------------------
-- 3. kg.v_agent_run_cost -- per-day, per-agent rollup of cost & tokens
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW kg.v_agent_run_cost AS
SELECT
    CAST(started_at AS DATE)                          AS day,
    agent_name,
    COUNT(*)                                          AS run_count,
    COALESCE(SUM(prompt_tokens),         0)           AS prompt_tokens_total,
    COALESCE(SUM(completion_tokens),     0)           AS completion_tokens_total,
    COALESCE(SUM(cache_read_tokens),     0)           AS cache_read_tokens_total,
    COALESCE(SUM(cache_creation_tokens), 0)           AS cache_creation_tokens_total,
    COALESCE(SUM(cost_usd),              0.0)         AS cost_usd_total
FROM kg.agent_run
GROUP BY day, agent_name
ORDER BY day DESC, agent_name;

-- ---------------------------------------------------------------------------
-- 4. kg.v_agent_run_failures -- recent non-success rows for ops dashboards
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW kg.v_agent_run_failures AS
SELECT
    run_id,
    agent_name,
    observation_id,
    started_at,
    ended_at,
    duration_ms,
    model_id,
    outcome,
    error_message
FROM kg.agent_run
WHERE outcome IS NOT NULL
  AND outcome <> 'success'
ORDER BY started_at DESC;
