"""
run_contribution_split_test.py

Question: is it better to invest every monthly contribution immediately
(pure DCA), or to hold part of it back as cash and deploy the accumulated
pile into AVGO at crash-ROC triggers?

The dip-buying half is already validated (`MEMORY.md`, "Gap-down tranche
validated", 2026-08-14): at a real crash-ROC trigger, new capital into AVGO
beats both the defensive mix and the base mix, decisively past ~63d. What
was NEVER tested is the cost of *waiting*. Triggers fired 32 times in 17
years -- roughly twice a year -- so held-back cash sits idle a long while
between them, and that drag has to be paid out of the dip edge before the
strategy is worth anything.

This script tests the whole round trip: contributions -> cash -> trigger ->
AVGO, against pure DCA, as a compounding portfolio simulation rather than
the event study the 2026-08-14 test used (each of those 32 events was
treated independently, with no netting of overlapping windows).

EXECUTION REALISM -- the thing that killed the 200d guard: every trigger
here executes at the NEXT session's close, never the signal-generating one.
The guard's entire "validated" edge turned out to be lookahead bias from
trading the same close that generated the signal (MEMORY.md, "the AVGO 200d
guard's entire validated edge is lookahead bias"). A dip-buying rule is
exactly the kind of strategy that would flatter itself the same way, since
the trigger fires on a sharp down day and the bounce often starts
immediately.

Two source regimes, kept separate, same convention as
run_outlook_montecarlo.py:
  1. AVGO actual (2009-2026)
  2. TXN analog (2000-2026, incl. 2001 dot-com + 2008 GFC)

Exploratory script -- not wired into daily automation.
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

import run_combined_system as rcs

# ── Live config ───────────────────────────────────────────────────────────────
BASE_WEIGHTS = {"GC_F": 0.25, "AVGO": 0.40, "LLY": 0.35}
REBAL_BAND = 0.10               # matches vol_target.REBAL_BAND
MONTHLY_CONTRIBUTION = 6_000.0
START_TPV = 1_104_009.0

# Crash-ROC trigger, same parameters as run_combined_system's CRASH_ROC_*
CRASH_WINDOW = 5
CRASH_THRESHOLD = -0.10
DECLUSTER_DAYS = 21             # matches the 2026-08-14 event study

# Held-back cash has to earn something or the test is rigged against waiting.
# 2% is deliberately generous for an Avanza cash balance (which pays ~0).
CASH_ANNUAL = 0.02
CASH_DAILY = (1 + CASH_ANNUAL) ** (1 / 252) - 1

HOLDBACK_FRACTIONS = [0.0, 0.25, 0.50, 0.75, 1.00]


def crash_trigger_days(avgo: pd.Series) -> pd.DatetimeIndex:
    """Declustered crash-ROC trigger dates (the SIGNAL days, not the trade
    days -- callers must execute on the following session)."""
    roc = avgo.pct_change(CRASH_WINDOW)
    raw = roc.index[roc <= CRASH_THRESHOLD]
    kept: list[pd.Timestamp] = []
    for d in raw:
        if not kept or (avgo.index.get_loc(d) - avgo.index.get_loc(kept[-1])) >= DECLUSTER_DAYS:
            kept.append(d)
    return pd.DatetimeIndex(kept)


def simulate(prices: pd.DataFrame, holdback: float, avgo_key: str) -> dict:
    """Fixed-weight base portfolio with banded rebalancing, monthly
    contributions, and (1-holdback) invested immediately while `holdback`
    accumulates as cash for deployment into AVGO at the next trigger."""
    dates = prices.index
    signal_days = set(crash_trigger_days(prices[avgo_key]))

    # Seed at target weights.
    shares = {t: START_TPV * w / prices[t].iloc[0] for t, w in BASE_WEIGHTS.items()}
    cash = 0.0
    pending_deploy = False          # set on a signal day, acted on next session
    n_deploys = 0
    deployed_total = 0.0
    contributed = 0.0
    cash_days = 0

    prev_month = dates[0].month

    for i, d in enumerate(dates):
        px = prices.loc[d]
        cash *= (1 + CASH_DAILY)
        if cash > 0:
            cash_days += 1

        # --- act on YESTERDAY's signal, at today's close (no lookahead) ---
        if pending_deploy and cash > 0:
            shares[avgo_key] += cash / px[avgo_key]
            deployed_total += cash
            cash = 0.0
            n_deploys += 1
        pending_deploy = d in signal_days

        # --- monthly contribution ---
        if d.month != prev_month:
            prev_month = d.month
            contributed += MONTHLY_CONTRIBUTION
            invest_now = MONTHLY_CONTRIBUTION * (1 - holdback)
            cash += MONTHLY_CONTRIBUTION * holdback
            if invest_now > 0:
                # Route new money to the most-underweight leg, mirroring
                # fi_tracker's NEXT CONTRIBUTION rule rather than splitting
                # pro-rata.
                vals = {t: shares[t] * px[t] for t in BASE_WEIGHTS}
                tot = sum(vals.values())
                gaps = {t: BASE_WEIGHTS[t] - vals[t] / tot for t in BASE_WEIGHTS}
                target = max(gaps, key=gaps.get)
                shares[target] += invest_now / px[target]

        # --- banded rebalance on already-held capital ---
        vals = {t: shares[t] * px[t] for t in BASE_WEIGHTS}
        tot = sum(vals.values())
        if tot > 0 and any(abs(BASE_WEIGHTS[t] - vals[t] / tot) > REBAL_BAND for t in BASE_WEIGHTS):
            for t in BASE_WEIGHTS:
                shares[t] = tot * BASE_WEIGHTS[t] / px[t]

    final_px = prices.iloc[-1]
    terminal = sum(shares[t] * final_px[t] for t in BASE_WEIGHTS) + cash
    years = (dates[-1] - dates[0]).days / 365.25
    return {
        "terminal": terminal,
        "years": years,
        "contributed": contributed,
        "n_deploys": n_deploys,
        "deployed_total": deployed_total,
        "pct_days_holding_cash": cash_days / len(dates),
    }


def run_dataset(label: str, avgo_series: pd.Series, gold: pd.Series,
                lly: pd.Series, start: pd.Timestamp) -> pd.DataFrame:
    common = (gold.index.intersection(avgo_series.index)
              .intersection(lly.index))
    common = common[common >= start].sort_values()
    prices = pd.DataFrame({
        "GC_F": gold.reindex(common).ffill(),
        "AVGO": avgo_series.reindex(common).ffill(),
        "LLY": lly.reindex(common).ffill(),
    }).dropna()

    n_triggers = len(crash_trigger_days(prices["AVGO"]))
    rows = []
    for hb in HOLDBACK_FRACTIONS:
        r = simulate(prices, hb, "AVGO")
        rows.append({
            "holdback": hb,
            "terminal": r["terminal"],
            "cagr": (r["terminal"] / START_TPV) ** (1 / r["years"]) - 1,
            "n_deploys": r["n_deploys"],
            "deployed_kr": r["deployed_total"],
            "pct_days_cash": r["pct_days_holding_cash"],
        })
    df = pd.DataFrame(rows)
    base = df.loc[df.holdback == 0.0, "terminal"].iloc[0]
    df["vs_pure_dca"] = df["terminal"] / base - 1

    print(f"\n=== {label} ===")
    print(f"  {prices.index[0].date()} -> {prices.index[-1].date()}  "
          f"({(prices.index[-1]-prices.index[0]).days/365.25:.1f}y), "
          f"{n_triggers} declustered triggers, {MONTHLY_CONTRIBUTION:,.0f} kr/mo")
    print(f"  {'holdback':>9} {'terminal':>14} {'CAGR':>7} {'deploys':>8} "
          f"{'days in cash':>13} {'vs pure DCA':>12}")
    for _, r in df.iterrows():
        print(f"  {r.holdback:>8.0%} {r.terminal:>14,.0f} {r.cagr:>7.1%} "
              f"{int(r.n_deploys):>8} {r.pct_days_cash:>12.0%} {r.vs_pure_dca:>+12.1%}")
    return df


def main():
    gold = rcs.load_prices("commodities", "GC_F")
    lly = rcs.load_prices("equities", "LLY")
    avgo = rcs.load_prices("equities", "AVGO")
    txn = rcs.load_prices("equities", "TXN")

    a = run_dataset("AVGO actual (2009-2026)", avgo, gold, lly,
                    pd.Timestamp("2009-08-06"))
    t = run_dataset("TXN analog (2000-2026, incl. 2001 + 2008)", txn, gold, lly,
                    pd.Timestamp("2000-08-30"))

    a["dataset"] = "AVGO_actual"
    t["dataset"] = "TXN_analog"
    out = PROJECT_ROOT / "comparison_results" / "contribution_split.csv"
    pd.concat([a, t]).to_csv(out, index=False)
    print(f"\nWrote {out}")

    print("\nSelf-check: holdback=0% must be exactly pure DCA (no cash, no deploys).")
    for df, name in ((a, "AVGO actual"), (t, "TXN analog")):
        r = df[df.holdback == 0.0].iloc[0]
        ok = r.n_deploys == 0 and r.pct_days_cash == 0 and abs(r.vs_pure_dca) < 1e-12
        print(f"  {name:<12} {'PASS' if ok else 'FAIL'}  "
              f"(deploys={int(r.n_deploys)}, days_in_cash={r.pct_days_cash:.0%})")


if __name__ == "__main__":
    main()
