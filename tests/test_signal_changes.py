import subprocess
import sys
from pathlib import Path

from check_signal_changes import build_actionable_message, extract_fingerprint

FIXTURE_BASE = """
  AVGO 200d Guard
    AVGO now       : $377.75  (as of 2026-06-30)
    200d SMA       : $360.14  (+4.9% gap)
    5d ROC         : -0.6%  (crash threshold: -10%)
    Signal         : BASE  (trigger: none)
    LLY stress     : inactive  ($1199.43 vs 200d SMA $978.00, 5d ROC +8.3%)
    Joint stress   : inactive  (guard AND LLY stress both active)
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
"""

FIXTURE_GUARD_FIRED = FIXTURE_BASE.replace(
    "Signal         : BASE  (trigger: none)", "Signal         : DEFENSIVE  (trigger: CRASH)"
).replace(
    "Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)",
    "Action         : Rotate AVGO -> Gold+LLY (Gold 52.5%, AVGO 0%, LLY 47.5%)",
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


def test_message_leads_with_action_not_just_state_change():
    prev = extract_fingerprint(FIXTURE_BASE)
    curr = extract_fingerprint(FIXTURE_GUARD_FIRED)
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result

    assert "AVGO guard -> DEFENSIVE" in subject
    assert "BASE -> DEFENSIVE" in body
    # The whole point: the exact instruction must be present, not just the
    # raw state transition.
    assert "ACTION: Rotate AVGO -> Gold+LLY (Gold 52.5%, AVGO 0%, LLY 47.5%)" in body


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


def test_lly_stress_alone_is_informational_not_actioned():
    prev = extract_fingerprint(FIXTURE_BASE)
    changed = FIXTURE_BASE.replace("LLY stress     : inactive", "LLY stress     : ACTIVE")
    curr = extract_fingerprint(changed)
    result = build_actionable_message(prev, curr)
    assert result is not None
    _, body = result
    assert "informational" in body.lower()
    assert "No action" in body


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
    out = _run_cli(FIXTURE_BASE, FIXTURE_GUARD_FIRED, tmp_path)
    assert "ACTION: Rotate AVGO" in out


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
