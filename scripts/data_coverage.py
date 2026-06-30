"""Document historical coverage of datasets used in the fiscal pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW = DATA_DIR / "raw"
OUT = DATA_DIR / "processed"


def _fye_years_from_sheet(path: Path, sheet: str) -> list[str]:
    df = pd.read_excel(path, sheet, header=None)
    for row in range(min(8, df.shape[0])):
        years = [
            str(df.iloc[row, col]).strip()
            for col in range(2, df.shape[1])
            if " to 20" in str(df.iloc[row, col])
        ]
        if len(years) >= 5:
            return years
    return []


def build_coverage() -> dict:
    coverage = {
        "description": (
            "Historical span of datasets currently in data/raw and used by the pipeline. "
            "FYE = financial year ending 31 March. Tax year runs 6 April to 5 April."
        ),
        "datasets": [],
    }

    def add(
        name: str,
        period_start: str,
        period_end: str,
        geography: str,
        granularity: str,
        source: str,
        file: str,
        notes: str = "",
    ) -> None:
        coverage["datasets"].append(
            {
                "name": name,
                "period_start": period_start,
                "period_end": period_end,
                "geography": geography,
                "granularity": granularity,
                "source": source,
                "file": file,
                "notes": notes,
            }
        )

    exp_years = _fye_years_from_sheet(RAW / "crpsf_fye2025_exp.xlsx", "United Kingdom")
    rev_years = _fye_years_from_sheet(RAW / "crpsf_fye2025_rev.xlsx", "United Kingdom")

    add(
        "ONS Country & Regional PSF — expenditure",
        exp_years[0].replace(" to ", "-") if exp_years else "2000-01",
        exp_years[-1].replace(" to ", "-") if exp_years else "2024-25",
        "UK, 4 nations, 9 English regions (ITL1)",
        "COFOG function; identifiable expenditure",
        "ONS",
        "crpsf_fye2025_exp.xlsx",
        f"{len(exp_years)} financial years in current workbook.",
    )
    add(
        "ONS Country & Regional PSF — revenue",
        rev_years[0].replace(" to ", "-") if rev_years else "2000-01",
        rev_years[-1].replace(" to ", "-") if rev_years else "2024-25",
        "UK, 4 nations, 9 English regions (ITL1)",
        "~58 revenue lines incl. tax type",
        "ONS Table S9 in supplementary tables",
        "crpsf_fye2025_supp.xlsx",
        f"{len(rev_years)} financial years.",
    )
    add(
        "HM Treasury CRA database",
        "2020-21",
        "2024-25",
        "UK, ITL1",
        "Department segment × function × region",
        "HM Treasury",
        "cra2025_db.xlsx",
        "Older CRA editions available back to 1999 on GOV.UK.",
    )
    add(
        "HM Treasury PESA Chapter 1",
        "2020-21",
        "2025-26",
        "UK",
        "TME budgetary aggregates",
        "HM Treasury",
        "pesa_ch1.xlsx",
        "PESA functional tables (Ch 4–5) go back to 1999-00.",
    )
    add(
        "HMRC Income Tax Liabilities Statistics",
        "1999-2000",
        "2024-2025",
        "UK; ITL1 for payer counts (Table 2.2)",
        "Income tax marginal bands",
        "HMRC SPI / ITLS",
        "hmrc_itls.ods",
        "2022-23 to 2024-25 are projections from 2021-22 SPI.",
    )
    add(
        "VOA Council Tax stock of properties (CTSOP)",
        "1993",
        "2024",
        "England & Wales",
        "Property count by band A–H (I in Wales); region/LA",
        "Valuation Office Agency",
        "ctsop1.0_supp_2024.xlsx",
        "Time series in ctsop1.0_timeseries.xlsx (1993–2024 per year sheet).",
    )
    add(
        "NRS Scotland dwelling estimates",
        "2005",
        "2024",
        "Scotland",
        "Council tax band A–H by data zone",
        "National Records of Scotland",
        "scotland_dwelling_est_2024.xlsx",
        "Aggregated to Scotland total in pipeline.",
    )
    add(
        "MHCLG Council Taxbase (England LA)",
        "1993",
        "2024",
        "England billing authorities",
        "Band D equivalent taxbase, discounts",
        "MHCLG",
        "council_taxbase_la_2024.ods",
        "Annual collection; multi-year on GOV.UK.",
    )

    coverage["summary"] = {
        "longest_revenue_expenditure_series": "ONS CR PSF: FYE 2000-01 to 2024-25",
        "longest_property_band_series": "VOA CTSOP: 1993 to 2024 (England & Wales)",
        "longest_income_tax_band_series": "HMRC ITLS: tax years 1999-2000 to 2024-2025",
        "cra_segment_data": "2020-21 to 2024-25 in current file",
        "not_in_pipeline_yet": [
            "Local authority revenue outturn (England): 2017-18 to 2024-25 on GOV.UK",
            "Wales council tax dwellings by band: StatsWales from 2014-15",
            "Northern Ireland domestic rates (no council tax bands)",
        ],
    }

    return coverage


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "data_coverage.json"
    path.write_text(json.dumps(build_coverage(), indent=2))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
