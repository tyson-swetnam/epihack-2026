# GitHub Pages

Three GitHub Actions workflows publish to a single `gh-pages` branch,
all with `keep_files: true`:

| Workflow | Triggers on | Lands at |
|---|---|---|
| `deploy-jekyll.yml` | root, excluding `app/`, `api/`, `docs/` | `gh-pages:/` |
| `deploy-app.yml` | `app/**`, `api/openapi.yaml` | `gh-pages:/app/` |
| `deploy-docs.yml` | `docs/**`, `mkdocs.yml` | `gh-pages:/docs/` |

The Jekyll `_config.yml` excludes `app/`, `api/`, `agents/`, `docs/`,
`mkdocs.yml`, and `site/` so the four generators (Jekyll, Next.js,
MkDocs, plus the unbundled viewers) don't fight over the same files.

Don't add Jekyll frontmatter to anything under `app/`, `api/`, or
`docs/` — Jekyll won't see those, and MkDocs/Next.js will see the
frontmatter as raw text.
