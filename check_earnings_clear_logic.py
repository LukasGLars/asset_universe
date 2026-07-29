"""
check_earnings_clear_logic.py — ONE-OFF diagnostic, delete after use.

get_earnings_dates() works fine standalone post-lxml-fix (confirmed real
historical dates for STLD/AVGO/NVDA). But the full execution-drift
backtest still produced byte-identical results before/after the fix --
same 34,151 raw events, same 4,322 declustered entries. This tests the
EXACT earnings_clear() function the backtest calls (not just the raw
fetch) against a date that SHOULD fail gate 4 (a date shortly before a
known real earnings report), to find where the disconnect is.

Read-only. No commits, no state changes.
"""
from __future__ import annotations
import sys, io, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import run_sleeve_entry_reconstruction as recon

print(f"HOLD_DAYS = {recon.HOLD_DAYS}")

# STLD reported 2026-07-20 (confirmed via get_earnings_dates). A date 5
# days before that (2026-07-15) should FAIL earnings_clear (inside the
# hold window). A date 40 days before (2026-06-10) should PASS.
for label, d in [
    ("5 days before a known STLD report (2026-07-15) -- should FAIL", pd.Timestamp("2026-07-15")),
    ("40 days before (2026-06-10) -- should PASS", pd.Timestamp("2026-06-10")),
    ("today (2026-07-28, right after the report) -- should PASS", pd.Timestamp("2026-07-28")),
]:
    result = recon.earnings_clear("STLD", d, hold_days=recon.HOLD_DAYS)
    print(f"{label}: earnings_clear = {result}")

print("\nDirect _earnings_dates('STLD') call (the cached fetch the backtest uses):")
dates = recon._earnings_dates("STLD")
print(f"  n={len(dates)}, first 5: {dates[:5] if len(dates) else 'EMPTY'}")
