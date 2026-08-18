"""
run_clean_sheet_search.py

"Is there a better combination of assets than Gold/AVGO/LLY?" -- asked
properly for the first time. Every previous search in this repo perturbed
the incumbent: run_base_optimizer gridded weights across the same three
names, run_lly_substitution swapped one slot, the 4th-asset work added to
the existing three. None asked the clean-sheet question.

THE OVERFITTING PROBLEM IS THE WHOLE DIFFICULTY. The universe was assembled
with 2026 hindsight, so an unconstrained optimiser will hand back whatever
had the best realised path and call it optimal. This repo has already been
burned twice -- the walk-forward optimiser lost to plain equal-weight, and
the universe-frequency study found nothing stable enough to anchor on.

So the search is deliberately crippled:
  1. Candidates must be ROBUST diversity (rules out the THIN recent
     high-fliers that top the screen -- SNDK/APP/HOOD/PLTR all <6yr) and
     must have data back to the in-sample start.
  2. Weights are SELECTED on 2009-2017 and JUDGED on 2018-2026. The search
     never sees the period it is graded on.
  3. The incumbent is force-included in the pool and always reported, so
     "we beat the incumbent" is measured, not assumed.

A combination only counts if it beats the incumbent OUT of sample. Winning
in-sample is expected and means nothing.
"""
from __future__ import annotations

import sys, warnings, itertools
from pathlib import Path

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
import run_combined_system as rcs

IS_START, IS_END = "2009-08-06", "2017-12-31"   # AVGO's history starts 2009
OOS_START, OOS_END = "2018-01-01", "2026-12-31"
INCUMBENT = {"GC_F": 0.25, "AVGO": 0.40, "LLY": 0.35}
TOP_N_POOL = 35          # individually-best in-sample names to combine
MIN_W, W_STEP = 0.10, 0.10
REBAL_BAND = 0.10


def weight_grid(k: int) -> list[tuple[float, ...]]:
    steps = int(round(1 / W_STEP))
    lo = int(round(MIN_W / W_STEP))
    out = []
    for combo in itertools.product(range(lo, steps + 1), repeat=k):
        if sum(combo) == steps:
            out.append(tuple(c * W_STEP for c in combo))
    return out


def load_pool() -> dict[str, pd.Series]:
    scr = pd.read_csv("universe_screen_results.csv")
    scr = scr[scr.diversity == "ROBUST"]
    cats = {"US Equity": "equities", "Swedish": "se_equities", "Commodity": "commodities"}
    out: dict[str, pd.Series] = {}
    for _, r in scr.iterrows():
        cat = cats.get(r["category"])
        if cat is None:
            continue
        stem = str(r["ticker"]).replace(".", "_").replace("-", "_")
        s = rcs.load_prices(cat, stem)
        if s is None:
            s = rcs.load_prices(cat, str(r["ticker"]))
        if s is None or len(s) == 0:
            continue
        if s.index[0] > pd.Timestamp(IS_START):
            continue
        out[str(r["ticker"])] = s
    for t, c in (("GC_F", "commodities"), ("AVGO", "equities"), ("LLY", "equities")):
        if t not in out:
            s = rcs.load_prices(c, t)
            if s is not None:
                out[t] = s
    return out


def metrics(rets: np.ndarray, w: np.ndarray, years: float) -> tuple[float, float]:
    """Banded-rebalance portfolio: approximated by fixed-weight daily blend,
    which is what the incumbent's own band converges to over long windows."""
    port = rets @ w
    eq = np.cumprod(1.0 + port)
    dd = eq / np.maximum.accumulate(eq) - 1.0
    cagr = eq[-1] ** (1 / years) - 1.0
    return cagr, dd.min()


