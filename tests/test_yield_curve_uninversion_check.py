import pandas as pd

import run_yield_curve_uninversion_check as yc


def test_find_sign_flips_detects_negative_to_positive_crossings_only():
    idx = pd.date_range("2022-01-01", periods=8, freq="D")
    # inverted, inverted, uninverts, stays positive, dips back negative, uninverts again
    s = pd.Series([-0.5, -0.3, 0.1, 0.4, -0.1, 0.2, 0.3, -0.05], index=idx)
    flips = yc.find_sign_flips(s)
    flip_dates = [d.date() for d, _, _ in flips]
    assert flip_dates == [idx[2].date(), idx[5].date()]


def test_main_reports_most_recent_uninversion_and_reinversion(monkeypatch, tmp_path, capsys):
    idx = pd.date_range("2022-01-01", periods=6, freq="D")
    s = pd.Series([-0.5, -0.3, 0.1, 0.4, -0.2, -0.1], index=idx)  # uninverts then re-inverts

    monkeypatch.setattr(yc, "SERIES", ["FAKE"])
    monkeypatch.setattr(yc.reader, "ticker_path", lambda *a, **k: tmp_path / "FAKE.parquet")
    monkeypatch.setattr(yc.reader, "load", lambda path: pd.DataFrame({"value": s}))

    yc.main()
    out = capsys.readouterr().out
    assert f"Most recent uninversion: {idx[2].date()}" in out
    assert f"Re-inverted since then: YES -- {idx[4].date()}" in out
    assert "Current (2022-01-06): -0.10" in out
