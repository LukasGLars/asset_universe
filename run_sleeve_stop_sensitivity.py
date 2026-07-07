"""
run_sleeve_stop_sensitivity.py

Validates HARD_STOP_PCT (run_entry_screen.py -- currently a flat 2%
applied to every sleeve candidate regardless of its own volatility)
against the sleeve's real gated-entry population. Same population
run_sleeve_entry_reconstruction.py built for the exit-duration question
(PR #45); same gap that PR explicitly flagged as deliberately not built:
a compound-exit simulation where a hard stop can cut a trade short
before the time exit ever binds.

For each real gated entry and each candidate HARD_STOP_PCT, simulates:
walk forward day-by-day from entry, capped at TIME_EXIT_DAYS=30 calendar
days (the current live time exit) -- if the close ever drops below
entry_price * (1 - pct), the trade exits there (return = -pct, the exact
stop price); otherwise the trade runs the full 30 days and its actual
forward return is used.

Reports, per HARD_STOP_PCT: n, median return, win rate, AND
stopped_out_frac (how often that threshold actually bites) -- this last
one didn't exist in the duration study and is the key diagnostic for
whether a stop is too tight (stops out often, cuts winners short on
normal noise) or too loose (rarely triggers, little real protection).

Self-check: HARD_STOP_PCT=0.02 (the live value) is one of the grid cells,
so its own result is directly comparable to the others in the same
table, not computed separately.

Output: comparison_results/sleeve_stop_sensitivity_grid.csv + console.
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.store import reader

from run_sleeve_entry_reconstruction import (
    BENCHMARK,
    decluster,
    detect_transitions,
    find_gated_entries,
    load_candidates,
    rank_at_transitions,
)

DATA_DIR = config.raw_data_dir()
OUT_CSV = PROJECT_ROOT / "comparison_results" / "sleeve_stop_sensitivity_grid.csv"

TIME_EXIT_DAYS = 30  # matches run_entry_screen.py's live TIME_EXIT_DAYS
STOP_PCT_GRID = [0.01, 0.015, 0.02, 0.03, 0.04]  # 0.02 is the live HARD_STOP_PCT
MIN_N_OBS = 10


def simulate_stop(
    prices: pd.Series,
    entry_date: pd.Timestamp,
    stop_pct: float,
    max_calendar_days: int = TIME_EXIT_DAYS,
) -> float | None:
    """Walk forward day-by-day from entry_date; return the stop-adjusted
    trade return, or None if there isn't enough data to evaluate it."""
    p0_idx = prices.index.searchsorted(entry_date)
    if p0_idx >= len(prices) or abs((prices.index[p0_idx] - entry_date).days) > 5:
        return None
    p0 = prices.iloc[p0_idx]
    if p0 <= 0:
        return None
    stop_price = p0 * (1 - stop_pct)

    end_date = entry_date + pd.Timedelta(days=max_calendar_days)
    window = prices.iloc[p0_idx:]
    window = window[window.index <= end_date]
    if window.empty:
        return None

    breach = window[window <= stop_price]
    if not breach.empty:
        return -stop_pct  # exits at the stop, the day it's first breached

    # Not stopped out -- use the actual close nearest the time exit.
    exit_idx = prices.index.searchsorted(end_date)
    if exit_idx >= len(prices):
        exit_idx = len(prices) - 1
    if abs((prices.index[exit_idx] - end_date).days) > 5:
        return None
    p1 = prices.iloc[exit_idx]
    return (p1 - p0) / p0


def stop_sensitivity(
    entries: list[dict], candidates: dict[str, tuple[str, pd.Series]]
) -> pd.DataFrame:
    rows = []
    for pct in STOP_PCT_GRID:
        rets: list[float] = []
        stopped = 0
        for e in entries:
            _cat, prices = candidates[e["ticker"]]
            r = simulate_stop(prices, e["date"], pct)
            if r is None:
                continue
            rets.append(r)
            if r == -pct:
                stopped += 1
        n = len(rets)
        if n < MIN_N_OBS:
            rows.append({
                "stop_pct": pct, "n": n, "median_return": float("nan"),
                "win_rate": float("nan"), "stopped_out_frac": float("nan"),
            })
            continue
        s = pd.Series(rets)
        rows.append({
            "stop_pct": pct, "n": n,
            "median_return": round(float(s.median()), 4),
            "win_rate": round(float((s > 0).mean()), 4),
            "stopped_out_frac": round(stopped / n, 4),
        })
    return pd.DataFrame(rows)


def main() -> None:
    print("Building regime labels...")
    labeled_df, _ = regime_module.build(DATA_DIR)

    print("Loading full candidate universe...")
    candidates = load_candidates(DATA_DIR)
    print(f"Candidates: {len(candidates)}")

    print("Detecting regime transitions...")
    transitions = detect_transitions(labeled_df)
    print(f"Transitions: {len(transitions)}")

    print("Walk-forward ranking at each transition...")
    selections = rank_at_transitions(transitions, labeled_df, candidates)

    print("Loading benchmark (SPY)...")
    bm_path = reader.ticker_path(DATA_DIR, "equities", BENCHMARK)
    bm_prices = reader.load(bm_path)["close"].dropna().sort_index()

    print("Scanning full history for gate-clearing (ticker, date) events...")
    raw_events = find_gated_entries(selections, candidates, bm_prices)
    print(f"Raw gate-clearing events: {len(raw_events)}")

    entries = decluster(raw_events)
    print(f"Declustered entry population: {len(entries)}")

    print("Simulating compound stop-loss exits across the HARD_STOP_PCT grid...")
    out = stop_sensitivity(entries, candidates)

    OUT_CSV.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n")
    print(out.to_string(index=False))
    print(
        "\nReading this: stopped_out_frac is the key new diagnostic vs. the "
        "duration study -- how often each threshold actually bites. A tight "
        "stop with a high stopped_out_frac and a lower median_return than "
        "looser thresholds is cutting winners short on normal noise, not "
        "protecting against real drawdowns. HARD_STOP_PCT=0.02 (the live "
        "value) is in this grid for direct comparison, not computed "
        "separately. Still a population-level statistic, not a full "
        "compound-exit simulation racing MA50 breach against the stop and "
        "time exit together -- see MEMORY.md research backlog.\n\n"
        "HONEST FLAG, NOT RECONCILED (2026-07-08): every tested threshold "
        "(1-4%) shows a NEGATIVE median return and >47% stopped_out_frac, "
        "which is in tension with run_sleeve_entry_reconstruction.py's "
        "(PR #45) no-stop duration study finding POSITIVE annualized "
        "returns on this same population. Plausible explanation: a fixed "
        "stop permanently locks in a loss for any entry that dips past it, "
        "even ones that would have recovered by the time exit -- i.e. the "
        "real question this raises may be 'should any fixed stop exist at "
        "all', not just 'what percentage'. NOT verified via a direct side-"
        "by-side no-stop-vs-stop comparison on the identical population --"
        " do that before treating this as decision-grade either way."
    )


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    main()
