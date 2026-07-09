import datetime as dt

from asset_universe import update as update_mod


def test_yf_fetch_end_is_one_day_past_today(monkeypatch, tmp_path):
    """yfinance's `end` is exclusive (unlike FRED's `observation_end`), so
    fetching with end=today silently drops today's own close even when the
    job runs after market close. Regression for the real one-trading-day
    lag found 2026-07-09: the pipeline must fetch with end=tomorrow so
    today's bar is actually included."""

    fixed_today = dt.date(2026, 7, 8)

    class FixedDate(dt.date):
        @classmethod
        def today(cls):
            return fixed_today

    monkeypatch.setattr(update_mod, "date", FixedDate)

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

    assert captured["end"] == "2026-07-09"  # today + 1 day, not today itself
    assert captured["end"] != fixed_today.isoformat()
