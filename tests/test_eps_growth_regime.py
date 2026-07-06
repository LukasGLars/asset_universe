import datetime as dt

import pytest

from eps_growth_regime import (
    capped_forward_return,
    diversity_flag,
    label_regimes,
    regime_label,
    summarize_returns,
    ttm_series,
    yoy_growth_series,
)


def test_ttm_series_rolling_sum():
    q = {
        dt.date(2024, 3, 31): 1.0,
        dt.date(2024, 6, 30): 1.0,
        dt.date(2024, 9, 30): 1.0,
        dt.date(2024, 12, 31): 1.0,
        dt.date(2025, 3, 31): 2.0,
    }
    ttm = ttm_series(q)
    assert ttm[dt.date(2024, 12, 31)] == 4.0
    assert ttm[dt.date(2025, 3, 31)] == 5.0  # drops the 2024-03-31 quarter, adds 2025-03-31
    assert dt.date(2024, 9, 30) not in ttm  # fewer than 4 quarters available


def test_yoy_growth_matches_within_tolerance():
    ttm = {
        dt.date(2024, 3, 28): 4.0,   # slightly off-calendar from the date below (fiscal drift)
        dt.date(2025, 3, 31): 6.0,
    }
    growth = yoy_growth_series(ttm)
    assert growth[dt.date(2025, 3, 31)] == pytest.approx(0.5)


def test_yoy_growth_skips_when_no_prior_within_tolerance():
    ttm = {
        dt.date(2023, 1, 1): 4.0,   # way more than 45 days off from a year prior
        dt.date(2025, 3, 31): 6.0,
    }
    growth = yoy_growth_series(ttm)
    assert dt.date(2025, 3, 31) not in growth


def test_yoy_growth_skips_nonpositive_prior():
    ttm = {
        dt.date(2024, 3, 31): -2.0,  # loss year -- division would be nonsensical
        dt.date(2025, 3, 31): 6.0,
    }
    growth = yoy_growth_series(ttm)
    assert dt.date(2025, 3, 31) not in growth


def test_yoy_growth_excludes_anomalous_swings():
    ttm = {
        dt.date(2024, 3, 31): 1.0,
        dt.date(2025, 3, 31): 10.0,  # +900% -- clearly M&A/restructuring, not organic
    }
    growth = yoy_growth_series(ttm, anomaly_threshold=3.0)
    assert dt.date(2025, 3, 31) not in growth


def test_label_regimes_needs_at_least_three_values():
    with pytest.raises(ValueError):
        label_regimes([0.1, 0.2])


def test_regime_label_buckets_correctly():
    p33, p67 = 0.10, 0.30
    assert regime_label(0.05, p33, p67) == "LOW"
    assert regime_label(0.10, p33, p67) == "MID"  # boundary: exactly p33 is MID, not LOW
    assert regime_label(0.20, p33, p67) == "MID"
    assert regime_label(0.30, p33, p67) == "HIGH"  # boundary: exactly p67 is HIGH
    assert regime_label(0.50, p33, p67) == "HIGH"


def test_capped_forward_return_normal_case():
    prices = {
        dt.date(2025, 1, 1): 100.0,
        dt.date(2025, 4, 11): 110.0,  # ~100 days out
    }
    r = capped_forward_return(prices, dt.date(2025, 1, 1), horizon_days=100, regime_end_date=None)
    assert r == pytest.approx(0.10)


def test_capped_forward_return_caps_at_regime_end():
    prices = {
        dt.date(2025, 1, 1): 100.0,
        dt.date(2025, 2, 1): 105.0,   # regime ends here
        dt.date(2025, 4, 11): 150.0,  # would be the 100d point, but must not be used
    }
    r = capped_forward_return(
        prices, dt.date(2025, 1, 1), horizon_days=100,
        regime_end_date=dt.date(2025, 2, 1),
    )
    assert r == pytest.approx(0.05)


def test_capped_forward_return_insufficient_data_returns_none():
    prices = {dt.date(2025, 1, 1): 100.0}
    r = capped_forward_return(prices, dt.date(2025, 1, 1), horizon_days=63, regime_end_date=None)
    assert r is None


def test_capped_forward_return_start_date_not_in_data_uses_next_available():
    prices = {
        dt.date(2025, 1, 2): 100.0,  # market closed on 2025-01-01, first trading day is 01-02
        dt.date(2025, 4, 12): 110.0,
    }
    r = capped_forward_return(prices, dt.date(2025, 1, 1), horizon_days=100, regime_end_date=None)
    assert r == pytest.approx(0.10)


def test_summarize_returns_empty():
    assert summarize_returns([]) == {"n": 0, "median": None, "win_rate": None}


def test_summarize_returns_normal():
    s = summarize_returns([0.10, -0.05, 0.20, 0.02])
    assert s["n"] == 4
    assert s["median"] == pytest.approx(0.06)
    assert s["win_rate"] == 0.75


def test_diversity_flag_thresholds():
    assert diversity_flag(1) == "SINGLE"
    assert diversity_flag(3) == "THIN"
    assert diversity_flag(8) == "MODERATE"
    assert diversity_flag(9) == "ROBUST"
