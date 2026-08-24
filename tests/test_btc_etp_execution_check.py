import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from run_btc_etp_execution_check import (
    etp_position, spot_position, equity_from_position, perf,
)


def _series(n=300, start="2020-01-01", value=100.0):
    idx = pd.date_range(start, periods=n, freq="D")
    return pd.Series(value, index=idx)


def test_etp_position_never_changes_on_a_weekend():
    """The core constraint: a Swedish ETP cannot be traded Sat/Sun, so the
    position series must be flat across every weekend bar."""
    rng = np.random.default_rng(3)
    close = _series(n=500)
    close.iloc[:] = 100 * (1 + rng.normal(0.002, 0.03, 500)).cumprod()

    pos = etp_position(close, 200)
    changes = pos.diff().abs().fillna(0.0)
    weekend = pos.index.dayofweek >= 5
    assert changes[weekend].sum() == 0.0, "position changed on a weekend bar"


def test_spot_position_does_change_on_weekends():
    """Control: the 24/7 model is allowed to trade weekends, so the two
    models must actually differ -- otherwise the test above proves nothing."""
    rng = np.random.default_rng(4)
    close = _series(n=500)
    close.iloc[:] = 100 * (1 + rng.normal(0.002, 0.03, 500)).cumprod()

    spot = spot_position(close, 200)
    weekend = spot.index.dayofweek >= 5
    assert spot.diff().abs().fillna(0.0)[weekend].sum() > 0.0


def test_saturday_signal_is_filled_monday_not_sunday():
    """A signal that first turns true on a Saturday must not be acted on
    until the Monday bar."""
    idx = pd.date_range("2021-01-04", periods=400, freq="D")  # starts a Monday
    close = pd.Series(100.0, index=idx)
    # Pick a Saturday comfortably past bar 200 so SMA(200) is already defined,
    # then push price decisively above it from that Saturday onward.
    sat = [d for d in idx[250:] if d.dayofweek == 5][0]
    close.loc[sat:] = 300.0

    pos = etp_position(close, 200)
    sun = sat + pd.Timedelta(days=1)
    mon = sat + pd.Timedelta(days=2)
    assert pos.loc[sat] == 0.0, "filled on the Saturday itself"
    assert pos.loc[sun] == 0.0, "filled on the Sunday -- ETP is closed"
    assert pos.loc[mon] == 1.0, "should be filled on the Monday bar"


def test_etp_holder_is_exposed_to_the_weekend_move_while_held():
    """Being long into Friday means you eat the weekend gap -- that exposure
    must show up in the equity curve, not be silently skipped."""
    idx = pd.date_range("2021-01-04", periods=300, freq="D")
    close = pd.Series(100.0, index=idx)
    close.iloc[:250] = np.linspace(100, 400, 250)   # long uptrend -> long
    # crash across a specific weekend while held
    sat = [d for d in idx[250:] if d.dayofweek == 5][0]
    close.loc[sat:] = close.loc[:sat].iloc[-1] * 0.5

    ret = close.pct_change()
    pos = etp_position(close, 200)
    eq = equity_from_position(pos, ret, tc=0.0)
    # the drawdown must be materially negative -- the holder could not exit
    assert perf(eq)["maxdd"] < -0.20


def test_equity_charges_cost_once_per_flip():
    idx = pd.date_range("2021-01-04", periods=100, freq="D")
    pos = pd.Series(0.0, index=idx)
    pos.iloc[30:60] = 1.0
    ret = pd.Series(0.0, index=idx)
    eq = equity_from_position(pos, ret, tc=0.01)
    # exactly two flips at 1% each, compounded
    assert abs(eq.iloc[-1] - (0.99 * 0.99)) < 1e-9
