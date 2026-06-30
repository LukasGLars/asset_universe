"""
Metals Tactical Layer — Complete Analysis

Sections:
  1. Gold trigger comparison  — no macro / ry=HIGH / baa10y=TIGHT / hy_oas=TIGHT
                                paired with gold_mom21d=LOW. Pick the winner.
  2. Gold exit analysis       — persistence of trigger + return at different exits
  3. Gold sizing backtest     — grid over overweight weights vs Gold25/AVGO55/LLY20 base
  4. Silver exit validation   — test cycle-complete exit at GSR p33 vs alternatives
  5. Silver sizing backtest   — T1 and T2 add amounts

Output: console + comparison_results/metals_tactical.csv
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.store import reader

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "metals_tactical.csv"

# 3-asset base weights
BASE = {"gold": 0.25, "avgo": 0.55, "lly": 0.20}

# Silver T1/T2 thresholds (from signal audit)
GSR_T1 = 83.36
GSR_T2 = 86.45
GSR_CYCLE_COMPLETE = 59.65  # p33 — exit level from signal audit


def load(cat: str, ticker: str) -> pd.Series:
    path = reader.ticker_path(DATA_DIR, cat, ticker)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index()


def fwd_ret(prices: pd.Series, date: pd.Timestamp, days: int) -> float | None:
    idx = prices.index.searchsorted(date)
    if idx >= len(prices) or abs((prices.index[idx] - date).days) > 5:
        return None
    end = idx + days
    if end >= len(prices):
        return None
    p0, p1 = prices.iloc[idx], prices.iloc[end]
    return (p1 - p0) / p0 if p0 > 0 else None


def stats(rets: list[float]) -> dict:
    if not rets:
        return {"n": 0, "median": float("nan"), "wr": float("nan")}
    s = pd.Series(rets)
    return {
        "n":      len(s),
        "median": round(float(s.median()), 4),
        "wr":     round(float((s > 0).mean()), 4),
        "p25":    round(float(s.quantile(0.25)), 4),
        "p75":    round(float(s.quantile(0.75)), 4),
    }


def diversity(dates: pd.DatetimeIndex) -> str:
    if len(dates) < 2:
        return "THIN"
    span = (dates[-1] - dates[0]).days / 365.25
    pct3 = float((dates >= dates[-1] - pd.DateOffset(years=3)).mean())
    if span >= 10 and pct3 < 0.50:
        return "ROBUST"
    if span < 5 or pct3 > 0.80:
        return "THIN"
    return "MODERATE"


def backtest_base(gold: pd.Series, avgo: pd.Series, lly: pd.Series,
                  weights: dict) -> pd.Series:
    """Daily portfolio value, equal-weighted rebalance at start only."""
    common = gold.index.intersection(avgo.index).intersection(lly.index)
    g = gold.reindex(common)
    a = avgo.reindex(common)
    l = lly.reindex(common)
    ret = (
        weights["gold"] * g.pct_change() +
        weights["avgo"] * a.pct_change() +
        weights["lly"]  * l.pct_change()
    ).fillna(0)
    return (1 + ret).cumprod()


def perf(equity: pd.Series) -> dict:
    r = equity.pct_change().dropna()
    total_yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = float(equity.iloc[-1] ** (1 / total_yrs) - 1)
    rolling_max = equity.cummax()
    dd = (equity / rolling_max - 1)
    maxdd = float(dd.min())
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0
    calmar = cagr / abs(maxdd) if maxdd != 0 else 0
    return {
        "cagr":   round(cagr, 4),
        "sharpe": round(sharpe, 3),
        "maxdd":  round(maxdd, 4),
        "calmar": round(calmar, 3),
    }


def header(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    print("Loading data...")
    labeled_df, _ = regime_module.build(DATA_DIR)

    gold   = load("commodities", "GC_F")
    silver = load("commodities", "SI_F")
    avgo   = load("equities",    "AVGO")
    lly    = load("equities",    "LLY")

    # Gold momentum tertile thresholds (full history)
    mom21 = gold.pct_change(21).dropna()
    p33_mom = float(mom21.quantile(0.333))
    p67_mom = float(mom21.quantile(0.667))
    mom21_low_dates = mom21.index[mom21 <= p33_mom]

    current_mom21 = float(mom21.iloc[-1])
    print(f"Gold mom21d thresholds: p33={p33_mom:.1%}  p67={p67_mom:.1%}")
    print(f"Current gold mom21d: {current_mom21:.1%}  -> {'LOW' if current_mom21<=p33_mom else 'MID' if current_mom21<=p67_mom else 'HIGH'}")

    # ── 1. GOLD TRIGGER COMPARISON ────────────────────────────────────────────
    header("1. GOLD TRIGGER COMPARISON  (gold_mom21d=LOW x macro filter)")

    combos = {
        "mom21=LOW (no macro)":           mom21_low_dates,
        "mom21=LOW + ry=HIGH":            mom21_low_dates[mom21_low_dates.isin(
                                            labeled_df.index[labeled_df["ry_regime"] == "HIGH"])],
        "mom21=LOW + baa10y=TIGHT":       mom21_low_dates[mom21_low_dates.isin(
                                            labeled_df.index[labeled_df["baa10y_regime"] == "TIGHT"])],
        "mom21=LOW + hy_oas=TIGHT":       mom21_low_dates[mom21_low_dates.isin(
                                            labeled_df.index[labeled_df["hy_oas_regime"] == "TIGHT"])],
    }

    # Baseline (unconditional)
    all_dates = labeled_df.index
    base_rets_63  = [r for d in all_dates if (r := fwd_ret(gold, d, 63))  is not None]
    base_rets_252 = [r for d in all_dates if (r := fwd_ret(gold, d, 252)) is not None]
    base63  = stats(base_rets_63)
    base252 = stats(base_rets_252)
    print(f"Baseline:  63d median={base63['median']:+.1%}  wr={base63['wr']:.0%} | "
          f"252d median={base252['median']:+.1%}  wr={base252['wr']:.0%}")
    print()

    trigger_rows = []
    for name, dates in combos.items():
        r63  = [r for d in dates if (r := fwd_ret(gold, d, 63))  is not None]
        r252 = [r for d in dates if (r := fwd_ret(gold, d, 252)) is not None]
        s63, s252 = stats(r63), stats(r252)
        active_now = current_mom21 <= p33_mom
        if "ry=HIGH" in name:
            active_now = active_now and labeled_df["ry_regime"].iloc[-1] == "HIGH"
        elif "baa10y=TIGHT" in name:
            active_now = active_now and labeled_df["baa10y_regime"].iloc[-1] == "TIGHT"
        elif "hy_oas=TIGHT" in name:
            active_now = active_now and labeled_df["hy_oas_regime"].iloc[-1] == "TIGHT"
        row = {
            "trigger":    name,
            "active_now": active_now,
            "diversity":  diversity(dates),
            "n_63d":      s63["n"],
            "med_63d":    s63["median"],
            "wr_63d":     s63["wr"],
            "lift_63d":   round(s63["median"] - base63["median"], 4) if s63["n"] > 0 else float("nan"),
            "n_252d":     s252["n"],
            "med_252d":   s252["median"],
            "wr_252d":    s252["wr"],
            "lift_252d":  round(s252["median"] - base252["median"], 4) if s252["n"] > 0 else float("nan"),
        }
        trigger_rows.append(row)
        print(f"{name}")
        print(f"  diversity={row['diversity']}  active={active_now}")
        print(f"  63d:  n={s63['n']}  median={s63['median']:+.1%}  wr={s63['wr']:.0%}  lift={row['lift_63d']:+.1%}")
        print(f"  252d: n={s252['n']}  median={s252['median']:+.1%}  wr={s252['wr']:.0%}  lift={row['lift_252d']:+.1%}")
        print()

    # Pick winner: best wr_252d with diversity != THIN (prefer ROBUST/MODERATE)
    tdf = pd.DataFrame(trigger_rows)
    robust_first = tdf[tdf["diversity"] != "THIN"].sort_values("wr_252d", ascending=False)
    winner_name  = robust_first.iloc[0]["trigger"] if not robust_first.empty else tdf.sort_values("wr_252d", ascending=False).iloc[0]["trigger"]
    winner_dates = combos[winner_name]
    print(f">>> WINNER: {winner_name}  (best wr_252d with non-THIN diversity)")

    # ── 2. GOLD EXIT ANALYSIS ─────────────────────────────────────────────────
    header("2. GOLD EXIT ANALYSIS  (what happens after trigger fires)")

    # For each trigger date, find: mom21 recovery date, fixed horizons
    # Then compare gold return to each potential exit
    exit_results = {"mom_recovery": [], "fixed_63d": [], "fixed_126d": [], "fixed_252d": []}

    # mom21 recovery = first date after entry where mom21 > p33 (flips to MID or HIGH)
    mom21_aligned = mom21.reindex(gold.index, method="nearest", tolerance=pd.Timedelta("3D"))

    durations = []
    for entry_date in winner_dates:
        idx = gold.index.searchsorted(entry_date)
        if idx >= len(gold) or abs((gold.index[idx] - entry_date).days) > 5:
            continue
        p0 = gold.iloc[idx]

        # Find mom recovery: scan forward until mom21 > p33
        recovery_idx = None
        for fi in range(idx + 5, min(idx + 300, len(gold))):
            if mom21_aligned.iloc[fi] > p33_mom:
                recovery_idx = fi
                break

        if recovery_idx is not None:
            ret = (gold.iloc[recovery_idx] - p0) / p0
            days_held = recovery_idx - idx
            durations.append(days_held)
            exit_results["mom_recovery"].append(ret)

        for label, days in [("fixed_63d", 63), ("fixed_126d", 126), ("fixed_252d", 252)]:
            r = fwd_ret(gold, entry_date, days)
            if r is not None:
                exit_results[label].append(r)

    print(f"Trigger instances analysed: {len(winner_dates)}")
    if durations:
        print(f"Momentum recovery (med days held): {np.median(durations):.0f}d  "
              f"(p25={np.percentile(durations,25):.0f}  p75={np.percentile(durations,75):.0f})")
    print()

    best_exit, best_wr = None, 0.0
    for exit_name, rets in exit_results.items():
        s = stats(rets)
        wr   = s["wr"] if not pd.isna(s["wr"]) else 0
        med  = s["median"] if not pd.isna(s["median"]) else 0
        print(f"  Exit: {exit_name:20}  n={s['n']}  median={med:+.1%}  wr={wr:.0%}")
        if wr > best_wr and s["n"] >= 20:
            best_wr, best_exit = wr, exit_name

    print(f"\n>>> BEST EXIT: {best_exit}  (wr={best_wr:.0%})")

    # ── 3. GOLD SIZING BACKTEST ───────────────────────────────────────────────
    header("3. GOLD SIZING BACKTEST  (overweight during trigger, base otherwise)")

    # Build daily trigger signal aligned to price index
    # Active when: gold_mom21d=LOW AND [winner macro condition]
    macro_key = None
    if "ry=HIGH" in winner_name:
        macro_key = ("ry_regime", "HIGH")
    elif "baa10y=TIGHT" in winner_name:
        macro_key = ("baa10y_regime", "TIGHT")
    elif "hy_oas=TIGHT" in winner_name:
        macro_key = ("hy_oas_regime", "TIGHT")

    # Build common price index
    common = gold.index.intersection(avgo.index).intersection(lly.index)
    g = gold.reindex(common)
    a = avgo.reindex(common)
    l = lly.reindex(common)

    # Mom21 signal on common dates
    mom21_common = g.pct_change(21)
    mom21_p33    = float(mom21_common.dropna().quantile(0.333))

    # Macro signal
    if macro_key:
        col, val = macro_key
        macro_signal = labeled_df[col].reindex(common, method="ffill") == val
    else:
        macro_signal = pd.Series(True, index=common)

    mom_signal = mom21_common <= mom21_p33
    trigger    = (mom_signal & macro_signal).fillna(False)

    print(f"Trigger active: {trigger.sum()} / {len(trigger)} days "
          f"({trigger.mean():.0%} of time)")
    print()

    sizing_rows = []
    for gold_ow in [0.25, 0.30, 0.35, 0.40, 0.45, 0.50]:
        # When trigger: shift gold to gold_ow, reduce avgo/lly proportionally
        slack    = gold_ow - BASE["gold"]
        total_al = BASE["avgo"] + BASE["lly"]
        avgo_w   = BASE["avgo"] - slack * (BASE["avgo"] / total_al)
        lly_w    = BASE["lly"]  - slack * (BASE["lly"]  / total_al)

        # Ensure weights are valid
        if avgo_w < 0.05 or lly_w < 0.02:
            continue

        # Daily portfolio return
        base_ret = (BASE["gold"] * g.pct_change() +
                    BASE["avgo"] * a.pct_change() +
                    BASE["lly"]  * l.pct_change())

        ow_ret = (gold_ow * g.pct_change() +
                  avgo_w  * a.pct_change() +
                  lly_w   * l.pct_change())

        port_ret = base_ret.copy()
        port_ret[trigger] = ow_ret[trigger]

        equity = (1 + port_ret.fillna(0)).cumprod()
        p = perf(equity)

        row = {
            "gold_weight":  gold_ow,
            "avgo_weight":  round(avgo_w, 3),
            "lly_weight":   round(lly_w, 3),
            "cagr":         p["cagr"],
            "sharpe":       p["sharpe"],
            "maxdd":        p["maxdd"],
            "calmar":       p["calmar"],
        }
        sizing_rows.append(row)
        print(f"  Gold={gold_ow:.0%}  AVGO={avgo_w:.0%}  LLY={lly_w:.0%}  "
              f"-> CAGR={p['cagr']:+.1%}  Sharpe={p['sharpe']:.3f}  "
              f"MaxDD={p['maxdd']:+.1%}  Calmar={p['calmar']:.3f}")

    sdf = pd.DataFrame(sizing_rows)
    best_size_row = sdf.loc[sdf["calmar"].idxmax()]
    print(f"\n>>> BEST GOLD OVERWEIGHT: {best_size_row['gold_weight']:.0%}  "
          f"(AVGO={best_size_row['avgo_weight']:.0%}  LLY={best_size_row['lly_weight']:.0%})  "
          f"Calmar={best_size_row['calmar']:.3f}")

    # ── 4. SILVER EXIT VALIDATION ─────────────────────────────────────────────
    header("4. SILVER EXIT VALIDATION  (cycle-complete at GSR p33 vs alternatives)")

    common_sl = gold.index.intersection(silver.index)
    gsr       = (gold.reindex(common_sl) / silver.reindex(common_sl)).dropna()
    gsr_p33   = float(gsr.quantile(0.333))
    print(f"GSR p33 (cycle-complete threshold): {gsr_p33:.2f}  (signal audit: {GSR_CYCLE_COMPLETE})")

    # Find T1 trigger entry dates (GSR >= T1 AND fallen >=5% from 60d peak)
    gsr_peak60 = gsr.rolling(60, min_periods=30).max()
    gsr_drop   = gsr / gsr_peak60 - 1
    t1_signal  = (gsr >= GSR_T1) & (gsr_drop <= -0.05)
    t1_entries = gsr.index[t1_signal]

    print(f"T1 trigger instances: {len(t1_entries)}")

    silver_sl = silver.reindex(common_sl)
    sv_exit_results = {
        "exit_cycle_complete":  [],   # exit when GSR < gsr_p33
        "exit_t1_level":        [],   # exit when GSR drops back below T1
        "fixed_63d":            [],
        "fixed_126d":           [],
        "fixed_252d":           [],
    }
    sv_durations = {"cycle_complete": [], "t1_level": []}

    for entry_date in t1_entries:
        idx = silver_sl.index.searchsorted(entry_date)
        if idx >= len(silver_sl) or abs((silver_sl.index[idx] - entry_date).days) > 5:
            continue
        p0 = silver_sl.iloc[idx]
        if p0 <= 0:
            continue

        # Scan forward for exits
        cc_idx, t1_idx = None, None
        for fi in range(idx + 1, min(idx + 500, len(silver_sl))):
            gsr_fi = gsr.iloc[fi] if fi < len(gsr) else float("nan")
            if cc_idx is None and gsr_fi < gsr_p33:
                cc_idx = fi
            if t1_idx is None and gsr_fi < GSR_T1:
                t1_idx = fi

        if cc_idx is not None:
            ret = (silver_sl.iloc[cc_idx] - p0) / p0
            sv_exit_results["exit_cycle_complete"].append(ret)
            sv_durations["cycle_complete"].append(cc_idx - idx)

        if t1_idx is not None:
            ret = (silver_sl.iloc[t1_idx] - p0) / p0
            sv_exit_results["exit_t1_level"].append(ret)
            sv_durations["t1_level"].append(t1_idx - idx)

        for label, days in [("fixed_63d", 63), ("fixed_126d", 126), ("fixed_252d", 252)]:
            if idx + days < len(silver_sl):
                ret = (silver_sl.iloc[idx + days] - p0) / p0
                sv_exit_results[label].append(ret)

    print()
    best_sv_exit, best_sv_wr = None, 0.0
    for exit_name, rets in sv_exit_results.items():
        s = stats(rets)
        dur_info = ""
        if exit_name in sv_durations and sv_durations[exit_name]:
            med_dur = np.median(sv_durations[exit_name])
            dur_info = f"  med_hold={med_dur:.0f}d"
        wr  = s["wr"] if not pd.isna(s["wr"]) else 0
        med = s["median"] if not pd.isna(s["median"]) else 0
        print(f"  {exit_name:30}  n={s['n']}  median={med:+.1%}  wr={wr:.0%}{dur_info}")
        if wr > best_sv_wr and s["n"] >= 5:
            best_sv_wr, best_sv_exit = wr, exit_name

    print(f"\n>>> BEST SILVER EXIT: {best_sv_exit}  (wr={best_sv_wr:.0%})")

    # ── 5. SILVER SIZING BACKTEST ─────────────────────────────────────────────
    header("5. SILVER SIZING BACKTEST  (T1 and T2 add amounts on top of base)")

    # Strategy: hold Gold25/AVGO55/LLY20 base + add silver during T1/T2
    # Silver funded from AVGO (proportionally)
    # Exit when GSR < gsr_p33 (cycle complete)

    # Build daily T1 and T2 signals (entry to cycle complete)
    # For each day: is a T1 or T2 episode active?
    t1_full = (gsr >= GSR_T1) & (gsr_drop <= -0.05)
    t2_full = (gsr >= GSR_T2) & (gsr_drop <= -0.05)

    # Extend signal forward until cycle complete (GSR < gsr_p33)
    def extend_signal(signal: pd.Series, gsr_series: pd.Series, exit_level: float) -> pd.Series:
        active = pd.Series(False, index=signal.index)
        in_episode = False
        for i, (dt, fired) in enumerate(signal.items()):
            if fired:
                in_episode = True
            if in_episode:
                active.iloc[i] = True
                if gsr_series.iloc[i] < exit_level:
                    in_episode = False
        return active

    t1_active = extend_signal(t1_full, gsr, gsr_p33)
    t2_active = extend_signal(t2_full, gsr, gsr_p33)

    print(f"T1 episode active: {t1_active.sum()} days ({t1_active.mean():.0%})")
    print(f"T2 episode active: {t2_active.sum()} days ({t2_active.mean():.0%})")
    print()

    # Align all series to common index
    common_all = g.index.intersection(silver_sl.index)
    g2  = g.reindex(common_all)
    a2  = a.reindex(common_all)
    l2  = l.reindex(common_all)
    sv2 = silver_sl.reindex(common_all)
    t1a = t1_active.reindex(common_all, fill_value=False)
    t2a = t2_active.reindex(common_all, fill_value=False)

    # Base return (no silver)
    base_ret2 = (BASE["gold"] * g2.pct_change() +
                 BASE["avgo"] * a2.pct_change() +
                 BASE["lly"]  * l2.pct_change()).fillna(0)

    silver_sizing_rows = []
    for t1_add in [0.05, 0.08, 0.10, 0.12]:
        for t2_extra in [0.0, 0.03, 0.05]:
            t2_add = t1_add + t2_extra

            # Only T1 active (not T2): add t1_add silver, reduce AVGO
            # T2 active: add t2_add silver, reduce AVGO more
            port_ret = base_ret2.copy()

            for signal, sv_add in [(t1a & ~t2a, t1_add), (t2a, t2_add)]:
                if sv_add <= 0:
                    continue
                avgo_adj = BASE["avgo"] - sv_add
                if avgo_adj < 0.05:
                    continue
                scale = 1 - sv_add  # gold and lly scale down
                sv_ret = (
                    BASE["gold"] * scale / (BASE["gold"] + BASE["lly"]) * g2.pct_change() +
                    avgo_adj * a2.pct_change() +
                    BASE["lly"] * scale / (BASE["gold"] + BASE["lly"]) * l2.pct_change() +
                    sv_add * sv2.pct_change()
                ).fillna(0)
                port_ret[signal] = sv_ret[signal]

            equity = (1 + port_ret).cumprod()
            p = perf(equity)
            row = {
                "t1_add": t1_add,
                "t2_add": t2_add,
                **p,
            }
            silver_sizing_rows.append(row)
            print(f"  T1+{t1_add:.0%}  T2+{t2_add:.0%}  -> "
                  f"CAGR={p['cagr']:+.1%}  Sharpe={p['sharpe']:.3f}  "
                  f"MaxDD={p['maxdd']:+.1%}  Calmar={p['calmar']:.3f}")

    ssdf = pd.DataFrame(silver_sizing_rows)
    base_p = perf((1 + base_ret2).cumprod())
    print(f"\n  Base (no silver): "
          f"CAGR={base_p['cagr']:+.1%}  Sharpe={base_p['sharpe']:.3f}  "
          f"MaxDD={base_p['maxdd']:+.1%}  Calmar={base_p['calmar']:.3f}")

    best_sv_size = ssdf.loc[ssdf["calmar"].idxmax()]
    print(f"\n>>> BEST SILVER SIZING: T1=+{best_sv_size['t1_add']:.0%}  "
          f"T2=+{best_sv_size['t2_add']:.0%}  Calmar={best_sv_size['calmar']:.3f}")

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    header("METALS TACTICAL LAYER — FINAL RULES")
    print(f"GOLD")
    print(f"  Base weight:   {BASE['gold']:.0%}")
    print(f"  Trigger:       {winner_name}")
    print(f"  Overweight to: {best_size_row['gold_weight']:.0%}  "
          f"(AVGO -> {best_size_row['avgo_weight']:.0%}, LLY -> {best_size_row['lly_weight']:.0%})")
    print(f"  Exit:          {best_exit}")
    print()
    print(f"SILVER")
    print(f"  Base weight:   0% (not in 3-asset base)")
    print(f"  T1 trigger:    GSR >= {GSR_T1} AND fallen >=5% from 60d peak")
    print(f"  T1 add:        +{best_sv_size['t1_add']:.0%} silver (funded from AVGO)")
    print(f"  T2 trigger:    GSR >= {GSR_T2} AND fallen >=5% from 60d peak")
    print(f"  T2 add:        +{best_sv_size['t2_add']:.0%} silver (funded from AVGO)")
    print(f"  Exit:          {best_sv_exit}  (GSR < {gsr_p33:.2f})")

    OUT_CSV.parent.mkdir(exist_ok=True)
    combined = pd.DataFrame(trigger_rows)
    combined.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")


if __name__ == "__main__":
    main()
