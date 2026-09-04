import subprocess
import sys
from pathlib import Path

from check_signal_changes import build_actionable_message, extract_fingerprint

FIXTURE_BASE = """
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
    Latest qtr EPS (actual vs est.): $2.44 vs $2.40  (+1.7% surprise)
    Revenue (latest qtr, actual): $14.92B  (TTM YoY: +32.3%)
    Next-qtr revenue consensus : $16.10B (implied YoY +28.1%)
    Next earnings  : 2026-09-03
    Reminder       : not_due
    Latest quarter : 2026-04-30
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)

  LLY Earnings Checkpoint
    Latest qtr EPS (actual vs est.): $8.55 vs $6.79  (+25.9% surprise)
    Revenue (latest qtr, actual): $12.73B  (TTM YoY: +47.4%)
    Next-qtr revenue consensus : $13.50B (implied YoY +40.2%)
    Next earnings  : 2026-08-06
    Reminder       : not_due
    Latest quarter : 2026-03-31
    Beat streak    : 4
    Guidance trend : revising up  (+1yr estimate vs. 90 days ago)

  Regime check (2026-06-30): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)

  AVGO Rebalance Check  [existing capital, band: 5%]
    Gold status: HOLD  (27.7% actual vs 27.7% target, gap +0.0%)
    AVGO status: HOLD  (35.0% actual vs 33.5% target, gap -1.5%)
    LLY status: HOLD  (37.3% actual vs 38.8% target, gap +1.5%)
"""

FIXTURE_REBAL_AVGO_SELL = FIXTURE_BASE.replace(
    "    AVGO status: HOLD  (35.0% actual vs 33.5% target, gap -1.5%)",
    "    AVGO status: SELL  (46.8% actual vs 33.5% target, gap -13.3%) -- ~29 shares (~107,382 kr)",
)

FIXTURE_REBAL_LLY_BUY = FIXTURE_BASE.replace(
    "    LLY status: HOLD  (37.3% actual vs 38.8% target, gap +1.5%)",
    "    LLY status: BUY  (22.3% actual vs 38.8% target, gap +16.5%) -- ~12 shares (~133,499 kr)",
)

# Guard retired as a rotation rule 2026-08-16 (PR #88). The CRASH trigger
# survives as a gap-down BUY signal -- that rests on the gap-down forward-
# return study, which has no execution assumption to get wrong.
FIXTURE_GAP_DOWN_FIRED = FIXTURE_BASE.replace(
    "Signal         : BASE  (trigger: none)  -- informational, no rotation", "Signal         : DEFENSIVE  (trigger: CRASH)  -- informational, no rotation"
).replace(
    "Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)",
    "Action         : No rotation. But the 5d/-10% gap-down trigger has fired: "
    "if the gap-down tranche (50k into AVGO) hasn't been deployed yet, this is "
    "that signal -- see MEMORY.md 'Gap-down tranche validated'.",
)

# A plain 200d-SMA breach with no crash: silent since the retirement.
FIXTURE_MA_BREACH_ONLY = FIXTURE_BASE.replace(
    "Signal         : BASE  (trigger: none)  -- informational, no rotation", "Signal         : DEFENSIVE  (trigger: MA)  -- informational, no rotation"
)

FIXTURE_REGIME_FLIP = FIXTURE_BASE + "\n  REGIME CHANGE ALERT -- 2026-07-05\n"

FIXTURE_SLEEVE_OPEN_CLEAN = FIXTURE_BASE.replace(
    "  Opportunistic Sleeve\n    Status         : CLOSED (0/1 position)\n",
    "  Opportunistic Sleeve\n"
    "    Status         : OPEN -- HWM @ $276.93 (2026-06-24), 11 sh\n"
    "    Current price  : $277.91\n"
    "    Time exit      : 2026-07-24  (17d left)\n"
    "    Binding stop   : $271.39 (HARD)\n"
    "    Tripwires      : CLEAN\n"
    "    Risk           : CLEAN\n",
)

FIXTURE_SLEEVE_STOPPED = FIXTURE_SLEEVE_OPEN_CLEAN.replace(
    "    Current price  : $277.91", "    Current price  : $269.50"
).replace(
    "    Tripwires      : CLEAN\n    Risk           : CLEAN", "    Tripwires      : CLEAN\n    Risk           : STOPPED"
)

