"""
run_joint_stress_validation.py

Validates the joint-stress escalation rule (see MEMORY.md, "AVGO/LLY joint
stress escalation") against two datasets, same pattern as
run_crash_guard_validation.py:

  1. AVGO's own history (2009-2026).
  2. A TXN analog: same methodology, TXN substituted for AVGO, run over
     TXN's full 2000-2026 history -- includes the 2001 dot-com crash and
     2008 GFC, neither of which AVGO's own history was ever tested against.

Question: when the AVGO guard fires AND LLY independently trips the exact
same guard logic (200d SMA / 5d-(-10%) ROC -- no new parameters, just
checking if LLY trips the already-validated AVGO trigger too), does
escalating further into Gold help, versus the guard-alone system?

Finding (2026-07-02): yes, on both datasets, and the effect is monotonic in
the escalation weight (not a curve-fit interior spike) -- more Gold during
joint stress is steadily better up to 100%. Validated parameters: 100% Gold
(AVGO 0%, LLY 0%) when guard AND LLY-stress are both active, silver funded
from Gold instead of AVGO in that state (AVGO is already 0%).

  AVGO actual:  Calmar 2.407 (guard alone) -> 2.957 (100% Gold escalation)
  TXN analog:   Calmar 0.824 (guard alone) -> 1.028 (100% Gold escalation)

Also reports what gold does during joint-stress episodes specifically --
the point of the rule is that gold should be doing useful work exactly when
both growth engines are confirmed correlated and falling together.

Output: printed only -- no CSV, this is a validation/robustness check to
rerun when reconsidering the rule, not a daily-automation script.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from asset_universe import config

DATA_DIR = config.raw_data_dir()

GSR_T1, GSR_T2, GSR_EXIT = 83.36, 86.45, 62.56
GSR_PEAK_WINDOW, GSR_PEAK_FALL = 60, 0.05
TC = 0.0010
AVGO_MA, LLY_MA = 200, 200
CRASH_WINDOW, CRASH_THRESH = 5, -0.10  # same validated params as the AVGO guard, reused for LLY

ESC_WEIGHTS = [0.60, 0.70, 0.80, 0.90, 1.00]
WINDOWS = [3, 5, 10, 15]
THRESHOLDS = [-0.10, -0.12, -0.15, -0.18, -0.20]


def load(category: str, stem: str) -> pd.Series:
    df = pd.read_parquet(DATA_DIR / category / f"{stem}.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index().dropna()


def perf(equity: pd.Series) -> dict:
    r = equity.pct_change().dropna()
    yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = float(equity.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 else 0.0
    dd = equity / equity.cummax() - 1
    maxdd = float(dd.min())
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
    calmar = cagr / abs(maxdd) if maxdd != 0 else 0.0
    return {"cagr": cagr, "sharpe": sharpe, "maxdd": maxdd, "calmar": calmar,
            "worst_date": dd.idxmin()}


def compute_gsr_states(gold, silver, common):
    gsr = (gold.reindex(common) / silver.reindex(common)).dropna().reindex(common)
    peak = gsr.rolling(GSR_PEAK_WINDOW).max()
    fall = (peak - gsr) / peak.replace(0, np.nan)
    states, state = [], "INACTIVE"
    for i in range(len(common)):
        gv = gsr.iloc[i]
        fv = fall.iloc[i] if not pd.isna(fall.iloc[i]) else 0.0
        if pd.isna(gv):
            states.append(state)
            continue
        if state in ("T1", "T2") and gv < GSR_EXIT:
            state = "INACTIVE"
        if state == "INACTIVE":
            fallen = fv >= GSR_PEAK_FALL
            if gv >= GSR_T2 and fallen:
                state = "T2"
            elif gv >= GSR_T1 and fallen:
                state = "T1"
        states.append(state)
    return states


def weights_for(guard: bool, lly_stress: bool, gsr_state: str, g_esc: float) -> dict:
    if guard and lly_stress:
        base = {"G": g_esc, "X": 0.00, "L": round(1 - g_esc, 4)}
    elif guard:
        base = {"G": 0.525, "X": 0.00, "L": 0.475}
    else:
        base = {"G": 0.250, "X": 0.550, "L": 0.200}
    base["S"] = 0.0
    if gsr_state in ("T1", "T2"):
        shift = 0.12 if gsr_state == "T1" else 0.17
        fund_from = "X" if base["X"] > 0 else "G"
        base = dict(base)
        base[fund_from] = round(base[fund_from] - shift, 4)
        base["S"] = shift
    return base


def build_common_and_signals(x_series, gold, lly_series, silver, start,
                              g_esc, lly_window, lly_thresh):
    common = (gold.index.intersection(x_series.index)
              .intersection(lly_series.index).intersection(silver.index))
    common = common[common >= start].sort_values()

    x_r = x_series.reindex(common)
    guard = ((x_r < x_r.rolling(AVGO_MA).mean())
             | (x_r.pct_change(CRASH_WINDOW) <= CRASH_THRESH)).fillna(False)

    l_r = lly_series.reindex(common)
    lly_stress = ((l_r < l_r.rolling(LLY_MA).mean())
                  | (l_r.pct_change(lly_window) <= lly_thresh)).fillna(False)

    states = compute_gsr_states(gold, silver, common)
    return common, x_r, l_r, guard, lly_stress, states


def run(x_series, gold, lly_series, silver, start, g_esc, lly_window, lly_thresh):
    common, x_r, l_r, guard, lly_stress, states = build_common_and_signals(
        x_series, gold, lly_series, silver, start, g_esc, lly_window, lly_thresh)

    prices = {"G": gold, "X": x_r, "L": l_r, "S": silver}
    rets = {k: v.reindex(common).pct_change() for k, v in prices.items()}
    port = pd.Series(0.0, index=common)
    prev = None
    for i in range(len(common)):
        g, ls = bool(guard.iloc[i]), bool(lly_stress.iloc[i])
        w = weights_for(g, ls, states[i], g_esc)
        if prev is not None and w != prev:
            cost = sum(TC for a in set(list(w) + list(prev))
                       if abs(w.get(a, 0) - prev.get(a, 0)) > 0.005)
            port.iloc[i] -= cost
        r = sum(wt * (rets[a].iloc[i] if not pd.isna(rets[a].iloc[i]) else 0.0)
                for a, wt in w.items())
        port.iloc[i] += r
        prev = w
    return (1 + port).cumprod(), guard, lly_stress


def main() -> None:
    gold = load("commodities", "GC_F")
    silver = load("commodities", "SI_F")
    lly = load("equities", "LLY")
    avgo = load("equities", "AVGO")
    txn = load("equities", "TXN")

    datasets = [
        ("AVGO actual", avgo, pd.Timestamp("2009-08-06")),
        ("TXN analog (includes 2001, 2008)", txn, pd.Timestamp("2000-08-30")),
    ]

    for label, series, start in datasets:
        print("=" * 90)
        print(label)
        print("=" * 90)

        # Guard-alone baseline: disable the joint condition entirely (impossible
        # LLY-stress thresholds) to reproduce the existing live rule exactly.
        eq_guard_alone, _, _ = run(series, gold, lly, silver, start, 0.525, 10**9, -10**9)
        p_guard = perf(eq_guard_alone)
        print(f"Guard alone (existing live rule):     CAGR {p_guard['cagr']:+.1%}  "
              f"MaxDD {p_guard['maxdd']:+.1%}  Calmar {p_guard['calmar']:.3f}")

        eq_joint, guard2, lly_stress2 = run(series, gold, lly, silver, start, 1.00, CRASH_WINDOW, CRASH_THRESH)
        p_joint = perf(eq_joint)
        print(f"+ Joint-stress escalation (100% G):   CAGR {p_joint['cagr']:+.1%}  "
              f"MaxDD {p_joint['maxdd']:+.1%}  Calmar {p_joint['calmar']:.3f}")

        joint_mask = guard2 & lly_stress2
        common = joint_mask.index
        gold_ret = gold.reindex(common).pct_change()
        print(f"\nJoint stress active {joint_mask.mean():.1%} of days (n={joint_mask.sum()})")
        print(f"Gold daily return, joint-stress days:    mean {gold_ret[joint_mask].mean():+.3%}")
        print(f"Gold daily return, guard-only days:      mean {gold_ret[guard2 & ~lly_stress2].mean():+.3%}")
        print(f"Gold daily return, all other days:       mean {gold_ret[~guard2].mean():+.3%}")

        print("\nEscalation-weight grid (Calmar), LLY-stress fixed at 5d/-10%:")
        rows = []
        for g_esc in ESC_WEIGHTS:
            eq, _, _ = run(series, gold, lly, silver, start, g_esc, CRASH_WINDOW, CRASH_THRESH)
            rows.append({"gold_weight": f"{g_esc:.0%}", "calmar": round(perf(eq)["calmar"], 3)})
        print(pd.DataFrame(rows).set_index("gold_weight").to_string())

        print("\nLLY-stress definition grid (Calmar), escalation fixed at 100% Gold:")
        grid_rows = []
        for w in WINDOWS:
            row = {"window": w}
            for t in THRESHOLDS:
                eq, _, _ = run(series, gold, lly, silver, start, 1.00, w, t)
                row[f"{t:.0%}"] = round(perf(eq)["calmar"], 3)
            grid_rows.append(row)
        print(pd.DataFrame(grid_rows).set_index("window").to_string())
        print()


if __name__ == "__main__":
    main()
