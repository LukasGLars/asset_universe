"""Temporary one-off: does a simple BTC trend/momentum rule actually
capture rallies better than buy-and-hold? Full real history via yfinance.

CRITICAL: signal computed from day i's CLOSE is applied starting day i+1's
return (shift(1)) -- the AVGO guard's entire validated edge turned out to
be lookahead bias (signal[i] applied to return[i], impossible to trade),
so this is built shift-correct from the start, not retrofitted.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf


def perf(equity: pd.Series) -> dict:
    r = equity.pct_change().dropna()
    yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = float(equity.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 else 0.0
    dd = equity / equity.cummax() - 1
    maxdd = float(dd.min())
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
    calmar = cagr / abs(maxdd) if maxdd != 0 else 0.0
    return {"cagr": cagr, "sharpe": sharpe, "maxdd": maxdd, "calmar": calmar, "years": yrs}


def main() -> None:
    btc_df = yf.Ticker("BTC-USD").history(period="max")
    btc = btc_df["Close"]
    btc.index = pd.to_datetime(btc.index.date)
    btc = btc.sort_index().dropna()
    print(f"BTC-USD full history: {btc.index[0].date()} to {btc.index[-1].date()} "
          f"({len(btc)} trading days)")

    ret = btc.pct_change()
    TC = 0.0015  # 15bps per side, crypto-realistic

    # --- Buy & hold ---
    bh_eq = (1 + ret.fillna(0)).cumprod()

    # --- 200d SMA trend rule, shift(1) correct ---
    sma200 = btc.rolling(200).mean()
    signal_200 = (btc > sma200).astype(float)          # computed on day i's close
    position_200 = signal_200.shift(1).fillna(0)        # ACTED ON starting day i+1
    trades_200 = position_200.diff().abs().fillna(0)
    port_200 = position_200 * ret - trades_200 * TC
    eq_200 = (1 + port_200.fillna(0)).cumprod()

    # --- Golden cross: 50d SMA vs 200d SMA, shift(1) correct ---
    sma50 = btc.rolling(50).mean()
    signal_gc = (sma50 > sma200).astype(float)
    position_gc = signal_gc.shift(1).fillna(0)
    trades_gc = position_gc.diff().abs().fillna(0)
    port_gc = position_gc * ret - trades_gc * TC
    eq_gc = (1 + port_gc.fillna(0)).cumprod()

    common_start = sma200.dropna().index[0]
    for label, eq, pos in [
        ("Buy & Hold", bh_eq, None),
        ("200d SMA trend (shift-1 correct)", eq_200, position_200),
        ("Golden cross 50/200 (shift-1 correct)", eq_gc, position_gc),
    ]:
        eq_c = eq.loc[common_start:] / eq.loc[common_start]
        p = perf(eq_c)
        extra = ""
        if pos is not None:
            n_trades = int(pos.loc[common_start:].diff().abs().fillna(0).sum())
            pct_in = float(pos.loc[common_start:].mean())
            extra = f"  trades={n_trades}  time_in_market={pct_in:.0%}"
        print(f"{label:<40} CAGR={p['cagr']:+7.1%}  Sharpe={p['sharpe']:6.3f}  "
              f"MaxDD={p['maxdd']:+7.1%}  Calmar={p['calmar']:6.3f}{extra}")

    print(f"\nCommon start (200d SMA available): {common_start.date()}")

    # Sub-period check: does the verdict hold across different eras, not just full-sample?
    print("\nSub-period check (200d trend vs buy&hold, Calmar):")
    eras = [
        ("2016-2018 (incl. 2017 mania + 2018 crash)", "2016-01-01", "2018-12-31"),
        ("2019-2022 (incl. 2021 mania + 2022 crash)", "2019-01-01", "2022-12-31"),
        ("2023-2026 (recovery + current)", "2023-01-01", "2026-12-31"),
    ]
    for label, start, end in eras:
        s, e = pd.Timestamp(start), pd.Timestamp(end)
        bh_sub = bh_eq.loc[s:e]
        tr_sub = eq_200.loc[s:e]
        if len(bh_sub) < 50:
            continue
        bh_sub = bh_sub / bh_sub.iloc[0]
        tr_sub = tr_sub / tr_sub.iloc[0]
        p_bh, p_tr = perf(bh_sub), perf(tr_sub)
        print(f"  {label:<45} B&H Calmar={p_bh['calmar']:6.3f}  "
              f"Trend Calmar={p_tr['calmar']:6.3f}")


if __name__ == "__main__":
    main()
