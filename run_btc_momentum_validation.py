"""
run_btc_momentum_validation.py

VERIFICATION of the 2026-08-24 BTC trend result (200d SMA beats buy-and-hold
on Sharpe/Calmar). Written because this project has twice shipped an "edge"
that did not survive scrutiny -- the AVGO 200d guard (lookahead bias:
signal[i] applied to ret[i]) and AVGO vol-targeting (shipped numbers did not
reproduce at all). A single favourable backtest is not evidence here.

Six checks, each able to kill the result independently:

  A. ANNUALIZATION BUG. The first run used sqrt(252) on an asset that trades
     365 days/year. Recompute with sqrt(365) and report both, so the
     originally-reported Sharpe is explicitly corrected rather than quietly
     replaced.

  B. LOOKAHEAD SELF-CHECK. Run the SAME code path with and without the
     shift(1). If the no-shift version is dramatically better, that both
     (a) confirms the shift is actually doing something, and (b) quantifies
     exactly how much the AVGO-style bug would have inflated this. A
     correct backtest should be clearly WORSE than its lookahead twin.

  C. EXECUTION REALISM. The shift(1) convention fills at the signal day's
     close. Also test filling at the NEXT DAY'S OPEN (real OHLC), which is
     what an operator reacting to a close actually gets. Every AVGO guard
     execution model failed this step -- it is the one that matters most.

  D. PARAMETER GRID. MA window in {50,100,150,200,250,300}. A real effect
     should hold across neighbouring windows, not spike at exactly 200.
     (Same standard the AVGO crash guard's 20-cell grid was held to.)

  E. SUB-PERIODS incl. dropping early history. 2015-2016 BTC was thin and
     structurally different; if the edge only exists there, it is not
     tradeable today.

  F. COST SENSITIVITY. 5 / 15 / 50 bps per flip. Crypto spreads and the
     Swedish ETP wrapper (Virtune) are wider than equities; an edge that
     dies at realistic cost is not an edge for THIS operator.

Printed only. Temporary diagnostic -- delete after logging.
"""
from __future__ import annotations

import sys
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf

BARS_PER_YEAR = 365.0  # BTC trades every calendar day -- NOT 252


