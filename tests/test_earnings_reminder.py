import datetime as dt

from earnings_reminder import earnings_reminder_state

TODAY = dt.date(2026, 7, 6)


def test_none_date_is_unknown():
    assert earnings_reminder_state(None, TODAY) == "unknown"


def test_far_out_is_not_due():
    assert earnings_reminder_state(TODAY + dt.timedelta(days=10), TODAY) == "not_due"


def test_exactly_at_lead_boundary_is_due():
    assert earnings_reminder_state(TODAY + dt.timedelta(days=7), TODAY) == "DUE"


def test_just_outside_lead_boundary_is_not_due():
    assert earnings_reminder_state(TODAY + dt.timedelta(days=8), TODAY) == "not_due"


def test_today_is_due():
    assert earnings_reminder_state(TODAY, TODAY) == "DUE"


def test_already_passed_is_not_due():
    assert earnings_reminder_state(TODAY - dt.timedelta(days=1), TODAY) == "not_due"


def test_state_is_binary_not_a_day_count():
    # Same window, different days-out -- must collapse to the same string
    # so the diff-based notifier doesn't re-fire every day inside the window.
    assert (earnings_reminder_state(TODAY + dt.timedelta(days=7), TODAY)
            == earnings_reminder_state(TODAY + dt.timedelta(days=1), TODAY)
            == "DUE")
