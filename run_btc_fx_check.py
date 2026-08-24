"""
run_btc_fx_check.py

Closes gap #1 from the 2026-08-24 ETP-execution entry: every BTC trend
number so far was computed on BTC-USD, but the operator holds **Virtune
Bitcoin, a SEK-denominated Swedish ETP tracking a USD asset**. The SEK/USD
leg was absent entirely, which is why that entry refused to call the result
decision-ready.

Model, matching the repo's own convention (`portfolio.py`:
`price_sek = price * usdsek`, `USDSEK=X` in the `fx` category):

    BTC_SEK = BTC_USD x USDSEK

Holding the ETP is therefore long BTC **and** long USD vs SEK simultaneously.
Sitting flat is SEK cash: no BTC exposure and no FX exposure (cash earns 0
here -- deliberately conservative, it understates the flat arm).

USDSEK trades weekdays only while BTC trades 365 days, so FX is reindexed
onto BTC's daily index and forward-filled. That is the correct treatment,
not a fudge: over a weekend the FX rate genuinely has not moved, and
Monday's bar then carries both the weekend BTC move and the FX gap at once
-- exactly what the ETP holder actually experiences on Monday's open.

TWO SIGNAL VARIANTS, because it is not obvious which is right and they can
disagree once USDSEK has its own trend:
  USD-signal -- trend measured on BTC-USD (the underlying's own trend)
  SEK-signal -- trend measured on BTC-SEK (the price the operator actually
                sees in his broker, i.e. the ETP's own line)

Everything is scored in SEK, because that is the operator's currency, and
benchmarked against buy-and-hold BTC-SEK (what he gets by simply holding
the ETP he already owns).

Window fixed at 150d -- the grid winner, and the operator asked for 150d
specifically. 200d is shown once as a control since it was the prior
anchor and the family's known failure case.

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
TC = 0.0015
MAIN_WINDOW = 150
CONTROL_WINDOW = 200


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
    """Long when signal_price > its SMA(window). shift(1) so the signal day's
    own move is never captured, then weekday-only: a Sat/Sun signal change
    cannot take effect until Monday."""
    sig = (signal_price > signal_price.rolling(window).mean()).astype(float).shift(1)
    tradeable = sig.where(sig.index.dayofweek < 5)
    return tradeable.ffill().fillna(0.0)


def equity(position: pd.Series, ret: pd.Series, tc: float = TC) -> pd.Series:
    flips = position.diff().abs().fillna(0.0)
    return (1 + (position * ret - flips * tc).fillna(0.0)).cumprod()


def load_usdsek() -> tuple[pd.Series, str]:
    """Parquet store first (repo's own data), else fetch the same ticker the
    repo's fx universe lists. The restored CI cache does not always contain
    the fx/ directory, and silently proceeding without FX is exactly the gap
    this script exists to close -- so fall back rather than skip."""
    path = DATA_DIR / "fx" / "USDSEK=X.parquet"
    if path.exists():
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")["close"].sort_index().dropna(), "parquet store"

    fx = yf.Ticker("USDSEK=X").history(period="max")["Close"]
    fx.index = pd.to_datetime(fx.index.date)
    fx = fx.sort_index().dropna()
    if fx.empty:
        raise RuntimeError("USDSEK=X unavailable from both parquet and yfinance")
    return fx, "yfinance USDSEK=X (parquet cache had no fx/)"


def main() -> None:
    btc_df = yf.Ticker("BTC-USD").history(period="max")
    btc_df.index = pd.to_datetime(btc_df.index.date)
    btc_usd = btc_df["Close"].sort_index().dropna()

    usdsek_raw, fx_source = load_usdsek()
    print(f"BTC-USD  : {btc_usd.index[0].date()} -> {btc_usd.index[-1].date()}  "
          f"({len(btc_usd)} bars)")
    print(f"USDSEK=X : {usdsek_raw.index[0].date()} -> {usdsek_raw.index[-1].date()}  "
          f"({len(usdsek_raw)} bars, weekday-only)  [source: {fx_source}]")

    # Overlap, then FX forward-filled onto BTC's 365-day index.
    start = max(btc_usd.index[0], usdsek_raw.index[0])
    end = min(btc_usd.index[-1], usdsek_raw.index[-1])
    btc_usd = btc_usd.loc[start:end]
    usdsek = usdsek_raw.reindex(btc_usd.index).ffill().bfill()
    btc_sek = btc_usd * usdsek

    fx_chg = usdsek.iloc[-1] / usdsek.iloc[0] - 1
    print(f"Overlap  : {start.date()} -> {end.date()}  ({len(btc_usd)} bars)")
    print(f"USDSEK moved {usdsek.iloc[0]:.3f} -> {usdsek.iloc[-1]:.3f} "
          f"({fx_chg:+.1%}) over the sample -- this is the leg that was missing.\n")

    ret_usd = btc_usd.pct_change()
    ret_sek = btc_sek.pct_change()

    w = MAIN_WINDOW
    s = btc_sek.rolling(w).mean().dropna().index[0]

    def scored(eq: pd.Series, frm=s) -> dict:
        e = eq.loc[frm:]
        return perf(e / e.iloc[0])

    # ── Headline: 150d, FX in vs FX out ────────────────────────────────────
    print("=" * 94)
    print(f"{w}d TREND -- WITH the FX leg (scored in SEK) vs the earlier USD-only run")
    print("=" * 94)

    bh_sek = (1 + ret_sek.fillna(0)).cumprod()
    bh_usd = (1 + ret_usd.fillna(0)).cumprod()

    pos_usd_sig = etp_position(btc_usd, w)
    pos_sek_sig = etp_position(btc_sek, w)

    rows = [
        ("B&H  BTC-USD  (no FX, old benchmark)", scored(bh_usd)),
        ("B&H  BTC-SEK  (what holding the ETP gives)", scored(bh_sek)),
        (f"{w}d USD-signal -> SEK returns", scored(equity(pos_usd_sig, ret_sek))),
        (f"{w}d SEK-signal -> SEK returns", scored(equity(pos_sek_sig, ret_sek))),
        (f"{w}d USD-signal -> USD returns (old run)", scored(equity(pos_usd_sig, ret_usd))),
    ]
    print(f"  {'Variant':<42} {'CAGR':>9} {'Sharpe':>8} {'MaxDD':>9} {'Calmar':>8}")
    print(f"  {'-'*80}")
    for label, p in rows:
        print(f"  {label:<42} {p['cagr']:>+9.1%} {p['sharpe']:>8.3f} "
              f"{p['maxdd']:>+9.1%} {p['calmar']:>8.3f}")

    bh_sek_p = scored(bh_sek)
    print(f"\n  Benchmark that matters = B&H BTC-SEK (Calmar {bh_sek_p['calmar']:.3f}).")
    for label, p in rows[2:4]:
        print(f"    {label:<40} vs B&H-SEK: {p['calmar'] - bh_sek_p['calmar']:+.3f}")
    print()

    # ── Post-2020 ──────────────────────────────────────────────────────────
    print("=" * 94)
    print("POST-2020 (decision-relevant regime), scored in SEK")
    print("=" * 94)
    s20 = pd.Timestamp("2020-01-01")
    r20 = ret_sek.loc[s20:]
    bh20 = (1 + r20.fillna(0)).cumprod()
    p_bh20 = perf(bh20)
    print(f"  {'Variant':<42} {'CAGR':>9} {'Calmar':>8} {'vs B&H':>9}  Verdict")
    print(f"  {'-'*80}")
    print(f"  {'B&H BTC-SEK':<42} {p_bh20['cagr']:>+9.1%} {p_bh20['calmar']:>8.3f} "
          f"{'--':>9}")
    for label, pos in [(f"{w}d USD-signal", pos_usd_sig), (f"{w}d SEK-signal", pos_sek_sig),
                       (f"{CONTROL_WINDOW}d SEK-signal (control)",
                        etp_position(btc_sek, CONTROL_WINDOW))]:
        eq = equity(pos.loc[s20:], r20)
        p = perf(eq / eq.iloc[0])
        d = p["calmar"] - p_bh20["calmar"]
        verdict = "trend" if d > 0.02 else ("B&H" if d < -0.02 else "wash")
        print(f"  {label:<42} {p['cagr']:>+9.1%} {p['calmar']:>8.3f} {d:>+9.3f}  {verdict}")
    print()

    # ── Signal agreement ───────────────────────────────────────────────────
    both = pd.concat([pos_usd_sig, pos_sek_sig], axis=1).dropna().loc[s:]
    agree = float((both.iloc[:, 0] == both.iloc[:, 1]).mean())
    print("=" * 94)
    print("DO THE TWO SIGNALS ACTUALLY DIFFER?")
    print("=" * 94)
    print(f"  USD-signal and SEK-signal agree on {agree:.1%} of days "
          f"({int((1-agree)*len(both))} days apart).")
    print("  If ~identical, the FX leg does not change WHEN you trade -- only what")
    print("  you earn while holding. If they diverge, signal choice is a real decision.\n")

    # ── Cost sensitivity in SEK ────────────────────────────────────────────
    print("=" * 94)
    print(f"COST SENSITIVITY -- {w}d SEK-signal, scored in SEK (full sample)")
    print("=" * 94)
    print(f"  {'TC/flip':>8}  {'CAGR':>9}  {'Calmar':>8}  {'vs B&H-SEK':>11}")
    print(f"  {'-'*44}")
    for tc in [0.0005, 0.0015, 0.0050, 0.0100, 0.0150]:
        p = scored(equity(pos_sek_sig, ret_sek, tc))
        print(f"  {tc*1e4:>6.0f}bp  {p['cagr']:>+9.1%}  {p['calmar']:>8.3f}  "
              f"{p['calmar'] - bh_sek_p['calmar']:>+11.3f}")
    print("\n  Virtune's annual management fee is still NOT modelled -- it drags the")
    print("  trend arm and buy-and-hold alike, so it is ~neutral to this comparison.")


if __name__ == "__main__":
    main()
