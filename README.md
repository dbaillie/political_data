# political_data

Collation, visualisation and storytelling of political, social and other data.

## UK government spending

Research guide and starter data pipeline for **where government money is spent** — UK totals, devolved nations, English regions, and a path to council-level + demographic views.

- [Full guide](docs/uk-government-spending.md)
- Run `python scripts/build_fiscal_summary.py` after placing ONS workbooks in `data/raw/`
- Revenue by tax type and income tax band by region: `data/processed/revenue_by_type_region_fye2025.json`
- Council tax by property band (A–H): included in the same file under `council_tax_by_band_and_region`
- Historical data coverage: `data/processed/data_coverage.json`
- HM Treasury historical CRA/PESA (GOV.UK editions 2010–2025): run `python scripts/download_hm_treasury.py`, then `build_cra_history.py` / `build_pesa_history.py`
- Merged time series: `data/processed/cra_expenditure_history.json`, `data/processed/pesa_expenditure_history.json`

### Visualization (React)

**Live preview (after GitHub Pages is enabled):** https://dbaillie.github.io/political_data/

```bash
# Export normalized CSVs from processed JSON
python scripts/export_viz_data.py

# Start the dashboard locally
cd viz && npm install && npm run dev   # → http://localhost:5173
```

- **Data export:** `data/export/*.csv` (Postgres-ready; see `supabase/schema.sql`)
- **Frontend:** `viz/` — React + Vite + Recharts
- **Deploy:** `.github/workflows/deploy-viz.yml` → GitHub Pages
