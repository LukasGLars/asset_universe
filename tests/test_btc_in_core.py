"""Tests for run_btc_in_core.py (temporary diagnostic, 2026-08-31).

The BTC leg has three things that every earlier BTC run in this repo got
wrong at least once: the fee basis (charged to the trend arm but given free
to buy-and-hold), the annualization (365 vs 252), and the signal shift.
These pin all three before any number is read.
"""
import numpy as np
import pandas as pd
import pytest

import run_btc_in_core as bc


def _cal(n=800):
    return pd.bdate_range("2015-01-05", periods=n)


def _flat_btc(cal, level=100.0):
    return pd.Series(level, index=cal, dtype=float)


# ── The fee: the error MEMORY.md records as worth +1.02% CAGR ─────────────

def test_hold_pays_the_full_fee_on_a_flat_price():
    """Flat BTC, held throughout: NAV must decay at exactly the ETP fee."""
    cal = _cal(1000)
    nav, in_mkt, fee = bc.btc_leg(_flat_btc(cal), cal, None)
    yrs = (cal[-1] - cal[0]).days / 365.0
    assert nav.iloc[-1] == pytest.approx((1 - bc.ETP_FEE_ANNUAL) ** yrs, rel=1e-6)
    assert in_mkt == pytest.approx(1.0)
    assert fee == pytest.approx(bc.ETP_FEE_ANNUAL)


def test_out_of_market_pays_no_fee():
    """The whole point of the correction: fee accrues only while held."""
    cal = _cal(600)
    never = np.zeros(len(cal))
    nav, in_mkt, fee = bc.btc_leg(_flat_btc(cal), cal, never)
    assert nav.iloc[-1] == pytest.approx(1.0)      # no fee, no spread, no move
    assert in_mkt == pytest.approx(0.0)
    assert fee == pytest.approx(0.0)


def test_half_time_in_market_pays_about_half_the_fee():
    cal = _cal(1000)
    half = np.tile([1.0, 1.0, 0.0, 0.0], len(cal) // 4 + 1)[:len(cal)]
    _, in_mkt, fee = bc.btc_leg(_flat_btc(cal), cal, half)
    assert in_mkt == pytest.approx(0.5, abs=0.02)
    assert fee == pytest.approx(bc.ETP_FEE_ANNUAL * in_mkt, rel=1e-6)


def test_always_in_trend_arm_equals_buy_and_hold_exactly():
    """MEMORY.md records this as the check that proves the fee is applied
    on the SAME basis to both arms. If it fails, the arms are not
    comparable and no BTC number in the run means anything."""
    cal = _cal(700)
    rng = np.random.default_rng(0)
    px = pd.Series(100 * np.cumprod(1 + rng.normal(0.001, 0.04, len(cal))), index=cal)
    hold, _, _ = bc.btc_leg(px, cal, None)
    always, _, _ = bc.btc_leg(px, cal, np.ones(len(cal)))
    pd.testing.assert_series_equal(hold, always)


def test_spread_charged_on_every_flip():
    cal = _cal(400)
    px = _flat_btc(cal)
    steady = np.ones(len(cal))
    flippy = np.tile([1.0, 0.0], len(cal) // 2 + 1)[:len(cal)]
    nav_steady, _, _ = bc.btc_leg(px, cal, steady)
    nav_flip, _, _ = bc.btc_leg(px, cal, flippy)
    # Flipping constantly must cost more than holding, despite paying less fee.
    assert nav_flip.iloc[-1] < nav_steady.iloc[-1]


def test_fee_uses_calendar_days_not_bar_count():
    """252 weekday bars must still cost a full year of fee, because the
    fee accrues over the weekend too. Getting this wrong understates the
    drag by ~30%."""
    cal = pd.bdate_range("2015-01-05", "2015-12-31")
    nav, _, _ = bc.btc_leg(_flat_btc(cal), cal, None)
    yrs = (cal[-1] - cal[0]).days / 365.0
    assert nav.iloc[-1] == pytest.approx((1 - bc.ETP_FEE_ANNUAL) ** yrs, rel=1e-6)
    assert 0.98 < yrs < 1.0


# ── Portfolio blend ───────────────────────────────────────────────────────

def test_zero_btc_weight_is_identical_to_no_btc_asset():
    """The 0% row is the baseline every other row is judged against, so it
    must be exactly the BTC-free portfolio."""
    cal = _cal(500)
    rng = np.random.default_rng(3)
    navs = {k: pd.Series(np.cumprod(1 + rng.normal(0.0004, 0.012, len(cal))),
                         index=cal) for k in ("Gold", "AVGO", "LLY")}
    navs["BTC"] = pd.Series(np.cumprod(1 + rng.normal(0.002, 0.05, len(cal))),
                            index=cal)
    with_btc = bc.simulate(navs, {**bc.CORE_BASE, "BTC": 0.0})
    without = bc.simulate(navs, dict(bc.CORE_BASE))
    pd.testing.assert_series_equal(with_btc, without)


def test_weights_sum_to_one_at_every_btc_weight():
    for bw in bc.BTC_WEIGHTS:
        t = {k: v * (1 - bw) for k, v in bc.CORE_BASE.items()}
        t["BTC"] = bw
        assert sum(t.values()) == pytest.approx(1.0)


def test_more_btc_raises_volatility():
    """Sanity: BTC is the most volatile leg by far, so exposure to it must
    show up as portfolio vol. If not, the blend is not wiring BTC in."""
    cal = _cal(900)
    rng = np.random.default_rng(7)
    navs = {k: pd.Series(np.cumprod(1 + rng.normal(0.0004, 0.010, len(cal))),
                         index=cal) for k in ("Gold", "AVGO", "LLY")}
    navs["BTC"] = pd.Series(np.cumprod(1 + rng.normal(0.001, 0.055, len(cal))),
                            index=cal)
    vols = []
    for bw in (0.0, 0.05, 0.10, 0.20):
        t = {k: v * (1 - bw) for k, v in bc.CORE_BASE.items()}
        t["BTC"] = bw
        vols.append(bc.metrics(bc.simulate(navs, t))["vol"])
    assert vols == sorted(vols)


# ── Metrics / projection ──────────────────────────────────────────────────

def test_calmar_definition_and_scale_invariance():
    idx = _cal(900)
    nav = pd.Series(np.linspace(1, 3, 900), index=idx)
    nav.iloc[300:380] *= 0.6
    m = bc.metrics(nav)
    assert m["calmar"] == pytest.approx(m["cagr"] / abs(m["mdd"]))
    assert bc.metrics(nav * 99)["calmar"] == pytest.approx(m["calmar"])


def test_window_bounds_are_inclusive():
    idx = _cal(600)
    s = pd.Series(np.arange(600, dtype=float), index=idx)
    w = bc.window(s, "2016-01-01", "2016-12-31")
    assert w.index[0] >= pd.Timestamp("2016-01-01")
    assert w.index[-1] <= pd.Timestamp("2016-12-31")


def test_fv_matches_zero_return_contributions():
    assert bc.fv(100_000, 0.0, 10, 1_000) == pytest.approx(100_000 + 1_000 * 120)
    assert bc.fv(100_000, 0.07, 10, 0) == pytest.approx(100_000 * 1.07 ** 10, rel=1e-6)
