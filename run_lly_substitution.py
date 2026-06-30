"""
run_lly_substitution.py

Test every quality-filtered candidate in the 20% base slot (Gold25/AVGO55/[X]20).
Ranks by Calmar. LLY included as baseline.

Quality filter (same as run_rotation_quality.py):
  Sharpe >= 0.60, MaxDD >= -65%, history >= 15yr

Output: comparison_results/lly_substitution.csv
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "lly_substitution.csv"

GOLD_W   = 0.25
AVGO_W   = 0.55
THIRD_W  = 0.20

MIN_HISTORY_YRS    = 15
MIN_SHARPE         = 0.60
MAX_DRAWDOWN_FLOOR = -0.65
MIN_COMMON_DAYS    = 1000   # need reasonable backtest length


def load_prices(category: str, stem: str) -> pd.Series | None:
    path = DATA_DIR / category / f"{stem}.parquet"
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        s = df.set_index("date")["close"].sort_index().dropna()
        return s if len(s) > 252 else None
    except Exception:
        return None


def full_period_stats(prices: pd.Series) -> dict:
    r      = prices.pct_change().dropna()
    yrs    = (prices.index[-1] - prices.index[0]).days / 365.25
    cagr   = float(prices.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 else 0
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0
    dd     = prices / prices.cummax() - 1
    maxdd  = float(dd.min())
    return {"cagr": cagr, "sharpe": sharpe, "maxdd": maxdd, "years": yrs}


def portfolio_perf(g: pd.Series, av: pd.Series, third: pd.Series) -> dict:
    common = g.index.intersection(av.index).intersection(third.index).sort_values()
    if len(common) < MIN_COMMON_DAYS:
        return {}
    g_r  = g.reindex(common).pct_change()
    av_r = av.reindex(common).pct_change()
    th_r = third.reindex(common).pct_change()
    port = (GOLD_W * g_r + AVGO_W * av_r + THIRD_W * th_r).fillna(0)
    eq   = (1 + port).cumprod()
    r    = eq.pct_change().dropna()
    yrs  = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = float(eq.iloc[-1] ** (1 / yrs) - 1)
    dd   = eq / eq.cummax() - 1
    maxdd  = float(dd.min())
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0
    calmar = cagr / abs(maxdd) if maxdd != 0 else 0
    start  = common[0].date()
    return {
        "cagr":   round(cagr, 4),
        "sharpe": round(sharpe, 3),
        "maxdd":  round(maxdd, 4),
        "calmar": round(calmar, 3),
        "years":  round(yrs, 1),
        "start":  str(start),
    }


def main() -> None:
    print("=" * 80)
    print("LLY Substitution Test — Gold25/AVGO55/[X]20")
    print(f"Quality filter: Sharpe >= {MIN_SHARPE}, MaxDD >= {MAX_DRAWDOWN_FLOOR:.0%}, "
          f"history >= {MIN_HISTORY_YRS}yr")
    print("=" * 80)

    gold_prices = load_prices("commodities", "GC_F")
    avgo_prices = load_prices("equities",    "AVGO")
    if gold_prices is None or avgo_prices is None:
        print("ERROR: Gold or AVGO prices not found")
        return

    min_days = int(MIN_HISTORY_YRS * 252)

    # Load and screen all equity candidates
    candidates: dict[str, pd.Series] = {}
    for stem in sorted((DATA_DIR / "equities").glob("*.parquet")):
        t = stem.stem
        if t in ("AVGO",):
            continue
        s = load_prices("equities", t)
        if s is None or len(s) < min_days:
            continue
        st = full_period_stats(s)
        if st["sharpe"] < MIN_SHARPE or st["maxdd"] < MAX_DRAWDOWN_FLOOR:
            continue
        candidates[t] = s

    # Always include LLY as baseline (may or may not pass quality filter)
    lly = load_prices("equities", "LLY")
    if lly is not None and "LLY" not in candidates:
        candidates["LLY"] = lly
        print("Note: LLY added as baseline (may not pass quality filter)")

    # Also test WMT, MNST, COST — commonly mentioned alternatives
    for t in ("WMT", "MNST", "COST"):
        if t not in candidates:
            s = load_prices("equities", t)
            if s is not None:
                candidates[t] = s
                print(f"Note: {t} added for comparison (outside quality filter)")

    print(f"\nTesting {len(candidates)} candidates in 20% slot...\n")

    rows = []
    for ticker, prices in candidates.items():
        p = portfolio_perf(gold_prices, avgo_prices, prices)
        if not p:
            continue
        st = full_period_stats(prices)
        rows.append({
            "ticker":       ticker,
            "port_cagr":    p["cagr"],
            "port_sharpe":  p["sharpe"],
            "port_maxdd":   p["maxdd"],
            "port_calmar":  p["calmar"],
            "port_years":   p["years"],
            "port_start":   p["start"],
            "asset_sharpe": round(st["sharpe"], 3),
            "asset_cagr":   round(st["cagr"], 4),
            "asset_maxdd":  round(st["maxdd"], 4),
            "asset_years":  round(st["years"], 1),
        })

    df = pd.DataFrame(rows).sort_values("port_calmar", ascending=False)

    # Print top 25
    print(f"{'Rank':>4}  {'Ticker':>8}  {'Port CAGR':>10}  {'Sharpe':>7}  "
          f"{'MaxDD':>8}  {'Calmar':>7}  {'Yrs':>5}  {'Asset Sharpe':>13}")
    print("-" * 80)
    for i, row in enumerate(df.head(25).itertuples(), 1):
        marker = " ◄ LLY" if row.ticker == "LLY" else ""
        print(f"  {i:2}.  {row.ticker:>8}  {row.port_cagr:+.1%}      "
              f"{row.port_sharpe:.3f}  {row.port_maxdd:+.1%}   "
              f"{row.port_calmar:.3f}   {row.port_years:.0f}yr  "
              f"{row.asset_sharpe:.3f}{marker}")

    # LLY baseline rank
    lly_rank = df.index[df["ticker"] == "LLY"].tolist()
    if lly_rank:
        lly_row = df[df["ticker"] == "LLY"].iloc[0]
        lly_pos = (df["port_calmar"] > lly_row["port_calmar"]).sum() + 1
        print(f"\nLLY baseline: rank {lly_pos}/{len(df)}  "
              f"CAGR={lly_row['port_cagr']:+.1%}  Calmar={lly_row['port_calmar']:.3f}  "
              f"MaxDD={lly_row['port_maxdd']:+.1%}")

    # Best substitute
    best = df.iloc[0]
    print(f"\nBest substitute: {best['ticker']}  "
          f"CAGR={best['port_cagr']:+.1%}  Calmar={best['port_calmar']:.3f}  "
          f"MaxDD={best['port_maxdd']:+.1%}  ({best['port_years']:.0f}yr backtest)")

    # Save
    OUT_CSV.parent.mkdir(exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")


if __name__ == "__main__":
    main()