FIXTURE_SLEEVE_TRIPWIRE = FIXTURE_SLEEVE_OPEN_CLEAN.replace(
    "    Tripwires      : CLEAN\n    Risk           : CLEAN",
    "    Tripwires      : FLAGGED -- run run_entry_screen.py for detail\n    Risk           : TRIPWIRE",
)

# Real 2026-07-09 HWM case: cluster health fires, other 3 checks are clean --
# the enriched fixture carries the full one-line breakdown plus the
# risk-to-stop annotation, exactly what the daily status.md now prints.
FIXTURE_SLEEVE_TRIPWIRE_DETAILED = FIXTURE_SLEEVE_OPEN_CLEAN.replace(
    "    Current price  : $277.91\n",
    "    Current price  : $271.58  (risk to stop: 20 kr, 0.07% of sleeve capital)\n",
).replace(
    "    Tripwires      : CLEAN\n    Risk           : CLEAN",
    "    Tripwires      : FLAGGED -- run run_entry_screen.py for detail\n"
    "    Tripwire detail : RS +9.1% [OK] | Regime stable [OK] | MA50 $264.99 (slope +10.68) [OK] | "
    "Cluster avg -6.9% [WATCH, sector-only match -- low-confidence]\n"
    "    Risk           : TRIPWIRE",
)


FIXTURE_SLEEVE_CLOSED_NO_CANDIDATE = FIXTURE_BASE.replace(
    "  Opportunistic Sleeve\n    Status         : CLOSED (0/1 position)\n",
    "  Opportunistic Sleeve\n"
    "    Status         : CLOSED (0/1 position)\n"
    "    Best candidate : none eligible today (either no ENTER survivors, or all "
    "failed the pre-entry tripwire gate)\n"
    "    Basket-crash   : none eligible today\n",
)

# Plan/Open lines are what the Telegram alert now quotes verbatim (see
# MEMORY.md "Sleeve alert clarity", 2026-07-30) -- self-contained enough to
# act on without running the screen.
FIXTURE_SLEEVE_CLOSED_WITH_CANDIDATE = FIXTURE_BASE.replace(
    "  Opportunistic Sleeve\n    Status         : CLOSED (0/1 position)\n",
    "  Opportunistic Sleeve\n"
    "    Status         : CLOSED (0/1 position)\n"
    "    Best candidate : HWM (Howmet Aerospace)  $275.43  (ext +1.2%, 21d med +4.1%, div ROBUST)\n"
    "    Plan           : buy near $275.43, hold ~21d, stop = MA50-5% then trails 3% once +5% gain\n"
    "    Open           : run_entry_screen.py --open HWM <fill_price> <shares> <capital_sek>\n",
)

FIXTURE_SLEEVE_CLOSED_WITH_BASKET_CANDIDATE = FIXTURE_BASE.replace(
    "  Opportunistic Sleeve\n    Status         : CLOSED (0/1 position)\n",
    "  Opportunistic Sleeve\n"
    "    Status         : CLOSED (0/1 position)\n"
    "    Best candidate : none eligible today (either no ENTER survivors, or all "
    "failed the pre-entry tripwire gate)\n"
    "    Basket-crash   : EME (Emerson Electric Co.)  $650.12  (sector Industrials, -14.0% 5d, "
    "2 peers crashing)\n"
    "    Plan           : buy near $650.12, flat 21d exit, NO stop until +8% gain then trails 8% "
    "(no floor before that -- riskier than the extension pathway above)\n"
    "    Open           : run_entry_screen.py --open EME <fill_price> <shares> <capital_sek> "
    "--entry-type basket_crash\n",
)

# Both real at once -- reachable since 2026-07-30 (basket-crash visibility no
# longer suppressed just because extension has a pick). The two Plan/Open
# pairs must stay correctly attributed to their own candidate.
FIXTURE_SLEEVE_CLOSED_WITH_BOTH_CANDIDATES = FIXTURE_BASE.replace(
    "  Opportunistic Sleeve\n    Status         : CLOSED (0/1 position)\n",
    "  Opportunistic Sleeve\n"
    "    Status         : CLOSED (0/1 position)\n"
    "    Best candidate : HWM (Howmet Aerospace)  $275.43  (ext +1.2%, 21d med +4.1%, div ROBUST)\n"
    "    Plan           : buy near $275.43, hold ~21d, stop = MA50-5% then trails 3% once +5% gain\n"
    "    Open           : run_entry_screen.py --open HWM <fill_price> <shares> <capital_sek>\n"
    "    Basket-crash   : EME (Emerson Electric Co.)  $650.12  (sector Industrials, -14.0% 5d, "
    "2 peers crashing)\n"
    "    Plan           : buy near $650.12, flat 21d exit, NO stop until +8% gain then trails 8% "
    "(no floor before that -- riskier than the extension pathway)\n"
    "    Open           : run_entry_screen.py --open EME <fill_price> <shares> <capital_sek> "
    "--entry-type basket_crash\n"
    "    NOTE           : extension pathway also has a candidate today (HWM) -- that one is "
    "preferred (live-validated); this is shown for awareness.\n",
)


