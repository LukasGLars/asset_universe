"""sec_edgar.py

Pulls realized (GAAP) quarterly financials from SEC EDGAR's XBRL API --
free, official, and (validated 2026-07-06 against yfinance for AVGO/AAPL/
ANET diluted EPS) accurate to within a 1-cent rounding artifact. Reaches
back ~10 years, well beyond yfinance's 5-year cap on quarterly financials.

Key gotcha this module exists to handle: many 10-K filings only tag the
ANNUAL figure in XBRL, not a standalone Q4 duration fact -- Q4 has to be
derived as annual minus the sum of the other three discrete quarters.
Confirmed present for AVGO, AAPL, and ANET (three different fiscal
year-end conventions) on diluted EPS specifically, so it isn't an
AVGO-only quirk; the same derivation applies to any duration-based
concept, including revenue.

Revenue growth was added 2026-07-06 alongside EPS growth: AVGO's realized
EPS growth is inflated by the VMware-acquisition amortization depressing
its year-ago GAAP base (the same distortion already found in the fwd/trail
ratio work) -- revenue isn't touched by that kind of non-cash charge, so
it's a cleaner regime input for names with a large recent M&A-driven
GAAP/non-GAAP gap.

`fetch_*_facts()` functions do the network call (impure, need a real
User-Agent per SEC's policy). `reconstruct_quarterly_facts()` is the pure
logic -- dedup by most-recently-filed, derive missing Q4s -- and is what's
actually unit tested. Generic to any XBRL duration concept, not EPS-specific.
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.request

USER_AGENT = "AssetUniverseResearch contact@example.com"

# Companies vary in which revenue concept they tag; try in this order and
# use whichever the filer actually reports.
REVENUE_CONCEPTS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"]


def fetch_ticker_cik_map() -> dict[str, str]:
    """SEC's bulk ticker -> CIK mapping. CIKs come back zero-padded to 10 digits."""
    url = "https://www.sec.gov/files/company_tickers.json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())
    return {v["ticker"]: str(v["cik_str"]).zfill(10) for v in data.values()}


def _fetch_company_concept(cik: str, concept: str, unit: str) -> list[dict]:
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())
    return data.get("units", {}).get(unit, [])


def fetch_diluted_eps_facts(cik: str) -> list[dict]:
    """Raw XBRL us-gaap:EarningsPerShareDiluted facts for one CIK. Returns
    the raw entries list (start/end/val/form/filed/...) -- reconstruction
    logic lives in reconstruct_quarterly_facts(), kept separate for testing."""
    return _fetch_company_concept(cik, "EarningsPerShareDiluted", "USD/shares")


def fetch_revenue_facts(cik: str) -> list[dict]:
    """Raw XBRL revenue facts for one CIK, trying REVENUE_CONCEPTS in order
    (filers differ on which tag they use) and returning the first non-empty
    result. Empty list if the CIK reports under neither concept."""
    for concept in REVENUE_CONCEPTS:
        try:
            facts = _fetch_company_concept(cik, concept, "USD")
        except Exception:
            continue
        if facts:
            return facts
    return []


def reconstruct_quarterly_facts(facts: list[dict]) -> dict[dt.date, float]:
    """Dedups restated periods (keep most-recently-filed per start/end
    pair) and derives any fiscal year's missing 4th quarter as the annual
    figure minus the sum of the other three discrete quarters -- the
    standard technique for XBRL filers that only tag the annual figure.
    Generic to any duration-based concept (EPS, revenue, ...). Returns
    {period_end_date: value}, most raw fields not kept."""
    by_period: dict[tuple[str, str], dict] = {}
    for e in facts:
        key = (e["start"], e["end"])
        if key not in by_period or e["filed"] > by_period[key]["filed"]:
            by_period[key] = e

    entries = []
    for e in by_period.values():
        start_d = dt.date.fromisoformat(e["start"])
        end_d = dt.date.fromisoformat(e["end"])
        entries.append({**e, "start_d": start_d, "end_d": end_d, "dur": (end_d - start_d).days})

    discrete_q = {e["end_d"]: e["val"] for e in entries if 80 <= e["dur"] <= 100}
    annuals = [e for e in entries if 350 <= e["dur"] <= 380]

    results: dict[dt.date, float] = dict(discrete_q)

    for ann in annuals:
        q_in_year = sorted(d for d in discrete_q if ann["start_d"] < d <= ann["end_d"])
        if len(q_in_year) == 3 and ann["end_d"] not in results:
            derived = round(ann["val"] - sum(discrete_q[d] for d in q_in_year), 2)
            results[ann["end_d"]] = derived

    return dict(sorted(results.items(), key=lambda kv: kv[0], reverse=True))
