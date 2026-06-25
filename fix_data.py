"""
Data integrity fixer.
Pass 1: clamp OHLC so high >= open/close and low <= open/close.
Pass 2: reference-price sanity check on latest close across all instruments.
Rewrites only files that needed changes.
"""

import sys
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "src"))
from asset_universe import config
from asset_universe.store import reader

DATA_DIR = config.raw_data_dir()
OHLCV_CATEGORIES = ["equities", "intl_etfs", "commodities", "fixed_income", "fx", "volatility"]

# Expected approximate last-close ranges for reference check.
# Wide bands — only catch gross errors (10x wrong, missing adjustment, etc.)
REFERENCE_RANGES = {
    # equities
    "AAPL":    (100,   800),
    "MSFT":    (150,  1000),
    "GOOGL":   ( 80,   400),
    "JPM":     ( 50,   400),
    "GS":      (100,   800),
    # intl etfs
    "EWJ":     (  5,    80),
    "EEM":     ( 10,    80),
    # commodities (front-month futures)
    "GC_F":    (500,  6000),   # gold $/oz
    "CL_F":    ( 10,   200),   # WTI crude $/bbl
    "SI_F":    (  5,   100),   # silver $/oz
    "ZC_F":    (200,  2000),   # corn ¢/bu
    "NG_F":    (  1,    30),   # nat gas $/mmBtu
    # fixed income
    "TLT":     ( 50,   200),
    "IEF":     ( 70,   150),
    "HYG":     ( 50,   120),
    # fx (quote per USD or USD per quote)
    "EURUSD_X": (0.80, 1.60),
    "USDJPY_X": (80,   165),
    "GBPUSD_X": (1.00, 1.80),
    # vol
    "VIX":     (  5,   100),
}


# ── Pass 1: OHLC clamp ────────────────────────────────────────────────────────

print("=" * 65)
print("PASS 1 — OHLC integrity clamp")
print("=" * 65)

total_fixed_rows = 0
total_fixed_files = 0

for category in OHLCV_CATEGORIES:
    tickers = reader.available_tickers(DATA_DIR, category)
    cat_fixed = 0

    for ticker in tickers:
        path = DATA_DIR / category / f"{ticker}.parquet"
        df = pd.read_parquet(path)

        if not all(c in df.columns for c in ["open", "high", "low", "close"]):
            continue

        # Identify violating rows before fix
        bad_high = (df["high"] < df[["open", "close"]].max(axis=1) - 0.0001).sum()
        bad_low  = (df["low"]  > df[["open", "close"]].min(axis=1) + 0.0001).sum()
        n_bad = bad_high + bad_low

        if n_bad == 0:
            continue

        # Apply clamp
        df["high"] = df[["open", "high", "close"]].max(axis=1)
        df["low"]  = df[["open", "low",  "close"]].min(axis=1)

        df.to_parquet(path, index=False)
        cat_fixed += n_bad
        total_fixed_rows += n_bad
        total_fixed_files += 1
        print(f"  fixed  {category:<14} {ticker:<16} {n_bad} rows clamped")

    if cat_fixed == 0:
        print(f"  clean  {category}")

print(f"\n  Total: {total_fixed_rows} rows fixed across {total_fixed_files} files")


# ── Pass 2: reference price check ─────────────────────────────────────────────

print(f"\n{'='*65}")
print("PASS 2 — Reference price check (last available close)")
print(f"{'='*65}")
print(f"  {'Instrument':<18} {'Last date':<14} {'Last close':>12}  {'Range':<22} {'Status'}")
print(f"  {'-'*18} {'-'*14} {'-'*12}  {'-'*22} {'-'*6}")

ref_issues = []

for ticker, (lo, hi) in REFERENCE_RANGES.items():
    # Find category
    found = False
    for category in OHLCV_CATEGORIES:
        path = DATA_DIR / category / f"{ticker}.parquet"
        if path.exists():
            df = pd.read_parquet(path)
            df["date"] = pd.to_datetime(df["date"])
            last = df.sort_values("date").iloc[-1]
            close = last["close"]
            last_date = last["date"].strftime("%Y-%m-%d")
            in_range = lo <= close <= hi
            status = "OK" if in_range else "FAIL"
            if not in_range:
                ref_issues.append((ticker, close, lo, hi))
            print(f"  {ticker:<18} {last_date:<14} {close:>12.4f}  [{lo:>6}, {hi:>6}]      {status}")
            found = True
            break
    if not found:
        print(f"  {ticker:<18} {'FILE NOT FOUND':<14}")

if ref_issues:
    print(f"\n  FAIL: {len(ref_issues)} instruments outside expected range:")
    for ticker, close, lo, hi in ref_issues:
        print(f"    {ticker}: {close:.4f} not in [{lo}, {hi}]")
else:
    print(f"\n  All reference prices within expected ranges.")


# ── Pass 3: volume check on equities ─────────────────────────────────────────

print(f"\n{'='*65}")
print("PASS 3 — Zero-volume days on equities (post-2005)")
print(f"{'='*65}")

zero_vol_issues = []
tickers = reader.available_tickers(DATA_DIR, "equities")

for ticker in tickers:
    path = DATA_DIR / "equities" / f"{ticker}.parquet"
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    recent = df[df["date"] >= "2005-01-01"]
    zero = recent[recent["volume"] == 0]
    if len(zero) > 5:   # tolerate a handful of holidays/halts
        zero_vol_issues.append((ticker, len(zero), zero["date"].dt.strftime("%Y-%m-%d").tolist()[:3]))

if zero_vol_issues:
    print(f"  {len(zero_vol_issues)} tickers with >5 zero-volume days (post-2005):")
    for ticker, n, dates in zero_vol_issues:
        print(f"    {ticker:<10} {n} days — e.g. {dates}")
else:
    print("  No significant zero-volume issues.")

print(f"\n{'='*65}")
print("FIX COMPLETE")
print(f"{'='*65}")
