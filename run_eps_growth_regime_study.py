"""run_eps_growth_regime_study.py

Phase 1 of the realized-growth regime study (session 2026-07-06). First
pass used only the "quality peer set" already established for the AVGO/LLY
valuation checkpoint (AAPL, GOOG, MA, TDG, MNST, ANET, COST) -- but that
set is pre-selected for having succeeded, so "high growth followed by good
returns" was close to circular. This version:

  1. Adds revenue growth alongside EPS growth as a regime input. AVGO's
     realized EPS growth is inflated by the VMware-acquisition amortization
     depressing its year-ago GAAP base (the same distortion already found
     in the fwd/trail ratio checkpoint) -- revenue isn't touched by that
     kind of non-cash charge, so it's a cleaner read for names with a large
     recent M&A-driven GAAP/non-GAAP gap.
  2. Adds a deliberate "growth disappointment" cohort (INTC, PYPL, ZM,
     PTON) -- real companies whose high-growth periods were followed by
     real, well-documented deceleration and price declines -- specifically
     to break the all-winners pattern the quality-only peer set produced.
     This is still a small, hand-picked set, not a fix for survivorship
     bias generally (that needs SEC's full filer universe, a separate,
     bigger piece of work) -- just a cheap check on whether the quality-set
     result was an artifact of who was in it.

Explicitly conditions on REALIZED past growth, not analyst-estimated
forward growth (unavailable -- see session notes). Small sample by this
project's own standards -- diversity flags reported honestly.

Usage:
    python run_eps_growth_regime_study.py
"""
from __future__ import annotations

import datetime as dt
import time
import warnings
from pathlib import Path

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

from sec_edgar import (
    fetch_diluted_eps_facts,
    fetch_revenue_facts,
    fetch_ticker_cik_map,
    reconstruct_quarterly_facts,
)
from eps_growth_regime import (
    capped_forward_return,
    diversity_flag,
    label_regimes,
    regime_label,
    summarize_returns,
    ttm_series,
    yoy_growth_series,
)

DATA_DIR = Path(__file__).parent / "data" / "raw" / "equities"

QUALITY_PEER_SET = ["AVGO", "LLY", "AAPL", "GOOG", "MA", "TDG", "MNST", "ANET", "COST"]
DISAPPOINTMENT_COHORT = ["INTC", "PYPL", "ZM", "PTON"]
ALL_TICKERS = QUALITY_PEER_SET + DISAPPOINTMENT_COHORT

FORWARD_HORIZONS = [63, 252]


def load_prices(ticker: str) -> dict[dt.date, float]:
    path = DATA_DIR / f"{ticker}.parquet"
    if path.exists():
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        series = df.set_index("date")["close"].sort_index().dropna()
        return {d.date(): float(v) for d, v in series.items()}

    # Not in the local store (e.g. a one-off research ticker not part of
    # the daily-sync universe) -- pull live via yfinance, in-memory only,
    # not written back to the shared parquet store.
    hist = yf.Ticker(ticker).history(period="max")
    return {d.date(): float(v) for d, v in hist["Close"].dropna().items()}


def build_ticker_growth(cik: str, fetch_fn) -> dict[dt.date, float]:
    facts = fetch_fn(cik)
    if not facts:
        return {}
    quarters = reconstruct_quarterly_facts(facts)
    ttm = ttm_series(quarters)
    return yoy_growth_series(ttm)


