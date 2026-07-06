from eps_ratio import normalized_eps_ratio


def test_avgo_like_figures_give_normalized_not_gaap_mismatched_ratio():
    # AVGO's real 2026-07-06 numbers -- normalized ratio should land at
    # ~2.39x, not the 3.22x a naive GAAP-trailing/non-GAAP-forward
    # comparison would give.
    quarterly = [1.69, 1.95, 2.05, 2.44]  # TTM = 8.13
    ratio = normalized_eps_ratio(quarterly, 19.39578)
    assert round(ratio, 2) == 2.39


def test_lly_like_figures_barely_move_vs_naive():
    quarterly = [6.31, 7.02, 7.54, 8.55]  # TTM = 29.42
    ratio = normalized_eps_ratio(quarterly, 44.46733)
    assert round(ratio, 2) == 1.51


def test_empty_quarters_returns_none():
    assert normalized_eps_ratio([], 19.4) is None


def test_missing_forward_estimate_returns_none():
    assert normalized_eps_ratio([1.69, 1.95, 2.05, 2.44], None) is None


def test_zero_or_negative_ttm_returns_none():
    assert normalized_eps_ratio([1.0, -1.0, 0.0, 0.0], 19.4) is None
    assert normalized_eps_ratio([-5.0, -5.0], 19.4) is None