def test_extract_fingerprint_parses_known_fields():
    fp = extract_fingerprint(FIXTURE_BASE)
    assert fp["avgo_guard"] == "BASE"
    assert fp["avgo_trigger"] == "none"
    assert fp["avgo_action"] == "Hold base (Gold 25%, AVGO 55%, LLY 20%)"
    assert fp["lly_stress"] == "inactive"
    assert fp["joint_stress"] == "inactive"
    assert fp["silver_signal"] == "INACTIVE"
    assert fp["silver_action"] == "No action -- hold base"
    assert fp["sleeve_status"] == "CLOSED"
    assert fp["regime_flip"] == "stable"
    assert fp["avgo_earnings_reminder"] == "not_due"
    assert fp["lly_earnings_reminder"] == "not_due"
    assert fp["avgo_latest_quarter"] == "2026-04-30"
    assert fp["avgo_beat_streak"] == "4"
    assert fp["avgo_guidance_trend"] == "revising up"
    assert fp["avgo_eps_actual_vs_est"] == "$2.44 vs $2.40  (+1.7% surprise)"
    assert fp["avgo_revenue_actual"] == "$14.92B  (TTM YoY: +32.3%)"
    assert fp["avgo_revenue_next_q"] == "$16.10B (implied YoY +28.1%)"
    assert fp["lly_latest_quarter"] == "2026-03-31"
    assert fp["lly_beat_streak"] == "4"
    assert fp["lly_guidance_trend"] == "revising up"
    assert fp["lly_eps_actual_vs_est"] == "$8.55 vs $6.79  (+25.9% surprise)"
    assert fp["lly_revenue_actual"] == "$12.73B  (TTM YoY: +47.4%)"
    assert fp["lly_revenue_next_q"] == "$13.50B (implied YoY +40.2%)"


def test_extract_fingerprint_detects_regime_flip():
    fp = extract_fingerprint(FIXTURE_REGIME_FLIP)
    assert fp["regime_flip"] == "FLIP"


def test_no_message_when_unchanged():
    fp = extract_fingerprint(FIXTURE_BASE)
    assert build_actionable_message(fp, fp) is None


def test_gap_down_trigger_still_alerts_and_leads_with_action():
    prev = extract_fingerprint(FIXTURE_BASE)
    curr = extract_fingerprint(FIXTURE_GAP_DOWN_FIRED)
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result

    assert "gap-down" in subject.lower()
    # The whole point: the exact instruction must be present, not just the
    # raw state transition.
    assert "ACTION:" in body
    assert "gap-down tranche" in body
    # And it must NOT tell the operator to rotate -- that rule is retired.
    assert "Rotate AVGO" not in body


def test_plain_ma_breach_is_silent_since_guard_retirement():
    """A 200d-SMA breach with no crash used to trigger a full rotation alert.
    Retired 2026-08-16: corrected for execution lag the guard halves CAGR and
    deepens drawdown, so a trend-state flip is not a trade and must not page
    the operator."""
    prev = extract_fingerprint(FIXTURE_BASE)
    curr = extract_fingerprint(FIXTURE_MA_BREACH_ONLY)
    assert build_actionable_message(prev, curr) is None


def test_extract_fingerprint_parses_open_sleeve_risk_fields():
    fp = extract_fingerprint(FIXTURE_SLEEVE_OPEN_CLEAN)
    assert fp["sleeve_status"] == "OPEN"
    assert fp["sleeve_risk"] == "CLEAN"
    assert fp["sleeve_price"] == "$277.91"
    assert fp["sleeve_stop"] == "$271.39"


