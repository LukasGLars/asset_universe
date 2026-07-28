import pandas as pd

from run_avgo_gap_down_analysis import event_stats, forward_return, gap_pct


def _df(dates, opens, closes) -> pd.DataFrame:
    idx = pd.to_datetime(dates)
    return pd.DataFrame({"open": opens, "close": closes}, index=idx)


def test_gap_pct_flags_negative_gap_correctly():
    # prior close 100, next open 95 -> gap of -5%
    df = _df(["2020-01-01", "2020-01-02"], [100.0, 95.0], [100.0, 96.0])
    gaps = gap_pct(df)
    assert pd.isna(gaps.iloc[0])  # no prior close for the first row
    assert abs(gaps.iloc[1] - (-0.05)) < 1e-9


def test_gap_pct_positive_gap_is_not_negative():
    df = _df(["2020-01-01", "2020-01-02"], [100.0, 103.0], [100.0, 104.0])
    gaps = gap_pct(df)
    assert gaps.iloc[1] > 0


def test_forward_return_basic():
    closes = pd.Series([100.0, 101.0, 102.0, 110.0])
    r = forward_return(closes, idx=0, horizon_days=3)
    assert r is not None
    assert abs(r - 0.10) < 1e-9


def test_forward_return_none_when_horizon_beyond_history():
    closes = pd.Series([100.0, 101.0, 102.0])
    assert forward_return(closes, idx=0, horizon_days=5) is None


def test_event_stats_blanks_below_min_n_obs():
    df = _df(
        [f"2020-01-{d:02d}" for d in range(1, 11)],
        [100.0] * 10,
        [100 + i for i in range(10)],
    )
    # only 2 events -- below MIN_N_OBS=5
    result = event_stats(df, event_idx=[1, 2], label="test")
    row = next(r for r in result if r["horizon_days"] == 5)
    assert row["n"] == 2
    assert row["median_return"] is None


def test_event_stats_computes_median_and_win_rate_above_min_n_obs():
    closes = [100 + i for i in range(300)]  # steadily rising
    df = _df([f"2020-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(300)],
             [100.0] * 300, closes)
    event_idx = list(range(1, 8))  # 7 events, above MIN_N_OBS
    result = event_stats(df, event_idx, label="test")
    row = next(r for r in result if r["horizon_days"] == 5)
    assert row["n"] == 7
    assert row["median_return"] is not None
    assert row["median_return"] > 0  # steadily rising series
    assert row["win_rate"] == 1.0
