"""
run_cash_tranche_ladder.py

TEMPORARY diagnostic (2026-10-02). Deployment schedule for the standing 10%
cash position in the Reactor Core target allocation.

This is NOT the question "Contribution-splitting to dip-buy" (2026-08-18,
PR #96) already answered. That test asked whether to MANUFACTURE cash by
diverting contributions -- answer no, the idle drag cancels the dip edge.
Here the cash already exists as a standing 10% target the operator has
chosen, so its drag is sunk and is not a variable. The only open question
is how to spend it when the growth sleeve falls: all at the trigger, or
laddered into deeper levels?

Three parts, in the order the sizing argument needs them:

  1. CONDITIONAL DRAWDOWN. Given the live crash trigger has fired, how much
     further does the name typically fall? This sets WHERE tranches 2 and 3
     can sit at all -- a level that is reached 10% of the time is a tranche
     that sits in cash 90% of the time.

  2. FORWARD RETURNS BY ENTRY DEPTH. Among the episodes that did reach each
     level, what did buying there return at 21/63/252d? This sets the
     WEIGHTING -- but it must be read against part 1's hit rate, never
     alone, because it is conditioned on the level being reached.

  3. LADDER COMPARISON. Candidate ladders deploying the whole sleeve, with
     undeployed tranches explicitly charged as cash (CASH_ANNUAL, same
     generous 2% the 2026-08-18 test used). This is the only part that
     prices the wait, and therefore the only part a decision should rest on.

Discipline, all three parts:
  - Signal comes from close(i); every fill is at close(i+1) or later. The
     trigger day's own close is never a fill price.
  - Triggers declustered 21 trading days apart via the SAME helper
     run_contribution_split_test.py uses -- comparable to the n=32 event
     study at MEMORY.md "Gap-down tranche validated" (2026-08-14).
  - Ladders are ranked on the WORST date-third, never full-sample
     (MEMORY.md [[project-reactor-core-mix]]). Crash-buying is precisely
     the shape that looks good pooled and dies in one sub-period.

Read-only analysis. Not wired into any live gate.

Delete this file, tests/test_cash_tranche_ladder.py and
.github/workflows/cash_tranche_ladder.yml once logged to MEMORY.md.

Usage:
    python run_cash_tranche_ladder.py
    python run_cash_tranche_ladder.py --ticker LLY
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
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.store import reader

# Reuse the live trigger + declustering rather than restating the constants,
# so this cannot drift from the study it is meant to extend.
from run_contribution_split_test import (
    CASH_ANNUAL,
    CASH_DAILY,
    CRASH_THRESHOLD,
    CRASH_WINDOW,
    DECLUSTER_DAYS,
    crash_trigger_days,
)

DATA_DIR = config.raw_data_dir()

# Levels are measured DOWN from the first tranche's fill price (close i+1).
DEPTH_LEVELS   = [0.00, 0.05, 0.07, 0.10, 0.15, 0.20, 0.25, 0.30]
DEPLOY_WINDOW  = 126      # trading days a tranche has to find its level
HORIZONS       = [63, 126, 252]
DD_WINDOW      = 126      # window for the conditional-drawdown distribution
MIN_N          = 5

# (depth, weight) -- weights must sum to 1.0, asserted below and in tests.
LADDERS: dict[str, list[tuple[float, float]]] = {
    "A  all-in at trigger":        [(0.00, 1.00)],
    "B  50/50  @0/-10":            [(0.00, 0.50), (0.10, 0.50)],
    "C  40/30/30  @0/-10/-20":     [(0.00, 0.40), (0.10, 0.30), (0.20, 0.30)],
    "D  34/33/33  @0/-7/-15":      [(0.00, 0.34), (0.07, 0.33), (0.15, 0.33)],
    "E  25x4  @0/-5/-10/-20":      [(0.00, 0.25), (0.05, 0.25), (0.10, 0.25), (0.20, 0.25)],
    "F  60/40  @0/-15":            [(0.00, 0.60), (0.15, 0.40)],
    "G  wait-for--15 (control)":   [(0.15, 1.00)],
}


# ── mechanics ─────────────────────────────────────────────────────────────────

def load_closes(ticker: str, category: str) -> pd.Series:
    path = reader.ticker_path(DATA_DIR, category, ticker)
    return reader.load(path)["close"].dropna()


def first_touch(closes: pd.Series, entry_i: int, target: float, last_i: int) -> int | None:
    """Index of the first close at or below `target`, searched STRICTLY after
    entry_i and no later than last_i. Returns None if never reached."""
    lo, hi = entry_i + 1, min(last_i, len(closes) - 1)
    if lo > hi:
        return None
    seg = closes.iloc[lo:hi + 1]
    hits = np.flatnonzero((seg <= target).to_numpy())
    return None if hits.size == 0 else lo + int(hits[0])


def ladder_episode(
    closes: pd.Series,
    sig_i: int,
    ladder: list[tuple[float, float]],
    horizon: int,
    deploy_window: int = DEPLOY_WINDOW,
) -> dict | None:
    """Total return of one ladder over one episode, measured on a COMMON
    clock: entry day (sig_i+1) to entry day + horizon. Each tranche earns
    cash until its level is touched, then the asset to the common end date.
    A tranche whose level is never touched inside the window earns cash for
    the whole horizon -- that is the charge for waiting."""
    entry_i = sig_i + 1
    end_i   = entry_i + horizon
    if end_i >= len(closes):
        return None

    entry_px = float(closes.iloc[entry_i])
    end_px   = float(closes.iloc[end_i])
    # A tranche cannot fill after the measurement ends.
    last_fill_i = min(entry_i + deploy_window, end_i)

    value, filled = 0.0, []
    for depth, w in ladder:
        if depth == 0.0:
            fill_i, fill_px = entry_i, entry_px
        else:
            fill_i = first_touch(closes, entry_i, entry_px * (1.0 - depth), last_fill_i)
            fill_px = float(closes.iloc[fill_i]) if fill_i is not None else None

        if fill_i is None:
            value += w * (1.0 + CASH_DAILY) ** horizon
            filled.append(False)
        else:
            cash_days = fill_i - entry_i
            value += w * ((1.0 + CASH_DAILY) ** cash_days) * (end_px / fill_px)
            filled.append(True)

    return {"ret": value - 1.0, "filled": filled, "entry_i": entry_i}


# ── parts ─────────────────────────────────────────────────────────────────────

def part1_conditional_drawdown(closes: pd.Series, sigs: list[int]) -> pd.DataFrame:
    rows = []
    for sig_i in sigs:
        entry_i = sig_i + 1
        if entry_i + DD_WINDOW >= len(closes):
            continue
        entry_px = float(closes.iloc[entry_i])
        seg = closes.iloc[entry_i + 1:entry_i + DD_WINDOW + 1]
        trough = float(seg.min())
        rows.append({
            "date": closes.index[entry_i].date(),
            "further_dd": trough / entry_px - 1.0,
            "days_to_trough": int(np.argmin(seg.to_numpy())) + 1,
        })
    return pd.DataFrame(rows)


def part2_depth_returns(closes: pd.Series, sigs: list[int]) -> pd.DataFrame:
    rows = []
    for depth in DEPTH_LEVELS:
        for h in [21, 63, 252]:
            rets, reached, eligible = [], 0, 0
            for sig_i in sigs:
                entry_i = sig_i + 1
                if entry_i + DEPLOY_WINDOW + h >= len(closes):
                    continue
                eligible += 1
                entry_px = float(closes.iloc[entry_i])
                if depth == 0.0:
                    fill_i = entry_i
                else:
                    fill_i = first_touch(
                        closes, entry_i, entry_px * (1.0 - depth),
                        entry_i + DEPLOY_WINDOW,
                    )
                if fill_i is None:
                    continue
                reached += 1
                if fill_i + h < len(closes):
                    rets.append(float(closes.iloc[fill_i + h] / closes.iloc[fill_i]) - 1.0)
            s = pd.Series(rets, dtype=float)
            hit = reached / eligible if eligible else np.nan
            med = float(s.median()) if len(s) >= MIN_N else np.nan
            rows.append({
                "depth": f"-{depth:.0%}" if depth else "at trigger",
                "horizon": h, "eligible": eligible, "reached": reached,
                "hit_rate": hit, "n_ret": len(s),
                "median": med,
                "win_rate": float((s > 0).mean()) if len(s) >= MIN_N else np.nan,
                # The number that actually matters for sizing: a tranche only
                # earns its conditional return when the level is reached.
                "hit_x_median": hit * med if (len(s) >= MIN_N and eligible) else np.nan,
            })
    return pd.DataFrame(rows)


def part3_ladders(closes: pd.Series, sigs: list[int]) -> pd.DataFrame:
    rows = []
    for h in HORIZONS:
        episodes = {}
        for name, ladder in LADDERS.items():
            res = [r for sig_i in sigs
                   if (r := ladder_episode(closes, sig_i, ladder, h)) is not None]
            episodes[name] = res

        # Common episode set per horizon, so ladders are compared on the same
        # events -- otherwise a ladder can win by dropping its hard episodes.
        common = set.intersection(*[{r["entry_i"] for r in v} for v in episodes.values()]) \
            if episodes else set()

        for name, res in episodes.items():
            res = [r for r in res if r["entry_i"] in common]
            if len(res) < MIN_N:
                continue
            rets = pd.Series([r["ret"] for r in res])
            dates = [closes.index[r["entry_i"]] for r in res]
            order = np.argsort(dates)
            thirds = np.array_split(np.asarray(order), 3)
            third_meds = [float(rets.iloc[list(t)].median()) for t in thirds if len(t)]
            deploy = np.mean([np.mean(r["filled"]) for r in res])
            rows.append({
                "horizon": h, "ladder": name, "n": len(res),
                "median": float(rets.median()),
                "average": float(rets.mean()),
                "worst": float(rets.min()),
                "win_rate": float((rets > 0).mean()),
                "T1": third_meds[0] if len(third_meds) > 0 else np.nan,
                "T2": third_meds[1] if len(third_meds) > 1 else np.nan,
                "T3": third_meds[2] if len(third_meds) > 2 else np.nan,
                "worst_third": min(third_meds) if third_meds else np.nan,
                "deployed": float(deploy),
            })
    return pd.DataFrame(rows)


def _fmt(df: pd.DataFrame, pct_cols: list[str]) -> str:
    d = df.copy()
    for c in pct_cols:
        if c in d.columns:
            d[c] = d[c].map(lambda v: "   n/a" if pd.isna(v) else f"{v:+.1%}")
    return d.to_string(index=False)


def run_ticker(ticker: str, category: str) -> None:
    closes = load_closes(ticker, category)
    sig_dates = crash_trigger_days(closes)
    sigs = [closes.index.get_loc(d) for d in sig_dates]
    # The signal needs a next session to trade on.
    sigs = [i for i in sigs if i + 1 < len(closes)]

    print("=" * 78)
    print(f"{ticker}: cash-tranche deployment ladder")
    print("=" * 78)
    print(f"History      : {closes.index.min().date()} to {closes.index.max().date()} "
          f"({len(closes)} sessions)")
    print(f"Trigger      : {CRASH_WINDOW}d ROC <= {CRASH_THRESHOLD:.0%}, "
          f"declustered {DECLUSTER_DAYS} trading days")
    print(f"Episodes     : n={len(sigs)}  "
          f"({sig_dates.min().date()} to {sig_dates.max().date()})")
    print(f"Execution    : fills at close(signal+1) or later; never the signal close")
    print(f"Idle cash    : {CASH_ANNUAL:.0%}/yr, charged on every undeployed tranche")
    print(f"Deploy window: {DEPLOY_WINDOW} trading days from entry")

    dd = part1_conditional_drawdown(closes, sigs)
    print("\n" + "-" * 78)
    print(f"PART 1  further drawdown from the entry close, next {DD_WINDOW} sessions (n={len(dd)})")
    print("-" * 78)
    if len(dd) >= MIN_N:
        q = dd["further_dd"].quantile([0.10, 0.25, 0.50, 0.75, 0.90])
        print(f"  p10 {q[0.10]:+.1%}   p25 {q[0.25]:+.1%}   median {q[0.50]:+.1%}   "
              f"p75 {q[0.75]:+.1%}   p90 {q[0.90]:+.1%}")
        print(f"  median days to trough: {int(dd['days_to_trough'].median())}")
        print("\n  reaches at least:")
        for lvl in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
            frac = float((dd["further_dd"] <= -lvl).mean())
            print(f"    -{lvl:.0%} further : {frac:5.1%}  ({int(frac * len(dd))}/{len(dd)} episodes)")
    else:
        print("  too few episodes")

    print("\n" + "-" * 78)
    print("PART 2  forward return BY ENTRY DEPTH (conditional on the level being reached)")
    print("-" * 78)
    p2 = part2_depth_returns(closes, sigs)
    print(_fmt(p2, ["hit_rate", "median", "win_rate", "hit_x_median"]))
    print("\n  hit_x_median = hit_rate x median: what a tranche parked at that")
    print("  level is worth BEFORE charging the cash it holds while it waits.")
    print("  Read 'median' alone and every deep level looks free.")

    print("\n" + "-" * 78)
    print("PART 3  LADDER COMPARISON -- cash charged, common episode set, date-thirds")
    print("-" * 78)
    p3 = part3_ladders(closes, sigs)
    for h in HORIZONS:
        sub = p3[p3["horizon"] == h].sort_values("worst_third", ascending=False)
        if sub.empty:
            continue
        print(f"\n  horizon {h}d  (ranked on WORST third, per MEMORY.md's standard)")
        print(_fmt(sub.drop(columns=["horizon"]),
                   ["median", "average", "worst", "win_rate",
                    "T1", "T2", "T3", "worst_third", "deployed"]))

    out = PROJECT_ROOT / "comparison_results" / f"{ticker}_cash_tranche_ladder.csv"
    out.parent.mkdir(exist_ok=True)
    p3.to_csv(out, index=False)
    print(f"\n  saved: {out}")


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", default=None)
    p.add_argument("--category", default="equities")
    a = p.parse_args()

    for depth_w in LADDERS.values():
        assert abs(sum(w for _, w in depth_w) - 1.0) < 1e-9, "ladder weights must sum to 1"

    pairs = [(a.ticker, a.category)] if a.ticker else [("AVGO", "equities"), ("LLY", "equities")]
    for t, c in pairs:
        run_ticker(t, c)
        print()

    print("=" * 78)
    print("Caveats that bound every number above:")
    print("  - Episodes are declustered but their 126/252d windows still overlap")
    print("    across 2008/2020/2022 clusters; n is not n independent draws.")
    print("  - Touch detection and fills both use CLOSES. No intraday low is")
    print("    assumed, so a level pierced and recovered within one session")
    print("    does not fill. Conservative for deep tranches.")
    print("  - Idle cash at 2%/yr is generous for an Avanza balance (~0%), so")
    print("    the deep ladders are flattered, not penalised, on this axis.")
    print("  - This prices DEPLOYING a standing cash position, not holding one.")
    print("    Whether 10% cash should exist at all is a separate question and")
    print("    was decided by the operator, not by this test.")
    print("=" * 78)


if __name__ == "__main__":
    main()