def test_sleeve_risk_stopped_fires_as_action_not_review():
    prev = extract_fingerprint(FIXTURE_SLEEVE_OPEN_CLEAN)
    curr = extract_fingerprint(FIXTURE_SLEEVE_STOPPED)
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result
    assert "Sleeve risk -> STOPPED" in subject
    assert "CLEAN -> STOPPED" in body
    assert "ACTION" in body
    assert "$269.50" in body and "$271.39" in body


def test_sleeve_risk_tripwire_fires_as_review_not_action():
    prev = extract_fingerprint(FIXTURE_SLEEVE_OPEN_CLEAN)
    curr = extract_fingerprint(FIXTURE_SLEEVE_TRIPWIRE)
    result = build_actionable_message(prev, curr)
    assert result is not None
    _, body = result
    assert "CLEAN -> TRIPWIRE" in body
    assert "REVIEW" in body
    assert "ACTION" not in body.split("\n")[0]  # not framed as urgent for a soft flag


def test_extract_fingerprint_parses_tripwire_detail_and_risk_to_stop():
    fp = extract_fingerprint(FIXTURE_SLEEVE_TRIPWIRE_DETAILED)
    assert fp["sleeve_tripwire_detail"] == (
        "RS +9.1% [OK] | Regime stable [OK] | MA50 $264.99 (slope +10.68) [OK] | "
        "Cluster avg -6.9% [WATCH, sector-only match -- low-confidence]"
    )
    assert fp["sleeve_risk_to_stop"] == "20 kr, 0.07% of sleeve capital"
    # existing sleeve_price parsing must still grab just the price token,
    # not the trailing risk-to-stop parenthetical.
    assert fp["sleeve_price"] == "$271.58"


def test_sleeve_risk_alert_carries_full_tripwire_picture_not_just_cluster():
    # The actual fix requested 2026-07-09: the alert must include the RS/
    # regime/MA50 checks too, not just whichever one fired -- cluster
    # health is the noisiest of the four and shouldn't be the only thing
    # the message says.
    prev = extract_fingerprint(FIXTURE_SLEEVE_OPEN_CLEAN)
    curr = extract_fingerprint(FIXTURE_SLEEVE_TRIPWIRE_DETAILED)
    result = build_actionable_message(prev, curr)
    assert result is not None
    _, body = result
    assert "CLEAN -> TRIPWIRE" in body
    assert "RS +9.1% [OK]" in body
    assert "Regime stable [OK]" in body
    assert "MA50 $264.99 (slope +10.68) [OK]" in body
    assert "Cluster avg -6.9% [WATCH, sector-only match -- low-confidence]" in body
    assert "20 kr, 0.07% of sleeve capital" in body
    assert "$271.58" in body and "$271.39" in body


def test_sleeve_risk_alert_omits_detail_lines_when_status_md_lacks_them():
    # Backward compatible: an older/plain status.md without the new lines
    # still produces a valid (if less detailed) message, not a crash or
    # a literal "unknown" leaking into the Telegram text.
    prev = extract_fingerprint(FIXTURE_SLEEVE_OPEN_CLEAN)
    curr = extract_fingerprint(FIXTURE_SLEEVE_TRIPWIRE)
    result = build_actionable_message(prev, curr)
    assert result is not None
    _, body = result
    assert "unknown" not in body


def test_sleeve_risk_unchanged_produces_no_message():
    fp = extract_fingerprint(FIXTURE_SLEEVE_OPEN_CLEAN)
    assert build_actionable_message(fp, fp) is None


def test_lly_stress_alone_is_silent_since_guard_retirement():
    """LLY stress only ever mattered as the escalation leg of the AVGO guard
    (joint stress). With the guard retired there is no rule it can escalate,
    so it no longer generates a message at all -- previously it produced an
    explicitly informational 'no action' block."""
    prev = extract_fingerprint(FIXTURE_BASE)
    changed = FIXTURE_BASE.replace("LLY stress     : inactive", "LLY stress     : ACTIVE")
    curr = extract_fingerprint(changed)
    assert build_actionable_message(prev, curr) is None


def test_avgo_earnings_reminder_fires_once_on_transition():
    prev = extract_fingerprint(FIXTURE_BASE)
    curr = extract_fingerprint(FIXTURE_BASE.replace(
        "Next earnings  : 2026-09-03\n    Reminder       : not_due",
        "Next earnings  : 2026-09-03\n    Reminder       : DUE",
    ))
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result
    assert "AVGO earnings due" in subject
    assert "AVGO EARNINGS due" in body


