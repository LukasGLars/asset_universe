"""
notify_signal_changes.py

Sends a Telegram message if check_signal_changes.py detects an actionable
signal change between status.md.prev (the previous day's committed
dashboard) and status.md (today's). Silent (sends nothing, exits 0) when
nothing actionable changed or when either file is missing (e.g. first-ever
run).

Requires env vars TELEGRAM_BOT_TOKEN (secret) and TELEGRAM_CHAT_ID
(variable, not sensitive -- just an identifier). Telegram is the channel
for urgent/time-sensitive items per the 2026-07-03 ops-scope decision
(guard/joint-stress/silver/sleeve events); the FI@50 pace digest and
quarterly thesis re-check are separate, lower-urgency work that goes via
email instead, not built here.

Never raises on a missing/misconfigured sender -- a failed notification
should not fail the daily sync job; check_sync_health.py is the thing
responsible for failing loudly on a genuinely broken sync.

Usage:
    python notify_signal_changes.py status.md.prev status.md
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from check_signal_changes import build_actionable_message, extract_fingerprint


def build_change_email(prev_path: str, curr_path: str) -> tuple[str, str] | None:
    """Returns (subject, body) leading with the exact action to take, or
    None if nothing actionable changed. Name kept from the email-era
    pipeline -- still just "the message to send", channel-agnostic."""
    if not Path(prev_path).exists() or not Path(curr_path).exists():
        return None
    prev = extract_fingerprint(Path(prev_path).read_text(encoding="utf-8", errors="replace"))
    curr = extract_fingerprint(Path(curr_path).read_text(encoding="utf-8", errors="replace"))
    return build_actionable_message(prev, curr)


def send_telegram(subject: str, body: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    text = f"{subject}\n\n{body}"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API returned not-ok: {result}")


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: notify_signal_changes.py <prev_status.md> <curr_status.md>", file=sys.stderr)
        return

    # Manual on-demand test send (workflow_dispatch input), bypasses the
    # diff entirely -- lets you verify Telegram delivery works without
    # waiting for a real signal to flip.
    if os.environ.get("FORCE_TEST_TELEGRAM") == "true":
        try:
            send_telegram("Asset Universe: test message", "This is a manual test send -- notification pipeline is working.")
            print("Test Telegram message sent.")
        except Exception as e:
            print(f"Test Telegram send failed: {e}", file=sys.stderr)
        return

    result = build_change_email(sys.argv[1], sys.argv[2])
    if not result:
        print("No actionable signal change -- no message sent.")
        return

    subject, body = result
    try:
        send_telegram(subject, body)
        print(f"Telegram message sent -- subject: {subject}\n{body}")
    except Exception as e:
        # Don't fail the sync job over a notification failure -- log and move on.
        print(f"Telegram send failed (non-fatal): {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
