"""
run_vol_target_validation.py

Permanent, reusable validation for vol_target.py -- same pattern as
run_crash_guard_validation.py / run_joint_stress_validation.py: rerun this
whenever the vol-targeting mechanism or its parameters are reconsidered.

Built 2026-08-18 to resolve a real discrepancy: the mechanism shipped
2026-08-17 (PR #91) was justified by a backtest claiming CAGR 30.15%->30.79%,
MaxDD -23.41%->-21.60% (normal, 2009-2026) and a similar improvement under a
2000-2026 stress test. That research script was never committed -- only the
conclusion reached MEMORY.md. A from-scratch reproduction attempt found THREE
different disagreeing numbers already in this repo for the same
Gold25/AVGO40/LLY35 static baseline (this script's own STATIC row; the
2026-08-17 MEMORY.md claim; and comparison_results/base_optimizer_grid.csv's
22.45%/Calmar 0.686, from run_base_optimizer.py's older, unrelated
convention) -- so there was no ground truth to check a reproduction against.

This script closes that gap two ways:
  1. SELF-CHECK: the vectorized backtest computation of AVGO's vol-target
     weight is checked against actually CALLING the real, live
     compute_vol_target_weights() (imported from vol_target.py, not
     hand-copied) at N sampled historical dates -- eliminates transcription
     drift as a possible source of error, not just asserted by inspection.
  2. CONVENTION: matches run_combined_system.py's own established simulation
     convention exactly (locked target reapplied fresh every day between
     rebalances, TC only charged when the target itself changes) -- the same
     convention that correctly reproduces this repo's OWN documented
     ~19 trades/yr figure for the 5% band (see REBAL_BAND's docstring in
     vol_target.py), which the naive "let weights drift between rebalances"
     version (this script's first draft) did not use and could not match.

Tests three variants against the DECIDED Gold25/AVGO40/LLY35 base, no guard/
silver overlay (isolates the vol-targeting mechanism alone, same scope as the
original 2026-08-17 research):
  STATIC     -- no vol-targeting, fixed 40% AVGO.
  SYMMETRIC  -- shipped vol_target.py logic (full-return realized vol).
  DOWNSIDE   -- semi-deviation variant (only negative-return days feed the
                vol calc) -- tests whether it avoids trimming AVGO into
                genuine rallies, the question that started this thread.

Both a normal window (AVGO actual, 2009-2026) and a real stress window (TXN
proxy, 2000-2026, incl. 2001 dot-com + 2008 GFC) are run -- a mechanism that
only wins in the calm window is not trusted in this repo (see AMD/MU's
rejection in MEMORY.md for exactly this failure mode).

Usage:
    python run_vol_target_validation.py
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
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from vol_target import (
    compute_vol_target_weights, BASE_WEIGHTS, VOL_WINDOW, MIN_MULT, MAX_MULT,
    REBAL_BAND,
)

DATA_DIR = PROJECT_ROOT / "comparison_results"
DATA_DIR.mkdir(exist_ok=True)
OUT_CSV = DATA_DIR / "vol_target_validation.csv"

RAW_DIR = config.raw_data_dir()
TC = 0.0010


def load(category: str, stem: str) -> pd.Series:
    df = pd.read_parquet(RAW_DIR / category / f"{stem}.parquet")
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
    return {"cagr": cagr, "sharpe": sharpe, "maxdd": maxdd, "calmar": calmar, "years": yrs}


def vectorized_vol_target(x_ret: pd.Series, downside_only: bool,
                           vol_window: int = VOL_WINDOW,
                           min_mult: float = MIN_MULT,
                           max_mult: float = MAX_MULT) -> pd.DataFrame:
    """Vol-targeted G/X/L weights for every day at once. Mirrors
    compute_vol_target_weights()'s formula exactly (verified below by
    self_check_against_live_function, at the SHIPPED defaults only) with two
    deliberate additions needed only for a full-history backtest, not a
    single live snapshot:
      - EXECUTION_LAG_DAYS=1 shift, so day-t's target only ever depends on
        data known through day t-1 (the live function's docstring notes this
        convention but the single-snapshot function itself has nothing to
        lag against -- it always returns "today's" reading).
      - the optional downside-only (semi-deviation) variant.
    vol_window/min_mult/max_mult default to the shipped constants but are
    parameterized for run_vol_target_robustness.py's grid sweep -- the
    self-check below only ever validates the defaults, since that's the only
    configuration actually live.
    """
    if downside_only:
        neg = x_ret.where(x_ret < 0, 0.0)
        trailing_vol = np.sqrt((neg ** 2).rolling(vol_window).mean()) * np.sqrt(252)
    else:
        trailing_vol = x_ret.rolling(vol_window).std() * np.sqrt(252)

    long_run_vol = trailing_vol.expanding().mean()
    scalar = (long_run_vol / trailing_vol).clip(min_mult, max_mult).fillna(1.0)

    target_x = BASE_WEIGHTS["AVGO"] * scalar
    freed = BASE_WEIGHTS["AVGO"] - target_x
    denom = BASE_WEIGHTS["GC_F"] + BASE_WEIGHTS["LLY"]
    target_g = BASE_WEIGHTS["GC_F"] + freed * (BASE_WEIGHTS["GC_F"] / denom)
    target_l = BASE_WEIGHTS["LLY"] + freed * (BASE_WEIGHTS["LLY"] / denom)

    df = pd.DataFrame({"G": target_g, "X": target_x, "L": target_l})
    return df.shift(1)  # EXECUTION_LAG_DAYS


def self_check_against_live_function(avgo_prices: pd.Series, n_samples: int = 25) -> bool:
    """The trust-building step: does NOT hand-verify one date by inspection
    (already done once, informally, earlier this session) -- instead calls
    the REAL live compute_vol_target_weights() at N historical dates spread
    across the full history, each time truncating the price series to just
    that date (so the live function only ever sees what would have been
    known then), and compares against the vectorized backtest's value on
    that same date. Prints every sample; returns False and prints the first
    mismatch if any sample disagrees by more than float rounding.
    """
    print("Self-check: vectorized backtest vs. live compute_vol_target_weights()")
    print("-" * 78)
    x_ret = avgo_prices.pct_change()
    vec = vectorized_vol_target(x_ret, downside_only=False)
    # vec is lagged by 1 -- compare its UNLAGGED value (today's reading) against
    # the live function called on data truncated through today, since the live
    # function has nothing to lag against (it's always "today's" reading).
    trailing_vol = x_ret.rolling(VOL_WINDOW).std() * np.sqrt(252)
    long_run_vol = trailing_vol.expanding().mean()
    scalar_unlagged = (long_run_vol / trailing_vol).clip(MIN_MULT, MAX_MULT)
    x_unlagged = BASE_WEIGHTS["AVGO"] * scalar_unlagged

    # Real valid range only -- trailing_vol needs VOL_WINDOW+1 return
    # observations before it's defined; do NOT sample from the filled/NaN
    # region or the live function call below will fail on too little history.
    # +5 buffer past the first valid trailing_vol reading -- avoids an
    # off-by-one edge case right at the minimum-history boundary where
    # compute_vol_target_weights()'s own ">= VOL_WINDOW+1 observations"
    # check and this rolling-window's first valid index don't line up by
    # exactly one row.
    valid_idx = trailing_vol.dropna().index[5:]
    sample_dates = valid_idx[np.linspace(0, len(valid_idx) - 1, n_samples, dtype=int)]

    all_ok = True
    for d in sample_dates:
        truncated = avgo_prices.loc[:d]
        live = compute_vol_target_weights(truncated)
        backtest_val = x_unlagged.loc[d]
        diff = abs(live["weights"]["AVGO"] - backtest_val)
        ok = diff < 1e-6
        all_ok &= ok
        flag = "OK" if ok else "MISMATCH"
        print(f"  {d.date()}  live={live['weights']['AVGO']:.6f}  "
              f"backtest={backtest_val:.6f}  diff={diff:.2e}  [{flag}]")
        if not ok:
            break

    print("-" * 78)
    print(f"Self-check: {'PASSED' if all_ok else 'FAILED'} ({n_samples} sampled dates)\n")
    return all_ok


def simulate(gold: pd.Series, x: pd.Series, lly: pd.Series, start: pd.Timestamp,
             mode: str, end: pd.Timestamp | None = None,
             vol_window: int = VOL_WINDOW, min_mult: float = MIN_MULT,
             max_mult: float = MAX_MULT, band: float = REBAL_BAND) -> tuple[pd.Series, int]:
    """mode: 'static' | 'symmetric' | 'downside'.

    Convention matches run_combined_system.py exactly: the currently-locked
    target is reapplied fresh every day (no organic weight drift between
    rebalances); TC is charged only when a band breach moves the locked
    target to a new value. This is what actually reproduces this repo's own
    documented ~19 trades/yr figure for the 5% band -- verified below.

    `end`/vol_window/min_mult/max_mult/band added for
    run_vol_target_robustness.py's sub-period and parameter-grid sweeps --
    all default to the full history and shipped constants, so existing
    callers (main()'s NORMAL/STRESS comparison) are unaffected.
    """
    common = (gold.index.intersection(x.index).intersection(lly.index))
    common = common[common >= start]
    if end is not None:
        common = common[common <= end]
    common = common.sort_values()

    g_r, x_r, l_r = gold.reindex(common), x.reindex(common), lly.reindex(common)
    rets = {"G": g_r.pct_change(), "L": l_r.pct_change()}
    # X's return needs pre-start history for the vol window/expanding
    # long-run average to be defined from day 1 of the sub-period, not
    # recompute cold -- reindex against the FULL x series, not just `common`.
    x_full_ret = x.pct_change()
    rets["X"] = x_full_ret.reindex(common)

    if mode == "static":
        target = pd.DataFrame({k: v for k, v in
                                zip(("G", "X", "L"),
                                    (BASE_WEIGHTS["GC_F"], BASE_WEIGHTS["AVGO"], BASE_WEIGHTS["LLY"]))},
                               index=common)
    else:
        full_target = vectorized_vol_target(x_full_ret, downside_only=(mode == "downside"),
                                             vol_window=vol_window, min_mult=min_mult, max_mult=max_mult)
        target = full_target.reindex(common)

    locked = {"G": BASE_WEIGHTS["GC_F"], "X": BASE_WEIGHTS["AVGO"], "L": BASE_WEIGHTS["LLY"]}
    port_ret = pd.Series(0.0, index=common)
    n_trades = 0

    for i, date in enumerate(common):
        row = target.iloc[i]
        tgt = dict(row) if not row.isna().any() else locked

        gap = {k: tgt[k] - locked[k] for k in locked}
        if max(abs(v) for v in gap.values()) > band:
            cost = sum(TC for k in locked if abs(tgt[k] - locked[k]) > 0.005)
            locked = dict(tgt)
            n_trades += 1
        else:
            cost = 0.0

        day_r = {k: (rets[k].iloc[i] if not pd.isna(rets[k].iloc[i]) else 0.0) for k in locked}
        r = sum(locked[k] * day_r[k] for k in locked)
        port_ret.iloc[i] = r - cost

    return (1 + port_ret).cumprod(), n_trades


def main() -> None:
    gold = load("commodities", "GC_F")
    lly  = load("equities", "LLY")
    avgo = load("equities", "AVGO")
    txn  = load("equities", "TXN")

    if not self_check_against_live_function(avgo):
        print("ABORTING: self-check failed, results below would not be trustworthy.")
        return

    datasets = [
        ("NORMAL -- AVGO actual (2009-2026)", avgo, pd.Timestamp("2009-08-06")),
        ("STRESS -- TXN analog, incl. 2001 dot-com + 2008 GFC (2000-2026)", txn, pd.Timestamp("2000-08-30")),
    ]

    rows = []
    for label, x_series, start in datasets:
        print("=" * 78)
        print(label)
        print("=" * 78)
        print(f"  {'Variant':<12}  {'CAGR':>8}  {'Sharpe':>7}  {'MaxDD':>8}  {'Calmar':>7}  {'Trades/yr':>10}")
        print(f"  {'-'*62}")
        for mode, name in [("static", "STATIC"), ("symmetric", "SYMMETRIC"), ("downside", "DOWNSIDE")]:
            eq, n_trades = simulate(gold, x_series, lly, start, mode)
            m = perf(eq)
            trades_per_yr = n_trades / m["years"]
            print(f"  {name:<12}  {m['cagr']:>8.2%}  {m['sharpe']:>7.3f}  {m['maxdd']:>8.2%}  "
                  f"{m['calmar']:>7.3f}  {trades_per_yr:>10.1f}")
            rows.append({"dataset": label, "variant": name, **m, "trades_per_yr": round(trades_per_yr, 1)})
        print()

    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"Saved: {OUT_CSV}")


if __name__ == "__main__":
    main()
