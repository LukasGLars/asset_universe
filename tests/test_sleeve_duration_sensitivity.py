import pytest

from sleeve_duration_sensitivity import aggregate_duration_results, annualize, best_duration_by_median


def test_annualize_compounds_correctly():
    # 10% over 30 days, annualized: (1.10)^(365/30) - 1
    result = annualize(0.10, 30)
    assert result == pytest.approx(1.10 ** (365 / 30) - 1)


def test_annualize_same_rate_different_windows_ranks_shorter_higher():
    # The exact scenario this exists to prevent: same raw return, but a
    # shorter window annualizes to a much higher rate.
    short = annualize(0.05, 15)
    long = annualize(0.05, 90)
    assert short > long


def test_annualize_total_loss_returns_none():
    assert annualize(-1.5, 30) is None  # more than -100%, nonsensical to annualize


def test_annualize_zero_days_returns_none():
    assert annualize(0.05, 0) is None


def test_aggregate_pools_median_of_medians_and_weighted_win_rate():
    per_ticker = {
        30: [(0.03, 0.60, 100), (0.05, 0.70, 200)],
    }
    result = aggregate_duration_results(per_ticker)
    assert result[30]["median"] == 0.04  # median of [0.03, 0.05]
    assert result[30]["annualized"] == pytest.approx(1.04 ** (365 / 30) - 1)
    assert round(result[30]["win_rate"], 4) == round((0.60 * 100 + 0.70 * 200) / 300, 4)
    assert result[30]["n_total"] == 300
    assert result[30]["n_tickers"] == 2


def test_aggregate_empty_duration_returns_none_fields():
    result = aggregate_duration_results({30: []})
    assert result[30] == {"median": None, "annualized": None, "win_rate": None,
                           "n_total": 0, "n_tickers": 0}


def test_aggregate_handles_multiple_durations_independently():
    per_ticker = {
        15: [(0.02, 0.55, 50)],
        30: [(0.04, 0.65, 80)],
        60: [(0.06, 0.70, 40)],
    }
    result = aggregate_duration_results(per_ticker)
    assert result[15]["median"] == 0.02
    assert result[30]["median"] == 0.04
    assert result[60]["median"] == 0.06


def test_best_duration_by_median_ranks_on_annualized_not_raw():
    # Raw medians rise with duration (15d < 30d < 60d < 90d), which would
    # trivially favor 90d on raw numbers alone -- but annualized, a shorter
    # window compounding to a similar or better rate should win instead.
    # 15d +2% raw annualizes far higher than 90d +9% raw.
    per_ticker = {
        15: [(0.02, 0.55, 50)],
        90: [(0.09, 0.70, 40)],
    }
    aggregated = aggregate_duration_results(per_ticker)
    assert aggregated[15]["annualized"] > aggregated[90]["annualized"]
    assert best_duration_by_median(aggregated) == 15


def test_best_duration_by_median_ignores_none_entries():
    aggregated = {
        15: {"median": None, "annualized": None, "win_rate": None, "n_total": 0, "n_tickers": 0},
        30: {"median": 0.034, "annualized": 0.55, "win_rate": 0.61, "n_total": 243, "n_tickers": 8},
    }
    assert best_duration_by_median(aggregated) == 30


def test_best_duration_by_median_all_none_returns_none():
    aggregated = {15: {"median": None, "annualized": None, "win_rate": None, "n_total": 0, "n_tickers": 0}}
    assert best_duration_by_median(aggregated) is None
