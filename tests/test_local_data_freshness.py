import datetime as dt

from check_local_data_freshness import _last_trading_day_before


def test_last_trading_day_before_monday_is_friday():
    monday = dt.date(2026, 7, 6)
    assert _last_trading_day_before(monday) == dt.date(2026, 7, 3)


def test_last_trading_day_before_tuesday_is_monday():
    tuesday = dt.date(2026, 7, 7)
    assert _last_trading_day_before(tuesday) == dt.date(2026, 7, 6)


def test_last_trading_day_before_sunday_is_friday():
    sunday = dt.date(2026, 7, 5)
    assert _last_trading_day_before(sunday) == dt.date(2026, 7, 3)


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
