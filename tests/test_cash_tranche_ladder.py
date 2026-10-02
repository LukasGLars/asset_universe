"""Accounting guards for run_cash_tranche_ladder.py.

The verdict turns entirely on whether undeployed cash is charged honestly
and whether a fill can see the future. If any of these fail, the printed
ladder table must not be read.

Delete alongside run_cash_tranche_ladder.py.
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

import run_cash_tranche_ladder as m


def series(values: list[float]) -> pd.Series:
    idx = pd.bdate_range("2010-01-04", periods=len(values))
    return pd.Series(values, index=idx, dtype=float)


def flat_then(n_pre: int, path: list[float]) -> pd.Series:
    return series([100.0] * n_pre + path)


# ── ladder weights ────────────────────────────────────────────────────────────

def test_every_ladder_sums_to_one():
    for name, ladder in m.LADDERS.items():
        total = sum(w for _, w in ladder)
        assert abs(total - 1.0) < 1e-9, f"{name} sums to {total}"


def test_depths_are_non_negative_and_ordered_within_each_ladder():
    for name, ladder in m.LADDERS.items():
        depths = [d for d, _ in ladder]
        assert all(d >= 0.0 for d in depths), name
        assert depths == sorted(depths), f"{name} depths not ascending"


# ── single-tranche identity: the ladder maths must not add anything ──────────

def test_all_in_at_trigger_equals_plain_forward_return():
    """Ladder A is a 100% tranche at depth 0. Its return must be exactly the
    buy-and-hold return from close(signal+1) to close(signal+1+horizon) --
    no cash accrual, no fill-search, nothing."""
    px = series([100.0 + i for i in range(80)])
    sig_i, h = 10, 40
    r = m.ladder_episode(px, sig_i, [(0.00, 1.00)], h)
    expected = px.iloc[sig_i + 1 + h] / px.iloc[sig_i + 1] - 1.0
    assert r["ret"] == pytest.approx(expected, abs=1e-12)
    assert r["filled"] == [True]


# ── the cash charge ──────────────────────────────────────────────────────────

def test_unreachable_tranche_earns_exactly_cash_for_the_whole_horizon():
    """A level that is never touched must earn the cash rate compounded over
    the FULL horizon -- not 0%, and not the asset's return."""
    px = series([100.0 + i for i in range(80)])      # monotonically rising
    sig_i, h = 10, 40
    r = m.ladder_episode(px, sig_i, [(0.20, 1.00)], h)
    assert r["filled"] == [False]
    assert r["ret"] == pytest.approx((1 + m.CASH_DAILY) ** h - 1.0, abs=1e-12)


def test_cash_accrues_only_until_the_fill_day():
    """A tranche that fills on day k must earn cash for exactly k days, then
    the asset. Off-by-one here is worth several percent at 252d."""
    # entry at index 11 (=100). Falls to 90 on index 16, then recovers.
    px = flat_then(11, [100, 98, 96, 94, 92, 90, 95, 100, 110, 120, 130, 140])
    sig_i, h = 10, 10
    entry_i = sig_i + 1
    r = m.ladder_episode(px, sig_i, [(0.10, 1.00)], h)
    fill_i = 16
    assert px.iloc[fill_i] == 90.0
    expected = ((1 + m.CASH_DAILY) ** (fill_i - entry_i)) * (px.iloc[entry_i + h] / 90.0) - 1.0
    assert r["ret"] == pytest.approx(expected, abs=1e-12)


def test_cash_rate_is_a_drag_relative_to_a_rising_asset():
    """Sanity on direction: waiting in cash through a rally must lose to
    being invested. If this inverts, the cash leg has the wrong sign."""
    px = series([100.0 * (1.01 ** i) for i in range(80)])
    a = m.ladder_episode(px, 10, [(0.00, 1.00)], 40)["ret"]
    g = m.ladder_episode(px, 10, [(0.20, 1.00)], 40)["ret"]
    assert g < a


# ── no lookahead ─────────────────────────────────────────────────────────────

def test_signal_day_close_is_never_a_fill_price():
    """The trigger is computed FROM close(sig_i), so close(sig_i) is not a
    tradable price. Entry must be close(sig_i+1) even when the signal day
    was cheaper."""
    # index 10 is the cheap signal-day close; index 11 is higher.
    px = flat_then(10, [80, 100, 101, 102, 103, 104, 105, 106])
    r = m.ladder_episode(px, 10, [(0.00, 1.00)], 5)
    expected = px.iloc[16] / px.iloc[11] - 1.0      # 11 = entry, not 10
    assert r["ret"] == pytest.approx(expected, abs=1e-12)


