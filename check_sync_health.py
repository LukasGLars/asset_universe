#!/usr/bin/env python3
"""Operational fail-safe for the daily-sync GitHub Actions job.

The portfolio strategy (AVGO 200d guard, silver GSR tactical, AVGO earnings
checkpoint) depends entirely on `.github/workflows/sync.yml` running every
weekday and writing a healthy `status.md`. A silent failure (network blip,
a yfinance API change, an Actions runner hiccup) currently looks identical
to "the guard ran and said hold" -- there's no signal that distinguishes
them. This script closes that gap with two checks:

  1. Freshness -- status.md's last-modified time must be recent enough
     given the cron schedule in sync.yml (06:07 UTC / 20:37 UTC, Mon-Fri --
     offset off round minutes 2026-07-08 after measuring a consistent
     166-286min delay on the old exact-hour slots). The Fri-evening ->
     Mon-morning gap (up to ~60h with no scheduled run) is handled by
     walking the actual weekday schedule backwards rather than using a
     flat hour threshold.
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
import subprocess
import sys
from pathlib import Path

STATUS_FILE = Path(__file__).resolve().parent / "status.md"

# Cron schedule mirrored from .github/workflows/sync.yml (UTC, weekdays only).
# Offset off round minutes 2026-07-08 -- see sync.yml's own comment for the
# measured delay data that motivated this:
#   '37 20 * * 1-5'  -> ~22:37 CEST after NYSE close
#   '7 6 * * 1-5'    -> ~08:07 CEST morning FRED catch-up
SCHEDULED_RUN_TIMES_UTC = [
    dt.time(hour=6, minute=7),
    dt.time(hour=20, minute=37),
]

# How long to wait after a scheduled run time before treating a missing
# update as a real problem. Generous enough to absorb Actions queueing
# delays / retries, tight enough to catch a same-day outage rather than
# waiting for the next scheduled slot (which could be ~14h or, across a
# weekend, ~60h away).
GRACE_PERIOD = dt.timedelta(hours=3)

REQUIRED_SECTIONS = [
    "Silver GSR Tactical",
    "AVGO Trend Diagnostic",
    "AVGO Earnings Checkpoint",
    "LLY Earnings Checkpoint",
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


def _last_updated(status_path: Path) -> dt.datetime:
    """Prefer the file's last git-commit time over filesystem mtime.
    `actions/checkout` resets mtimes to checkout time on every job, so mtime
    alone would make a stale file look freshly-written to any workflow other
    than the one that generated it. Falls back to mtime when the path isn't
    in a git repo (e.g. tests using a bare tmp_path)."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", status_path.name],
            cwd=status_path.resolve().parent,
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = result.stdout.strip()
        if result.returncode == 0 and out:
            return dt.datetime.fromisoformat(out)
    except (OSError, subprocess.SubprocessError):
        pass
    return dt.datetime.fromtimestamp(status_path.stat().st_mtime, tz=dt.timezone.utc)


def check_freshness(status_path: Path, now_utc: dt.datetime) -> list[str]:
    if not status_path.exists():
        return [f"{status_path} does not exist"]

    mtime = _last_updated(status_path)
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
