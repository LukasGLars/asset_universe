"""
run_midterm_election_analysis.py -- ONE-OFF diagnostic, delete after use.

Does the well-known US midterm-election-year market pattern (weak run-up,
strong post-election rally) show up in AVGO/LLY/Gold specifically, not
just the broad index? Real historical US midterm election dates only
(no forecasting, no assumption the broad-market pattern transfers to
these three names individually).

Convention: idx = first trading day ON OR AFTER the election date.
  pre_63d  = return over the 63 trading days INTO the election (~1 quarter)
  post_21d / post_63d / post_252d = return over N trading days AFTER

Read-only. No commits, no state changes.
"""
from __future__ import annotations
import sys, io, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd

from asset_universe import config
from asset_universe.store import reader

DATA_DIR = config.raw_data_dir()

# Real US midterm election dates (first Tuesday after first Monday in
# November, even years not divisible by 4). 2026-11-03 excluded --
# hasn't happened yet, no forward data.
MIDTERM_DATES = [
    "2002-11-05", "2006-11-07", "2010-11-02",
    "2014-11-04", "2018-11-06", "2022-11-08",
]

HOLDINGS = [
    ("AVGO", "equities"),
    ("LLY", "equities"),
    ("GC_F", "commodities"),
]

POST_HORIZONS = [21, 63, 252]


def main() -> None:
    for ticker, category in HOLDINGS:
        path = reader.ticker_path(DATA_DIR, category, ticker)
        if not path.exists():
            print(f"{ticker}: no data, skipping")
            continue
        prices = reader.load(path)["close"].dropna().sort_index()
        print(f"\n{'=' * 64}\n{ticker}  ({prices.index.min().date()} to {prices.index.max().date()})\n{'=' * 64}")

        rows = []
        for d in MIDTERM_DATES:
            dt = pd.Timestamp(d)
            if dt < prices.index.min() or dt > prices.index.max():
                continue
            idx = prices.index.searchsorted(dt)
            if idx >= len(prices) or idx < 63:
                continue
            base = prices.iloc[idx]
            row = {"election": d, "pre_63d": base / prices.iloc[idx - 63] - 1}
            for h in POST_HORIZONS:
                fwd_idx = idx + h
                row[f"post_{h}d"] = (prices.iloc[fwd_idx] / base - 1) if fwd_idx < len(prices) else None
            rows.append(row)

        if not rows:
            print("  no usable election dates in this ticker's history")
            continue
        df = pd.DataFrame(rows)
        for _, r in df.iterrows():
            post_str = "  ".join(
                f"post_{h}d={r[f'post_{h}d']:+.1%}" if pd.notna(r[f"post_{h}d"]) else f"post_{h}d=n/a"
                for h in POST_HORIZONS
            )
            print(f"  {r['election']}  pre_63d={r['pre_63d']:+.1%}  {post_str}")

        print(f"\n  Summary (n={len(df)}):")
        print(f"    pre_63d  : median {df['pre_63d'].median():+.1%}  win {(df['pre_63d'] > 0).mean():.0%}")
        for h in POST_HORIZONS:
            col = df[f"post_{h}d"].dropna()
            if len(col) == 0:
                continue
            print(f"    post_{h}d: median {col.median():+.1%}  win {(col > 0).mean():.0%}  n={len(col)}")

    print("\nInformational only -- not wired into any live gate.")


if __name__ == "__main__":
    main()