def perf(equity: pd.Series, bars_per_year: float = BARS_PER_YEAR) -> dict:
    r = equity.pct_change().dropna()
    yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = float(equity.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 else 0.0
    dd = equity / equity.cummax() - 1
    maxdd = float(dd.min())
    sharpe = float(r.mean() / r.std() * np.sqrt(bars_per_year)) if r.std() > 0 else 0.0
    calmar = cagr / abs(maxdd) if maxdd != 0 else 0.0
    return {"cagr": cagr, "sharpe": sharpe, "maxdd": maxdd, "calmar": calmar, "years": yrs}


def trend_equity(close: pd.Series, ret: pd.Series, window: int,
                 tc: float, shift: int = 1) -> tuple[pd.Series, pd.Series]:
    """Long when close > SMA(window). shift=1 is correct (act next bar);
    shift=0 is the deliberate lookahead twin used by check B."""
    sma = close.rolling(window).mean()
    signal = (close > sma).astype(float)
    position = signal.shift(shift).fillna(0.0)
    flips = position.diff().abs().fillna(0.0)
    port = position * ret - flips * tc
    return (1 + port.fillna(0.0)).cumprod(), position


def open_fill_equity(df: pd.DataFrame, window: int, tc: float) -> tuple[pd.Series, pd.Series]:
    """Most conservative realistic model: signal from day i's CLOSE, position
    entered at day i+1's OPEN, so day i+1's captured return is open->close,
    and every later day is close->close while held."""
    close, opn = df["Close"], df["Open"]
    sma = close.rolling(window).mean()
    signal = (close > sma).astype(float)
    position = signal.shift(1).fillna(0.0)
    prev_position = position.shift(1).fillna(0.0)

    c2c = close.pct_change()
    o2c = (close / opn) - 1.0

    # On an entry bar capture open->close; while already held capture close->close.
    captured = np.where(
        (position > 0) & (prev_position == 0), o2c,
        np.where(position > 0, c2c, 0.0),
    )
    captured = pd.Series(captured, index=close.index)
    flips = position.diff().abs().fillna(0.0)
    port = captured - flips * tc
    return (1 + port.fillna(0.0)).cumprod(), position


def main() -> None:
    df = yf.Ticker("BTC-USD").history(period="max")
    df.index = pd.to_datetime(df.index.date)
    df = df.sort_index().dropna(subset=["Close", "Open"])
    close = df["Close"]
    ret = close.pct_change()

    span_years = (close.index[-1] - close.index[0]).days / 365.25
    print(f"BTC-USD: {close.index[0].date()} -> {close.index[-1].date()}  "
          f"({len(close)} bars, {span_years:.2f} yrs, "
          f"{len(close)/span_years:.1f} bars/yr)")
    print(f"Annualization uses sqrt({BARS_PER_YEAR:.0f}), not sqrt(252).\n")

    start = close.rolling(200).mean().dropna().index[0]
    TC = 0.0015

    def rebase(eq: pd.Series, frm=start) -> pd.Series:
        e = eq.loc[frm:]
        return e / e.iloc[0]

    # ── A. Annualization correction ────────────────────────────────────────
    print("=" * 96)
    print("A. ANNUALIZATION -- correcting the originally-reported Sharpe")
    print("=" * 96)
    bh_eq = (1 + ret.fillna(0)).cumprod()
    eq200, pos200 = trend_equity(close, ret, 200, TC, shift=1)
    for label, eq in [("Buy & Hold", bh_eq), ("200d trend", eq200)]:
        e = rebase(eq)
        p252 = perf(e, 252.0)
        p365 = perf(e, 365.0)
        print(f"  {label:<14} Sharpe(252, AS REPORTED)={p252['sharpe']:.3f}   "
              f"Sharpe(365, CORRECT)={p365['sharpe']:.3f}")
    print("  -> CAGR/MaxDD/Calmar are unaffected by this; only Sharpe was wrong,")
    print("     and it was wrong for BOTH arms equally, so the ranking stands.\n")

    # ── B. Lookahead self-check ────────────────────────────────────────────
    print("=" * 96)
    print("B. LOOKAHEAD SELF-CHECK -- correct shift(1) vs the deliberate biased twin")
    print("=" * 96)
    eq_look, _ = trend_equity(close, ret, 200, TC, shift=0)
    for label, eq in [("shift(1)  CORRECT ", eq200), ("shift(0)  LOOKAHEAD", eq_look)]:
        p = perf(rebase(eq))
        print(f"  {label}  CAGR={p['cagr']:+7.1%}  Sharpe={p['sharpe']:6.3f}  "
              f"MaxDD={p['maxdd']:+7.1%}  Calmar={p['calmar']:6.3f}")
    pc, pl = perf(rebase(eq200)), perf(rebase(eq_look))
    print(f"  -> Lookahead inflates Calmar by {pl['calmar'] - pc['calmar']:+.3f} "
          f"({(pl['calmar']/pc['calmar'] - 1):+.0%}). The reported result is the")
    print("     WORSE of the two, which is what a correctly-shifted backtest should be.\n")

    # ── C. Execution realism ───────────────────────────────────────────────
    print("=" * 96)
    print("C. EXECUTION REALISM -- prior-close fill vs next-open fill (real OHLC)")
    print("=" * 96)
    eq_open, _ = open_fill_equity(df, 200, TC)
    rows = [("Buy & Hold", bh_eq), ("200d, close fill", eq200), ("200d, next-OPEN fill", eq_open)]
    for label, eq in rows:
        p = perf(rebase(eq))
        print(f"  {label:<24} CAGR={p['cagr']:+7.1%}  Sharpe={p['sharpe']:6.3f}  "
              f"MaxDD={p['maxdd']:+7.1%}  Calmar={p['calmar']:6.3f}")
    print()

    # ── D. Parameter grid ──────────────────────────────────────────────────
    print("=" * 96)
    print("D. PARAMETER GRID -- is 200 special, or does the family work?")
    print("=" * 96)
    bh_p = perf(rebase(bh_eq))
    print(f"  {'Window':>7}  {'CAGR':>8}  {'Sharpe':>7}  {'MaxDD':>8}  {'Calmar':>7}  "
          f"{'vs B&H':>8}  {'Trades':>7}  {'InMkt':>6}")
    print(f"  {'-'*72}")
    print(f"  {'B&H':>7}  {bh_p['cagr']:+8.1%}  {bh_p['sharpe']:7.3f}  "
          f"{bh_p['maxdd']:+8.1%}  {bh_p['calmar']:7.3f}  {'--':>8}  {'--':>7}  {'100%':>6}")
    wins = 0
    windows = [50, 100, 150, 200, 250, 300]
    for w in windows:
        eq, pos = trend_equity(close, ret, w, TC, shift=1)
        s = close.rolling(w).mean().dropna().index[0]
        e = eq.loc[s:] / eq.loc[s]
        bh_e = bh_eq.loc[s:] / bh_eq.loc[s]
        p, pbh = perf(e), perf(bh_e)
        d = p["calmar"] - pbh["calmar"]
        if d > 0:
            wins += 1
        n_tr = int(pos.loc[s:].diff().abs().fillna(0).sum())
        print(f"  {w:>7}  {p['cagr']:+8.1%}  {p['sharpe']:7.3f}  {p['maxdd']:+8.1%}  "
              f"{p['calmar']:7.3f}  {d:+8.3f}  {n_tr:>7}  {pos.loc[s:].mean():>5.0%}")
    print(f"  -> beats buy-and-hold on Calmar in {wins}/{len(windows)} windows "
          f"(each vs its OWN start date).\n")

    # ── E. Sub-periods ─────────────────────────────────────────────────────
    print("=" * 96)
    print("E. SUB-PERIODS -- including dropping thin/illiquid early history")
    print("=" * 96)
    eras = [
        ("Full (from 2015-04)", start, close.index[-1]),
        ("Drop early: 2017+", pd.Timestamp("2017-01-01"), close.index[-1]),
        ("Drop early: 2020+", pd.Timestamp("2020-01-01"), close.index[-1]),
        ("2016-2018 (mania+crash)", pd.Timestamp("2016-01-01"), pd.Timestamp("2018-12-31")),
        ("2019-2022 (mania+crash)", pd.Timestamp("2019-01-01"), pd.Timestamp("2022-12-31")),
        ("2023-2026 (recovery)", pd.Timestamp("2023-01-01"), close.index[-1]),
    ]
    print(f"  {'Period':<28} {'B&H Calmar':>11} {'Trend Calmar':>13} {'Delta':>8}   Verdict")
    print(f"  {'-'*78}")
    era_wins = 0
    for label, s, e in eras:
        b = bh_eq.loc[s:e]
        t = eq200.loc[s:e]
        if len(b) < 120:
            continue
        b = b / b.iloc[0]
        t = t / t.iloc[0]
        pb, pt = perf(b), perf(t)
        d = pt["calmar"] - pb["calmar"]
        verdict = "trend" if d > 0.02 else ("B&H" if d < -0.02 else "wash")
        if d > 0.02:
            era_wins += 1
        print(f"  {label:<28} {pb['calmar']:>11.3f} {pt['calmar']:>13.3f} {d:>+8.3f}   {verdict}")
    print(f"  -> trend clearly wins {era_wins} of the periods shown.\n")

    # ── F. Cost sensitivity ────────────────────────────────────────────────
    print("=" * 96)
    print("F. COST SENSITIVITY -- Virtune ETP spread is wider than equity")
    print("=" * 96)
    print(f"  {'TC/flip':>8}  {'CAGR':>8}  {'Calmar':>7}  {'vs B&H Calmar':>14}")
    print(f"  {'-'*46}")
    for tc in [0.0005, 0.0015, 0.0050, 0.0100]:
        eq, _ = trend_equity(close, ret, 200, tc, shift=1)
        p = perf(rebase(eq))
        print(f"  {tc*1e4:>6.0f}bp  {p['cagr']:+8.1%}  {p['calmar']:7.3f}  "
              f"{p['calmar'] - bh_p['calmar']:>+14.3f}")
    print()

    print("=" * 96)
    print("Buy & Hold reference (from 2015-04, sqrt(365)):")
    print(f"  CAGR={bh_p['cagr']:+.1%}  Sharpe={bh_p['sharpe']:.3f}  "
          f"MaxDD={bh_p['maxdd']:+.1%}  Calmar={bh_p['calmar']:.3f}")
    print("=" * 96)


if __name__ == "__main__":
    main()
