import datetime as dt
import os
import subprocess

from check_sync_health import (
    GRACE_PERIOD,
    most_recent_required_run,
    run_health_check,
)

HEALTHY_STATUS = """\
==============================================================
TACTICAL RULES
==============================================================

  Silver GSR Tactical
    Signal         : INACTIVE
    Action         : No action -- hold base

  AVGO 200d Guard
    Signal         : BASE
    Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)

  AVGO Earnings Checkpoint
    Next earnings  : 2026-09-03
    Action         : check guided trajectory

  LLY Earnings Checkpoint
    Next earnings  : 2026-08-06
    Action         : check guided trajectory
"""


def _write(path, text, mtime=None):
    path.write_text(text, encoding="utf-8")
    if mtime is not None:
        ts = mtime.timestamp()
        os.utime(path, (ts, ts))


def test_most_recent_required_run_friday_evening_covers_weekend():
    # Saturday morning -- Friday 20:30 UTC run is still the latest required one.
    saturday = dt.datetime(2026, 7, 4, 10, 0, tzinfo=dt.timezone.utc)
    required = most_recent_required_run(saturday)
    assert required == dt.datetime(2026, 7, 3, 20, 30, tzinfo=dt.timezone.utc)


def test_most_recent_required_run_monday_morning_after_grace():
    # Monday 10:00 UTC, past the 06:00 + 3h grace -> Monday morning run required.
    monday = dt.datetime(2026, 7, 6, 10, 0, tzinfo=dt.timezone.utc)
    required = most_recent_required_run(monday)
    assert required == dt.datetime(2026, 7, 6, 6, 0, tzinfo=dt.timezone.utc)


def test_healthy_status_passes(tmp_path):
    status_path = tmp_path / "status.md"
    now = dt.datetime(2026, 7, 6, 10, 0, tzinfo=dt.timezone.utc)
    _write(status_path, HEALTHY_STATUS, mtime=now - dt.timedelta(minutes=5))

    problems = run_health_check(status_path, now)
    assert problems == []


def test_stale_status_fails(tmp_path):
    status_path = tmp_path / "status.md"
    now = dt.datetime(2026, 7, 6, 10, 0, tzinfo=dt.timezone.utc)
    # Last touched well before Friday's run -- a multi-day outage.
    _write(status_path, HEALTHY_STATUS, mtime=now - dt.timedelta(days=4))

    problems = run_health_check(status_path, now)
    assert any("last modified" in p for p in problems)


def test_broken_content_fails(tmp_path):
    status_path = tmp_path / "status.md"
    now = dt.datetime(2026, 7, 6, 10, 0, tzinfo=dt.timezone.utc)
    broken = HEALTHY_STATUS.replace(
        "Signal         : BASE",
        "Signal         : [unavailable -- HTTPError]",
    )
    _write(status_path, broken, mtime=now - dt.timedelta(minutes=5))

    problems = run_health_check(status_path, now)
    assert any("[unavailable" in p for p in problems)


def test_missing_section_fails(tmp_path):
    status_path = tmp_path / "status.md"
    now = dt.datetime(2026, 7, 6, 10, 0, tzinfo=dt.timezone.utc)
    missing = HEALTHY_STATUS.split("AVGO Earnings Checkpoint")[0]
    _write(status_path, missing, mtime=now - dt.timedelta(minutes=5))

    problems = run_health_check(status_path, now)
    assert any("AVGO Earnings Checkpoint" in p for p in problems)


def test_freshness_uses_git_commit_time_not_checkout_mtime(tmp_path):
    # Simulates the exact failure mode this check exists to catch: a fresh
    # `actions/checkout` resets the file's mtime to "now" even though the
    # content is a month-old commit. If freshness used mtime alone, a stale
    # file checked out today would wrongly read as fresh.
    repo = tmp_path
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    status_path = repo / "status.md"
    _write(status_path, HEALTHY_STATUS, mtime=None)  # mtime = now, as a real checkout would leave it

    old_commit_date = "2026-06-01T12:00:00+00:00"
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": old_commit_date,
        "GIT_COMMITTER_DATE": old_commit_date,
    }
    subprocess.run(["git", "add", "status.md"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "user.email=t@example.com",
         "-c", "user.name=Test", "commit", "-q", "-m", "old"],
        cwd=repo, check=True, env=env,
    )

    now = dt.datetime(2026, 7, 6, 10, 0, tzinfo=dt.timezone.utc)
    problems = run_health_check(status_path, now)
    assert any("last modified" in p for p in problems)
