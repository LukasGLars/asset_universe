"""
run_btc_etp_execution_check.py

The 2026-08-24 BTC trend validation passed its execution-realism check on the
explicit reasoning that BTC trades 24/7, so there is no gap between a signal
close and the next tradeable price. **That reasoning does not hold for the
instrument the operator actually owns.** Virtune Bitcoin is a Swedish-listed
ETP on ~252 exchange days/yr. BTC keeps moving nights and weekends; the ETP
cannot be traded then. A Friday-close signal is not actionable until Monday,
with two full days of BTC movement in between -- structurally the same
signal-to-fill gap that voided the AVGO 200d guard.

This re-runs the trend test with that constraint made explicit:

  - Returns still accrue every calendar day (the ETP prices in the weekend
    move at Monday's open -- you are exposed to it if you were holding).
  - POSITION CAN ONLY CHANGE ON A WEEKDAY. A signal that fires Saturday is
    filled Monday, not Sunday.

Compares, per MA window:
  SPOT      -- daily rebalancing, what the passing test assumed (24/7 venue)
  ETP       -- weekday-only rebalancing, what the operator can actually do
  B&H       -- reference

Also sizes the weekend-gap exposure directly: how much BTC movement happens
across weekends that no ETP holder can react to.

Windows include 50 and 150, not just 200 -- the grid showed 200 is the
WEAKEST member of the family, so testing only 200 would understate the
family and mislead the decision.

Printed only. Temporary diagnostic -- delete after logging.
"""
from __future__ import annotations

import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf

BARS_PER_YEAR = 365.0
WINDOWS = [50, 100, 150, 200, 250]
TC = 0.0015


