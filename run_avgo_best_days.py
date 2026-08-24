"""
run_avgo_best_days.py

How concentrated is AVGO's return? Is it a handful of days doing all the
work, or is it broad?

This is not idle trivia -- it is the sharpest available test of whether ANY
out-of-market rule (the retired 200d guard, a trend overlay, discretionary
de-risking) is safe on AVGO. If almost all the return arrives on a few
dozen days, then being flat at the wrong moment is catastrophic in a way no
Calmar number communicates.

Five things measured, on the real 2009-2026 daily series:

  1. CAGR after removing the best N days (N = 1,5,10,20,30,50).
  2. CAGR after removing the WORST N days -- the honest mirror. Quoting
     only the "missed best days" half is a standard piece of buy-and-hold
     advocacy; the symmetric number has to be shown alongside it.
  3. Share of total compounded growth attributable to the top N days.
  4. CLUSTERING: how close are the best days to the worst days? Best days
     concentrate in high-volatility regimes, which are exactly the periods
     a defensive rule puts you on the sidelines for. If they interleave,
     you cannot harvest one and dodge the other.
  5. THE DECISIVE ONE for this project: what fraction of the best days
     occurred while AVGO was BELOW its 200d SMA -- i.e. on days the retired
     guard would have had the position in Gold/LLY instead of AVGO.

AVGO is an equity: 252 bars/yr, NOT the 365 used for BTC in this file.

Printed only. Temporary diagnostic -- delete after logging.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from asset_universe import config

DATA_DIR = config.raw_data_dir()
BARS_PER_YEAR = 252.0
REMOVE_N = [1, 5, 10, 20, 30, 50]


def load(category: str, stem: str) -> pd.Series:
    df = pd.read_parquet(DATA_DIR / category / f"{stem}.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index().dropna()


def cagr_from_returns(rets: pd.Series, years: float) -> float:
    total = float((1 + rets).prod())
    return total ** (1 / years) - 1 if years > 0 and total > 0 else -1.0


def main() -> None:
    px = load("equities", "AVGO")
    ret = px.pct_change().dropna()
    years = (ret.index[-1] - ret.index[0]).days / 365.25
    n = len(ret)

    total_mult = float((1 + ret).prod())
    base_cagr = cagr_from_returns(ret, years)

    print(f"AVGO: {ret.index[0].date()} -> {ret.index[-1].date()}")
    print(f"      {n} trading days, {years:.1f} years")
    print(f"      Total growth {total_mult:.1f}x  |  CAGR {base_cagr:+.1%}\n")

    order_best = ret.sort_values(ascending=False)
    order_worst = ret.sort_values(ascending=True)

    # -- 1 & 2: remove best / remove worst --------------------------------
    print("=" * 94)
    print("REMOVING THE BEST DAYS vs REMOVING THE WORST DAYS")
    print("=" * 94)
    print(f"  {'Days':>5} {'% of all days':>14}   {'Miss BEST: CAGR':>16} {'growth':>10}   "
          f"{'Miss WORST: CAGR':>17} {'growth':>10}")
    print(f"  {'-'*84}")
    print(f"  {0:>5} {0.0:>13.2f}%   {base_cagr:>+16.1%} {total_mult:>9.1f}x   "
          f"{base_cagr:>+17.1%} {total_mult:>9.1f}x")
    for k in REMOVE_N:
        drop_b = ret.drop(order_best.index[:k])
        drop_w = ret.drop(order_worst.index[:k])
        cb, cw = cagr_from_returns(drop_b, years), cagr_from_returns(drop_w, years)
        mb, mw = float((1 + drop_b).prod()), float((1 + drop_w).prod())
        print(f"  {k:>5} {100*k/n:>13.2f}%   {cb:>+16.1%} {mb:>9.1f}x   "
              f"{cw:>+17.1%} {mw:>9.1f}x")
    print()

    # -- 3: share of growth from top N ------------------------------------
    print("=" * 94)
    print("SHARE OF TOTAL COMPOUNDED GROWTH FROM THE TOP N DAYS")
    print("=" * 94)
    log_tot = float(np.log1p(ret).sum())
    for k in REMOVE_N:
        share = float(np.log1p(order_best.iloc[:k]).sum()) / log_tot
        print(f"  Top {k:>3} days ({100*k/n:>5.2f}% of all days): "
              f"{share:>6.1%} of total growth")
    print()

    # -- 4: clustering of best and worst ----------------------------------
    print("=" * 94)
    print("ARE THE BEST DAYS NEAR THE WORST DAYS?")
    print("=" * 94)
    pos = {d: i for i, d in enumerate(ret.index)}
    for k in [10, 20, 50]:
        b_idx = [pos[d] for d in order_best.index[:k]]
        w_idx = [pos[d] for d in order_worst.index[:k]]
        near = sum(1 for i in b_idx if any(abs(i - j) <= 5 for j in w_idx))
        print(f"  Of the top {k:>2} BEST days, {near}/{k} ({near/k:>4.0%}) fall within "
              f"5 trading days of a top-{k} WORST day.")
    yrs_best = pd.Series([d.year for d in order_best.index[:20]]).value_counts().sort_index()
    print(f"\n  Calendar years holding the 20 best days: "
          f"{', '.join(f'{y} x{c}' for y, c in yrs_best.items())}")
    print()

    # -- 5: were the best days inside guard-active periods? ---------------
    print("=" * 94)
    print("WOULD A 200d-SMA RULE HAVE BEEN OUT ON THE BEST DAYS?")
    print("=" * 94)
    sma200 = px.rolling(200).mean()
    below = (px < sma200).reindex(ret.index).fillna(False)
    pct_days_below = float(below.mean())
    print(f"  AVGO trades below its 200d SMA on {pct_days_below:.1%} of all days.")
    for k in [10, 20, 50]:
        b_below = int(below.reindex(order_best.index[:k]).fillna(False).sum())
        w_below = int(below.reindex(order_worst.index[:k]).fillna(False).sum())
        print(f"  Top {k:>2} BEST days below the 200d SMA: {b_below}/{k} ({b_below/k:>4.0%})"
              f"   |  top {k:>2} WORST: {w_below}/{k} ({w_below/k:>4.0%})")
    print("\n  A rule that sits out below the 200d SMA forfeits the BEST days in that")
    print("  bucket and dodges the WORST ones. The two percentages above are the")
    print("  trade it actually makes -- not one or the other.")


if __name__ == "__main__":
    main()
