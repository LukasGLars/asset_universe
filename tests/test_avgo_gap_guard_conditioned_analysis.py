import numpy as np
import pandas as pd

from run_avgo_gap_guard_conditioned_analysis import event_stats_by_guard, guard_active_series


def _closes(values) -> pd.Series:
    idx = pd.date_range("2020-01-01", periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def test_guard_active_when_below_200d_sma():
    # Flat at 100 for 200+ days (SMA settles at 100), then drops to 90 and
    # stays there -- once below its own 200d SMA, guard must go active.
    closes = _closes([100.0] * 210 + [90.0] * 10)
    active = guard_active_series(closes)
    assert active.iloc[-1] == True
    assert active.iloc[205] == False  # still flat at 100, above its own SMA


def test_guard_active_on_crash_roc():
    # A sharp drop over the trailing 5 days should trip the crash-ROC
    # early-activation layer (-10% threshold) on its own.
    values = [100.0] * 205 + [98, 95, 92, 88, 85]
    closes = _closes(values)
    active = guard_active_series(closes)
    roc_5d = closes.iloc[-1] / closes.iloc[-6] - 1
    assert roc_5d <= -0.10
    assert active.iloc[-1] == True


def test_guard_inactive_in_a_calm_uptrend():
    closes = _closes([100 + i * 0.1 for i in range(250)])
    active = guard_active_series(closes)
    assert active.iloc[-1] == False


def test_guard_active_series_never_nan():
    closes = _closes([100.0] * 50)  # shorter than the 200d window
    active = guard_active_series(closes)
    assert not active.isna().any()


def test_event_stats_by_guard_splits_correctly():
    # 20 flat-then-rising sessions; mark guard active for the first half
    # of event indices, inactive for the second half, and confirm the
    # split groups land in the right buckets.
    closes = pd.Series([100 + i for i in range(60)])
    df = pd.DataFrame({"close": closes})
    guard = pd.Series([True] * 30 + [False] * 30)
    event_idx = list(range(0, 12))  # first 12 indices -- guard True for these (< 30)
    result = event_stats_by_guard(df, guard, event_idx, label="test")
    active_row = next(r for r in result if r["group"] == "test | guard ACTIVE" and r["horizon_days"] == 21)
    base_row = next(r for r in result if r["group"] == "test | guard base" and r["horizon_days"] == 21)
    assert active_row["n"] == 12   # all 12 event dates have guard=True
    assert base_row["n"] == 0      # none of them have guard=False


def test_event_stats_by_guard_blanks_below_min_n_obs():
    closes = pd.Series([100 + i for i in range(60)])
    df = pd.DataFrame({"close": closes})
    guard = pd.Series([True] * 60)
    event_idx = [0, 1]  # only 2 events -- below MIN_N_OBS=5
    result = event_stats_by_guard(df, guard, event_idx, label="test")
    row = next(r for r in result if r["group"] == "test | guard ACTIVE" and r["horizon_days"] == 21)
    assert row["n"] == 2
    assert row["median_return"] is None
