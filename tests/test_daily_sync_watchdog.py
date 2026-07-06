import datetime as dt
import os
from unittest.mock import patch

import check_daily_sync_watchdog as watchdog

STATUS_TEXT = "anything -- content doesn't matter, only freshness does here\n"


def _write(path, text, mtime):
    path.write_text(text, encoding="utf-8")
    ts = mtime.timestamp()
    os.utime(path, (ts, ts))


def test_fresh_status_does_nothing(tmp_path):
    status_path = tmp_path / "status.md"
    now = dt.datetime(2026, 7, 6, 10, 0, tzinfo=dt.timezone.utc)
    _write(status_path, STATUS_TEXT, now - dt.timedelta(minutes=5))

    with patch.object(watchdog, "trigger_daily_sync") as mock_trigger, \
         patch.object(watchdog, "send_telegram") as mock_send:
        code = watchdog.run_watchdog(status_path, now)

    assert code == 0
    mock_trigger.assert_not_called()
    mock_send.assert_not_called()


def test_stale_status_self_heals_silently(tmp_path):
    status_path = tmp_path / "status.md"
    now = dt.datetime(2026, 7, 6, 10, 0, tzinfo=dt.timezone.utc)
    _write(status_path, STATUS_TEXT, now - dt.timedelta(days=4))

    with patch.object(watchdog, "trigger_daily_sync") as mock_trigger, \
         patch.object(watchdog, "send_telegram") as mock_send:
        code = watchdog.run_watchdog(status_path, now)

    assert code == 0
    mock_trigger.assert_called_once()
    mock_send.assert_not_called()  # self-heal worked -- not news


def test_stale_status_trigger_failure_sends_alert(tmp_path):
    status_path = tmp_path / "status.md"
    now = dt.datetime(2026, 7, 6, 10, 0, tzinfo=dt.timezone.utc)
    _write(status_path, STATUS_TEXT, now - dt.timedelta(days=4))

    with patch.object(watchdog, "trigger_daily_sync", side_effect=RuntimeError("dispatch 403")), \
         patch.object(watchdog, "send_telegram") as mock_send:
        code = watchdog.run_watchdog(status_path, now)

    assert code == 1
    mock_send.assert_called_once()
    subject, body = mock_send.call_args[0]
    assert "watchdog" in subject.lower()
    assert "dispatch 403" in body


def test_trigger_and_telegram_both_failing_does_not_raise(tmp_path):
    status_path = tmp_path / "status.md"
    now = dt.datetime(2026, 7, 6, 10, 0, tzinfo=dt.timezone.utc)
    _write(status_path, STATUS_TEXT, now - dt.timedelta(days=4))

    with patch.object(watchdog, "trigger_daily_sync", side_effect=RuntimeError("dispatch 403")), \
         patch.object(watchdog, "send_telegram", side_effect=RuntimeError("telegram down")):
        code = watchdog.run_watchdog(status_path, now)  # must not raise

    assert code == 1


def test_trigger_daily_sync_posts_to_correct_endpoint(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "LukasGLars/asset_universe")

    captured = {}

    class FakeResponse:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b""

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = req.data
        return FakeResponse()

    with patch("check_daily_sync_watchdog.urllib.request.urlopen", side_effect=fake_urlopen):
        watchdog.trigger_daily_sync()

    assert captured["url"] == (
        "https://api.github.com/repos/LukasGLars/asset_universe/actions/workflows/sync.yml/dispatches"
    )
    assert captured["method"] == "POST"
    assert b'"ref": "master"' in captured["body"]


def test_trigger_daily_sync_raises_on_unexpected_status(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "LukasGLars/asset_universe")

    class FakeResponse:
        status = 404

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b""

    with patch("check_daily_sync_watchdog.urllib.request.urlopen", return_value=FakeResponse()):
        try:
            watchdog.trigger_daily_sync()
            assert False, "expected RuntimeError"
        except RuntimeError as e:
            assert "404" in str(e)
