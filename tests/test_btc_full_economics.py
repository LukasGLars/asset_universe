import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from run_btc_full_economics import (
    etp_position, trend_equity, hold_equity, perf,
    MGMT_FEE_ANNUAL, DAILY_FEE, breakeven_spread,
)


def _days(n, start="2021-01-04"):
    return pd.date_range(start, periods=n, freq="D")


def test_hold_pays_the_full_fee_every_day():
    """Zero market return for a year -> buy-and-hold must lose ~the whole
    annual fee, because the ETP charges it regardless of performance."""
    idx = _days(365)
    ret = pd.Series(0.0, index=idx)
    eq = hold_equity(ret)
    assert abs((eq.iloc[-1] - 1.0) + MGMT_FEE_ANNUAL) < 2e-4


def test_flat_trend_arm_pays_no_fee_at_all():
    """Never holding means never paying the management fee -- the whole
    point of the leg that earlier runs omitted."""
    idx = _days(365)
    ret = pd.Series(0.02, index=idx)          # market rips; we are out
    pos = pd.Series(0.0, index=idx)
    eq = trend_equity(pos, ret, spread=0.005)
    assert abs(eq.iloc[-1] - 1.0) < 1e-12


def test_always_held_trend_arm_matches_hold_when_no_flips():
    """Held every day with zero flips must equal buy-and-hold exactly --
    proves the fee is applied on the same basis to both arms."""
    idx = _days(400)
    rng = np.random.default_rng(7)
    ret = pd.Series(rng.normal(0.001, 0.02, 400), index=idx)
    pos = pd.Series(1.0, index=idx)
    a = trend_equity(pos, ret, spread=0.01)   # spread irrelevant: no flips
    b = hold_equity(ret)
    assert abs(a.iloc[-1] - b.iloc[-1]) < 1e-12


def test_half_time_in_market_pays_about_half_the_fee():
    idx = _days(365)
    ret = pd.Series(0.0, index=idx)
    pos = pd.Series(0.0, index=idx)
    pos.iloc[:182] = 1.0                       # ~half the year, one flip out
    eq = trend_equity(pos, ret, spread=0.0)
    drag = 1.0 - eq.iloc[-1]
    assert abs(drag - MGMT_FEE_ANNUAL * 0.5) < 1e-3


def test_spread_charged_per_flip_not_per_day_held():
    idx = _days(100)
    ret = pd.Series(0.0, index=idx)
    pos = pd.Series(0.0, index=idx)
    pos.iloc[30:60] = 1.0                      # exactly two flips
    eq_a = trend_equity(pos, ret, spread=0.01)
    # strip the fee to isolate spread: 2 flips x 1%
    fee_drag = DAILY_FEE * 30
    assert abs((1.0 - eq_a.iloc[-1]) - (2 * 0.01 + fee_drag)) < 1e-3


def test_breakeven_spread_is_monotonic_and_bracketed():
    idx = _days(800)
    rng = np.random.default_rng(5)
    px = pd.Series(100 * (1 + rng.normal(0.003, 0.03, 800)).cumprod(), index=idx)
    ret = px.pct_change()
    pos = etp_position(px, 150)
    hold_cagr = perf(hold_equity(ret))["cagr"]
    be = breakeven_spread(pos, ret, hold_cagr)
    if be not in (None, float("inf")):
        # just below break-even the trend arm wins; just above it loses
        below = perf(trend_equity(pos, ret, be * 0.5))["cagr"]
        above = perf(trend_equity(pos, ret, min(be * 2, 0.5)))["cagr"]
        assert below > hold_cagr >= above - 1e-9


def test_signal_still_cannot_capture_its_own_day():
    idx = _days(400)
    px = pd.Series(100.0, index=idx)
    px.iloc[300] = 900.0
    assert etp_position(px, 150).iloc[300] == 0.0