def perf(equity: pd.Series, bars_per_year: float = BARS_PER_YEAR) -> dict:
    r = equity.pct_change().dropna()
    yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = float(equity.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 else 0.0
    dd = equity / equity.cummax() - 1
    maxdd = float(dd.min())
    sharpe = float(r.mean() / r.std() * np.sqrt(bars_per_year)) if r.std() > 0 else 0.0
    calmar = cagr / abs(maxdd) if maxdd != 0 else 0.0
    return {"cagr": cagr, "sharpe": sharpe, "maxdd": maxdd, "calmar": calmar}


def raw_signal(close: pd.Series, window: int) -> pd.Series:
    """Long when close > SMA(window), computed on that day's close."""
    return (close > close.rolling(window).mean()).astype(float)


def spot_position(close: pd.Series, window: int) -> pd.Series:
    """24/7 venue: act on the very next bar (shift 1). What the passing
    execution test assumed."""
    return raw_signal(close, window).shift(1).fillna(0.0)


def etp_position(close: pd.Series, window: int) -> pd.Series:
    """Swedish ETP: position may only CHANGE on a weekday. A signal from any
    day is carried forward until the next weekday bar, where it is applied
    from the following bar onward (still no same-bar fill).

    Implementation: take the shift(1) signal, then blank it on non-weekdays
    and forward-fill -- so a Sat/Sun signal change cannot take effect until
    Monday's bar."""
    desired = raw_signal(close, window).shift(1)
    is_weekday = desired.index.dayofweek < 5      # Mon-Fri
    tradeable = desired.where(is_weekday)          # NaN on Sat/Sun
    return tradeable.ffill().fillna(0.0)


def equity_from_position(position: pd.Series, ret: pd.Series, tc: float) -> pd.Series:
    flips = position.diff().abs().fillna(0.0)
    port = position * ret - flips * tc
    return (1 + port.fillna(0.0)).cumprod()


def main() -> None:
    df = yf.Ticker("BTC-USD").history(period="max")
    df.index = pd.to_datetime(df.index.date)
    df = df.sort_index().dropna(subset=["Close"])
    close = df["Close"]
    ret = close.pct_change()

    print(f"BTC-USD: {close.index[0].date()} -> {close.index[-1].date()}  ({len(close)} bars)")
    n_weekday = int((close.index.dayofweek < 5).sum())
    print(f"Weekday bars (ETP-tradeable): {n_weekday}  "
          f"({n_weekday/len(close):.1%})  |  weekend bars: {len(close)-n_weekday}\n")

    # ── Weekend gap exposure -- how much movement is unreactable? ───────────
    print("=" * 92)
    print("WEEKEND GAP EXPOSURE -- BTC movement no ETP holder can react to")
    print("=" * 92)
    # Fri close -> Mon close, i.e. what a Monday-open ETP trader wakes up to.
    fri = close[close.index.dayofweek == 4]
    weekend_moves = []
    for d, px in fri.items():
        mon = d + pd.Timedelta(days=3)
        # nearest available bar within 3-5 days (handles missing bars)
        future = close.loc[close.index > d]
        if future.empty:
            continue
        nxt = future.iloc[0:3]
        cand = nxt[nxt.index >= mon]
        if cand.empty:
            continue
        weekend_moves.append(cand.iloc[0] / px - 1.0)
    wm = pd.Series(weekend_moves).dropna()
    print(f"  Fri-close -> Mon-close moves: n={len(wm)}")
    print(f"    median |move| : {wm.abs().median():.2%}")
    print(f"    mean   |move| : {wm.abs().mean():.2%}")
    print(f"    90th pct|move|: {wm.abs().quantile(0.90):.2%}")
    print(f"    worst down    : {wm.min():.2%}")
    print(f"    best up       : {wm.max():.2%}")
    print(f"    |move| > 5%   : {(wm.abs() > 0.05).mean():.1%} of weekends")
    print(f"    |move| > 10%  : {(wm.abs() > 0.10).mean():.1%} of weekends\n")

    # ── SPOT vs ETP execution, per window ──────────────────────────────────
    print("=" * 92)
    print("SPOT (24/7, daily rebalance) vs ETP (weekday-only rebalance)")
    print("=" * 92)
    print(f"  {'Win':>4}  {'SPOT CAGR':>10} {'SPOT Calm':>10}  "
          f"{'ETP CAGR':>10} {'ETP Calm':>10}  {'ETP-B&H':>9}  {'Lost':>7}")
    print(f"  {'-'*70}")

    results = {}
    for w in WINDOWS:
        s = close.rolling(w).mean().dropna().index[0]
        r_sub = ret.loc[s:]
        bh = (1 + r_sub.fillna(0)).cumprod()
        p_bh = perf(bh)

        eq_spot = equity_from_position(spot_position(close, w).loc[s:], r_sub, TC)
        eq_etp = equity_from_position(etp_position(close, w).loc[s:], r_sub, TC)
        p_s, p_e = perf(eq_spot), perf(eq_etp)
        results[w] = (p_bh, p_s, p_e)

        lost = p_e["calmar"] - p_s["calmar"]
        print(f"  {w:>4}  {p_s['cagr']:>+10.1%} {p_s['calmar']:>10.3f}  "
              f"{p_e['cagr']:>+10.1%} {p_e['calmar']:>10.3f}  "
              f"{p_e['calmar']-p_bh['calmar']:>+9.3f}  {lost:>+7.3f}")

    print("\n  'ETP-B&H' = does the tradeable version still beat buy-and-hold?")
    print("  'Lost'    = Calmar given up purely to the weekday-only constraint.\n")

    # ── Decision-relevant window: post-2020 only ───────────────────────────
    print("=" * 92)
    print("POST-2020 ONLY (the decision-relevant regime, per the 2026-08-24 finding)")
    print("=" * 92)
    s2020 = pd.Timestamp("2020-01-01")
    r20 = ret.loc[s2020:]
    bh20 = (1 + r20.fillna(0)).cumprod()
    p_bh20 = perf(bh20)
    print(f"  {'Win':>4}  {'ETP CAGR':>10} {'ETP Calm':>10}  {'vs B&H':>9}   Verdict")
    print(f"  {'-'*56}")
    print(f"  {'B&H':>4}  {p_bh20['cagr']:>+10.1%} {p_bh20['calmar']:>10.3f}  "
          f"{'--':>9}")
    etp_wins_2020 = 0
    for w in WINDOWS:
        eq = equity_from_position(etp_position(close, w).loc[s2020:], r20, TC)
        p = perf(eq)
        d = p["calmar"] - p_bh20["calmar"]
        verdict = "trend" if d > 0.02 else ("B&H" if d < -0.02 else "wash")
        if d > 0.02:
            etp_wins_2020 += 1
        print(f"  {w:>4}  {p['cagr']:>+10.1%} {p['calmar']:>10.3f}  {d:>+9.3f}   {verdict}")
    print(f"  -> tradeable-ETP trend beats B&H post-2020 in "
          f"{etp_wins_2020}/{len(WINDOWS)} windows.\n")

    # ── Cost sensitivity on the ETP model, best window ─────────────────────
    best_w = max(WINDOWS, key=lambda w: results[w][2]["calmar"])
    print("=" * 92)
    print(f"COST SENSITIVITY on the ETP-tradeable model (best window = {best_w}d, full sample)")
    print("=" * 92)
    s = close.rolling(best_w).mean().dropna().index[0]
    r_sub = ret.loc[s:]
    p_bh_full = perf((1 + r_sub.fillna(0)).cumprod())
    print(f"  {'TC/flip':>8}  {'CAGR':>9}  {'Calmar':>8}  {'vs B&H':>9}")
    print(f"  {'-'*40}")
    for tc in [0.0005, 0.0015, 0.0050, 0.0100, 0.0150]:
        eq = equity_from_position(etp_position(close, best_w).loc[s:], r_sub, tc)
        p = perf(eq)
        print(f"  {tc*1e4:>6.0f}bp  {p['cagr']:>+9.1%}  {p['calmar']:>8.3f}  "
              f"{p['calmar']-p_bh_full['calmar']:>+9.3f}")
    print("\n  NOTE: Virtune's annual management fee is a separate, additive drag")
    print("  and is NOT modelled anywhere above -- it applies to buy-and-hold too.")


if __name__ == "__main__":
    main()
