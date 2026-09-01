"""
run_btc_in_core.py

TEMPORARY DIAGNOSTIC (2026-08-31). User: "What would happen if I held x%
BTC in RC as well?"

Ranked on the WORST SUB-PERIOD from the start, per MEMORY.md's
[[project-reactor-core-mix]] standard. Earlier tonight I ranked the core
mix full-sample first and got the LLY conclusion exactly backwards; that
is not repeated here.

Everything is modelled on the ACTUAL instrument and the ACTUAL rule the
operator already adopted (MEMORY.md 2026-08-24):
  - Virtune Sustainable Bitcoin ETP SE0020845709, **1.49%/yr**, the only
    Virtune BTC ETP on Avanza -- a constraint, not a choice
  - SEK-denominated: BTC_SEK = BTC_USD x USDSEK
  - weekday-only execution (~252 exchange days/yr); BTC itself moves
    nights and weekends but the ETP cannot be traded then
  - 0.16% spread per flip (his measured number)
  - fee accrues ONLY while held, on actual calendar-day gaps
  - signal read off BTC-USD, not BTC-SEK (his vessel-vs-signal thesis:
    trend-following the SEK line contaminates a Bitcoin-momentum signal
    with SEK/USD moves that carry no information about Bitcoin)

Two BTC arms, because he holds a position AND has an adopted rule:
  HOLD  -- buy and hold the ETP
  150d  -- the adopted rule: in when BTC-USD > its 150d SMA, else out

EVERYTHING IS IN SEK. The committed 2004-2026 grid is in raw USD prices;
that is fine for ranking USD assets against each other but not for adding
a SEK-denominated crypto ETP, so all four assets are converted via USDSEK
here. Numbers are therefore NOT comparable to base_optimizer_grid.csv --
the no-BTC row in this run is the baseline to compare against.

Window is BTC's, not the Core's: ~2014-09 onward. Much shorter than the
Core's 2004 start, and that limitation is the main reason to distrust any
result here.

Read-only. Delete script, tests and workflow once logged to MEMORY.md.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.store import reader

# ── The operator's real instrument constraints ────────────────────────────
ETP_FEE_ANNUAL = 0.0149      # Virtune Sustainable, only one on Avanza
BTC_SPREAD     = 0.0016      # measured
SMA_WINDOW     = 150         # the ADOPTED rule
TC_BPS         = 10          # equity/gold leg, matches the rest of the repo
REBAL_TRIGGER  = 0.05

CORE_BASE  = {"Gold": 0.25, "AVGO": 0.40, "LLY": 0.35}   # live, and correct
BTC_WEIGHTS = [0.0, 0.02, 0.05, 0.075, 0.10, 0.15, 0.20]
CORE_FRACS  = [0.80, 0.85, 1.00]
DD_TOLERANCE = -0.25

ASSETS = {"Gold": ("commodities", "GC_F"),
          "AVGO": ("equities", "AVGO"),
          "LLY":  ("equities", "LLY")}

# Sub-periods inside BTC's own history. 2021-2022 is BTC's -77% bear and
# MUST be its own window -- averaging it away is exactly how a volatile
# asset gets waved into a portfolio.
SUBPERIODS = [
    ("2014-09..2017", None,         "2017-12-31"),
    ("2018..2020",    "2018-01-01", "2020-12-31"),
    ("2021..2022",    "2021-01-01", "2022-12-31"),
    ("2023..2026",    "2023-01-01", None),
]

TPV_NOW, MONTHLY, YEARS_LEFT = 1_150_000, 6_000, 12.11
TARGET_NOMINAL = 20_482_105


def load_close(data_dir: Path, cat: str, safe: str) -> pd.Series:
    df = pd.read_parquet(reader.ticker_path(data_dir, cat, safe))
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index()


def fetch_btc_usd() -> pd.Series:
    """BTC-USD is not in the parquet universe (offered 2026-08-24, never
    actioned), so fetch it live. 7-day series: the SMA is computed on all
    of it because Bitcoin moves at weekends, but it is only ACTED on when
    the ETP can actually be traded."""
    import yfinance as yf
    df = yf.download("BTC-USD", start="2014-01-01", progress=False, auto_adjust=True)
    s = df["Close"]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s.sort_index().dropna()


def metrics(nav: pd.Series) -> dict:
    nav = nav.dropna()
    if len(nav) < 60:
        return {k: np.nan for k in ("cagr", "vol", "sharpe", "mdd", "calmar")}
    nav = nav / nav.iloc[0]
    r = nav.pct_change().dropna()
    yrs = (nav.index[-1] - nav.index[0]).days / 365.25
    cagr = nav.iloc[-1] ** (1 / yrs) - 1
    vol = r.std() * np.sqrt(252)
    peak = nav.expanding().max()
    mdd = ((nav - peak) / peak).min()
    return {"cagr": cagr, "vol": vol,
            "sharpe": r.mean() * 252 / vol if vol > 0 else 0.0,
            "mdd": mdd, "calmar": cagr / abs(mdd) if mdd < 0 else 0.0}


def window(s: pd.Series, a, b) -> pd.Series:
    if a: s = s[s.index >= pd.Timestamp(a)]
    if b: s = s[s.index <= pd.Timestamp(b)]
    return s


def btc_leg(btc_sek: pd.Series, cal: pd.DatetimeIndex,
            in_market: np.ndarray | None) -> tuple[pd.Series, float, float]:
    """NAV of the ETP position on the trading calendar.

    in_market=None -> buy and hold. Otherwise in_market[i] is the position
    HELD over (i-1, i], already shifted by the caller.

    The 1.49% fee accrues on real calendar-day gaps and ONLY while held --
    an out-of-market trend arm genuinely does not pay it. MEMORY.md
    2026-08-24 records that every earlier BTC run got this backwards and it
    was worth +1.02% CAGR once fixed.
    """
    p = btc_sek.reindex(cal).ffill()
    days = np.diff(cal.values).astype("timedelta64[D]").astype(float)
    ret = p.pct_change().fillna(0.0).to_numpy()
    nav, out = 1.0, [1.0]
    held_days = total_days = 0.0
    prev = 1.0 if in_market is None else float(in_market[0])
    for i in range(1, len(cal)):
        pos = 1.0 if in_market is None else float(in_market[i])
        nav *= (1.0 + pos * ret[i])
        dt = days[i - 1]
        total_days += dt
        if pos > 0:
            nav *= (1.0 - ETP_FEE_ANNUAL) ** (dt / 365.0)
            held_days += dt * pos
        if pos != prev:
            nav *= (1.0 - BTC_SPREAD * abs(pos - prev))
            prev = pos
        out.append(nav)
    return (pd.Series(out, index=cal),
            held_days / total_days if total_days else 0.0,
            ETP_FEE_ANNUAL * (held_days / total_days if total_days else 0.0))


def simulate(navs: dict[str, pd.Series], target: dict[str, float]) -> pd.Series:
    """Drift-and-rebalance over precomputed per-asset NAV paths."""
    keys = [k for k in target if target[k] > 0]
    R = np.column_stack([navs[k].pct_change().fillna(0.0).to_numpy() for k in keys])
    tgt = np.array([target[k] for k in keys])
    w = tgt.copy()
    nav, out = 1.0, [1.0]
    for i in range(1, len(R)):
        nav *= (1.0 + float(w @ R[i]))
        w = w * (1.0 + R[i])
        s = w.sum()
        if s > 0:
            w = w / s
        if np.max(np.abs(w - tgt)) > REBAL_TRIGGER:
            nav *= (1.0 - np.abs(tgt - w).sum() / 2 * TC_BPS / 10_000)
            w = tgt.copy()
        out.append(nav)
    return pd.Series(out, index=navs[keys[0]].index)


def fv(pv, r, yrs, monthly):
    n = int(round(yrs * 12)); m = (1 + r) ** (1 / 12) - 1
    return pv * (1 + m) ** n + (monthly * (((1 + m) ** n - 1) / m) if m else monthly * n)


def main() -> None:
    d = config.raw_data_dir()
    usdsek = load_close(d, "fx", "USDSEK=X")
    core_usd = {n: load_close(d, c, t) for n, (c, t) in ASSETS.items()}
    btc_usd = fetch_btc_usd()

    print("=" * 78)
    print("BTC INSIDE THE REACTOR CORE  --  actual instrument, adopted rule")
    print("=" * 78)
    print(f"BTC-USD  {btc_usd.index[0].date()} -> {btc_usd.index[-1].date()} "
          f"({len(btc_usd):,} obs, 7d/wk)")
    print(f"ETP: Virtune Sustainable SE0020845709, fee {ETP_FEE_ANNUAL:.2%}/yr, "
          f"spread {BTC_SPREAD:.2%}, weekday-only")

    # Trading calendar = the equity calendar (weekday-only, matches the ETP)
    cal = core_usd["AVGO"].index
    cal = cal[cal >= max(btc_usd.index[0], usdsek.index[0])]
    fx = usdsek.reindex(cal.union(usdsek.index)).ffill().reindex(cal)

    # EVERYTHING in SEK
    navs_sek = {}
    for k, s in core_usd.items():
        v = (s.reindex(cal).ffill() * fx)
        navs_sek[k] = v / v.iloc[0]
    btc_sek = btc_usd.reindex(btc_usd.index.union(cal)).ffill().reindex(cal) * fx

    print(f"Window   {cal[0].date()} -> {cal[-1].date()} "
          f"({len(cal):,} trading days, {(cal[-1]-cal[0]).days/365.25:.1f}yr)")
    print("All assets converted to SEK -- NOT comparable to the 2004-2026")
    print("USD grid. The 0% BTC row below is the baseline to compare against.")

    # Adopted 150d rule: SMA on the full 7-day BTC-USD series (Bitcoin moves
    # at weekends), sampled on trading days, shift(1) to act next day.
    sma = btc_usd.rolling(SMA_WINDOW).mean()
    sig = (btc_usd > sma).reindex(btc_usd.index.union(cal)).ffill().reindex(cal)
    in_mkt = sig.shift(1).fillna(False).astype(float).to_numpy()

    hold_nav, hold_in, hold_fee = btc_leg(btc_sek, cal, None)
    trend_nav, trend_in, trend_fee = btc_leg(btc_sek, cal, in_mkt)

    print(f"\nBTC leg, standalone in SEK, net of fee and spread:")
    for name, nv, inm, fee in (("HOLD", hold_nav, hold_in, hold_fee),
                               ("150d", trend_nav, trend_in, trend_fee)):
        m = metrics(nv)
        print(f"  {name}  in-market {inm:5.0%}  fee paid {fee:.2%}/yr  "
              f"CAGR {m['cagr']:7.2%}  MaxDD {m['mdd']:7.2%}  "
              f"Calmar {m['calmar']:.3f}")

    # ── Grid ──────────────────────────────────────────────────────────────
    rows = []
    for arm, bnav in (("HOLD", hold_nav), ("150d", trend_nav)):
        for bw in BTC_WEIGHTS:
            tgt = {k: v * (1 - bw) for k, v in CORE_BASE.items()}
            tgt["BTC"] = bw
            core_nav = simulate({**navs_sek, "BTC": bnav}, tgt)
            for cf in CORE_FRACS:
                # Home Base modelled as flat cash; SHY in SEK would import a
                # second FX leg for a sleeve that is ~2% vol anyway.
                if cf >= 1.0:
                    tpv = core_nav
                else:
                    hb = pd.Series((1 + (1.02) ** (1 / 252) - 1) **
                                   np.arange(len(cal)), index=cal)
                    tpv = simulate({"C": core_nav / core_nav.iloc[0],
                                    "H": hb}, {"C": cf, "H": 1 - cf})
                m = metrics(tpv)
                worst_mdd, worst_cal = 0.0, 1e9
                for nm, a, b in SUBPERIODS:
                    w = window(tpv, a, b)
                    if len(w) < 120:
                        continue
                    sm = metrics(w)
                    worst_mdd = min(worst_mdd, sm["mdd"])
                    worst_cal = min(worst_cal, sm["calmar"])
                rows.append({"arm": arm, "btc_w": bw, "core_frac": cf,
                             "cagr": m["cagr"], "mdd": m["mdd"],
                             "calmar": m["calmar"], "sharpe": m["sharpe"],
                             "worst_mdd": worst_mdd, "worst_calmar": worst_cal,
                             "within_tol": bool(m["mdd"] >= DD_TOLERANCE),
                             "worst_within_tol": bool(worst_mdd >= DD_TOLERANCE)})
    df = pd.DataFrame(rows)
    out = PROJECT_ROOT / "comparison_results"
    out.mkdir(exist_ok=True)
    df.to_csv(out / "btc_in_core_grid.csv", index=False)

    for cf in CORE_FRACS:
        print("\n" + "=" * 78)
        print(f"REACTOR CORE = {cf:.0%} of TPV   (Home Base = flat 2% cash)")
        print("=" * 78)
        for arm in ("HOLD", "150d"):
            sub = df[(df.arm == arm) & (df.core_frac == cf)].sort_values("btc_w")
            print(f"\n  BTC arm: {arm}")
            print(f"  {'BTC%':>6}{'CAGR':>9}{'MaxDD':>9}{'Calmar':>8}"
                  f"{'worstDD':>10}{'worstCal':>10}  tolerance")
            base = sub[sub.btc_w == 0].iloc[0]
            for _, r in sub.iterrows():
                tag = "OK " if r.worst_within_tol else "BREACH"
                delta = "" if r.btc_w == 0 else \
                    f"  ({r.cagr - base.cagr:+.2%} CAGR, {r.mdd - base.mdd:+.2%} DD)"
                print(f"  {r.btc_w:>5.1%}{r.cagr:>9.2%}{r.mdd:>9.2%}"
                      f"{r.calmar:>8.3f}{r.worst_mdd:>10.2%}"
                      f"{r.worst_calmar:>10.3f}  {tag}{delta}")

    # ── The decision framing ──────────────────────────────────────────────
    print("\n" + "=" * 78)
    print("RANKED ON WORST SUB-PERIOD (the standard this repo sets)")
    print("=" * 78)
    for cf in (0.85, 0.80):
        print(f"\nCore {cf:.0%} -- best BTC weight by WORST-sub-period Calmar:")
        sub = df[df.core_frac == cf]
        for arm in ("HOLD", "150d"):
            a = sub[sub.arm == arm].sort_values("worst_calmar", ascending=False)
            b = a.iloc[0]
            z = sub[(sub.arm == arm) & (sub.btc_w == 0)].iloc[0]
            print(f"  {arm}: best at BTC {b.btc_w:.1%} "
                  f"(worst Calmar {b.worst_calmar:.3f} vs {z.worst_calmar:.3f} "
                  f"at 0%)  -> {'ADDS' if b.btc_w > 0 else 'NO BTC'}")

    print("\n" + "=" * 78)
    print("FI@50 IMPACT (Core 85%, illustrative -- a 11yr CAGR is not a forecast)")
    print("=" * 78)
    print(f"{'arm':>6}{'BTC%':>7}{'CAGR':>9}{'worstDD':>10}{'proj 2038':>15}"
          f"{'vs no BTC':>14}")
    b0 = df[(df.arm == "HOLD") & (df.btc_w == 0) & (df.core_frac == 0.85)].iloc[0]
    f0 = fv(TPV_NOW, b0.cagr, YEARS_LEFT, MONTHLY)
    for arm in ("HOLD", "150d"):
        for bw in BTC_WEIGHTS:
            r = df[(df.arm == arm) & (df.btc_w == bw) & (df.core_frac == 0.85)].iloc[0]
            f = fv(TPV_NOW, r.cagr, YEARS_LEFT, MONTHLY)
            print(f"{arm:>6}{bw:>7.1%}{r.cagr:>9.2%}{r.worst_mdd:>10.2%}"
                  f"{f:>15,.0f}{f - f0:>+14,.0f}")

    print(f"\nWrote {out / 'btc_in_core_grid.csv'} ({len(df)} rows)")
    print("\nHARD LIMIT: this window is ~11.5 years and contains ONE BTC bull")
    print("cycle and ONE -77% bear. Any BTC weight conclusion rests on that.")


if __name__ == "__main__":
    main()
