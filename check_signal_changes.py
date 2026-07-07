"""
check_signal_changes.py

Extracts an "actionable signal fingerprint" from a status.md dashboard
snapshot (AVGO guard state, LLY-stress, joint-stress, silver GSR state,
opportunistic sleeve status AND risk state (stop breach / time-exit due /
tripwire -- not just the bare OPEN/CLOSED word, which never changes for
the life of a trade no matter what the price does), confirmed regime flip,
AVGO/LLY earnings reminders and reported-quarter changes) and compares
two snapshots. Used
by sync.yml to decide whether the daily run is worth an email: silence
when nothing actionable changed, a one-line summary when something did.
Price/valuation noise (which changes every day) is deliberately not part
of the fingerprint.

The "just reported" trigger (latest_quarter changing) fires the automated
half of the earnings-day checklist (beat streak, guidance-revision
direction) alongside an explicit prompt for the two items that aren't
automatable -- actual AI revenue vs. guided pace and contract-timing
commentary both require reading the real release/call, no API exposes
them.

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
        "sleeve_risk": _find(r"Opportunistic Sleeve.*?Risk\s*:\s*(\S+)", text),
        "sleeve_price": _find(r"Opportunistic Sleeve.*?Current price\s*:\s*(\S+)", text),
        "sleeve_stop": _find(r"Opportunistic Sleeve.*?Binding stop\s*:\s*(\S+)", text),
        "regime_flip": "FLIP" if re.search(r"REGIME CHANGE ALERT", text) else "stable",
        "avgo_earnings_reminder": _find(r"AVGO Earnings Checkpoint.*?Reminder\s*:\s*(\S+)", text),
        "lly_earnings_reminder": _find(r"LLY Earnings Checkpoint.*?Reminder\s*:\s*(\S+)", text),
        "avgo_latest_quarter": _find(r"AVGO Earnings Checkpoint.*?Latest quarter\s*:\s*(\S+)", text),
        "avgo_beat_streak": _find(r"AVGO Earnings Checkpoint.*?Beat streak\s*:\s*(\S+)", text),
        "avgo_guidance_trend": _find(r"AVGO Earnings Checkpoint.*?Guidance trend\s*:\s*([^\n(]+)", text),
        "avgo_eps_actual_vs_est": _find(r"AVGO Earnings Checkpoint.*?Latest qtr EPS \(actual vs est\.\)\s*:\s*([^\n]+)", text),
        "avgo_revenue_actual": _find(r"AVGO Earnings Checkpoint.*?Revenue \(latest qtr, actual\)\s*:\s*([^\n]+)", text),
        "avgo_revenue_next_q": _find(r"AVGO Earnings Checkpoint.*?Next-qtr revenue consensus\s*:\s*([^\n]+)", text),
        "lly_latest_quarter": _find(r"LLY Earnings Checkpoint.*?Latest quarter\s*:\s*(\S+)", text),
        "lly_beat_streak": _find(r"LLY Earnings Checkpoint.*?Beat streak\s*:\s*(\S+)", text),
        "lly_guidance_trend": _find(r"LLY Earnings Checkpoint.*?Guidance trend\s*:\s*([^\n(]+)", text),
        "lly_eps_actual_vs_est": _find(r"LLY Earnings Checkpoint.*?Latest qtr EPS \(actual vs est\.\)\s*:\s*([^\n]+)", text),
        "lly_revenue_actual": _find(r"LLY Earnings Checkpoint.*?Revenue \(latest qtr, actual\)\s*:\s*([^\n]+)", text),
        "lly_revenue_next_q": _find(r"LLY Earnings Checkpoint.*?Next-qtr revenue consensus\s*:\s*([^\n]+)", text),
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

    # Risk state on an OPEN position -- distinct from the status line above,
    # which only flips OPEN/CLOSED on a manual --open/--close and would
    # otherwise never fire again for the life of the trade no matter what
    # the price actually does (this was the actual gap: exit triggers were
    # being computed and shown in status.md, but nothing diffed the values,
    # only the bare OPEN/CLOSED word).
    if (prev["sleeve_risk"] != curr["sleeve_risk"]
            and "unknown" not in (prev["sleeve_risk"], curr["sleeve_risk"])):
        urgent = curr["sleeve_risk"] in ("STOPPED", "TIME-EXIT-DUE")
        label = "ACTION" if urgent else "REVIEW"
        detail = (f"price {curr['sleeve_price']} vs stop {curr['sleeve_stop']}"
                  if curr["sleeve_risk"] == "STOPPED" else
                  "time exit has arrived" if curr["sleeve_risk"] == "TIME-EXIT-DUE" else
                  "run `run_entry_screen.py` for tripwire detail")
        blocks.append(
            f"OPPORTUNISTIC SLEEVE RISK: {prev['sleeve_risk']} -> {curr['sleeve_risk']}\n"
            f"{label}: {detail}"
        )
        subject_parts.append(f"Sleeve risk -> {curr['sleeve_risk']}")

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
            "ACTION: after the print, check AI revenue against management's CURRENT guided "
            "pace -- don't assume prior guidance still holds."
        )
        subject_parts.append("AVGO earnings due")

    if (curr["lly_earnings_reminder"] == "DUE" and prev["lly_earnings_reminder"] != "DUE"
            and "unknown" not in (prev["lly_earnings_reminder"], curr["lly_earnings_reminder"])):
        blocks.append(
            "LLY EARNINGS due within the next 7 days.\n"
            "ACTION: after the print, check the growth trajectory against guidance."
        )
        subject_parts.append("LLY earnings due")

    # A new reported quarter appearing is the actual earnings-day trigger --
    # distinct from the reminder above (which fires *before* the print).
    # Reports what changed (revenue, EPS beat streak, guidance trend) --
    # no "go check X" language; the two items that genuinely need a human
    # reading the release (AI revenue vs. guided pace, contract-timing
    # commentary) aren't restated here every time -- see earnings_verdict.py.
    if (curr["avgo_latest_quarter"] != prev["avgo_latest_quarter"]
            and "unknown" not in (prev["avgo_latest_quarter"], curr["avgo_latest_quarter"])):
        blocks.append(
            f"AVGO EARNINGS JUST REPORTED (quarter: {curr['avgo_latest_quarter']}).\n"
            f"EPS: {curr['avgo_eps_actual_vs_est']}\n"
            f"Revenue: {curr['avgo_revenue_actual']} | Next-qtr consensus: {curr['avgo_revenue_next_q']}\n"
            f"EPS beat streak: {curr['avgo_beat_streak']} | Guidance: {curr['avgo_guidance_trend']}"
        )
        subject_parts.append("AVGO earnings reported")

    if (curr["lly_latest_quarter"] != prev["lly_latest_quarter"]
            and "unknown" not in (prev["lly_latest_quarter"], curr["lly_latest_quarter"])):
        blocks.append(
            f"LLY EARNINGS JUST REPORTED (quarter: {curr['lly_latest_quarter']}).\n"
            f"EPS: {curr['lly_eps_actual_vs_est']}\n"
            f"Revenue: {curr['lly_revenue_actual']} | Next-qtr consensus: {curr['lly_revenue_next_q']}\n"
            f"EPS beat streak: {curr['lly_beat_streak']} | Guidance: {curr['lly_guidance_trend']}"
        )
        subject_parts.append("LLY earnings reported")

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
