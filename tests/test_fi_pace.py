import math

from asset_universe.portfolio import (
    future_value_with_contributions,
    years_to_reach_target,
    _solve_required_cagr,
)


def test_required_cagr_zero_contribution_matches_pure_compounding():
    # Regression: monthly_contribution=0 must reproduce the exact prior
    # formula, (target/tpv)**(1/years) - 1.
    tpv, target, years = 1_000_000.0, 5_000_000.0, 10.0
    expected = (target / tpv) ** (1 / years) - 1
    assert math.isclose(_solve_required_cagr(tpv, target, years, 0.0), expected, rel_tol=1e-9)


def test_required_cagr_with_contributions_is_lower_than_without():
    # The whole point of the fix: ongoing contributions must lower the bar,
    # not leave it unchanged. This was previously silently ignored.
    tpv, target, years = 1_090_000.0, 12_930_000.0, 11.1
    no_contrib = _solve_required_cagr(tpv, target, years, 0.0)
    with_contrib = _solve_required_cagr(tpv, target, years, 6000.0)
    assert with_contrib < no_contrib
    # Sanity-check the magnitude is in the right ballpark (confirmed
    # 2026-07-02: ~24.9% -> ~22.1% at similar inputs), not just "lower".
    assert 0.20 < with_contrib < 0.23


def test_future_value_with_contributions_zero_contribution_is_pure_compounding():
    tpv, rate, years = 1_000_000.0, 0.15, 10.0
    fv = future_value_with_contributions(tpv, rate, years, 0.0)
    assert math.isclose(fv, tpv * (1 + rate) ** years, rel_tol=1e-9)


def test_future_value_with_contributions_adds_meaningful_value():
    # 6,000 kr/month for ~11 years is real money -- confirm it's not a
    # rounding-level effect (silently dropping it would understate the
    # true projection).
    tpv, rate, years = 1_000_000.0, 0.20, 11.0
    fv_no_contrib = future_value_with_contributions(tpv, rate, years, 0.0)
    fv_with_contrib = future_value_with_contributions(tpv, rate, years, 6000.0)
    assert fv_with_contrib - fv_no_contrib > 1_000_000.0


def test_years_to_reach_target_zero_when_already_there():
    assert years_to_reach_target(10_000_000.0, 0.10, 6000.0, 5_000_000.0) == 0.0


def test_years_to_reach_target_roundtrips_with_future_value():
    tpv, rate, monthly = 1_000_000.0, 0.20, 6000.0
    target = future_value_with_contributions(tpv, rate, 8.0, monthly)
    yrs = years_to_reach_target(tpv, rate, monthly, target)
    assert math.isclose(yrs, 8.0, abs_tol=1e-3)