def main():
    pool = load_pool()
    print(f"Pool after ROBUST + history filter: {len(pool)} assets")

    px = pd.DataFrame(pool).sort_index()
    px = px.ffill().dropna(how="any")
    is_px = px.loc[IS_START:IS_END]
    oos_px = px.loc[OOS_START:OOS_END]
    print(f"  in-sample  {is_px.index[0].date()} -> {is_px.index[-1].date()}  ({len(is_px)} days)")
    print(f"  out-sample {oos_px.index[0].date()} -> {oos_px.index[-1].date()}  ({len(oos_px)} days)")

    is_r = is_px.pct_change().dropna()
    oos_r = oos_px.pct_change().dropna()
    is_yrs = len(is_r) / 252
    oos_yrs = len(oos_r) / 252

    # --- individual in-sample Calmar to build the combination pool ---
    singles = []
    for t in is_r.columns:
        c, d = metrics(is_r[[t]].values, np.array([1.0]), is_yrs)
        singles.append((t, c, d, c / abs(d) if d < 0 else 0.0))
    singles.sort(key=lambda x: -x[3])
    names = [s[0] for s in singles[:TOP_N_POOL]]
    for t in INCUMBENT:
        if t not in names:
            names.append(t)
    print(f"  combination pool: {len(names)} names (top {TOP_N_POOL} by in-sample Calmar + incumbent)")

    grid = weight_grid(3)
    isr = is_r[names].values
    osr = oos_r[names].values
    idx = {n: i for i, n in enumerate(names)}

    results = []
    for trio in itertools.combinations(range(len(names)), 3):
        sub_is = isr[:, trio]
        for w in grid:
            wa = np.array(w)
            c, d = metrics(sub_is, wa, is_yrs)
            if d < 0:
                results.append((trio, w, c / abs(d), c, d))
    results.sort(key=lambda x: -x[2])
    print(f"  evaluated {len(results):,} portfolios in-sample")

    inc_idx = tuple(idx[t] for t in INCUMBENT)
    inc_w = np.array(list(INCUMBENT.values()))
    ic_is, id_is = metrics(isr[:, inc_idx], inc_w, is_yrs)
    ic_os, id_os = metrics(osr[:, inc_idx], inc_w, oos_yrs)

    print("\n=== INCUMBENT  Gold 25 / AVGO 40 / LLY 35 ===")
    print(f"  in-sample  CAGR {ic_is:+.1%}  MaxDD {id_is:+.1%}  Calmar {ic_is/abs(id_is):.3f}")
    print(f"  out-sample CAGR {ic_os:+.1%}  MaxDD {id_os:+.1%}  Calmar {ic_os/abs(id_os):.3f}")

    print("\n=== TOP 15 IN-SAMPLE, EVALUATED OUT OF SAMPLE ===")
    print(f"  {'assets':<26}{'weights':<20}{'IS Cal':>8}{'OOS CAGR':>10}{'OOS DD':>9}{'OOS Cal':>9}  beats?")
    beat = 0
    for trio, w, cal_is, _, _ in results[:15]:
        c, d = metrics(osr[:, trio], np.array(w), oos_yrs)
        cal = c / abs(d) if d < 0 else 0.0
        tag = "YES" if cal > ic_os / abs(id_os) else "no"
        beat += tag == "YES"
        nm = "/".join(names[i] for i in trio)
        wt = "/".join(f"{x:.0%}" for x in w)
        print(f"  {nm:<26}{wt:<20}{cal_is:>8.2f}{c:>10.1%}{d:>9.1%}{cal:>9.3f}  {tag}")

    n_top = 100
    survivors = 0
    for trio, w, _, _, _ in results[:n_top]:
        c, d = metrics(osr[:, trio], np.array(w), oos_yrs)
        if d < 0 and c / abs(d) > ic_os / abs(id_os):
            survivors += 1
    print(f"\n  Of the top {n_top} in-sample portfolios, {survivors} beat the incumbent "
          f"out of sample ({survivors/n_top:.0%}).")
    print("  Chance alone would give roughly the incumbent's own OOS percentile.")

    pd.DataFrame([{"assets": "/".join(names[i] for i in t),
                   "weights": "/".join(f"{x:.0%}" for x in w),
                   "is_calmar": cal} for t, w, cal, _, _ in results[:500]]
                 ).to_csv(PROJECT_ROOT / "comparison_results" / "clean_sheet_search.csv", index=False)


if __name__ == "__main__":
    main()
