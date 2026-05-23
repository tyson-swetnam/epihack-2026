# Local development

!!! info "Source"
    Mirrors the "Commands" section of the repo
    [`CLAUDE.md`](https://github.com/tyson-swetnam/epihack-2026/blob/main/CLAUDE.md).

## Knowledge graph bootstrap

```bash
duckdb
```

```sql
INSTALL ducklake; INSTALL postgres; LOAD ducklake; LOAD postgres;
ATTACH 'ducklake:postgres:dbname=epihack host=localhost user=epihack'
  AS epihack (DATA_PATH 's3://epihack/ducklake/');
USE epihack;
-- then .read each seed in the order shown in kg/seeds.md
```

## Reporting app

```bash
cd app && npm install
npm run gen:api      # regenerate src/lib/api-types.ts from ../api/openapi.yaml
npm run dev          # localhost:3000
```

## Agents / FastAPI

```bash
cd agents && uv sync
ONEHEALTH_AUTH_MOCK=1 uv run uvicorn onehealth_agents.api:app --reload --port 8000
```

## MCP servers

```bash
cd mcp/<server> && uv sync && uv run pytest
```

## Jekyll site

```bash
bundle install && bundle exec jekyll serve
# localhost:4000/epihack-2026/
```

## MkDocs docs site

```bash
pip install -r docs/requirements.txt
mkdocs serve
# localhost:8000
```
