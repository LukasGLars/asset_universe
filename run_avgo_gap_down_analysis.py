"""
run_avgo_gap_down_analysis.py

Standalone, single-ticker research: how has AVGO behaved after an
overnight gap-down (open meaningfully below the prior close), and does
that differ from a random day? Prompted by the operator's interest in
AVGO's gap-down behavior, separate from the opportunistic-sleeve backlog.

Method:
  1. A "gap-down" is a day whose open is >= threshold% below the PRIOR
     day's close (thresholds tested: 2%, 3%, 5%).
  2. Forward returns are measured from that day's CLOSE (a realistic entry
     point -- you can't retroactively buy at a printed open), at 5/21/63/
     252 trading days out.
  3. Compared against an UNCONDITIONAL baseline (every trading day, same
     horizons) so "AVGO gains after a gap-down" can be read against
     "AVGO gains anyway, gap or not" -- the gap-down premium (or
     discount) is the delta between the two, not the raw number alone.
  4. Split into two eras (pre/post 2023-01-01) since AVGO's own volatility
     regime shifted materially around the AI-datacenter narrative --
     pooling 15+ years risks averaging two different stocks' behavior
     together. The cutoff is a round, defensible approximation, not a
     precisely-dated regime-change point.

Analysis only -- informational, not a signal wired into any live gate.

Usage:
    python run_avgo_gap_down_analysis.py
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

DATA_DIR = config.raw_data_dir()
TICKER   = "AVGO"
CATEGORY = "equities"
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "avgo_gap_down_analysis.csv"

GAP_THRESHOLDS = [0.02, 0.03, 0.05]
HORIZONS_DAYS  = [5, 21, 63, 252]
ERA_SPLIT      = pd.Timestamp("2023-01-01")
MIN_N_OBS      = 5


def load_ohlc(data_dir: Path, category: str, ticker: str) -> pd.DataFrame:
    path = reader.ticker_path(data_dir, category, ticker)
    df = reader.load(path)
    return df[["open", "close"]].dropna()


def gap_pct(df: pd.DataFrame) -> pd.Series:
    """(open[t] - close[t-1]) / close[t-1] -- negative means a gap DOWN."""
    prior_close = df["close"].shift(1)
    return (df["open"] - prior_close) / prior_close


def forward_return(closes: pd.Series, idx: int, horizon_days: int) -> float | None:
    target = idx + horizon_days
    if target >= len(closes):
        return None
    p0, p1 = closes.iloc[idx], closes.iloc[target]
    return (p1 - p0) / p0 if p0 > 0 else None


def event_stats(
    df: pd.DataFrame, event_idx: list[int], label: str,
) -> list[dict]:
    closes = df["close"]
    rows = []
    for h in HORIZONS_DAYS:
        rets = [r for i in event_idx if (r := forward_return(closes, i, h)) is not None]
        n = len(rets)
        if n < MIN_N_OBS:
            rows.append({"group": label, "horizon_days": h, "n": n,
                         "median_return": None, "win_rate": None})
            continue
        s = pd.Series(rets)
        rows.append({
            "group": label, "horizon_days": h, "n": n,
            "median_return": round(float(s.median()), 4),
            "win_rate": round(float((s > 0).mean()), 3),
        })
    return rows


def run_era(df: pd.DataFrame, era_label: str) -> pd.DataFrame:
    gaps = gap_pct(df)
    rows: list[dict] = []

    baseline_idx = list(range(1, len(df)))  # every day with a valid prior close
    rows += event_stats(df, baseline_idx, f"{era_label}: baseline (all days)")

    for thresh in GAP_THRESHOLDS:
        event_idx = [i for i in range(1, len(df)) if gaps.iloc[i] <= -thresh]
        rows += event_stats(df, event_idx, f"{era_label}: gap-down >= {thresh:.0%}")

    return pd.DataFrame(rows)


def main() -> None:
    print("=" * 72)
    print(f"{TICKER}: forward returns after an overnight gap-down")
    print("=" * 72)

    df = load_ohlc(DATA_DIR, CATEGORY, TICKER).reset_index()
    print(f"\nHistory: {df['date'].min().date()} to {df['date'].max().date()} ({len(df)} sessions)")

    pre  = df[df["date"] < ERA_SPLIT].reset_index(drop=True)
    post = df[df["date"] >= ERA_SPLIT].reset_index(drop=True)
    print(f"Era split at {ERA_SPLIT.date()}: pre={len(pre)} sessions, post={len(post)} sessions")

    full_df = run_era(df, "full history")
    pre_df  = run_era(pre, "pre-2023")
    post_df = run_era(post, "post-2023 (AI era)")

    out = pd.concat([full_df, pre_df, post_df], ignore_index=True)
    OUT_CSV.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n")
    print(out.to_string(index=False))
    print(
        "\nReading this: compare each 'gap-down >= X%' row to its era's 'baseline (all "
        "days)' row at the SAME horizon -- the gap-down premium/discount is the "
        "difference, not the raw median. n < 5 blanked (too few real events to trust). "
        "Pre/post-2023 split is an approximation of AVGO's AI-narrative volatility "
        "shift, not a precisely-dated regime change. Informational only -- not wired "
        "into any live gate."
    )


if __name__ == "__main__":
    main()
