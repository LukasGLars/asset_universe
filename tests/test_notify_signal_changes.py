from unittest.mock import patch

import notify_signal_changes as nsc

BASE = """
  AVGO 200d Guard
    Signal         : BASE  (trigger: none)
    LLY stress     : inactive
    Joint stress   : inactive
    Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)

  Silver GSR Tactical
    Signal         : INACTIVE
    Action         : No action -- hold base

  Opportunistic Sleeve
    Status         : CLOSED

  Regime check (2026-06-30): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
"""

CHANGED = BASE.replace(
    "Signal         : BASE  (trigger: none)", "Signal         : DEFENSIVE  (trigger: CRASH)"
).replace(
    "Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)",
    "Action         : Rotate AVGO -> Gold+LLY (Gold 52.5%, AVGO 0%, LLY 47.5%)",
)


def test_build_change_email_none_when_unchanged(tmp_path):
    prev = tmp_path / "prev.md"
    curr = tmp_path / "curr.md"
    prev.write_text(BASE, encoding="utf-8")
    curr.write_text(BASE, encoding="utf-8")
    assert nsc.build_change_email(str(prev), str(curr)) is None


def test_build_change_email_leads_with_action(tmp_path):
    prev = tmp_path / "prev.md"
    curr = tmp_path / "curr.md"
    prev.write_text(BASE, encoding="utf-8")
    curr.write_text(CHANGED, encoding="utf-8")
    result = nsc.build_change_email(str(prev), str(curr))
    assert result is not None
    subject, body = result
    assert "AVGO guard" in subject
    assert "ACTION: Rotate AVGO -> Gold+LLY" in body


def test_build_change_email_none_when_prev_missing(tmp_path):
    curr = tmp_path / "curr.md"
    curr.write_text(BASE, encoding="utf-8")
    assert nsc.build_change_email(str(tmp_path / "nope.md"), str(curr)) is None


def test_main_does_not_send_email_when_unchanged(tmp_path):
    prev = tmp_path / "prev.md"
    curr = tmp_path / "curr.md"
    prev.write_text(BASE, encoding="utf-8")
    curr.write_text(BASE, encoding="utf-8")

    with patch.object(nsc, "send_email") as mock_send:
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", str(prev), str(curr)]
        try:
            nsc.main()
        finally:
            sys.argv = old_argv
        mock_send.assert_not_called()


def test_main_sends_email_with_action_when_changed():
    with patch.object(nsc, "build_change_email",
                       return_value=("Asset Universe: AVGO guard -> DEFENSIVE",
                                     "AVGO GUARD: BASE -> DEFENSIVE\nACTION: Rotate AVGO -> Gold+LLY")), \
         patch.object(nsc, "send_email") as mock_send:
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", "a.md", "b.md"]
        try:
            nsc.main()
        finally:
            sys.argv = old_argv
        mock_send.assert_called_once()
        subject, body = mock_send.call_args[0]
        assert "AVGO guard" in subject
        assert "ACTION:" in body


def test_main_force_test_email_bypasses_diff_and_sends(monkeypatch):
    monkeypatch.setenv("FORCE_TEST_EMAIL", "true")
    with patch.object(nsc, "build_change_email") as mock_email, \
         patch.object(nsc, "send_email") as mock_send:
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", "a.md", "b.md"]
        try:
            nsc.main()
        finally:
            sys.argv = old_argv
        mock_email.assert_not_called()  # diff is bypassed entirely
        mock_send.assert_called_once()
        assert "test email" in mock_send.call_args[0][0].lower()


def test_main_does_not_raise_when_send_email_fails():
    with patch.object(nsc, "build_change_email",
                       return_value=("Asset Universe: AVGO guard -> DEFENSIVE", "ACTION: Rotate AVGO")), \
         patch.object(nsc, "send_email", side_effect=RuntimeError("smtp auth failed")):
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", "a.md", "b.md"]
        try:
            nsc.main()  # must not raise
        finally:
            sys.argv = old_argv
