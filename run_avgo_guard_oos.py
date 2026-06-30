"""
run_avgo_guard_oos.py

OOS validation of the 200d AVGO momentum guard (gold_lly defensive mode).

Split:
  IS  — 2009-08-06 to 2019-12-31 (~10.5yr, post-GFC bull market)
  OOS — 2020-01-01 to present     (~6.5yr, COVID + 2022 bear + 2024 bull + tariff)

Tests:
  1. IS vs OOS performance: does the guard hold up out-of-sample?
  2. Yearly breakdown: which years does the guard help/hurt?
  3. Generalisation: apply same 200d rule to LLY and Gold — does the
     mechanism work on other base assets or is it AVGO-specific?
  4. AVGO signal log: every 200d MA crossing with entry/exit dates.

Output: comparison_results/avgo_guard_oos.csv
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
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "avgo_guard_oos.csv"

GOLD_W  = 0.25
AVGO_W  = 0.55
LLY_W   = 0.20
TC      = 0.0010
MA      = 200

AVGO_IPO  = pd.Timestamp("2009-08-06")
OOS_START = pd.Timestamp("2020-01-01")


def load_prices(category: str, stem: str) -> pd.Series | None:
    path = DATA_DIR / category / f"{stem}.parquet"
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")["close"].sort_index().dropna()
    except Exception:
        return None


def perf(equity: pd.Series) -> dict:
    if len(equity) < 2:
        return {"cagr": 0, "sharpe": 0, "maxdd": 0, "calmar": 0}
    r      = equity.pct_change().dropna()
    yrs    = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr   = float(equity.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 else 0
    dd     = equity / equity.cummax() - 1
    maxdd  = float(dd.min())
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0
    calmar = cagr / abs(maxdd) if maxdd != 0 else 0
    return {
        "cagr":   round(cagr, 4),
        "sharpe": round(sharpe, 3),
        "maxdd":  round(maxdd, 4),
        "calmar": round(calmar, 3),
    }


def build_guard_returns(
    gold_r: pd.Series,
    avgo_r: pd.Series,
    lly_r:  pd.Series,
    avgo_p: pd.Series,
) -> tuple[pd.Series, list[dict]]:
    """
    Apply 200d AVGO guard (gold_lly defensive) to full common index.
    Returns daily portfolio returns and a list of signal events.
    """
    sma      = avgo_p.rolling(MA).mean()
    in_base  = avgo_p >= sma

    port_ret   = pd.Series(0.0, index=gold_r.index)
    prev_state = None
    events: list[dict] = []

    for i, date in enumerate(gold_r.index):
        state = bool(in_base.iloc[i]) if not pd.isna(in_base.iloc[i]) else True

        if prev_state is not None and state != prev_state:
            port_ret.iloc[i] -= 2 * TC
            events.append({
                "date":      date,
                "direction": "→BASE" if state else "→DEF",
                "avgo_px":   round(float(avgo_p.iloc[i]), 2),
                "sma200":    round(float(sma.iloc[i]), 2) if not pd.isna(sma.iloc[i]) else None,
            })

        if state:
            r = (GOLD_W * gold_r.iloc[i] +
                 AVGO_W * avgo_r.iloc[i] +
                 LLY_W  * lly_r.iloc[i])
        else:
            r = ((GOLD_W + AVGO_W / 2) * gold_r.iloc[i] +
                 (LLY_W  + AVGO_W / 2) * lly_r.iloc[i])

        port_ret.iloc[i] += r if not pd.isna(r) else 0.0
        prev_state = state

    return port_ret, events


def yearly_perf(returns: pd.Series) -> pd.DataFrame:
    rows = []
    for yr in sorted(returns.index.year.unique()):
        r_yr = returns[returns.index.year == yr]
        eq   = (1 + r_yr).cumprod()
        p    = perf(eq)
        rows.append({"year": yr, **p})
    return pd.DataFrame(rows)


def single_asset_guard(prices: pd.Series, label: str) -> None:
    """Apply 200d MA guard: when asset < 200d MA, hold cash (0% return)."""
    r    = prices.pct_change().fillna(0)
    sma  = prices.rolling(MA).mean()
    hold = prices >= sma

    guarded = r.copy()
    for i in range(len(r)):
        if not hold.iloc[i]:
            guarded.iloc[i] = 0.0

    eq_raw     = (1 + r.fillna(0)).cumprod()
    eq_guarded = (1 + guarded).cumprod()
    p_raw      = perf(eq_raw)
    p_guarded  = perf(eq_guarded)

    switches = int((hold != hold.shift()).sum())
    print(f"  {label:8}  raw:     CAGR={p_raw['cagr']:+.1%}  "
          f"MaxDD={p_raw['maxdd']:+.1%}  Calmar={p_raw['calmar']:.3f}")
    print(f"  {label:8}  guarded: CAGR={p_guarded['cagr']:+.1%}  "
          f"MaxDD={p_guarded['maxdd']:+.1%}  Calmar={p_guarded['calmar']:.3f}  "
          f"switches={switches}")


def main() -> None:
    print("=" * 80)
    print(f"AVGO 200d Guard — OOS Validation")
    print(f"  IS:  {AVGO_IPO.date()} → 2019-12-31")
    print(f"  OOS: {OOS_START.date()} → present")
    print("=" * 80)

    gold_prices = load_prices("commodities", "GC_F")
    avgo_prices = load_prices("equities",    "AVGO")
    lly_prices  = load_prices("equities",    "LLY")

    if any(p is None for p in [gold_prices, avgo_prices, lly_prices]):
        print("ERROR: missing price data")
        return

    common = (gold_prices.index
              .intersection(avgo_prices.index)
              .intersection(lly_prices.index))
    common = common[common >= AVGO_IPO].sort_values()

    gold_r = gold_prices.reindex(common).pct_change()
    avgo_r = avgo_prices.reindex(common).pct_change()
    lly_r  = lly_prices.reindex(common).pct_change()
    avgo_p = avgo_prices.reindex(common)

    # Base returns (no guard)
    base_ret = (GOLD_W * gold_r + AVGO_W * avgo_r + LLY_W * lly_r).fillna(0)

    # Guard returns (full period, so SMA is computed consistently)
    guard_ret, events = build_guard_returns(gold_r, avgo_r, lly_r, avgo_p)

    # ── IS / OOS split ────────────────────────────────────────────────────────
    is_mask  = common < OOS_START
    oos_mask = common >= OOS_START

    def split_perf(ret: pd.Series, label: str) -> None:
        eq_is  = (1 + ret[is_mask].fillna(0)).cumprod()
        eq_oos = (1 + ret[oos_mask].fillna(0)).cumprod()
        eq_all = (1 + ret.fillna(0)).cumprod()
        p_is   = perf(eq_is)
        p_oos  = perf(eq_oos)
        p_all  = perf(eq_all)
        print(f"\n  {label}")
        print(f"    Full  ({(common[-1]-common[0]).days//365}yr): "
              f"CAGR={p_all['cagr']:+.1%}  Sharpe={p_all['sharpe']:.3f}  "
              f"MaxDD={p_all['maxdd']:+.1%}  Calmar={p_all['calmar']:.3f}")
        print(f"    IS    (~{is_mask.sum()//252}yr):   "
              f"CAGR={p_is['cagr']:+.1%}  Sharpe={p_is['sharpe']:.3f}  "
              f"MaxDD={p_is['maxdd']:+.1%}  Calmar={p_is['calmar']:.3f}")
        print(f"    OOS   (~{oos_mask.sum()//252}yr):   "
              f"CAGR={p_oos['cagr']:+.1%}  Sharpe={p_oos['sharpe']:.3f}  "
              f"MaxDD={p_oos['maxdd']:+.1%}  Calmar={p_oos['calmar']:.3f}")
        return p_is, p_oos

    print("\n── IS / OOS Performance ─────────────────────────────────────────────────")
    split_perf(base_ret,  "Static base  (Gold25/AVGO55/LLY20)")
    split_perf(guard_ret, "200d guard   (gold_lly defensive)")

    # ── Year-by-year breakdown ────────────────────────────────────────────────
    print("\n── Year-by-Year Breakdown ───────────────────────────────────────────────")
    base_yr  = yearly_perf(base_ret)
    guard_yr = yearly_perf(guard_ret)
    merged   = base_yr.merge(guard_yr, on="year", suffixes=("_base", "_guard"))

    print(f"\n  {'Year':>6}  {'Base CAGR':>10}  {'Guard CAGR':>11}  "
          f"{'Base MaxDD':>11}  {'Guard MaxDD':>12}  {'Winner':>8}")
    print("  " + "-" * 70)
    for _, row in merged.iterrows():
        winner = "GUARD" if row["calmar_guard"] > row["calmar_base"] else "base"
        oos_tag = " *" if row["year"] >= OOS_START.year else "  "
        print(f"  {int(row['year']):>4}{oos_tag}  "
              f"{row['cagr_base']:+.1%}       "
              f"{row['cagr_guard']:+.1%}        "
              f"{row['maxdd_base']:+.1%}        "
              f"{row['maxdd_guard']:+.1%}         "
              f"{winner}")
    print("  (* = OOS year)")

    # ── Generalisation test ───────────────────────────────────────────────────
    print("\n── Generalisation: 200d MA Guard on Individual Assets (standalone) ──────")
    print("  (When asset < 200d SMA → hold cash; tests if mechanism is asset-specific)")
    single_asset_guard(avgo_prices.reindex(common).dropna(), "AVGO")
    single_asset_guard(gold_prices.reindex(common).dropna(), "Gold")
    single_asset_guard(lly_prices.reindex(common).dropna(),  "LLY")

    # ── Signal log ────────────────────────────────────────────────────────────
    print(f"\n── 200d MA Crossings ({len(events)} total) ──────────────────────────────────")
    for e in events:
        oos_tag = " [OOS]" if e["date"] >= OOS_START else ""
        print(f"  {e['date'].date()}  {e['direction']}  "
              f"AVGO=${e['avgo_px']}  SMA200=${e['sma200']}{oos_tag}")

    # Current status
    print(f"\n── Current Status ───────────────────────────────────────────────────────")
    latest_px  = float(avgo_p.iloc[-1])
    sma200_now = float(avgo_p.rolling(MA).mean().iloc[-1])
    state      = "BASE (hold AVGO)" if latest_px >= sma200_now else "DEFENSIVE (gold+lly)"
    print(f"  AVGO: ${latest_px:.2f}  |  200d SMA: ${sma200_now:.2f}  |  Signal: {state}")

    # ── Save ──────────────────────────────────────────────────────────────────
    rows = []
    for _, r in merged.iterrows():
        rows.append({
            "year":       int(r["year"]),
            "oos":        r["year"] >= OOS_START.year,
            "base_cagr":  r["cagr_base"],
            "guard_cagr": r["cagr_guard"],
            "base_maxdd": r["maxdd_base"],
            "guard_maxdd": r["maxdd_guard"],
            "base_calmar": r["calmar_base"],
            "guard_calmar": r["calmar_guard"],
        })
    OUT_CSV.parent.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")


if __name__ == "__main__":
    main()
