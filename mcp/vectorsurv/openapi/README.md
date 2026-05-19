---
title: VectorSurv OpenAPI snapshots
---

# VectorSurv OpenAPI snapshots

This directory holds versioned snapshots of the live VectorSurv OpenAPI
spec, fetched from <https://api.vectorsurv.org/openapi>. Each file is
named after the `info.version` reported by the API at the time of the
snapshot, so a `git diff` of two consecutive files shows API drift.

## Refresh

```bash
curl -sS https://api.vectorsurv.org/openapi \
  | jq . > openapi-$(jq -r .info.version openapi-*.json | sort -V | tail -1 | xargs -I {} curl -sS https://api.vectorsurv.org/openapi | jq -r .info.version).json
```

(or simpler — fetch, look at the version, name the file accordingly).

## Why this is in the repo

The `vectorsurv-mcp` client paths are derived from this spec. If the
spec changes (new fields, renamed endpoints, drift in the query-param
syntax), the next snapshot's diff is the source of truth for what to
update in `src/vectorsurv_mcp/client.py`. Keeping the snapshot in-tree
also unblocks contributors whose build environments can't reach
`api.vectorsurv.org` directly.
