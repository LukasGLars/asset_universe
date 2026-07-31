"""
run_lly_earnings_behavior_analysis.py — ONE-OFF diagnostic, delete after use.

LLY's own price behavior around its own real historical earnings dates:
run-up into the print, the immediate reaction, and post-earnings drift.
Reuses _earnings_surprises() from run_sleeve_pead_reconstruction.py (real
dates + Surprise(%), same tz-fix already validated) -- not a new data path.

Convention: idx = first trading day ON OR AFTER the earnings datetime
(handles both before-open and after-close reports the same way gap_pct
analyses elsewhere in this repo do).
  pre_5d      = return over the 5 trading days INTO the print (close
                before earnings vs. 5 days earlier)
  reaction    = close on/after earnings vs. close immediately before
  post_21d    = return over the 21 trading days AFTER the reaction close

Read-only. No commits, no state changes.
"""
from __future__ import annotations
import sys, io, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import pandas as pd

from asset_universe import config
from asset_universe.store import reader
import run_sleeve_pead_reconstruction as pead

TICKER = "LLY"
DATA_DIR = config.raw_data_dir()


def main() -> None:
    surprises = pead._earnings_surprises(TICKER)
    print(f"Real earnings events found for {TICKER}: {len(surprises)}")
    prices = reader.load(reader.ticker_path(DATA_DIR, "equities", TICKER))["close"].dropna().sort_index()
    print(f"Price history: {prices.index.min().date()} to {prices.index.max().date()} ({len(prices)} sessions)\n")

    rows = []
    for _, ev in surprises.iterrows():
        d, surprise = ev["date"], ev["surprise"]
        idx = prices.index.searchsorted(d)
        if idx < 6 or idx + 21 >= len(prices):
            continue
        pre_close, post_close = prices.iloc[idx - 1], prices.iloc[idx]
        pre_5d = pre_close / prices.iloc[idx - 6] - 1
        reaction = post_close / pre_close - 1
        post_21d = prices.iloc[idx + 21] / post_close - 1
        rows.append({"date": d.date(), "surprise_pct": surprise, "pre_5d": pre_5d,
                      "reaction": reaction, "post_21d": post_21d})

    df = pd.DataFrame(rows)
    print(f"Usable events (full pre/post window available): {len(df)}\n")

    def summarize(sub: pd.DataFrame, label: str) -> None:
        if len(sub) < 3:
            print(f"{label}: n={len(sub)} (too few to summarize)")
            return
        print(f"{label}  (n={len(sub)})")
        print(f"  Pre-earnings 5d run-up : median {sub['pre_5d'].median():+.1%}  win {(sub['pre_5d']>0).mean():.0%}")
        print(f"  Earnings-day reaction  : median {sub['reaction'].median():+.1%}  win {(sub['reaction']>0).mean():.0%}")
        print(f"  Post-earnings 21d drift: median {sub['post_21d'].median():+.1%}  win {(sub['post_21d']>0).mean():.0%}")

    print("=" * 64)
    summarize(df, "ALL real LLY earnings events")
    print()
    summarize(df[df["surprise_pct"] > 0], "BEATS (surprise > 0%)")
    print()
    summarize(df[df["surprise_pct"] <= 0], "MISSES/IN-LINE (surprise <= 0%)")
    print("=" * 64)

    out_csv = Path(__file__).parent / "comparison_results" / "lly_earnings_behavior.csv"
    out_csv.parent.mkdir(exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_csv}")
    print("\nInformational only -- not wired into any live gate.")


if __name__ == "__main__":
    main()
