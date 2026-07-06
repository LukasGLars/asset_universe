#!/usr/bin/env python3
"""Catches a `daily-sync` (sync.yml) run that GitHub's cron scheduler
silently dropped -- the schedule trigger has no retry or alerting of its
own, so a skipped fire looks identical to "everything is fine" until
someone happens to notice status.md's age.

Runs as a step in sync_sheet.yml, which fires every ~2h regardless of
weekday and has never missed a scheduled run -- a much shorter, more
reliable heartbeat than daily-sync's own Mon-Fri cron. Reuses
check_sync_health's schedule-aware freshness check (same grace period,
same weekday walk-back) so there's one definition of "stale", not two.

Behavior:
  - status.md is fresh -> do nothing, exit 0. Silent by design: an
    auto-heal that worked is not news.
  - status.md is stale -> re-trigger sync.yml via workflow_dispatch.
      Succeeds -> exit 0, still silent (self-healed, no action needed).
      Fails    -> send a Telegram alert (this is the one case that
                  actually needs a human) and exit 1, so a failed Actions
                  run + GitHub's default failure email is the second line
                  of defense if Telegram is also down.

Requires GITHUB_TOKEN (for the dispatch call) and, only on the failure
path, TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

from check_sync_health import STATUS_FILE, check_freshness
from notify_signal_changes import send_telegram

DAILY_SYNC_WORKFLOW = "sync.yml"
REF = "master"


def trigger_daily_sync() -> None:
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{DAILY_SYNC_WORKFLOW}/dispatches"
    payload = json.dumps({"ref": REF}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status != 204:
            raise RuntimeError(f"dispatch returned unexpected status {resp.status}")


def run_watchdog(status_path: Path, now_utc: dt.datetime) -> int:
    problems = check_freshness(status_path, now_utc)

    if not problems:
        print("WATCHDOG: daily-sync is fresh -- nothing to do.")
        return 0

    print("WATCHDOG: daily-sync looks stale:")
    for p in problems:
        print(f"  - {p}")

    try:
        trigger_daily_sync()
        print("WATCHDOG: re-triggered sync.yml -- self-healed, no alert needed.")
        return 0
    except Exception as e:
        message = (
            f"Watchdog could not re-trigger daily-sync: {e}\n\n"
            f"Manual check needed -- trigger sync.yml by hand."
        )
        print(f"WATCHDOG: {message}", file=sys.stderr)
        try:
            send_telegram("Asset Universe: sync watchdog needs attention", message)
        except Exception as telegram_err:
            print(f"WATCHDOG: Telegram alert also failed: {telegram_err}", file=sys.stderr)
        return 1


def main() -> int:
    return run_watchdog(STATUS_FILE, dt.datetime.now(dt.timezone.utc))


if __name__ == "__main__":
    raise SystemExit(main())
