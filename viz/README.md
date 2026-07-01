# UK Government Spending — Viz

React dashboard for UK public finance data.

## How to view

### Option A — GitHub Pages (no local install)

After the [Deploy viz to GitHub Pages](https://github.com/dbaillie/political_data/actions/workflows/deploy-viz.yml) workflow runs:

**https://dbaillie.github.io/political_data/**

First-time setup (repo owner only):

1. GitHub → **Settings** → **Pages**
2. **Build and deployment** → Source: **GitHub Actions**

The workflow deploys on push to `main` (and the viz feature branch while in development).

### Option B — Run locally

From the repo root:

```bash
git clone https://github.com/dbaillie/political_data.git
cd political_data
git checkout cursor/react-viz-setup-362b   # or main once merged

python scripts/export_viz_data.py          # optional — CSVs already in repo
cd viz && npm install && npm run dev
```

Open **http://localhost:5173**

### Option C — Static preview build

```bash
cd viz && npm install && npm run build && npm run preview
```

Open **http://localhost:4173**

## Data

Charts load normalized CSV from `public/data/`, synced from `data/export/` by the export script.

Postgres schema for Supabase: `../supabase/schema.sql`

## Views

| Tab | Content |
|---|---|
| UK overview | Revenue, TME, deficit, spending by COFOG function |
| Regions | Net fiscal balance by ITL1 region |
| History | TME trend (1990+) and major spending areas over time |
| Revenue | Tax type breakdown by region |
