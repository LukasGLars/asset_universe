"""
Universe Screen — Regime-Conditional

Ranks all available assets by their empirical forward return distributions
conditioned on the current macro regime (Core 3 + USD: ry, nominal_10y,
baa10y, usd). No history cutoffs. No unconditional Sharpe ranking.

Transparency per row:
  N         — matched dates with valid 252d forward return
  diversity — THIN / MODERATE / ROBUST (temporal spread of matched dates)
  history   — full available history, not truncated

Sources
-------
  US equities  : parquet store  (data/raw/equities/)
  Commodities  : parquet store  (data/raw/commodities/)
  Swedish caps : yfinance (.ST) — period=max
  UCITS ETFs   : yfinance (.DE / .L / .CO) — period=max

Output
------
  Console ranked table + universe_screen_results.csv
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
from asset_universe.analysis import regimes as regime_module
from asset_universe.analysis.engine import current_regime

DATA_DIR = config.raw_data_dir()
OUT_CSV  = Path(__file__).parent / "universe_screen_results.csv"

# Core conditioning dimensions (empirically validated — signal audit)
CORE_FEATURES = ["ry_regime", "baa10y_regime"]

MIN_N = 10  # minimum matched dates to include an asset

SWEDISH: dict[str, str] = {
    "INVE-B.ST":  "Investor B",
    "ATCO-A.ST":  "Atlas Copco A",
    "HEX-B.ST":   "Hexagon B",
    "SAND.ST":    "Sandvik",
    "VOLV-B.ST":  "Volvo B",
    "ESSITY-B.ST":"Essity B",
    "ERIC-B.ST":  "Ericsson B",
    "AZN.ST":     "AstraZeneca",
    "SHB-A.ST":   "Handelsbanken A",
    "SEB-A.ST":   "SEB A",
    "ALFA.ST":    "Alfa Laval",
    "SKF-B.ST":   "SKF B",
    "SWED-A.ST":  "Swedbank A",
    "NIBE-B.ST":  "NIBE B",
    "HM-B.ST":    "H&M B",
}

UCITS: dict[str, str] = {
    "SXR8.DE":   "iSh Core S&P 500",
    "EUNL.DE":   "iSh MSCI World",
    "EXXT.DE":   "iSh NASDAQ-100",
    "EXSA.DE":   "iSh STOXX Europe 600",
    "IQQH.DE":   "iSh Global Healthcare",
    "EXV3.DE":   "iSh STOXX 600 HC",
    "EXI2.DE":   "iSh STOXX 600 Tech",
    "EXV6.DE":   "iSh STOXX 600 Energy",
    "EXH1.DE":   "iSh Core MSCI Europe",
    "SXRJ.DE":   "iSh Core MSCI Japan",
    "EMIM.L":    "iSh Core MSCI EM",
    "INRG.L":    "iSh Global Clean Energy",
    "PPFB.DE":   "WisdomTree Phys Gold",
    "PHAG.L":    "WisdomTree Phys Silver",
    "4GLD.DE":   "Xetra-Gold",
    "NOVO-B.CO": "Novo Nordisk B",
    "EXI3.DE":   "iSh STOXX 600 Financials",
    "EXV1.DE":   "iSh STOXX 600 Materials",
    "EXV4.DE":   "iSh STOXX 600 Industrials",
    "XMWO.DE":   "Xtrackers MSCI World",
}


def _forward_return(prices: pd.Series, date: pd.Timestamp, fwd_days: int) -> float | None:
    idx = prices.index.searchsorted(date)
    if idx >= len(prices):
        return None
    if abs((prices.index[idx] - date).days) > 5:
        return None
    fwd_idx = idx + fwd_days
    if fwd_idx >= len(prices):
        return None
    p0, p1 = prices.iloc[idx], prices.iloc[fwd_idx]
    return (p1 - p0) / p0 if p0 > 0 else None


def _diversity(dates: pd.DatetimeIndex) -> str:
    if len(dates) < 2:
        return "THIN"
    span_yr = (dates[-1] - dates[0]).days / 365.25
    pct_3y  = float((dates >= dates[-1] - pd.DateOffset(years=3)).mean())
    if span_yr >= 10 and pct_3y < 0.50:
        return "ROBUST"
    if span_yr < 5 or pct_3y > 0.80:
        return "THIN"
    return "MODERATE"


def _process(
    prices: pd.Series,
    ticker: str,
    name: str,
    category: str,
    matched_dates: pd.DatetimeIndex,
) -> dict | None:
    prices = prices.dropna().sort_index()
    if len(prices) < 50:
        return None

    nyrs = len(prices) / 252
    cagr = float((prices.iloc[-1] / prices.iloc[0]) ** (1 / nyrs) - 1) if nyrs > 0.5 else float("nan")

    fwd_horizons = [21, 63, 252]
    rets: dict[int, list[float]] = {h: [] for h in fwd_horizons}
    valid_dates_252: list[pd.Timestamp] = []

    for dt in matched_dates:
        r252 = _forward_return(prices, dt, 252)
        if r252 is not None:
            rets[252].append(r252)
            valid_dates_252.append(dt)
        for h in [21, 63]:
            r = _forward_return(prices, dt, h)
            if r is not None:
                rets[h].append(r)

    if len(rets[252]) < MIN_N:
        return None

    div = _diversity(pd.DatetimeIndex(valid_dates_252))

    row: dict = {
        "ticker":    ticker,
        "name":      name,
        "category":  category,
        "history_yr": round(nyrs, 1),
        "start":     str(prices.index[0].date()),
        "cagr":      round(cagr, 4),
        "n_matched": len(rets[252]),
        "diversity": div,
    }
    for h in fwd_horizons:
        rs = rets[h]
        if len(rs) >= MIN_N:
            s = pd.Series(rs)
            row[f"med_{h}d"] = round(float(s.median()), 4)
            row[f"win_{h}d"] = round(float((s > 0).mean()), 4)
        else:
            row[f"med_{h}d"] = float("nan")
            row[f"win_{h}d"] = float("nan")
    return row


def _fetch_yf(ticker: str) -> pd.Series | None:
    try:
        raw = yf.Ticker(ticker).history(period="max", auto_adjust=True)
        if raw.empty or "Close" not in raw.columns:
            return None
        s = raw["Close"].dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        return s.sort_index()
    except Exception:
        return None


# ── Build regime labels and derive current conditions ─────────────────────────
print("Building regime labels ...", flush=True)
labeled_df, thresholds = regime_module.build(DATA_DIR)

regime = current_regime(DATA_DIR)
conditions: dict[str, str] = {
    feat: regime["regimes"][feat]
    for feat in CORE_FEATURES
    if feat in regime["regimes"]
}

print(f"  Date    : {regime['date']}", flush=True)
print(f"  Conditions: {conditions}", flush=True)

mask = pd.Series(True, index=labeled_df.index)
for feat, val in conditions.items():
    mask &= labeled_df[feat] == val
matched_dates = labeled_df.index[mask]

print(f"  Matched dates: {len(matched_dates)}  "
      f"({matched_dates[0].date()} — {matched_dates[-1].date()})", flush=True)

rows: list[dict] = []

# ── US equities ───────────────────────────────────────────────────────────────
print("\nScreening US equities ...", flush=True)
eq_dir = DATA_DIR / "equities"
us_pass = 0
for f in sorted(eq_dir.glob("*.parquet")):
    try:
        df = pd.read_parquet(f)
        df["date"] = pd.to_datetime(df["date"])
        s = df.set_index("date")["close"].sort_index().dropna()
        row = _process(s, f.stem, f.stem, "US Equity", matched_dates)
        if row:
            rows.append(row)
            us_pass += 1
    except Exception:
        pass
print(f"  {us_pass} passed (N >= {MIN_N})", flush=True)

# ── Commodities ───────────────────────────────────────────────────────────────
for sym, name in {"GC_F": "Gold (futures)", "SI_F": "Silver (futures)"}.items():
    path = DATA_DIR / "commodities" / f"{sym}.parquet"
    if not path.exists():
        continue
    try:
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        s = df.set_index("date")["close"].sort_index().dropna()
        row = _process(s, sym, name, "Commodity", matched_dates)
        if row:
            rows.append(row)
    except Exception:
        pass

# -- Swedish stocks -----------------------------------------------------------
# Reads the se_equities parquet store (added 2026-08-18) rather than the old
# hardcoded 15-name live-yfinance list. That list omitted SAAB entirely and
# carried a dead Hexagon ticker (HEX-B.ST, correct is HEXA-B.ST), so names
# were being silently dropped from the ranking on every run.
print("")
print("Screening Swedish stocks ...", flush=True)
se_dir = DATA_DIR / "se_equities"
se_pass = 0
for f in sorted(se_dir.glob("*.parquet")):
    try:
        df = pd.read_parquet(f)
        df["date"] = pd.to_datetime(df["date"])
        s_px = df.set_index("date")["close"].sort_index().dropna()
        ticker = (f.stem[:-3].replace("_", "-") + ".ST") if f.stem.endswith("_ST") else f.stem
        row = _process(s_px, ticker, SWEDISH.get(ticker, ticker), "Swedish", matched_dates)
        if row:
            rows.append(row)
            se_pass += 1
    except Exception:
        pass
print(f"  {se_pass} passed (N >= {MIN_N})", flush=True)

# ── UCITS ETFs ────────────────────────────────────────────────────────────────
print("Fetching UCITS ETFs ...", flush=True)
for ticker, name in UCITS.items():
    s = _fetch_yf(ticker)
    if s is None:
        print(f"  -- {ticker:<12} no data", flush=True)
        continue
    row = _process(s, ticker, name, "UCITS ETF", matched_dates)
    if row:
        rows.append(row)
        print(f"  OK {ticker:<12} {name:<28} {row['history_yr']:.0f}yr  N={row['n_matched']}  {row['diversity']}", flush=True)
    else:
        print(f"  -- {ticker:<12} N < {MIN_N}", flush=True)

# ── Results ───────────────────────────────────────────────────────────────────
if not rows:
    print("No assets passed screening.", flush=True)
    sys.exit(1)

df_out = pd.DataFrame(rows)
df_out = df_out.sort_values("med_252d", ascending=False).reset_index(drop=True)
df_out.index += 1
df_out.to_csv(OUT_CSV, index_label="rank")
print(f"\nSaved: {OUT_CSV}", flush=True)

W = 122
print()
print("=" * W)
print(f"UNIVERSE SCREEN  —  ranked by median 252d conditional return")
print(f"Conditions: {conditions}  |  N >= {MIN_N}")
print("=" * W)
print(f"  {'#':>4}  {'Cat':<10}  {'Ticker':<14}  {'Name':<24}  "
      f"{'Hist':>5}  {'CAGR':>7}  {'N':>5}  {'Div':<8}  "
      f"{'21d':>7}  {'63d':>7}  {'252d':>7}  {'W252':>6}")
print("  " + "-" * (W - 2))

for rank, row in df_out.iterrows():
    print(f"  {rank:>4}  {str(row['category'])[:10]:<10}  {row['ticker']:<14}  "
          f"{str(row['name'])[:24]:<24}  "
          f"{row['history_yr']:>5.1f}  {row['cagr']:>+6.1%}  "
          f"{row['n_matched']:>5}  {str(row['diversity']):<8}  "
          f"{row['med_21d']:>+6.1%}  {row['med_63d']:>+6.1%}  "
          f"{row['med_252d']:>+6.1%}  {row['win_252d']:>5.0%}")

print()
print(f"  {len(df_out)} assets  |  {len(matched_dates)} matched dates in current regime  "
      f"({matched_dates[0].date()} — {matched_dates[-1].date()})")
print("  Diversity: ROBUST = 10yr+ span, <50% last-3yr  |  THIN = <5yr span or >80% last-3yr")
