import numpy as np
import pandas as pd

import run_opp_sleeve_capitulation_stop_sensitivity as sens


def _prices(start, values):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def test_simulate_trade_no_stop_returns_natural_exit():
    values = [100.0] + [100.0 + i * 0.5 for i in range(1, 30)]
    prices = _prices("2020-01-01", values)
    trade = sens.simulate_trade(prices, prices.index[0], duration_days=21, hard_stop_pct=None,
                                 trailing_trigger_pct=None, trailing_pct=None)
    assert trade is not None
    assert trade["stopped"] is False
    assert trade["return"] == trade["natural_return"]


def test_simulate_trade_hits_entry_floor():
    # Drops straight through a 10% floor from entry.
    values = [100.0] + [100.0 - i for i in range(1, 30)]
    prices = _prices("2020-01-01", values)
    trade = sens.simulate_trade(prices, prices.index[0], duration_days=21, hard_stop_pct=0.10,
                                 trailing_trigger_pct=None, trailing_pct=None)
    assert trade is not None
    assert trade["stopped"] is True
    assert trade["return"] <= -0.10 + 1e-9


def test_simulate_trade_hits_trailing_stop_after_arming():
    # Rallies 10% (arms a 5% trigger), then falls 5% off the peak.
    values = [100.0] + [100.0 + i for i in range(1, 11)] + [110.0 - i for i in range(1, 20)]
    prices = _prices("2020-01-01", values)
    trade = sens.simulate_trade(prices, prices.index[0], duration_days=21, hard_stop_pct=None,
                                 trailing_trigger_pct=0.05, trailing_pct=0.05)
    assert trade is not None
    assert trade["stopped"] is True


def test_simulate_trade_none_when_entry_beyond_history():
    prices = _prices("2020-01-01", [100.0, 101.0])
    trade = sens.simulate_trade(prices, pd.Timestamp("2025-01-01"), duration_days=21,
                                 hard_stop_pct=0.10, trailing_trigger_pct=None, trailing_pct=None)
    assert trade is None


def test_run_config_false_stop_when_natural_return_higher():
    # Dips just past a tight 2% floor, then fully recovers by day 21 -- a
    # textbook false stop: natural (unstopped) return ends up positive.
    values = [100.0, 97.5] + [97.5 + i * 0.5 for i in range(1, 25)]
    prices = _prices("2020-01-01", values)
    candidates = {"A": ("equities", prices)}
    entries = [{"ticker": "A", "date": prices.index[0]}]

    row = sens.run_config(entries, candidates, hard_stop_pct=0.02, trailing_trigger_pct=None, trailing_pct=None)
    assert row["n_trades"] == 1
    assert row["stopped_pct"] == 1.0
    assert row["false_stop_pct_of_stopped"] == 1.0
    assert row["protection_pct_of_stopped"] == 0.0


def test_run_config_protection_when_natural_return_lower():
    # Dips past a tight floor, then keeps falling hard -- the stop earned its keep.
    values = [100.0, 97.5] + [97.5 - i for i in range(1, 25)]
    prices = _prices("2020-01-01", values)
    candidates = {"A": ("equities", prices)}
    entries = [{"ticker": "A", "date": prices.index[0]}]

    row = sens.run_config(entries, candidates, hard_stop_pct=0.02, trailing_trigger_pct=None, trailing_pct=None)
    assert row["n_trades"] == 1
    assert row["stopped_pct"] == 1.0
    assert row["protection_pct_of_stopped"] == 1.0
    assert row["false_stop_pct_of_stopped"] == 0.0


def test_run_config_empty_entries_returns_nan_row():
    row = sens.run_config([], {}, hard_stop_pct=0.10, trailing_trigger_pct=None, trailing_pct=None)
    assert row["n_trades"] == 0
    assert np.isnan(row["median_return"])


def test_run_phase_includes_none_floor_as_a_competing_row():
    # None (no floor at all) must appear as a real, scored Phase 1 row --
    # not skipped or treated only as a bracketing case -- same fix already
    # applied to the original stop-sensitivity script after it wrongly
    # excluded its own "stop never active" baseline from competing.
    values = [100.0 + i * 0.3 for i in range(40)]
    prices = _prices("2020-01-01", values)
    candidates = {"A": ("equities", prices)}
    entries = [{"ticker": "A", "date": prices.index[0]}]

    rows = sens.run_phase("TEST", entries, candidates)
    phase1 = [r for r in rows if r["trailing_trigger"] == ""]
    assert len(phase1) == len(sens.HARD_STOP_GRID)
    assert any(r["hard_stop_pct"] == "" for r in phase1)  # None present, not excluded
