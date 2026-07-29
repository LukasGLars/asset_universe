"""
check_earnings_limit60.py — ONE-OFF diagnostic, delete after use.

recon._earnings_dates('STLD') returns empty even though a direct
get_earnings_dates(limit=12) call succeeded. The only difference is
recon uses limit=60 and does extra processing (tz_localize + sorted +
np.array) inside a broad try/except that silently swallows whatever is
actually failing. This reproduces it WITHOUT the try/except to see the
real exception.

Read-only. No commits, no state changes.
"""
from __future__ import annotations
import sys, io, warnings
warnings.filterwarnings("ignore")
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import yfinance as yf

print("Step 1: get_earnings_dates(limit=60)")
df = yf.Ticker("STLD").get_earnings_dates(limit=60)
print(f"  Success. Shape: {df.shape if df is not None else None}")
print(f"  Index type: {type(df.index)}")
print(f"  Index dtype: {df.index.dtype}")

print("\nStep 2: the exact processing recon._earnings_dates() does")
dates = sorted(d.tz_localize(None) if d.tzinfo else d for d in df.index.to_pydatetime())
print(f"  Success. n={len(dates)}, first 3: {dates[:3]}")

import numpy as np
arr = np.array(dates, dtype="datetime64[ns]")
print(f"\nStep 3: np.array conversion -- n={len(arr)}, first 3: {arr[:3]}")
