"""Guards for run_avgo_breakout_signal.py.

The verdict turns on whether the signal can see its own bar and whether the
entry can see the future. If these fail, do not read the tables.

Delete alongside run_avgo_breakout_signal.py.
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

import run_avgo_breakout_signal as m


def frame(close, volume=None):
    idx = pd.bdate_range("2010-01-04", periods=len(close))
    d = {"close": pd.Series(close, index=idx, dtype=float)}
    if volume is not None:
        d["volume"] = pd.Series(volume, index=idx, dtype=float)
    return pd.DataFrame(d)


# ── resistance must exclude the bar being tested ─────────────────────────────

def test_a_flat_series_never_breaks_out():
    """If the current bar counted toward its own resistance, >= vs > errors
    would fire here. It must not."""
    df = frame([100.0] * 200)
    assert m.signals(df, lookback=20, vol_min=0.0) == []


def test_breakout_requires_strictly_exceeding_the_prior_window_high():
    close = [100.0] * 30 + [100.0] + [101.0] + [100.0] * 30
    df = frame(close)
    sig = m.signals(df, lookback=20, vol_min=0.0)
    assert sig == [31]                      # the 101.0 bar, nothing else


def test_equalling_the_prior_high_is_not_a_breakout():
    """The matching high must sit INSIDE the lookback window, otherwise the
    second print is a real breakout against a window of 100s -- which is what
    the first version of this test got wrong."""
    close = [100.0] * 20 + [105.0] + [100.0] * 10 + [105.0] + [100.0] * 20
    df = frame(close)
    sig = m.signals(df, lookback=20, vol_min=0.0)
    assert 20 in sig, "the first 105 clears a window of 100s"
    assert 31 not in sig, "a tie with a high still inside the window is not a break"


def test_resistance_uses_only_the_lookback_window():
    """An old high outside the window must not suppress a breakout."""
    close = [500.0] + [100.0] * 60 + [110.0] + [100.0] * 10
    df = frame(close)
    sig = m.signals(df, lookback=20, vol_min=0.0)
    assert 61 in sig, "the 500 is 60 sessions back and outside a 20d lookback"


# ── volume ───────────────────────────────────────────────────────────────────

def test_volume_ratio_excludes_the_bar_from_its_own_mean():
    """A 10x spike must read ~10x. If the bar were inside its own trailing
    mean the ratio would be damped toward 1 and every threshold would be
    wrong."""
    vol = [100.0] * 60 + [1000.0]
    r = m.vol_ratio(frame([1.0] * 61, vol)["volume"])
    assert float(r.iloc[-1]) == pytest.approx(10.0, rel=1e-9)


def test_volume_filter_removes_low_volume_breakouts():
    close = [100.0] * 60 + [110.0]
    quiet = frame(close, [100.0] * 60 + [50.0])     # 0.5x
    loud = frame(close, [100.0] * 60 + [300.0])     # 3.0x
    assert m.signals(quiet, 20, 0.0) == [60]
    assert m.signals(quiet, 20, 1.5) == []
    assert m.signals(loud, 20, 1.5) == [60]


def test_vol_min_zero_is_the_unfiltered_control():
    close = [100.0] * 60 + [110.0]
    df = frame(close, [100.0] * 60 + [1.0])         # near-zero volume
    assert m.signals(df, 20, 0.0) == [60], "vol_min=0 must ignore volume entirely"


# ── declustering ─────────────────────────────────────────────────────────────

def test_a_rising_run_is_declustered_to_the_spacing():
    """A monotonic climb breaks out every session. Declustering must thin it,
    or one trend counts as a hundred independent signals."""
    df = frame([100.0 + i for i in range(200)])
    sig = m.signals(df, 20, 0.0)
    assert len(sig) >= 3
    assert all(b - a >= m.DECLUSTER for a, b in zip(sig, sig[1:]))


# ── no lookahead ─────────────────────────────────────────────────────────────

def test_entry_is_the_session_after_the_signal():
    close = frame([float(i) for i in range(100)])["close"]
    assert m.fwd(close, 10, 5) == pytest.approx(close.iloc[16] / close.iloc[11] - 1)


def test_forward_return_is_none_past_the_end_of_history():
    close = frame([1.0] * 20)["close"]
    assert m.fwd(close, 15, 10) is None
    assert m.fwd(close, 18, 1) is None


def test_baseline_is_computed_on_the_same_entry_convention():
    """The baseline must use close(i+1) entries too, or the edge-over-holding
    column compares two different conventions."""
    close = frame([100.0 * 1.001 ** i for i in range(400)])["close"]
    base = m.baseline(close)
    manual = pd.Series([m.fwd(close, i, 21) for i in range(len(close))]).dropna()
    assert base[21] == pytest.approx(float(manual.median()), rel=1e-12)
