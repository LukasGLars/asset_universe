# -*- coding: utf-8 -*-
"""The alert that fires when the daily sync dies.

The two failure cases need opposite advice, and getting them the wrong way
round is worse than sending nothing: telling the operator a signal "will be
reported later" when it has actually been lost is the exact class of mistake
CLAUDE.md's first rule is about.
"""
import importlib
import os

import notify_sync_failure


def _build(tmp_path, monkeypatch, committed: bool):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_WORKFLOW", "daily-sync")
    monkeypatch.setenv("GITHUB_REPOSITORY", "LukasGLars/asset_universe")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    if committed:
        (tmp_path / notify_sync_failure.COMMIT_MARKER).write_text("")
    return notify_sync_failure.build_message()


def test_failure_before_commit_promises_the_signal_is_only_delayed(tmp_path, monkeypatch):
    subject, body = _build(tmp_path, monkeypatch, committed=False)
    assert "FAILED" in subject and "after commit" not in subject
    assert "not lost" in body
    assert "will NOT be reported" not in body


def test_failure_after_commit_says_the_signal_is_gone(tmp_path, monkeypatch):
    """status.md was pushed, so the next run diffs against THIS commit and a
    change in this run is never reported. It must not promise otherwise."""
    subject, body = _build(tmp_path, monkeypatch, committed=True)
    assert "after commit" in subject
    assert "will NOT be reported" in body
    assert "not lost" not in body


def test_the_run_log_is_always_linked(tmp_path, monkeypatch):
    _, body = _build(tmp_path, monkeypatch, committed=False)
    assert "actions/runs/123" in body


def test_no_portfolio_numbers_are_quoted(tmp_path, monkeypatch):
    """This alert runs when the source is untrustworthy or absent, so it must
    describe the outage and nothing else."""
    _, body = _build(tmp_path, monkeypatch, committed=False)
    for token in ("%", "kr", "SEK", "$"):
        assert token not in body, f"{token!r} suggests a restated figure"


def test_a_dead_telegram_does_not_mask_the_real_failure(tmp_path, monkeypatch):
    """The workflow is already red; a notification error must not replace the
    reason it went red."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(notify_sync_failure, "send_with_retry_and_fallback",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("telegram down")))
    assert notify_sync_failure.main() == 0
