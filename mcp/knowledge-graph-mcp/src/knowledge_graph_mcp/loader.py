"""Bootstrap a DuckDB connection with the EpiHack knowledge-graph schema.

Two operating modes:

* **In-memory (default).** Open a fresh in-memory DuckDB and replay
  every ``.sql`` file under ``$KG_SCHEMA_PATH`` (defaults to
  ``../../schema`` relative to this package). Useful for development,
  CI, and the MCP server running on a contributor's laptop without
  any external infrastructure.

* **Attached DuckLake.** When ``KG_DUCKLAKE_URI`` is set (e.g.
  ``ducklake:postgres:dbname=epihack host=localhost user=epihack``),
  install + load the ``ducklake`` and ``postgres`` extensions, attach
  the catalog, and ``USE`` it instead of seeding from SQL files.
  ``KG_DUCKLAKE_DATA_PATH`` is forwarded as the ``DATA_PATH`` attach
  option when present.

Schema files are loaded in a deterministic order matching the
project's documentation -- the top-level overview files first
(``knowledge_graph.sql`` -> ``system_designs.sql`` -> ``world_cafe.sql``
-> ``wildlife_vectors.sql`` -> ``heat.sql``) followed by every
``deep/*.sql`` in alphabetical order. Files that error are logged and
skipped so a single broken seed doesn't take the server down.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import duckdb

log = logging.getLogger(__name__)

# Top-level schema files in the canonical load order. Everything under
# `deep/` is appended in alphabetical order afterwards.
TOP_LEVEL_ORDER = (
    "knowledge_graph.sql",
    "system_designs.sql",
    "world_cafe.sql",
    "wildlife_vectors.sql",
    "heat.sql",
)


def _default_schema_path() -> Path:
    """Resolve the default schema path: ``<repo>/schema``.

    From this file ``src/knowledge_graph_mcp/loader.py`` the parent
    chain runs:
      parents[0] = knowledge_graph_mcp/
      parents[1] = src/
      parents[2] = knowledge-graph-mcp/
      parents[3] = mcp/
      parents[4] = <repo root>
    """
    here = Path(__file__).resolve()
    return here.parents[4] / "schema"


def discover_schema_files(schema_root: Path) -> list[Path]:
    """Return the ordered list of ``.sql`` files to apply.

    Order: canonical top-level files (skipping any that are missing),
    then every ``deep/*.sql`` alphabetically, then any other top-level
    ``.sql`` files we didn't already enumerate (for forward-compat with
    new seeds).
    """
    if not schema_root.is_dir():
        log.warning("KG schema directory not found: %s", schema_root)
        return []

    ordered: list[Path] = []
    seen: set[Path] = set()

    for name in TOP_LEVEL_ORDER:
        candidate = schema_root / name
        if candidate.is_file():
            ordered.append(candidate)
            seen.add(candidate)

    # Any other top-level .sql files we haven't enumerated yet.
    extras = sorted(
        p for p in schema_root.glob("*.sql") if p not in seen
    )
    for p in extras:
        ordered.append(p)
        seen.add(p)

    deep_dir = schema_root / "deep"
    if deep_dir.is_dir():
        # `deep/standards.sql` and `deep/pathogens.sql` must load before
        # the files that FK-reference them (`deep/application.sql` ->
        # SNOMED/ICD-10 codes; `deep/outbreaks.sql` -> pathogens).
        # Pin those first; everything else stays alphabetical.
        DEEP_ORDER = ("standards.sql", "pathogens.sql")
        for name in DEEP_ORDER:
            candidate = deep_dir / name
            if candidate.is_file() and candidate not in seen:
                ordered.append(candidate)
                seen.add(candidate)
        for p in sorted(deep_dir.glob("*.sql")):
            if p not in seen:
                ordered.append(p)
                seen.add(p)

    return ordered


def _apply_sql_file(conn: duckdb.DuckDBPyConnection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    conn.execute(sql)


def load_in_memory(
    schema_root: Path | None = None,
) -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB and replay every schema file."""
    root = schema_root or _default_schema_path()
    conn = duckdb.connect(":memory:")
    files = discover_schema_files(root)
    if not files:
        log.warning(
            "No SQL files found under %s; the kg schema will be empty.", root
        )
        return conn
    loaded = 0
    for path in files:
        try:
            _apply_sql_file(conn, path)
            loaded += 1
        except Exception as exc:  # noqa: BLE001 -- one bad file != fatal
            log.warning("Skipping %s: %s", path, exc)
    log.info("Loaded %d/%d schema files from %s", loaded, len(files), root)
    return conn


def attach_ducklake(uri: str) -> duckdb.DuckDBPyConnection:
    """Attach a real DuckLake catalog (Postgres + object storage)."""
    conn = duckdb.connect(":memory:")
    # DuckLake + the Postgres extension power the catalog.
    for ext in ("ducklake", "postgres"):
        try:
            conn.execute(f"INSTALL {ext}; LOAD {ext};")
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to install/load %s extension: %s", ext, exc)

    attach_opts = ""
    data_path = os.environ.get("KG_DUCKLAKE_DATA_PATH")
    if data_path:
        # DuckDB parameter binding doesn't apply to ATTACH options, so
        # escape single quotes the old-fashioned way.
        escaped = data_path.replace("'", "''")
        attach_opts = f" (DATA_PATH '{escaped}')"
    safe_uri = uri.replace("'", "''")
    conn.execute(f"ATTACH '{safe_uri}' AS epihack_kg{attach_opts};")
    conn.execute("USE epihack_kg;")
    log.info("Attached DuckLake catalog %s", uri)
    return conn


def bootstrap() -> duckdb.DuckDBPyConnection:
    """Bootstrap a DuckDB connection from env config.

    * ``KG_DUCKLAKE_URI`` -> attach a real DuckLake catalog.
    * otherwise -> in-memory DuckDB seeded from ``$KG_SCHEMA_PATH``
      (default ``../../schema``).
    """
    ducklake_uri = os.environ.get("KG_DUCKLAKE_URI")
    if ducklake_uri:
        return attach_ducklake(ducklake_uri)
    schema_env = os.environ.get("KG_SCHEMA_PATH")
    schema_root = Path(schema_env).expanduser() if schema_env else None
    return load_in_memory(schema_root)