def test_lly_earnings_reminder_fires_once_on_transition():
    prev = extract_fingerprint(FIXTURE_BASE)
    curr = extract_fingerprint(FIXTURE_BASE.replace(
        "Next earnings  : 2026-08-06\n    Reminder       : not_due",
        "Next earnings  : 2026-08-06\n    Reminder       : DUE",
    ))
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result
    assert "LLY earnings due" in subject
    assert "LLY EARNINGS due" in body


def test_earnings_reminder_does_not_refire_while_still_due():
    # Both prev and curr already "DUE" -- no transition, no new message.
    due = FIXTURE_BASE.replace(
        "Next earnings  : 2026-09-03\n    Reminder       : not_due",
        "Next earnings  : 2026-09-03\n    Reminder       : DUE",
    )
    fp = extract_fingerprint(due)
    assert build_actionable_message(fp, fp) is None


def test_avgo_new_quarter_fires_with_revenue_and_eps_prechecks():
    prev = extract_fingerprint(FIXTURE_BASE)
    curr = extract_fingerprint(FIXTURE_BASE.replace(
        "Latest quarter : 2026-04-30\n    Beat streak    : 4\n    Guidance trend : revising up",
        "Latest quarter : 2026-07-30\n    Beat streak    : 5\n    Guidance trend : revising up",
    ))
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result
    assert "AVGO earnings reported" in subject
    assert "AVGO EARNINGS JUST REPORTED" in body
    assert "EPS: $2.44 vs $2.40" in body
    assert "EPS beat streak: 5" in body
    assert "Revenue: $14.92B" in body
    assert "Next-qtr consensus: $16.10B" in body
    # No vague "go check X" deflection and no hardcoded guidance figure --
    # both dropped per explicit feedback (2026-07-06).
    assert "MANUAL REVIEW" not in body
    assert "$56B" not in body


def test_lly_new_quarter_fires():
    prev = extract_fingerprint(FIXTURE_BASE)
    curr = extract_fingerprint(FIXTURE_BASE.replace(
        "Latest quarter : 2026-03-31\n    Beat streak    : 4",
        "Latest quarter : 2026-06-30\n    Beat streak    : 5",
    ))
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result
    assert "LLY earnings reported" in subject
    assert "LLY EARNINGS JUST REPORTED" in body
    assert "EPS: $8.55 vs $6.79" in body


def test_new_quarter_does_not_fire_when_unchanged():
    fp = extract_fingerprint(FIXTURE_BASE)
    assert build_actionable_message(fp, fp) is None


def _run_cli(prev_text: str, curr_text: str, tmp_path: Path) -> str:
    prev = tmp_path / "prev.md"
    curr = tmp_path / "curr.md"
    prev.write_text(prev_text, encoding="utf-8")
    curr.write_text(curr_text, encoding="utf-8")
    script = Path(__file__).parent.parent / "check_signal_changes.py"
    result = subprocess.run(
        [sys.executable, str(script), str(prev), str(curr)],
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def test_cli_no_output_when_unchanged(tmp_path):
    assert _run_cli(FIXTURE_BASE, FIXTURE_BASE, tmp_path) == ""


def test_cli_reports_actionable_change(tmp_path):
    out = _run_cli(FIXTURE_BASE, FIXTURE_GAP_DOWN_FIRED, tmp_path)
    assert "ACTION:" in out
    assert "gap-down tranche" in out


def test_extract_fingerprint_parses_sleeve_candidate_none():
    fp = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_NO_CANDIDATE)
    assert fp["sleeve_candidate"] == "none"
    assert fp["sleeve_basket_candidate"] == "none"


def test_extract_fingerprint_parses_sleeve_candidate_ticker():
    fp = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_WITH_CANDIDATE)
    assert fp["sleeve_candidate"] == "HWM"
    assert fp["sleeve_plan"] == "buy near $275.43, hold ~21d, stop = MA50-5% then trails 3% once +5% gain"
    assert fp["sleeve_open_cmd"] == "run_entry_screen.py --open HWM <fill_price> <shares> <capital_sek>"


