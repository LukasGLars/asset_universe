import pandas as pd

import run_midterm_election_analysis as mid


def test_pre_and_post_windows_align_on_first_trading_day_on_or_after_election(monkeypatch, capsys, tmp_path):
    # Flat at 100 through election day itself, with a known -5% dip 63
    # trading days before the election, then a +10% jump starting the
    # day AFTER the election (the "post" window) -- isolates pre_63d
    # from the reaction instead of mixing the two together.
    n = 400
    dates = pd.date_range("2018-01-01", periods=n, freq="D")
    values = [100.0] * n
    election_idx = 200
    values[election_idx - 63] = 105.26  # so 100/105.26 - 1 = -5%
    for i in range(election_idx + 1, n):
        values[i] = 110.0
    prices = pd.Series(values, index=dates)

    dummy_path = tmp_path / "AVGO.parquet"
    pd.DataFrame({"date": dates, "close": values}).to_parquet(dummy_path)

    monkeypatch.setattr(mid, "MIDTERM_DATES", [str(dates[election_idx].date())])
    monkeypatch.setattr(mid, "HOLDINGS", [("AVGO", "equities")])
    monkeypatch.setattr(mid.reader, "ticker_path", lambda *a, **k: dummy_path)

    mid.main()
    out = capsys.readouterr().out
    assert "AVGO" in out
    assert "pre_63d=-5.0%" in out
    assert "post_21d=+10.0%" in out
    assert "post_63d=+10.0%" in out
