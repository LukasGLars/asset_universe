"""
check_stld_earnings_dates.py — ONE-OFF diagnostic, delete after use.

User found a TradingView article suggesting STLD reported (a 10-Q
summary) around 2026-07-28 -- the same day the opp sleeve's entry screen
ran and showed STLD as ENTER-eligible with "NextEarn: 2026-10-19". Checks
whether the earnings-clear gate (gate 4) missed something, or whether
2026-10-19 is correctly the NEXT scheduled report after a 2026-07-28
print (i.e. the gate is forward-looking by design, not backward-looking).

Read-only. No commits, no state changes.
"""
from __future__ import annotations
import sys, io, warnings
warnings.filterwarnings("ignore")
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import yfinance as yf

t = yf.Ticker("STLD")
df = t.get_earnings_dates(limit=12)
print("STLD earnings dates (yfinance get_earnings_dates, limit=12):")
print(df[["EPS Estimate", "Reported EPS", "Surprise(%)"]] if df is not None else "No data")
