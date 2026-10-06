"""
run_avgo_now_check.py

TEMPORARY (2026-10-06). Evaluates AVGO's CURRENT state against the two entry
conditions this project has already studied. No new conditions, no new
parameters -- both are taken from existing MEMORY.md entries:

  1. Crash-ROC: 5d ROC <= -10%  (validated, n=32, "Gap-down tranche validated")
  2. Overnight gap-down >= 2/3/5% below the prior close, read together with
     200d-SMA state  ("AVGO gap-down forward-return analysis" and the
     guard-conditioned follow-on, both 2026-07-28)

Prints the last 15 sessions so the answer is auditable rather than asserted.

Delete after reading.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", write_through=True)

import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.store import reader

CRASH_WINDOW, CRASH_THRESHOLD = 5, -0.10
GAP_THRESHOLDS = [0.02, 0.03, 0.05]
MA = 200

df = reader.load(reader.ticker_path(config.raw_data_dir(), "equities", "AVGO"))
df = df[["open", "high", "low", "close"]].dropna()
df["prior_close"] = df["close"].shift(1)
df["gap"] = df["open"] / df["prior_close"] - 1
df["sma200"] = df["close"].rolling(MA).mean()
df["vs200"] = df["close"] / df["sma200"] - 1
df["roc5"] = df["close"].pct_change(CRASH_WINDOW)

print("=" * 72)
print(f"AVGO state check -- data through {df.index[-1].date()}")
print("=" * 72)
last = df.iloc[-1]
print(f"  close            : {last['close']:.2f} USD")
print(f"  vs 200d SMA      : {last['vs200']:+.1%}  "
      f"({'BELOW -- guard-active state' if last['vs200'] < 0 else 'above'})")
print(f"  5d ROC           : {last['roc5']:+.1%}  "
      f"(crash trigger at {CRASH_THRESHOLD:.0%}: "
      f"{'FIRED' if last['roc5'] <= CRASH_THRESHOLD else 'NOT FIRED'})")
print(f"  today's gap      : {last['gap']:+.1%}")
for t in GAP_THRESHOLDS:
    print(f"  gap <= -{t:.0%}        : {'YES' if last['gap'] <= -t else 'no'}")

print("\n  last 15 sessions:")
print(f"  {'date':<12}{'open':>9}{'close':>9}{'gap':>8}{'vs200':>8}{'roc5':>8}")
for d, r in df.tail(15).iterrows():
    print(f"  {str(d.date()):<12}{r['open']:>9.2f}{r['close']:>9.2f}"
          f"{r['gap']:>+8.1%}{r['vs200']:>+8.1%}{r['roc5']:>+8.1%}")

n_gap = int((df["gap"].tail(15) <= -0.02).sum())
print(f"\n  gap-downs >= 2% in the last 15 sessions: {n_gap}")
print("=" * 72)