def test_extract_fingerprint_parses_basket_candidate_ticker():
    fp = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_WITH_BASKET_CANDIDATE)
    assert fp["sleeve_candidate"] == "none"
    assert fp["sleeve_basket_candidate"] == "EME"
    # basket-crash's own scoped fields, not the extension's -- these are
    # separate now that both can appear together (see MEMORY.md
    # "Basket-crash visibility decoupled from extension-gate priority").
    assert "flat 21d exit" in fp["sleeve_basket_plan"]
    assert "--entry-type basket_crash" in fp["sleeve_basket_open_cmd"]
    assert fp["sleeve_plan"] == "unknown"
    assert fp["sleeve_open_cmd"] == "unknown"


def test_sleeve_candidate_fires_when_new_enter_appears_while_closed():
    # The alert must be self-contained (Plan + Open quoted verbatim) rather
    # than telling the user to go run the screen -- see MEMORY.md "Sleeve
    # alert clarity", 2026-07-30.
    prev = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_NO_CANDIDATE)
    curr = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_WITH_CANDIDATE)
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result
    assert "Sleeve candidate -> HWM" in subject
    assert "OPPORTUNISTIC SLEEVE CANDIDATE: HWM is now ENTER-eligible" in body
    assert "Plan: buy near $275.43, hold ~21d, stop = MA50-5% then trails 3% once +5% gain" in body
    assert "Open: run_entry_screen.py --open HWM <fill_price> <shares> <capital_sek>" in body


def test_sleeve_candidate_does_not_fire_when_still_none():
    fp = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_NO_CANDIDATE)
    assert build_actionable_message(fp, fp) is None


def test_sleeve_candidate_does_not_fire_when_ticker_unchanged():
    fp = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_WITH_CANDIDATE)
    assert build_actionable_message(fp, fp) is None


def test_sleeve_candidate_does_not_double_fire_alongside_status_change():
    # The day the sleeve actually opens, sleeve_status already alerts --
    # the candidate-appearance check must stay silent on its own (both
    # sides must be CLOSED for it to fire).
    prev = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_WITH_CANDIDATE)
    curr = extract_fingerprint(FIXTURE_SLEEVE_OPEN_CLEAN)
    result = build_actionable_message(prev, curr)
    assert result is not None
    _, body = result
    assert "OPPORTUNISTIC SLEEVE CANDIDATE" not in body
    assert "OPPORTUNISTIC SLEEVE:" in body  # the real status-change alert still fires


def test_basket_candidate_fires_when_it_appears_while_closed():
    prev = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_NO_CANDIDATE)
    curr = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_WITH_BASKET_CANDIDATE)
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result
    assert "Sleeve basket-crash candidate -> EME" in subject
    assert "OPPORTUNISTIC SLEEVE BASKET-CRASH CANDIDATE: EME is now eligible" in body
    assert "secondary pathway" in body
    assert "Plan: buy near $650.12, flat 21d exit, NO stop until +8% gain" in body
    assert "Open: run_entry_screen.py --open EME <fill_price> <shares> <capital_sek> --entry-type basket_crash" in body


def test_basket_candidate_does_not_fire_when_still_none():
    fp = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_NO_CANDIDATE)
    assert build_actionable_message(fp, fp) is None


def test_basket_candidate_does_not_fire_when_ticker_unchanged():
    fp = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_WITH_BASKET_CANDIDATE)
    assert build_actionable_message(fp, fp) is None


def test_basket_candidate_and_extension_candidate_are_independent():
    # Extension candidate appearing alone must not also claim a basket-crash
    # alert fired -- separate fields, separate blocks.
    prev = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_NO_CANDIDATE)
    curr = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_WITH_CANDIDATE)
    result = build_actionable_message(prev, curr)
    assert result is not None
    _, body = result
    assert "BASKET-CRASH CANDIDATE" not in body


def test_both_candidates_can_appear_together_with_correctly_scoped_plan_open():
    # Since 2026-07-30, basket-crash visibility is no longer suppressed just
    # because extension also has a pick -- both can be real on the same day.
    # Each alert must quote its OWN Plan/Open, not the other candidate's.
    fp = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_WITH_BOTH_CANDIDATES)
    assert fp["sleeve_candidate"] == "HWM"
    assert fp["sleeve_basket_candidate"] == "EME"
    assert "hold ~21d" in fp["sleeve_plan"]
    assert "--open HWM" in fp["sleeve_open_cmd"]
    assert "flat 21d exit" in fp["sleeve_basket_plan"]
    assert "--open EME" in fp["sleeve_basket_open_cmd"]
    assert "EME" not in fp["sleeve_plan"] and "EME" not in fp["sleeve_open_cmd"]
    assert "HWM" not in fp["sleeve_basket_plan"] and "HWM" not in fp["sleeve_basket_open_cmd"]


