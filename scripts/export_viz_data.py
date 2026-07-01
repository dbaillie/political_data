#!/usr/bin/env python3
"""Export normalized CSV datasets for the viz frontend and future Supabase load."""

from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PROCESSED = DATA_DIR / "processed"
EXPORT_DIR = DATA_DIR / "export"
VIZ_DATA = Path(__file__).resolve().parents[1] / "viz" / "public" / "data"

REGIONS = [
    {"slug": "north-east", "name": "North East", "nation": "England", "sort_order": 1},
    {"slug": "north-west", "name": "North West", "nation": "England", "sort_order": 2},
    {"slug": "yorkshire-and-the-humber", "name": "Yorkshire and The Humber", "nation": "England", "sort_order": 3},
    {"slug": "east-midlands", "name": "East Midlands", "nation": "England", "sort_order": 4},
    {"slug": "west-midlands", "name": "West Midlands", "nation": "England", "sort_order": 5},
    {"slug": "east-of-england", "name": "East of England", "nation": "England", "sort_order": 6},
    {"slug": "london", "name": "London", "nation": "England", "sort_order": 7},
    {"slug": "south-east", "name": "South East", "nation": "England", "sort_order": 8},
    {"slug": "south-west", "name": "South West", "nation": "England", "sort_order": 9},
    {"slug": "england", "name": "England", "nation": "England", "sort_order": 10},
    {"slug": "wales", "name": "Wales", "nation": "Wales", "sort_order": 11},
    {"slug": "scotland", "name": "Scotland", "nation": "Scotland", "sort_order": 12},
    {"slug": "northern-ireland", "name": "Northern Ireland", "nation": "Northern Ireland", "sort_order": 13},
    {"slug": "uk", "name": "UK", "nation": "UK", "sort_order": 14},
]

REGION_BY_NAME = {r["name"]: r["slug"] for r in REGIONS}
REGION_BY_NAME["United Kingdom"] = "uk"


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"^\d+\.\s*", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fye_parts(label: str) -> tuple[int, int]:
    start, end = label.split("-")
    return int(start), int(end)


def export_dimensions() -> dict:
    write_csv(
        EXPORT_DIR / "regions.csv",
        ["slug", "name", "nation", "sort_order"],
        REGIONS,
    )

    years: dict[str, dict] = {}
    pesa_path = PROCESSED / "pesa_expenditure_history.json"
    if pesa_path.exists():
        pesa = json.loads(pesa_path.read_text())
        for label in pesa.get("tme", {}).get("financial_years", []):
            start, end = fye_parts(label)
            years[label] = {
                "label": label,
                "start_year": start,
                "end_year": 2000 + int(end) if int(end) < 100 else int(end),
            }

    fiscal = json.loads((PROCESSED / "fiscal_summary_fye2025.json").read_text())
    fye_label = fiscal["fye"].replace(" to ", "-")
    if fye_label not in years:
        start, end = fye_parts(fye_label)
        years[fye_label] = {
            "label": fye_label,
            "start_year": start,
            "end_year": 2000 + int(end),
        }

    year_rows = [
        {"label": y["label"], "start_year": y["start_year"], "end_year": y["end_year"]}
        for y in sorted(years.values(), key=lambda x: x["start_year"])
    ]
    write_csv(
        EXPORT_DIR / "financial_years.csv",
        ["label", "start_year", "end_year"],
        year_rows,
    )

    functions: dict[str, dict] = {}
    for fn in fiscal["uk"]["spending_by_function_bn"]:
        slug = slugify(fn)
        functions[slug] = {"slug": slug, "name": fn, "sort_order": int(fn.split(".")[0])}

    pesa = json.loads(pesa_path.read_text()) if pesa_path.exists() else {}
    for fy_data in pesa.get("spending_by_function", {}).get("uk_by_function", {}).values():
        for fn in fy_data:
            slug = slugify(fn)
            if slug not in functions:
                match = re.match(r"^(\d+)\.", fn)
                functions[slug] = {
                    "slug": slug,
                    "name": fn,
                    "sort_order": int(match.group(1)) if match else 99,
                }

    fn_rows = sorted(functions.values(), key=lambda x: x["sort_order"])
    write_csv(
        EXPORT_DIR / "cofog_functions.csv",
        ["slug", "name", "sort_order"],
        fn_rows,
    )

    revenue_types: list[dict] = []
    revenue = json.loads((PROCESSED / "revenue_by_type_region_fye2025.json").read_text())
    seen: set[str] = set()
    for region_data in revenue["revenue_by_type_and_region"].values():
        for slug in region_data["by_type_bn"]:
            if slug in seen:
                continue
            seen.add(slug)
            revenue_types.append(
                {
                    "slug": slug,
                    "name": slug.replace("_", " ").title(),
                    "sort_order": len(revenue_types) + 1,
                }
            )

    write_csv(
        EXPORT_DIR / "revenue_types.csv",
        ["slug", "name", "sort_order"],
        revenue_types,
    )

    return {"years": len(year_rows), "functions": len(fn_rows), "revenue_types": len(revenue_types)}


