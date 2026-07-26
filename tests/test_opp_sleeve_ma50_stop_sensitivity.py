import pandas as pd

from run_opp_sleeve_ma50_stop_sensitivity import simulate_trade


def _prices(start, values):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def _flat_ma50(prices: pd.Series, level: float) -> pd.Series:
    return pd.Series(level, index=prices.index)


def test_ma50_binds_immediately_with_zero_grace_and_no_buffer():
    prices = _prices("2020-01-01", [100] * 4 + [94] + [100] * 10)
    ma50 = _flat_ma50(prices, 95.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"), duration_days=14,
                            ma50_grace_days=0, ma50_buffer_pct=0.0)
    assert trade["stopped"] is True
    assert trade["return"] == (94 - 100) / 100


def test_ma50_grace_period_suppresses_early_stop():
    # Dip below MA50 on day 3, well within a 10-day grace period -- must NOT
    # stop; rides through the rest of the (flat) series to the time exit.
    prices = _prices("2020-01-01", [100] * 3 + [94] + [100] * 15)
    ma50 = _flat_ma50(prices, 95.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"), duration_days=18,
                            ma50_grace_days=10, ma50_buffer_pct=0.0)
    assert trade["stopped"] is False


def test_ma50_grace_period_still_binds_after_it_expires():
    # Price sits below MA50 the whole time; grace period only delays the
    # stop, it doesn't cancel it once expired.
    prices = _prices("2020-01-01", [100] * 11 + [94] * 10)
    ma50 = _flat_ma50(prices, 95.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"), duration_days=20,
                            ma50_grace_days=10, ma50_buffer_pct=0.0)
    assert trade["stopped"] is True
    assert trade["return"] == (94 - 100) / 100


def test_ma50_buffer_requires_deeper_breach_than_raw_ma50():
    # MA50 at 95; a close of 94 is below the raw MA50 but within a 3% buffer
    # (stop level 95*0.97=92.15) -- must NOT stop under the buffered rule,
    # but WOULD stop with zero buffer (covered by the first test above).
    prices = _prices("2020-01-01", [100] * 4 + [94] + [100] * 10)
    ma50 = _flat_ma50(prices, 95.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"), duration_days=14,
                            ma50_grace_days=0, ma50_buffer_pct=0.03)
    assert trade["stopped"] is False


def test_ma50_buffer_still_binds_on_a_deep_enough_breach():
    prices = _prices("2020-01-01", [100] * 4 + [90] + [100] * 10)  # well below 92.15
    ma50 = _flat_ma50(prices, 95.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"), duration_days=14,
                            ma50_grace_days=0, ma50_buffer_pct=0.03)
    assert trade["stopped"] is True


def test_trailing_stop_still_active_regardless_of_ma50_config():
    # MA50 held far below (never binds); trailing stop must still fire once
    # the profit trigger is reached and price pulls back.
    entry = 100.0
    peak = 110.0
    pullback = peak * 0.95 - 0.01
    prices = _prices("2020-01-01", [entry, 105, peak, pullback] + [110] * 15)
    ma50 = _flat_ma50(prices, 50.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"), duration_days=18,
                            ma50_grace_days=0, ma50_buffer_pct=0.0)
    assert trade["stopped"] is True


def test_ma50_off_sentinel_never_binds():
    prices = _prices("2020-01-01", [100] * 4 + [50] + [100] * 10)  # deep crash
    ma50 = _flat_ma50(prices, 95.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"), duration_days=14,
                            ma50_grace_days=10 ** 6, ma50_buffer_pct=0.0)
    assert trade["stopped"] is False


def test_none_when_entry_date_unresolvable():
    prices = _prices("2020-01-01", [100.0] * 5)
    ma50 = _flat_ma50(prices, 50.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2019-01-01"), duration_days=30,
                            ma50_grace_days=0, ma50_buffer_pct=0.0)
    assert trade is None
