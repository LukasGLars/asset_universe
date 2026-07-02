import subprocess
import sys
from pathlib import Path

from check_signal_changes import extract_fingerprint

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

  Opportunistic Sleeve
    Status         : CLOSED (0/1 position)

  Regime check (2026-06-30): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
"""

FIXTURE_GUARD_FIRED = FIXTURE_BASE.replace(
    "Signal         : BASE  (trigger: none)", "Signal         : DEFENSIVE  (trigger: CRASH)"
)

FIXTURE_REGIME_FLIP = FIXTURE_BASE + "\n  REGIME CHANGE ALERT -- 2026-07-05\n"


def test_extract_fingerprint_parses_known_fields():
    fp = extract_fingerprint(FIXTURE_BASE)
    assert fp["avgo_guard"] == "BASE"
    assert fp["avgo_trigger"] == "none"
    assert fp["lly_stress"] == "inactive"
    assert fp["joint_stress"] == "inactive"
    assert fp["silver_signal"] == "INACTIVE"
    assert fp["sleeve_status"] == "CLOSED"
    assert fp["regime_flip"] == "stable"


def test_extract_fingerprint_detects_regime_flip():
    fp = extract_fingerprint(FIXTURE_REGIME_FLIP)
    assert fp["regime_flip"] == "FLIP"


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


def test_cli_reports_guard_change(tmp_path):
    out = _run_cli(FIXTURE_BASE, FIXTURE_GUARD_FIRED, tmp_path)
    assert "AVGO guard: BASE -> DEFENSIVE" in out
    assert "AVGO guard trigger: none -> CRASH" in out


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