def run_metric(name: str, fetch_fn, cik_map: dict[str, str], tickers: list[str]) -> None:
    per_ticker_growth: dict[str, dict[dt.date, float]] = {}
    for tkr in tickers:
        cik = cik_map.get(tkr)
        if not cik:
            print(f"  {tkr}: CIK not found, skipping")
            continue
        try:
            g = build_ticker_growth(cik, fetch_fn)
            if g:
                per_ticker_growth[tkr] = g
            print(f"  {tkr}: {len(g)} {name} growth observations")
        except Exception as e:
            print(f"  {tkr}: ERROR {e}")
        time.sleep(0.2)  # polite pacing against SEC's rate limit

    all_growth = [g for series in per_ticker_growth.values() for g in series.values()]
    if len(all_growth) < 3:
        print(f"  Not enough {name} data to fit regime thresholds.")
        return
    p33, p67 = label_regimes(all_growth)
    print(f"\n  Pooled {name}-growth thresholds (N={len(all_growth)}): p33={p33:+.1%}  p67={p67:+.1%}")

    labeled = {
        tkr: {d: regime_label(g, p33, p67) for d, g in series.items()}
        for tkr, series in per_ticker_growth.items()
    }

    bucket_returns: dict[str, dict[int, list[float]]] = {
        b: {h: [] for h in FORWARD_HORIZONS} for b in ("LOW", "MID", "HIGH")
    }
    bucket_tickers: dict[str, set[str]] = {"LOW": set(), "MID": set(), "HIGH": set()}
    decel_returns: dict[int, list[float]] = {h: [] for h in FORWARD_HORIZONS}
    decel_tickers: set[str] = set()

    for tkr in per_ticker_growth:
        try:
            prices = load_prices(tkr)
        except Exception as e:
            print(f"  {tkr}: price data unavailable ({e}), skipping forward returns")
            continue

        dates_sorted = sorted(labeled[tkr].keys())
        for i, d in enumerate(dates_sorted):
            label = labeled[tkr][d]
            regime_end = dates_sorted[i + 1] if i + 1 < len(dates_sorted) else None
            for h in FORWARD_HORIZONS:
                r = capped_forward_return(prices, d, h, regime_end)
                if r is not None:
                    bucket_returns[label][h].append(r)
            bucket_tickers[label].add(tkr)

            if i + 1 < len(dates_sorted):
                next_label = labeled[tkr][dates_sorted[i + 1]]
                if label == "HIGH" and next_label in ("MID", "LOW"):
                    confirm_date = dates_sorted[i + 1]
                    confirm_end = dates_sorted[i + 2] if i + 2 < len(dates_sorted) else None
                    for h in FORWARD_HORIZONS:
                        r = capped_forward_return(prices, confirm_date, h, confirm_end)
                        if r is not None:
                            decel_returns[h].append(r)
                    decel_tickers.add(tkr)

    print(f"\n  --- Forward returns by {name}-growth regime ---")
    for label in ["LOW", "MID", "HIGH"]:
        n_tkrs = len(bucket_tickers[label])
        print(f"\n    {label}  (tickers: {n_tkrs}, {diversity_flag(n_tkrs)})")
        for h in FORWARD_HORIZONS:
            s = summarize_returns(bucket_returns[label][h])
            if s["n"] == 0:
                print(f"      {h}d: no data")
            else:
                print(f"      {h}d: median={s['median']:+.1%}  win_rate={s['win_rate']:.0%}  N={s['n']}")

    print(f"\n    DECELERATION (HIGH -> MID/LOW), tickers: {len(decel_tickers)}, {diversity_flag(len(decel_tickers))}")
    for h in FORWARD_HORIZONS:
        s = summarize_returns(decel_returns[h])
        if s["n"] == 0:
            print(f"      {h}d: no data")
        else:
            print(f"      {h}d: median={s['median']:+.1%}  win_rate={s['win_rate']:.0%}  N={s['n']}")

    print(f"\n  --- Current position ({name} growth) ---")
    for tkr in ["AVGO", "LLY"]:
        if tkr not in per_ticker_growth or not per_ticker_growth[tkr]:
            continue
        latest_date = max(per_ticker_growth[tkr].keys())
        latest_growth = per_ticker_growth[tkr][latest_date]
        label = regime_label(latest_growth, p33, p67)
        print(f"    {tkr}: TTM YoY {name} growth {latest_growth:+.1%} as of {latest_date} -> {label}")


def main() -> None:
    print("Fetching SEC ticker->CIK map...")
    cik_map = fetch_ticker_cik_map()

    print(f"\n{'='*62}\nEPS GROWTH (quality peer set + disappointment cohort)\n{'='*62}")
    run_metric("EPS", fetch_diluted_eps_facts, cik_map, ALL_TICKERS)

    print(f"\n{'='*62}\nREVENUE GROWTH (quality peer set + disappointment cohort)\n{'='*62}")
    run_metric("revenue", fetch_revenue_facts, cik_map, ALL_TICKERS)


if __name__ == "__main__":
    main()
