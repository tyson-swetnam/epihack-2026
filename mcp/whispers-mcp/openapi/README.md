---
title: WHISPers OpenAPI snapshots
---

# WHISPers OpenAPI snapshots

This directory holds versioned snapshots of the upstream WHISPers
service spec.

## Status: pending fetch from a network-enabled host

The WHISPers Django service (USGS-WiM/whispersservices) registers
`openapi/` and `docs/` (Swagger UI) routes alongside its DRF router
(see `whispersapi/urls.py`). The production deployment at
<https://whispers.usgs.gov/api/openapi/> returns the live spec, but
the sandbox where this MCP server was authored could not reach
`whispers.usgs.gov` to capture a snapshot.

A maintainer with network access should refresh this directory:

```bash
curl -sS https://whispers.usgs.gov/api/openapi/?format=openapi-json \
  | jq . > snapshot-$(date +%Y%m%d).json
```

Until then, the paths used by `src/whispers_mcp/client.py` are derived
from the URL router in `whispersapi/urls.py` (each DRF
`router.register('<basename>', <ViewSet>)` becomes `/api/<basename>/`)
and the EventSummaryFilter in `whispersapi/filters.py`. Every path is
overridable via `WHISPERS_PATH_*` env vars so the deployed server can
follow upstream drift without a code change.

## Why this directory exists

Mirrors the convention in `mcp/vectorsurv-mcp/openapi/`: keeping a spec
snapshot in-tree means contributors whose build environment can't
reach the live USGS host (e.g. CI sandboxes) can still trace each
client path back to an authoritative source.
