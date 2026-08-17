from unittest.mock import patch

import notify_signal_changes as nsc

BASE = """
  AVGO Trend Diagnostic
    Signal         : BASE  (trigger: none)  -- informational, no rotation
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

# Guard retired as a rotation rule 2026-08-16 (PR #88); the CRASH leg
# survives as the gap-down BUY trigger, which is what still alerts.
CHANGED = BASE.replace(
    "Signal         : BASE  (trigger: none)  -- informational, no rotation", "Signal         : DEFENSIVE  (trigger: CRASH)  -- informational, no rotation"
).replace(
    "Action         : Hold base (Gold 25%, AVGO 55%, LLY 20%)",
    "Action         : No rotation. But the 5d/-10% gap-down trigger has fired: "
    "if the gap-down tranche (50k into AVGO) hasn't been deployed yet, this is "
    "that signal -- see MEMORY.md 'Gap-down tranche validated'.",
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
    assert "gap-down" in subject.lower()
    assert "ACTION:" in body
    assert "gap-down tranche" in body
    assert "Rotate AVGO" not in body


def test_build_change_email_none_when_prev_missing(tmp_path):
    curr = tmp_path / "curr.md"
    curr.write_text(BASE, encoding="utf-8")
    assert nsc.build_change_email(str(tmp_path / "nope.md"), str(curr)) is None


def test_main_does_not_send_when_unchanged(tmp_path):
    prev = tmp_path / "prev.md"
    curr = tmp_path / "curr.md"
    prev.write_text(BASE, encoding="utf-8")
    curr.write_text(BASE, encoding="utf-8")

    with patch.object(nsc, "send_telegram") as mock_send:
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", str(prev), str(curr)]
        try:
            code = nsc.main()
        finally:
            sys.argv = old_argv
        mock_send.assert_not_called()
        assert code == 0


def test_main_sends_telegram_with_action_when_changed():
    with patch.object(nsc, "build_change_email",
                       return_value=("Asset Universe: AVGO gap-down trigger",
                                     "AVGO GAP-DOWN TRIGGER: 5d ROC breached -10%\n"
                                     "ACTION: deploy the gap-down tranche")), \
         patch.object(nsc, "send_telegram") as mock_send:
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", "a.md", "b.md"]
        try:
            code = nsc.main()
        finally:
            sys.argv = old_argv
        mock_send.assert_called_once()
        subject, body = mock_send.call_args[0]
        assert "gap-down" in subject.lower()
        assert "ACTION:" in body
        assert code == 0


def test_main_force_test_telegram_bypasses_diff_and_sends(monkeypatch):
    monkeypatch.setenv("FORCE_TEST_TELEGRAM", "true")
    with patch.object(nsc, "build_change_email") as mock_email, \
         patch.object(nsc, "send_telegram") as mock_send:
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", "a.md", "b.md"]
        try:
            code = nsc.main()
        finally:
            sys.argv = old_argv
        mock_email.assert_not_called()  # diff is bypassed entirely
        mock_send.assert_called_once()
        assert "test message" in mock_send.call_args[0][0].lower()
        assert code == 0


def test_main_diagnostic_send_failure_does_not_escalate(monkeypatch):
    # The manual FORCE_TEST_TELEGRAM diagnostic isn't a real actionable
    # event -- its own send failure should stay non-fatal, unlike a real
    # signal change's send failure below.
    monkeypatch.setenv("FORCE_TEST_TELEGRAM", "true")
    with patch.object(nsc, "send_telegram", side_effect=RuntimeError("telegram api error")):
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", "a.md", "b.md"]
        try:
            code = nsc.main()
        finally:
            sys.argv = old_argv
        assert code == 0


def test_main_does_not_raise_but_escalates_when_all_channels_fail(monkeypatch):
    # A failed Telegram send (all retries) AND a failed email fallback for a
    # REAL actionable change must fail the job (non-zero exit) so GitHub's
    # failure-run email is a third, independent channel -- previously this
    # was silent-only, so a broken delivery for a genuine guard flip would
    # never reach anyone.
    monkeypatch.delenv("EMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("EMAIL_PASSWORD", raising=False)
    with patch.object(nsc, "build_change_email",
                       return_value=("Asset Universe: AVGO gap-down trigger", "ACTION: deploy the gap-down tranche")), \
         patch.object(nsc, "send_telegram", side_effect=RuntimeError("telegram api error")), \
         patch.object(nsc.time, "sleep"):
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", "a.md", "b.md"]
        try:
            code = nsc.main()  # must not raise, but must signal failure
        finally:
            sys.argv = old_argv
        assert code == 1


def test_send_with_retry_succeeds_on_second_attempt():
    # First Telegram attempt fails, second succeeds -- no email fallback
    # needed, and the retry itself is invisible to the caller.
    with patch.object(nsc, "send_telegram", side_effect=[RuntimeError("transient"), None]) as mock_send, \
         patch.object(nsc.time, "sleep") as mock_sleep:
        nsc.send_with_retry_and_fallback("subject", "body")
        assert mock_send.call_count == 2
        mock_sleep.assert_called_once()


def test_send_with_retry_falls_back_to_email_when_telegram_exhausted(monkeypatch):
    monkeypatch.setenv("EMAIL_ADDRESS", "me@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "app-password")
    with patch.object(nsc, "send_telegram", side_effect=RuntimeError("telegram down")), \
         patch.object(nsc, "send_email_fallback") as mock_email, \
         patch.object(nsc.time, "sleep"):
        nsc.send_with_retry_and_fallback("subject", "body")  # must not raise
        mock_email.assert_called_once_with("subject", "body")


def test_send_with_retry_raises_when_both_channels_fail():
    with patch.object(nsc, "send_telegram", side_effect=RuntimeError("telegram down")), \
         patch.object(nsc, "send_email_fallback", side_effect=RuntimeError("smtp auth failed")), \
         patch.object(nsc.time, "sleep"):
        try:
            nsc.send_with_retry_and_fallback("subject", "body")
            assert False, "expected RuntimeError"
        except RuntimeError as e:
            assert "telegram down" in str(e)
            assert "smtp auth failed" in str(e)


def test_main_suppress_notify_skips_even_a_real_change(monkeypatch):
    # 2026-07-07: deploying a state-file correction (e.g. the HWM sleeve-
    # state backfill) must not fire a phantom "real event" alert -- this
    # flag is the escape hatch, checked before the diff even runs.
    monkeypatch.setenv("SUPPRESS_NOTIFY", "true")
    with patch.object(nsc, "build_change_email",
                       return_value=("Asset Universe: Sleeve -> OPEN", "REVIEW: ...")) as mock_diff, \
         patch.object(nsc, "send_with_retry_and_fallback") as mock_send:
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", "a.md", "b.md"]
        try:
            code = nsc.main()
        finally:
            sys.argv = old_argv
        mock_diff.assert_not_called()
        mock_send.assert_not_called()
        assert code == 0


def test_send_telegram_raises_on_not_ok_response(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return b'{"ok": false, "description": "chat not found"}'

    with patch("notify_signal_changes.urllib.request.urlopen", return_value=FakeResponse()):
        try:
            nsc.send_telegram("subject", "body")
            assert False, "expected RuntimeError"
        except RuntimeError as e:
            assert "not-ok" in str(e)


REBAL_OUT_OF_BAND = BASE + """
  AVGO Rebalance Check  [existing capital, band: 5%]
    Gold status: HOLD  (30.5% actual vs 27.7% target, gap -2.8%)
    AVGO status: SELL  (46.8% actual vs 33.5% target, gap -13.3%) -- ~29 shares (~107,382 kr)
    LLY status: BUY  (22.3% actual vs 38.8% target, gap +16.5%) -- ~12 shares (~133,499 kr)
