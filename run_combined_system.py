"""
run_combined_system.py

Complete integrated system backtest.

Layers:
  1. Base          : Gold 25%, AVGO 55%, LLY 20%
  2. AVGO 200d guard: AVGO < 200d SMA → Gold 52.5%, AVGO 0%, LLY 47.5%
  3. Silver tactical: T1/T2 adds funded from AVGO (base) or Gold (guard)

Priority rule (guard + silver simultaneous):
  Silver funded from AVGO in base mode, from Gold in guard mode.

Weight table:
  Base          : Gold 25%   AVGO 55%  LLY 20%   Silver 0%
  Base + T1     : Gold 25%   AVGO 43%  LLY 20%   Silver 12%
  Base + T2     : Gold 25%   AVGO 38%  LLY 20%   Silver 17%
  Guard         : Gold 52.5% AVGO 0%   LLY 47.5% Silver 0%
  Guard + T1    : Gold 40.5% AVGO 0%   LLY 47.5% Silver 12%
  Guard + T2    : Gold 35.5% AVGO 0%   LLY 47.5% Silver 17%

Silver state machine:
  INACTIVE → T1/T2 when GSR >= threshold AND fallen >=5% from 60d peak
  T1/T2    → INACTIVE when GSR < 62.56 (cycle-complete exit)

Comparison strategies:
  A. Static base only
  B. Base + AVGO guard only
  C. Base + silver tactical only
  D. Base + guard + silver (combined system)

TC: 10bps per asset per transition.
Output: comparison_results/combined_system.csv
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    # Windows console UTF-8 wrapping -- only when run directly. Doing this
    # at import time breaks pytest's stdout/stderr capture for anything
    # that imports this module (e.g. tests/test_crash_guard.py).
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "combined_system.csv"

# ── Thresholds ────────────────────────────────────────────────────────────────
AVGO_MA          = 200
GSR_T1           = 83.36
GSR_T2           = 86.45
GSR_EXIT         = 62.56
GSR_PEAK_WINDOW  = 60
GSR_PEAK_FALL    = 0.05
TC               = 0.0010
AVGO_IPO         = pd.Timestamp("2009-08-06")
OOS_START        = pd.Timestamp("2020-01-01")

# Crash guard (2026-07-02): the 200d SMA guard is a lagging indicator -- it
# can't react to a fast, sharp break (2001 dot-com: -35.3% MaxDD even with
# the guard active, per the TXN analog test, since a violent move can blow
# through the SMA cross before it triggers). This is an early-activation
# layer on the SAME guard, not a separate strategy: if AVGO drops more than
# CRASH_ROC_THRESHOLD over CRASH_ROC_WINDOW trading days, the guard fires
# immediately regardless of where price sits vs the 200d SMA. Re-entry is
# unchanged -- still governed by price closing back above the 200d SMA,
# since the ROC condition self-clears once the rolling window recovers
# (confirmed empirically: only a handful of standalone ROC-triggered days
# in both the TXN-analog and AVGO backtests, not sustained periods).
# Validated via a 20-cell parameter grid (window x threshold) against both
# AVGO's own history and a TXN analog (2000-2026, includes 2001 and 2008) --
# every cell matched or beat the SMA-only guard on both datasets.
CRASH_ROC_WINDOW    = 5
CRASH_ROC_THRESHOLD = -0.10

# Bars between a signal being observable and the position actually changing.
# Signals come from closing prices, so the earliest any trade can happen is
# the next session -- 1 is the most generous *honest* value, not a
# conservative padding. Added 2026-08-16 after every guard backtest was found
# to be trading on the same close that generated its signal; see
# apply_execution_lag() for the measured impact.
EXECUTION_LAG_DAYS = 1

# Joint-stress escalation (2026-07-02): the guard alone assumes LLY is a
# reliable diversifier whenever AVGO is stressed, but that correlation is
# regime-dependent -- it holds in liquidity crashes (COVID) and breaks down
# in macro/trade-driven selloffs (2022 rate hikes, 2025 tariffs), where LLY
# fell alongside or worse than AVGO. When LLY independently trips the SAME
# already-validated guard logic (200d SMA / 5d-(-10%) ROC -- no new
# parameters) at the same time AVGO's guard is active, that's the signature
# of the diversification actually breaking down, not just AVGO having a bad
# day. Escalate fully into Gold rather than splitting into LLY, which is no
# longer diversifying in that state.
# Validated via a TXN analog (2000-2026, includes 2001 dot-com + 2008 GFC)
# plus AVGO's own history: monotonic improvement with more Gold (not a
# curve-fit interior spike), best at 100%. See run_joint_stress_validation.py.
#   AVGO actual:  Calmar 2.407 (guard alone) -> 2.957 (100% Gold escalation)
#   TXN analog:   Calmar 0.824 (guard alone) -> 1.028 (100% Gold escalation)
LLY_MA = 200

# ── Weight table ──────────────────────────────────────────────────────────────
# Base moved from Gold25/AVGO55/LLY20 to Gold25/AVGO40/LLY35 on 2026-08-16.
# Rationale (see MEMORY.md, "DECIDED 2026-08-16"): with the guard retired the
# mix IS the risk control, and AVGO at 55% had the worst Calmar in all four
# sub-periods tested plus the worst single-name shock exposure -- a -50% AVGO
# move alone cost ~25% of TPV. LLY at 35% ranked 1 of 4,991 alternatives for
# its slot, tested with equal-weight splits so no weight-fitting was possible.
# Result: CAGR 32.6% -> 30.6%, MaxDD -30.5% -> -23.5%, Calmar 1.068 -> 1.31.
#
# Silver T1/T2 still funded from AVGO, same mechanism as before (+12% / +17%).
# The guard-active rows are RETIRED for live use (fi_tracker.py never selects
# them, see PR #89) and kept only so the backtests in this module can still
# reproduce PR #88's honest guarded-vs-unguarded comparison.
WEIGHTS: dict[tuple[bool, str], dict[str, float]] = {
    (False, "INACTIVE"): {"GC_F": 0.250, "AVGO": 0.400, "LLY": 0.350, "SI_F": 0.000},
    (False, "T1"):       {"GC_F": 0.250, "AVGO": 0.280, "LLY": 0.350, "SI_F": 0.120},
    (False, "T2"):       {"GC_F": 0.250, "AVGO": 0.230, "LLY": 0.350, "SI_F": 0.170},
    # Guard-active rows follow the base: AVGO's weight splits evenly into Gold
    # and LLY (0.25 + 0.40/2 = 0.45, 0.35 + 0.40/2 = 0.55), silver funded from
    # Gold. Re-derived from the new base so a guarded-vs-unguarded backtest
    # still compares like with like; the previous 0.525/0.475 rows were the
    # same construction applied to the old 55% AVGO. Note PR #88's published
    # figures were computed at the OLD 25/55/20 base -- rerun to compare at
    # the current one.
    (True,  "INACTIVE"): {"GC_F": 0.450, "AVGO": 0.000, "LLY": 0.550, "SI_F": 0.000},
    (True,  "T1"):       {"GC_F": 0.330, "AVGO": 0.000, "LLY": 0.550, "SI_F": 0.120},
    (True,  "T2"):       {"GC_F": 0.280, "AVGO": 0.000, "LLY": 0.550, "SI_F": 0.170},
}

# Joint-stress override: guard active AND LLY independently stressed -> full
# flight to Gold (silver funded from Gold, not AVGO, since AVGO is already 0).
JOINT_WEIGHTS: dict[str, dict[str, float]] = {
    "INACTIVE": {"GC_F": 1.000, "AVGO": 0.000, "LLY": 0.000, "SI_F": 0.000},
    "T1":       {"GC_F": 0.880, "AVGO": 0.000, "LLY": 0.000, "SI_F": 0.120},
    "T2":       {"GC_F": 0.830, "AVGO": 0.000, "LLY": 0.000, "SI_F": 0.170},
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
    lly_p: pd.Series,
    common: pd.DatetimeIndex,
) -> pd.DataFrame:
    """
    Build daily guard, LLY-stress, and silver state signals.
    Returns DataFrame with columns: guard, guard_ma, guard_crash, lly_stress,
    joint, silver_state
    """
    avgo_r   = avgo_p.reindex(common)
    sma200   = avgo_r.rolling(AVGO_MA).mean()
    guard_ma = (avgo_r < sma200).fillna(False)

    roc            = avgo_r.pct_change(CRASH_ROC_WINDOW)
    guard_crash    = (roc <= CRASH_ROC_THRESHOLD).fillna(False)
    guard          = guard_ma | guard_crash

    # LLY-stress: same validated guard logic (200d SMA / 5d ROC), reused
    # as-is -- checks whether LLY independently trips it too, not a new fit.
    lly_r        = lly_p.reindex(common)
    lly_sma200   = lly_r.rolling(LLY_MA).mean()
    lly_ma       = (lly_r < lly_sma200).fillna(False)
    lly_roc      = lly_r.pct_change(CRASH_ROC_WINDOW)
    lly_crash    = (lly_roc <= CRASH_ROC_THRESHOLD).fillna(False)
    lly_stress   = lly_ma | lly_crash
    joint        = guard & lly_stress

    gold_r   = gold_p.reindex(common)
    silv_r   = silver_p.reindex(common)
    gsr      = (gold_r / silv_r).dropna()
    gsr      = gsr.reindex(common)
    peak_60d = gsr.rolling(GSR_PEAK_WINDOW).max()
    fall_pct = (peak_60d - gsr) / peak_60d.replace(0, np.nan)

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
        if state in ("T1", "T2") and gsr_val < GSR_EXIT:
            state = "INACTIVE"

        # Entry check (only from INACTIVE)
        if state == "INACTIVE":
            fallen = fall_val >= GSR_PEAK_FALL
            if gsr_val >= GSR_T2 and fallen:
                state = "T2"
            elif gsr_val >= GSR_T1 and fallen:
                state = "T1"

        silver_states.append(state)

    signals = pd.DataFrame({
        "guard":        guard.values,
        "guard_ma":     guard_ma.values,
        "guard_crash":  guard_crash.values,
        "lly_stress":   lly_stress.values,
        "joint":        joint.values,
        "silver_state": silver_states,
    }, index=common)

    return apply_execution_lag(signals)


def apply_execution_lag(signals: pd.DataFrame) -> pd.DataFrame:
    """Shift every signal forward by EXECUTION_LAG_DAYS bars.

    Every signal in build_signals() is derived from a CLOSING price, so the
    earliest a position can actually change is the NEXT session -- you cannot
    observe a close and trade at that same close. Without this lag the
    simulation buys and sells at the very print that generates the signal.

    This is not a cosmetic correction. Measured 2026-08-16 on AVGO's real
    history: mean AVGO return on the 99 days the guard flips defensive is
    -3.46%, and on the day after it is +0.01%. Same-day accounting therefore
    credited the strategy with roughly 651 percentage points of raw AVGO
    return that no one could have traded, and it was the entire source of the
    guard's apparent edge (Calmar 2.99 same-day vs 0.49 lagged, against 1.06
    for the unguarded base). See MEMORY.md, 2026-08-16.

    Kept as a separate, named function so the assumption is explicit and
    directly testable rather than buried in a `.shift()` call.
    """
    lagged = signals.shift(EXECUTION_LAG_DAYS)

    # Restore dtypes: shifting introduces NaN in the first row(s). Default to
    # the non-acting state -- no guard, no stress, silver inactive -- since on
    # day one there is no prior close to have acted on.
    # `.eq(True)` rather than `.fillna(False).astype(bool)`: shifting promotes
    # a bool column to object with NaN in the gap, and bool(nan) is True --
    # which would silently turn a missing signal into an ACTIVE guard. eq()
    # maps NaN to False and restores real bool dtype in one step, with no
    # object-downcasting FutureWarning.
    for col in ("guard", "guard_ma", "guard_crash", "lly_stress", "joint"):
        lagged[col] = lagged[col].eq(True)
    lagged["silver_state"] = lagged["silver_state"].fillna("INACTIVE")

    return lagged


def run_strategy(
    prices: dict[str, pd.Series],
    signals: pd.DataFrame,
    use_guard: bool,
    use_silver: bool,
    label: str,
    use_joint: bool = False,
) -> tuple[pd.Series, list[dict]]:
    """
    Simulate portfolio using given signal flags.
    Returns (equity curve, list of state change events).
    """
    common = signals.index
    rets   = {t: prices[t].reindex(common).pct_change() for t in prices}

    port_ret = pd.Series(0.0, index=common)
    prev_w   = None
    events   = []

    for i, date in enumerate(common):
        guard  = bool(signals["guard"].iloc[i])  if use_guard  else False
        joint  = bool(signals["joint"].iloc[i])  if (use_guard and use_joint) else False
        silver = signals["silver_state"].iloc[i]  if use_silver else "INACTIVE"

        curr_w = JOINT_WEIGHTS[silver] if joint else WEIGHTS[(guard, silver)]

        # TC on weight change
        if prev_w is not None and curr_w != prev_w:
            cost = tc_cost(prev_w, curr_w)
            port_ret.iloc[i] -= cost
            events.append({
                "date":   date,
                "guard":  guard,
                "silver": silver,
                "label":  label,
            })

        # Portfolio return
        r = sum(w * (rets[t].iloc[i] if not pd.isna(rets[t].iloc[i]) else 0.0)
                for t, w in curr_w.items())
        port_ret.iloc[i] += r
        prev_w = curr_w

    return (1 + port_ret).cumprod(), events


def yearly_breakdown(equity: pd.Series, label: str) -> None:
    for yr in sorted(equity.index.year.unique()):
        eq_yr = equity[equity.index.year == yr]
        if len(eq_yr) < 2:
            continue
        ret  = float(eq_yr.iloc[-1] / eq_yr.iloc[0] - 1)
        dd   = eq_yr / eq_yr.cummax() - 1
        mdd  = float(dd.min())
        oos  = "*" if yr >= OOS_START.year else " "
        print(f"    {yr}{oos}  {ret:+.1%}  (MaxDD {mdd:+.1%})")


def main() -> None:
    print("=" * 70)
    print("Combined System Backtest — All Layers Integrated")
    print("  A: Static base | B: +Guard | C: +Silver | D: +Guard +Silver")
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

    # ── Build signals ──────────────────────────────────────────────────────────
    print("\nBuilding signals...")
    signals = build_signals(avgo_p, gold_p, silver_p, lly_p, common)

    guard_days   = signals["guard"].sum()
    crash_only   = int((signals["guard_crash"] & ~signals["guard_ma"]).sum())
    t1_days      = (signals["silver_state"] == "T1").sum()
    t2_days      = (signals["silver_state"] == "T2").sum()
    both_days    = (signals["guard"] & (signals["silver_state"] != "INACTIVE")).sum()
    joint_days   = signals["joint"].sum()

    print(f"  Guard active    : {guard_days} days ({guard_days/len(common):.0%})")
    print(f"    of which crash-only (ROC fired, MA hadn't yet): {crash_only} days")
    print(f"  Silver T1       : {t1_days} days ({t1_days/len(common):.0%})")
    print(f"  Silver T2       : {t2_days} days ({t2_days/len(common):.0%})")
    print(f"  Both active     : {both_days} days ({both_days/len(common):.0%})")
    print(f"  Joint stress    : {joint_days} days ({joint_days/len(common):.0%}) "
          f"-- guard active AND LLY independently stressed")

    # ── Run five strategies ────────────────────────────────────────────────────
    configs = [
        (False, False, False, "A: Static base"),
        (True,  False, False, "B: Base + guard"),
        (False, True,  False, "C: Base + silver"),
        (True,  True,  False, "D: Base + guard + silver"),
        (True,  True,  True,  "E: Base + guard + silver + joint-stress"),
    ]

    results = []
    equities = {}

    print("\n── Full-period results ───────────────────────────────────────────────")
    print(f"  {'Strategy':<40}  {'CAGR':>8}  {'Sharpe':>7}  {'MaxDD':>8}  {'Calmar':>7}")
    print("  " + "-" * 77)

    for use_guard, use_silver, use_joint, label in configs:
        eq, events = run_strategy(prices, signals, use_guard, use_silver, label, use_joint)
        p = perf(eq, label)
        p["transitions"] = len(events)
        results.append(p)
        equities[label] = eq
        print(f"  {label:<40}  {p['cagr']:+.1%}    {p['sharpe']:.3f}  "
              f"{p['maxdd']:+.1%}   {p['calmar']:.3f}  ({len(events)} switches)")

    # ── IS / OOS split ─────────────────────────────────────────────────────────
    print("\n── IS / OOS breakdown ────────────────────────────────────────────────")
    is_mask  = common < OOS_START
    oos_mask = common >= OOS_START

    print(f"\n  {'Strategy':<28}  {'IS CAGR':>8}  {'IS Cal':>7}  "
          f"{'OOS CAGR':>9}  {'OOS Cal':>8}")
    print("  " + "-" * 70)
    for use_guard, use_silver, use_joint, label in configs:
        eq = equities[label]
        p_is  = perf(eq[is_mask])
        p_oos = perf(eq[oos_mask])
        print(f"  {label:<28}  {p_is['cagr']:+.1%}    {p_is['calmar']:.3f}  "
              f"  {p_oos['cagr']:+.1%}    {p_oos['calmar']:.3f}")

    # ── Year-by-year: combined vs static ──────────────────────────────────────
    print("\n── Year-by-year: Static base vs Combined system (* = OOS) ───────────")
    eq_a = equities["A: Static base"]
    eq_d = equities["E: Base + guard + silver + joint-stress"]
    print(f"\n  {'Year':>5}  {'Base CAGR':>10}  {'Combined CAGR':>14}  "
          f"{'Base MaxDD':>11}  {'Combined MaxDD':>15}  {'Winner':>8}")
    print("  " + "-" * 75)
    for yr in sorted(common.year.unique()):
        mask = common.year == yr
        if mask.sum() < 2:
            continue
        def yr_ret(eq):
            s = eq[mask]
            return float(s.iloc[-1] / s.iloc[0] - 1)
        def yr_mdd(eq):
            s = eq[mask]
            return float((s / s.cummax() - 1).min())
        oos_tag = "*" if yr >= OOS_START.year else " "
        r_base = yr_ret(eq_a); r_comb = yr_ret(eq_d)
        m_base = yr_mdd(eq_a); m_comb = yr_mdd(eq_d)
        c_base = r_base / abs(m_base) if m_base != 0 else 0
        c_comb = r_comb / abs(m_comb) if m_comb != 0 else 0
        winner = "COMB" if c_comb > c_base else "base"
        print(f"  {yr}{oos_tag}  {r_base:+.1%}        {r_comb:+.1%}           "
              f"{m_base:+.1%}        {m_comb:+.1%}           {winner}")

    # ── Current state ──────────────────────────────────────────────────────────
    print("\n── Current state ─────────────────────────────────────────────────────")
    last = signals.iloc[-1]
    guard_now  = bool(last["guard"])
    lly_stress_now = bool(last["lly_stress"])
    joint_now  = bool(last["joint"])
    silver_now = last["silver_state"]
    curr_w     = JOINT_WEIGHTS[silver_now] if joint_now else WEIGHTS[(guard_now, silver_now)]

    avgo_last  = float(avgo_p.reindex(common).iloc[-1])
    sma200_now = float(avgo_p.reindex(common).rolling(AVGO_MA).mean().iloc[-1])
    roc_now    = float(avgo_p.reindex(common).pct_change(CRASH_ROC_WINDOW).iloc[-1])
    lly_last     = float(lly_p.reindex(common).iloc[-1])
    lly_sma_now  = float(lly_p.reindex(common).rolling(LLY_MA).mean().iloc[-1])
    lly_roc_now  = float(lly_p.reindex(common).pct_change(CRASH_ROC_WINDOW).iloc[-1])
    gsr_last   = float((gold_p.reindex(common) / silver_p.reindex(common)).iloc[-1])

    ma_active    = bool(last["guard_ma"])
    crash_active = bool(last["guard_crash"])
    trigger = "MA" if (ma_active and not crash_active) else ("CRASH" if crash_active and not ma_active else ("MA+CRASH" if guard_now else "none"))
    print(f"  AVGO: ${avgo_last:.2f}  vs 200d SMA ${sma200_now:.2f}  "
          f"-> guard={'ACTIVE' if guard_now else 'inactive'} (trigger: {trigger})")
    print(f"  AVGO {CRASH_ROC_WINDOW}d ROC: {roc_now:+.1%}  (crash threshold: {CRASH_ROC_THRESHOLD:.0%})")
    print(f"  LLY:  ${lly_last:.2f}  vs 200d SMA ${lly_sma_now:.2f}  "
          f"-> lly_stress={'ACTIVE' if lly_stress_now else 'inactive'}  "
          f"({CRASH_ROC_WINDOW}d ROC: {lly_roc_now:+.1%})")
    print(f"  Joint stress (guard AND lly_stress): {'ACTIVE -> full flight to Gold' if joint_now else 'inactive'}")
    print(f"  GSR:  {gsr_last:.2f}  -> silver={silver_now}")
    print(f"  Active state: guard={guard_now}, lly_stress={lly_stress_now}, joint={joint_now}, silver={silver_now}")
    print(f"  Current weights:")
    for t, w in curr_w.items():
        if w > 0:
            name = {"GC_F": "Gold", "AVGO": "AVGO", "LLY": "LLY", "SI_F": "Silver"}[t]
            print(f"    {name:<8}: {w:.1%}")

    # ── Save ───────────────────────────────────────────────────────────────────
    OUT_CSV.parent.mkdir(exist_ok=True)
    pd.DataFrame(results).to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")


if __name__ == "__main__":
    main()
