"""preview_all_triggers.py

One-off diagnostic: confirms EVERY known actionable trigger (not just the
AVGO guard flip that preview_notification.yml already covers) actually
fires a real Telegram send end-to-end, through the real production code
(check_signal_changes.build_actionable_message, notify_signal_changes.
send_telegram) -- unit tests already prove the logic is correct; this
proves delivery actually works for each trigger type, which unit tests
can't cover.

Uses a controlled synthetic baseline (same shape as the test fixtures),
not live status.md -- this is a mechanism test ("does this trigger fire
and deliver"), not a real portfolio status update, so deterministic
synthetic data is more reliable than string-matching against whatever the
live file happens to contain today. Nothing here commits, pushes, or
modifies any tracked file.

Usage:
    python preview_all_triggers.py
"""
from __future__ import annotations

import sys
import time

from check_signal_changes import build_actionable_message, extract_fingerprint
from notify_signal_changes import send_telegram

BASE = """
  AVGO Trend Diagnostic
    AVGO now       : $377.75  (as of 2026-06-30)
    200d SMA       : $360.14  (+4.9% gap)
    5d ROC         : -0.6%  (gap-down buy level: -10%)
    Signal         : BASE  (trigger: none)  -- informational, no rotation
    LLY stress     : inactive  ($1199.43 vs 200d SMA $978.00, 5d ROC +8.3%)
    Joint stress   : inactive  -- retired alongside the guard, shown for continuity only
    Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)

  Silver GSR Tactical
    GSR now        : 67.64
    Signal         : INACTIVE
    Action         : No action -- hold base

  Opportunistic Sleeve
    Status         : CLOSED (0/1 position)

  AVGO Earnings Checkpoint
    Next earnings  : 2026-09-03
    Reminder       : not_due
    Latest quarter : 2026-04-30
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)

  LLY Earnings Checkpoint
    Next earnings  : 2026-08-05
    Reminder       : not_due
    Latest quarter : 2026-03-31
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)

  Regime check (2026-07-06): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
"""

SCENARIOS = [
    ("AVGO guard flip", BASE.replace(
        "Signal         : BASE  (trigger: none)  -- informational, no rotation", "Signal         : DEFENSIVE  (trigger: CRASH)  -- informational, no rotation"
    ).replace(
        "Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)",
        "Action         : No rotation. But the 5d/-10% gap-down trigger has fired: this is the tranche-deployment signal (guard retired, PR #88).",
    )),
    ("Silver GSR trigger", BASE.replace(
        "Signal         : INACTIVE\n    Action         : No action -- hold base",
        "Signal         : T1 ACTIVE\n    Action         : ADD +12% silver (fund from AVGO: AVGO -> 43%, Silver -> 12%)",
    )),
    ("Opportunistic sleeve opens", BASE.replace(
        "Status         : CLOSED (0/1 position)", "Status         : OPEN (1/1 position)"
    )),
    ("Regime flip", BASE + "\n  REGIME CHANGE ALERT -- 2026-07-06\n"),
    ("AVGO earnings reminder due", BASE.replace(
        "AVGO Earnings Checkpoint\n    Next earnings  : 2026-09-03\n    Reminder       : not_due",
        "AVGO Earnings Checkpoint\n    Next earnings  : 2026-09-03\n    Reminder       : DUE",
    )),
    ("LLY earnings reminder due", BASE.replace(
        "LLY Earnings Checkpoint\n    Next earnings  : 2026-08-05\n    Reminder       : not_due",
        "LLY Earnings Checkpoint\n    Next earnings  : 2026-08-05\n    Reminder       : DUE",
    )),
    ("AVGO earnings just reported", BASE.replace(
        "Latest quarter : 2026-04-30\n    Beat streak    : 4\n    Guidance trend : revising up",
        "Latest quarter : 2026-09-03\n    Beat streak    : 5\n    Guidance trend : revising up",
    )),
    ("LLY earnings just reported", BASE.replace(
        "Latest quarter : 2026-03-31\n    Beat streak    : 4",
        "Latest quarter : 2026-08-05\n    Beat streak    : 5",
    )),
]


def main() -> int:
    prev_fp = extract_fingerprint(BASE)
    failures = 0

    for name, curr_text in SCENARIOS:
        curr_fp = extract_fingerprint(curr_text)
        result = build_actionable_message(prev_fp, curr_fp)
        if result is None:
            print(f"[{name}] FAILED: no actionable message generated (trigger logic didn't fire)")
            failures += 1
            continue

        subject, body = result
        try:
            send_telegram(f"[TEST] {subject}", f"(preview_all_triggers -- {name})\n\n{body}")
            print(f"[{name}] OK -- sent: {subject}")
        except Exception as e:
            print(f"[{name}] FAILED to send: {e}")
            failures += 1
        time.sleep(1)  # avoid tripping Telegram's rate limit across 8 sends

    print(f"\n{len(SCENARIOS) - failures}/{len(SCENARIOS)} triggers fired and delivered.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