def export_fiscal_snapshot() -> None:
    fiscal = json.loads((PROCESSED / "fiscal_summary_fye2025.json").read_text())
    fye = fiscal["fye"].replace(" to ", "-")

    uk_rows = [
        {"fye": fye, "metric": "revenue", "value_bn": fiscal["uk"]["revenue_bn"]},
        {"fye": fye, "metric": "expenditure_tme", "value_bn": fiscal["uk"]["expenditure_tme_bn"]},
        {
            "fye": fye,
            "metric": "expenditure_identifiable",
            "value_bn": fiscal["uk"]["expenditure_identifiable_bn"],
        },
        {"fye": fye, "metric": "fiscal_deficit", "value_bn": fiscal["uk"]["fiscal_deficit_bn"]},
        {"fye": fye, "metric": "debt_interest", "value_bn": fiscal["uk"]["debt_interest_bn"]},
    ]
    write_csv(
        EXPORT_DIR / "uk_fiscal_summary.csv",
        ["fye", "metric", "value_bn"],
        uk_rows,
    )

    fn_rows = []
    for fn, amount in fiscal["uk"]["spending_by_function_bn"].items():
        fn_rows.append(
            {
                "fye": fye,
                "function_slug": slugify(fn),
                "function_name": fn,
                "spend_bn": amount,
                "pct_of_tme": fiscal["uk"]["spending_by_function_pct_of_tme"][fn],
            }
        )
    write_csv(
        EXPORT_DIR / "uk_spending_by_function.csv",
        ["fye", "function_slug", "function_name", "spend_bn", "pct_of_tme"],
        fn_rows,
    )

    regional_rows = []
    for row in fiscal["regions"]:
        slug = REGION_BY_NAME.get(row["region"])
        if not slug:
            continue
        regional_rows.append(
            {
                "fye": fye,
                "region_slug": slug,
                "region_name": row["region"],
                "revenue_bn": row["revenue_bn"],
                "expenditure_identifiable_bn": row["identifiable_expenditure_bn"],
                "net_balance_bn": row["net_fiscal_balance_identifiable_bn"],
                "revenue_per_head_gbp": row["revenue_per_head_gbp"],
                "expenditure_per_head_gbp": row["expenditure_per_head_gbp"],
                "net_balance_per_head_gbp": row["net_balance_per_head_gbp"],
            }
        )
    write_csv(
        EXPORT_DIR / "regional_fiscal.csv",
        ["fye", "region_slug", "region_name", "revenue_bn", "expenditure_identifiable_bn",
         "net_balance_bn", "revenue_per_head_gbp", "expenditure_per_head_gbp",
         "net_balance_per_head_gbp"],
        regional_rows,
    )


