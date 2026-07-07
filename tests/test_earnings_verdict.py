import datetime as dt

import pytest

from earnings_verdict import format_verdict_line, load_verdicts, save_verdict


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "earnings_verdicts.toml"
    save_verdict("AVGO", "CLEARED", "AI revenue on pace, Anthropic on schedule.",
                 date=dt.date(2026, 9, 3), path=path)

    verdicts = load_verdicts(path)
    assert verdicts["AVGO"]["verdict"] == "CLEARED"
    assert verdicts["AVGO"]["date"] == "2026-09-03"
    assert verdicts["AVGO"]["reasoning"] == "AI revenue on pace, Anthropic on schedule."


def test_load_missing_file_returns_empty_dict(tmp_path):
    assert load_verdicts(tmp_path / "does_not_exist.toml") == {}


def test_save_rejects_invalid_verdict(tmp_path):
    with pytest.raises(ValueError):
        save_verdict("AVGO", "MAYBE", "unclear", path=tmp_path / "v.toml")


def test_second_ticker_does_not_clobber_first(tmp_path):
    path = tmp_path / "earnings_verdicts.toml"
    save_verdict("AVGO", "CLEARED", "AVGO reasoning", date=dt.date(2026, 9, 3), path=path)
    save_verdict("LLY", "NOT_CLEARED", "LLY reasoning", date=dt.date(2026, 8, 5), path=path)

    verdicts = load_verdicts(path)
    assert verdicts["AVGO"]["verdict"] == "CLEARED"
    assert verdicts["LLY"]["verdict"] == "NOT_CLEARED"


def test_re_recording_same_ticker_overwrites_not_duplicates(tmp_path):
    path = tmp_path / "earnings_verdicts.toml"
    save_verdict("AVGO", "NOT_CLEARED", "first read", date=dt.date(2026, 9, 3), path=path)
    save_verdict("AVGO", "CLEARED", "corrected after re-reading", date=dt.date(2026, 9, 4), path=path)

    verdicts = load_verdicts(path)
    assert len(verdicts) == 1
    assert verdicts["AVGO"]["verdict"] == "CLEARED"
    assert verdicts["AVGO"]["reasoning"] == "corrected after re-reading"


def test_reasoning_with_quotes_and_backslashes_survives_roundtrip(tmp_path):
    path = tmp_path / "earnings_verdicts.toml"
    tricky = 'management said "on track" -- path\\to\\nowhere'
    save_verdict("AVGO", "CLEARED", tricky, path=path)

    verdicts = load_verdicts(path)
    assert verdicts["AVGO"]["reasoning"] == tricky


def test_format_verdict_line_present():
    verdicts = {"AVGO": {"verdict": "CLEARED", "date": "2026-09-03", "reasoning": "on pace"}}
    assert format_verdict_line("AVGO", verdicts) == "CLEARED  (2026-09-03) -- on pace"


def test_format_verdict_line_absent_is_none():
    assert format_verdict_line("AVGO", {}) is None
