"""
run_avgo_gap_guard_conditioned_analysis.py

Direct follow-on to run_avgo_gap_down_analysis.py: that study found AVGO
gap-downs are a consistent buy signal, but never conditioned on WHERE AVGO
was relative to its own 200d Guard at the time -- it can't distinguish a
dip inside a healthy uptrend from a lower high during an actual
breakdown, which is exactly the distinction the guard exists to make.

This splits the same gap-down population by guard state on the gap day,
reconstructed with the SAME point-in-time logic fi_tracker.py's live
guard uses (no new parameters, no lookahead -- both the 200d SMA and the
5-day crash ROC only ever look backward from each date):
  - guard ACTIVE (DEFENSIVE) if close < 200d SMA, OR 5d ROC <= -10%
  - guard INACTIVE (BASE) otherwise

Forward returns (from the gap day's close, same convention as the prior
study) are then compared: gap-downs while the guard was already active vs.
gap-downs while it was still base.

Analysis only -- informational, not wired into any live gate. Small
sample sizes are expected in the guard-active bucket (the guard has fired
rarely in AVGO's history) -- treat that bucket as directional, not
conclusive, if n comes back thin.

Usage:
    python run_avgo_gap_guard_conditioned_analysis.py
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
from asset_universe.store import reader

from run_avgo_gap_down_analysis import forward_return, gap_pct

DATA_DIR = config.raw_data_dir()
TICKER   = "AVGO"
CATEGORY = "equities"
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "avgo_gap_guard_conditioned_analysis.csv"

GAP_THRESHOLDS = [0.02, 0.03, 0.05]
HORIZONS_DAYS  = [21, 63, 252]
MIN_N_OBS      = 5

# Matches fi_tracker.py's live AVGO 200d Guard exactly -- same constants,
# same crash-ROC early-activation layer, no new parameters.
GUARD_MA_WINDOW     = 200
CRASH_ROC_WINDOW    = 5
CRASH_ROC_THRESHOLD = -0.10


def load_ohlc(data_dir: Path, category: str, ticker: str) -> pd.DataFrame:
    path = reader.ticker_path(data_dir, category, ticker)
    return reader.load(path)[["open", "close"]].dropna()


def guard_active_series(closes: pd.Series) -> pd.Series:
    """Point-in-time guard state for every date -- True = DEFENSIVE
    (active), False = BASE. Both signals only look backward from each
    date, so this reconstructs the live guard's own daily read at every
    historical point, not just today's."""
    sma = closes.rolling(GUARD_MA_WINDOW).mean()
    ma_below = closes < sma
    roc = closes / closes.shift(CRASH_ROC_WINDOW) - 1
    crash = roc <= CRASH_ROC_THRESHOLD
    return (ma_below | crash).fillna(False)


def event_stats_by_guard(
    df: pd.DataFrame, guard_active: pd.Series, event_idx: list[int], label: str,
) -> list[dict]:
    closes = df["close"]
    rows = []
    for h in HORIZONS_DAYS:
        for guard_label, want_active in [("guard ACTIVE", True), ("guard base", False)]:
            rets = [
                r for i in event_idx
                if bool(guard_active.iloc[i]) == want_active
                and (r := forward_return(closes, i, h)) is not None
            ]
            n = len(rets)
            if n < MIN_N_OBS:
                rows.append({"group": f"{label} | {guard_label}", "horizon_days": h,
                             "n": n, "median_return": None, "win_rate": None})
                continue
            s = pd.Series(rets)
            rows.append({
                "group": f"{label} | {guard_label}", "horizon_days": h, "n": n,
                "median_return": round(float(s.median()), 4),
                "win_rate": round(float((s > 0).mean()), 3),
            })
    return rows


def main() -> None:
    print("=" * 72)
    print(f"{TICKER}: gap-down forward returns, split by 200d Guard state on the gap day")
    print("=" * 72)

    df = load_ohlc(DATA_DIR, CATEGORY, TICKER).reset_index()
    print(f"\nHistory: {df['date'].min().date()} to {df['date'].max().date()} ({len(df)} sessions)")

    guard_active = guard_active_series(df["close"])
    pct_active = float(guard_active.mean())
    print(f"Guard active (DEFENSIVE) on {pct_active:.1%} of all sessions")

    gaps = gap_pct(df)
    rows: list[dict] = []
    for thresh in GAP_THRESHOLDS:
        event_idx = [i for i in range(1, len(df)) if gaps.iloc[i] <= -thresh]
        rows += event_stats_by_guard(df, guard_active, event_idx, f"gap-down >= {thresh:.0%}")

    out = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n")
    print(out.to_string(index=False))
    print(
        "\nReading this: compare 'guard ACTIVE' vs 'guard base' rows at the SAME "
        "gap threshold and horizon. If ACTIVE consistently underperforms base, "
        "that validates conditioning gap-down buys on guard state (buy the dip "
        "only while the guard hasn't fired). If they're similar, the guard isn't "
        "adding information the gap-down signal doesn't already have. n < 5 "
        "blanked -- the guard fires rarely, so the ACTIVE bucket is expected to "
        "be thin; treat it as directional only. Informational, not wired into "
        "any live gate."
    )


if __name__ == "__main__":
    main()
