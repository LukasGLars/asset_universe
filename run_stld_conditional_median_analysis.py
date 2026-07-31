"""
run_stld_conditional_median_analysis.py -- ONE-OFF diagnostic, delete after use.

Follow-up to the STLD real-expectancy check (MEMORY.md 2026-07-31): mean win
+8.2% / mean loss -6.7% gave real expectancy +2.27%. Question: is that mean
being propped up by a few outlier winners in the 1390-sample regime-matched
history? Compares against the median-of-winners / median-of-losers (medians
computed WITHIN each group, not the earlier invalid overall-median), plus
max win / max loss so an outlier-driven mean would be visible directly.

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
import run_entry_screen as es

TICKER = "STLD"
CATEGORY = "equities"
CALENDAR_DAYS = 21


def main() -> None:
    data_dir = config.raw_data_dir()
    conditions = {"ry_regime": "HIGH", "baa10y_regime": "TIGHT"}
    matched = es._matched_dates(conditions, data_dir)

    path = reader.ticker_path(data_dir, CATEGORY, TICKER)
    prices = reader.load(path)["close"].dropna().sort_index()
    trading_days = max(1, round(CALENDAR_DAYS * 252 / 365.25))

    rets = [r for dt in matched if (r := es._uncapped_forward_return(prices, dt, trading_days)) is not None]
    s = pd.Series(rets)
    print(f"n = {len(s)}")

    wins = s[s > 0]
    losses = s[s <= 0]
    win_rate = len(wins) / len(s)

    mean_win, mean_loss = wins.mean(), losses.mean()
    med_win, med_loss = wins.median(), losses.median()
    max_win, max_loss = wins.max(), losses.min()

    print(f"\nWin rate: {win_rate:.1%}  (n_win={len(wins)}, n_loss={len(losses)})")
    print(f"Mean win   : {mean_win:+.1%}   Median win   : {med_win:+.1%}   Max win : {max_win:+.1%}")
    print(f"Mean loss  : {mean_loss:+.1%}   Median loss  : {med_loss:+.1%}   Max loss: {max_loss:+.1%}")

    mean_ev = win_rate * mean_win + (1 - win_rate) * mean_loss
    median_ev = win_rate * med_win + (1 - win_rate) * med_loss
    print(f"\nMean-based expectancy   : {mean_ev:+.2%}")
    print(f"Median-based expectancy : {median_ev:+.2%}")
    print(f"Gap (mean - median)     : {mean_ev - median_ev:+.2%}")

    print("\nInformational only -- not wired into any live gate.")


if __name__ == "__main__":
    main()
