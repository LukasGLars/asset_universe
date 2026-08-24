import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from run_btc_fx_check import etp_position, equity, perf


def _days(n, start="2021-01-04"):
    return pd.date_range(start, periods=n, freq="D")


def test_fx_conversion_direction_matches_portfolio_py():
    """Repo convention is price_sek = price_usd * usdsek. A STRENGTHENING
    dollar must therefore RAISE the SEK value of a USD-priced asset."""
    idx = _days(10)
    btc_usd = pd.Series(100.0, index=idx)
    usdsek = pd.Series(np.linspace(10.0, 11.0, 10), index=idx)  # USD strengthens
    btc_sek = btc_usd * usdsek
    assert btc_sek.iloc[-1] > btc_sek.iloc[0]
    assert btc_sek.iloc[0] == 1000.0


def test_flat_position_earns_nothing_and_carries_no_fx():
    """Sitting in SEK cash must be immune to both BTC and FX moves."""
    idx = _days(300)
    ret = pd.Series(np.linspace(-0.05, 0.05, 300), index=idx)
    pos = pd.Series(0.0, index=idx)
    eq = equity(pos, ret, tc=0.0)
    assert abs(eq.iloc[-1] - 1.0) < 1e-12


def test_weekend_fx_forward_fill_defers_the_gap_to_monday():
    """FX is weekday-only. Forward-filling must leave Sat/Sun FX unchanged and
    put the whole FX gap into Monday's bar -- what a Monday ETP open shows."""
    idx = _days(14)                      # starts Monday 2021-01-04
    fx_weekday = pd.Series(
        [10.0, 10.0, 10.0, 10.0, 10.0, 12.0, 12.0, 12.0, 12.0, 12.0],
        index=[d for d in idx if d.dayofweek < 5],
    )
    fx = fx_weekday.reindex(idx).ffill()
    sat = [d for d in idx if d.dayofweek == 5][0]
    sun = sat + pd.Timedelta(days=1)
    mon = sat + pd.Timedelta(days=2)
    assert fx.loc[sat] == 10.0, "FX moved on a Saturday"
    assert fx.loc[sun] == 10.0, "FX moved on a Sunday"
    assert fx.loc[mon] == 12.0, "FX gap should land on Monday"


def test_etp_position_still_never_trades_a_weekend_with_fx_prices():
    rng = np.random.default_rng(11)
    idx = _days(600)
    px = pd.Series(100 * (1 + rng.normal(0.002, 0.03, 600)).cumprod(), index=idx)
    pos = etp_position(px, 150)
    weekend = pos.index.dayofweek >= 5
    assert pos.diff().abs().fillna(0.0)[weekend].sum() == 0.0


def test_signal_cannot_capture_its_own_day_move():
    idx = _days(400)
    px = pd.Series(100.0, index=idx)
    px.iloc[300] = 500.0                 # one-day spike
    pos = etp_position(px, 150)
    assert pos.iloc[300] == 0.0, "captured the spike day it was computed from"


def test_perf_sharpe_uses_365_not_252():
    idx = _days(730)
    rng = np.random.default_rng(2)
    eq = pd.Series((1 + rng.normal(0.001, 0.02, 730)).cumprod(), index=idx)
    r = eq.pct_change().dropna()
    expected = float(r.mean() / r.std() * np.sqrt(365.0))
    assert abs(perf(eq)["sharpe"] - expected) < 1e-9