def test_both_candidates_fire_both_alerts_with_correct_content():
    prev = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_NO_CANDIDATE)
    curr = extract_fingerprint(FIXTURE_SLEEVE_CLOSED_WITH_BOTH_CANDIDATES)
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result
    assert "Sleeve candidate -> HWM" in subject
    assert "Sleeve basket-crash candidate -> EME" in subject
    assert "OPPORTUNISTIC SLEEVE CANDIDATE: HWM is now ENTER-eligible" in body
    assert "OPPORTUNISTIC SLEEVE BASKET-CRASH CANDIDATE: EME is now eligible" in body
    assert "Plan: buy near $275.43, hold ~21d" in body
    assert "Open: run_entry_screen.py --open HWM <fill_price> <shares> <capital_sek>" in body
    assert "Plan: buy near $650.12, flat 21d exit" in body
    assert "Open: run_entry_screen.py --open EME <fill_price> <shares> <capital_sek> --entry-type basket_crash" in body


def test_cli_no_crash_when_prev_file_missing(tmp_path):
    curr = tmp_path / "curr.md"
    curr.write_text(FIXTURE_BASE, encoding="utf-8")
    script = Path(__file__).parent.parent / "check_signal_changes.py"
    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path / "does_not_exist.md"), str(curr)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_avgo_trigger_regex_not_captured_by_an_earlier_trigger_word():
    """Regression, 2026-08-16. The avgo_trigger regex is non-greedy from the
    section header, so the FIRST 'trigger:' inside the block wins. A wording
    change that put 'gap-down buy trigger: -10%' on the ROC line silently made
    avgo_trigger parse as '-10%' instead of the real trigger, which in turn
    made the gap-down alert unreachable. Caught only by running the real
    dashboard -- the fixtures at the time still carried the old wording.

    Any line above 'Signal :' in this block must therefore avoid the literal
    'trigger:'. This pins that."""
    hostile = FIXTURE_BASE.replace(
        "5d ROC         : -0.6%  (gap-down buy level: -10%)",
        "5d ROC         : -0.6%  (gap-down buy trigger: -10%)",
    )
    assert extract_fingerprint(hostile)["avgo_trigger"] == "-10%", (
        "fixture no longer reproduces the hazard -- rewrite this test"
    )
    # The real format must not hit it.
    assert extract_fingerprint(FIXTURE_BASE)["avgo_trigger"] == "none"


def test_live_dashboard_labels_are_parseable():
    """The section header and the 'Signal :' label are a parsing contract
    between fi_tracker.py and this module. Renaming either silently degrades
    every AVGO field to 'unknown' -- which is how the retirement change broke
    the gap-down alert before it was caught."""
    fp = extract_fingerprint(FIXTURE_BASE)
    for key in ("avgo_guard", "avgo_trigger", "avgo_action"):
        assert fp[key] != "unknown", f"{key} did not parse -- label contract broken"


def test_extract_fingerprint_parses_rebalance_check_fields():
    fp = extract_fingerprint(FIXTURE_BASE)
    assert fp["rebal_gold_status"] == "HOLD"
    assert fp["rebal_avgo_status"] == "HOLD"
    assert fp["rebal_lly_status"] == "HOLD"
    assert fp["rebal_avgo_detail"] == "(35.0% actual vs 33.5% target, gap -1.5%)"


def test_rebalance_hold_to_sell_fires_with_action():
    prev = extract_fingerprint(FIXTURE_BASE)
    curr = extract_fingerprint(FIXTURE_REBAL_AVGO_SELL)
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result
    assert "AVGO rebalance" in subject
    assert "ACTION:" in body
    assert "~29 shares" in body


def test_rebalance_hold_to_buy_fires_with_action():
    prev = extract_fingerprint(FIXTURE_BASE)
    curr = extract_fingerprint(FIXTURE_REBAL_LLY_BUY)
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result
    assert "LLY rebalance" in subject
    assert "~12 shares" in body


