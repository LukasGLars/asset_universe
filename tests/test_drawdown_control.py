"""Tests for run_drawdown_control.py (temporary diagnostic, 2026-08-31).

This script's conclusions rest on two things being right: the bucket blend
must be real two-level rebalancing (not a linear fudge), and the core sim
must match run_base_optimizer.py's convention so its numbers are
comparable to the 231-combo grid already committed to the repo.
"""
import numpy as np
import pandas as pd
import pytest

import run_drawdown_control as dc


def _prices(n=500, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-04", periods=n)      # post AVGO IPO
    return pd.DataFrame(
        {k: 100.0 * np.cumprod(1 + rng.normal(0.0003, 0.011, n))
         for k in ("Gold", "AVGO", "LLY")}, index=idx)


def _flat(idx, annual=0.02):
    d = (1 + annual) ** (1 / 252) - 1
    return pd.Series((1 + d) ** np.arange(len(idx)), index=idx)


# ── Bucket blend ──────────────────────────────────────────────────────────

def test_full_core_returns_the_core_path_unchanged():
    px = _prices()
    core = dc.simulate_core(px, dc.LIVE_CORE_W)
    pd.testing.assert_series_equal(dc.blend(core, _flat(px.index), 1.0), core)


def test_zero_core_tracks_home_base():
    px = _prices()
    core = dc.simulate_core(px, dc.LIVE_CORE_W)
    hb = _flat(px.index)
    out = dc.blend(core, hb, 0.0, tc_bps=0.0)
    assert out.iloc[-1] == pytest.approx(hb.iloc[-1], rel=1e-9)


def test_blend_drawdown_sits_between_the_two_legs():
    """The whole premise of using the bucket split as the drawdown lever:
    diluting with a low-vol sleeve must land strictly between."""
    px = _prices()
    core = dc.simulate_core(px, dc.LIVE_CORE_W)
    hb = _flat(px.index)
    dd_core = dc.metrics(core)["mdd"]
    dd_hb = dc.metrics(hb)["mdd"]
    dd_mix = dc.metrics(dc.blend(core, hb, 0.5))["mdd"]
    assert dd_core <= dd_mix <= dd_hb


def test_drawdown_shrinks_monotonically_as_core_shrinks():
    """The claim the recommendation rests on. If this fails, the bucket
    split is not a reliable drawdown lever and the advice is wrong."""
    px = _prices()
    core = dc.simulate_core(px, dc.LIVE_CORE_W)
    hb = _flat(px.index)
    dds = [dc.metrics(dc.blend(core, hb, cf))["mdd"]
           for cf in (1.0, 0.9, 0.8, 0.7, 0.6)]
    assert dds == sorted(dds), f"MaxDD must get shallower as core shrinks: {dds}"


def test_blend_is_linear_when_rebalancing_is_off():
    """With no rebalancing and no costs the blend is a static two-asset
    mix; pins the return accounting exactly."""
    px = _prices(n=300)
    core = dc.simulate_core(px, dc.LIVE_CORE_W)
    hb = _flat(px.index)
    got = dc.blend(core, hb, 0.6, tc_bps=0.0, rebal_trigger=99.0)
    want = 0.6 * core / core.iloc[0] + 0.4 * hb / hb.iloc[0]
    pd.testing.assert_series_equal(got, want, rtol=1e-9)


def test_blend_charges_cost_when_it_rebalances():
    """Use a core that definitely drifts past the +-5pp band -- a mild
    random walk may never trigger a rebalance, which would make this pass
    for the wrong reason (zero rebalances, zero cost, equal results)."""
    idx = pd.bdate_range("2010-01-04", periods=800)
    core = pd.Series(np.cumprod(np.full(800, 1.001)), index=idx)  # +0.1%/day
    hb = _flat(idx)
    free = dc.blend(core, hb, 0.7, tc_bps=0.0).iloc[-1]
    paid = dc.blend(core, hb, 0.7, tc_bps=200.0).iloc[-1]
    assert paid < free, "no rebalance was triggered; the test proves nothing"


# ── Core simulation convention ────────────────────────────────────────────

def test_core_matches_manual_buy_and_hold_without_rebalancing():
    px = _prices(n=200)
    nav = dc.simulate_core(px, dc.LIVE_CORE_W)
    # Re-run with rebalancing effectively disabled by using the module's
    # own constants patched at call time is not supported, so compare the
    # first rebalance-free stretch instead: day 1 return must be the
    # weighted asset return exactly.
    r1 = sum(dc.LIVE_CORE_W[k] * (px[k].iloc[1] / px[k].iloc[0] - 1)
             for k in dc.LIVE_CORE_W)
    assert nav.iloc[1] / nav.iloc[0] - 1 == pytest.approx(r1, rel=1e-12)


def test_pre_ipo_avgo_weight_redistributes_proportionally():
    pre = dc.eff_weights(dc.LIVE_CORE_W, pd.Timestamp("2005-01-03"))
    assert "AVGO" not in pre
    assert sum(pre.values()) == pytest.approx(1.0)
    assert pre["Gold"] / pre["LLY"] == pytest.approx(0.25 / 0.35)
    assert dc.eff_weights(dc.LIVE_CORE_W, pd.Timestamp("2015-01-02")) == dc.LIVE_CORE_W


def test_core_nav_length_matches_price_index():
    px = _prices(n=137)
    assert len(dc.simulate_core(px, dc.LIVE_CORE_W)) == len(px)


# ── Metrics / projection ──────────────────────────────────────────────────

def test_calmar_and_mdd_definitions():
    idx = pd.bdate_range("2010-01-04", periods=900)
    nav = pd.Series(np.linspace(1.0, 2.5, 900), index=idx)
    nav.iloc[400:460] *= 0.75
    m = dc.metrics(nav)
    assert m["mdd"] < 0
    assert m["calmar"] == pytest.approx(m["cagr"] / abs(m["mdd"]))


def test_metrics_scale_invariant():
    idx = pd.bdate_range("2010-01-04", periods=400)
    rng = np.random.default_rng(5)
    nav = pd.Series(np.cumprod(1 + rng.normal(0.0004, 0.01, 400)), index=idx)
    a, b = dc.metrics(nav), dc.metrics(nav * 1000)
    for k in ("cagr", "vol", "sharpe", "mdd", "calmar"):
        assert a[k] == pytest.approx(b[k])


def test_future_value_contributions_and_growth():
    # Zero return: it is just the contributions plus the principal.
    fv = dc.fv_with_contributions(100_000, 0.0, 10, 1_000)
    assert fv == pytest.approx(100_000 + 1_000 * 120)
    # Positive return must beat the zero-return case.
    assert dc.fv_with_contributions(100_000, 0.07, 10, 1_000) > fv
    # No contributions: plain compounding.
    assert dc.fv_with_contributions(100_000, 0.07, 10, 0) == pytest.approx(
        100_000 * 1.07 ** 10, rel=1e-6)
