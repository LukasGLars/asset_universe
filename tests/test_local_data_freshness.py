import datetime as dt

import pytest

from check_local_data_freshness import (
    _is_trading_day,
    _last_trading_day_before,
    _trading_days_before,
)


def test_last_trading_day_before_tuesday_is_monday():
    tuesday = dt.date(2026, 7, 7)
    assert _last_trading_day_before(tuesday) == dt.date(2026, 7, 6)


def test_last_trading_day_before_a_weekend_skips_back_over_a_friday_closure():
    """This case previously asserted the bug. 2026-07-03 is the OBSERVED
    Independence Day closure (Jul 4 is a Saturday), so the last session before
    that weekend is Thursday Jul 2, not the Friday."""
    sunday = dt.date(2026, 7, 5)
    assert not _is_trading_day(dt.date(2026, 7, 3))
    assert _last_trading_day_before(sunday) == dt.date(2026, 7, 2)


# ── Holiday-awareness (2026-10-02) ───────────────────────────────────────────
# The original version skipped weekends only. On the morning after every NYSE
# closure it required a close that does not exist, so the check failed, forced
# a pointless refresh, failed again and exited non-zero -- then self-healed the
# next day, which is why it ran for months as accepted noise.
#
# Note the first case below: 2026-07-06 is a Monday and the PREVIOUS Friday
# 2026-07-03 was the observed Independence Day holiday (Jul 4 fell on a
# Saturday). The old code returned that Friday. It is not a session.

def test_monday_after_an_observed_friday_holiday_skips_back_to_thursday():
    monday = dt.date(2026, 7, 6)
    assert _last_trading_day_before(monday) == dt.date(2026, 7, 2)


@pytest.mark.parametrize(
    "holiday, previous_session",
    [
        (dt.date(2026, 1, 1),  dt.date(2025, 12, 31)),  # New Year's Day
        (dt.date(2026, 1, 19), dt.date(2026, 1, 16)),   # MLK Day (Mon)
        (dt.date(2026, 2, 16), dt.date(2026, 2, 13)),   # Washington's Birthday
        (dt.date(2026, 4, 3),  dt.date(2026, 4, 2)),    # Good Friday
        (dt.date(2026, 5, 25), dt.date(2026, 5, 22)),   # Memorial Day
        (dt.date(2026, 6, 19), dt.date(2026, 6, 18)),   # Juneteenth (Fri)
        (dt.date(2026, 9, 7),  dt.date(2026, 9, 4)),    # Labor Day
        (dt.date(2026, 11, 26), dt.date(2026, 11, 25)), # Thanksgiving
        (dt.date(2026, 12, 25), dt.date(2026, 12, 24)), # Christmas (Fri)
    ],
)
def test_day_after_each_closure_requires_the_session_before_it(holiday, previous_session):
    """The real failure shape: asked on the day AFTER a closure, the last
    session must be the one before the closure, never the closure itself."""
    assert not _is_trading_day(holiday)
    assert _last_trading_day_before(holiday) == previous_session
    # And the day after the closure must look past it to the same session --
    # that is the morning the live check actually ran and failed.
    assert _last_trading_day_before(holiday + dt.timedelta(days=1)) == previous_session


def test_juneteenth_was_not_a_closure_before_2022():
    assert _is_trading_day(dt.date(2021, 6, 18))
    assert not _is_trading_day(dt.date(2022, 6, 20))  # observed Mon, Jun 19 = Sun


def test_thanksgiving_friday_is_a_session():
    """A half day is still a session with a close -- it must not be skipped."""
    assert _is_trading_day(dt.date(2026, 11, 27))


def test_christmas_eve_is_a_session():
    assert _is_trading_day(dt.date(2026, 12, 24))


def test_step_back_crosses_the_new_year_boundary():
    """The holiday set is built per-year; a step back from early January must
    still see the previous December's closures."""
    assert _last_trading_day_before(dt.date(2026, 1, 2)) == dt.date(2025, 12, 31)


def test_trading_days_before_counts_sessions_not_calendar_days():
    """MAX_STALE_TRADING_DAYS is named in trading days. The old code subtracted
    calendar days from the last session, which was a no-op at 1 and wrong at
    anything else."""
    tuesday = dt.date(2026, 7, 7)
    assert _trading_days_before(tuesday, 1) == dt.date(2026, 7, 6)
    assert _trading_days_before(tuesday, 2) == dt.date(2026, 7, 2)   # skips Jul 3 holiday
    assert _trading_days_before(tuesday, 3) == dt.date(2026, 7, 1)


def test_trading_days_before_zero_is_today():
    assert _trading_days_before(dt.date(2026, 7, 7), 0) == dt.date(2026, 7, 7)


# ── Delisted tickers must stay out of the fetch universe (2026-08-19) ───────
# A delisted ticker makes yfinance return nothing, which made
# `python -m asset_universe.update` exit non-zero, which made
# check_local_data_freshness.py report the whole refresh FAILED -- leaving
# the local store silently stale while analysis scripts kept reading it.
# One dead name cost a day of freshness and a wrong trade price.
#
# The universe file is regenerated from an external S&P 500 constituent
# list, so a re-add is a live risk, not a hypothetical.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from asset_universe import config

DELISTED = {"EA", "SATS"}


def test_known_delisted_tickers_are_not_in_the_us_universe():
    tickers = set(config.load_universe("us_equities"))
    assert not (tickers & DELISTED), (
        f"delisted ticker(s) back in us_equities: {sorted(tickers & DELISTED)} -- "
        "they break the daily refresh, see the header comment in that file"
    )
