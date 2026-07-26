import numpy as np
import pandas as pd

from run_opp_sleeve_combined_sensitivity import (
    realized_vol_at_entry, simulate_trade, summarize, vol_bucket,
)


def _prices(start, values):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def _flat_ma50(prices: pd.Series, level: float) -> pd.Series:
    return pd.Series(level, index=prices.index)


def test_simulate_trade_hard_stop_triggers_when_always_active():
    prices = _prices("2020-01-01", [100, 99, 98.5, 97, 99, 100, 101, 102])
    ma50 = _flat_ma50(prices, 50.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"), duration_days=30,
                            n_cutoff="always", trailing_trigger=None, trailing_pct=None)
    assert trade["stopped"] is True
    assert trade["return"] == (97 - 100) / 100


def test_simulate_trade_hard_stop_off_when_n_cutoff_zero():
    # Same dip to 97, but hard stop never active (n_cutoff=0) and MA50 far
    # below -- should ride through to the time exit.
    prices = _prices("2020-01-01", [100, 99, 98.5, 97] + [100] * 10)
    ma50 = _flat_ma50(prices, 50.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"), duration_days=10,
                            n_cutoff=0, trailing_trigger=None, trailing_pct=None)
    assert trade["stopped"] is False


def test_simulate_trade_hard_stop_expires_after_n_cutoff_days():
    # Hard stop only active for the first 5 days; the dip to 97 happens on
    # day 8 (calendar), past the cutoff, and MA50 sits far below -- no stop.
    prices = _prices("2020-01-01", [100] * 8 + [97] + [100] * 10)
    ma50 = _flat_ma50(prices, 50.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"), duration_days=18,
                            n_cutoff=5, trailing_trigger=None, trailing_pct=None)
    assert trade["stopped"] is False


def test_simulate_trade_ma50_binds_regardless_of_hard_stop_state():
    prices = _prices("2020-01-01", [100] * 6 + [95, 94] + [100] * 10)
    ma50 = _flat_ma50(prices, 95.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"), duration_days=17,
                            n_cutoff=0, trailing_trigger=None, trailing_pct=None)
    assert trade["stopped"] is True


def test_simulate_trade_trailing_stop_triggers_after_threshold():
    entry = 100.0
    peak = 110.0
    pullback = peak * 0.95 - 0.01  # just under the trailing level
    prices = _prices("2020-01-01", [entry, 105, peak, pullback] + [110] * 10)
    ma50 = _flat_ma50(prices, 50.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"), duration_days=14,
                            n_cutoff=0, trailing_trigger=0.05, trailing_pct=0.05)
    assert trade["stopped"] is True


def test_simulate_trade_time_exit_at_target_duration():
    prices = _prices("2020-01-01", [100.0] * 40)
    prices.iloc[30] = 123.0
    ma50 = _flat_ma50(prices, 50.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"), duration_days=30,
                            n_cutoff=0, trailing_trigger=None, trailing_pct=None)
    assert trade["stopped"] is False
    assert abs(trade["return"] - 0.23) < 1e-9


def test_simulate_trade_none_when_entry_date_unresolvable():
    prices = _prices("2020-01-01", [100.0] * 5)
    ma50 = _flat_ma50(prices, 50.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2019-01-01"), duration_days=30,
                            n_cutoff=0, trailing_trigger=None, trailing_pct=None)
    assert trade is None


def test_realized_vol_at_entry_higher_for_choppier_series():
    calm = _prices("2020-01-01", [100 + (i % 2) * 0.1 for i in range(40)])
    choppy = _prices("2020-01-01", [100 + (i % 2) * 10 for i in range(40)])
    entry = pd.Timestamp("2020-02-01")
    v_calm = realized_vol_at_entry(calm, entry)
    v_choppy = realized_vol_at_entry(choppy, entry)
    assert v_calm is not None and v_choppy is not None
    assert v_choppy > v_calm


def test_realized_vol_at_entry_none_before_lookback_window():
    prices = _prices("2020-01-01", [100.0] * 40)
    assert realized_vol_at_entry(prices, pd.Timestamp("2020-01-02")) is None


def test_vol_bucket_assigns_by_tercile():
    assert vol_bucket(0.01, q33=0.02, q67=0.05) == "low_vol"
    assert vol_bucket(0.03, q33=0.02, q67=0.05) == "mid_vol"
    assert vol_bucket(0.08, q33=0.02, q67=0.05) == "high_vol"
    assert vol_bucket(None, q33=0.02, q67=0.05) == "unknown"


def test_summarize_blanks_stats_below_min_n_obs():
    trades = [{"return": 0.05, "stopped": False}] * 3  # below MIN_N_OBS=10
    stats = summarize(trades, duration_days=30)
    assert stats["n"] == 3
    assert stats["median_return"] is None


def test_summarize_computes_median_win_rate_and_annualized():
    trades = [{"return": r, "stopped": False} for r in
              [0.10, 0.12, 0.08, -0.02, 0.15, 0.09, 0.11, 0.07, 0.13, 0.10]]
    stats = summarize(trades, duration_days=30)
    assert stats["n"] == 10
    assert stats["median_return"] == round(float(np.median([t["return"] for t in trades])), 4)
    assert stats["win_rate"] == 0.9
    assert stats["annualized_median"] is not None
