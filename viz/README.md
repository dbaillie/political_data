# UK Government Spending — Viz

React dashboard for UK public finance data.

## Quick start

From the repo root:

```bash
python scripts/export_viz_data.py   # refresh CSVs
cd viz && npm install && npm run dev
```

Open http://localhost:5173

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