def test_first_touch_searches_strictly_after_the_entry_day():
    """The entry day's own close cannot fill a deeper tranche, even if the
    entry close already sits below that tranche's level."""
    px = flat_then(11, [50, 50, 50, 50])            # entry close is already 50
    assert m.first_touch(px, entry_i=11, target=60.0, last_i=11) is None
    assert m.first_touch(px, entry_i=11, target=60.0, last_i=13) == 12


def test_fill_never_lands_after_the_measurement_window():
    """A level reached only after entry+horizon must count as unfilled, or
    the ladder is reading prices past its own end date."""
    px = flat_then(11, [100] * 20 + [50] * 10)      # drop happens at index ~31
    h = 10
    r = m.ladder_episode(px, 10, [(0.20, 1.00)], h)
    assert r["filled"] == [False]


def test_fill_never_lands_after_the_deploy_window():
    px = flat_then(11, [100] * 30 + [50] * 40)
    r = m.ladder_episode(px, 10, [(0.20, 1.00)], 60, deploy_window=5)
    assert r["filled"] == [False]


# ── fill price integrity ─────────────────────────────────────────────────────

def test_fill_price_is_at_or_below_the_requested_level():
    px = flat_then(11, [100, 97, 93, 88, 80, 95, 110, 120])
    entry_i, entry_px = 11, 100.0
    for depth in [0.05, 0.10, 0.15, 0.20]:
        fi = m.first_touch(px, entry_i, entry_px * (1 - depth), entry_i + 50)
        assert fi is not None
        assert px.iloc[fi] <= entry_px * (1 - depth) + 1e-9, depth


def test_deeper_tranches_fill_no_earlier_than_shallower_ones():
    px = flat_then(11, [100, 97, 93, 88, 80, 95, 110, 120])
    prev = -1
    for depth in [0.05, 0.10, 0.15, 0.20]:
        fi = m.first_touch(px, 11, 100.0 * (1 - depth), 61)
        assert fi >= prev
        prev = fi


# ── episode eligibility ──────────────────────────────────────────────────────

def test_episode_without_enough_forward_data_returns_none():
    px = series([100.0] * 20)
    assert m.ladder_episode(px, 10, [(0.00, 1.00)], 252) is None


def test_blend_is_a_weighted_average_of_its_own_tranches():
    """A multi-tranche ladder must equal the weight-blend of the same
    tranches run alone. Guards against double-counting a fill."""
    px = flat_then(11, [100, 96, 92, 88, 84, 95, 105, 115, 125, 135, 145, 155])
    sig_i, h = 10, 10
    ladder = [(0.00, 0.40), (0.10, 0.30), (0.20, 0.30)]
    blended = m.ladder_episode(px, sig_i, ladder, h)["ret"]
    parts = sum(
        w * (1.0 + m.ladder_episode(px, sig_i, [(d, 1.00)], h)["ret"])
        for d, w in ladder
    )
    assert blended == pytest.approx(parts - 1.0, abs=1e-12)


# ── part 1 / part 2 shapes ───────────────────────────────────────────────────

def test_conditional_drawdown_is_measured_from_the_entry_close():
    px = flat_then(11, [100] + [70] + [100] * (m.DD_WINDOW + 5))
    dd = m.part1_conditional_drawdown(px, [10])
    assert len(dd) == 1
    assert dd["further_dd"].iloc[0] == pytest.approx(-0.30, abs=1e-9)
    assert dd["days_to_trough"].iloc[0] == 1


def test_conditional_drawdown_ignores_the_entry_day_itself():
    """A -30% entry close is the price you paid, not a further drawdown."""
    px = flat_then(10, [100, 70] + [70] * (m.DD_WINDOW + 5))
    dd = m.part1_conditional_drawdown(px, [10])
    assert dd["further_dd"].iloc[0] == pytest.approx(0.0, abs=1e-9)


def test_hit_rate_is_bounded_and_depth_zero_always_hits():
    px = series([100.0 * (1.0 + 0.001 * np.sin(i / 7)) for i in range(1200)])
    sigs = [50, 300, 600]
    p2 = m.part2_depth_returns(px, sigs)
    assert ((p2["hit_rate"] >= 0) & (p2["hit_rate"] <= 1)).all()
    at_trigger = p2[p2["depth"] == "at trigger"]
    assert (at_trigger["hit_rate"] == 1.0).all()
