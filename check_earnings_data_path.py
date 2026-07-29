"""
check_earnings_data_path.py — ONE-OFF diagnostic, delete after use.

Discovered while investigating whether STLD's opp-sleeve entry should
have been blocked by an earnings-proximity gate: the BACKTEST earnings
lookup (run_sleeve_entry_reconstruction.py's _earnings_dates(), using
yfinance's get_earnings_dates()) crashed on a missing lxml dependency in
this environment, silently caught by that function's own try/except and
defaulting to "gate passes." The LIVE screen uses a different method
(_next_earnings() in engine.py, via t.calendar) that doesn't need lxml
and DOES work correctly.

This checks, explicitly and without swallowing the exception:
  1. Is lxml actually missing?
  2. Does get_earnings_dates() fail for STLD specifically?
  3. Does t.calendar (the live screen's working path) give STLD's real
     past + next earnings dates?
  4. What does t.earnings_dates (the property _next_earnings() tries
     FIRST, before falling back to t.calendar) give?

If get_earnings_dates() fails universally, the backtest's earnings gate
(gate 4) has likely been a silent no-op across run_sleeve_entry_
reconstruction.py, run_opp_sleeve_extension_decile_analysis.py, and
run_opp_sleeve_execution_drift_analysis.py -- a real methodological gap,
not just a STLD-specific question.

Read-only. No commits, no state changes.
"""
from __future__ import annotations
import sys, io, warnings
warnings.filterwarnings("ignore")
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

print("=" * 72)
print("1. Is lxml importable?")
print("=" * 72)
try:
    import lxml
    print(f"lxml IS installed: version {lxml.__version__}")
except ImportError as e:
    print(f"lxml is NOT installed: {e}")

import yfinance as yf
t = yf.Ticker("STLD")

print("\n" + "=" * 72)
print("2. get_earnings_dates(limit=12) -- backtest's method")
print("=" * 72)
try:
    df = t.get_earnings_dates(limit=12)
    print(df[["EPS Estimate", "Reported EPS", "Surprise(%)"]] if df is not None else "None returned")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")

print("\n" + "=" * 72)
print("3. t.calendar -- live screen's working fallback method")
print("=" * 72)
try:
    cal = t.calendar
    print(cal)
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")

print("\n" + "=" * 72)
print("4. t.earnings_dates -- live screen's FIRST-tried property")
print("=" * 72)
try:
    ed = t.earnings_dates
    print(ed[["EPS Estimate", "Reported EPS", "Surprise(%)"]] if ed is not None else "None returned")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
