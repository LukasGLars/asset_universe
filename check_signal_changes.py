"""
check_signal_changes.py

Extracts an "actionable signal fingerprint" from a status.md dashboard
snapshot (AVGO guard state, LLY-stress, joint-stress, silver GSR state,
opportunistic sleeve status AND risk state (stop breach / time-exit due /
tripwire -- not just the bare OPEN/CLOSED word, which never changes for
the life of a trade no matter what the price does), a new ENTER candidate
appearing while the sleeve stays closed (the daily 4-gate screen reruns
every day regardless of manual triggering, but nothing used to diff its
verdict -- only the bare CLOSED word, which never changes either),
confirmed regime flip, AVGO/LLY earnings reminders and reported-quarter
changes) and compares
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
        "avgo_guard": _find(r"AVGO Trend Diagnostic.*?Signal\s*:\s*(\S+)", text),
        "avgo_trigger": _find(r"AVGO Trend Diagnostic.*?trigger:\s*(\S+)\)", text),
        "avgo_action": _find(r"AVGO Trend Diagnostic.*?Action\s*:\s*([^\n]+)", text),
        "lly_stress": _find(r"LLY stress\s*:\s*(\S+)", text),
        "joint_stress": _find(r"Joint stress\s*:\s*(\S+)", text),
        "silver_signal": _find(r"Silver GSR Tactical.*?Signal\s*:\s*(\S+)", text),
        "silver_action": _find(r"Silver GSR Tactical.*?Action\s*:\s*([^\n]+)", text),
        "sleeve_status": _find(r"Opportunistic Sleeve.*?Status\s*:\s*(\S+)", text),
        "sleeve_risk": _find(r"Opportunistic Sleeve.*?Risk\s*:\s*(\S+)", text),
        "sleeve_price": _find(r"Opportunistic Sleeve.*?Current price\s*:\s*(\S+)", text),
        "sleeve_stop": _find(r"Opportunistic Sleeve.*?Binding stop\s*:\s*(\S+)", text),
        "sleeve_risk_to_stop": _find(
            r"Opportunistic Sleeve.*?Current price\s*:\s*\S+\s*\(risk to stop:\s*([^)]+)\)", text),
        "sleeve_tripwire_detail": _find(r"Opportunistic Sleeve.*?Tripwire detail\s*:\s*([^\n]+)", text),
        "sleeve_candidate": _find(r"Opportunistic Sleeve.*?Best candidate\s*:\s*(\S+)", text),
        "sleeve_basket_candidate": _find(r"Opportunistic Sleeve.*?Basket-crash\s*:\s*(\S+)", text),
        # Scoped to each candidate's OWN Plan/Open lines (not just "the first
        # Plan: in the section") -- both can now appear together since
        # basket-crash visibility was decoupled from extension-gate priority
        # (see MEMORY.md "Basket-crash visibility decoupled from extension-
        # gate priority", 2026-07-30), so a single generic capture would grab
        # the extension's Plan/Open even when building the basket-crash
        # alert. The negative lookahead skips the "none eligible" case,
        # which has no following Plan/Open lines to match anyway.
        "sleeve_plan": _find(
            r"Best candidate\s*:\s*(?!none eligible)[^\n]*\n\s*Plan\s*:\s*([^\n]+)", text),
        "sleeve_open_cmd": _find(
            r"Best candidate\s*:\s*(?!none eligible)[^\n]*\n\s*Plan\s*:[^\n]*\n\s*Open\s*:\s*([^\n]+)", text),
        "sleeve_basket_plan": _find(
            r"Basket-crash\s*:\s*(?!none eligible)[^\n]*\n\s*Plan\s*:\s*([^\n]+)", text),
        "sleeve_basket_open_cmd": _find(
            r"Basket-crash\s*:\s*(?!none eligible)[^\n]*\n\s*Plan\s*:[^\n]*\n\s*Open\s*:\s*([^\n]+)", text),
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
        "rebal_gold_status": _find(r"AVGO Rebalance Check.*?Gold status:\s*(\S+)", text),
        "rebal_avgo_status": _find(r"AVGO Rebalance Check.*?AVGO status:\s*(\S+)", text),
        "rebal_lly_status": _find(r"AVGO Rebalance Check.*?LLY status:\s*(\S+)", text),
        "rebal_gold_detail": _find(r"AVGO Rebalance Check.*?Gold status:\s*\S+\s*([^\n]+)", text),
        "rebal_avgo_detail": _find(r"AVGO Rebalance Check.*?AVGO status:\s*\S+\s*([^\n]+)", text),
        "rebal_lly_detail": _find(r"AVGO Rebalance Check.*?LLY status:\s*\S+\s*([^\n]+)", text),
    }


LABELS = {
    "avgo_guard": "AVGO trend state",
    "avgo_trigger": "AVGO trend trigger",
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

    # AVGO guard RETIRED as a rotation rule 2026-08-16 -- it no longer
    # produces an actionable alert. A trend-state flip on its own is not a
    # trade: corrected for execution lag the guard halves CAGR and deepens
    # drawdown, and its crash leg is an 87% false alarm (PR #88).
    #
    # The ONE case still worth a push is the crash trigger, which survives as
    # a BUY signal for the gap-down tranche -- that rests on the gap-down
    # forward-return study, which has no execution assumption to get wrong.
    # A plain MA breach, an MA-breach clearing, or a joint-stress flip are all
    # silent now.
    avgo_changed = False
    if (prev["avgo_trigger"] != curr["avgo_trigger"]
            and curr["avgo_trigger"] == "CRASH"
            and "unknown" not in (prev["avgo_trigger"], curr["avgo_trigger"])):
        avgo_changed = True
        blocks.append(
            f"AVGO GAP-DOWN TRIGGER: 5d ROC breached -10%\n"
            f"ACTION: {curr['avgo_action']}"
        )
        subject_parts.append("AVGO gap-down trigger")

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
                  "see tripwire detail below")
        lines = [
            f"OPPORTUNISTIC SLEEVE RISK: {prev['sleeve_risk']} -> {curr['sleeve_risk']}",
            f"{label}: {detail}",
        ]
        # Full picture every time, not just whichever check happens to have
        # fired -- cluster health in particular is a coarse sector-only
        # match (confirmed 2026-07-09), so it shouldn't be the only thing
        # the alert says when it's the noisiest of the four checks.
        if curr["sleeve_tripwire_detail"] != "unknown":
            lines.append(f"Tripwire detail: {curr['sleeve_tripwire_detail']}")
        if curr["sleeve_risk_to_stop"] != "unknown":
            lines.append(
                f"Risk to stop: {curr['sleeve_risk_to_stop']} "
                f"(price {curr['sleeve_price']} vs stop {curr['sleeve_stop']})"
            )
        blocks.append("\n".join(lines))
        subject_parts.append(f"Sleeve risk -> {curr['sleeve_risk']}")

    # New ENTER candidate while the sleeve stays closed -- distinct from the
    # sleeve_status block above, which only fires on OPEN/CLOSED transitions
    # and would otherwise never catch a candidate quietly flipping PASS ->
    # ENTER in the daily rerun (2026-07-26 gap: the screen already reran
    # every day, nothing diffed its verdict). Guarded to CLOSED on both
    # sides so this can't double-fire alongside (or instead of) the
    # sleeve_status alert on the day the sleeve actually opens/closes.
    # Self-contained on purpose (see MEMORY.md "Sleeve alert clarity",
    # 2026-07-30): quotes the exact Plan/Open lines fi_tracker.py already
    # computed and printed, rather than telling the user to go run the
    # screen themselves -- they may not be able to before the signal moves.
    if (prev["sleeve_status"] == "CLOSED" and curr["sleeve_status"] == "CLOSED"
            and prev["sleeve_candidate"] in ("none", "unknown")
            and curr["sleeve_candidate"] not in ("none", "unknown")):
        lines = [f"OPPORTUNISTIC SLEEVE CANDIDATE: {curr['sleeve_candidate']} is now ENTER-eligible "
                 f"(sleeve remains closed)."]
        if curr["sleeve_plan"] != "unknown":
            lines.append(f"Plan: {curr['sleeve_plan']}")
        if curr["sleeve_open_cmd"] != "unknown":
            lines.append(f"Open: {curr['sleeve_open_cmd']}")
        blocks.append("\n".join(lines))
        subject_parts.append(f"Sleeve candidate -> {curr['sleeve_candidate']}")

    # Same pattern, for the basket-crash secondary pathway. Shown
    # independently of the extension-gate candidate above -- both can now
    # appear the same day (see MEMORY.md "Basket-crash visibility decoupled
    # from extension-gate priority", 2026-07-30) -- so this uses its OWN
    # scoped Plan/Open fields, not the extension's. Explicitly labeled
    # "secondary" / "backtest-only" so it isn't mistaken for equal-confidence
    # with the extension pathway when both fire together.
    if (prev["sleeve_status"] == "CLOSED" and curr["sleeve_status"] == "CLOSED"
            and prev["sleeve_basket_candidate"] in ("none", "unknown")
            and curr["sleeve_basket_candidate"] not in ("none", "unknown")):
        lines = [f"OPPORTUNISTIC SLEEVE BASKET-CRASH CANDIDATE: {curr['sleeve_basket_candidate']} "
                 f"is now eligible (secondary pathway, backtest-only -- sleeve remains closed)."]
        if curr["sleeve_basket_plan"] != "unknown":
            lines.append(f"Plan: {curr['sleeve_basket_plan']}")
        if curr["sleeve_basket_open_cmd"] != "unknown":
            lines.append(f"Open: {curr['sleeve_basket_open_cmd']}")
        blocks.append("\n".join(lines))
        subject_parts.append(f"Sleeve basket-crash candidate -> {curr['sleeve_basket_candidate']}")

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

    # AVGO Rebalance Check (2026-08-17): fires only on the HOLD -> SELL/BUY
    # transition (an asset NEWLY drifting out of the vol-target band), not on
    # every run while it stays out of band -- same "alert on transition, not
    # on persisting state" convention as every other block above. The
    # reverse (SELL/BUY -> HOLD, the gap closing) isn't actionable, so it's
    # deliberately silent too. Quotes fi_tracker.py's own detail line so the
    # trade size can never drift from what the dashboard says.
    for _asset, _status_key, _detail_key, _label in (
        ("Gold", "rebal_gold_status", "rebal_gold_detail", "Gold"),
        ("AVGO", "rebal_avgo_status", "rebal_avgo_detail", "AVGO"),
        ("LLY", "rebal_lly_status", "rebal_lly_detail", "LLY"),
    ):
        if (prev[_status_key] == "HOLD" and curr[_status_key] in ("SELL", "BUY")
                and "unknown" not in (prev[_status_key], curr[_status_key])):
            blocks.append(
                f"AVGO REBALANCE CHECK: {_label} drifted out of band ({curr[_status_key]}).\n"
                f"ACTION: {curr[_detail_key]}"
            )
            subject_parts.append(f"{_label} rebalance -> {curr[_status_key]}")

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
