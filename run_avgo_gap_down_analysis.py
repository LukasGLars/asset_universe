"""
run_avgo_gap_down_analysis.py

Standalone, single-ticker research: how has a given ticker behaved after
an overnight gap-down (open meaningfully below the prior close), and does
that differ from a random day? Originally built for AVGO (kept as the
default), then generalized (2026-07-29) to run against any ticker in the
parquet store -- same "shopping at a discount" question applied to Gold
(GC_F) or LLY, not just AVGO. Separate from the opportunistic-sleeve
backlog.

Method:
  1. A "gap-down" is a day whose open is >= threshold% below the PRIOR
     day's close (thresholds tested: 2%, 3%, 5%).
  2. Forward returns are measured from that day's CLOSE (a realistic entry
     point -- you can't retroactively buy at a printed open), at 5/21/63/
     252 trading days out.
  3. Compared against an UNCONDITIONAL baseline (every trading day, same
     horizons) so "gains after a gap-down" can be read against "gains
     anyway, gap or not" -- the gap-down premium (or discount) is the
     delta between the two, not the raw number alone.
  4. An optional era split (--era-split YYYY-MM-DD) additionally breaks
     the history in two, for a ticker with a known narrative/volatility-
     regime shift (e.g. AVGO's own AI-datacenter re-rating around
     2023-01-01) -- pooling 15+ years risks averaging two different
     regimes together. Omit it to report full history only, the right
     default for a ticker without an obvious single-date break (Gold,
     LLY).

Analysis only -- informational, not a signal wired into any live gate.

Usage:
    python run_avgo_gap_down_analysis.py                              # AVGO, full history
    python run_avgo_gap_down_analysis.py --era-split 2023-01-01        # AVGO, pre/post split
    python run_avgo_gap_down_analysis.py --ticker GC_F --category commodities
    python run_avgo_gap_down_analysis.py --ticker LLY
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
    import argparse

    parser = argparse.ArgumentParser(description="Gap-down forward-return analysis for any ticker.")
    parser.add_argument("--ticker", default=TICKER, help=f"Ticker symbol (default: {TICKER})")
    parser.add_argument("--category", default=CATEGORY,
                         help=f"Category directory: equities/commodities/etc. (default: {CATEGORY})")
    parser.add_argument("--era-split", default=None,
                         help="Optional YYYY-MM-DD to additionally split into two eras "
                              "(e.g. a known narrative/volatility-regime shift for this ticker). "
                              "Omit to report full history only.")
    args = parser.parse_args()

    ticker, category = args.ticker, args.category

    print("=" * 72)
    print(f"{ticker}: forward returns after an overnight gap-down")
    print("=" * 72)

    df = load_ohlc(DATA_DIR, category, ticker).reset_index()
    print(f"\nHistory: {df['date'].min().date()} to {df['date'].max().date()} ({len(df)} sessions)")

    frames = [run_era(df, "full history")]
    if args.era_split:
        split = pd.Timestamp(args.era_split)
        pre  = df[df["date"] < split].reset_index(drop=True)
        post = df[df["date"] >= split].reset_index(drop=True)
        print(f"Era split at {split.date()}: pre={len(pre)} sessions, post={len(post)} sessions")
        frames.append(run_era(pre, f"pre-{split.date()}"))
        frames.append(run_era(post, f"post-{split.date()}"))

    out = pd.concat(frames, ignore_index=True)
    out_csv = OUT_CSV.parent / f"{ticker.replace('.', '_')}_gap_down_analysis.csv"
    out_csv.parent.mkdir(exist_ok=True)
    out.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_csv}\n")
    print(out.to_string(index=False))
    print(
        "\nReading this: compare each 'gap-down >= X%' row to its era's 'baseline (all "
        "days)' row at the SAME horizon -- the gap-down premium/discount is the "
        "difference, not the raw median. n < 5 blanked (too few real events to trust). "
        "An era split (if requested) is an approximation of a known narrative/volatility "
        "shift for this specific ticker, not a precisely-dated regime change. "
        "Informational only -- not wired into any live gate."
    )


if __name__ == "__main__":
    main()
