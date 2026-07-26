"""
run_opp_sleeve_combined_sensitivity.py

Combines two backlog findings that were each validated SEPARATELY, and each
explicitly disclaimed the same gap:

  1. run_opp_sleeve_stop_sensitivity.py (2026-07-24): dropping the hard stop
     entirely (N=0) + a trailing-peak stop (5% trigger / 5% trailing)
     outperformed the current always-on 2% hard stop by Calmar-like ratio --
     but only tested on a BLIND/2-gate-proxy population (above-MA50 + a
     price-only RS proxy), not the sleeve's real 4-gate entries.
  2. run_sleeve_entry_reconstruction.py (PR #45): on the REAL 4-gate gated
     entry population (~4,300 entries, 2009-2026), annualized median return
     DECLINES with hold duration (26.5% at 15d -> ~20-22% at 45-90d) --
     front-loaded edge, suggesting TIME_EXIT_DAYS=30 may already be generous.
     Explicitly flagged as NOT a verdict: a hard stop or MA50 breach would
     truncate many of those "held to duration X" trades before the time
     exit ever binds, so stop and duration were never tested together.

This script tests stop config x hold duration jointly, on the REAL 4-gate
entry population (reusing run_sleeve_entry_reconstruction.py's gate
reconstruction directly rather than re-deriving it), and additionally
stratifies every result by a realized-20d-volatility tercile at entry --
prompted by the question of whether one hard-coded stop/duration pair can
fit both a low-vol and a high-beta candidate, or whether the rule should be
asset-specific.

Neither of the two source scripts is modified or superseded for their own
narrower questions -- this is a new, additive cross-check.

Analysis only: no live trading-logic changes. Any recommendation from this
still needs explicit operator go-ahead before touching run_entry_screen.py /
fi_tracker.py, same as the two backlog items it builds on.

Usage:
    python run_opp_sleeve_combined_sensitivity.py
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    # Only when run directly -- doing this at import time would break
    # pytest's stdout/stderr capture for anything that imports this module
    # (same gotcha documented in the two scripts this one reuses).
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

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "opp_sleeve_combined_sensitivity.csv"

HARD_STOP_PCT = 0.02   # matches run_entry_screen.py's live constant
VOL_LOOKBACK  = 20     # trading days, realized-vol bucketing window
MIN_N_OBS     = 10     # minimum trades per (config, bucket) cell to report a stat

DURATION_GRID = [15, 21, 30, 45, 60, 90]   # calendar days, matches recon's grid

# (label, n_cutoff, trailing_trigger, trailing_pct)
# n_cutoff: "always" = hard stop active for the whole hold (current live
# behaviour); 0 = hard stop never active (MA50-only); an int = active for
# that many calendar days post-entry then off.
STOP_CONFIGS = [
    ("current_hardstop", "always", None, None),
    ("no_hardstop",       0,       None, None),
    ("trailing_5_5",      0,       0.05, 0.05),
    ("trailing_5_8",      0,       0.05, 0.08),
]


def realized_vol_at_entry(prices: pd.Series, entry_date: pd.Timestamp) -> float | None:
    """Trailing VOL_LOOKBACK-day stdev of daily returns, as of entry_date.
    Used only to rank/bucket entries into vol terciles -- not annualized,
    since only the relative ordering matters here."""
    vol = prices.pct_change().rolling(VOL_LOOKBACK).std()
    idx = vol.index.searchsorted(entry_date)
    if idx >= len(vol) or abs((vol.index[idx] - entry_date).days) > 5:
        return None
    v = vol.iloc[idx]
    return float(v) if pd.notna(v) else None


def simulate_trade(
    prices: pd.Series,
    ma50: pd.Series,
    entry_date: pd.Timestamp,
    duration_days: int,
    n_cutoff,
    trailing_trigger: float | None,
    trailing_pct: float | None,
) -> dict | None:
    """One simulated trade: entry at entry_date, held up to duration_days
    calendar days, exiting at whichever of {hard stop (if active), MA50,
    trailing-peak stop} binds first, else at the time exit. `ma50` must
    share `prices`' index (e.g. prices.rolling(50).mean()). Returns None if
    entry_date isn't resolvable in prices (missing/misaligned data)."""
    entry_idx = prices.index.searchsorted(entry_date)
    if entry_idx >= len(prices) or abs((prices.index[entry_idx] - entry_date).days) > 5:
        return None

    entry_price = float(prices.iloc[entry_idx])
    hard_stop_level = entry_price * (1 - HARD_STOP_PCT)
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
        if n_cutoff == "always" or (isinstance(n_cutoff, (int, float)) and days_since <= n_cutoff):
            levels.append(hard_stop_level)
        ma = ma50.iloc[i]
        if pd.notna(ma):
            levels.append(float(ma))
        if trailing_trigger is not None and (peak / entry_price - 1) >= trailing_trigger:
            levels.append(peak * (1 - trailing_pct))

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


