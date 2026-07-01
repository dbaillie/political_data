#!/usr/bin/env python3
"""Merge historical HM Treasury CRA databases into a longitudinal series."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CRA_DIR = DATA_DIR / "raw" / "hm_treasury" / "cra"
OUT = DATA_DIR / "processed" / "cra_expenditure_history.json"

REGION_COLUMNS = ("ITL Region", "NUTS Region", "NUTS 1 region")
COFOG_COLUMNS = ("COFOG Level 0", "COFOG Level 1")
UK_REGIONS = {
    "NORTH EAST",
    "NORTH WEST",
    "YORKSHIRE AND THE HUMBER",
    "EAST MIDLANDS",
    "WEST MIDLANDS",
    "EAST OF ENGLAND",
    "LONDON",
    "SOUTH EAST",
    "SOUTH WEST",
    "ENGLAND",
    "WALES",
    "SCOTLAND",
    "NORTHERN IRELAND",
    "UK",
    "UNITED KINGDOM",
    "OUTSIDE UK",
}


def database_sheet(path: Path) -> str:
    xl = pd.ExcelFile(path)
    for name in xl.sheet_names:
        lower = name.lower()
        if "database" in lower or "combined db" in lower:
            return name
    return xl.sheet_names[-1]


def year_columns(columns) -> list[str]:
    out: list[str] = []
    for col in columns:
        if not isinstance(col, str):
            continue
        if len(col) == 7 and col[4] == "-" and col[:4].isdigit() and col[5:7].isdigit():
            out.append(col)
    return out


def pick_column(columns, options: tuple[str, ...]) -> str | None:
    for opt in options:
        if opt in columns:
            return opt
    return None


def normalise_region(value: str) -> str:
    text = str(value).strip()
    upper = text.upper()
    mapping = {
        "YORKSHIRE AND THE HUMBER": "Yorkshire and The Humber",
        "NORTH EAST": "North East",
        "NORTH WEST": "North West",
        "EAST MIDLANDS": "East Midlands",
        "WEST MIDLANDS": "West Midlands",
        "EAST OF ENGLAND": "East of England",
        "SOUTH EAST": "South East",
        "SOUTH WEST": "South West",
        "NORTHERN IRELAND": "Northern Ireland",
        "UNITED KINGDOM": "UK",
    }
    return mapping.get(upper, text)


def load_edition(path: Path, edition_year: int) -> pd.DataFrame:
    sheet = database_sheet(path)
    df = pd.read_excel(path, sheet_name=sheet)
    region_col = pick_column(df.columns, REGION_COLUMNS)
    cofog_col = pick_column(df.columns, COFOG_COLUMNS)
    if not region_col or not cofog_col:
        raise ValueError(f"Missing region/cofog columns in {path.name}")

    years = year_columns(df.columns)
    if not years:
        raise ValueError(f"No year columns in {path.name}")

    id_col = None
    for candidate in ("ID/non-ID", "ID or non-ID"):
        if candidate in df.columns:
            id_col = candidate
            break

    subset = df.copy()
    if id_col:
        subset = subset[subset[id_col].astype(str).str.upper().str.startswith("ID")]

    subset = subset[subset[region_col].astype(str).str.upper().isin(UK_REGIONS)]

    records: list[dict] = []
    for _, row in subset.iterrows():
        region = normalise_region(row[region_col])
        function = str(row[cofog_col]).strip()
        for year in years:
            value = row[year]
            if pd.isna(value):
                continue
            records.append(
                {
                    "financial_year": year,
                    "region": region,
                    "function": function,
                    "spend_gbp_thousands": float(value),
                    "source_edition": edition_year,
                }
            )
    return pd.DataFrame.from_records(records)


def merge_editions(frames: list[pd.DataFrame]) -> pd.DataFrame:
    combined = pd.concat(frames, ignore_index=True)
    # Prefer newer CRA edition when the same FY appears in multiple releases.
    combined = combined.sort_values("source_edition")
    combined = combined.drop_duplicates(
        subset=["financial_year", "region", "function"], keep="last"
    )
    return combined


def summarise(df: pd.DataFrame) -> dict:
    uk = (
        df[df["region"].isin(["UK", "United Kingdom"])]
        .groupby(["financial_year", "function"], as_index=False)["spend_gbp_thousands"]
        .sum()
    )
    uk_totals = uk.groupby("financial_year")["spend_gbp_thousands"].sum()
    uk_by_function: dict[str, dict[str, float]] = {}
    for _, row in uk.iterrows():
        fy = row["financial_year"]
        fn = row["function"]
        total = uk_totals[fy]
        uk_by_function.setdefault(fy, {})[fn] = {
            "gbp_bn": round(row["spend_gbp_thousands"] / 1e6, 2),
            "pct": round(row["spend_gbp_thousands"] / total * 100, 1),
        }

    regional = (
        df[~df["region"].isin(["UK", "United Kingdom", "Outside UK"])]
        .groupby(["financial_year", "region"], as_index=False)["spend_gbp_thousands"]
        .sum()
    )
    regional_out: dict[str, dict[str, float]] = {}
    for _, row in regional.iterrows():
        regional_out.setdefault(row["financial_year"], {})[row["region"]] = round(
            row["spend_gbp_thousands"] / 1e6, 2
        )

    years = sorted(df["financial_year"].unique())
    editions = [int(x) for x in sorted(df["source_edition"].unique())]

    return {
        "financial_years": years,
        "first_year": years[0] if years else None,
        "last_year": years[-1] if years else None,
        "source_editions": editions,
        "uk_by_function": uk_by_function,
        "identifiable_expenditure_by_region_gbp_bn": regional_out,
    }


def main() -> None:
    paths = sorted(CRA_DIR.glob("cra_*_database.xlsx"))
    if not paths:
        raise SystemExit(f"No CRA files in {CRA_DIR}. Run download_hm_treasury.py first.")

    frames: list[pd.DataFrame] = []
    loaded: list[dict] = []
    for path in paths:
        edition = int(path.stem.split("_")[1])
        try:
            frames.append(load_edition(path, edition))
            loaded.append({"edition": edition, "file": path.name, "status": "ok"})
        except Exception as exc:  # noqa: BLE001
            loaded.append({"edition": edition, "file": path.name, "status": "error", "error": str(exc)})

    merged = merge_editions(frames)
    summary = summarise(merged)
    summary["load_log"] = loaded
    summary["method"] = (
        "Merged HM Treasury CRA database editions from GOV.UK. "
        "Overlapping years use the latest available edition. "
        "Values are identifiable expenditure in £ thousands."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {OUT}")
    print(f"Coverage: {summary.get('first_year')} → {summary.get('last_year')}")


if __name__ == "__main__":
    main()
