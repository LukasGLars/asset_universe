"""
run_btc_full_economics.py

First model of the operator's ACTUAL setup end to end. Every prior BTC run
in this file omitted at least one leg. Now all of them are pinned down:

  Instrument : Virtune Sustainable Bitcoin ETP (SE0020845709), 1.49%/yr
               management fee. The only Virtune BTC ETP on Avanza, so the
               0.25% Prime product is NOT an option -- 1.49% is a constraint,
               not a choice.
  Currency   : SEK-denominated, tracking a USD asset
               -> BTC_SEK = BTC_USD x USDSEK
  Signal     : read off BITCOIN'S OWN PRICE (BTC-USD). Operator's stated
               thesis -- the ETP is a vessel, Bitcoin is the asset. This is
               a prior, not a post-hoc pick, and is mechanically the right
               call: trending BTC_SEK would contaminate a Bitcoin-momentum
               signal with unrelated SEK/USD moves.
  Execution  : Swedish exchange, weekday-only position changes.

THE LEG THAT WAS NEVER MODELLED, AND IT FAVOURS THE STRATEGY:
a 1.49%/yr fee is paid only while you HOLD the ETP. Buy-and-hold pays it
every single day. A trend strategy sitting out ~41% of the time pays only
~59% of it -- roughly 0.6%/yr saved. Every earlier run charged the trend arm
its trading costs while giving buy-and-hold its fee for free, which
systematically understated the strategy.

So the honest comparison charges BOTH arms properly:
  buy-and-hold : BTC_SEK returns, minus 1.49%/yr accrued daily, always
  trend        : BTC_SEK returns while long, minus 1.49%/yr accrued daily
                 ONLY while long, minus a spread cost on every flip

Virtune's real bid/ask spread is unknown and not published, so it is SWEPT
rather than guessed, and the break-even spread is solved for explicitly --
that number is checkable against Avanza's order book, which is the one
input the operator can verify himself.

Printed only. Temporary diagnostic -- delete after logging.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from asset_universe import config

DATA_DIR = config.raw_data_dir()

BARS_PER_YEAR = 365.0
MGMT_FEE_ANNUAL = 0.0149          # Virtune Sustainable Bitcoin ETP
DAILY_FEE = MGMT_FEE_ANNUAL / BARS_PER_YEAR
WINDOWS = [50, 100, 150, 200, 250]


def perf(equity: pd.Series) -> dict:
    r = equity.pct_change().dropna()
    yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = float(equity.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 else 0.0
    dd = equity / equity.cummax() - 1
    maxdd = float(dd.min())
    sharpe = float(r.mean() / r.std() * np.sqrt(BARS_PER_YEAR)) if r.std() > 0 else 0.0
    calmar = cagr / abs(maxdd) if maxdd != 0 else 0.0
    return {"cagr": cagr, "sharpe": sharpe, "maxdd": maxdd, "calmar": calmar}


def etp_position(signal_price: pd.Series, window: int) -> pd.Series:
    """Long when signal_price > SMA(window). shift(1) so the signal day's own
    move is never captured; weekday-only so a Sat/Sun change waits for
    Monday."""
    sig = (signal_price > signal_price.rolling(window).mean()).astype(float).shift(1)
    return sig.where(sig.index.dayofweek < 5).ffill().fillna(0.0)


def trend_equity(position: pd.Series, ret: pd.Series, spread: float) -> pd.Series:
    """Fee accrues daily ONLY while held; spread charged on every flip."""
    flips = position.diff().abs().fillna(0.0)
    daily = position * ret - position * DAILY_FEE - flips * spread
    return (1 + daily.fillna(0.0)).cumprod()


def hold_equity(ret: pd.Series) -> pd.Series:
    """Buy-and-hold the ETP: full exposure, and the fee every single day."""
    return (1 + (ret - DAILY_FEE).fillna(0.0)).cumprod()


def load_usdsek() -> pd.Series:
    path = DATA_DIR / "fx" / "USDSEK=X.parquet"
    if path.exists():
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")["close"].sort_index().dropna()
    fx = yf.Ticker("USDSEK=X").history(period="max")["Close"]
    fx.index = pd.to_datetime(fx.index.date)
    return fx.sort_index().dropna()


def breakeven_spread(position: pd.Series, ret: pd.Series,
                     hold_cagr: float, lo=0.0, hi=0.20) -> float | None:
    """Spread at which the trend arm's CAGR falls to buy-and-hold's."""
    def f(sp):
        return perf(trend_equity(position, ret, sp))["cagr"] - hold_cagr
    if f(lo) <= 0:
        return None
    if f(hi) > 0:
        return float("inf")
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main() -> None:
    btc = yf.Ticker("BTC-USD").history(period="max")["Close"]
    btc.index = pd.to_datetime(btc.index.date)
    btc_usd = btc.sort_index().dropna()

    usdsek_raw = load_usdsek()
    start = max(btc_usd.index[0], usdsek_raw.index[0])
    end = min(btc_usd.index[-1], usdsek_raw.index[-1])
    btc_usd = btc_usd.loc[start:end]
    usdsek = usdsek_raw.reindex(btc_usd.index).ffill().bfill()
    btc_sek = btc_usd * usdsek
    ret_sek = btc_sek.pct_change()

    print(f"Sample   : {start.date()} -> {end.date()}  ({len(btc_usd)} bars)")
    print(f"Fee      : {MGMT_FEE_ANNUAL:.2%}/yr, accrued daily, paid ONLY while holding")
    print(f"Signal   : BTC-USD (Bitcoin's own price) | Returns: SEK | Exec: weekday-only\n")

    s = btc_usd.rolling(max(WINDOWS)).mean().dropna().index[0]
    r = ret_sek.loc[s:]

    hold = hold_equity(r)
    p_hold = perf(hold / hold.iloc[0])

    # ── Full-cost comparison, per window ───────────────────────────────────
    print("=" * 98)
    print("FULL ECONOMICS -- fee charged correctly to BOTH arms (spread 50bp/flip)")
    print("=" * 98)
    print(f"  {'Win':>4} {'InMkt':>6} {'Fee paid':>9} {'Flips/yr':>9}  "
          f"{'CAGR':>8} {'MaxDD':>8} {'Calmar':>8}  {'vs Hold':>8}")
    print(f"  {'-'*76}")
    print(f"  {'HOLD':>4} {'100%':>6} {MGMT_FEE_ANNUAL:>8.2%} {'0.0':>9}  "
          f"{p_hold['cagr']:>+8.1%} {p_hold['maxdd']:>+8.1%} {p_hold['calmar']:>8.3f}  {'--':>8}")

    yrs = (r.index[-1] - r.index[0]).days / 365.25
    per_window = {}
    for w in WINDOWS:
        pos = etp_position(btc_usd, w).loc[s:]
        eq = trend_equity(pos, r, 0.0050)
        p = perf(eq / eq.iloc[0])
        in_mkt = float(pos.mean())
        flips_yr = float(pos.diff().abs().fillna(0).sum()) / yrs
        per_window[w] = (p, pos, in_mkt, flips_yr)
        print(f"  {w:>4} {in_mkt:>6.0%} {MGMT_FEE_ANNUAL*in_mkt:>8.2%} {flips_yr:>9.1f}  "
              f"{p['cagr']:>+8.1%} {p['maxdd']:>+8.1%} {p['calmar']:>8.3f}  "
              f"{p['calmar']-p_hold['calmar']:>+8.3f}")
    print()

    # ── Spread sweep on the two live candidates ────────────────────────────
    print("=" * 98)
    print("SPREAD SWEEP -- Virtune's real spread is unpublished, so solve for it")
    print("=" * 98)
    cands = [50, 150]
    header = "  " + f"{'Spread/flip':>12}" + "".join(f"{f'{w}d Calmar':>14}" for w in cands)
    print(header)
    print(f"  {'-'*(12 + 14*len(cands))}")
    for sp in [0.0000, 0.0025, 0.0050, 0.0100, 0.0200, 0.0300]:
        line = f"  {sp*1e4:>10.0f}bp"
        for w in cands:
            pos = per_window[w][1]
            eq = trend_equity(pos, r, sp)
            line += f"{perf(eq / eq.iloc[0])['calmar']:>14.3f}"
        print(line)
    print(f"  {'HOLD':>12}" + "".join(f"{p_hold['calmar']:>14.3f}" for _ in cands))

    print("\n  Break-even spread (trend CAGR falls to buy-and-hold's):")
    for w in cands:
        be = breakeven_spread(per_window[w][1], r, p_hold["cagr"])
        if be is None:
            txt = "already below hold at 0bp"
        elif be == float("inf"):
            txt = "beats hold even at 2000bp"
        else:
            txt = f"{be*1e4:.0f}bp per flip  ({per_window[w][3]:.1f} flips/yr)"
        print(f"    {w}d: {txt}")
    print()

    # ── Post-2020 under full economics ─────────────────────────────────────
    print("=" * 98)
    print("POST-2020 under full economics (50bp/flip)")
    print("=" * 98)
    s20 = pd.Timestamp("2020-01-01")
    r20 = ret_sek.loc[s20:]
    h20 = hold_equity(r20)
    p_h20 = perf(h20 / h20.iloc[0])
    print(f"  {'Variant':<16} {'CAGR':>9} {'MaxDD':>9} {'Calmar':>9} {'vs Hold':>9}")
    print(f"  {'-'*56}")
    print(f"  {'HOLD':<16} {p_h20['cagr']:>+9.1%} {p_h20['maxdd']:>+9.1%} "
          f"{p_h20['calmar']:>9.3f} {'--':>9}")
    for w in WINDOWS:
        pos = etp_position(btc_usd, w).loc[s20:]
        eq = trend_equity(pos, r20, 0.0050)
        p = perf(eq / eq.iloc[0])
        print(f"  {str(w)+'d':<16} {p['cagr']:>+9.1%} {p['maxdd']:>+9.1%} "
              f"{p['calmar']:>9.3f} {p['calmar']-p_h20['calmar']:>+9.3f}")
    print()

    # ── What the fee leg alone is worth ────────────────────────────────────
    print("=" * 98)
    print("ISOLATING THE FEE EFFECT -- how much of the edge is just avoided fee?")
    print("=" * 98)
    w = 150
    pos = per_window[w][1]
    with_fee = perf(trend_equity(pos, r, 0.0050) / trend_equity(pos, r, 0.0050).iloc[0])
    # same strategy, but charged the fee every day like buy-and-hold is
    flips = pos.diff().abs().fillna(0.0)
    naive = (1 + (pos * r - DAILY_FEE - flips * 0.0050).fillna(0.0)).cumprod()
    p_naive = perf(naive / naive.iloc[0])
    print(f"  150d, fee only while held   : CAGR {with_fee['cagr']:+.1%}  "
          f"Calmar {with_fee['calmar']:.3f}")
    print(f"  150d, fee charged every day : CAGR {p_naive['cagr']:+.1%}  "
          f"Calmar {p_naive['calmar']:.3f}")
    print(f"  -> the avoided-fee leg is worth {with_fee['cagr']-p_naive['cagr']:+.2%} CAGR "
          f"({MGMT_FEE_ANNUAL*(1-per_window[w][2]):.2%}/yr expected).")


if __name__ == "__main__":
    main()