def vol_bucket(v: float | None, q33: float, q67: float) -> str:
    if v is None:
        return "unknown"
    if v <= q33:
        return "low_vol"
    if v <= q67:
        return "mid_vol"
    return "high_vol"


def summarize(trades: list[dict], duration_days: int) -> dict:
    n = len(trades)
    if n < MIN_N_OBS:
        return {"n": n, "median_return": None, "win_rate": None,
                "annualized_median": None, "stopped_pct": None, "calmar_like": None}
    rets = np.array([t["return"] for t in trades])
    stopped = np.array([t["stopped"] for t in trades])
    med = float(np.median(rets))
    annualized = (1 + med) ** (365.25 / duration_days) - 1
    downside = rets[rets < 0]
    med_dd = float(np.median(downside)) if len(downside) else 0.0
    calmar = (med / abs(med_dd)) if med_dd != 0 else float("nan")
    return {
        "n": n,
        "median_return": round(med, 4),
        "win_rate": round(float((rets > 0).mean()), 3),
        "annualized_median": round(annualized, 4),
        "stopped_pct": round(float(stopped.mean()), 3),
        "calmar_like": round(calmar, 3) if not np.isnan(calmar) else None,
    }


def main() -> None:
    print("=" * 72)
    print("Opportunistic sleeve: combined stop x duration sensitivity")
    print("(real 4-gate entry population, stratified by entry-vol tercile)")
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
    for stop_name, n_cutoff, trigger, trail_pct in STOP_CONFIGS:
        for duration in DURATION_GRID:
            by_bucket: dict[str, list[dict]] = {"pooled": [], "low_vol": [], "mid_vol": [], "high_vol": []}
            for e in entries:
                prices = candidates[e["ticker"]][1]
                ma50 = ma50_by_ticker[e["ticker"]]
                trade = simulate_trade(prices, ma50, e["date"], duration, n_cutoff, trigger, trail_pct)
                if trade is None:
                    continue
                by_bucket["pooled"].append(trade)
                if e["vol_bucket"] != "unknown":
                    by_bucket[e["vol_bucket"]].append(trade)

            for bucket_name, trades in by_bucket.items():
                stats = summarize(trades, duration)
                rows.append({"stop_config": stop_name, "duration_days": duration,
                             "vol_bucket": bucket_name, **stats})

    df = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n")
    print(df.to_string(index=False))
    print(
        "\nReading this: compare stop_config x duration_days WITHIN each vol_bucket "
        "(and against 'pooled') on calmar_like and annualized_median. If the best "
        "combo differs materially by bucket, that's evidence the rule should be "
        "asset-specific rather than one global stop/duration pair; if buckets agree, "
        "the simpler single-rule fix stands. Cells with n < 10 are blanked, not "
        "reported, to avoid over-reading thin buckets -- treat all bucket-level "
        "results as directional pending more history. This is analysis only: no "
        "change to run_entry_screen.py / fi_tracker.py without explicit go-ahead."
    )


if __name__ == "__main__":
    main()
