import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from run_new_capital_deployment_test import (
    find_triggers, mix_forward_return, dip_buy_forward_return,
    BASE_MIX, DEFENSIVE_MIX,
)


def _flat_series(n=300, start=100.0):
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.Series(start, index=idx)


def test_find_triggers_detects_a_real_crash():
    idx = pd.bdate_range("2020-01-01", periods=60)
    prices = pd.Series(100.0, index=idx)
    # Sharp -12% drop over 5 trading days starting day 30
    prices.iloc[30:35] = [100, 96, 92, 90, 88]
    triggers = find_triggers(prices)
    assert len(triggers) >= 1
    assert triggers[0] in prices.index[30:36]


def test_find_triggers_ignores_flat_series():
    prices = _flat_series()
    assert find_triggers(prices) == []


def test_find_triggers_decluster_drops_adjacent_hits():
    idx = pd.bdate_range("2020-01-01", periods=60)
    prices = pd.Series(100.0, index=idx)
    prices.iloc[10:16] = [100, 88, 87, 86, 85, 84]  # one real crash, several days <=-10% ROC
    triggers = find_triggers(prices)
    assert len(triggers) == 1


def test_dip_buy_forward_return_matches_price_ratio():
    idx = pd.bdate_range("2020-01-01", periods=100)
    prices = pd.Series(np.linspace(100, 150, 100), index=idx)
    trigger = idx[20]
    horizon = 21
    ret = dip_buy_forward_return(prices, trigger, horizon)
    expected = prices.iloc[20 + horizon] / (prices.iloc[20] * 1.0010) - 1
    assert ret is not None
    assert abs(ret - expected) < 1e-9


def test_dip_buy_forward_return_none_near_end_of_series():
    idx = pd.bdate_range("2020-01-01", periods=30)
    prices = pd.Series(100.0, index=idx)
    assert dip_buy_forward_return(prices, idx[25], 21) is None


def test_mix_forward_return_flat_prices_only_pays_entry_cost():
    idx = pd.bdate_range("2020-01-01", periods=50)
    prices = {"G": pd.Series(100.0, index=idx), "X": pd.Series(100.0, index=idx),
              "L": pd.Series(100.0, index=idx)}
    ret = mix_forward_return(BASE_MIX, prices, idx, idx[5], 21)
    assert ret is not None
    assert abs(ret - (-0.0010)) < 1e-9


def test_mix_forward_return_defensive_excludes_avgo():
    idx = pd.bdate_range("2020-01-01", periods=50)
    # AVGO craters, Gold/LLY flat -- defensive mix (no AVGO) should barely move
    avgo = pd.Series(100.0, index=idx)
    avgo.iloc[10:] = 50.0
    prices = {"G": pd.Series(100.0, index=idx), "X": avgo, "L": pd.Series(100.0, index=idx)}
    ret = mix_forward_return(DEFENSIVE_MIX, prices, idx, idx[5], 21)
    assert ret is not None
    assert abs(ret - (-0.0010)) < 1e-6
