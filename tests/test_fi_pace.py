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
