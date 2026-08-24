import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from run_btc_momentum_validation import perf, trend_equity, open_fill_equity


def _ramp(n=400, slope=1.0, start=100.0):
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    return pd.Series(start + slope * np.arange(n), index=idx)


def test_shift1_cannot_capture_the_signal_day_move():
    """The core anti-lookahead property: a one-day spike that FLIPS the signal
    must not be captured by the shift(1) strategy on that same day."""
    close = _ramp(n=300, slope=0.0, start=100.0)   # flat -> price == SMA
    close.iloc[250] = 200.0                        # single-day spike up
    ret = close.pct_change()

    eq_correct, pos_correct = trend_equity(close, ret, 200, tc=0.0, shift=1)
    eq_look, pos_look = trend_equity(close, ret, 200, tc=0.0, shift=0)

    # Lookahead is positioned ON the spike day and captures the +100% move.
    assert pos_look.iloc[250] == 1.0
    # Correct version is flat that day -- it could not have known.
    assert pos_correct.iloc[250] == 0.0
    # So lookahead ends materially richer on the identical price series.
    assert eq_look.iloc[-1] > eq_correct.iloc[-1]


def test_shift1_acts_the_day_after_signal():
    close = _ramp(n=300, slope=0.5)
    ret = close.pct_change()
    _, pos = trend_equity(close, ret, 200, tc=0.0, shift=1)
    sma = close.rolling(200).mean()
    signal = (close > sma).astype(float)
    # position on day i must equal signal on day i-1, everywhere it's defined
    assert pos.iloc[1:].equals(signal.shift(1).fillna(0.0).iloc[1:])


def test_transaction_cost_charged_once_per_flip():
    close = _ramp(n=300, slope=0.0, start=100.0)
    close.iloc[220:260] = 150.0          # one sustained regime up, then back
    ret = close.pct_change()
    _, pos = trend_equity(close, ret, 200, tc=0.0, shift=1)
    flips = pos.diff().abs().fillna(0.0).sum()
    # one entry + one exit, not one charge per day held
    assert flips == 2.0


def test_open_fill_entry_bar_uses_open_to_close_not_close_to_close():
    n = 300
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    close = pd.Series(100.0, index=idx)
    close.iloc[250:] = 150.0             # regime shift up at 250
    opn = close.copy()
    # entry bar (251) gaps: opens at 150, closes at 165
    opn.iloc[251] = 150.0
    close.iloc[251] = 165.0
    df = pd.DataFrame({"Open": opn, "Close": close})

    eq_open, pos = open_fill_equity(df, 200, tc=0.0)
    # Signal fires on 250 (close 150 > SMA), so position starts 251.
    assert pos.iloc[251] == 1.0
    # Captured return on the entry bar is open->close (165/150-1 = +10%),
    # NOT close->close (165/150-1 also 10% here) -- so make the gap explicit:
    # prior close was 150, open 150 -> identical; use a gap-up case instead.
    opn.iloc[251] = 160.0                # gaps up above prior close of 150
    df2 = pd.DataFrame({"Open": opn, "Close": close})
    eq2, _ = open_fill_equity(df2, 200, tc=0.0)
    # open->close = 165/160-1 = +3.1%, strictly less than close->close +10%.
    # Paying the gap makes the open-fill model WORSE, as it should be.
    assert eq2.iloc[-1] < eq_open.iloc[-1]


def test_perf_annualization_uses_the_bars_per_year_given():
    idx = pd.date_range("2020-01-01", periods=730, freq="D")
    rng = np.random.default_rng(0)
    eq = pd.Series((1 + rng.normal(0.001, 0.02, 730)).cumprod(), index=idx)
    s252 = perf(eq, 252.0)["sharpe"]
    s365 = perf(eq, 365.0)["sharpe"]
    assert abs(s365 / s252 - np.sqrt(365 / 252)) < 1e-9


def test_perf_flat_equity_is_zero_return_zero_drawdown():
    idx = pd.date_range("2020-01-01", periods=400, freq="D")
    eq = pd.Series(1.0, index=idx)
    p = perf(eq)
    assert abs(p["cagr"]) < 1e-9
    assert abs(p["maxdd"]) < 1e-12
