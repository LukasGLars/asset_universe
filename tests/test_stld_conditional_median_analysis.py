import pandas as pd

import run_stld_conditional_median_analysis as cma


def test_median_and_mean_expectancy_diverge_when_one_outlier_win_present(monkeypatch, capsys):
    # 3 winners: +10%, +10%, +100% (outlier) ; 2 losers: -10%, -10%.
    idx = pd.date_range("2020-01-01", periods=20, freq="D")
    prices = pd.Series([100.0] * 20, index=idx)
    prices.iloc[2] = 110.0    # date0 -> date2: +10%
    prices.iloc[6] = 110.0    # date4 -> date6: +10%
    prices.iloc[10] = 200.0   # date8 -> date10: +100% (outlier)
    prices.iloc[14] = 90.0    # date12 -> date14: -10%
    prices.iloc[18] = 90.0    # date16 -> date18: -10%

    matched = pd.DatetimeIndex([idx[0], idx[4], idx[8], idx[12], idx[16]])

    monkeypatch.setattr(cma, "config", type("C", (), {"raw_data_dir": staticmethod(lambda: "dummy")}))
    monkeypatch.setattr(cma.es, "_matched_dates", lambda conditions, data_dir: matched)
    monkeypatch.setattr(cma.reader, "ticker_path", lambda *a, **k: "dummy")
    monkeypatch.setattr(cma.reader, "load", lambda path: pd.DataFrame({"close": prices}))
    monkeypatch.setattr(cma, "CALENDAR_DAYS", 2 * 365.25 / 252)

    cma.main()
    out = capsys.readouterr().out
    assert "Mean win   : +40.0%" in out    # (10+10+100)/3
    assert "Median win   : +10.0%" in out  # unaffected by the outlier
    assert "Max win : +100.0%" in out
    # Mean-based EV: 0.6*40% + 0.4*-10% = 24% - 4% = 20%
    # Median-based EV: 0.6*10% + 0.4*-10% = 6% - 4% = 2%
    assert "Mean-based expectancy   : +20.00%" in out
    assert "Median-based expectancy : +2.00%" in out
    assert "Gap (mean - median)     : +18.00%" in out
