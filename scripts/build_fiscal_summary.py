#!/usr/bin/env python3
"""Build UK fiscal summary from ONS Country & Regional PSF workbooks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from revenue_breakdown import build_revenue_breakdown

try:
    from data_coverage import build_coverage
except ImportError:
    build_coverage = None

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW = DATA_DIR / "raw"
OUT = DATA_DIR / "processed"
FYE_LABEL = "2024 to 2025"

REGIONS = [
    "North East",
    "North West",
    "Yorkshire and The Humber",
    "East Midlands",
    "West Midlands",
    "East of England",
    "London",
    "South East",
    "South West",
    "England",
    "Wales",
    "Scotland",
    "Northern Ireland",
    "UK",
]


def find_year_column(df: pd.DataFrame) -> int:
    for col in range(df.shape[1]):
        for row in range(min(6, df.shape[0])):
            if str(df.iloc[row, col]).strip() == FYE_LABEL:
                return col
    raise ValueError(f"Could not find column {FYE_LABEL!r}")


def total_receipts(region: str) -> float:
    sheet = "United Kingdom" if region == "UK" else region
    df = pd.read_excel(RAW / "crpsf_fye2025_rev.xlsx", sheet, header=None)
    col = find_year_column(df)
    for row in range(df.shape[0]):
        label = str(df.iloc[row, 0])
        if "Total Current Receipts (excl" in label:
            return float(df.iloc[row, col]) / 1_000
    raise ValueError(f"No total receipts row for {region}")


def identifiable_expenditure() -> dict[str, float]:
    df = pd.read_excel(RAW / "crpsf_fye2025_exp.xlsx", "Combined Expenditure", header=None)
    col = find_year_column(df)
    out: dict[str, float] = {}
    for row in range(3, 17):
        region = str(df.iloc[row, 0]).strip()
        if region in REGIONS:
            out[region] = float(df.iloc[row, col]) / 1_000
    return out


def total_managed_expenditure() -> float:
    df = pd.read_excel(RAW / "crpsf_fye2025_exp.xlsx", "United Kingdom", header=None)
    col = find_year_column(df)
    for row in range(df.shape[0]):
        label = str(df.iloc[row, 0]).strip()
        if label == "Total managed expenditure":
            return float(df.iloc[row, col]) / 1_000
    raise ValueError("Could not find UK TME row")


def spending_by_function() -> dict[str, float]:
    df = pd.read_excel(RAW / "crpsf_fye2025_exp.xlsx", "United Kingdom", header=None)
    col = find_year_column(df)
    out: dict[str, float] = {}
    for row in range(3, 24):
        label = str(df.iloc[row, 0]).strip()
        value = df.iloc[row, col]
        if not label or pd.isna(value):
            continue
        out[label] = float(value) / 1_000
    return out


def per_head_metrics() -> dict[str, dict[str, float]]:
    metrics = {
        "Table S5": "revenue_per_head_gbp",
        "Table S6": "expenditure_per_head_gbp",
        "Table S4": "net_balance_per_head_gbp",
    }
    result: dict[str, dict[str, float]] = {}
    for sheet, key in metrics.items():
        df = pd.read_excel(RAW / "crpsf_fye2025_supp.xlsx", sheet, header=None)
        col = find_year_column(df)
        for row in range(df.shape[0]):
            region = str(df.iloc[row, 0]).strip()
            if region in (*REGIONS, "United Kingdom"):
                value = df.iloc[row, col]
                if pd.notna(value):
                    name = "UK" if region == "United Kingdom" else region
                    result.setdefault(name, {})[key] = float(value)
    return result


def build_summary() -> dict:
    ident = identifiable_expenditure()
    tme = total_managed_expenditure()
    revenue = {region: total_receipts(region) for region in REGIONS}
    functions = spending_by_function()
    per_head = per_head_metrics()

    top_functions = {
        label: value
        for label, value in functions.items()
        if label[0].isdigit() and "of which" not in label and "Total" not in label
    }
    debt_interest = functions.get("1. of which: public sector debt interest", 0.0)

    return {
        "fye": "2024-25",
        "sources": {
            "expenditure": "ONS Country and regional public sector finances expenditure tables (FYE 2025)",
            "revenue": "ONS Country and regional public sector finances revenue tables (FYE 2025)",
            "per_head": "ONS Country and regional public sector finances supplementary tables (FYE 2025)",
            "revenue_by_type": "ONS supplementary Table S9 + HMRC ITLS for income tax bands",
        },
        "uk": {
            "revenue_bn": round(revenue["UK"], 1),
            "expenditure_tme_bn": round(tme, 1),
            "expenditure_identifiable_bn": round(ident["UK"], 1),
            "non_identifiable_and_accounting_bn": round(tme - ident["UK"], 1),
            "fiscal_deficit_bn": round(tme - revenue["UK"], 1),
            "debt_interest_bn": round(debt_interest, 1),
            "spending_by_function_bn": {k: round(v, 1) for k, v in top_functions.items()},
            "spending_by_function_pct_of_tme": {
                k: round(v / tme * 100, 1) for k, v in top_functions.items()
            },
        },
        "regions": [
            {
                "region": "United Kingdom" if region == "UK" else region,
                "revenue_bn": round(revenue[region], 1),
                "identifiable_expenditure_bn": round(ident[region], 1),
                "net_fiscal_balance_identifiable_bn": round(
                    ident[region] - revenue[region], 1
                ),
                **per_head.get(region, {}),
            }
            for region in REGIONS
            if region != "UK"
        ],
        "revenue_breakdown": build_revenue_breakdown(),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summary = build_summary()
    out_path = OUT / "fiscal_summary_fye2025.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {out_path}")

    revenue_path = OUT / "revenue_by_type_region_fye2025.json"
    revenue_path.write_text(json.dumps(summary["revenue_breakdown"], indent=2))
    print(f"Wrote {revenue_path}")

    if build_coverage:
        coverage_path = OUT / "data_coverage.json"
        coverage_path.write_text(json.dumps(build_coverage(), indent=2))
        print(f"Wrote {coverage_path}")


if __name__ == "__main__":
    main()
