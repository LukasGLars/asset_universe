"""
run_vol_target_robustness.py

Follow-up to run_vol_target_validation.py: that script established the vol
formula is bit-exact vs. the live compute_vol_target_weights() (self-check,
0.00e+00 diff), and that at the SHIPPED parameters, SYMMETRIC vol-targeting
loses to STATIC on CAGR/Sharpe/Calmar in both the 2009-2026 normal window and
the 2000-2026 TXN stress window.

That alone does not prove the mechanism has no value -- two real confounds
were flagged and neither was tested:

  1. STATIC beating any trim-the-winner mechanism is close to guaranteed
     whenever the trimmed asset happens to be the best performer over the
     exact test window. AVGO's 2023-2026 stretch was an exceptional,
     concentrated rally -- if that's what's driving STATIC's win, the result
     says nothing about whether vol-targeting helps in a normal regime.
  2. Only ONE parameterization (21d window, 0.3-1.3x clip, 5% band) was
     tested. A result that only looks bad at one specific setting and
     reverses nearby is a fragile finding, not a robust one -- same standard
     already applied to the AVGO guard (20-cell grid) and the crash trigger
     (20-cell grid) before either was trusted.

This script closes both gaps, same rigor bar, before any live-system
decision gets made:

  A. SUB-PERIOD TEST -- same anti-fitting method as the 2026-08-16 base-mix
     research (project_reactor_core_mix.md): rank on the WORST sub-period,
     never full-sample. Splits AVGO into two halves, and separately isolates
     the 2023-2026 AI-melt-up from everything before it, to see directly
     whether excluding that one stretch changes the verdict. Splits TXN into
     two halves so the dot-com/GFC crisis era is isolated from the modern
     era.
  B. PARAMETER GRID -- VOL_WINDOW x REBAL_BAND swept (clip bounds held at
     the shipped 0.3x-1.3x, since that wasn't the confound in question), on
     both datasets, for the shipped SYMMETRIC variant. Reports what fraction
     of the grid actually beats static on Calmar.

Usage:
    python run_vol_target_robustness.py
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

import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from run_vol_target_validation import (
    load, perf, simulate, self_check_against_live_function, vectorized_vol_target,
)

OUT_CSV = PROJECT_ROOT / "comparison_results" / "vol_target_robustness.csv"


BASE_D = {"G": 0.25, "X": 0.40, "L": 0.35}
TC = 0.0010


def simulate_real_drift(gold, x, lly, start, band, mode, end=None, vol_window=21):
    """REALISTIC rebalance convention -- held weights actually DRIFT with
    prices, and are only pulled back to the current target when that drift
    exceeds `band`.

    This exists because the convention inherited from run_combined_system.py
    (and used by run_vol_target_validation.simulate) reapplies the locked
    target fresh EVERY day regardless of drift, charging TC only when the
    target itself changes. For a fixed static target that silently means
    FREE DAILY REBALANCING -- verified 2026-08-18: static under that
    convention scores CAGR 30.58% with TC forced to zero, i.e. identical to
    its headline 30.64%, because it never pays a cost at all. That flattered
    static by ~1.6pp CAGR against any moving-target strategy, which does pay.

    Here the mechanics are IDENTICAL for both modes -- same drift, same band,
    same TC -- so the only difference is what the target is. That is the
    apples-to-apples comparison.
    """
    common = (gold.index.intersection(x.index).intersection(lly.index))
    common = common[common >= start]
    if end is not None:
        common = common[common <= end]
    common = common.sort_values()

    rets = {"G": gold.reindex(common).pct_change(), "L": lly.reindex(common).pct_change()}
    x_full_ret = x.pct_change()
    rets["X"] = x_full_ret.reindex(common)

    if mode == "static":
        tgt_df = pd.DataFrame({k: BASE_D[k] for k in BASE_D}, index=common)
    else:
        tgt_df = vectorized_vol_target(x_full_ret, downside_only=(mode == "downside"),
                                        vol_window=vol_window).reindex(common)

    held = dict(BASE_D)
    pr = pd.Series(0.0, index=common)
    n = 0
    for i, _d in enumerate(common):
        row = tgt_df.iloc[i]
        tgt = dict(row) if not row.isna().any() else dict(BASE_D)
        gap = {k: tgt[k] - held[k] for k in held}
        if max(abs(v) for v in gap.values()) > band:
            pr.iloc[i] -= sum(TC for k in held if abs(tgt[k] - held[k]) > 0.005)
            n += 1
            held = dict(tgt)
        dr = {k: (rets[k].iloc[i] if not pd.isna(rets[k].iloc[i]) else 0.0) for k in held}
        pr.iloc[i] += sum(held[k] * dr[k] for k in held)
        nv = {k: held[k] * (1 + dr[k]) for k in held}
        t = sum(nv.values())
        held = {k: v / t for k, v in nv.items()} if t > 0 else held
    return (1 + pr).cumprod(), n


def sub_period_test(gold, x, lly, periods: list[tuple[str, pd.Timestamp, pd.Timestamp]]) -> list[dict]:
    rows = []
    for label, start, end in periods:
        for mode in ("static", "symmetric", "downside"):
            eq, n_trades = simulate(gold, x, lly, start, mode, end=end)
            m = perf(eq)
            rows.append({"period": label, "variant": mode.upper(), **m,
                         "trades_per_yr": round(n_trades / m["years"], 1) if m["years"] > 0 else 0})
    return rows


def print_period_table(rows: list[dict], periods: list[str]) -> None:
    for p in periods:
        sub = [r for r in rows if r["period"] == p]
        if not sub:
            continue
        print(f"\n  {p}")
        print(f"    {'Variant':<12}  {'CAGR':>8}  {'MaxDD':>8}  {'Calmar':>7}  {'Trades/yr':>10}")
        for r in sub:
            print(f"    {r['variant']:<12}  {r['cagr']:>8.2%}  {r['maxdd']:>8.2%}  "
                  f"{r['calmar']:>7.3f}  {r['trades_per_yr']:>10.1f}")


def param_grid(gold, x, lly, start: pd.Timestamp, label: str) -> list[dict]:
    rows = []
    windows = [10, 15, 21, 30, 42]
    bands = [0.03, 0.05, 0.08]
    for vw in windows:
        for band in bands:
            eq_static, _ = simulate(gold, x, lly, start, "static")
            m_static = perf(eq_static)
            eq_sym, n_trades = simulate(gold, x, lly, start, "symmetric", vol_window=vw, band=band)
            m_sym = perf(eq_sym)
            rows.append({
                "dataset": label, "vol_window": vw, "band": band,
                "static_calmar": round(m_static["calmar"], 3),
                "symmetric_calmar": round(m_sym["calmar"], 3),
                "symmetric_cagr": round(m_sym["cagr"], 4),
                "symmetric_maxdd": round(m_sym["maxdd"], 4),
                "beats_static": m_sym["calmar"] > m_static["calmar"],
                "trades_per_yr": round(n_trades / m_sym["years"], 1),
            })
    return rows


def main() -> None:
    gold = load("commodities", "GC_F")
    lly  = load("equities", "LLY")
    avgo = load("equities", "AVGO")
    txn  = load("equities", "TXN")

    if not self_check_against_live_function(avgo):
        print("ABORTING: self-check failed.")
        return

    print("=" * 78)
    print("A. SUB-PERIOD TEST -- rank on worst sub-period, never full-sample")
    print("=" * 78)

    avgo_end = avgo.index.max()
    avgo_mid = pd.Timestamp("2017-10-01")  # roughly bisects 2009-08-06..avgo_end by time
    ai_era_start = pd.Timestamp("2023-01-01")

    avgo_periods = [
        ("AVGO half 1 (2009-2017)", pd.Timestamp("2009-08-06"), avgo_mid),
        ("AVGO half 2 (2017-2026)", avgo_mid, avgo_end),
        ("AVGO pre-AI-melt-up (2009-2022)", pd.Timestamp("2009-08-06"), pd.Timestamp("2022-12-31")),
        ("AVGO AI-melt-up ONLY (2023-2026)", ai_era_start, avgo_end),
    ]
    rows = sub_period_test(gold, avgo, lly, avgo_periods)
    print_period_table(rows, [p[0] for p in avgo_periods])

    txn_end = txn.index.max()
    txn_mid = pd.Timestamp("2013-08-01")
    txn_periods = [
        ("TXN half 1, incl. dot-com+GFC (2000-2013)", pd.Timestamp("2000-08-30"), txn_mid),
        ("TXN half 2, modern era (2013-2026)", txn_mid, txn_end),
    ]
    rows += sub_period_test(gold, txn, lly, txn_periods)
    print_period_table(rows, [p[0] for p in txn_periods])

    print("\n" + "=" * 78)
    print("B. PARAMETER GRID -- VOL_WINDOW x REBAL_BAND, SYMMETRIC vs STATIC (Calmar)")
    print("=" * 78)

    grid_rows = param_grid(gold, avgo, lly, pd.Timestamp("2009-08-06"), "NORMAL (AVGO)")
    grid_rows += param_grid(gold, txn, lly, pd.Timestamp("2000-08-30"), "STRESS (TXN)")

    for label in ("NORMAL (AVGO)", "STRESS (TXN)"):
        sub = [r for r in grid_rows if r["dataset"] == label]
        n_beat = sum(1 for r in sub if r["beats_static"])
        print(f"\n  {label}: SYMMETRIC beats STATIC on Calmar in {n_beat}/{len(sub)} grid cells")
        print(f"    {'VOL_WIN':>8}  {'BAND':>6}  {'Static':>8}  {'Symm':>8}  {'Beats?':>7}  {'Trades/yr':>10}")
        for r in sub:
            flag = "YES" if r["beats_static"] else "no"
            print(f"    {r['vol_window']:>8}  {r['band']:>6.0%}  {r['static_calmar']:>8.3f}  "
                  f"{r['symmetric_calmar']:>8.3f}  {flag:>7}  {r['trades_per_yr']:>10.1f}")

    print("\n" + "=" * 78)
    print("C. APPLES-TO-APPLES -- realistic weight drift, identical mechanics both modes")
    print("=" * 78)
    print("  (sections A/B above inherit run_combined_system.py's convention, which")
    print("   silently gives a FIXED target free daily rebalancing -- see")
    print("   simulate_real_drift's docstring. This section removes that advantage.)")

    drift_rows = []
    for label, x_series, start in [("NORMAL (AVGO 2009-2026)", avgo, pd.Timestamp("2009-08-06")),
                                     ("STRESS (TXN 2000-2026)", txn, pd.Timestamp("2000-08-30"))]:
        print(f"\n  === {label} ===")
        print(f"    {'Band':>5}  {'Mode':<10}  {'CAGR':>8}  {'Sharpe':>7}  {'MaxDD':>8}  {'Calmar':>7}  {'Tr/yr':>6}")
        for b in (0.03, 0.05, 0.08, 0.15):
            for mode in ("static", "symmetric"):
                eq, n = simulate_real_drift(gold, x_series, lly, start, b, mode)
                m = perf(eq)
                print(f"    {b:>4.0%}  {mode:<10}  {m['cagr']:>8.2%}  {m['sharpe']:>7.3f}  "
                      f"{m['maxdd']:>8.2%}  {m['calmar']:>7.3f}  {n/m['years']:>6.1f}")
                drift_rows.append({"dataset": label, "band": b, "mode": mode, **m,
                                    "trades_per_yr": round(n / m["years"], 1)})
            print()

    pd.DataFrame(rows).to_csv(OUT_CSV.with_name("vol_target_subperiods.csv"), index=False)
    pd.DataFrame(grid_rows).to_csv(OUT_CSV, index=False)
    pd.DataFrame(drift_rows).to_csv(OUT_CSV.with_name("vol_target_realistic_drift.csv"), index=False)
    print(f"\nSaved: {OUT_CSV}")
    print(f"Saved: {OUT_CSV.with_name('vol_target_subperiods.csv')}")
    print(f"Saved: {OUT_CSV.with_name('vol_target_realistic_drift.csv')}")


if __name__ == "__main__":
    main()
