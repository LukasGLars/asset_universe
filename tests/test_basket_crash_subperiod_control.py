"""Tests for run_basket_crash_subperiod_control.py (temporary, 2026-09-17).

The whole point of this diagnostic is the date-matched control, so that is
what gets pinned: if `universe_median_forward` is wrong, the excess number is
wrong and the verdict is meaningless either way it lands.
"""
import numpy as np
import pandas as pd
import pytest

import run_basket_crash_subperiod_control as bc
import run_sleeve_entry_reconstruction as recon


def _series(start="2015-01-05", n=400, step=0.001, p0=100.0):
    idx = pd.bdate_range(start, periods=n)
    return pd.Series(p0 * np.cumprod(np.full(n, 1 + step)), index=idx)


def _universe(k=20, step=0.001):
    return {f"T{i}": ("equities", _series(step=step)) for i in range(k)}


# ── The control ───────────────────────────────────────────────────────────

def test_universe_median_matches_a_known_constant_drift():
    """Every name compounding at the same rate: the universe median forward
    return must equal that rate over the horizon, within the calendar/bday
    slack `forward_return` allows."""
    uni = _universe(k=12, step=0.001)
    d = pd.Timestamp("2015-03-02")
    out = bc.universe_median_forward(uni, [d], 21)
    one = recon.forward_return(uni["T0"][1], d, 21)
    assert out[d] == pytest.approx(one, rel=1e-9)
    assert out[d] > 0


def test_excess_is_zero_when_the_bucket_is_the_universe():
    """A 'signal' that picks names behaving exactly like the universe must
    show zero excess. This is the failure mode the control exists to catch:
    a bucket that only looks good because everything bounced."""
    uni = _universe(k=10, step=0.002)
    d = pd.Timestamp("2015-03-02")
    umed = bc.universe_median_forward(uni, [d], 21)[d]
    picked = recon.forward_return(uni["T3"][1], d, 21)
    assert picked - umed == pytest.approx(0.0, abs=1e-12)


def test_excess_is_positive_only_when_the_pick_outperforms():
    idx = pd.bdate_range("2015-01-05", periods=400)
    uni = {f"T{i}": ("equities", pd.Series(100 * np.cumprod(np.full(400, 1.001)), index=idx))
           for i in range(9)}
    uni["WIN"] = ("equities", pd.Series(100 * np.cumprod(np.full(400, 1.004)), index=idx))
    d = pd.Timestamp("2015-03-02")
    umed = bc.universe_median_forward(uni, [d], 21)[d]
    assert recon.forward_return(uni["WIN"][1], d, 21) - umed > 0
    assert recon.forward_return(uni["T0"][1], d, 21) - umed == pytest.approx(0.0, abs=1e-12)


def test_control_returns_nan_below_min_n():
    """Too few usable names on a date must yield NaN, not a median of two —
    otherwise a thin date silently drives the excess."""
    uni = _universe(k=3)
    d = pd.Timestamp("2015-03-02")
    assert np.isnan(bc.universe_median_forward(uni, [d], 21)[d])


def test_control_is_computed_per_date_not_pooled():
    uni = _universe(k=12, step=0.001)
    d1, d2 = pd.Timestamp("2015-03-02"), pd.Timestamp("2016-01-04")
    out = bc.universe_median_forward(uni, [d1, d2], 21)
    assert set(out) == {d1, d2}
    assert all(v == v for v in out.values())


# ── Stats helper ──────────────────────────────────────────────────────────

def test_stats_reports_median_and_win_rate():
    s = bc._stats([0.10, -0.05, 0.02, 0.30, -0.20, 0.01, 0.07, -0.03, 0.05, 0.12])
    assert s["n"] == 10
    assert s["median"] == pytest.approx(0.035)
    assert s["win"] == pytest.approx(0.7)


def test_stats_refuses_below_min_n():
    s = bc._stats([0.1] * (bc.MIN_N - 1))
    assert np.isnan(s["median"]) and np.isnan(s["win"])


# ── Era config ────────────────────────────────────────────────────────────

def test_covid_is_its_own_era_and_is_excludable():
    """Criterion 1 turns on excluding 2020 wholesale, so 2020 must sit in
    exactly one era and that era must be the one named COVID_ERA."""
    names = [n for n, _, _ in bc.ERAS]
    assert bc.COVID_ERA in names
    covid = next(e for e in bc.ERAS if e[0] == bc.COVID_ERA)
    assert pd.Timestamp(covid[1]) <= pd.Timestamp("2020-03-23") <= pd.Timestamp(covid[2])
    others = [e for e in bc.ERAS if e[0] != bc.COVID_ERA]
    for _, a, b in others:
        in_a = a is None or pd.Timestamp("2020-03-23") >= pd.Timestamp(a)
        in_b = b is None or pd.Timestamp("2020-03-23") <= pd.Timestamp(b)
        assert not (in_a and in_b), "2020 leaks into a second era"


def test_eras_do_not_overlap_and_are_ordered():
    bounds = [(pd.Timestamp(a), pd.Timestamp(b) if b else pd.Timestamp("2100-01-01"))
              for _, a, b in bc.ERAS]
    for (a1, b1), (a2, b2) in zip(bounds, bounds[1:]):
        assert b1 < a2, "eras overlap"


def test_horizons_include_the_headline_duration():
    assert 21 in bc.HORIZONS, "21d is the duration the +4.41% claim was quoted at"
