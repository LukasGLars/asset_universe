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

Delivery for a real actionable change retries Telegram a couple of times,
then falls back to email (EMAIL_ADDRESS/EMAIL_PASSWORD -- the same Gmail
App Password secrets provisioned for the pre-Telegram pipeline, PR #14)
before giving up. Only if BOTH channels fail does this escalate (non-zero
exit), which fails the Actions run so GitHub's own failure-run email is a
third, independent channel. Fixed 2026-07-07: previously a single Telegram
API hiccup would jump straight to "hope you read the GitHub failure email"
with no attempt to route around it first.

SUPPRESS_NOTIFY=true skips sending entirely, before the diff even runs.
For use when deploying a fix that changes tracked state (e.g. backfilling
a state file) -- the diff would otherwise read the correction itself as a
"real" transition and fire a phantom alert (this happened for real on
2026-07-07 fixing the HWM sleeve-state gap: a manual re-run to verify the
fix sent a live "Sleeve CLOSED -> OPEN" message for a position that had
actually been open since 2026-06-24).

The "nothing actionable changed" case and the manual FORCE_TEST_TELEGRAM
diagnostic path stay single-attempt/non-fatal -- there's nothing urgent to
retry or escalate in either of those.

Usage:
    python notify_signal_changes.py status.md.prev status.md
"""
from __future__ import annotations

import json
import os
import smtplib
import sys
import time
import urllib.error
import urllib.request
from email.mime.text import MIMEText
from pathlib import Path

from check_signal_changes import (
    build_actionable_message,
    build_rebalance_snapshot_message,
    extract_fingerprint,
)

TELEGRAM_RETRIES = 2
RETRY_DELAY_SECONDS = 2


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


def send_email_fallback(subject: str, body: str) -> None:
    """Backup delivery via Gmail SMTP, used only when Telegram itself is
    unreachable. Reuses EMAIL_ADDRESS/EMAIL_PASSWORD -- already provisioned
    as repo secrets from the pre-Telegram notification pipeline."""
    address = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]

    msg = MIMEText(body)
    msg["Subject"] = f"[Telegram unreachable] {subject}"
    msg["From"] = address
    msg["To"] = address

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(address, password)
        server.send_message(msg)


def send_with_retry_and_fallback(subject: str, body: str) -> None:
    """Retry Telegram a couple of times, then fall back to email, before
    giving up. Raises only if every channel fails."""
    last_err: Exception | None = None
    for attempt in range(TELEGRAM_RETRIES):
        try:
            send_telegram(subject, body)
            return
        except Exception as e:
            last_err = e
            if attempt < TELEGRAM_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)

    try:
        send_email_fallback(subject, body)
        print(f"Telegram failed after {TELEGRAM_RETRIES} attempts ({last_err}) -- email fallback succeeded.")
        return
    except Exception as email_err:
        raise RuntimeError(
            f"Telegram failed ({last_err}) and email fallback also failed ({email_err})"
        ) from email_err


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: notify_signal_changes.py <prev_status.md> <curr_status.md>", file=sys.stderr)
        return 0

    # State-correction escape hatch -- see module docstring. Checked before
    # anything else so a fix deploy never masquerades as a real event.
    if os.environ.get("SUPPRESS_NOTIFY") == "true":
        print("Notification suppressed (SUPPRESS_NOTIFY=true) -- state correction, not a real event.")
        return 0

    # Manual on-demand test send (workflow_dispatch input), bypasses the
    # diff entirely -- lets you verify Telegram delivery works without
    # waiting for a real signal to flip. Non-fatal, single-attempt: this is
    # a diagnostic, not a real actionable event.
    if os.environ.get("FORCE_TEST_TELEGRAM") == "true":
        try:
            send_telegram("Asset Universe: test message", "This is a manual test send -- notification pipeline is working.")
            print("Test Telegram message sent.")
        except Exception as e:
            print(f"Test Telegram send failed: {e}", file=sys.stderr)
        return 0

    # On-demand resend of whatever is CURRENTLY out of band in the AVGO
    # Rebalance Check, bypassing the diff -- see
    # build_rebalance_snapshot_message()'s docstring for why the diff-based
    # alert structurally cannot announce a condition that predates it (e.g.
    # the day this feature ships, or any time state was out of band before
    # the operator started watching). This IS real actionable content if
    # anything is out of band, so it uses the same retry+fallback path as a
    # genuine diff-triggered alert, not the single-attempt test path above.
    if os.environ.get("FORCE_SEND_REBALANCE") == "true":
        try:
            with open(sys.argv[2], "r", encoding="utf-8", errors="replace") as f:
                curr_text = f.read()
        except FileNotFoundError:
            print(f"Cannot force-send: {sys.argv[2]} not found.", file=sys.stderr)
            return 1

        result = build_rebalance_snapshot_message(curr_text)
        if not result:
            print("FORCE_SEND_REBALANCE set, but nothing is currently out of band -- no message sent.")
            return 0

        subject, body = result
        try:
            send_with_retry_and_fallback(subject, body)
            print(f"Rebalance snapshot delivered -- subject: {subject}\n{body}")
            return 0
        except Exception as e:
            print(f"Rebalance snapshot delivery FAILED on all channels: {e}", file=sys.stderr)
            print(f"Undelivered message was:\n{subject}\n{body}", file=sys.stderr)
            return 1

    result = build_change_email(sys.argv[1], sys.argv[2])
    if not result:
        print("No actionable signal change -- no message sent.")
        return 0

    subject, body = result
    try:
        send_with_retry_and_fallback(subject, body)
        print(f"Message delivered -- subject: {subject}\n{body}")
        return 0
    except Exception as e:
        # This IS a real actionable event that failed on every channel --
        # escalate by failing the job, so GitHub's own failure-run email is
        # a third, independent fallback.
        print(f"Delivery FAILED on all channels for an actionable change: {e}", file=sys.stderr)
        print(f"Undelivered message was:\n{subject}\n{body}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