def export_revenue() -> None:
    revenue = json.loads((PROCESSED / "revenue_by_type_region_fye2025.json").read_text())
    fye = revenue["fye"].replace(" to ", "-")
    rows = []
    for region_name, data in revenue["revenue_by_type_and_region"].items():
        slug = REGION_BY_NAME.get(region_name, slugify(region_name))
        for rev_type, amount in data["by_type_bn"].items():
            rows.append(
                {
                    "fye": fye,
                    "region_slug": slug,
                    "region_name": region_name,
                    "revenue_type_slug": rev_type,
                    "amount_bn": amount,
                    "pct_of_regional_total": data["by_type_pct"][rev_type],
                }
            )
    write_csv(
        EXPORT_DIR / "regional_revenue_by_type.csv",
        ["fye", "region_slug", "region_name", "revenue_type_slug", "amount_bn", "pct_of_regional_total"],
        rows,
    )


def export_pesa_history() -> None:
    path = PROCESSED / "pesa_expenditure_history.json"
    if not path.exists():
        return

    pesa = json.loads(path.read_text())
    tme_rows = [
        {"financial_year": fy, "tme_bn": value}
        for fy, value in pesa["tme"]["total_managed_expenditure_gbp_bn"].items()
    ]
    write_csv(
        EXPORT_DIR / "pesa_tme_history.csv",
        ["financial_year", "tme_bn"],
        tme_rows,
    )

    fn_rows = []
    for fy, functions in pesa["spending_by_function"]["uk_by_function"].items():
        for fn, metrics in functions.items():
            fn_rows.append(
                {
                    "financial_year": fy,
                    "function_slug": slugify(fn),
                    "function_name": fn,
                    "spend_bn": metrics["gbp_bn"],
                    "pct_of_total": metrics["pct"],
                }
            )
    write_csv(
        EXPORT_DIR / "pesa_spending_by_function_history.csv",
        ["financial_year", "function_slug", "function_name", "spend_bn", "pct_of_total"],
        fn_rows,
    )


def export_manifest(counts: dict) -> None:
    manifest = {
        "generated_by": "scripts/export_viz_data.py",
        "format": "csv",
        "target_database": "postgresql (supabase)",
        "tables": {
            "regions.csv": "dimension — ITL1 regions and nations",
            "financial_years.csv": "dimension — FY labels",
            "cofog_functions.csv": "dimension — COFOG Level 0 functions",
            "revenue_types.csv": "dimension — tax and non-tax revenue types",
            "uk_fiscal_summary.csv": "fact — UK headline fiscal metrics by FYE",
            "uk_spending_by_function.csv": "fact — UK spend by function (snapshot)",
            "regional_fiscal.csv": "fact — regional revenue, spend, balance",
            "regional_revenue_by_type.csv": "fact — regional revenue decomposition",
            "pesa_tme_history.csv": "fact — UK TME time series (1967-68+)",
            "pesa_spending_by_function_history.csv": "fact — UK function spend time series",
        },
        "row_counts": counts,
    }
    (EXPORT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))


def sync_to_viz() -> None:
    if VIZ_DATA.exists():
        shutil.rmtree(VIZ_DATA)
    shutil.copytree(EXPORT_DIR, VIZ_DATA)


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    counts = export_dimensions()
    export_fiscal_snapshot()
    export_revenue()
    export_pesa_history()

    counts["uk_fiscal_summary"] = sum(1 for _ in open(EXPORT_DIR / "uk_fiscal_summary.csv")) - 1
    counts["regional_fiscal"] = sum(1 for _ in open(EXPORT_DIR / "regional_fiscal.csv")) - 1
    counts["pesa_tme_history"] = sum(1 for _ in open(EXPORT_DIR / "pesa_tme_history.csv")) - 1
    counts["pesa_function_history"] = (
        sum(1 for _ in open(EXPORT_DIR / "pesa_spending_by_function_history.csv")) - 1
    )
    export_manifest(counts)
    sync_to_viz()
    print(f"Exported CSVs to {EXPORT_DIR}")
    print(f"Synced to {VIZ_DATA}")


if __name__ == "__main__":
    main()
