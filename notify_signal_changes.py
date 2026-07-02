"""
notify_signal_changes.py

Sends a one-line email via Gmail SMTP if check_signal_changes.py detects an
actionable signal change between status.md.prev (the previous day's
committed dashboard) and status.md (today's). Silent (sends nothing, exits
0) when nothing actionable changed or when either file is missing (e.g.
first-ever run).

Requires env vars EMAIL_ADDRESS and EMAIL_PASSWORD (a Gmail App Password,
not the account password -- see MEMORY.md). Sends to the same address it
sends from. Never raises on a missing/misconfigured mailer -- a failed
notification should not fail the daily sync job; the pre-existing
check_sync_health.py step is the thing that's supposed to fail loudly.

Usage:
    python notify_signal_changes.py status.md.prev status.md
"""
from __future__ import annotations

import os
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path

from check_signal_changes import extract_fingerprint, LABELS


def build_change_summary(prev_path: str, curr_path: str) -> str | None:
    if not Path(prev_path).exists() or not Path(curr_path).exists():
        return None
    prev = extract_fingerprint(Path(prev_path).read_text(encoding="utf-8", errors="replace"))
    curr = extract_fingerprint(Path(curr_path).read_text(encoding="utf-8", errors="replace"))
    changes = [
        f"{LABELS[k]}: {prev[k]} -> {curr[k]}"
        for k in LABELS
        if prev[k] != curr[k] and "unknown" not in (prev[k], curr[k])
    ]
    return "; ".join(changes) if changes else None


def send_email(subject: str, body: str) -> None:
    address = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = address
    msg["To"] = address

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(address, password)
        server.send_message(msg)


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: notify_signal_changes.py <prev_status.md> <curr_status.md>", file=sys.stderr)
        return

    # Manual on-demand test send (workflow_dispatch input), bypasses the
    # diff entirely -- lets you verify Gmail SMTP auth works without
    # waiting for a real signal to flip.
    if os.environ.get("FORCE_TEST_EMAIL") == "true":
        try:
            send_email("Asset Universe: test email", "This is a manual test send -- notification pipeline is working.")
            print("Test email sent.")
        except Exception as e:
            print(f"Test email send failed: {e}", file=sys.stderr)
        return

    summary = build_change_summary(sys.argv[1], sys.argv[2])
    if not summary:
        print("No actionable signal change -- no email sent.")
        return

    try:
        send_email("Asset Universe: signal change", summary)
        print(f"Email sent: {summary}")
    except Exception as e:
        # Don't fail the sync job over a notification failure -- log and move on.
        print(f"Email send failed (non-fatal): {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
