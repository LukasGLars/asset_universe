"""
check_signal_changes.py

Extracts an "actionable signal fingerprint" from a status.md dashboard
snapshot (AVGO guard state, LLY-stress, joint-stress, silver GSR state,
opportunistic sleeve status, confirmed regime flip, AVGO/LLY earnings
reminders) and compares two snapshots. Used by sync.yml to decide whether
the daily run is worth an email: silence when nothing actionable changed,
a one-line summary when something did. Price/valuation noise (which
changes every day) is deliberately not part of the fingerprint.

Usage:
    python check_signal_changes.py <prev_status.md> <curr_status.md>

Exit code 0 always. Prints nothing (no output) if unchanged. Prints a
one-line, human-readable summary to stdout if something changed -- that
output is used directly as the notification email body by sync.yml.
Missing/unparseable fields degrade to "unknown" rather than crashing --
check_sync_health.py already fails the job loudly on genuinely broken
status.md content; this script's job is signal comparison, not validation.
"""
from __future__ import annotations

import re
import sys


def _find(pattern: str, text: str, default: str = "unknown") -> str:
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else default


def extract_fingerprint(text: str) -> dict:
    return {
        "avgo_guard": _find(r"AVGO 200d Guard.*?Signal\s*:\s*(\S+)", text),
        "avgo_trigger": _find(r"AVGO 200d Guard.*?trigger:\s*(\S+)\)", text),
        "avgo_action": _find(r"AVGO 200d Guard.*?Action\s*:\s*([^\n]+)", text),
        "lly_stress": _find(r"LLY stress\s*:\s*(\S+)", text),
        "joint_stress": _find(r"Joint stress\s*:\s*(\S+)", text),
        "silver_signal": _find(r"Silver GSR Tactical.*?Signal\s*:\s*(\S+)", text),
        "silver_action": _find(r"Silver GSR Tactical.*?Action\s*:\s*([^\n]+)", text),
        "sleeve_status": _find(r"Opportunistic Sleeve.*?Status\s*:\s*(\S+)", text),
        "regime_flip": "FLIP" if re.search(r"REGIME CHANGE ALERT", text) else "stable",
        "avgo_earnings_reminder": _find(r"AVGO Earnings Checkpoint.*?Reminder\s*:\s*(\S+)", text),
        "lly_earnings_reminder": _find(r"LLY Earnings Checkpoint.*?Reminder\s*:\s*(\S+)", text),
    }


LABELS = {
    "avgo_guard": "AVGO guard",
    "avgo_trigger": "AVGO guard trigger",
    "lly_stress": "LLY stress",
    "joint_stress": "Joint stress",
    "silver_signal": "Silver GSR",
    "sleeve_status": "Opportunistic sleeve",
    "regime_flip": "Regime",
}


def build_actionable_message(prev: dict, curr: dict) -> tuple[str, str] | None:
    """
    Builds (subject, body) leading with the exact instruction to act on --
    not just "X changed to Y". Pulls the same Action-line text fi_tracker.py
    already computes and prints live, so the wording here can never drift
    from what the dashboard itself says to do.

    Returns None if nothing actionable changed.
    """
    blocks: list[str] = []
    subject_parts: list[str] = []

    avgo_changed = (prev["avgo_guard"] != curr["avgo_guard"]
                     or prev["avgo_trigger"] != curr["avgo_trigger"]
                     or prev["joint_stress"] != curr["joint_stress"])
    if avgo_changed and "unknown" not in (prev["avgo_guard"], curr["avgo_guard"]):
        blocks.append(
            f"AVGO GUARD: {prev['avgo_guard']} -> {curr['avgo_guard']}"
            f" (trigger: {curr['avgo_trigger']}, joint stress: {curr['joint_stress']})\n"
            f"ACTION: {curr['avgo_action']}"
        )
        subject_parts.append(f"AVGO guard -> {curr['avgo_guard']}")

    # LLY stress can flip on its own without the AVGO guard also firing --
    # informational only in that case, no trade follows from it alone.
    if (prev["lly_stress"] != curr["lly_stress"] and not avgo_changed
            and "unknown" not in (prev["lly_stress"], curr["lly_stress"])):
        blocks.append(
            f"LLY STRESS (informational, no AVGO guard change): "
            f"{prev['lly_stress']} -> {curr['lly_stress']}\n"
            f"No action -- only matters if the AVGO guard fires too."
        )

    if prev["silver_signal"] != curr["silver_signal"] and "unknown" not in (prev["silver_signal"], curr["silver_signal"]):
        blocks.append(
            f"SILVER GSR: {prev['silver_signal']} -> {curr['silver_signal']}\n"
            f"ACTION: {curr['silver_action']}"
        )
        subject_parts.append(f"Silver -> {curr['silver_signal']}")

    if prev["sleeve_status"] != curr["sleeve_status"] and "unknown" not in (prev["sleeve_status"], curr["sleeve_status"]):
        blocks.append(
            f"OPPORTUNISTIC SLEEVE: {prev['sleeve_status']} -> {curr['sleeve_status']}\n"
            f"REVIEW: run `run_entry_screen.py` for the candidate/exit details."
        )
        subject_parts.append(f"Sleeve -> {curr['sleeve_status']}")

    if prev["regime_flip"] != curr["regime_flip"] and curr["regime_flip"] == "FLIP":
        blocks.append(
            "REGIME FLIP confirmed.\n"
            "REVIEW: rotation-sleeve candidates may have changed -- check "
            "status.md's exit-priority table / run_universe_screen.py."
        )
        subject_parts.append("Regime FLIP")

    # Earnings reminders fire once, on the not_due -> DUE transition only --
    # the reverse (DUE -> not_due, once the date passes) isn't actionable.
    if (curr["avgo_earnings_reminder"] == "DUE" and prev["avgo_earnings_reminder"] != "DUE"
            and "unknown" not in (prev["avgo_earnings_reminder"], curr["avgo_earnings_reminder"])):
        blocks.append(
            "AVGO EARNINGS due within the next 7 days.\n"
            "ACTION: after the print, check actual AI revenue/EPS against the "
            "$56B FY26 / $100B FY27 guided path."
        )
        subject_parts.append("AVGO earnings due")

    if (curr["lly_earnings_reminder"] == "DUE" and prev["lly_earnings_reminder"] != "DUE"
            and "unknown" not in (prev["lly_earnings_reminder"], curr["lly_earnings_reminder"])):
        blocks.append(
            "LLY EARNINGS due within the next 7 days.\n"
            "ACTION: after the print, check the growth trajectory against guidance."
        )
        subject_parts.append("LLY earnings due")

    if not blocks:
        return None

    subject = "Asset Universe: " + (", ".join(subject_parts) if subject_parts else "review needed")
    body = "\n\n".join(blocks)
    return subject, body


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: check_signal_changes.py <prev_status.md> <curr_status.md>", file=sys.stderr)
        sys.exit(0)  # fail open -- never block the sync job over this check

    prev_path, curr_path = sys.argv[1], sys.argv[2]
    try:
        with open(prev_path, "r", encoding="utf-8", errors="replace") as f:
            prev = extract_fingerprint(f.read())
        with open(curr_path, "r", encoding="utf-8", errors="replace") as f:
            curr = extract_fingerprint(f.read())
    except FileNotFoundError:
        # No previous snapshot (first run ever) -- nothing to compare against.
        sys.exit(0)

    result = build_actionable_message(prev, curr)
    if result:
        subject, body = result
        print(f"{subject}\n{body}")


if __name__ == "__main__":
    main()
