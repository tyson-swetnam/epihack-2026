#!/usr/bin/env python3
"""Seed the DuckLake knowledge-graph catalog (idempotent).

Run with the knowledge-graph-mcp venv's Python so the duckdb version and the
`knowledge_graph_mcp` package (for the canonical schema-file order) match the
runtime exactly.

Why not just ``.read`` the schema files into DuckLake?
  DuckLake does **not** support PRIMARY KEY / UNIQUE / FK constraints or
  secondary indexes, and the schema files use them throughout. So we:
    1. replay the full schema into an in-memory DuckDB (constraints OK there);
    2. ATTACH the DuckLake catalog;
    3. CTAS-copy every base table memory -> DuckLake (CTAS carries no
       constraints, so it lands cleanly);
    4. recreate the views.
  The data is identical; only the storage-layer constraints are dropped, which
  is fine for an append-mostly analytical lakehouse.

Env:
  KG_DUCKLAKE_URI        ducklake:postgres:dbname=... host=... user=... password=...
  KG_DUCKLAKE_DATA_PATH  local dir for the Parquet data files
  KG_SCHEMA_PATH         <repo>/schema

Idempotency: if epihack.kg.node already has rows, the copy is skipped.
Prints a summary line beginning with SEEDED / SKIPPED.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb

_SYS_SCHEMAS = ("information_schema", "pg_catalog", "main")


def _ordered_schema_files(schema_root: Path) -> list[Path]:
    try:
        from knowledge_graph_mcp.loader import discover_schema_files

        return discover_schema_files(schema_root)
    except Exception as exc:  # pragma: no cover - fallback
        print(f"WARN: glob order fallback ({exc})", file=sys.stderr)
        top = sorted(schema_root.glob("*.sql"))
        deep = sorted((schema_root / "deep").glob("*.sql"))
        pri = [p for n in ("standards.sql", "pathogens.sql")
               for p in deep if p.name == n]
        return top + pri + [p for p in deep if p not in pri]


def main() -> int:
    uri = os.environ["KG_DUCKLAKE_URI"]
    data_path = os.environ["KG_DUCKLAKE_DATA_PATH"]
    schema_root = Path(os.environ["KG_SCHEMA_PATH"]).expanduser()

    con = duckdb.connect(":memory:")

    # 1. Replay full schema into in-memory DuckDB (constraints supported here).
    files = _ordered_schema_files(schema_root)
    if not files:
        print(f"ERROR: no schema files under {schema_root}", file=sys.stderr)
        return 2
    loaded = 0
    for path in files:
        try:
            con.execute(Path(path).read_text(encoding="utf-8"))
            loaded += 1
        except Exception as exc:
            print(f"WARN: skipped {path}: {exc}", file=sys.stderr)
    print(f"in-memory: loaded {loaded}/{len(files)} schema files", file=sys.stderr)

    # 2. Attach the DuckLake catalog on the same connection.
    for ext in ("ducklake", "postgres"):
        con.execute(f"INSTALL {ext}; LOAD {ext};")
    esc_path = data_path.replace("'", "''")
    esc_uri = uri.replace("'", "''")
    con.execute(f"ATTACH '{esc_uri}' AS epihack (DATA_PATH '{esc_path}');")

    # Idempotency probe.
    try:
        already = con.execute("SELECT count(*) FROM epihack.kg.node").fetchone()[0]
    except Exception:
        already = 0
    if already:
        print(f"SKIPPED: epihack.kg.node already has {already} rows.")
        return 0

    # 3. Recreate schemas + CTAS-copy base tables (memory -> DuckLake).
    schemas = con.execute(
        "SELECT DISTINCT schema_name FROM duckdb_tables() "
        "WHERE database_name = 'memory' AND internal = false"
    ).fetchall()
    for (sch,) in schemas:
        con.execute(f'CREATE SCHEMA IF NOT EXISTS epihack."{sch}";')

    tables = con.execute(
        "SELECT schema_name, table_name FROM duckdb_tables() "
        "WHERE database_name = 'memory' AND internal = false "
        "ORDER BY schema_name, table_name"
    ).fetchall()
    copied = 0
    for sch, tbl in tables:
        con.execute(
            f'CREATE TABLE epihack."{sch}"."{tbl}" AS '
            f'SELECT * FROM "{sch}"."{tbl}";'
        )
        copied += 1

    # 4. Recreate views inside the DuckLake catalog.
    con.execute("USE epihack;")
    views = con.execute(
        "SELECT schema_name, view_name, sql FROM duckdb_views() "
        "WHERE database_name = 'memory' AND internal = false"
    ).fetchall()
    views_made = 0
    for sch, vname, vsql in views:
        try:
            con.execute(vsql)
            views_made += 1
        except Exception as exc:
            print(f"WARN: view {sch}.{vname} not recreated: {exc}", file=sys.stderr)

    nodes = con.execute("SELECT count(*) FROM epihack.kg.node").fetchone()[0]
    try:
        snaps = con.execute(
            "SELECT max(snapshot_id) FROM ducklake_snapshots('epihack')"
        ).fetchone()[0]
    except Exception:
        snaps = "?"
    print(
        f"SEEDED: {copied} tables + {views_made}/{len(views)} views copied to "
        f"DuckLake, kg.node={nodes} rows, latest_snapshot={snaps}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
