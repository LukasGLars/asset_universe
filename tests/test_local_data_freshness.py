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
