"""Tests for run_derisk_signal_test.py (temporary diagnostic, 2026-08-31).

The point of these is narrow and specific: the AVGO 200d guard was retired
because `signal[i]` was applied to `ret[i]`, and nobody had a test that
would have caught it. These pin the timing plumbing of the de-risk overlay
BEFORE any result is read, so a favourable number can't be trusted on vibes.
"""
import numpy as np
import pandas as pd
import pytest

import run_derisk_signal_test as rd


def _prices(n=400, seed=0):
    """Deterministic 3-asset price panel on business days from 2010 (post
    AVGO-IPO, so no pre-IPO redistribution muddies the timing tests)."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-04", periods=n)
    data = {}
    for k in ("Gold", "AVGO", "LLY"):
        data[k] = 100.0 * np.cumprod(1.0 + rng.normal(0.0003, 0.01, n))
    return pd.DataFrame(data, index=idx)


# ── Timing: the thing that killed the guard ───────────────────────────────

def test_signal_never_affects_its_own_day_return():
    """derisk[k] must move the weights held from close(k) to close(k+1).
    Returns up to and including day k must be byte-identical to the
    all-False path."""
    px = _prices()
    n  = len(px)
    k  = 200

    base = np.zeros(n, dtype=bool)
    one  = base.copy()
    one[k] = True

    nav_base = rd.simulate(px, base, 1.0, 0.0)
    nav_one  = rd.simulate(px, one,  1.0, 0.0)

    pd.testing.assert_series_equal(nav_base.iloc[:k + 1], nav_one.iloc[:k + 1])
    assert nav_base.iloc[k + 1] != nav_one.iloc[k + 1], (
        "flipping derisk[k] must change the return realised on day k+1"
    )


def test_last_day_signal_is_inert():
    """A signal on the final bar has no return left to act on. If flipping
    it changes the NAV, the shift is off by one in the other direction."""
    px = _prices()
    n  = len(px)
    a  = np.zeros(n, dtype=bool)
    b  = a.copy()
    b[-1] = True
    pd.testing.assert_series_equal(
        rd.simulate(px, a, 1.0, 0.0), rd.simulate(px, b, 1.0, 0.0)
    )


def test_lookahead_twin_actually_looks_ahead():
    """Construct a signal that fires exactly on the day before a crash.
    The honest run should dodge it; the lookahead run is handed the crash
    day itself and must differ. If they agree, `lookahead` is a no-op and
    the self-check in main() proves nothing."""
    px = _prices(n=300).copy()
    crash = 150
    px.iloc[crash:, :] *= 0.70          # -30% gap on day `crash`

    n = len(px)
    honest_flags = np.zeros(n, dtype=bool)
    honest_flags[crash - 1] = True       # known at close(crash-1)

    nav_h = rd.simulate(px, honest_flags, 1.0, 0.0, lookahead=False)
    nav_l = rd.simulate(px, honest_flags, 1.0, 0.0, lookahead=True)

    # Honest: flat in cash across the crash day -> no -30%.
    assert nav_h.iloc[crash] / nav_h.iloc[crash - 1] > 0.99
    # Lookahead consumes flags[crash-1] on day crash-1 instead, so it is
    # fully invested into the crash and must end lower.
    assert nav_l.iloc[crash] < nav_h.iloc[crash]


# ── Signal construction ───────────────────────────────────────────────────

def test_credit_widening_is_bps_and_lagged():
    cal = pd.bdate_range("2010-01-04", periods=60)
    # BAA10Y in percentage points: flat 2.00, steps to 3.00 at index 30.
    lvl = pd.Series(2.0, index=cal)
    lvl.iloc[30:] = 3.0

    w = rd.credit_widening_bps(lvl, cal, lookback=5, macro_lag=0)
    assert w.iloc[34] == pytest.approx(100.0)   # 1.00pp -> 100bp
    assert w.iloc[29] == pytest.approx(0.0)

    w_lag = rd.credit_widening_bps(lvl, cal, lookback=5, macro_lag=1)
    # One extra publication day of delay shifts the whole signal right.
    assert w_lag.iloc[35] == pytest.approx(w.iloc[34])


def test_credit_widening_never_uses_future_levels():
    """Truncating the series after date t must not change the signal at t."""
    cal = pd.bdate_range("2010-01-04", periods=80)
    rng = np.random.default_rng(1)
    lvl = pd.Series(2.0 + np.cumsum(rng.normal(0, 0.02, 80)), index=cal)

    full = rd.credit_widening_bps(lvl, cal, lookback=10)
    t    = 60
    trunc = rd.credit_widening_bps(lvl.iloc[:t + 1], cal[:t + 1], lookback=10)
    assert full.iloc[t] == pytest.approx(trunc.iloc[t])


def test_vix_percentile_is_point_in_time_not_full_sample():
    """The whole reason to use an expanding quantile. A full-sample
    quantile would change when later data is appended; this must not."""
    cal = pd.bdate_range("2005-01-03", periods=1200)
    rng = np.random.default_rng(2)
    vix = pd.Series(15 + np.abs(rng.normal(0, 5, 1200)), index=cal)

    t     = 900
    full  = rd.vix_expanding_pctl(vix, cal, 0.90, min_obs=756)
    trunc = rd.vix_expanding_pctl(vix.iloc[:t + 1], cal[:t + 1], 0.90, min_obs=756)
    assert full.iloc[t] == pytest.approx(trunc.iloc[t])

    # And it must genuinely differ from the full-sample quantile, or the
    # distinction is cosmetic.
    assert full.iloc[t] != pytest.approx(vix.quantile(0.90))


def test_vix_percentile_is_nan_before_min_obs():
    cal = pd.bdate_range("2005-01-03", periods=1000)
    vix = pd.Series(np.linspace(10, 40, 1000), index=cal)
    p = rd.vix_expanding_pctl(vix, cal, 0.90, min_obs=756)
    assert p.iloc[:755].isna().all()
    assert p.iloc[756:].notna().all()


# ── Portfolio mechanics ───────────────────────────────────────────────────

def test_static_path_matches_manual_buy_and_hold_when_no_rebalancing():
    """With a huge drift trigger and zero costs, the static sim is just a
    weighted buy-and-hold. Anchors the accounting."""
    px = _prices(n=120)
    nav = rd.simulate(px, None, 0.0, 0.0, tc_bps=0.0, rebal_trigger=99.0)
    manual = sum(rd.BASE_W[k] * px[k] / px[k].iloc[0] for k in rd.BASE_W)
    assert nav.iloc[-1] == pytest.approx(manual.iloc[-1], rel=1e-9)


def test_full_derisk_holds_only_cash():
    """reduction=1.0 with an always-on signal must earn the cash rate and
    nothing else, regardless of what the assets did."""
    px = _prices(n=250)
    flags = np.ones(len(px), dtype=bool)
    nav = rd.simulate(px, flags, 1.0, 0.02, tc_bps=0.0)
    daily = (1.02) ** (1 / 252) - 1
    assert nav.iloc[-1] == pytest.approx((1 + daily) ** (len(px) - 1), rel=1e-9)


def test_derisk_charges_turnover_on_every_state_flip():
    """A whipsawing signal must cost more than a signal that fires once.
    If costs aren't charged on target changes the overlay gets a free
    option and any result is meaningless."""
    px = _prices(n=300)
    n  = len(px)
    once = np.zeros(n, dtype=bool)
    once[100:200] = True                      # 1 entry, 1 exit
    whip = np.zeros(n, dtype=bool)
    whip[100:200:2] = True                    # 50 round trips

    nav_once = rd.simulate(px, once, 1.0, 0.0, tc_bps=100.0)
    nav_whip = rd.simulate(px, whip, 1.0, 0.0, tc_bps=100.0)
    nav_free = rd.simulate(px, whip, 1.0, 0.0, tc_bps=0.0)
    assert nav_whip.iloc[-1] < nav_free.iloc[-1]
    assert nav_whip.iloc[-1] < nav_once.iloc[-1]


def test_reduction_is_exactly_a_linear_blend_of_assets_and_cash():
    """With rebalancing switched off and zero costs, a `reduction` of r is
    by construction the static blend (1-r) x fully-invested + r x cash.
    This is the exact accounting identity; monotonicity across r is NOT a
    valid invariant once drift-rebalancing is on (rebalancing changes the
    compounding path), so pin the identity instead of a vibe."""
    px = _prices(n=250)
    flags = np.ones(len(px), dtype=bool)
    kw = dict(tc_bps=0.0, rebal_trigger=99.0)

    nav_assets = rd.simulate(px, flags, 0.0, 0.0, **kw)
    nav_cash   = rd.simulate(px, flags, 1.0, 0.0, **kw)
    assert nav_cash.iloc[-1] == pytest.approx(1.0)   # 0% cash yield

    for r in (0.25, 0.50, 0.75):
        blended = rd.simulate(px, flags, r, 0.0, **kw)
        expected = (1 - r) * nav_assets + r * nav_cash
        pd.testing.assert_series_equal(blended, expected, rtol=1e-9)


def test_pre_ipo_avgo_weight_redistributes():
    pre  = rd.eff_core_weights(pd.Timestamp("2005-01-03"), rd.BASE_W)
    assert "AVGO" not in pre
    assert pre["Gold"] + pre["LLY"] == pytest.approx(1.0)
    # Proportional to the surviving Gold:LLY ratio, not 50/50.
    assert pre["Gold"] / pre["LLY"] == pytest.approx(0.25 / 0.35)

    post = rd.eff_core_weights(pd.Timestamp("2015-01-02"), rd.BASE_W)
    assert post == rd.BASE_W


def test_weights_always_sum_to_one():
    for date in (pd.Timestamp("2005-01-03"), pd.Timestamp("2020-01-02")):
        w = rd.eff_core_weights(date, rd.BASE_W)
        assert sum(w.values()) == pytest.approx(1.0)


# ── Metrics ───────────────────────────────────────────────────────────────

def test_calmar_is_cagr_over_maxdd():
    idx = pd.bdate_range("2010-01-04", periods=800)
    nav = pd.Series(np.linspace(1.0, 2.0, 800), index=idx)
    nav.iloc[400:450] *= 0.80                 # a real drawdown
    m = rd.metrics(nav)
    assert m["calmar"] == pytest.approx(m["cagr"] / abs(m["mdd"]))
    assert m["mdd"] < 0


def test_metrics_are_scale_invariant():
    idx = pd.bdate_range("2010-01-04", periods=500)
    rng = np.random.default_rng(3)
    nav = pd.Series(np.cumprod(1 + rng.normal(0.0004, 0.01, 500)), index=idx)
    a, b = rd.metrics(nav), rd.metrics(nav * 37.0)
    for k in ("cagr", "vol", "sharpe", "mdd", "calmar"):
        assert a[k] == pytest.approx(b[k])


def test_window_slices_inclusively():
    idx = pd.bdate_range("2010-01-04", periods=500)
    nav = pd.Series(np.arange(500, dtype=float) + 1, index=idx)
    w = rd.window(nav, "2011-01-03", "2011-06-30")
    assert w.index[0] >= pd.Timestamp("2011-01-03")
    assert w.index[-1] <= pd.Timestamp("2011-06-30")
    assert len(w) > 100
