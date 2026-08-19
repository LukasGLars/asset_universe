import math

import pandas as pd
import pytest

import asset_universe.portfolio as portfolio
from asset_universe.portfolio import (
    future_value_with_contributions,
    years_to_reach_target,
    _solve_required_cagr,
)


_FI_CFG = {
    "fi": {
        "start_date": "2025-07-21",
        "start_value_sek": 925983,
        "target_sek": 12934706,
        "years": 12,
        "monthly_contribution_sek": 6000,
    }
}


def _snap(rows: list[dict]) -> pd.DataFrame:
    """Build a snapshot()-shaped DataFrame from partial row dicts (only the
    columns fi_pace() actually reads: name, shares, value_sek)."""
    defaults = {"ticker": "", "bucket": "reactor_core", "currency": "SEK",
                "price_local": None, "fx_rate": None, "price_sek": None, "weight": 0.0}
    return pd.DataFrame([{**defaults, **r} for r in rows])


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


# ── fi_pace(): TPV = sum(snapshot().value_sek), nothing else ────────────────
# (2026-07-24 -- reverted from a dedicated Google Sheet TPV cell: broker-
# screenshot reconciliation showed that cell lagged the real balance more
# than the position sum does, once idle Reactor Core cash and War Chest
# were correctly tracked in config/portfolio.toml. The position sum is
# fresher because it's built from data synced daily, not a separately-
# maintained cell nothing in this codebase ever writes to.)

def test_fi_pace_sums_snapshot_value_sek(monkeypatch, tmp_path):
    snap = _snap([
        {"name": "Gold", "shares": 304, "value_sek": 233162.0},
        {"name": "Eli Lilly", "shares": 14, "value_sek": 161793.0},
        {"name": "Reactor Core Cash", "shares": 0, "value_sek": 30621.0},
    ])
    monkeypatch.setattr(portfolio, "snapshot", lambda data_dir: snap)
    monkeypatch.setattr(portfolio, "_load_portfolio_config", lambda: _FI_CFG)

    result = portfolio.fi_pace(tmp_path)
    assert result["tpv_sek"] == 233162.0 + 161793.0 + 30621.0


def test_fi_pace_raises_when_a_share_position_is_missing_price_data():
    """Missing price data must fail loud, not silently undercount TPV by
    however much that position was worth -- the exact class of silent
    substitution this whole fix has been about avoiding."""
    snap = _snap([
        {"name": "Gold", "shares": 304, "value_sek": 233162.0},
        {"name": "Broadcom", "shares": 80, "value_sek": float("nan")},  # missing price
    ])
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(portfolio, "snapshot", lambda data_dir: snap)
        mp.setattr(portfolio, "_load_portfolio_config", lambda: _FI_CFG)
        try:
            portfolio.fi_pace("unused")
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "Broadcom" in str(exc)


def test_fi_pace_does_not_raise_for_manual_positions_with_zero_shares():
    """A manual (no-ticker) position always has shares=0 and a real
    value_sek from config -- must never trip the missing-price check."""
    snap = _snap([
        {"name": "Gold", "shares": 304, "value_sek": 233162.0},
        {"name": "War Chest", "shares": 0, "value_sek": 0.0},
    ])
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(portfolio, "snapshot", lambda data_dir: snap)
        mp.setattr(portfolio, "_load_portfolio_config", lambda: _FI_CFG)
        result = portfolio.fi_pace("unused")
        assert result["tpv_sek"] == 233162.0


# ── Inflation-indexed FI@50 threshold (2026-08-19) ──────────────────────────
# The trigger is wealth-based and can fire in any year, so the threshold is
# stored in real (base-year) kr and indexed. Flat `target_sek` remains
# supported -- the tests above still use it -- so an older config keeps
# working unchanged.

_FI_CFG_INDEXED = {
    "fi": {
        "start_date": "2025-07-21",
        "start_value_sek": 925983,
        "target_real_sek": 16_150_000,
        "target_base_year": 2026,
        "target_inflation": 0.02,
        "years": 13.223,
        "monthly_contribution_sek": 6000,
    }
}


def test_fi_target_falls_back_to_flat_target_sek():
    # Backwards compatibility: no target_real_sek -> the flat figure, and
    # crucially NOT indexed (a flat config has no base year to index from).
    fi = dict(_FI_CFG["fi"])
    assert portfolio._fi_target(fi, 0.0) == 12934706
    assert portfolio._fi_target(fi, 12.0) == 12934706


