"""Parse regional tax revenue by type and income tax by marginal band."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from council_tax_bands import build_council_tax_breakdown

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW = DATA_DIR / "raw"
FYE_LABEL = "2024 to 2025"
TAX_YEAR = "2024 to 2025"

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
    "United Kingdom",
]

ITLS_REGION_SHEETS = {
    "England": "2_2_Taxpayers_by_demographic_EN",
    "North East": "2_2_Taxpayers_by_demographic_NE",
    "North West": "2_2_Taxpayers_by_demographic_NW",
    "Yorkshire and The Humber": "2_2_Taxpayers_by_demographic_YH",
    "East Midlands": "2_2_Taxpayers_by_demographic_EM",
    "West Midlands": "2_2_Taxpayers_by_demographic_WM",
    "East of England": "2_2_Taxpayers_by_demographic_EE",
    "London": "2_2_Taxpayers_by_demographic_LD",
    "South East": "2_2_Taxpayers_by_demographic_SE",
    "South West": "2_2_Taxpayers_by_demographic_SW",
    "Wales": "2_2_Taxpayers_by_demographic_WA",
    "Scotland": "2_2_Taxpayers_by_demographic_SC",
    "Northern Ireland": "2_2_Taxpayers_by_demographic_NI",
}

BAND_COLUMNS = {
    "starting_lower": "Lower or starting rate [note 1][note 2]",
    "savers": "Savers rate [note 3]",
    "basic": "Basic rate [note 4]",
    "higher": "Higher rate [note 5]",
    "additional": "Additional rate [note 6]",
}

# ONS Table S9 revenue lines mapped to chart-friendly groups.
REVENUE_GROUPS: dict[str, str] = {
    "Income Tax": "income_tax",
    "Capital gains tax": "capital_gains_tax",
    "Corporation Tax": "corporation_tax",
    "Value added tax": "vat",
    "VAT net of refunds": "vat",
    "Council Tax": "council_tax",
    "Business rates paid by market sector bodies": "business_rates",
    "Business rates paid by private sector non-profit institutions": "business_rates",
    "Fuel Duties": "fuel_duties",
    "Tobacco Duties": "excise_duties",
    "Alcohol Duties": "excise_duties",
    "Stamp Duty Land Tax": "property_transaction_taxes",
    "Land Transaction Tax": "property_transaction_taxes",
    "Land and Buildings Transaction Tax": "property_transaction_taxes",
    "Social Contributions": "national_insurance",
    "Interest and Dividends": "interest_and_dividends",
    "Gross Operating Surplus": "gross_operating_surplus",
}


def find_year_column(df: pd.DataFrame) -> int:
    for col in range(df.shape[1]):
        for row in range(min(6, df.shape[0])):
            if str(df.iloc[row, col]).strip() == FYE_LABEL:
                return col
    raise ValueError(f"Could not find column {FYE_LABEL!r}")


def parse_numeric(value) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text or "[" in text:
        return None
    return float(text)


def parse_table_s9() -> pd.DataFrame:
    df = pd.read_excel(RAW / "crpsf_fye2025_supp.xlsx", "Table S9", header=None)
    col = find_year_column(df)
    rows: list[dict] = []
    current_type: str | None = None
    for i in range(3, df.shape[0]):
        revenue_type = str(df.iloc[i, 0]).strip()
        region = str(df.iloc[i, 1]).strip()
        if revenue_type and revenue_type != "nan":
            current_type = revenue_type
        if region not in REGIONS or not current_type:
            continue
        value = parse_numeric(df.iloc[i, col])
        if value is None:
            continue
        rows.append(
            {
                "revenue_type": current_type,
                "region": region,
                "gbp_m": value,
                "group": REVENUE_GROUPS.get(current_type, "other"),
            }
        )
    return pd.DataFrame(rows)


def aggregate_revenue_by_group(df: pd.DataFrame) -> dict:
    # Prefer VAT net of refunds over gross VAT line when both exist.
    vat = df[df["revenue_type"] == "VAT net of refunds"]
    if not vat.empty:
        df = df[df["revenue_type"] != "Value added tax"]

    grouped = (
        df.groupby(["region", "group"], as_index=False)["gbp_m"]
        .sum()
        .sort_values(["region", "gbp_m"], ascending=[True, False])
    )

    by_region: dict[str, dict] = {}
    for region in REGIONS:
        subset = grouped[grouped["region"] == region]
        if subset.empty:
            continue
        total = subset["gbp_m"].sum()
        taxes = {
            row["group"]: round(row["gbp_m"] / 1_000, 2)
            for _, row in subset.iterrows()
        }
        by_region[region] = {
            "total_revenue_bn": round(total / 1_000, 2),
            "by_type_bn": taxes,
            "by_type_pct": {
                k: round(v / (total / 1_000) * 100, 1) for k, v in taxes.items()
            },
        }

    # Detailed lines for power users.
    detail = (
        df.groupby(["region", "revenue_type"], as_index=False)["gbp_m"]
        .sum()
        .sort_values(["region", "gbp_m"], ascending=[True, False])
    )
    detailed: dict[str, list] = {}
    for region in REGIONS:
        subset = detail[detail["region"] == region]
        detailed[region] = [
            {
                "revenue_type": row["revenue_type"],
                "gbp_bn": round(row["gbp_m"] / 1_000, 3),
            }
            for _, row in subset.iterrows()
            if row["gbp_m"] > 0
        ]

    return {"summary": by_region, "detailed": detailed}


def parse_itls_payers(sheet_name: str) -> dict | None:
    df = pd.read_excel(RAW / "hmrc_itls.ods", sheet_name, header=None, engine="odf")
    header_row = None
    for i in range(df.shape[0]):
        if str(df.iloc[i, 0]).strip() == "Tax year":
            header_row = i
            break
    if header_row is None:
        return None

    columns = {str(df.iloc[header_row, j]).strip(): j for j in range(df.shape[1])}
    for i in range(header_row + 1, df.shape[0]):
        tax_year = str(df.iloc[i, 0]).strip()
        if not tax_year.startswith(TAX_YEAR):
            continue
        result: dict[str, float] = {}
        for key, column in BAND_COLUMNS.items():
            value = parse_numeric(df.iloc[i, columns[column]])
            if value is not None:
                result[f"{key}_payers_k"] = value
        all_payers = parse_numeric(df.iloc[i, columns["All Income Tax payers"]])
        if all_payers is not None:
            result["all_payers_k"] = all_payers
        return result
    return None


def uk_income_tax_liabilities_by_band() -> dict[str, float]:
    df = pd.read_excel(
        RAW / "hmrc_itls.ods", "2_5_IT_Liabilities_2024-25", header=None, engine="odf"
    )
    row = df.iloc[14]
    return {
        "savers": parse_numeric(row[2]) or 0.0,
        "basic": parse_numeric(row[4]) or 0.0,
        "higher": parse_numeric(row[6]) or 0.0,
        "additional": parse_numeric(row[8]) or 0.0,
    }


def uk_income_tax_payers_by_band() -> dict[str, float]:
    df = pd.read_excel(
        RAW / "hmrc_itls.ods", "2_5_IT_Liabilities_2024-25", header=None, engine="odf"
    )
    row = df.iloc[14]
    return {
        "savers": parse_numeric(row[1]) or 0.0,
        "basic": parse_numeric(row[3]) or 0.0,
        "higher": parse_numeric(row[5]) or 0.0,
        "additional": parse_numeric(row[7]) or 0.0,
    }


def ons_income_tax_by_region(df_s9: pd.DataFrame) -> dict[str, float]:
    subset = df_s9[df_s9["revenue_type"] == "Income Tax"]
    return {
        row["region"]: row["gbp_m"] / 1_000
        for _, row in subset.iterrows()
    }


def estimate_income_tax_by_band(
    df_s9: pd.DataFrame,
) -> dict[str, dict]:
    """
    Estimate regional income tax receipts by marginal band.

    HMRC publishes payer counts by band and region (ITLS 2.2) and UK liabilities
    by band (ITLS 2.5). ONS publishes accrued regional income tax totals (Table S9).
    We estimate band shares using average UK liability per payer in each band, then
    scale to the ONS regional income tax total.
    """
    ons_totals = ons_income_tax_by_region(df_s9)
    uk_liab = uk_income_tax_liabilities_by_band()
    uk_payers = uk_income_tax_payers_by_band()

    avg_liab_per_payer = {
        band: uk_liab[band] / uk_payers[band] if uk_payers[band] else 0.0
        for band in uk_liab
    }

    by_region: dict[str, dict] = {}
    for region, sheet in ITLS_REGION_SHEETS.items():
        payers = parse_itls_payers(sheet)
        if not payers or region not in ons_totals:
            continue

        raw_estimates: dict[str, float] = {}
        for band in uk_liab:
            payer_key = f"{band}_payers_k"
            if payer_key in payers:
                # payers in thousands; liabilities in £m → result in £m
                raw_estimates[band] = payers[payer_key] * avg_liab_per_payer[band]

        raw_total = sum(raw_estimates.values()) or 1.0
        target = ons_totals[region] * 1_000  # £m
        scale = target / raw_total

        scaled = {band: raw_estimates[band] * scale for band in raw_estimates}
        payer_counts = {
            band: payers.get(f"{band}_payers_k")
            for band in uk_liab
            if payers.get(f"{band}_payers_k") is not None
        }

        by_region[region] = {
            "income_tax_total_bn": round(ons_totals[region], 2),
            "by_band_bn": {k: round(v / 1_000, 2) for k, v in scaled.items()},
            "by_band_pct": {
                k: round(v / target * 100, 1) for k, v in scaled.items()
            },
            "payers_by_band_k": payer_counts,
            "all_payers_k": payers.get("all_payers_k"),
        }

    return by_region


def build_revenue_breakdown() -> dict:
    df_s9 = parse_table_s9()
    revenue = aggregate_revenue_by_group(df_s9)
    income_tax_bands = estimate_income_tax_by_band(df_s9)
    council_tax = build_council_tax_breakdown(df_s9)

    return {
        "fye": "2024-25",
        "sources": {
            "revenue_by_type_region": (
                "ONS Country and regional public sector finances supplementary Table S9"
            ),
            "income_tax_bands": (
                "HMRC Income Tax Liabilities Statistics tables 2.2 and 2.5, "
                "scaled to ONS regional income tax totals"
            ),
            "council_tax_bands": (
                "VOA CTSOP 1.0 (England/Wales) + NRS dwelling estimates (Scotland), "
                "receipts allocated by Band-D-equivalent stock"
            ),
        },
        "notes": {
            "revenue_basis": (
                "Accrued public sector current receipts on a residence basis "
                "('who pays'), consistent with ONS Country and Regional PSF."
            ),
            "income_tax_bands": (
                "Band £ estimates are modelled: regional payer counts from HMRC SPI "
                "× UK average liability per payer in each band, then scaled to match "
                "ONS regional income tax. Tax year 2024-25 ITLS figures are projected "
                "from 2021-22 SPI. Scottish/Welsh rate differences are reflected in "
                "marginal-rate payer classification but not as separate band labels."
            ),
            "band_labels": {
                "starting_lower": "Starting / lower rate payers",
                "savers": "Savings rate payers",
                "basic": "Basic rate payers (incl. Scottish starter/intermediate)",
                "higher": "Higher rate payers",
                "additional": "Additional rate payers (incl. Scottish advanced/top)",
            },
        },
        "revenue_by_type_and_region": revenue["summary"],
        "revenue_detailed_lines": revenue["detailed"],
        "income_tax_by_band_and_region": income_tax_bands,
        "council_tax_by_band_and_region": council_tax,
    }


def main() -> None:
    out_dir = DATA_DIR / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = build_revenue_breakdown()
    out_path = out_dir / "revenue_by_type_region_fye2025.json"
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
