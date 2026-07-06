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
    Next earnings  : 2026-09-03
    Reminder       : not_due

  LLY Earnings Checkpoint
    Next earnings  : 2026-08-06
    Reminder       : not_due

  Regime check (2026-06-30): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
"""

FIXTURE_GUARD_FIRED = FIXTURE_BASE.replace(
    "Signal         : BASE  (trigger: none)", "Signal         : DEFENSIVE  (trigger: CRASH)"
).replace(
    "Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)",
    "Action         : Rotate AVGO -> Gold+LLY (Gold 52.5%, AVGO 0%, LLY 47.5%)",
)

FIXTURE_REGIME_FLIP = FIXTURE_BASE + "\n  REGIME CHANGE ALERT -- 2026-07-05\n"


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
        "AVGO Earnings Checkpoint\n    Next earnings  : 2026-09-03\n    Reminder       : not_due",
        "AVGO Earnings Checkpoint\n    Next earnings  : 2026-09-03\n    Reminder       : DUE",
    ))
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result
    assert "AVGO earnings due" in subject
    assert "AVGO EARNINGS due" in body


def test_lly_earnings_reminder_fires_once_on_transition():
    prev = extract_fingerprint(FIXTURE_BASE)
    curr = extract_fingerprint(FIXTURE_BASE.replace(
        "LLY Earnings Checkpoint\n    Next earnings  : 2026-08-06\n    Reminder       : not_due",
        "LLY Earnings Checkpoint\n    Next earnings  : 2026-08-06\n    Reminder       : DUE",
    ))
    result = build_actionable_message(prev, curr)
    assert result is not None
    subject, body = result
    assert "LLY earnings due" in subject
    assert "LLY EARNINGS due" in body


def test_earnings_reminder_does_not_refire_while_still_due():
    # Both prev and curr already "DUE" -- no transition, no new message.
    due = FIXTURE_BASE.replace(
        "AVGO Earnings Checkpoint\n    Next earnings  : 2026-09-03\n    Reminder       : not_due",
        "AVGO Earnings Checkpoint\n    Next earnings  : 2026-09-03\n    Reminder       : DUE",
    )
    fp = extract_fingerprint(due)
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
