#!/usr/bin/env python3
"""Telegram alert when the daily sync fails.

Why this exists: the signal-change notification is the last step of sync.yml,
so any earlier failure stops the workflow and sends nothing at all. On
2026-09-08 the freshness guard tripped three times and the only way to find out
was to open the Actions tab.

The signal itself is not lost — the next successful run diffs against the last
committed status.md, so a change that happened during the outage is still
reported. What is lost is knowing the system stopped, which matters most on the
run that was supposed to tell you to act.

Deliberately quotes no portfolio numbers. Per CLAUDE.md an alert must read its
numbers from the source rather than restate them, and this one runs precisely
when the source is untrustworthy or absent. It reports which run failed and
where to look, nothing more.
"""
from __future__ import annotations

import os
import sys

# Written by the workflow's commit step. Its presence is the only reliable way
# to tell a failure that wrote nothing from one that already pushed status.md,
# and the two need opposite advice.
COMMIT_MARKER = ".sync_committed"

from notify_signal_changes import send_with_retry_and_fallback


def build_message() -> tuple[str, str]:
    workflow = os.environ.get("GITHUB_WORKFLOW", "daily-sync")
    repo     = os.environ.get("GITHUB_REPOSITORY", "")
    run_id   = os.environ.get("GITHUB_RUN_ID", "")
    reason   = (os.environ.get("FAILED_STEP") or "").strip()

    committed = os.path.exists(COMMIT_MARKER)

    subject = f"[asset_universe] {workflow} FAILED"
    lines = [f"The {workflow} workflow failed and did not complete.", ""]

    if committed:
        # The dangerous case. status.md was pushed, so the next run snapshots
        # THIS commit as status.md.prev and diffs against it — any change this
        # run would have reported is gone, not merely delayed.
        subject += " (after commit — check manually)"
        lines += [
            "It failed AFTER pushing a new status.md, so no signal notification "
            "was sent and the next run will diff against this commit rather than "
            "the previous one.",
            "",
            "A signal change in this run will NOT be reported later. Read "
            "status.md on master and compare it yourself.",
        ]
    else:
        lines += [
            "It failed before writing anything, so master still holds the last "
            "successful sync.",
            "",
            "A signal change during the outage is not lost: the next successful "
            "run diffs against that same committed status.md and will report it "
            "then.",
        ]
    if reason:
        lines += ["", f"Failing step: {reason}"]
    if repo and run_id:
        lines += ["", f"Log: https://github.com/{repo}/actions/runs/{run_id}"]
    return subject, "\n".join(lines)


def main() -> int:
    subject, body = build_message()
    try:
        send_with_retry_and_fallback(subject, body)
    except Exception as e:
        # Never mask the original failure with a notification failure — the
        # workflow is already red and that is what the operator must see.
        print(f"Failure notification could not be delivered: {e}", file=sys.stderr)
        return 0
    print("Failure notification sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
