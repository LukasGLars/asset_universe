import pandas as pd

from run_opp_sleeve_vol_scaled_trailing_sensitivity import simulate_trade, summarize


def _prices(start, values):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def _flat_ma50(prices: pd.Series, level: float) -> pd.Series:
    return pd.Series(level, index=prices.index)


def test_ma50_buffer_binds_at_the_live_5pct_value():
    # MA50 at 100; buffered stop = 95. A close of 96 must NOT stop (above
    # the buffer); a close of 94 must stop (below it).
    prices = _prices("2020-01-01", [100, 100, 100, 96] + [100] * 15)
    ma50 = _flat_ma50(prices, 100.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"),
                            trailing_trigger=0.05, trailing_pct=0.05)
    assert trade["stopped"] is False

    prices2 = _prices("2020-01-01", [100, 100, 100, 94] + [100] * 15)
    trade2 = simulate_trade(prices2, ma50, pd.Timestamp("2020-01-01"),
                             trailing_trigger=0.05, trailing_pct=0.05)
    assert trade2["stopped"] is True


def test_no_hard_stop_a_dip_below_entry_without_ma50_breach_survives():
    # MA50 held far below price -- a routine dip that never crosses the
    # buffered MA50 must never stop, regardless of how far below entry it
    # goes (no hard stop in this exit logic anymore).
    prices = _prices("2020-01-01", [100] * 3 + [90] + [100] * 15)
    ma50 = _flat_ma50(prices, 50.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"),
                            trailing_trigger=0.05, trailing_pct=0.05)
    assert trade["stopped"] is False


def test_trailing_trigger_and_pct_are_the_variables_under_test():
    # Peak at +6% (above a 5% trigger, below an 8% trigger) -- must stop
    # under trigger=0.05 but not under trigger=0.08, all else equal.
    entry = 100.0
    peak = 106.0
    pullback = peak * 0.95 - 0.01  # just under a 5%-trailing level
    prices = _prices("2020-01-01", [entry, 103, peak, pullback] + [110] * 15)
    ma50 = _flat_ma50(prices, 50.0)

    trade_tight = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"),
                                  trailing_trigger=0.05, trailing_pct=0.05)
    assert trade_tight["stopped"] is True

    trade_loose_trigger = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"),
                                          trailing_trigger=0.08, trailing_pct=0.05)
    assert trade_loose_trigger["stopped"] is False  # peak never reached the 8% trigger


def test_time_exit_at_21_days_when_nothing_binds():
    prices = _prices("2020-01-01", [100.0] * 30)
    prices.iloc[21] = 111.0
    ma50 = _flat_ma50(prices, 50.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2020-01-01"),
                            trailing_trigger=0.05, trailing_pct=0.05)
    assert trade["stopped"] is False
    assert abs(trade["return"] - 0.11) < 1e-9


def test_none_when_entry_date_unresolvable():
    prices = _prices("2020-01-01", [100.0] * 5)
    ma50 = _flat_ma50(prices, 50.0)
    trade = simulate_trade(prices, ma50, pd.Timestamp("2019-01-01"),
                            trailing_trigger=0.05, trailing_pct=0.05)
    assert trade is None


def test_summarize_blanks_below_min_n_obs():
    trades = [{"return": 0.05, "stopped": False}] * 3
    stats = summarize(trades)
    assert stats["n"] == 3
    assert stats["median_return"] is None
    assert stats["calmar_like"] is None


def test_summarize_computes_calmar_like():
    trades = [{"return": r, "stopped": False} for r in
              [0.10, 0.12, -0.05, 0.08, 0.15, -0.03, 0.09, 0.11, 0.07, 0.10]]
    stats = summarize(trades)
    assert stats["n"] == 10
    assert stats["median_return"] is not None
    assert stats["calmar_like"] is not None
    assert stats["calmar_like"] > 0  # positive median over a modest downside
