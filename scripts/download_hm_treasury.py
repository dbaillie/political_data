#!/usr/bin/env python3
"""Download historical HM Treasury CRA and PESA workbooks from GOV.UK."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW = DATA_DIR / "raw" / "hm_treasury"
CRA_DIR = RAW / "cra"
PESA_DIR = RAW / "pesa"
MANIFEST = RAW / "manifest.json"

CRA_FIRST_YEAR = 2013
CRA_LAST_YEAR = 2025
PESA_FIRST_YEAR = 2010
PESA_LAST_YEAR = 2025

USER_AGENT = "political_data/1.0 (research; github.com/dbaillie/political_data)"


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def download_file(url: str, dest: Path, retries: int = 4, force: bool = False) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not force and dest.exists() and dest.stat().st_size > 10_000:
        return

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            if len(data) < 10_000:
                raise ValueError(f"File too small ({len(data)} bytes)")
            dest.write_bytes(data)
            return
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            if attempt == retries - 1:
                raise
            time.sleep(4 * (2**attempt))
            last_exc = exc
    raise last_exc  # type: ignore[misc]


def find_assets_urls(html: str, pattern: str) -> list[str]:
    matches = re.findall(
        r"https://assets\.publishing\.service\.gov\.uk/[^\"'\s>]+\.(?:xlsx?|ods)",
        html,
        flags=re.I,
    )
    selected = [u for u in matches if re.search(pattern, u, flags=re.I)]
    # preserve order, dedupe
    seen: set[str] = set()
    out: list[str] = []
    for url in selected:
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def pick_cra_database_url(html: str) -> str | None:
    urls = find_assets_urls(html, r"database")
    if not urls:
        urls = find_assets_urls(html, r"combined.*database")
    return urls[0] if urls else None


def is_pesa_chapter_url(url: str, chapter: int) -> bool:
    """Match PESA chapter N URLs without confusing chapter 1 with chapter 10."""
    path = urlparse(url).path
    normalised = re.sub(r"[%_\-]+", " ", path.lower())
    # Reject multi-digit chapter numbers that share a prefix (e.g. 10, 11 for ch 1).
    for other in range(10, 20):
        if other != chapter and re.search(rf"\bchapter\s*{other}\b", normalised):
            if chapter == 1 and other == 10:
                continue  # handled below
            pass
    if chapter == 1:
        if re.search(r"\bchapter\s*1[0-9]\b", normalised):
            return False
        if re.search(r"chapter1[0-9]", path.lower()):
            return False
        patterns = (
            r"chapter[_\s-]?1(?:[_\s.]|\.(?:xls|xlsx|ods)|$)",
            r"chapter1\.(?:xls|xlsx|ods)",
            r"tables_chapter1\.(?:xls|xlsx|ods)",
            r"cp_chapter_1",
            r"cm_chapter_1",
            r"chapter_1_tables",
            r"chapter_1\.",
        )
    else:
        patterns = (
            rf"chapter[_\s-]?{chapter}(?:[_\s.]|\.(?:xls|xlsx|ods)|$)",
            rf"chapter{chapter}\.(?:xls|xlsx|ods)",
            rf"tables_chapter{chapter}\.(?:xls|xlsx|ods)",
            rf"cp_chapter_{chapter}",
            rf"cm_chapter_{chapter}",
            rf"chapter_{chapter}_tables",
            rf"chapter_{chapter}\.",
        )
    return any(re.search(p, path, flags=re.I) for p in patterns)


def pick_pesa_chapter_urls(html: str) -> dict[int, str]:
    all_urls = find_assets_urls(html, r"chapter|ch[0-9]")
    chapters: dict[int, str] = {}
    for ch in (1, 4):
        matches = [u for u in all_urls if is_pesa_chapter_url(u, ch)]
        if matches:
            # Prefer standard tables over interactive/database variants.
            matches.sort(
                key=lambda u: (
                    "database" in u.lower(),
                    "interactive" in u.lower(),
                    u.lower(),
                )
            )
            chapters[ch] = matches[0]
    return chapters


def govuk_stats_url(collection: str, year: int) -> str:
    return f"https://www.gov.uk/government/statistics/{collection}-{year}"


def download_cra() -> list[dict]:
    records: list[dict] = []
    for year in range(CRA_FIRST_YEAR, CRA_LAST_YEAR + 1):
        page_url = govuk_stats_url("country-and-regional-analysis", year)
        dest = CRA_DIR / f"cra_{year}_database.xlsx"
        try:
            html = fetch_html(page_url)
            file_url = pick_cra_database_url(html)
            if not file_url:
                records.append({"edition": year, "status": "no_database_url", "page": page_url})
                continue
            download_file(file_url, dest)
            records.append(
                {
                    "edition": year,
                    "status": "ok",
                    "page": page_url,
                    "url": file_url,
                    "path": str(dest.relative_to(DATA_DIR)),
                    "bytes": dest.stat().st_size,
                }
            )
        except Exception as exc:  # noqa: BLE001 - collect per-year errors
            records.append({"edition": year, "status": "error", "page": page_url, "error": str(exc)})
    return records


def download_pesa(chapters: tuple[int, ...] = (1, 4), force: bool = False) -> list[dict]:
    records: list[dict] = []
    for year in range(PESA_FIRST_YEAR, PESA_LAST_YEAR + 1):
        page_url = govuk_stats_url("public-expenditure-statistical-analyses", year)
        try:
            html = fetch_html(page_url)
            urls = pick_pesa_chapter_urls(html)
            if not urls:
                records.append({"edition": year, "status": "no_files", "page": page_url})
                continue
            year_files: dict[str, str] = {}
            for ch in chapters:
                if ch not in urls:
                    continue
                ext = Path(urlparse(urls[ch]).path).suffix.lower()
                if ext not in {".xls", ".xlsx", ".ods"}:
                    ext = ".xlsx"
                dest = PESA_DIR / f"pesa_{year}_chapter{ch}{ext}"
                download_file(urls[ch], dest, force=force)
                year_files[f"chapter_{ch}"] = str(dest.relative_to(DATA_DIR))
            records.append(
                {
                    "edition": year,
                    "status": "ok" if year_files else "partial",
                    "page": page_url,
                    "files": year_files,
                    "urls": {f"chapter_{k}": v for k, v in urls.items() if k in chapters},
                }
            )
        except Exception as exc:  # noqa: BLE001
            records.append({"edition": year, "status": "error", "page": page_url, "error": str(exc)})
    return records


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force-pesa",
        action="store_true",
        help="Re-download PESA chapter files even if they already exist",
    )
    args = parser.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {
        "cra": download_cra(),
        "pesa": download_pesa(force=args.force_pesa),
        "notes": {
            "cra": "Each edition contains ~5 outturn years; merge with build_cra_history.py",
            "pesa": "Chapter 1 = TME/budget aggregates; Chapter 4 = spending by function",
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2))
    ok_cra = sum(1 for r in manifest["cra"] if r["status"] == "ok")
    ok_pesa = sum(1 for r in manifest["pesa"] if r["status"] == "ok")
    print(f"Wrote {MANIFEST}")
    print(f"CRA: {ok_cra}/{len(manifest['cra'])} editions downloaded")
    print(f"PESA: {ok_pesa}/{len(manifest['pesa'])} editions downloaded")


if __name__ == "__main__":
    main()
