# GitHub Pages deployment

The site combines two build outputs at one origin:

```
https://tyson-swetnam.github.io/epihack-2026/        ← Jekyll site (root)
https://tyson-swetnam.github.io/epihack-2026/app/    ← Next.js static export
```

Both deploy to the **`gh-pages` branch**, which Pages serves directly.

## One-time setup (repo settings)

Under **Settings → Pages**:

- **Build and deployment → Source**: `Deploy from a branch`
- **Branch**: `gh-pages` / `/ (root)`
- Save.

After this is configured, the workflows below take over.

## Workflows that publish to `gh-pages`

| Workflow | What it builds | Where it lands on `gh-pages` |
|---|---|---|
| `.github/workflows/deploy-jekyll.yml` (next commit) | The Jekyll site at the repo root | `/` (the root of `gh-pages`) |
| `.github/workflows/deploy-app.yml` | The Next.js reporting app at `app/` | `/app/` (under `gh-pages`) |

Both workflows use `peaceiris/actions-gh-pages@v4` with
`keep_files: true` so they don't clobber each other. The app
workflow sets `destination_dir: app`; the Jekyll workflow publishes
at the root.

## Local preview

```bash
# Jekyll site (root):
bundle install
bundle exec jekyll serve

# Next.js app:
cd app
npm install
npm run dev
```

Both can run side-by-side on different ports.

## Switching from "Deploy from a branch (main)" to gh-pages

If the Pages source was previously `main`:

1. Push the first `gh-pages`-targeting workflow run (or run
   `npm run build && ./scripts/seed-gh-pages.sh` from a maintainer
   machine).
2. Verify `gh-pages` branch exists and contains the built site.
3. Settings → Pages → Source → switch to `gh-pages`.
4. Wait for the next workflow run to complete; the URL stays the same.

There's a ~5 minute propagation delay; URLs may 404 briefly during
the cut-over.
