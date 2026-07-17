"""
run_base_optimizer_with_guard.py

The missing cross-test flagged 2026-07-17: run_base_optimizer.py finds the
best STATIC Gold/AVGO/LLY split (no guard); run_combined_system.py tests
the guard mechanism only on the one weighting already chosen (25/55/20).
Nobody has tested "a different base weight + the same guard" against the
live strategy. This does that -- same 231-combination grid (5% steps) as
run_base_optimizer.py, but each point runs the FULL guard + crash-trigger +
silver + joint-stress overlay from run_combined_system.py, not the static
base alone.

Weight-table generalization: run_combined_system.py's WEIGHTS/JOINT_WEIGHTS
are hand-built constants for the 25/55/20 case specifically. build_weight_tables()
below reproduces them from three mechanical rules -- verified byte-for-byte
identical to the original tables at gold=0.25/avgo=0.55/lly=0.20 (see
tests/test_base_optimizer_with_guard.py):
  1. Silver (T1/T2) funds from AVGO in base mode, from Gold in guard mode,
     by the fixed GSR_T1_SILVER/GSR_T2_SILVER amounts (0.12/0.17) -- same
     amounts regardless of the base split, since these come from the
     silver tactical rule's own sizing, not the base weights.
  2. Guard trigger redistributes AVGO's full base weight 50/50 into
     Gold/LLY (confirmed algebraically from the original 25/55/20 table:
     0.25 + 0.55*0.5 = 0.525, 0.20 + 0.55*0.5 = 0.475 -- exactly matches
     the hardcoded Gold52.5%/LLY47.5% guard-state weights).
  3. Joint-stress (guard AND LLY stress) flies to 100% Gold, minus
     whatever silver is taking -- unchanged by the base split, since it's
     a full flight to the ballast asset regardless of what the base was.

Usage:
    python run_base_optimizer_with_guard.py
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    # Only when run directly -- doing this at import time breaks pytest's
    # stdout/stderr capture for anything that imports this module (same
    # gotcha as run_combined_system.py).
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import run_combined_system as rcs

OUT_CSV = PROJECT_ROOT / "comparison_results" / "base_optimizer_with_guard_grid.csv"

SILVER_T1 = 0.12
SILVER_T2 = 0.17


def build_weight_tables(gold: float, avgo: float, lly: float) -> tuple[dict, dict]:
    """Generalized WEIGHTS/JOINT_WEIGHTS for an arbitrary (gold, avgo, lly)
    base split, following the three rules above. Returns (weights, joint_weights)
    in the same shape run_combined_system.run_strategy expects."""
    weights = {
        (False, "INACTIVE"): {"GC_F": gold, "AVGO": avgo, "LLY": lly, "SI_F": 0.0},
        (False, "T1"):       {"GC_F": gold, "AVGO": avgo - SILVER_T1, "LLY": lly, "SI_F": SILVER_T1},
        (False, "T2"):       {"GC_F": gold, "AVGO": avgo - SILVER_T2, "LLY": lly, "SI_F": SILVER_T2},
        (True,  "INACTIVE"): {"GC_F": gold + avgo / 2, "AVGO": 0.0, "LLY": lly + avgo / 2, "SI_F": 0.0},
        (True,  "T1"):       {"GC_F": gold + avgo / 2 - SILVER_T1, "AVGO": 0.0, "LLY": lly + avgo / 2, "SI_F": SILVER_T1},
        (True,  "T2"):       {"GC_F": gold + avgo / 2 - SILVER_T2, "AVGO": 0.0, "LLY": lly + avgo / 2, "SI_F": SILVER_T2},
    }
    joint_weights = {
        "INACTIVE": {"GC_F": 1.0, "AVGO": 0.0, "LLY": 0.0, "SI_F": 0.0},
        "T1":       {"GC_F": 1.0 - SILVER_T1, "AVGO": 0.0, "LLY": 0.0, "SI_F": SILVER_T1},
        "T2":       {"GC_F": 1.0 - SILVER_T2, "AVGO": 0.0, "LLY": 0.0, "SI_F": SILVER_T2},
    }
    return weights, joint_weights


def run_strategy_variant(
    prices: dict[str, pd.Series],
    signals: pd.DataFrame,
    weights: dict,
    joint_weights: dict,
) -> pd.Series:
    """Same simulation as run_combined_system.run_strategy (guard + silver +
    joint-stress, i.e. strategy E), parameterized on explicit weight tables
    instead of module-level constants, so it can be run once per grid point."""
    common = signals.index
    rets   = {t: prices[t].reindex(common).pct_change() for t in prices}

    port_ret = pd.Series(0.0, index=common)
    prev_w   = None

    for i in range(len(common)):
        guard  = bool(signals["guard"].iloc[i])
        joint  = bool(signals["joint"].iloc[i])
        silver = signals["silver_state"].iloc[i]

        curr_w = joint_weights[silver] if joint else weights[(guard, silver)]

        if prev_w is not None and curr_w != prev_w:
            port_ret.iloc[i] -= rcs.tc_cost(prev_w, curr_w)

        r = sum(w * (rets[t].iloc[i] if not pd.isna(rets[t].iloc[i]) else 0.0)
                for t, w in curr_w.items())
        port_ret.iloc[i] += r
        prev_w = curr_w

    return (1 + port_ret).cumprod()


def main() -> None:
    print("=" * 72)
    print("Base weight grid x guard overlay -- 231 combinations, each with")
    print("the full guard + crash-trigger + silver + joint-stress overlay")
    print("=" * 72)

    gold_p   = rcs.load_prices("commodities", "GC_F")
    avgo_p   = rcs.load_prices("equities",    "AVGO")
    lly_p    = rcs.load_prices("equities",    "LLY")
    silver_p = rcs.load_prices("commodities", "SI_F")

    if any(p is None for p in [gold_p, avgo_p, lly_p, silver_p]):
        print("ERROR: missing price data")
        return

    common = (gold_p.index
              .intersection(avgo_p.index)
              .intersection(lly_p.index)
              .intersection(silver_p.index))
    common = common[common >= rcs.AVGO_IPO].sort_values()
    print(f"Common dates: {len(common)} ({common[0].date()} to {common[-1].date()})")

    prices = {"GC_F": gold_p, "AVGO": avgo_p, "LLY": lly_p, "SI_F": silver_p}
    signals = rcs.build_signals(avgo_p, gold_p, silver_p, lly_p, common)

    step = 5
    rows = []
    values = range(0, 101, step)

    print("\nRunning grid search (231 weight combinations x guard overlay)...")
    for g in values:
        for a in values:
            l = 100 - g - a
            if l < 0:
                continue
            gold_w, avgo_w, lly_w = g / 100, a / 100, l / 100
            weights, joint_weights = build_weight_tables(gold_w, avgo_w, lly_w)
            eq = run_strategy_variant(prices, signals, weights, joint_weights)
            m = rcs.perf(eq)
            rows.append({
                "gold": g, "avgo": a, "lly": l,
                **m,
                "label": f"Gold{g}/AVGO{a}/LLY{l}",
            })

    df = pd.DataFrame(rows)

    def print_top(title: str, col: str, n: int = 10) -> None:
        top = df.nlargest(n, col)
        print(f"\n{'='*72}")
        print(f"TOP {n} BY {title} (with guard overlay)")
        print(f"{'='*72}")
        print(f"  {'Weights':<28}  {'CAGR':>7}  {'Sharpe':>7}  {'MaxDD':>8}  {'Calmar':>7}")
        print(f"  {'-'*65}")
        for _, r in top.iterrows():
            print(f"  {r['label']:<28}  {r['cagr']:>7.2%}  {r['sharpe']:>7.3f}"
                  f"  {r['maxdd']:>8.2%}  {r['calmar']:>7.3f}")

    print_top("CAGR",   "cagr")
    print_top("SHARPE", "sharpe")
    print_top("CALMAR", "calmar")

    live = df[(df["gold"] == 25) & (df["avgo"] == 55) & (df["lly"] == 20)]
    if not live.empty:
        r = live.iloc[0]
        print(f"\n{'='*72}")
        print("LIVE STRATEGY (Gold25/AVGO55/LLY20) FOR COMPARISON")
        print(f"{'='*72}")
        print(f"  CAGR {r['cagr']:.2%}  Sharpe {r['sharpe']:.3f}  "
              f"MaxDD {r['maxdd']:.2%}  Calmar {r['calmar']:.3f}")
        print(f"  Rank by CAGR:   {int((df['cagr'] > r['cagr']).sum()) + 1} / {len(df)}")
        print(f"  Rank by Sharpe: {int((df['sharpe'] > r['sharpe']).sum()) + 1} / {len(df)}")
        print(f"  Rank by Calmar: {int((df['calmar'] > r['calmar']).sum()) + 1} / {len(df)}")

    OUT_CSV.parent.mkdir(exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")


if __name__ == "__main__":
    main()
