import numpy as np
import pandas as pd

import run_sleeve_pead_reconstruction as pead


def _prices(start, values):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def test_bucket_for_boundaries():
    assert pead._bucket_for(-1.0) == "miss_or_flat"
    assert pead._bucket_for(0.0) == "miss_or_flat"
    assert pead._bucket_for(1.5) == "beat_0_2"
    assert pead._bucket_for(2.0) == "beat_0_2"
    assert pead._bucket_for(3.0) == "beat_2_5"
    assert pead._bucket_for(7.0) == "beat_5_10"
    assert pead._bucket_for(25.0) == "beat_10_plus"


def test_earnings_surprises_handles_tz_aware_index_and_keeps_surprise_column(monkeypatch):
    idx = pd.DatetimeIndex(["2024-01-15", "2024-04-15"], tz="America/New_York")
    fake_df = pd.DataFrame(
        {"EPS Estimate": [1.0, 2.0], "Reported EPS": [1.1, 1.9], "Surprise(%)": [10.0, -5.0]},
        index=idx,
    )

    class FakeTicker:
        def get_earnings_dates(self, limit=60):
            return fake_df

    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())
    pead._surprise_cache.clear()

    out = pead._earnings_surprises("FAKECO")
    assert len(out) == 2
    assert out.iloc[0]["date"] == pd.Timestamp("2024-01-15")
    assert out.iloc[0]["surprise"] == 10.0
    assert out.iloc[1]["surprise"] == -5.0


def test_earnings_surprises_empty_on_missing_column(monkeypatch):
    fake_df = pd.DataFrame({"EPS Estimate": [1.0]}, index=pd.DatetimeIndex(["2024-01-15"]))

    class FakeTicker:
        def get_earnings_dates(self, limit=60):
            return fake_df

    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", lambda t: FakeTicker())
    pead._surprise_cache.clear()

    out = pead._earnings_surprises("FAKECO")
    assert out.empty


def test_find_pead_entries_requires_gate1_membership_at_print_date(monkeypatch):
    selections = [
        {"t_date": pd.Timestamp("2020-01-01"), "top": ["A"], "p67": {}},
        {"t_date": pd.Timestamp("2020-06-01"), "top": ["B"], "p67": {}},
    ]
    candidates = {
        "A": ("equities", _prices("2019-01-01", list(range(500)))),
        "B": ("equities", _prices("2019-01-01", list(range(500)))),
    }

    def fake_surprises(ticker):
        data = {
            # A: one print while A is in top (Feb), one after B takes over (July) -- should be dropped
            "A": pd.DataFrame({"date": [pd.Timestamp("2020-02-01"), pd.Timestamp("2020-07-01")],
                                "surprise": [3.0, 3.0]}),
            "B": pd.DataFrame({"date": [pd.Timestamp("2020-07-01")], "surprise": [12.0]}),
        }
        return data.get(ticker, pd.DataFrame(columns=["date", "surprise"]))

    monkeypatch.setattr(pead, "_earnings_surprises", fake_surprises)
    events = pead.find_pead_entries(selections, candidates)

    assert len(events) == 2
    by_ticker = {(e["ticker"], e["date"]): e["bucket"] for e in events}
    assert by_ticker[("A", pd.Timestamp("2020-02-01"))] == "beat_2_5"
    assert by_ticker[("B", pd.Timestamp("2020-07-01"))] == "beat_10_plus"
    assert ("A", pd.Timestamp("2020-07-01")) not in by_ticker  # A no longer in top-N by July


def test_early_stop_rate_detects_ma50_breach():
    # Price sits right at MA50 by construction (flat run-up then a hard drop) --
    # buffered MA50 should bind well before the 21d horizon.
    values = [100.0] * 60 + [70.0] * 30
    prices = _prices("2020-01-01", values)
    candidates = {"X": ("equities", prices)}
    entries = [{"ticker": "X", "date": prices.index[60]}]

    rate, n = pead.early_stop_rate(entries, candidates, horizon_days=21)
    assert n == 1
    assert rate == 1.0


def test_early_stop_rate_no_breach_on_steady_uptrend():
    values = [100.0 + i for i in range(120)]
    prices = _prices("2020-01-01", values)
    candidates = {"X": ("equities", prices)}
    entries = [{"ticker": "X", "date": prices.index[60]}]

    rate, n = pead.early_stop_rate(entries, candidates, horizon_days=21)
    assert n == 1
    assert rate == 0.0