"""

REBAL_ALL_HOLD = BASE + """
  AVGO Rebalance Check  [existing capital, band: 5%]
    Gold status: HOLD  (27.7% actual vs 27.7% target, gap +0.0%)
    AVGO status: HOLD  (33.5% actual vs 33.5% target, gap +0.0%)
    LLY status: HOLD  (38.8% actual vs 38.8% target, gap +0.0%)
"""


def test_force_send_rebalance_bypasses_diff_and_sends(monkeypatch, tmp_path):
    monkeypatch.setenv("FORCE_SEND_REBALANCE", "true")
    prev = tmp_path / "prev.md"  # deliberately stale/irrelevant -- must not be read for content
    curr = tmp_path / "curr.md"
    prev.write_text(BASE, encoding="utf-8")
    curr.write_text(REBAL_OUT_OF_BAND, encoding="utf-8")

    with patch.object(nsc, "build_change_email") as mock_email, \
         patch.object(nsc, "send_telegram") as mock_send:
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", str(prev), str(curr)]
        try:
            code = nsc.main()
        finally:
            sys.argv = old_argv
        mock_email.assert_not_called()  # diff path is bypassed entirely
        mock_send.assert_called_once()
        subject, body = mock_send.call_args[0]
        assert "AVGO" in body and "~29 shares" in body
        assert "LLY" in body and "~12 shares" in body
        assert code == 0


def test_force_send_rebalance_sends_nothing_when_all_in_band(monkeypatch, tmp_path):
    monkeypatch.setenv("FORCE_SEND_REBALANCE", "true")
    prev = tmp_path / "prev.md"
    curr = tmp_path / "curr.md"
    prev.write_text(BASE, encoding="utf-8")
    curr.write_text(REBAL_ALL_HOLD, encoding="utf-8")

    with patch.object(nsc, "send_telegram") as mock_send:
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", str(prev), str(curr)]
        try:
            code = nsc.main()
        finally:
            sys.argv = old_argv
        mock_send.assert_not_called()
        assert code == 0


def test_force_send_rebalance_missing_curr_file_fails_loudly(monkeypatch, tmp_path):
    monkeypatch.setenv("FORCE_SEND_REBALANCE", "true")
    prev = tmp_path / "prev.md"
    prev.write_text(BASE, encoding="utf-8")

    with patch.object(nsc, "send_telegram") as mock_send:
        import sys
        old_argv = sys.argv
        sys.argv = ["notify_signal_changes.py", str(prev), str(tmp_path / "nope.md")]
        try:
            code = nsc.main()
        finally:
            sys.argv = old_argv
        mock_send.assert_not_called()
        assert code == 1