def test_rebalance_still_out_of_band_does_not_refire():
    """Persisting in SELL/BUY (not a fresh transition from HOLD) must stay
    silent -- same 'alert on transition, not on persisting state' rule as
    every other block."""
    curr = extract_fingerprint(FIXTURE_REBAL_AVGO_SELL)
    assert build_actionable_message(curr, curr) is None


def test_rebalance_resolving_back_to_hold_is_silent():
    """The gap closing (SELL/BUY -> HOLD) isn't actionable, same as the
    earnings-reminder DUE -> not_due direction."""
    prev = extract_fingerprint(FIXTURE_REBAL_AVGO_SELL)
    curr = extract_fingerprint(FIXTURE_BASE)
    assert build_actionable_message(prev, curr) is None


def test_rebalance_snapshot_lists_only_out_of_band_assets():
    from check_signal_changes import build_rebalance_snapshot_message

    text = FIXTURE_BASE.replace(
        "    AVGO status: HOLD  (35.0% actual vs 33.5% target, gap -1.5%)",
        "    AVGO status: SELL  (46.8% actual vs 33.5% target, gap -13.3%) -- ~29 shares (~107,382 kr)",
    ).replace(
        "    LLY status: HOLD  (37.3% actual vs 38.8% target, gap +1.5%)",
        "    LLY status: BUY  (22.3% actual vs 38.8% target, gap +16.5%) -- ~12 shares (~133,499 kr)",
    )
    result = build_rebalance_snapshot_message(text)
    assert result is not None
    subject, body = result
    assert "AVGO" in body and "SELL" in body and "~29 shares" in body
    assert "LLY" in body and "BUY" in body and "~12 shares" in body
    # Gold stayed HOLD -- must not appear as an actionable block.
    assert "Gold is out of band" not in body


def test_rebalance_snapshot_none_when_everything_in_band():
    from check_signal_changes import build_rebalance_snapshot_message

    assert build_rebalance_snapshot_message(FIXTURE_BASE) is None


# ── Crypto trend sleeve ────────────────────────────────────────────────────

CRYPTO_BLOCK = """
  Crypto Trend Sleeve
    Bitcoin (BTC-USD)  $81,027  (as of 2026-09-04)
      Target       : {btc}  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $67,275, flat below $65,929)
      Last change  : 2026-08-21 -> 100%
    Ethereum (ETH-USD)  $4,120  (as of 2026-09-04)
      Target       : {eth}  = 27 225 kr of 27 225 kr
      MA50         : LONG (MA $3,400, flat below $3,332)
      Last change  : 2026-08-19 -> 100%
"""


def _crypto(btc: str, eth: str) -> str:
    return FIXTURE_BASE + CRYPTO_BLOCK.format(btc=btc, eth=eth)


def test_crypto_fingerprint_reads_each_asset_separately():
    fp = extract_fingerprint(_crypto("100%", "67%"))
    assert fp["crypto_btc_exposure"] == "100%"
    assert fp["crypto_eth_exposure"] == "67%"
    assert "27 225 kr" in fp["crypto_btc_target"]


def test_crypto_tier_change_alerts_with_the_kr_amount_from_status_md():
    prev = extract_fingerprint(_crypto("100%", "100%"))
    curr = extract_fingerprint(_crypto("67%", "100%"))
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result
    assert "BTC sleeve -> 67%" in subject
    assert "CRYPTO TREND SLEEVE -- BTC: 100% -> 67%" in body
    assert "Virtune BTC" in body
    assert "27 225 kr" in body          # quoted from status.md, not restated
    assert "ETH" not in subject         # unchanged leg stays silent


def test_crypto_both_legs_can_alert_independently():
    prev = extract_fingerprint(_crypto("100%", "100%"))
    curr = extract_fingerprint(_crypto("33%", "0%"))
    subject, body = build_actionable_message(prev, curr)
    assert "BTC sleeve -> 33%" in subject and "ETH sleeve -> 0%" in subject


def test_crypto_unchanged_is_silent():
    fp = extract_fingerprint(_crypto("100%", "100%"))
    assert build_actionable_message(fp, fp) is None


def test_crypto_missing_section_does_not_alert():
    """A status.md written before the sleeve existed must not read as a
    change -- 'unknown' on either side is not actionable."""
    prev = extract_fingerprint(FIXTURE_BASE)
    curr = extract_fingerprint(_crypto("100%", "100%"))
    result = build_actionable_message(prev, curr)
    assert result is None or "sleeve ->" not in result[0]
