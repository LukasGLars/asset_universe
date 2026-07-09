import datetime as dt
from zoneinfo import ZoneInfo

from asset_universe import update as update_mod


class _FixedDateTime(dt.datetime):
    _fixed = None

    @classmethod
    def now(cls, tz=None):
        return cls._fixed if tz is None else cls._fixed.astimezone(tz)


def _freeze(monkeypatch, ny_dt: dt.datetime):
    frozen = _FixedDateTime
    frozen._fixed = ny_dt.astimezone(ZoneInfo("America/New_York"))
    monkeypatch.setattr(update_mod, "datetime", frozen)


def test_yf_fetch_end_after_market_close_includes_today(monkeypatch):
    """After NYSE close, end should be today+1 (yfinance's end is
    exclusive) so today's own close is actually fetched -- the real bug
    found 2026-07-09."""
    _freeze(monkeypatch, dt.datetime(2026, 7, 8, 20, 30, tzinfo=ZoneInfo("America/New_York")))
    assert update_mod._yf_fetch_end() == "2026-07-09"


def test_yf_fetch_end_before_market_close_stays_at_today(monkeypatch):
    """Mid-session (e.g. a manual workflow_dispatch or watchdog re-trigger
    firing during market hours) must NOT extend to tomorrow -- doing so
    would capture a live, not-yet-final intraday print as if it were a
    completed close, and _next_fetch_start would never revisit that date
    to correct it later."""
    _freeze(monkeypatch, dt.datetime(2026, 7, 8, 12, 0, tzinfo=ZoneInfo("America/New_York")))
    assert update_mod._yf_fetch_end() == "2026-07-08"


def test_yf_fetch_end_respects_dst_mismatch_in_winter(monkeypatch):
    """NYSE closes at 21:00 UTC in winter (EST) vs 20:00 UTC in summer
    (EDT). A fixed UTC cron offset (sync.yml fires at 20:37 UTC) would
    land BEFORE close in winter -- this must still resolve correctly
    because the check is done in NY local time, not UTC."""
    _freeze(monkeypatch, dt.datetime(2026, 1, 8, 15, 45, tzinfo=ZoneInfo("America/New_York")))
    assert update_mod._yf_fetch_end() == "2026-01-08"

    _freeze(monkeypatch, dt.datetime(2026, 1, 8, 16, 10, tzinfo=ZoneInfo("America/New_York")))
    assert update_mod._yf_fetch_end() == "2026-01-09"


def test_run_passes_yf_fetch_end_through_to_fetch(monkeypatch, tmp_path):
    """End-to-end: run() must use _yf_fetch_end() (not `today`) as the
    yfinance fetch window's end."""
    monkeypatch.setattr(update_mod, "_yf_fetch_end", lambda: "2026-07-09")

    monkeypatch.setattr(update_mod.config, "load_settings", lambda: {
        "data": {"start_date": "2020-01-01"},
        "fetch": {"yf_sleep_seconds": 0, "fred_sleep_seconds": 0},
    })
    monkeypatch.setattr(update_mod.config, "raw_data_dir", lambda: tmp_path)
    monkeypatch.setattr(update_mod.config, "load_universe",
                         lambda name: ["AVGO"] if name == "us_equities" else [])
    monkeypatch.setattr(update_mod.config, "fred_api_key", lambda: None)
    monkeypatch.setattr(update_mod.reader, "last_date", lambda path: "2026-07-06")

    captured = {}

    def fake_fetch(ticker, start, end):
        captured["start"] = start
        captured["end"] = end
        return None

    monkeypatch.setattr(update_mod.yf_dl, "fetch", fake_fetch)

    update_mod.run(dry=False)

    assert captured["end"] == "2026-07-09"
