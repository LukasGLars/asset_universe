from unittest.mock import patch

import notify_signal_changes as nsc

BASE = """
  AVGO 200d Guard
    Signal         : BASE  (trigger: none)
    LLY stress     : inactive
    Joint stress   : inactive

  Silver GSR Tactical
    Signal         : INACTIVE

  Opportunistic Sleeve
    Status         : CLOSED

  Regime check (2026-06-30): RY=HIGH  BAA=TIGHT  -- no confirmed flip (window=3d)
"""

CHANGED = BASE.replace("Signal         : BASE  (trigger: none)",
                       "Signal         : DEFENSIVE  (trigger: CRASH)")


def test_build_change_summary_none_when_unchanged(tmp_path):
    prev = tmp_path / "prev.md"
    curr = tmp_path / "curr.md"
    prev.write_text(BASE, encoding="utf-8")
    curr.write_text(BASE, encoding="utf-8")
    assert nsc.build_change_summary(str(prev), str(curr)) is None


def test_build_change_summary_reports_guard_change(tmp_path):
    prev = tmp_path / "prev.md"
    curr = tmp_path / "curr.md"
    prev.write_text(BASE, encoding="utf-8")
    curr.write_text(CHANGED, encoding="utf-8")
    summary = nsc.build_change_summary(str(prev), str(curr))
    assert summary is not None
    assert "AVGO guard: BASE -> DEFENSIVE" in summary


def test_build_change_summary_none_when_prev_missing(tmp_path):
    curr = tmp_path / "curr.md"
    curr.write_text(BASE, encoding="utf-8")
    assert nsc.build_change_summary(str(tmp_path / "nope.md"), str(curr)) is None


def test_main_does_not_send_email_when_unchanged(tmp_path, capsys):
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


def test_main_sends_email_when_changed():
    with patch.object(nsc, "build_change_summary", return_value="AVGO guard: BASE -> DEFENSIVE"), \
         patch.object(nsc, "send_email") as mock_send:
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", "a.md", "b.md"]
        try:
            nsc.main()
        finally:
            sys.argv = old_argv
        mock_send.assert_called_once()
        args = mock_send.call_args[0]
        assert "signal change" in args[0].lower()
        assert "AVGO guard" in args[1]


def test_main_force_test_email_bypasses_diff_and_sends(monkeypatch):
    monkeypatch.setenv("FORCE_TEST_EMAIL", "true")
    with patch.object(nsc, "build_change_summary") as mock_summary, \
         patch.object(nsc, "send_email") as mock_send:
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", "a.md", "b.md"]
        try:
            nsc.main()
        finally:
            sys.argv = old_argv
        mock_summary.assert_not_called()  # diff is bypassed entirely
        mock_send.assert_called_once()
        assert "test email" in mock_send.call_args[0][0].lower()


def test_main_does_not_raise_when_send_email_fails():
    with patch.object(nsc, "build_change_summary", return_value="AVGO guard: BASE -> DEFENSIVE"), \
         patch.object(nsc, "send_email", side_effect=RuntimeError("smtp auth failed")):
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", "a.md", "b.md"]
        try:
            nsc.main()  # must not raise
        finally:
            sys.argv = old_argv
