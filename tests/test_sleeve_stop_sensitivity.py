import pandas as pd

from run_sleeve_stop_sensitivity import simulate_stop, stop_sensitivity


def _series(values: list[float], start: str = "2024-01-01") -> pd.Series:
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def test_simulate_stop_returns_forward_return_when_never_breached():
    # Flat then up 10% by day 30, never dips below entry.
    prices = _series([100.0] * 30 + [110.0])
    entry_date = prices.index[0]
    r = simulate_stop(prices, entry_date, stop_pct=0.02, max_calendar_days=30)
    assert r is not None
    assert r > 0  # ended up, never stopped out


def test_simulate_stop_exits_at_stop_price_when_breached():
    # Drops below the 2% stop on day 5, then recovers -- must still exit at -2%.
    values = [100.0] * 5 + [97.5] + [150.0] * 26  # breach on index 5
    prices = _series(values)
    entry_date = prices.index[0]
    r = simulate_stop(prices, entry_date, stop_pct=0.02, max_calendar_days=30)
    assert r == -0.02


def test_simulate_stop_none_when_entry_date_not_in_series():
    prices = _series([100.0] * 40, start="2024-01-01")
    far_off_date = pd.Timestamp("2030-01-01")
    assert simulate_stop(prices, far_off_date, stop_pct=0.02) is None


def test_simulate_stop_none_when_insufficient_forward_data():
    # Only 3 days of data past entry -- can't evaluate a 30-day exit and
    # never breaches, so there's nothing to conclude.
    prices = _series([100.0, 101.0, 102.0])
    entry_date = prices.index[0]
    assert simulate_stop(prices, entry_date, stop_pct=0.02, max_calendar_days=30) is None


def test_stop_sensitivity_computes_stopped_out_fraction():
    # 2 tickers, 10 entries each of the same shape: half breach, half don't.
    breached = _series([100.0] * 5 + [97.0] + [120.0] * 25)
    clean = _series([100.0] * 31 + [105.0])
    candidates = {"BREACH": ("equities", breached), "CLEAN": ("equities", clean)}

    entries = (
        [{"ticker": "BREACH", "date": breached.index[0]} for _ in range(5)]
        + [{"ticker": "CLEAN", "date": clean.index[0]} for _ in range(5)]
    )
    out = stop_sensitivity(entries, candidates)
    row = out[out["stop_pct"] == 0.02].iloc[0]
    assert row["n"] == 10
    assert row["stopped_out_frac"] == 0.5


def test_stop_sensitivity_nan_below_min_n_obs():
    clean = _series([100.0] * 31 + [105.0])
    candidates = {"CLEAN": ("equities", clean)}
    entries = [{"ticker": "CLEAN", "date": clean.index[0]}]  # only 1, below MIN_N_OBS
    out = stop_sensitivity(entries, candidates)
    row = out[out["stop_pct"] == 0.02].iloc[0]
    assert row["n"] == 1
    assert pd.isna(row["median_return"])
