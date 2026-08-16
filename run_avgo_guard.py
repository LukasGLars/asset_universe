"""
run_avgo_guard.py

AVGO Momentum Guard — protect the dominant return driver during drawdowns.

When AVGO drops below its N-day SMA, rotate AVGO's 55% weight to a
defensive allocation. Re-enter when AVGO crosses back above SMA.

Grid:
  MA windows:  50, 100, 150, 200 days
  Defensive:   Gold only | LLY only | Gold+LLY (50/50)

Base: Gold25/AVGO55/LLY20. TC: 10bps per transition.
Output: comparison_results/avgo_guard_grid.csv
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
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "avgo_guard_grid.csv"

GOLD_W  = 0.25
AVGO_W  = 0.55
LLY_W   = 0.20
TC      = 0.0010   # 10bps per transition (entry + exit = 2x)
EXECUTION_LAG_DAYS = 1  # signals come from closes; earliest trade is the next bar

AVGO_IPO = pd.Timestamp("2009-08-06")

# Defensive modes: how to redeploy AVGO's 55% when guard fires
DEFENSIVE_MODES = {
    "gold_only":   {"GC_F": AVGO_W,  "AVGO": 0.0,   "LLY": 0.0},
    "lly_only":    {"GC_F": 0.0,     "AVGO": 0.0,   "LLY": AVGO_W},
    "gold_lly":    {"GC_F": AVGO_W / 2, "AVGO": 0.0, "LLY": AVGO_W / 2},
}

MA_WINDOWS = [50, 100, 150, 200]


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
    r      = equity.pct_change().dropna()
    yrs    = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr   = float(equity.iloc[-1] ** (1 / yrs) - 1)
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


def run_guard(
    gold_r: pd.Series,
    avgo_r: pd.Series,
    lly_r:  pd.Series,
    avgo_price: pd.Series,
    ma_window: int,
    def_mode: str,
) -> dict:
    sma = avgo_price.rolling(ma_window).mean()

    # Signal: True = AVGO above SMA (hold base), False = AVGO below SMA (defensive)
    #
    # Shifted by EXECUTION_LAG_DAYS: the signal is derived from a CLOSING
    # price, so the earliest the position can change is the next session.
    # Without the shift this trades at the very close that generates the
    # signal -- worth -3.46% on the average exit day, which is where the
    # guard's entire apparent edge came from. See MEMORY.md 2026-08-16.
    in_base = (avgo_price >= sma).shift(EXECUTION_LAG_DAYS, fill_value=True)

    port_ret   = pd.Series(0.0, index=gold_r.index)
    prev_state = None   # True=base, False=defensive
    transitions = 0

    def_delta = DEFENSIVE_MODES[def_mode]  # extra weight vs base when defensive

    for i, date in enumerate(gold_r.index):
        state = bool(in_base.reindex([date]).iloc[0]) if date in in_base.index else True

        # TC on transition
        if prev_state is not None and state != prev_state:
            port_ret.iloc[i] -= 2 * TC  # entry + exit
            transitions += 1

        if state:
            # Base weights
            r = GOLD_W * gold_r.iloc[i] + AVGO_W * avgo_r.iloc[i] + LLY_W * lly_r.iloc[i]
        else:
            # Defensive: base gold + base lly + defensive delta, no AVGO
            g_w  = GOLD_W + def_delta["GC_F"]
            l_w  = LLY_W  + def_delta["LLY"]
            r    = g_w * gold_r.iloc[i] + l_w * lly_r.iloc[i]

        port_ret.iloc[i] += r if not pd.isna(r) else 0.0
        prev_state = state

    equity = (1 + port_ret).cumprod()
    p = perf(equity)
    p["transitions"] = transitions

    # Guard stats: % time in base vs defensive
    in_base_aligned = in_base.reindex(gold_r.index, method="ffill").fillna(True)
    p["pct_in_base"] = round(float(in_base_aligned.mean()), 3)
    return p


def main() -> None:
    print("=" * 80)
    print("AVGO Momentum Guard Backtest")
    print("Base: Gold25/AVGO55/LLY20  |  Grid: MA window x Defensive mode")
    print("=" * 80)

    gold_prices = load_prices("commodities", "GC_F")
    avgo_prices = load_prices("equities",    "AVGO")
    lly_prices  = load_prices("equities",    "LLY")

    if any(p is None for p in [gold_prices, avgo_prices, lly_prices]):
        print("ERROR: price data missing")
        return

    # Common date index, post AVGO IPO
    common = (gold_prices.index
              .intersection(avgo_prices.index)
              .intersection(lly_prices.index))
    common = common[common >= AVGO_IPO].sort_values()

    gold_r = gold_prices.reindex(common).pct_change()
    avgo_r = avgo_prices.reindex(common).pct_change()
    lly_r  = lly_prices.reindex(common).pct_change()
    avgo_p = avgo_prices.reindex(common)

    # Base (no guard)
    base_ret = (GOLD_W * gold_r + AVGO_W * avgo_r + LLY_W * lly_r).fillna(0)
    base_eq  = (1 + base_ret).cumprod()
    base_p   = perf(base_eq)
    base_p["transitions"] = 0
    base_p["pct_in_base"] = 1.0

    print(f"\nBase (no guard): CAGR={base_p['cagr']:+.1%}  "
          f"Sharpe={base_p['sharpe']:.3f}  MaxDD={base_p['maxdd']:+.1%}  "
          f"Calmar={base_p['calmar']:.3f}")

    # Print AVGO standalone stats
    avgo_eq   = (1 + avgo_r.fillna(0)).cumprod()
    avgo_base = perf(avgo_eq)
    print(f"AVGO standalone: CAGR={avgo_base['cagr']:+.1%}  "
          f"MaxDD={avgo_base['maxdd']:+.1%}  Calmar={avgo_base['calmar']:.3f}")

    print(f"\n{'MA':>5}  {'Mode':>12}  {'CAGR':>8}  {'Sharpe':>7}  "
          f"{'MaxDD':>8}  {'Calmar':>7}  {'Switches':>9}  {'%InBase':>8}")
    print("-" * 75)

    rows = []
    for ma in MA_WINDOWS:
        for mode_name in DEFENSIVE_MODES:
            p = run_guard(gold_r, avgo_r, lly_r, avgo_p, ma, mode_name)
            delta_calmar = p["calmar"] - base_p["calmar"]
            marker = " +" if delta_calmar > 0 else "  "
            print(f"  {ma:3}d  {mode_name:>12}  {p['cagr']:+.1%}    "
                  f"{p['sharpe']:.3f}  {p['maxdd']:+.1%}   "
                  f"{p['calmar']:.3f}{marker}  {p['transitions']:>6}x  "
                  f"{p['pct_in_base']:.0%}")
            rows.append({"ma": ma, "mode": mode_name, **p,
                         "delta_calmar": round(delta_calmar, 3)})

    # Summary
    gdf = pd.DataFrame(rows).sort_values("calmar", ascending=False)
    best = gdf.iloc[0]
    print(f"\n{'='*75}")
    print(f"Best:  MA={int(best['ma'])}d  mode={best['mode']}  "
          f"Calmar={best['calmar']:.3f}  CAGR={best['cagr']:+.1%}  "
          f"MaxDD={best['maxdd']:+.1%}  switches={int(best['transitions'])}")
    print(f"Base:  Calmar={base_p['calmar']:.3f}  CAGR={base_p['cagr']:+.1%}  "
          f"MaxDD={base_p['maxdd']:+.1%}")
    verdict = "IMPROVES" if best["calmar"] > base_p["calmar"] else "NO IMPROVEMENT"
    print(f"Verdict: {verdict}  "
          f"(delta Calmar={best['calmar'] - base_p['calmar']:+.3f})")

    # Current AVGO signal
    latest_avgo = avgo_p.iloc[-1]
    for ma in MA_WINDOWS:
        sma_val = avgo_p.iloc[-ma:].mean() if len(avgo_p) >= ma else None
        if sma_val:
            signal = "ABOVE (hold base)" if latest_avgo >= sma_val else "BELOW (defensive)"
            print(f"  AVGO vs {ma}d SMA: ${latest_avgo:.2f} vs ${sma_val:.2f}  → {signal}")

    OUT_CSV.parent.mkdir(exist_ok=True)
    gdf.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")


if __name__ == "__main__":
    main()
