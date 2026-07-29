"""
check_earnings_post_fix.py — ONE-OFF diagnostic, delete after use.

The execution-drift backtest produced byte-identical results before and
after adding lxml to pyproject.toml (same 34,151 raw events, same 4,322
declustered entries, same bucket stats). That's too exact to be a real
coincidence if the earnings gate actually started filtering anything --
suggests get_earnings_dates() is STILL failing, just for a different
reason now, silently caught by _earnings_dates()'s broad except clause.
This calls it directly, without swallowing the exception, to see what's
actually happening post-lxml-fix.

Read-only. No commits, no state changes.
"""
from __future__ import annotations
import sys, io, warnings
warnings.filterwarnings("ignore")
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import lxml
print(f"lxml version: {lxml.__version__}")

import yfinance as yf
for ticker in ["STLD", "AVGO", "NVDA"]:
    print(f"\n{'=' * 60}\n{ticker}: get_earnings_dates(limit=12)\n{'=' * 60}")
    try:
        df = yf.Ticker(ticker).get_earnings_dates(limit=12)
        print(f"Success. Shape: {df.shape if df is not None else None}")
        if df is not None:
            print(df.index.tolist()[:12])
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