def test_fi_target_indexes_forward_at_the_configured_rate():
    fi = _FI_CFG_INDEXED["fi"]
    now = portfolio._fi_target(fi, 0.0)
    ten = portfolio._fi_target(fi, 10.0)
    assert math.isclose(ten, now * 1.02 ** 10, rel_tol=1e-9)
    # Sanity: today's bar has already grown past the 2026 base figure.
    assert now > fi["target_real_sek"]


def test_indexed_target_raises_the_required_cagr_versus_the_stale_flat_one():
    """The whole point of the correction. The retired 12.93M figure was not
    merely unendorsed, it made the dashboard read materially better than
    reality -- required CAGR must go UP once the real, indexed threshold is
    used, on identical TPV and horizon."""
    snap = _snap([{"name": "Gold", "shares": 304, "value_sek": 1_106_368.0}])
    # Same horizon on both sides -- _FI_CFG carries the old years=12, and
    # comparing across different horizons would measure that instead of the
    # threshold change this test is about.
    stale_cfg = {"fi": {**_FI_CFG["fi"], "years": 13.223}}

    def _pace(cfg):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(portfolio, "snapshot", lambda data_dir: snap)
            mp.setattr(portfolio, "_load_portfolio_config", lambda: cfg)
            return portfolio.fi_pace("unused")

    stale   = _pace(stale_cfg)
    indexed = _pace(_FI_CFG_INDEXED)
    assert indexed["required_cagr"] > stale["required_cagr"] + 0.03
    # ~24-25% at these inputs, vs ~20% against the stale target.
    assert 0.23 < indexed["required_cagr"] < 0.27


def test_fi_pace_reports_todays_bar_below_the_horizon_bar():
    snap = _snap([{"name": "Gold", "shares": 304, "value_sek": 1_106_368.0}])
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(portfolio, "snapshot", lambda data_dir: snap)
        mp.setattr(portfolio, "_load_portfolio_config", lambda: _FI_CFG_INDEXED)
        r = portfolio.fi_pace("unused")
    # required_cagr / surplus are solved against the HORIZON bar, which must
    # be the larger of the two -- swapping them would understate the gap by
    # the whole indexing factor.
    assert r["target_now_sek"] < r["target_sek"]
    assert math.isclose(
        r["target_sek"],
        r["target_now_sek"] * 1.02 ** r["years_remaining"],
        rel_tol=1e-9,
    )


def test_years_to_reach_target_default_reproduces_fixed_target_behaviour():
    tpv, rate, monthly, target = 1_000_000.0, 0.20, 6000.0, 5_000_000.0
    assert math.isclose(
        years_to_reach_target(tpv, rate, monthly, target),
        years_to_reach_target(tpv, rate, monthly, target, target_inflation=0.0),
        rel_tol=1e-12,
    )


def test_years_to_reach_target_takes_longer_against_a_moving_bar():
    tpv, rate, monthly, target = 1_000_000.0, 0.20, 6000.0, 5_000_000.0
    fixed  = years_to_reach_target(tpv, rate, monthly, target)
    moving = years_to_reach_target(tpv, rate, monthly, target, target_inflation=0.02)
    assert moving > fixed


def test_years_to_reach_target_never_crosses_a_bar_growing_as_fast():
    """A path that only matches the indexing rate makes no real progress and
    must report inf, not a finite date. The old fixed-target solve would
    happily return one."""
    assert years_to_reach_target(1_000_000.0, 0.02, 0.0, 5_000_000.0,
                                 target_inflation=0.02) == float("inf")


# ── Bucket targets ──────────────────────────────────────────────────────────

def test_bucket_targets_reads_the_config_table():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(portfolio, "_load_portfolio_config",
                   lambda: {"buckets": {"reactor_core": 0.85, "home_base": 0.15,
                                        "war_chest": 0.0}})
        assert portfolio.bucket_targets() == {
            "reactor_core": 0.85, "home_base": 0.15, "war_chest": 0.0}


def test_bucket_targets_empty_when_table_absent():
    """Absent table must yield {} so callers print actuals only. Substituting
    a hardcoded default is the failure mode this table exists to remove."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(portfolio, "_load_portfolio_config", lambda: {"fi": {}})
        assert portfolio.bucket_targets() == {}


def test_live_config_bucket_targets_sum_to_one():
    """Guards the real config file, not a fixture: a split that does not sum
    to 1.0 would silently mis-scale run_outlook_montecarlo.py's blended
    return."""
    assert math.isclose(sum(portfolio.bucket_targets().values()), 1.0, abs_tol=1e-9)
