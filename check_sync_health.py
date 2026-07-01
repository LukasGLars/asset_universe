#!/usr/bin/env python3
"""Operational fail-safe for the daily-sync GitHub Actions job.

The portfolio strategy (AVGO 200d guard, silver GSR tactical, AVGO earnings
checkpoint) depends entirely on `.github/workflows/sync.yml` running every
weekday and writing a healthy `status.md`. A silent failure (network blip,
a yfinance API change, an Actions runner hiccup) currently looks identical
to "the guard ran and said hold" -- there's no signal that distinguishes
them. This script closes that gap with two checks:

  1. Freshness -- status.md's last-modified time must be recent enough
     given the cron schedule in sync.yml (06:00 UTC / 20:30 UTC, Mon-Fri).
     The Fri-evening -> Mon-morning gap (up to ~60h with no scheduled run)
     is handled by walking the actual weekday schedule backwards rather
     than using a flat hour threshold.
  2. Content -- status.md must be free of failure signatures
     (`[unavailable`, `Traceback`, `Error`) and must contain each of the
     key sections fi_tracker.py is expected to emit.

Exit code 0 = healthy, 1 = stale or broken content. Run as a step in
sync.yml so a non-zero exit fails the Actions run, which surfaces as a
failed run and triggers GitHub's default failure-run email to the repo
owner.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

STATUS_FILE = Path(__file__).resolve().parent / "status.md"

# Cron schedule mirrored from .github/workflows/sync.yml (UTC, weekdays only):
#   '30 20 * * 1-5'  -> 22:30 CEST after NYSE close
#   '0 6 * * 1-5'    -> 08:00 CEST morning FRED catch-up
SCHEDULED_RUN_TIMES_UTC = [
    dt.time(hour=6, minute=0),
    dt.time(hour=20, minute=30),
]

# How long to wait after a scheduled run time before treating a missing
# update as a real problem. Generous enough to absorb Actions queueing
# delays / retries, tight enough to catch a same-day outage rather than
# waiting for the next scheduled slot (which could be ~14h or, across a
# weekend, ~60h away).
GRACE_PERIOD = dt.timedelta(hours=3)

REQUIRED_SECTIONS = [
    "Silver GSR Tactical",
    "AVGO 200d Guard",
    "AVGO Earnings Checkpoint",
]

FAILURE_SIGNATURES = [
    "[unavailable",
    "Traceback",
    "Error",
]


def most_recent_required_run(now_utc: dt.datetime) -> dt.datetime:
    """Latest scheduled run (Mon-Fri, 06:00/20:30 UTC) that should already
    have completed and been committed, i.e. scheduled_time + GRACE_PERIOD
    <= now_utc. Walks backwards day by day so the Fri-evening -> Mon-
    morning gap is handled naturally instead of via a flat threshold."""
    for day_offset in range(10):  # generous lookback, covers any long weekend
        day = now_utc.date() - dt.timedelta(days=day_offset)
        if day.weekday() >= 5:  # Saturday=5, Sunday=6
            continue
        for run_time in sorted(SCHEDULED_RUN_TIMES_UTC, reverse=True):
            scheduled = dt.datetime.combine(day, run_time, tzinfo=dt.timezone.utc)
            if scheduled + GRACE_PERIOD <= now_utc:
                return scheduled
    raise RuntimeError("no scheduled run found within 10-day lookback")


def check_freshness(status_path: Path, now_utc: dt.datetime) -> list[str]:
    if not status_path.exists():
        return [f"{status_path} does not exist"]

    mtime = dt.datetime.fromtimestamp(status_path.stat().st_mtime, tz=dt.timezone.utc)
    required_since = most_recent_required_run(now_utc)

    if mtime < required_since:
        age = now_utc - mtime
        return [
            f"status.md last modified {mtime.isoformat()} ({age} ago), but the "
            f"scheduled run at {required_since.isoformat()} (+{GRACE_PERIOD} grace) "
            f"should already have refreshed it"
        ]
    return []


def check_content(text: str) -> list[str]:
    problems = []

    if not text.strip():
        return ["status.md is empty"]

    for sig in FAILURE_SIGNATURES:
        if sig in text:
            offending_line = next((l for l in text.splitlines() if sig in l), "")
            problems.append(f"failure signature {sig!r} found: {offending_line.strip()!r}")

    for section in REQUIRED_SECTIONS:
        if section not in text:
            problems.append(f"missing required section: {section!r}")

    return problems


def run_health_check(status_path: Path, now_utc: dt.datetime) -> list[str]:
    problems = check_freshness(status_path, now_utc)
    if status_path.exists():
        text = status_path.read_text(encoding="utf-8", errors="replace")
        problems += check_content(text)
    return problems


def main(argv: list[str]) -> int:
    status_path = Path(argv[1]) if len(argv) > 1 else STATUS_FILE
    now_utc = dt.datetime.now(dt.timezone.utc)

    problems = run_health_check(status_path, now_utc)

    if problems:
        print("SYNC HEALTH CHECK: FAIL")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("SYNC HEALTH CHECK: OK")
    print(f"  {status_path} is fresh and contains no failure signatures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
