import numpy as np
import pandas as pd

import run_sleeve_entry_reconstruction as recon


def _prices(start, values):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def test_detect_transitions_confirms_persistent_change_only():
    # regime flips at index 5 but reverts by index 7 (< CONFIRM_DAYS=5
    # persistence) -- should NOT register as a transition. Flips again at
    # index 10 and holds for >=5 days -- SHOULD register.
    labels = ["A"] * 5 + ["B"] * 2 + ["A"] * 3 + ["C"] * 6
    idx = pd.date_range("2020-01-01", periods=len(labels), freq="D")
    df = pd.DataFrame({
        "ry_regime": labels,
        "baa10y_regime": ["X"] * len(labels),
    }, index=idx)

    transitions = recon.detect_transitions(df)
    labels_seen = [ry for _d, ry, _baa in transitions]
    assert labels_seen == ["A", "C"]


def test_regime_median_return_requires_min_observations():
    prices = _prices("2020-01-01", list(range(100, 100 + 400)))
    matched = prices.index[:5]  # fewer than MIN_REGIME_DATES=15
    assert recon.regime_median_return(prices, matched) is None


def test_regime_median_return_computes_forward_median():
    # Prices rise 1 unit/day; 252 trading days later return should be
    # roughly consistent across a handful of matched dates.
    prices = _prices("2015-01-01", list(range(100, 100 + 2000)))
    matched = prices.index[100:120]  # 20 matched dates, > MIN_REGIME_DATES
    med = recon.regime_median_return(prices, matched, fwd_days=252)
    assert med is not None
    assert med > 0  # steadily rising series -> positive forward return


def test_earnings_dates_handles_tz_aware_index_from_yfinance(monkeypatch):
    # Regression test: get_earnings_dates() returns a DataFrame whose
    # index is tz-aware Timestamps, but .to_pydatetime() converts those
    # to plain stdlib datetime.datetime objects -- which do NOT have a
    # .tz_localize() method (that's pandas-Timestamp-only). The original
    # code called d.tz_localize(None) here, raising an AttributeError
    # that was silently swallowed by _earnings_dates()'s broad except,
    # making the earnings-clear gate a permanent no-op. Masked for a long
    # time by a SEPARATE missing-lxml issue that failed even earlier in
    # the same try block -- fixing lxml alone did not fix this.
    idx = pd.DatetimeIndex(
        ["2024-01-15", "2024-04-15"], tz="America/New_York",
    )
    fake_df = pd.DataFrame({"Reported EPS": [1.0, 2.0]}, index=idx)

    class FakeTicker:
        def get_earnings_dates(self, limit=60):
            return fake_df

    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())
    recon._earnings_cache.clear()

    dates = recon._earnings_dates("FAKECO")
    assert len(dates) == 2
    assert dates[0] == np.datetime64("2024-01-15")


def test_earnings_clear_true_when_no_data(monkeypatch):
    monkeypatch.setattr(recon, "_earnings_dates", lambda ticker: np.array([], dtype="datetime64[ns]"))
    assert recon.earnings_clear("ZZZ", pd.Timestamp("2020-01-01")) is True


def test_earnings_clear_false_within_hold_window(monkeypatch):
    dates = np.array([np.datetime64("2020-01-15")])
    monkeypatch.setattr(recon, "_earnings_dates", lambda ticker: dates)
    # 10 days before earnings, hold_days=21 -> inside window -> not clear
    assert recon.earnings_clear("ZZZ", pd.Timestamp("2020-01-05"), hold_days=21) is False


def test_earnings_clear_true_outside_hold_window(monkeypatch):
    dates = np.array([np.datetime64("2020-02-15")])
    monkeypatch.setattr(recon, "_earnings_dates", lambda ticker: dates)
    # 41 days before earnings, hold_days=21 -> outside window -> clear
    assert recon.earnings_clear("ZZZ", pd.Timestamp("2020-01-05"), hold_days=21) is True


def test_decluster_keeps_first_of_each_cluster_per_ticker():
    events = [
        {"ticker": "A", "date": pd.Timestamp("2020-01-01")},
        {"ticker": "A", "date": pd.Timestamp("2020-01-05")},   # 4d gap, within DECLUSTER_DAYS -> dropped
        {"ticker": "A", "date": pd.Timestamp("2020-02-10")},   # >=30d gap from last KEPT -> kept
        {"ticker": "B", "date": pd.Timestamp("2020-01-01")},
    ]
    kept = recon.decluster(events, min_gap_days=30)
    kept_pairs = sorted((e["ticker"], e["date"]) for e in kept)
    assert kept_pairs == [
        ("A", pd.Timestamp("2020-01-01")),
        ("A", pd.Timestamp("2020-02-10")),
        ("B", pd.Timestamp("2020-01-01")),
    ]


def test_forward_return_basic():
    prices = _prices("2020-01-01", [100.0, 101.0, 102.0, 103.0, 104.0, 110.0])
    r = recon.forward_return(prices, pd.Timestamp("2020-01-01"), calendar_days=5)
    assert r is not None
    assert abs(r - 0.10) < 1e-9  # 100 -> 110 over the 5-day-later date


def test_forward_return_none_when_target_beyond_history():
    prices = _prices("2020-01-01", [100.0, 101.0, 102.0])
    assert recon.forward_return(prices, pd.Timestamp("2020-01-01"), calendar_days=90) is None


def test_duration_stats_reports_nan_below_min_n_obs():
    prices = _prices("2020-01-01", [100 + i for i in range(200)])
    candidates = {"A": ("equities", prices)}
    entries = [{"ticker": "A", "date": pd.Timestamp("2020-01-01")}]  # only 1 entry, < MIN_N_OBS
    out = recon.duration_stats(entries, candidates)
    assert out["n"].max() <= 1
    assert out["median_return"].isna().all()
