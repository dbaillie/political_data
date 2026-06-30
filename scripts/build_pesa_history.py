#!/usr/bin/env python3
"""Merge historical HM Treasury PESA chapter 4 tables into longitudinal series."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PESA_DIR = DATA_DIR / "raw" / "hm_treasury" / "pesa"
OUT = DATA_DIR / "processed" / "pesa_expenditure_history.json"

FY_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def read_workbook(path: Path) -> pd.ExcelFile:
    if path.suffix.lower() == ".ods":
        return pd.ExcelFile(path, engine="odf")
    return pd.ExcelFile(path)


def find_sheet(xl: pd.ExcelFile, table: str) -> str | None:
    """Locate sheet for PESA table 4.1 or 4.2."""
    target = table.replace(".", "").lower()  # e.g. 41, 42
    for name in xl.sheet_names:
        compact = re.sub(r"[^0-9a-z]", "", name.lower())
        if compact.startswith(target) or compact == f"table{target}":
            return name
        if table == "4.1" and re.match(r"4[_ ]?1", name, flags=re.I):
            return name
        if table == "4.2" and re.match(r"4[_ ]?2", name, flags=re.I):
            return name
    return None


def is_financial_year(value) -> bool:
    return isinstance(value, str) and bool(FY_PATTERN.match(value.strip()))


def parse_table_41(path: Path) -> dict[str, float]:
    """Extract UK TME (nominal £bn) from PESA table 4.1."""
    xl = read_workbook(path)
    sheet = find_sheet(xl, "4.1")
    if not sheet:
        raise ValueError(f"No table 4.1 sheet in {path.name}")

    df = pd.read_excel(path, sheet_name=sheet, header=None)
    tme_col = None
    for row in range(min(6, df.shape[0])):
        for col in range(df.shape[1]):
            label = str(df.iloc[row, col])
            if "Total Managed Expenditure" in label:
                tme_col = col
                break
        if tme_col is not None:
            break
    if tme_col is None:
        raise ValueError(f"Could not find TME column in {path.name}")

    year_col = 1 if df.shape[1] > 1 else 0
    out: dict[str, float] = {}
    for row in range(df.shape[0]):
        year = df.iloc[row, year_col]
        if not is_financial_year(year):
            continue
        value = df.iloc[row, tme_col]
        if pd.notna(value) and isinstance(value, (int, float)):
            out[str(year).strip()] = float(value)
    return out


def parse_table_42(path: Path) -> dict[str, dict[str, float]]:
    """Extract COFOG function spending (nominal £bn) from PESA table 4.2."""
    xl = read_workbook(path)
    sheet = find_sheet(xl, "4.2")
    if not sheet:
        raise ValueError(f"No table 4.2 sheet in {path.name}")

    df = pd.read_excel(path, sheet_name=sheet, header=None)

    year_row = None
    year_cols: dict[int, str] = {}
    for row in range(min(10, df.shape[0])):
        cols: dict[int, str] = {}
        for col in range(1, df.shape[1]):
            val = df.iloc[row, col]
            if is_financial_year(val):
                cols[col] = str(val).strip()
        if len(cols) >= 3:
            year_row = row
            year_cols = cols
            break
    if not year_cols:
        raise ValueError(f"Could not find year header in {path.name}")

    label_col: int | None = None
    search_from = (year_row or 0) + 1
    for col in range(min(4, df.shape[1])):
        for row in range(search_from, min(df.shape[0], search_from + 25)):
            label = str(df.iloc[row, col]).strip()
            if re.match(r"^\d+\.", label):
                label_col = col
                break
        if label_col is not None:
            break
    if label_col is None:
        label_col = 0

    functions: dict[str, dict[str, float]] = {}
    for row in range(search_from, df.shape[0]):
        label = str(df.iloc[row, label_col]).strip()
        if not label or label.lower() == "nan":
            continue
        if label.lower() == "outturn":
            continue
        if label.startswith("(") or label.startswith("Total Managed"):
            continue
        if label.startswith("of which:"):
            continue
        if not re.match(r"^\d+\.", label):
            continue

        for col, fy in year_cols.items():
            value = df.iloc[row, col]
            if pd.notna(value) and isinstance(value, (int, float)):
                functions.setdefault(fy, {})[label] = float(value)

    return functions


def edition_year(path: Path) -> int:
    match = re.search(r"pesa_(\d{4})_chapter", path.name)
    if not match:
        raise ValueError(f"Cannot parse edition year from {path.name}")
    return int(match.group(1))


def chapter4_path(edition: int) -> Path | None:
    for ext in (".xlsx", ".xls", ".ods"):
        candidate = PESA_DIR / f"pesa_{edition}_chapter4{ext}"
        if candidate.exists():
            return candidate
    return None


def merge_series(
    records: list[tuple[int, dict]],
) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    tme_frames: list[tuple[int, dict[str, float]]] = []
    func_frames: list[tuple[int, dict[str, dict[str, float]]]] = []

    for edition, data in records:
        if "tme_gbp_bn" in data:
            tme_frames.append((edition, data["tme_gbp_bn"]))
        if "by_function_gbp_bn" in data:
            func_frames.append((edition, data["by_function_gbp_bn"]))

    tme_out: dict[str, float] = {}
    for edition, series in sorted(tme_frames):
        for fy, value in series.items():
            tme_out[fy] = value  # newer edition overwrites

    func_out: dict[str, dict[str, float]] = {}
    for edition, series in sorted(func_frames):
        for fy, functions in series.items():
            func_out[fy] = functions

    return tme_out, func_out


def summarise_functions(by_year: dict[str, dict[str, float]]) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for fy, functions in sorted(by_year.items()):
        total = sum(functions.values())
        out[fy] = {}
        for fn, value in sorted(functions.items(), key=lambda x: -x[1]):
            out[fy][fn] = {
                "gbp_bn": round(value, 2),
                "pct": round(value / total * 100, 1) if total else 0.0,
            }
    return out


def main() -> None:
    paths = sorted(PESA_DIR.glob("pesa_*_chapter4.*"))
    if not paths:
        raise SystemExit(f"No PESA chapter 4 files in {PESA_DIR}. Run download_hm_treasury.py first.")

    editions_seen: set[int] = set()
    records: list[tuple[int, dict]] = []
    load_log: list[dict] = []

    for path in paths:
        edition = edition_year(path)
        if edition in editions_seen:
            continue
        editions_seen.add(edition)

        entry: dict = {"edition": edition, "file": path.name}
        try:
            tme = parse_table_41(path)
            functions = parse_table_42(path)
            records.append(
                (
                    edition,
                    {
                        "tme_gbp_bn": tme,
                        "by_function_gbp_bn": functions,
                    },
                )
            )
            entry.update(
                {
                    "status": "ok",
                    "tme_years": len(tme),
                    "function_years": len(functions),
                    "tme_first": min(tme) if tme else None,
                    "tme_last": max(tme) if tme else None,
                }
            )
        except Exception as exc:  # noqa: BLE001
            entry["status"] = "error"
            entry["error"] = str(exc)
        load_log.append(entry)

    tme_series, func_series = merge_series(records)
    tme_years = sorted(tme_series)
    func_years = sorted(func_series)

    summary = {
        "method": (
            "Merged HM Treasury PESA chapter 4 table 4.1 (TME aggregates) and "
            "table 4.2 (spending by COFOG function) from GOV.UK editions 2010–2025. "
            "Overlapping years use the latest edition. Values are nominal £ billion."
        ),
        "source_editions": sorted(editions_seen),
        "tme": {
            "financial_years": tme_years,
            "first_year": tme_years[0] if tme_years else None,
            "last_year": tme_years[-1] if tme_years else None,
            "total_managed_expenditure_gbp_bn": {fy: round(v, 2) for fy, v in tme_series.items()},
        },
        "spending_by_function": {
            "financial_years": func_years,
            "first_year": func_years[0] if func_years else None,
            "last_year": func_years[-1] if func_years else None,
            "uk_by_function": summarise_functions(func_series),
        },
        "load_log": load_log,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {OUT}")
    print(
        f"TME: {summary['tme'].get('first_year')} → {summary['tme'].get('last_year')} "
        f"({len(tme_years)} years)"
    )
    print(
        f"Functions: {summary['spending_by_function'].get('first_year')} → "
        f"{summary['spending_by_function'].get('last_year')} ({len(func_years)} years)"
    )


if __name__ == "__main__":
    main()
