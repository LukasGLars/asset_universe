"""
run_opp_sleeve_capitulation_stop_sensitivity.py

Direct follow-on to the sector-capitulation reconstruction (MEMORY.md,
2026-07-29): basket_crash cleanly beat solo_crash on raw return/win-rate at
every duration, but the reconstruction's early-stop-rate column (94-98% in
BOTH buckets) was flagged as meaningless -- these entries are, by
construction, already deep in a 5d/-10% crash, so the live binding_stop()
(a buffered MA50 FLOOR) is close to guaranteed to trip immediately: price
starts below MA50, not above it like the existing extension gate's entries.

This asks the actual open question from that entry: does ANY stop protect
capital here without destroying the edge, or does it behave like the
sleeve's own HARD_STOP_PCT history (run_opp_sleeve_stop_sensitivity.py --
every threshold tested there got stopped out on over half of trades with
NEGATIVE median return, directly contradicting the no-stop duration study
on the same population)? That is a real, already-observed failure mode in
this exact codebase, not a hypothetical.

Design, isolating the one thing that needs to change for a below-MA50
entry: binding_stop()'s trailing-peak component (TRAILING_TRIGGER_PCT /
TRAILING_PCT) only ever references entry price and the peak close since
entry -- it does NOT depend on MA50, so it is already appropriate here
unchanged. Only the MA50 floor needs replacing, with a floor relative to
the ENTRY price instead (entry_price * (1 - hard_stop_pct)). Same two-
phase methodology as run_opp_sleeve_stop_sensitivity.py: Phase 1 grids the
entry-floor percentage alone (no trailing), picks the best by a Calmar-
like ratio; Phase 2 adds the live trailing grid on top of that floor.
`hard_stop_pct=None` (no floor at all, matching the no-stop duration
study's raw-hold numbers) competes in Phase 1 on equal footing, not
excluded as a bracketing case only -- same fix already applied to the
original stop-sensitivity script after it wrongly excluded N=0.

Population: the REAL basket_crash / solo_crash entries from
run_sleeve_sector_capitulation_reconstruction.py (gate-1-gated, not a
blind universe sample) -- reruns that reconstruction's pipeline to
regenerate them (~15-20 min, dominated by rank_at_transitions(), same
long pole logged in MEMORY.md).

Reports median/win-rate return, stopped_pct, false_stop_pct_of_stopped
(stopped, but the unstopped/natural return by the same horizon was
actually higher), protection_pct_of_stopped (stopped, and the natural
return was lower -- the stop earned its keep), and the same Calmar-like
ratio (median return / |median drawdown|) used throughout this backlog --
addresses the tail-risk gap the raw reconstruction didn't: a good median
return can still hide a catastrophic worst case.

Report-only. No gate, display flag, or live screen change made or implied
by running this script.

Usage:
    python run_opp_sleeve_capitulation_stop_sensitivity.py
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", write_through=True)
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module

import run_sleeve_entry_reconstruction as recon
import run_sleeve_sector_capitulation_reconstruction as cap

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "opp_sleeve_capitulation_stop_sensitivity.csv"

DURATION_DAYS = 21   # matches HOLD_DAYS/STOP_HORIZON_DAYS convention used elsewhere in this backlog

HARD_STOP_GRID = [0.05, 0.08, 0.10, 0.15, 0.20, None]  # None = no floor at all (trailing-only / raw hold)
TRAILING_GRID  = [(0.05, 0.03), (0.05, 0.05), (0.08, 0.05), (0.08, 0.08)]  # (trigger, trailing_pct)


def simulate_trade(
    prices: pd.Series,
    entry_date: pd.Timestamp,
    duration_days: int,
    hard_stop_pct: float | None,
    trailing_trigger_pct: float | None,
    trailing_pct: float | None,
) -> dict | None:
    """Same walk-forward mechanics as run_opp_sleeve_ma50_stop_sensitivity.
    simulate_trade(), with the MA50 floor replaced by an entry-price floor
    (appropriate for an entry that starts BELOW its own MA50 by
    construction) and the live trailing-peak stop left unchanged (it
    already only references entry price and peak-since-entry)."""
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

        levels = []
        if hard_stop_pct is not None:
            levels.append(entry_price * (1 - hard_stop_pct))
        if trailing_trigger_pct is not None and (peak / entry_price - 1) >= trailing_trigger_pct:
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

    natural_return = recon.forward_return(prices, entry_date, duration_days)
    return {
        "return": (exit_price - entry_price) / entry_price,
        "stopped": stopped,
        "natural_return": natural_return,
    }


def run_config(
    entries: list[dict],
    candidates: dict[str, tuple[str, pd.Series]],
    hard_stop_pct: float | None,
    trailing_trigger_pct: float | None,
    trailing_pct: float | None,
) -> dict:
    rets, false_stops, protections, stopped_flags, n = [], 0, 0, 0, 0
    for e in entries:
        _cat, prices = candidates[e["ticker"]]
        trade = simulate_trade(prices, e["date"], DURATION_DAYS, hard_stop_pct, trailing_trigger_pct, trailing_pct)
        if trade is None:
            continue
        n += 1
        rets.append(trade["return"])
        if trade["stopped"]:
            stopped_flags += 1
            nat = trade["natural_return"]
            if nat is not None:
                if nat > trade["return"]:
                    false_stops += 1
                elif nat < trade["return"]:
                    protections += 1

    if n == 0:
        return {"n_trades": 0, "median_return": float("nan"), "win_rate": float("nan"),
                "stopped_pct": float("nan"), "false_stop_pct_of_stopped": float("nan"),
                "protection_pct_of_stopped": float("nan"), "calmar_like": float("nan")}

    arr = np.array(rets)
    median_ret = float(np.median(arr))
    downside = arr[arr < 0]
    med_dd = float(np.median(downside)) if len(downside) else 0.0
    calmar = (median_ret / abs(med_dd)) if med_dd != 0 else float("nan")
    return {
        "n_trades": n,
        "median_return": round(median_ret, 4),
        "win_rate": round(float((arr > 0).mean()), 3),
        "stopped_pct": round(stopped_flags / n, 3),
        "false_stop_pct_of_stopped": round(false_stops / stopped_flags, 3) if stopped_flags else 0.0,
        "protection_pct_of_stopped": round(protections / stopped_flags, 3) if stopped_flags else 0.0,
        "calmar_like": round(calmar, 3) if not np.isnan(calmar) else "",
    }


def run_phase(label: str, entries: list[dict], candidates: dict[str, tuple[str, pd.Series]]) -> list[dict]:
    rows = []
    print(f"\n[{label}] Phase 1: entry-floor stop pct (no trailing)", flush=True)
    for hard_stop_pct in HARD_STOP_GRID:
        row = run_config(entries, candidates, hard_stop_pct, None, None)
        row["hard_stop_pct"] = hard_stop_pct if hard_stop_pct is not None else ""
        row["trailing_trigger"] = ""
        row["trailing_pct"] = ""
        rows.append(row)

    best_row = max(rows, key=lambda r: (r["calmar_like"] if r["calmar_like"] != "" else -999))
    best_floor = best_row["hard_stop_pct"] if best_row["hard_stop_pct"] != "" else None
    print(f"[{label}] Phase 1 best floor by Calmar-like: {best_floor}", flush=True)

    print(f"[{label}] Phase 2: trailing-peak stop on top of floor={best_floor}", flush=True)
    for trigger, pct in TRAILING_GRID:
        row = run_config(entries, candidates, best_floor, trigger, pct)
        row["hard_stop_pct"] = best_floor if best_floor is not None else ""
        row["trailing_trigger"] = trigger
        row["trailing_pct"] = pct
        rows.append(row)

    for r in rows:
        r["population"] = label
    return rows


def main() -> None:
    print("=" * 72, flush=True)
    print("Opp sleeve capitulation stop-sensitivity (solo_crash vs basket_crash)", flush=True)
    print("Report-only -- no gate/display change implied by this run.", flush=True)
    print("=" * 72, flush=True)

    print("\nBuilding regime labels...", flush=True)
    labeled_df, _ = regime_module.build(DATA_DIR)

    print("Loading full candidate universe (same as extension study)...", flush=True)
    candidates = recon.load_candidates(DATA_DIR)
    print(f"Candidates: {len(candidates)}", flush=True)

    print("Detecting regime transitions + walk-forward gate-1 ranking...", flush=True)
    transitions = recon.detect_transitions(labeled_df)
    print(f"Transitions: {len(transitions)}", flush=True)
    selections = recon.rank_at_transitions(transitions, labeled_df, candidates, verbose=True)
    print("Gate-1 ranking done.", flush=True)

    print(f"Scanning for {cap.CRASH_ROC_WINDOW}d/{cap.CRASH_ROC_THRESHOLD:.0%} crashes, "
          f"tagging same-sector peer-crash counts...", flush=True)
    raw_events = cap.find_capitulation_entries(selections, candidates)
    print(f"Raw crash events: {len(raw_events)}", flush=True)

    entries = recon.decluster(raw_events, min_gap_days=cap.DECLUSTER_MIN_GAP)
    print(f"Declustered: {len(entries)}", flush=True)

    rows = []
    for label in ("solo_crash", "basket_crash"):
        bucket_entries = [e for e in entries if e["bucket"] == label]
        print(f"\n{label}: {len(bucket_entries)} entries", flush=True)
        rows.extend(run_phase(label, bucket_entries, candidates))

    out = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n", flush=True)
    print(out.to_string(index=False), flush=True)
    print(
        "\nReading this: calmar_like = median_return / |median drawdown among losers| -- "
        "the tail-risk-aware ranking metric. false_stop_pct_of_stopped near 1.0 means "
        "the stop is mostly cutting off trades that would have recovered (destroying the "
        "edge); protection_pct_of_stopped near 1.0 means it's mostly catching trades that "
        "would have gotten worse (earning its keep). Compare median_return here to the raw "
        "reconstruction's un-stopped numbers in MEMORY.md -- if every config's median_return "
        "is materially worse than the raw-hold number, that repeats the sleeve's own "
        "HARD_STOP_PCT history: a stop that looks protective but actually destroys the edge."
    )


if __name__ == "__main__":
    main()
