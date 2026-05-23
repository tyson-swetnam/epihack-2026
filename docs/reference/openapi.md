# OpenAPI spec

The HTTP contract between `app/` and `agents/` is
[`api/openapi.yaml`](https://github.com/tyson-swetnam/epihack-2026/blob/main/api/openapi.yaml).

- `app/src/lib/api-types.ts` is **generated** (`npm run gen:api`).
- `agents/src/onehealth_agents/api/models.py` is **validated against** the spec.
- Never hand-edit `api-types.ts`.

CI validates the spec on every change:

```bash
redocly lint api/openapi.yaml
redocly preview-docs api/openapi.yaml
```
