import pandas as pd

import run_lly_earnings_behavior_analysis as lly


def test_reaction_and_drift_windows_align_on_first_day_on_or_after_earnings(monkeypatch):
    # Flat at 100 for 10 days, jumps to 110 on day 10 onward (the "reaction"),
    # then drifts up 1/day for 30 more days (the "post" window).
    values = [100.0] * 10 + [110.0 + i for i in range(30)]
    idx = pd.date_range("2020-01-01", periods=len(values), freq="D")
    prices = pd.Series(values, index=idx)
    monkeypatch.setattr(lly.reader, "load", lambda path: pd.DataFrame({"close": prices}))
    monkeypatch.setattr(lly.reader, "ticker_path", lambda *a, **k: "dummy")
    monkeypatch.setattr(lly.pead, "_earnings_surprises",
                         lambda ticker: pd.DataFrame({"date": [idx[10]], "surprise": [5.0]}))

    lly.main()
    df = pd.read_csv("comparison_results/lly_earnings_behavior.csv")
    assert len(df) == 1
    row = df.iloc[0]
    assert abs(row["reaction"] - 0.10) < 1e-6  # 100 -> 110
    assert row["post_21d"] > 0  # steady drift up after the reaction close
