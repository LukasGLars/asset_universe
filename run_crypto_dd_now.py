"""TEMPORARY (2026-10-07). BTC/ETH current price and whether today's drawdown
is normal against their own history. Delete after reading."""
from __future__ import annotations

import io
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", write_through=True)

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.store import reader

for tick in ("BTC-USD", "ETH-USD"):
    s = reader.load(reader.ticker_path(config.raw_data_dir(), "crypto", tick))["close"].dropna()
    peak = s.cummax()
    dd = s / peak - 1
    now = float(dd.iloc[-1])
    ath_date = s.idxmax()

    print("=" * 66)
    print(f"{tick}   last {s.index[-1].date()}")
    print("=" * 66)
    print(f"  price            : {s.iloc[-1]:,.2f}")
    print(f"  ATH              : {s.max():,.2f}  ({ath_date.date()})")
    print(f"  drawdown now     : {now:+.1%}")
    print(f"  days since ATH   : {(s.index[-1] - ath_date).days}")

    q = dd.quantile([0.05, 0.25, 0.50, 0.75, 0.95])
    print(f"\n  drawdown distribution over {len(s)} sessions "
          f"({s.index[0].date()} on):")
    print(f"    p5 {q[0.05]:+.1%}   p25 {q[0.25]:+.1%}   median {q[0.50]:+.1%}   "
          f"p75 {q[0.75]:+.1%}   p95 {q[0.95]:+.1%}")
    print(f"  share of sessions deeper than today: {float((dd < now).mean()):.0%}")
    print(f"  max drawdown     : {float(dd.min()):+.1%}  ({dd.idxmin().date()})")

    deep = (dd <= now).to_numpy()
    episodes, run = 0, False
    for v in deep:
        if v and not run:
            episodes += 1
            run = True
        elif not v:
            run = False
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    print(f"  separate episodes at least this deep: {episodes} over {yrs:.1f} yr")
    print(f"  share of all sessions at least this deep: {float(deep.mean()):.0%}")
print("=" * 66)
