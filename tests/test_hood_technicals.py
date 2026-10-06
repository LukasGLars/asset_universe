"""Guards for run_hood_technicals.py. Indicator maths only -- a misreported
RSI or an inverted range position is the whole risk in a read-out script.

Delete alongside run_hood_technicals.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import run_hood_technicals as m


def s(vals):
    return pd.Series(vals, index=pd.bdate_range("2020-01-01", periods=len(vals)),
                     dtype=float)


def test_rsi_is_100_when_price_only_rises():
    assert m.rsi(s([100 + i for i in range(60)])) == pytest.approx(100.0)


def test_rsi_is_near_zero_when_price_only_falls():
    assert m.rsi(s([100 - i for i in range(60)])) < 1.0


def test_rsi_stays_in_bounds_on_noise():
    rng = np.random.default_rng(3)
    v = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 400)))
    assert 0.0 <= m.rsi(s(list(v))) <= 100.0


def test_rsi_of_a_flat_series_is_100_by_the_zero_loss_branch():
    """Documents the convention: no losses means no RS denominator."""
    assert m.rsi(s([100.0] * 40)) == 100.0


def test_roc_matches_a_hand_computed_ratio():
    v = s([10.0, 11.0, 12.0, 13.0, 14.0])
    assert m.roc(v, 4) == pytest.approx(14 / 10 - 1)
    assert m.roc(v, 1) == pytest.approx(14 / 13 - 1)


def test_roc_returns_none_when_the_window_exceeds_history():
    assert m.roc(s([1.0, 2.0, 3.0]), 10) is None


def test_range_position_is_zero_at_the_low_and_one_at_the_high():
    rising = s([float(i) for i in range(1, 101)])
    _, _, pos, from_hi = m.pct_of_range(rising)
    assert pos == pytest.approx(1.0)
    assert from_hi == pytest.approx(0.0)

    falling = s([float(i) for i in range(100, 0, -1)])
    _, _, pos2, from_hi2 = m.pct_of_range(falling)
    assert pos2 == pytest.approx(0.0)
    assert from_hi2 == pytest.approx(1 / 100 - 1)


def test_range_uses_only_the_trailing_window():
    """An old spike outside the 252d window must not set the high."""
    v = [1000.0] + [50.0] * 300
    _, hi, _, _ = m.pct_of_range(s(v), window=252)
    assert hi == pytest.approx(50.0)


def test_realised_vol_of_a_constant_series_is_zero():
    assert m.realised_vol(s([100.0] * 100)) == pytest.approx(0.0)


def test_realised_vol_is_annualised():
    rng = np.random.default_rng(5)
    daily = 0.01
    v = 100 * np.exp(np.cumsum(rng.normal(0, daily, 3000)))
    got = m.realised_vol(s(list(v)), window=2000)
    assert got == pytest.approx(daily * np.sqrt(252), rel=0.15)
