"""collections_monitor.py

Days-sales-outstanding monitor beside Sightline. Sightline watches whether
demand holds (segment revenue YoY); this watches whether customers PAY. A
customer-funding problem shows up here first, while revenue YoY is still
strongly positive -- see config/collections.toml for the why and the
pre-registered thresholds.

States: OK, WARN (informs), BREAK (a pre-committed REVIEW, not a sell --
the action text is read from collections.toml), INSUFFICIENT
(not enough quarters for a baseline). Derived from the filings every run.

Pure logic (`dso_series`, `derive_state`) is separate from the EDGAR fetch
so it is testable offline.
"""
from __future__ import annotations

import datetime as dt
import statistics
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

CONFIG_PATH = Path(__file__).parent / "config" / "collections.toml"
AR_CONCEPT = "AccountsReceivableNetCurrent"
DAYS_PER_QUARTER = 91

OK, WARN, BREAK, INSUFFICIENT = "OK", "WARN", "BREAK", "INSUFFICIENT"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def latest_instants(facts: list[dict]) -> dict[dt.date, float]:
    """AR is an INSTANT concept (no start date), so reconstruct_quarterly_facts
    does not apply. Keeps the most recently filed value per balance-sheet date,
    so a restatement wins over the original."""
    best: dict[str, dict] = {}
    for e in facts:
        if "start" in e:
            continue
        if e["end"] not in best or e["filed"] > best[e["end"]]["filed"]:
            best[e["end"]] = e
    return {dt.date.fromisoformat(k): float(v["val"]) for k, v in best.items()}


def dso_series(ar: dict[dt.date, float],
               revenue: dict[dt.date, float]) -> list[tuple[dt.date, float]]:
    """Chronological (quarter_end, DSO). Only quarters where AR and revenue
    share the exact period-end date -- a near-miss date is a different
    balance sheet, not a match."""
    out = []
    for d in sorted(set(ar) & set(revenue)):
        if revenue[d] > 0:
            out.append((d, ar[d] / revenue[d] * DAYS_PER_QUARTER))
    return out


def _ratios(series: list[tuple[dt.date, float]], n: int) -> list[tuple[dt.date, float, float, float]]:
    """(date, dso, trailing median of the prior n, dso / median) for every
    quarter that has n prior quarters."""
    out = []
    for i in range(n, len(series)):
        med = statistics.median(v for _, v in series[i - n:i])
        d, v = series[i]
        out.append((d, v, med, v / med if med > 0 else float("nan")))
    return out


def derive_state(series: list[tuple[dt.date, float]], cfg: dict) -> tuple[str, str]:
    """(state, detail) from the latest quarters. BREAK takes precedence over
    WARN; neither is sticky."""
    n = int(cfg["baseline_quarters"])
    k = int(cfg["confirm_quarters"])
    rat = _ratios(series, n)
    if not rat:
        return INSUFFICIENT, f"{len(series)} quarters, need {n + 1}"
    d, v, med, r = rat[-1]
    detail = f"{d.isoformat()}: {v:.0f} days ({r:.2f}x {n}Q median {med:.0f})"
    if len(rat) >= k and all(x[3] > cfg["break_multiple"] for x in rat[-k:]):
        return BREAK, detail
    if r > cfg["warn_multiple"]:
        return WARN, detail
    return OK, detail


def fetch_series(ticker: str) -> list[tuple[dt.date, float]]:
    import sec_edgar
    cik = sec_edgar.fetch_ticker_cik_map()[ticker]
    ar = latest_instants(sec_edgar._fetch_company_concept(cik, AR_CONCEPT, "USD"))
    rev = sec_edgar.reconstruct_quarterly_facts(sec_edgar.fetch_revenue_facts(cik))
    return dso_series(ar, rev)


def format_dashboard_lines(states: dict[str, tuple[str, str]], cfg: dict) -> list[str]:
    """The block fi_tracker prints. 'Collections' and the '<TICKER> DSO'
    labels are what check_signal_changes greps -- keep them stable. Never
    prints "[unavailable" or "Error": check_sync_health fails the sync on
    either, and a transient SEC outage must not do that."""
    out = ["  Collections  [DSO -- BREAK triggers a review, never a sell]"]
    for tkr, (state, detail) in states.items():
        c = cfg[tkr]
        out.append(f"    {tkr} DSO")
        out.append(f"      Latest     : {detail}")
        out.append(f"      State      : {state}")
        out.append(f"      Rule       : warn >{c['warn_multiple']}x, break >{c['break_multiple']}x "
                   f"for {c['confirm_quarters']}Q, vs prior {c['baseline_quarters']}Q median")
        out.append(f"      Action     : {c['break_action']}")
    return out


def live_states(cfg: dict | None = None) -> dict[str, tuple[str, str]]:
    """{ticker: (state, detail)}. A fetch failure reads as state
    'fetch_failed' -- the alerter's unknown-guard skips it, so an SEC outage
    is silent rather than a false OK or a false BREAK."""
    cfg = cfg if cfg is not None else load_config()
    out = {}
    for tkr in cfg:
        try:
            out[tkr] = derive_state(fetch_series(tkr), cfg[tkr])
        except Exception as e:
            out[tkr] = ("fetch_failed", type(e).__name__.replace("Error", ""))
    return out
