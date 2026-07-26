"""
run_opp_sleeve_ma50_stop_sensitivity.py

Direct follow-on to run_opp_sleeve_combined_sensitivity.py's headline finding
(2026-07-26): on the real 4-gate entry population, EVERY stop config tested
-- including dropping the hard stop entirely + adding a trailing-peak stop --
had a NEGATIVE median return at every duration and every vol bucket. That
directly contradicts run_sleeve_entry_reconstruction.py's own raw finding on
the identical entries: held with NO exit rule at all, the same population
returned +26.5% annualized at 15 days. The one stop left unconditionally
active in every config of that study was MA50 (matches live binding_stop()
= max(hard_stop_if_active, ma50) -- MA50 always binds once above it). Since
these entries qualify by NOT being extended (gate 3: extension <= p67), they
sit close to their own MA50 by construction -- a plausible reason MA50 gets
touched by ordinary noise well before any real trend reversal, exiting right
before the recovery the raw hold captures.

This script isolates that variable: holds the already-validated pieces fixed
(hard stop OFF, trailing-peak stop at the winning 5% trigger / 5% trailing
from the combined study) and tests loosening MA50 two ways, independently
and combined:

  1. Grace period: MA50 doesn't bind for the first N calendar days post-
     entry (same mechanic already validated for the hard stop's own N-cutoff
     in run_opp_sleeve_stop_sensitivity.py, applied here to MA50 instead).
  2. Buffer: MA50 must be cleared by a margin (price <= ma50 * (1 - buffer))
     before it binds, instead of any close at or below the raw average.

Also includes an "ma50_off" bracketing case (grace period effectively
infinite) to show the ceiling if MA50 contributed nothing as a stop at all
-- not a serious live candidate on its own (no protection against a real
breakdown), but useful to see how much of the gap it explains.

Same population, same vol-tercile stratification, same discipline as the
study this follows on from.

NOT built here (bigger, separate task if this doesn't close the gap):
modeling re-entry after a stop-out. This sim treats every stop-out as a dead
trade; the real sleeve re-screens daily and could re-enter the same or a
different candidate, so real drag from an early MA50 stop is probably
smaller than what this script reports. Flagged, not modeled.

Analysis only: no live trading-logic change without explicit operator
go-ahead, same as every other script in this backlog.

Usage:
    python run_opp_sleeve_ma50_stop_sensitivity.py
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.store import reader

import run_sleeve_entry_reconstruction as recon
from run_opp_sleeve_combined_sensitivity import realized_vol_at_entry, summarize, vol_bucket

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "opp_sleeve_ma50_stop_sensitivity.csv"

HARD_STOP_PCT   = 0.02   # unused here (hard stop held OFF throughout) but kept
                          # for parity with the combined script's constant
TRAILING_TRIGGER = 0.05  # winning pair from the combined study, held fixed
TRAILING_PCT     = 0.05
VOL_LOOKBACK     = 20
MIN_N_OBS        = 10
NEVER = 10 ** 6  # sentinel grace-period length -> MA50 never binds

DURATION_GRID = [15, 21, 30, 45, 60, 90]

# (label, ma50_grace_days, ma50_buffer_pct)
MA50_CONFIGS = [
    ("ma50_always_tight",     0,    0.00),  # current live behaviour (MA50 binds immediately, no buffer)
    ("ma50_grace_10d",       10,    0.00),
    ("ma50_grace_20d",       20,    0.00),
    ("ma50_buffer_3pct",      0,    0.03),
    ("ma50_buffer_5pct",      0,    0.05),
    ("ma50_grace10_buffer3", 10,    0.03),
    ("ma50_off",           NEVER,   0.00),  # bracketing case, not a live candidate on its own
]


def simulate_trade(
    prices: pd.Series,
    ma50: pd.Series,
    entry_date: pd.Timestamp,
    duration_days: int,
    ma50_grace_days: int,
    ma50_buffer_pct: float,
) -> dict | None:
    """Same mechanics as run_opp_sleeve_combined_sensitivity.simulate_trade,
    with the hard stop permanently off and the winning trailing-peak stop
    (TRAILING_TRIGGER/TRAILING_PCT) permanently on, isolating MA50's grace
    period and buffer as the only variables under test."""
    entry_idx = prices.index.searchsorted(entry_date)
    if entry_idx >= len(prices) or abs((prices.index[entry_idx] - entry_date).days) > 5:
        return None

    entry_price = float(prices.iloc[entry_idx])
    peak = entry_price
    target_date = entry_date + pd.Timedelta(days=duration_days)

    exit_price, stopped = None, False
    i = entry_idx
    while True:
        i += 1
        if i >= len(prices) or prices.index[i] > target_date:
            break
        price = float(prices.iloc[i])
        peak = max(peak, price)
        days_since = (prices.index[i] - entry_date).days

        levels = []
        ma = ma50.iloc[i]
        if days_since >= ma50_grace_days and pd.notna(ma):
            levels.append(float(ma) * (1 - ma50_buffer_pct))
        if (peak / entry_price - 1) >= TRAILING_TRIGGER:
            levels.append(peak * (1 - TRAILING_PCT))

        binding = max(levels) if levels else -np.inf
        if price <= binding:
            exit_price, stopped = price, True
            break

    if exit_price is None:
        idx = prices.index.searchsorted(target_date)
        if idx >= len(prices):
            idx = len(prices) - 1
        if prices.index[idx] > target_date and idx > entry_idx:
            idx -= 1
        if idx <= entry_idx:
            return None
        exit_price = float(prices.iloc[idx])

    return {"return": (exit_price - entry_price) / entry_price, "stopped": stopped}


def main() -> None:
    print("=" * 72)
    print("Opportunistic sleeve: MA50 stop grace-period x buffer sensitivity")
    print("(hard stop OFF, trailing 5%/5% ON throughout -- isolates MA50)")
    print("=" * 72)

    print("\nBuilding regime labels...")
    labeled_df, _ = regime_module.build(DATA_DIR)

    print("Loading full candidate universe...")
    candidates = recon.load_candidates(DATA_DIR)
    print(f"Candidates: {len(candidates)}")

    print("Detecting regime transitions + walk-forward ranking...")
    transitions = recon.detect_transitions(labeled_df)
    selections = recon.rank_at_transitions(transitions, labeled_df, candidates)

    print("Loading benchmark (SPY)...")
    bm_path = reader.ticker_path(DATA_DIR, "equities", recon.BENCHMARK)
    bm_prices = reader.load(bm_path)["close"].dropna().sort_index()

    print("Scanning full history for the real 4-gate entry population...")
    raw_events = recon.find_gated_entries(selections, candidates, bm_prices)
    entries = recon.decluster(raw_events)
    print(f"Declustered real gated-entry population: {len(entries)}")

    tickers_used = {e["ticker"] for e in entries}
    ma50_by_ticker = {t: candidates[t][1].rolling(50, min_periods=25).mean() for t in tickers_used}

    vols = []
    for e in entries:
        prices = candidates[e["ticker"]][1]
        e["vol"] = realized_vol_at_entry(prices, e["date"])
        if e["vol"] is not None:
            vols.append(e["vol"])
    q33, q67 = np.quantile(np.array(vols), [1 / 3, 2 / 3])
    for e in entries:
        e["vol_bucket"] = vol_bucket(e["vol"], q33, q67)
    print(f"Vol tercile cutoffs (trailing {VOL_LOOKBACK}d daily-return stdev): "
          f"q33={q33:.4f}, q67={q67:.4f}")

    rows = []
    for ma_label, grace, buffer_pct in MA50_CONFIGS:
        for duration in DURATION_GRID:
            by_bucket: dict[str, list[dict]] = {"pooled": [], "low_vol": [], "mid_vol": [], "high_vol": []}
            for e in entries:
                prices = candidates[e["ticker"]][1]
                ma50 = ma50_by_ticker[e["ticker"]]
                trade = simulate_trade(prices, ma50, e["date"], duration, grace, buffer_pct)
                if trade is None:
                    continue
                by_bucket["pooled"].append(trade)
                if e["vol_bucket"] != "unknown":
                    by_bucket[e["vol_bucket"]].append(trade)

            for bucket_name, trades in by_bucket.items():
                stats = summarize(trades, duration)
                rows.append({"ma50_config": ma_label, "duration_days": duration,
                             "vol_bucket": bucket_name, **stats})

    df = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n")
    print(df.to_string(index=False))
    print(
        "\nReading this: ma50_always_tight reproduces the combined study's "
        "trailing_5_5 numbers (still negative everywhere) -- the baseline to "
        "beat. If loosening the grace period / adding a buffer brings "
        "median_return and calmar_like back toward (or past) zero, that "
        "confirms MA50-touch noise -- not a real breakdown -- was eating the "
        "entries' edge. ma50_off is a bracketing case, not a live candidate: "
        "it shows the ceiling with no ongoing downside protection at all. "
        "This still doesn't model re-entry after a stop-out (see module "
        "docstring) -- real drag from a tight MA50 is probably smaller than "
        "shown here. Analysis only: no change to run_entry_screen.py / "
        "fi_tracker.py without explicit go-ahead."
    )


if __name__ == "__main__":
    main()
