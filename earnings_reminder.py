"""earnings_reminder.py

Pure logic for the earnings-checkpoint reminder: fires once, when a
ticker's next earnings date comes within `lead_days`, then stays constant
until the date passes and the next cycle's date is far out again.

Deliberately a plain state string ("DUE" / "not_due"/"unknown"), not a
day-count -- a day-count would change every single day inside the lead
window, and check_signal_changes.py's diff-based notifier would treat each
of those as a fresh change and fire daily. A binary state only flips twice
per quarter (enter the window, then leave it), which is what makes reusing
that existing "notify only on change" pipeline correct here with no new
send logic.
"""
from __future__ import annotations

import datetime as dt

LEAD_DAYS = 7


def earnings_reminder_state(
    next_earnings_date: dt.date | None,
    today: dt.date,
    lead_days: int = LEAD_DAYS,
) -> str:
    if next_earnings_date is None:
        return "unknown"
    days_out = (next_earnings_date - today).days
    if 0 <= days_out <= lead_days:
        return "DUE"
    return "not_due"
