"""
run_opp_sleeve_stop_sensitivity.py

Prompted by the 2026-07-23 HWM trade (see MEMORY.md "HWM position closed"):
the sleeve's HARD_STOP_PCT (2%) produced one confirmed false trigger
(2026-07-10) and was never actually needed to protect the trade -- it closed
via a deliberate profitable exit, not a stop. The open design question:
binding_stop() already hands off from the hard stop to MA50 once MA50
organically converges above it (max(hard_stop, ma50)), but MA50 is a 50d
average partly anchored to PRE-entry prices, so that handoff can take far
longer than a reasonable initial-risk-bounding window -- exactly what
happened to HWM (still hard-stop-bound 16 days post-entry).

This tests two independent refinements against real historical data, not
guessed parameters:

  1. A fixed-day cutoff N: the hard stop is active for at most N trading
     days post-entry: after that, MA50 alone binds regardless of whether it
     has organically converged. Grid: N in {5, 10, 15, 20, 30} where N=30
     reproduces current behaviour (never turns off within the 30-day
     sleeve hold) and a "MA50-only" baseline (N=0, hard stop never active)
     brackets the other end.
  2. A trailing-peak stop, independent of (1): once unrealized gain since
     entry exceeds a trigger threshold, track the peak close since entry
     and add a trailing stop below it. Grid: trigger in {0.05, 0.08} x
     trailing_pct in {0.05, 0.08}.

Methodology: NOT limited to HWM's own ~10yr history (one ticker, one real
trade -- too thin to validate anything). Samples entry-like points across
the whole US equities universe (config/universes/us_equities.txt, the same
list the opportunistic screen draws candidates from), every 20 trading days
per ticker, simulated forward exactly like the real sleeve rule: 30-calendar
-day hold, exit at whichever stop binds first or the time exit.

For each config, reports: median/win-rate return, false-stop rate (stopped
out, but price would have closed higher than the stop price by day 30 if
held), protection rate (stopped out, and price closed lower by day 30 --
the stop earned its keep), and a Calmar-style ratio (median return / |median
drawdown from entry|) to compare configs on a risk-adjusted basis, same
spirit as run_parameter_sensitivity.py's validation discipline.

Usage:
    python run_opp_sleeve_stop_sensitivity.py
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    # Only when run directly -- doing this at import time breaks pytest's
    # stdout/stderr capture for anything that imports this module (same
    # gotcha as run_combined_system.py / run_base_optimizer_with_guard.py).
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config

DATA_DIR    = config.raw_data_dir()
UNIVERSE_TXT = PROJECT_ROOT / "config" / "universes" / "us_equities.txt"
OUT_CSV     = PROJECT_ROOT / "comparison_results" / "opp_sleeve_stop_sensitivity.csv"

HARD_STOP_PCT   = 0.02   # matches run_entry_screen.py's live constant
HOLD_DAYS       = 30     # matches TIME_EXIT_DAYS
SAMPLE_STRIDE   = 20     # trading days between sampled entry points per ticker
MIN_HISTORY     = 300    # trading days of history required before an entry sample is usable

N_GRID          = [0, 5, 10, 15, 20, 30]  # 0 = MA50-only, 30 = current (never turns off)
TRAILING_GRID   = [(0.05, 0.05), (0.05, 0.08), (0.08, 0.05), (0.08, 0.08)]  # (trigger, trailing_pct)


def load_universe_tickers() -> list[str]:
    lines = UNIVERSE_TXT.read_text().splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]


def load_prices(ticker: str) -> pd.Series | None:
    path = DATA_DIR / "equities" / f"{ticker}.parquet"
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        s = df.set_index("date")["close"].sort_index().dropna()
        return s if len(s) >= MIN_HISTORY else None
    except Exception:
        return None


def rs_20d_ok(closes: np.ndarray, dates: pd.DatetimeIndex, entry_idx: int, spy_ret20: pd.Series) -> bool | None:
    """Positive 20-trading-day relative strength vs SPY as of entry -- a
    cheap, price-only proxy for gate 2/3 of the real entry screen (the RS
    check inside compute_tripwires/screen_tactical). NOT the full gate
    (extension vs the regime's empirical p67 threshold isn't reconstructed
    here -- that needs the regime-ranking apparatus, out of scope for this
    proxy). Returns None if there isn't enough history on either side to
    compute a comparison."""
    if entry_idx < 20:
        return None
    t_ret = closes[entry_idx] / closes[entry_idx - 20] - 1
    dt = dates[entry_idx]
    pos = spy_ret20.index.searchsorted(dt)
    if pos >= len(spy_ret20) or abs((spy_ret20.index[pos] - dt).days) > 5:
        return None
    b_ret = spy_ret20.iloc[pos]
    if pd.isna(b_ret):
        return None
    return bool((t_ret - b_ret) >= 0)


def simulate_trade(
    closes: np.ndarray,
    ma50: np.ndarray,
    entry_idx: int,
    n_cutoff: int,
    trailing_trigger: float | None,
    trailing_pct: float | None,
) -> dict:
    """One simulated trade from entry_idx, HOLD_DAYS bars forward (bar-count
    stand-in for calendar days -- close enough for a universe-wide
    sensitivity study; the live system uses real calendar dates).
    n_cutoff: hard stop active for bars 1..n_cutoff post-entry, then off
    (0 = never active, HOLD_DAYS = always active, matching current code).
    Returns exit day offset, exit reason, and the realized return."""
    entry_price = closes[entry_idx]
    hard_stop_level = entry_price * (1 - HARD_STOP_PCT)
    peak = entry_price
    last_i = min(entry_idx + HOLD_DAYS, len(closes) - 1)

    for offset in range(1, last_i - entry_idx + 1):
        i = entry_idx + offset
        price = closes[i]
        peak = max(peak, price)

        levels = []
        if offset <= n_cutoff:
            levels.append(hard_stop_level)
        if not np.isnan(ma50[i]):
            levels.append(ma50[i])
        if trailing_trigger is not None and (peak / entry_price - 1) >= trailing_trigger:
            levels.append(peak * (1 - trailing_pct))

        binding = max(levels) if levels else -np.inf
        if price <= binding:
            return {"exit_offset": offset, "exit_price": price, "stopped": True}

    exit_price = closes[last_i]
    return {"exit_offset": last_i - entry_idx, "exit_price": exit_price, "stopped": False}


def natural_exit_price(closes: np.ndarray, entry_idx: int) -> float:
    last_i = min(entry_idx + HOLD_DAYS, len(closes) - 1)
    return closes[last_i]


def run_config(samples: list[tuple[np.ndarray, np.ndarray, int]], n_cutoff: int,
                trailing_trigger: float | None, trailing_pct: float | None) -> dict:
    rets, false_stops, protections, stopped_flags = [], 0, 0, 0
    for closes, ma50, entry_idx in samples:
        trade = simulate_trade(closes, ma50, entry_idx, n_cutoff, trailing_trigger, trailing_pct)
        entry_price = closes[entry_idx]
        ret = (trade["exit_price"] - entry_price) / entry_price
        rets.append(ret)
        if trade["stopped"]:
            stopped_flags += 1
            nat_price = natural_exit_price(closes, entry_idx)
            if nat_price > trade["exit_price"]:
                false_stops += 1
            elif nat_price < trade["exit_price"]:
                protections += 1

    rets = np.array(rets)
    n = len(rets)
    median_ret = float(np.median(rets))
    win_rate = float((rets > 0).mean())
    downside = rets[rets < 0]
    med_dd = float(np.median(downside)) if len(downside) else 0.0
    calmar = (median_ret / abs(med_dd)) if med_dd != 0 else float("nan")
    return {
        "n_cutoff": n_cutoff,
        "trailing_trigger": trailing_trigger if trailing_trigger is not None else "",
        "trailing_pct": trailing_pct if trailing_pct is not None else "",
        "n_trades": n,
        "median_return": round(median_ret, 4),
        "win_rate": round(win_rate, 3),
        "stopped_pct": round(stopped_flags / n, 3) if n else 0.0,
        "false_stop_pct_of_stopped": round(false_stops / stopped_flags, 3) if stopped_flags else 0.0,
        "protection_pct_of_stopped": round(protections / stopped_flags, 3) if stopped_flags else 0.0,
        "calmar_like": round(calmar, 3) if not np.isnan(calmar) else "",
    }


def run_phase(label: str, samples: list[tuple[np.ndarray, np.ndarray, int]]) -> list[dict]:
    rows = []
    print(f"\n[{label}] Phase 1: hard-stop cutoff N (no trailing stop)")
    for n_cutoff in N_GRID:
        rows.append(run_config(samples, n_cutoff, None, None))

    # N=0 (hard stop dropped entirely) is a legitimate candidate, not just a
    # bracketing baseline to exclude -- an earlier version of this script
    # wrongly excluded it here, which meant Phase 2's trailing-stop grid got
    # tested on top of the best NON-zero cutoff even when N=0 actually won
    # Phase 1. Fixed 2026-07-24: no exclusion, N=0 competes on equal footing.
    best_n = max(
        rows,
        key=lambda r: (r["calmar_like"] if r["calmar_like"] != "" else -999),
    )["n_cutoff"]

    print(f"[{label}] Phase 2: trailing-peak stop on top of N={best_n} (best Phase 1 cutoff)")
    for trigger, pct in TRAILING_GRID:
        rows.append(run_config(samples, best_n, trigger, pct))

    for r in rows:
        r["population"] = label
    print(f"[{label}] best N by Calmar-like ratio: {best_n}")
    return rows


def main() -> None:
    print("=" * 72)
    print("Opportunistic sleeve stop-management sensitivity study")
    print("Prompted by the HWM 2026-07-10 false stop / 2026-07-23 clean exit")
    print("=" * 72)

    tickers = load_universe_tickers()
    print(f"\nUniverse: {len(tickers)} tickers")

    spy = load_prices("SPY")
    if spy is None:
        print("ERROR: SPY price data required for the gated population's RS check")
        return
    spy_ret20 = spy.pct_change(20)

    samples_blind: list[tuple[np.ndarray, np.ndarray, int]] = []
    samples_gated: list[tuple[np.ndarray, np.ndarray, int]] = []
    tickers_used = 0
    for t in tickers:
        s = load_prices(t)
        if s is None:
            continue
        closes = s.to_numpy()
        ma50 = s.rolling(50).mean().to_numpy()
        dates = s.index
        n = len(closes)
        entries_this_ticker = 0
        for entry_idx in range(MIN_HISTORY, n - HOLD_DAYS, SAMPLE_STRIDE):
            if np.isnan(ma50[entry_idx]):
                continue
            samples_blind.append((closes, ma50, entry_idx))
            entries_this_ticker += 1
            above_ma50 = closes[entry_idx] > ma50[entry_idx]
            rs_ok = rs_20d_ok(closes, dates, entry_idx, spy_ret20)
            if above_ma50 and rs_ok:
                samples_gated.append((closes, ma50, entry_idx))
        if entries_this_ticker:
            tickers_used += 1

    print(f"Tickers with usable history: {tickers_used}")
    print(f"Total entry samples (blind, unconditioned): {len(samples_blind)}")
    print(f"Total entry samples (gated: above MA50 + positive 20d RS vs SPY): {len(samples_gated)}")
    print("\nNote: 'gated' reconstructs only 2 of the real screen's 4 entry gates")
    print("(above-MA50, RS-vs-benchmark proxy) from price data alone. The other 2")
    print("(regime-conditional top-N rank, no-earnings-soon) need the full")
    print("regime-ranking apparatus / an earnings calendar and are NOT")
    print("reconstructed here -- this narrows the gap to the real sleeve")
    print("population, it does not close it.")

    rows = run_phase("BLIND", samples_blind) + run_phase("GATED", samples_gated)

    df = pd.DataFrame(rows)
    print(f"\n{'='*72}\nRESULTS\n{'='*72}")
    print(df.to_string(index=False))

    OUT_CSV.parent.mkdir(exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")


if __name__ == "__main__":
    main()
