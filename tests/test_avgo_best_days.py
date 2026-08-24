import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from run_avgo_best_days import cagr_from_returns


def test_cagr_recovers_a_known_doubling():
    """Doubling over exactly 2 years is sqrt(2)-1 per year."""
    rets = pd.Series([0.0] * 100)
    rets.iloc[0] = 1.0                       # +100% once
    assert abs(cagr_from_returns(rets, 2.0) - (2 ** 0.5 - 1)) < 1e-9


def test_removing_the_single_best_day_lowers_cagr():
    rng = np.random.default_rng(1)
    idx = pd.bdate_range("2015-01-01", periods=500)
    rets = pd.Series(rng.normal(0.001, 0.02, 500), index=idx)
    yrs = 500 / 252
    full = cagr_from_returns(rets, yrs)
    without_best = cagr_from_returns(rets.drop(rets.idxmax()), yrs)
    assert without_best < full


def test_removing_the_single_worst_day_raises_cagr():
    rng = np.random.default_rng(2)
    idx = pd.bdate_range("2015-01-01", periods=500)
    rets = pd.Series(rng.normal(0.001, 0.02, 500), index=idx)
    yrs = 500 / 252
    full = cagr_from_returns(rets, yrs)
    without_worst = cagr_from_returns(rets.drop(rets.idxmin()), yrs)
    assert without_worst > full


def test_concentrated_series_collapses_when_its_few_good_days_are_removed():
    """A deliberately concentrated series must show the effect strongly --
    guards against a metric that cannot detect concentration at all."""
    idx = pd.bdate_range("2015-01-01", periods=500)
    rets = pd.Series(0.0, index=idx)
    rets.iloc[[10, 20, 30, 40, 50]] = 0.40   # five huge days carry everything
    yrs = 500 / 252
    full = cagr_from_returns(rets, yrs)
    stripped = cagr_from_returns(rets.drop(rets.sort_values(ascending=False).index[:5]), yrs)
    assert full > 0.5
    assert abs(stripped) < 1e-9              # nothing left at all


def test_log_shares_of_top_days_sum_correctly():
    """Share-of-growth accounting must be additive in log space."""
    rng = np.random.default_rng(3)
    rets = pd.Series(rng.normal(0.002, 0.02, 400))
    rets = rets[rets > -0.99]
    log_tot = float(np.log1p(rets).sum())
    order = rets.sort_values(ascending=False)
    top = float(np.log1p(order.iloc[:50]).sum())
    rest = float(np.log1p(order.iloc[50:]).sum())
    assert abs((top + rest) - log_tot) < 1e-9


def test_diversified_series_is_not_flagged_as_concentrated():
    """Mirror of the concentration test: an even series should retain most
    of its CAGR after dropping 5 days."""
    idx = pd.bdate_range("2015-01-01", periods=500)
    rets = pd.Series(0.002, index=idx)       # perfectly even growth
    yrs = 500 / 252
    full = cagr_from_returns(rets, yrs)
    stripped = cagr_from_returns(rets.drop(rets.index[:5]), yrs)
    assert stripped / full > 0.95
