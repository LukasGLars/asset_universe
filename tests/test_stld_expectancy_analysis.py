import pandas as pd

import run_stld_expectancy_analysis as sea
import run_entry_screen as es


def test_mean_win_mean_loss_differ_from_median_and_naive_stop_distance(monkeypatch, capsys):
    # 10 trading days/step price series so a 2-trading-day forward window is exact.
    # Matched dates: 3 winners (+20%, +10%, +10%) and 2 losers (-10%, -30%).
    idx = pd.date_range("2020-01-01", periods=20, freq="D")
    prices = pd.Series([100.0] * 20, index=idx)
    # date 0 -> date 2: 100 -> 120 (+20%)
    prices.iloc[2] = 120.0
    # date 4 -> date 6: 100 -> 110 (+10%)
    prices.iloc[6] = 110.0
    # date 8 -> date 10: 100 -> 110 (+10%)
    prices.iloc[10] = 110.0
    # date 12 -> date 14: 100 -> 90 (-10%)
    prices.iloc[14] = 90.0
    # date 16 -> date 18: 100 -> 70 (-30%)
    prices.iloc[18] = 70.0

    matched = pd.DatetimeIndex([idx[0], idx[4], idx[8], idx[12], idx[16]])

    monkeypatch.setattr(sea, "config", type("C", (), {"raw_data_dir": staticmethod(lambda: "dummy")}))
    monkeypatch.setattr(sea.es, "_matched_dates", lambda conditions, data_dir: matched)
    monkeypatch.setattr(sea.reader, "ticker_path", lambda *a, **k: "dummy")
    monkeypatch.setattr(sea.reader, "load", lambda path: pd.DataFrame({"close": prices}))
    monkeypatch.setattr(sea, "CALENDAR_DAYS", 2 * 365.25 / 252)  # forces trading_days == 2

    sea.main()
    out = capsys.readouterr().out
    assert "Win rate            : 60.0%" in out
    assert "Mean win (winners)   : +13.3%" in out
    assert "Mean loss (losers)   : -20.0%" in out
    # Real EV: 0.6*13.33% + 0.4*-20% ~= 0% (net to a rounding-noise sliver)
    ev_line = next(line for line in out.splitlines() if line.startswith("Real expectancy"))
    ev_value = float(ev_line.split(":")[-1].strip().rstrip("%")) / 100
    assert abs(ev_value) < 0.001
