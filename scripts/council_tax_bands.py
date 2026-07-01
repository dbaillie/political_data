"""Council tax property stock and estimated receipts by band (A–H) and region."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW = DATA_DIR / "raw"

BANDS = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
BAND_D_RATIO = {
    "A": 6 / 9,
    "B": 7 / 9,
    "C": 8 / 9,
    "D": 1.0,
    "E": 11 / 9,
    "F": 13 / 9,
    "G": 15 / 9,
    "H": 18 / 9,
    "I": 21 / 9,
}

ENGLISH_REGIONS = [
    "North East",
    "North West",
    "Yorkshire and The Humber",
    "East Midlands",
    "West Midlands",
    "East of England",
    "London",
    "South East",
    "South West",
]


def _parse_numeric(value) -> float:
    if pd.isna(value):
        return 0.0
    text = str(value).strip()
    if not text or text in {"..", "-", "nan", "[z]"}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_ctsop_england_wales() -> dict[str, dict[str, float]]:
    """VOA CTSOP1.0_SUP: dwellings by band for English regions and Wales."""
    df = pd.read_excel(RAW / "ctsop1.0_supp_2024.xlsx", "CTSOP1.0", header=None)
    band_cols = {band: idx for idx, band in zip(range(5, 14), BANDS)}
    out: dict[str, dict[str, float]] = {}

    for _, row in df.iterrows():
        geography = str(row.iloc[1]).strip()
        area = str(row.iloc[4]).strip()
        if geography == "REGL" and area in ENGLISH_REGIONS:
            region = area
        elif area == "Wales":
            region = "Wales"
        else:
            continue

        counts = {band: _parse_numeric(row.iloc[col]) for band, col in band_cols.items()}
        out[region] = counts
    return out


def parse_scotland_bands() -> dict[str, float]:
    """NRS dwelling estimates by data zone, aggregated to Scotland."""
    df = pd.read_excel(RAW / "scotland_dwelling_est_2024.xlsx", "2024", header=4)
    band_cols = [c for c in df.columns if "Council Tax band" in str(c)]
    totals = df[band_cols].apply(pd.to_numeric, errors="coerce").sum()
    mapping = {}
    for col, value in totals.items():
        band = col.split("\n")[-1].strip()
        mapping[band] = float(value)
    return mapping


def council_tax_revenue_from_parsed(df_s9: pd.DataFrame) -> dict[str, float]:
    subset = df_s9[df_s9["revenue_type"] == "Council Tax"]
    return {row["region"]: row["gbp_m"] / 1_000 for _, row in subset.iterrows()}


def band_d_equivalent(counts: dict[str, float]) -> dict[str, float]:
    return {band: counts.get(band, 0.0) * BAND_D_RATIO[band] for band in BANDS}


def allocate_revenue(
    counts: dict[str, float], total_revenue_bn: float
) -> dict[str, float]:
    """Allocate regional council tax £bn to bands by Band-D-equivalent dwelling share."""
    weights = band_d_equivalent(counts)
    total_weight = sum(weights.values()) or 1.0
    return {
        band: round(total_revenue_bn * weights[band] / total_weight, 3)
        for band in BANDS
        if counts.get(band, 0) > 0
    }


def build_council_tax_breakdown(df_s9: pd.DataFrame) -> dict:
    stock = parse_ctsop_england_wales()
    stock["Scotland"] = parse_scotland_bands()
    revenue = council_tax_revenue_from_parsed(df_s9)

    by_region: dict[str, dict] = {}
    for region, counts in stock.items():
        if region not in revenue or revenue[region] <= 0:
            continue
        total_dwellings = sum(counts.get(b, 0) for b in BANDS)
        d_equiv = sum(band_d_equivalent(counts).values())
        by_band_bn = allocate_revenue(counts, revenue[region])
        by_region[region] = {
            "council_tax_total_bn": round(revenue[region], 3),
            "dwellings_by_band": {b: int(counts.get(b, 0)) for b in BANDS if counts.get(b, 0)},
            "dwellings_total": int(total_dwellings),
            "band_d_equivalent_dwellings": round(d_equiv),
            "estimated_receipts_by_band_bn": by_band_bn,
            "estimated_receipts_by_band_pct": {
                b: round(v / revenue[region] * 100, 1) for b, v in by_band_bn.items()
            },
        }

    return {
        "reference_date": "2024-09-15 (England/Wales VOA); 2024-12 (Scotland NRS)",
        "method": (
            "Property counts from VOA CTSOP (England regions, Wales) and NRS dwelling "
            "estimates (Scotland). Receipts allocated to bands proportionally to "
            "Band-D-equivalent dwellings (A=6/9 … H=18/9, I=21/9), scaled to ONS "
            "regional council tax totals."
        ),
        "northern_ireland_note": (
            "Northern Ireland has no council tax; domestic rates are reported separately "
            "in ONS revenue tables (not split by property band)."
        ),
        "by_region": by_region,
    }
