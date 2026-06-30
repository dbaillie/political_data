# political_data

Collation, visualisation and storytelling of political, social and other data.

## UK government spending

Research guide and starter data pipeline for **where government money is spent** — UK totals, devolved nations, English regions, and a path to council-level + demographic views.

- [Full guide](docs/uk-government-spending.md)
- Run `python scripts/build_fiscal_summary.py` after placing ONS workbooks in `data/raw/`
- Revenue by tax type and income tax band by region: `data/processed/revenue_by_type_region_fye2025.json`
- Council tax by property band (A–H): included in the same file under `council_tax_by_band_and_region`
- Historical data coverage: `data/processed/data_coverage.json`
