import numpy as np
import pandas as pd

from run_opp_sleeve_stop_sensitivity import (
    natural_exit_price, rs_20d_ok, run_config, simulate_trade,
)


def _series(prices: list[float]) -> np.ndarray:
    return np.array(prices, dtype=float)


def _flat_ma50(n: int, level: float) -> np.ndarray:
    """MA50 held far below price throughout -- isolates the hard-stop/
    trailing-stop behaviour under test without MA50 ever binding first."""
    return np.full(n, level, dtype=float)


def test_hard_stop_triggers_within_cutoff():
    # entry 100 -> hard stop 98. Dips to 97 on day 3, well within N=10.
    closes = _series([100, 99, 98.5, 97, 99, 100, 101, 102, 103, 104, 105])
    ma50 = _flat_ma50(len(closes), 50.0)
    trade = simulate_trade(closes, ma50, entry_idx=0, n_cutoff=10,
                            trailing_trigger=None, trailing_pct=None)
    assert trade["stopped"] is True
    assert trade["exit_offset"] == 3
    assert trade["exit_price"] == 97


def test_hard_stop_ignored_after_cutoff():
    # Same dip to 97, but now on day 12 -- past a N=10 cutoff, and MA50 is
    # held far below price, so nothing should bind; rides through to time exit.
    closes = _series([100] * 11 + [97] + [100] * 18)  # dip at offset 11
    ma50 = _flat_ma50(len(closes), 50.0)
    trade = simulate_trade(closes, ma50, entry_idx=0, n_cutoff=10,
                            trailing_trigger=None, trailing_pct=None)
    assert trade["stopped"] is False


def test_ma50_still_binds_regardless_of_cutoff():
    # Hard stop turned off after N=5, but MA50 sits just below entry and
    # price drops to meet it on day 6 -- MA50 must still catch this.
    closes = _series([100] * 6 + [95, 94] + [100] * 22)
    ma50 = _flat_ma50(len(closes), 95.0)
    trade = simulate_trade(closes, ma50, entry_idx=0, n_cutoff=5,
                            trailing_trigger=None, trailing_pct=None)
    assert trade["stopped"] is True
    assert trade["exit_offset"] == 6  # index 6 (offset 6) is the first close <= 95


def test_trailing_stop_triggers_after_threshold():
    # Rises to +10% (past a 0.05 trigger), pulls back to a 5%-below-peak level.
    entry = 100.0
    peak = 110.0
    pullback = peak * 0.95  # exactly at the trailing level
    closes = _series([entry, 105, peak, pullback - 0.01] + [110] * 20)
    ma50 = _flat_ma50(len(closes), 50.0)
    trade = simulate_trade(closes, ma50, entry_idx=0, n_cutoff=0,
                            trailing_trigger=0.05, trailing_pct=0.05)
    assert trade["stopped"] is True
    assert trade["exit_offset"] == 3


def test_trailing_stop_inactive_before_threshold():
    # Only rises 3% (below the 0.05 trigger) then pulls back hard -- trailing
    # stop must never engage since the profit trigger was never reached.
    closes = _series([100, 102, 103, 95] + [100] * 20)
    ma50 = _flat_ma50(len(closes), 50.0)
    trade = simulate_trade(closes, ma50, entry_idx=0, n_cutoff=0,
                            trailing_trigger=0.05, trailing_pct=0.05)
    assert trade["stopped"] is False


def test_no_stop_hits_time_exit():
    closes = _series([100.0] * 31)
    ma50 = _flat_ma50(len(closes), 50.0)
    trade = simulate_trade(closes, ma50, entry_idx=0, n_cutoff=10,
                            trailing_trigger=0.05, trailing_pct=0.05)
    assert trade["stopped"] is False
    assert trade["exit_offset"] == 30


def test_natural_exit_price_is_day_30_close_regardless_of_stop():
    closes = _series([100.0] * 31)
    closes[30] = 123.0
    assert natural_exit_price(closes, entry_idx=0) == 123.0


def test_run_config_detects_false_stop():
    # Stopped out on day 3 at 97, but the unstopped 30-day close (105) is
    # higher -- this must count as a false stop, not a protection.
    closes = _series([100, 99, 98.5, 97] + [105] * 27)
    ma50 = _flat_ma50(len(closes), 50.0)
    result = run_config([(closes, ma50, 0)], n_cutoff=10, trailing_trigger=None, trailing_pct=None)
    assert result["n_trades"] == 1
    assert result["stopped_pct"] == 1.0
    assert result["false_stop_pct_of_stopped"] == 1.0
    assert result["protection_pct_of_stopped"] == 0.0


def test_run_config_detects_protection():
    # Stopped out on day 3 at 97, and the unstopped 30-day close (80) is
    # lower -- the stop genuinely avoided a worse outcome.
    closes = _series([100, 99, 98.5, 97] + [80] * 27)
    ma50 = _flat_ma50(len(closes), 50.0)
    result = run_config([(closes, ma50, 0)], n_cutoff=10, trailing_trigger=None, trailing_pct=None)
    assert result["false_stop_pct_of_stopped"] == 0.0
    assert result["protection_pct_of_stopped"] == 1.0


def _dates(n: int, start: str = "2020-01-01") -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="D")


def test_rs_20d_ok_true_when_outperforming_spy():
    dates = _dates(25)
    closes = _series([100.0] * 25)
    closes[4], closes[24] = 100.0, 110.0  # ticker +10% over the trailing 20 days
    spy_ret20 = pd.Series(0.0, index=dates)  # SPY flat over the same window
    assert rs_20d_ok(closes, dates, entry_idx=24, spy_ret20=spy_ret20) is True


def test_rs_20d_ok_false_when_underperforming_spy():
    dates = _dates(25)
    closes = _series([100.0] * 25)
    closes[4], closes[24] = 100.0, 110.0  # ticker +10%
    spy_ret20 = pd.Series(0.20, index=dates)  # SPY +20% -- ticker lags
    assert rs_20d_ok(closes, dates, entry_idx=24, spy_ret20=spy_ret20) is False


def test_rs_20d_ok_none_when_insufficient_history():
    dates = _dates(25)
    closes = _series([100.0] * 25)
    spy_ret20 = pd.Series(0.0, index=dates)
    assert rs_20d_ok(closes, dates, entry_idx=10, spy_ret20=spy_ret20) is None


def test_rs_20d_ok_none_when_spy_dates_dont_overlap():
    dates = _dates(25, start="2020-01-01")
    closes = _series([100.0] * 25)
    closes[4], closes[24] = 100.0, 110.0
    spy_dates = _dates(25, start="2021-01-01")  # no overlap with the ticker's dates
    spy_ret20 = pd.Series(0.0, index=spy_dates)
    assert rs_20d_ok(closes, dates, entry_idx=24, spy_ret20=spy_ret20) is None
