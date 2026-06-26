"""
Full Universe Screen

Screens all Avanza-accessible assets by long-run risk-adjusted compounding.

Sources
-------
  US equities  : parquet store (504 tickers, data/raw/equities/)
  Commodities  : parquet store (GC_F=gold, SI_F=silver)
  Swedish caps : yfinance (.ST)
  UCITS ETFs   : yfinance (.DE / .L / .CO)

Filter
------
  >= 12yr history (spans GFC, COVID, 2022 rate-hike cycle)

Metrics
-------
  history_yr, CAGR, vol, Sharpe (RF=0), max_dd, Calmar

Regime layer
------------
  RY regime (LOW/MID/HIGH) from DFII10 parquet.
  Conditional CAGR per regime state for top 40 by Sharpe.

Output
------
  Console ranked table + regime breakdown + current-regime best-list
  Saves: universe_screen_results.csv
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf

from asset_universe import config

# ── Config ────────────────────────────────────────────────────────────────────
MIN_YEARS       = 12
HISTORY_START   = "2004-01-01"
TOP_N_REGIME    = 40
OUT_CSV         = Path(__file__).parent / "universe_screen_results.csv"
DATA_DIR        = config.raw_data_dir()

# ── Avanza-accessible Swedish large caps ─────────────────────────────────────
SWEDISH: dict[str, str] = {
    "INVE-B.ST":    "Investor B",
    "ATCO-A.ST":    "Atlas Copco A",
    "HEX-B.ST":     "Hexagon B",
    "SAND.ST":      "Sandvik",
    "VOLV-B.ST":    "Volvo B",
    "ESSITY-B.ST":  "Essity B",
    "ERIC-B.ST":    "Ericsson B",
    "AZN.ST":       "AstraZeneca",
    "SHB-A.ST":     "Handelsbanken A",
    "SEB-A.ST":     "SEB A",
    "ALFA.ST":      "Alfa Laval",
    "SKF-B.ST":     "SKF B",
    "SWED-A.ST":    "Swedbank A",
    "NIBE-B.ST":    "NIBE B",
    "HM-B.ST":      "H&M B",
}

# ── UCITS ETFs available on Avanza ────────────────────────────────────────────
UCITS: dict[str, str] = {
    "SXR8.DE":    "iSh Core S&P 500",
    "EUNL.DE":    "iSh MSCI World",
    "EXXT.DE":    "iSh NASDAQ-100",
    "EXSA.DE":    "iSh STOXX Europe 600",
    "IQQH.DE":    "iSh Global Healthcare",
    "EXV3.DE":    "iSh STOXX 600 HC",
    "EXI2.DE":    "iSh STOXX 600 Tech",
    "EXV6.DE":    "iSh STOXX 600 Energy",
    "EXH1.DE":    "iSh Core MSCI Europe",
    "SXRJ.DE":    "iSh Core MSCI Japan",
    "EMIM.L":     "iSh Core MSCI EM",
    "INRG.L":     "iSh Global Clean Energy",
    "XMWO.DE":    "Xtrackers MSCI World",
    "PPFB.DE":    "WisdomTree Phys Gold",
    "PHAG.L":     "WisdomTree Phys Silver",
    "4GLD.DE":    "Xetra-Gold",
    "NOVO-B.CO":  "Novo Nordisk B",
    "EXI3.DE":    "iSh STOXX 600 Financials",
    "EXV1.DE":    "iSh STOXX 600 Materials",
    "EXV4.DE":    "iSh STOXX 600 Industrials",
}


# ── Metric computation ────────────────────────────────────────────────────────
def _metrics(prices: pd.Series, name: str, ticker: str, category: str) -> dict | None:
    s = prices.dropna()
    if len(s) < MIN_YEARS * 200:
        return None
    lr   = np.log(s / s.shift(1)).dropna()
    nyrs = len(lr) / 252
    if nyrs < MIN_YEARS:
        return None
    cagr   = (s.iloc[-1] / s.iloc[0]) ** (1 / nyrs) - 1
    vol    = float(lr.std() * np.sqrt(252))
    sharpe = cagr / vol if vol > 0 else 0.0
    cum    = s / s.iloc[0]
    dd     = (cum - cum.cummax()) / cum.cummax()
    max_dd = float(dd.min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0
    return {
        "category":   category,
        "ticker":     ticker,
        "name":       name,
        "history_yr": round(nyrs, 1),
        "start":      str(s.index[0].date()),
        "cagr":       round(cagr, 4),
        "vol":        round(vol, 4),
        "sharpe":     round(sharpe, 3),
        "max_dd":     round(max_dd, 4),
        "calmar":     round(calmar, 3),
    }


def _fetch_yf(ticker: str, name: str, category: str) -> tuple[dict | None, pd.Series | None]:
    try:
        raw = yf.Ticker(ticker).history(start=HISTORY_START, auto_adjust=True)
        if raw.empty or "Close" not in raw.columns:
            return None, None
        s = raw["Close"].dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        m = _metrics(s, name, ticker, category)
        return m, s if m else (None, None)
    except Exception:
        return None, None


# ── RY regime labels ──────────────────────────────────────────────────────────
def _ry_regimes() -> pd.Series:
    path = DATA_DIR / "macro" / "DFII10.parquet"
    df   = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    ry   = df.set_index("date")["value"].sort_index().dropna()
    ry_m = ry.resample("ME").last().dropna()
    p33  = float(ry_m.quantile(0.333))
    p67  = float(ry_m.quantile(0.667))
    labels = ry_m.map(lambda v: "HIGH" if v >= p67 else ("LOW" if v <= p33 else "MID"))
    return labels.rename("ry_regime")


def _regime_cagr(prices: pd.Series, regimes: pd.Series) -> dict[str, float]:
    m  = prices.resample("ME").last().dropna()
    df = pd.DataFrame({"price": m, "regime": regimes}).dropna()
    if df.empty:
        return {}
    df["lr"] = np.log(df["price"] / df["price"].shift(1))
    df = df.dropna()
    out: dict[str, float] = {}
    for state in ("LOW", "MID", "HIGH"):
        sub = df.loc[df["regime"] == state, "lr"]
        if len(sub) >= 6:
            out[state] = round(float(np.exp(sub.mean() * 12) - 1), 4)
    return out


# ── Main ──────────────────────────────────────────────────────────────────────
print("Loading RY regimes ...", flush=True)
ry_regimes = _ry_regimes()

rows:     list[dict]       = []
price_map: dict[str, pd.Series] = {}  # ticker -> price series for regime calc

# 1. US equities from parquet
print("Screening 504 US equities from parquet ...", flush=True)
eq_dir = DATA_DIR / "equities"
us_pass = 0
for f in sorted(eq_dir.glob("*.parquet")):
    try:
        df = pd.read_parquet(f)
        df["date"] = pd.to_datetime(df["date"])
        s  = df.set_index("date")["close"].sort_index().dropna()
        s  = s[s.index >= HISTORY_START]
        m  = _metrics(s, f.stem, f.stem, "US Equity")
        if m:
            price_map[f.stem] = s
            rows.append(m)
            us_pass += 1
    except Exception:
        pass
print(f"  {us_pass} US equities passed {MIN_YEARS}yr filter", flush=True)

# 2. Commodities from parquet (gold / silver as benchmarks)
COMMODITIES = {"GC_F": "Gold (futures)", "SI_F": "Silver (futures)"}
for sym, name in COMMODITIES.items():
    path = DATA_DIR / "commodities" / f"{sym}.parquet"
    if not path.exists():
        continue
    try:
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        s  = df.set_index("date")["close"].sort_index().dropna()
        s  = s[s.index >= HISTORY_START]
        m  = _metrics(s, name, sym, "Commodity")
        if m:
            price_map[sym] = s
            rows.append(m)
    except Exception:
        pass

# 3. Swedish stocks via yfinance
print("Fetching Swedish stocks via yfinance ...", flush=True)
sw_pass = 0
sw_fail: list[str] = []
for ticker, name in SWEDISH.items():
    m, s = _fetch_yf(ticker, name, "Swedish")
    if m and s is not None:
        price_map[ticker] = s
        rows.append(m)
        sw_pass += 1
        print(f"  OK  {ticker:<15}  {name:<22}  {m['history_yr']:.0f}yr  "
              f"CAGR {m['cagr']:>+.1%}  Sharpe {m['sharpe']:.2f}", flush=True)
    else:
        sw_fail.append(ticker)
        print(f"  --  {ticker:<15}  SKIP (no data / <{MIN_YEARS}yr)", flush=True)

# 4. UCITS ETFs via yfinance
print("Fetching UCITS ETFs via yfinance ...", flush=True)
etf_pass = 0
etf_fail: list[str] = []
for ticker, name in UCITS.items():
    m, s = _fetch_yf(ticker, name, "UCITS ETF")
    if m and s is not None:
        price_map[ticker] = s
        rows.append(m)
        etf_pass += 1
        print(f"  OK  {ticker:<12}  {name:<28}  {m['history_yr']:.0f}yr  "
              f"CAGR {m['cagr']:>+.1%}  Sharpe {m['sharpe']:.2f}", flush=True)
    else:
        etf_fail.append(ticker)
        print(f"  --  {ticker:<12}  SKIP (no data / <{MIN_YEARS}yr)", flush=True)

# ── Compute regime-conditional CAGR for all assets ───────────────────────────
print("\nComputing regime-conditional returns ...", flush=True)
for row in rows:
    tkr = row["ticker"]
    s   = price_map.get(tkr)
    if s is not None:
        row["rc"] = _regime_cagr(s, ry_regimes)
    else:
        row["rc"] = {}

# ── Build results DataFrame ───────────────────────────────────────────────────
base_cols = [k for k in rows[0] if k != "rc"]
df = pd.DataFrame([{k: v for k, v in r.items() if k != "rc"} for r in rows])
rc_map = {r["ticker"]: r.get("rc", {}) for r in rows}

df["ry_low"]  = df["ticker"].map(lambda t: rc_map.get(t, {}).get("LOW",  float("nan")))
df["ry_mid"]  = df["ticker"].map(lambda t: rc_map.get(t, {}).get("MID",  float("nan")))
df["ry_high"] = df["ticker"].map(lambda t: rc_map.get(t, {}).get("HIGH", float("nan")))

df = df.sort_values("sharpe", ascending=False).reset_index(drop=True)
df.index += 1

df.to_csv(OUT_CSV, index_label="rank")
print(f"Saved: {OUT_CSV}\n", flush=True)

# ── Print ranked table — top 50 ───────────────────────────────────────────────
W = 100
print("=" * W)
print("UNIVERSE SCREEN  —  ranked by Sharpe  (>=12yr history, no crypto, no leverage)")
print("=" * W)
print(f"  {'#':>3}  {'Cat':<10}  {'Ticker':<14}  {'Name':<24}  "
      f"{'Hist':>5}  {'CAGR':>7}  {'Vol':>6}  {'Sharpe':>7}  {'MaxDD':>7}  {'Calmar':>7}")
print("  " + "-" * (W - 2))

for rank, row in df.head(50).iterrows():
    cat  = row["category"][:10]
    name = str(row["name"])[:24]
    print(f"  {rank:>3}  {cat:<10}  {row['ticker']:<14}  {name:<24}  "
          f"{row['history_yr']:>5.1f}  {row['cagr']:>+6.1%}  "
          f"{row['vol']:>5.1%}  {row['sharpe']:>7.3f}  "
          f"{row['max_dd']:>+6.1%}  {row['calmar']:>7.3f}")

total = len(df)
print()
print(f"  Showing top 50 of {total} assets that passed the {MIN_YEARS}yr filter.")
print(f"  Full rankings saved to: {OUT_CSV}")

# ── Regime breakdown — top 40 ─────────────────────────────────────────────────
top40 = df.head(TOP_N_REGIME).dropna(subset=["ry_low", "ry_mid", "ry_high"], how="all")

if not top40.empty:
    print()
    print("=" * W)
    print(f"REGIME-CONDITIONAL CAGR  (RY = DFII10 percentile bands)  —  top {TOP_N_REGIME}")
    print("=" * W)
    print(f"  {'#':>3}  {'Cat':<10}  {'Ticker':<14}  {'Name':<24}  "
          f"{'CAGR':>7}  {'Sharpe':>7}  |  "
          f"{'RY=LOW':>8}  {'RY=MID':>8}  {'RY=HIGH':>8}  {'Spread':>8}")
    print("  " + "-" * (W - 2))
    for rank, row in top40.iterrows():
        lo  = row["ry_low"]
        mid = row["ry_mid"]
        hi  = row["ry_high"]
        spread = (lo - hi) if not (pd.isna(lo) or pd.isna(hi)) else float("nan")
        fmt = lambda v: f"{v:>+7.1%}" if not pd.isna(v) else f"{'n/a':>8}"
        print(f"  {rank:>3}  {row['category'][:10]:<10}  {row['ticker']:<14}  "
              f"{str(row['name'])[:24]:<24}  "
              f"{row['cagr']:>+6.1%}  {row['sharpe']:>7.3f}  |  "
              f"{fmt(lo)}  {fmt(mid)}  {fmt(hi)}  {fmt(spread)}")

# ── Current regime intelligence ───────────────────────────────────────────────
current_ry  = str(ry_regimes.iloc[-1])
current_ry_val = None
try:
    dfii_path = DATA_DIR / "macro" / "DFII10.parquet"
    _d = pd.read_parquet(dfii_path)
    _d["date"] = pd.to_datetime(_d["date"])
    current_ry_val = float(_d.set_index("date")["value"].sort_index().dropna().iloc[-1])
except Exception:
    pass

print()
print("=" * W)
print(f"CURRENT REGIME  :  RY = {current_ry}"
      + (f"  (DFII10 = {current_ry_val:.2f}%)" if current_ry_val is not None else "")
      + f"   as of {ry_regimes.index[-1].date()}")
print("=" * W)
print()
print("  RY=LOW  : real yield below p33  — gold/growth tailwind, expansion regime")
print("  RY=MID  : real yield p33-p67    — neutral, quality/momentum works")
print("  RY=HIGH : real yield above p67  — restrictive, current regime")
print()

full_rc = df.dropna(subset=["ry_high"]).copy()
full_rc["spread"] = full_rc["ry_low"] - full_rc["ry_high"]

if current_ry == "HIGH":
    print("  -- Best performers IN current RY=HIGH regime (top 10 by RY=HIGH CAGR) --")
    best_hi = full_rc.nlargest(10, "ry_high")
    for _, r in best_hi.iterrows():
        print(f"    {r['ticker']:<14}  {str(r['name'])[:24]:<24}  "
              f"RY=HIGH {r['ry_high']:>+6.1%}  Sharpe {r['sharpe']:.2f}")

    print()
    print("  -- Compression candidates (RY=LOW >> RY=HIGH, top 10 by spread) --")
    best_sp = full_rc.dropna(subset=["ry_low"]).nlargest(10, "spread")
    for _, r in best_sp.iterrows():
        print(f"    {r['ticker']:<14}  {str(r['name'])[:24]:<24}  "
              f"LOW {r['ry_low']:>+6.1%}  HIGH {r['ry_high']:>+6.1%}  "
              f"spread {r['spread']:>+6.1%}")
elif current_ry == "LOW":
    print("  -- Best performers IN current RY=LOW regime (top 10 by RY=LOW CAGR) --")
    best_lo = full_rc.dropna(subset=["ry_low"]).nlargest(10, "ry_low")
    for _, r in best_lo.iterrows():
        print(f"    {r['ticker']:<14}  {str(r['name'])[:24]:<24}  "
              f"RY=LOW {r['ry_low']:>+6.1%}  Sharpe {r['sharpe']:.2f}")
else:
    print("  -- Best performers IN current RY=MID regime (top 10 by RY=MID CAGR) --")
    best_mid = df.dropna(subset=["ry_mid"]).nlargest(10, "ry_mid")
    for _, r in best_mid.iterrows():
        print(f"    {r['ticker']:<14}  {str(r['name'])[:24]:<24}  "
              f"RY=MID {r['ry_mid']:>+6.1%}  Sharpe {r['sharpe']:.2f}")

print()
print(f"  Skipped (no data or <{MIN_YEARS}yr): {sw_fail + etf_fail}")
