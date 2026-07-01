"""
run_parameter_sensitivity.py

Parameter sensitivity grid for Strategy D (Base + AVGO 200d guard + silver
GSR tactical), the validated combined system in run_combined_system.py.

Parametrizes:
  AVGO_MA   : the AVGO guard's SMA window
  gsr_scale : a single multiplicative factor applied to GSR_T1, GSR_T2 and
              GSR_EXIT together (preserves their relative spacing)

Grid: AVGO_MA in [150, 175, 200, 225, 250]
      x gsr_scale in [0.80, 0.90, 1.00, 1.10, 1.20]  -> 25 combinations

For every cell, Strategy D (guard + silver combined) is re-run over the full
backtest period (2009-08-06 to present, 10bps TC per asset per transition)
and CAGR/Sharpe/MaxDD/Calmar are recorded.

Self-check: the cell at AVGO_MA=200, gsr_scale=1.00 must reproduce the known
-correct baseline from run_combined_system.py Strategy D:
  CAGR +37.1%, Sharpe 1.688, MaxDD -16.8%, Calmar 2.205

Output: comparison_results/parameter_sensitivity_grid.csv
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
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "parameter_sensitivity_grid.csv"

# ── Base thresholds (gsr_scale = 1.00 reproduces run_combined_system.py exactly) ──
GSR_T1_BASE      = 83.36
GSR_T2_BASE      = 86.45
GSR_EXIT_BASE    = 62.56
GSR_PEAK_WINDOW  = 60
GSR_PEAK_FALL    = 0.05
TC               = 0.0010
AVGO_IPO         = pd.Timestamp("2009-08-06")

# ── Grid ────────────────────────────────────────────────────────────────────────
AVGO_MA_GRID   = [150, 175, 200, 225, 250]
GSR_SCALE_GRID = [0.80, 0.90, 1.00, 1.10, 1.20]

# Known-correct baseline (Strategy D, AVGO_MA=200, gsr_scale=1.00) for self-check
BASELINE = {"cagr": 0.371, "sharpe": 1.688, "maxdd": -0.168, "calmar": 2.205}
BASELINE_TOL = {"cagr": 0.01, "sharpe": 0.01, "maxdd": 0.005, "calmar": 0.02}

# ── Weight table (unchanged from run_combined_system.py) ────────────────────────
WEIGHTS: dict[tuple[bool, str], dict[str, float]] = {
    (False, "INACTIVE"): {"GC_F": 0.250, "AVGO": 0.550, "LLY": 0.200, "SI_F": 0.000},
    (False, "T1"):       {"GC_F": 0.250, "AVGO": 0.430, "LLY": 0.200, "SI_F": 0.120},
    (False, "T2"):       {"GC_F": 0.250, "AVGO": 0.380, "LLY": 0.200, "SI_F": 0.170},
    (True,  "INACTIVE"): {"GC_F": 0.525, "AVGO": 0.000, "LLY": 0.475, "SI_F": 0.000},
    (True,  "T1"):       {"GC_F": 0.405, "AVGO": 0.000, "LLY": 0.475, "SI_F": 0.120},
    (True,  "T2"):       {"GC_F": 0.355, "AVGO": 0.000, "LLY": 0.475, "SI_F": 0.170},
}


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


def perf(equity: pd.Series, label: str = "") -> dict:
    r      = equity.pct_change().dropna()
    yrs    = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr   = float(equity.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 else 0
    dd     = equity / equity.cummax() - 1
    maxdd  = float(dd.min())
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0
    calmar = cagr / abs(maxdd) if maxdd != 0 else 0
    return {
        "label":  label,
        "cagr":   round(cagr, 4),
        "sharpe": round(sharpe, 3),
        "maxdd":  round(maxdd, 4),
        "calmar": round(calmar, 3),
        "years":  round(yrs, 1),
    }


def tc_cost(prev: dict, curr: dict) -> float:
    """10bps per asset that changed weight meaningfully."""
    cost = 0.0
    for asset in set(list(prev.keys()) + list(curr.keys())):
        if abs(prev.get(asset, 0) - curr.get(asset, 0)) > 0.005:
            cost += TC
    return cost


def build_signals(
    avgo_p: pd.Series,
    gold_p: pd.Series,
    silver_p: pd.Series,
    common: pd.DatetimeIndex,
    avgo_ma: int,
    gsr_t1: float,
    gsr_t2: float,
    gsr_exit: float,
) -> pd.DataFrame:
    """
    Build daily guard and silver state signals, parametrized by AVGO SMA window
    and the GSR T1/T2/exit thresholds. Same logic as run_combined_system.py.
    """
    avgo_r   = avgo_p.reindex(common)
    sma      = avgo_r.rolling(avgo_ma).mean()
    guard    = (avgo_r < sma).fillna(False)

    gold_r   = gold_p.reindex(common)
    silv_r   = silver_p.reindex(common)
    gsr      = (gold_r / silv_r).dropna()
    gsr      = gsr.reindex(common)
    peak     = gsr.rolling(GSR_PEAK_WINDOW).max()
    fall_pct = (peak - gsr) / peak.replace(0, np.nan)

    # Silver state machine
    silver_states = []
    state = "INACTIVE"
    for i in range(len(common)):
        gsr_val  = gsr.iloc[i]  if not pd.isna(gsr.iloc[i])  else np.nan
        fall_val = fall_pct.iloc[i] if not pd.isna(fall_pct.iloc[i]) else 0.0

        if pd.isna(gsr_val):
            silver_states.append(state)
            continue

        # Exit check first
        if state in ("T1", "T2") and gsr_val < gsr_exit:
            state = "INACTIVE"

        # Entry check (only from INACTIVE)
        if state == "INACTIVE":
            fallen = fall_val >= GSR_PEAK_FALL
            if gsr_val >= gsr_t2 and fallen:
                state = "T2"
            elif gsr_val >= gsr_t1 and fallen:
                state = "T1"

        silver_states.append(state)

    return pd.DataFrame({
        "guard":        guard.values,
        "silver_state": silver_states,
    }, index=common)


def run_strategy(
    prices: dict[str, pd.Series],
    signals: pd.DataFrame,
    use_guard: bool,
    use_silver: bool,
) -> pd.Series:
    """
    Simulate portfolio using given signal flags. Returns the equity curve.
    """
    common = signals.index
    rets   = {t: prices[t].reindex(common).pct_change() for t in prices}

    port_ret = pd.Series(0.0, index=common)
    prev_w   = None

    for i, date in enumerate(common):
        guard  = bool(signals["guard"].iloc[i])  if use_guard  else False
        silver = signals["silver_state"].iloc[i]  if use_silver else "INACTIVE"

        curr_w = WEIGHTS[(guard, silver)]

        if prev_w is not None and curr_w != prev_w:
            cost = tc_cost(prev_w, curr_w)
            port_ret.iloc[i] -= cost

        r = sum(w * (rets[t].iloc[i] if not pd.isna(rets[t].iloc[i]) else 0.0)
                for t, w in curr_w.items())
        port_ret.iloc[i] += r
        prev_w = curr_w

    return (1 + port_ret).cumprod()


def main() -> None:
    print("=" * 70)
    print("Parameter Sensitivity Grid — Strategy D (Guard + Silver)")
    print(f"  AVGO_MA   : {AVGO_MA_GRID}")
    print(f"  gsr_scale : {GSR_SCALE_GRID}")
    print(f"  Period: {AVGO_IPO.date()} to present  |  TC: {TC*100:.0f}bps")
    print("=" * 70)

    gold_p   = load_prices("commodities", "GC_F")
    avgo_p   = load_prices("equities",    "AVGO")
    lly_p    = load_prices("equities",    "LLY")
    silver_p = load_prices("commodities", "SI_F")

    if any(p is None for p in [gold_p, avgo_p, lly_p, silver_p]):
        print("ERROR: missing price data")
        return

    common = (gold_p.index
              .intersection(avgo_p.index)
              .intersection(lly_p.index)
              .intersection(silver_p.index))
    common = common[common >= AVGO_IPO].sort_values()
    print(f"Common dates: {len(common)} ({common[0].date()} to {common[-1].date()})")

    prices = {
        "GC_F": gold_p,
        "AVGO": avgo_p,
        "LLY":  lly_p,
        "SI_F": silver_p,
    }

    results = []
    print("\nRunning grid (25 combinations)...")
    for avgo_ma in AVGO_MA_GRID:
        for gsr_scale in GSR_SCALE_GRID:
            gsr_t1   = GSR_T1_BASE * gsr_scale
            gsr_t2   = GSR_T2_BASE * gsr_scale
            gsr_exit = GSR_EXIT_BASE * gsr_scale

            signals = build_signals(avgo_p, gold_p, silver_p, common,
                                     avgo_ma, gsr_t1, gsr_t2, gsr_exit)
            eq = run_strategy(prices, signals, use_guard=True, use_silver=True)
            p  = perf(eq)
            p["avgo_ma"]   = avgo_ma
            p["gsr_scale"] = gsr_scale
            results.append(p)
            print(f"  AVGO_MA={avgo_ma:<4} gsr_scale={gsr_scale:.2f}  "
                  f"CAGR {p['cagr']:+.1%}  Sharpe {p['sharpe']:.3f}  "
                  f"MaxDD {p['maxdd']:+.1%}  Calmar {p['calmar']:.3f}")

    df = pd.DataFrame(results)[["avgo_ma", "gsr_scale", "cagr", "sharpe", "maxdd", "calmar", "years"]]
    OUT_CSV.parent.mkdir(exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")

    # ── Self-check: AVGO_MA=200, gsr_scale=1.00 must reproduce the baseline ───
    print("\n" + "=" * 70)
    print("SELF-CHECK: AVGO_MA=200, gsr_scale=1.00 vs known-correct baseline")
    print("=" * 70)
    center = df[(df["avgo_ma"] == 200) & (df["gsr_scale"] == 1.00)].iloc[0]
    checks_passed = True
    for metric, base_val in BASELINE.items():
        cell_val = float(center[metric])
        tol = BASELINE_TOL[metric]
        ok = abs(cell_val - base_val) <= tol
        checks_passed &= ok
        status = "OK" if ok else "MISMATCH"
        print(f"  {metric:<8}: grid={cell_val:+.4f}  baseline={base_val:+.4f}  "
              f"diff={cell_val - base_val:+.4f}  tol={tol}  [{status}]")

    print(f"\n  SELF-CHECK RESULT: {'PASS' if checks_passed else 'FAIL'}")
    if not checks_passed:
        print("  WARNING: center cell does not reproduce baseline — do not trust grid results.")

    # ── Robustness analysis ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("ROBUSTNESS ANALYSIS")
    print("=" * 70)
    calmar_min = df["calmar"].min()
    calmar_max = df["calmar"].max()
    calmar_center = float(center["calmar"])
    calmar_mean = df["calmar"].mean()
    calmar_std  = df["calmar"].std()

    corners = df[df["avgo_ma"].isin([150, 250]) & df["gsr_scale"].isin([0.80, 1.20])]
    edges   = df[(df["avgo_ma"].isin([150, 250])) | (df["gsr_scale"].isin([0.80, 1.20]))]
    neighbors = df[(df["avgo_ma"].isin([175, 200, 225])) & (df["gsr_scale"].isin([0.90, 1.00, 1.10]))]

    print(f"  Calmar range across grid : [{calmar_min:.3f}, {calmar_max:.3f}]  "
          f"(spread {calmar_max - calmar_min:.3f})")
    print(f"  Calmar mean / std         : {calmar_mean:.3f} / {calmar_std:.3f}")
    print(f"  Center cell (200, 1.00)   : {calmar_center:.3f}")
    print(f"  3x3 neighborhood mean     : {neighbors['calmar'].mean():.3f}  "
          f"(min {neighbors['calmar'].min():.3f}, max {neighbors['calmar'].max():.3f})")
    print(f"  4 corner cells mean       : {corners['calmar'].mean():.3f}  "
          f"(min {corners['calmar'].min():.3f}, max {corners['calmar'].max():.3f})")
    print(f"  All edge cells mean       : {edges['calmar'].mean():.3f}")

    print("\n  Full grid (Calmar), rows=AVGO_MA, cols=gsr_scale:")
    pivot = df.pivot(index="avgo_ma", columns="gsr_scale", values="calmar")
    print(pivot.to_string())


if __name__ == "__main__":
    main()
