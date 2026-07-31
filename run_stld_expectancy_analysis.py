"""
run_stld_expectancy_analysis.py -- ONE-OFF diagnostic, delete after use.

Real expectancy for STLD's current opp-sleeve candidacy: mean win size and
mean loss size (not just median-of-everything and win rate), computed from
the SAME regime-matched historical dates and forward-return machinery
run_entry_screen.py already uses for med_21d/win_21d -- just keeping the raw
per-date return list instead of collapsing it to median/win-rate, then
splitting on sign.

Prompted by: median (+2.7%) x win rate (60.5%) - stop distance (6.8%) x loss
rate is NOT a valid expectancy formula -- median isn't mean-of-winners, and
stop distance isn't mean-of-losers. This computes the real mean win / mean
loss from the actual historical distribution instead.

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
CALENDAR_DAYS = 21  # matches today's live suggested_duration_days(STLD) -- earnings far off, so flat TIME_EXIT_DAYS


def main() -> None:
    data_dir = config.raw_data_dir()
    conditions = {"ry_regime": "HIGH", "baa10y_regime": "TIGHT"}  # today's live regime
    matched = es._matched_dates(conditions, data_dir)
    print(f"Regime-matched dates: {len(matched)}  (conditions={conditions})")

    path = reader.ticker_path(data_dir, CATEGORY, TICKER)
    prices = reader.load(path)["close"].dropna().sort_index()
    trading_days = max(1, round(CALENDAR_DAYS * 252 / 365.25))
    print(f"Trading-day window: {trading_days}")

    rets = [r for dt in matched if (r := es._uncapped_forward_return(prices, dt, trading_days)) is not None]
    s = pd.Series(rets)
    print(f"n = {len(s)}")

    wins = s[s > 0]
    losses = s[s <= 0]
    win_rate = len(wins) / len(s)
    mean_win = wins.mean()
    mean_loss = losses.mean()  # negative
    median_all = s.median()

    print(f"\nWin rate            : {win_rate:.1%}  (n_win={len(wins)}, n_loss={len(losses)})")
    print(f"Median (all)         : {median_all:+.1%}   <- what status.md shows")
    print(f"Mean win (winners)   : {mean_win:+.1%}")
    print(f"Mean loss (losers)   : {mean_loss:+.1%}")

    real_ev = win_rate * mean_win + (1 - win_rate) * mean_loss
    print(f"\nReal expectancy (win_rate*mean_win + loss_rate*mean_loss): {real_ev:+.2%}")

    naive_ev = win_rate * median_all - (1 - win_rate) * 0.068
    print(f"Naive (invalid) EV from earlier claim (median x win_rate - stop_dist x loss_rate): {naive_ev:+.2%}")

    print("\nInformational only -- not wired into any live gate.")


if __name__ == "__main__":
    main()
