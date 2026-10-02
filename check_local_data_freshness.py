"""
check_local_data_freshness.py

Originally built 2026-07-07 to guard the local `data/` parquet store
(gitignored, never synced anywhere -- see .gitignore), which only refreshes
when someone explicitly runs `python -m asset_universe.update`. Nothing
checked its age before local analysis scripts trusted it, and it sat a full
week stale (last updated 2026-06-30) without any warning, which nearly
produced a wrong "HWM has breached its stop" claim during a session that
used it directly.

Also wired into `sync.yml` itself (2026-07-07, after the alert-robustness
review): the live pipeline's own `asset_universe.update` step was assumed
to always produce fresh data since it runs every scheduled fire -- but
that assumption was never actually verified, and the healthchecks.io
heartbeat only proves the job *ran*, not that it ran on good data (a
silent yfinance/FRED hiccup that returns stale data without erroring would
still ping heartbeat healthy). Same check, same auto-refresh-then-fail
logic, now gates the live pipeline too, right after "Update prices" and
before any signal is computed from it.

Usage: run this FIRST, before any local script that reads from data/raw/,
or as a `sync.yml` step right after `python -m asset_universe.update`.
Auto-refreshes if stale (more than MAX_STALE_TRADING_DAYS sessions behind,
weekends AND NYSE holidays excluded) rather than just warning, since the fix
is one command either way; fails loudly (non-zero exit) only if a refresh
attempt doesn't fix it.

Fixed 2026-10-02: the expected-last-session calculation skipped weekends but
not market holidays, so on the morning after every NYSE closure it demanded a
close that never existed and exited non-zero. Because it self-healed the next
day it was written off as noise and left in place, costing roughly nine false
sync failures a year and training the operator to ignore the alert.
"""
from __future__ import annotations

import datetime as dt
import functools
import subprocess
import sys
from pathlib import Path

import pandas as pd
from pandas.tseries.holiday import (
    AbstractHolidayCalendar,
    GoodFriday,
    Holiday,
    USLaborDay,
    USMartinLutherKingJr,
    USMemorialDay,
    USPresidentsDay,
    USThanksgivingDay,
    nearest_workday,
)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from asset_universe import config
from asset_universe.store import reader

REFERENCE_TICKER = ("equities", "SPY")
MAX_STALE_TRADING_DAYS = 1


class _NYSECalendar(AbstractHolidayCalendar):
    """NYSE full-day closures, built from pandas' own holiday rules so this
    needs no extra dependency. `nearest_workday` is the exchange's observance
    rule: a Saturday holiday is taken the Friday before, a Sunday holiday the
    Monday after.

    Verified exact against actual 2025 and 2026 NYSE closures.

    What it cannot know: ad-hoc closures (presidential funerals, Hurricane
    Sandy). Those are rare and still produce a loud failure here, which is the
    right outcome -- a human should look. The failure message names the
    possibility.
    """

    rules = [
        Holiday("New Year's Day", month=1, day=1, observance=nearest_workday),
        USMartinLutherKingJr,
        USPresidentsDay,
        GoodFriday,
        USMemorialDay,
        # NYSE began observing Juneteenth in 2022.
        Holiday("Juneteenth", month=6, day=19, start_date="2022-06-19",
                observance=nearest_workday),
        Holiday("Independence Day", month=7, day=4, observance=nearest_workday),
        USLaborDay,
        USThanksgivingDay,
        Holiday("Christmas", month=12, day=25, observance=nearest_workday),
    ]


@functools.lru_cache(maxsize=8)
def _holidays(year: int) -> frozenset[dt.date]:
    """Closures for `year` +/- 1, so a step back across a New Year boundary
    still sees the holidays on the far side."""
    lo = pd.Timestamp(year=year - 1, month=1, day=1)
    hi = pd.Timestamp(year=year + 1, month=12, day=31)
    return frozenset(d.date() for d in _NYSECalendar().holidays(lo, hi))


def _is_trading_day(d: dt.date) -> bool:
    return d.weekday() < 5 and d not in _holidays(d.year)


def _last_trading_day_before(today: dt.date) -> dt.date:
    """Most recent NYSE session strictly before `today`.

    Holiday-awareness is the whole point: without it, the morning after every
    market holiday this check demanded a close that does not exist, failed,
    triggered a pointless refresh, failed again and exited non-zero. It
    self-healed the next day, which is exactly why it survived ~9 false
    failures a year unfixed.
    """
    d = today - dt.timedelta(days=1)
    while not _is_trading_day(d):
        d -= dt.timedelta(days=1)
    return d


def _trading_days_before(today: dt.date, n: int) -> dt.date:
    """`n` NYSE sessions back from `today`. MAX_STALE_TRADING_DAYS is named in
    trading days, but the old code subtracted CALENDAR days from the last
    session -- a no-op at the current value of 1, and silently wrong at any
    other. Stepping session by session makes the constant mean what it says.
    """
    d = today
    for _ in range(n):
        d = _last_trading_day_before(d)
    return d


def check_freshness(data_dir: Path, today: dt.date | None = None) -> tuple[bool, dt.date, dt.date]:
    """Returns (is_fresh, latest_date_in_store, required_since)."""
    today = today or dt.date.today()
    cat, ticker = REFERENCE_TICKER
    path = reader.ticker_path(data_dir, cat, ticker)
    prices = reader.load(path)["close"].dropna().sort_index()
    latest = prices.index[-1].date()
    required_since = _trading_days_before(today, MAX_STALE_TRADING_DAYS)
    return latest >= required_since, latest, required_since


def main() -> int:
    data_dir = config.raw_data_dir()
    is_fresh, latest, required_since = check_freshness(data_dir)

    if is_fresh:
        print(f"LOCAL DATA: fresh (latest {latest}, required since {required_since}).")
        return 0

    print(f"LOCAL DATA: stale -- latest is {latest}, required since {required_since}. Refreshing...")
    result = subprocess.run([sys.executable, "-m", "asset_universe.update"],
                             cwd=Path(__file__).parent, capture_output=True, text=True)
    if result.returncode != 0:
        print("LOCAL DATA: refresh FAILED -- do not trust local analysis until this is fixed.")
        print(result.stderr[-2000:])
        return 1

    is_fresh_now, latest_now, _ = check_freshness(data_dir)
    if not is_fresh_now:
        print(f"LOCAL DATA: still stale after refresh (latest {latest_now}) -- "
              f"the market may genuinely have no newer close (an ad-hoc NYSE "
              f"closure is not in this script's holiday rules), or yfinance "
              f"access is broken. Check which before trusting anything.")
        return 1
    print(f"LOCAL DATA: refreshed, now fresh (latest {latest_now}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
