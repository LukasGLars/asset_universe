import numpy as np
import pandas as pd

from run_opp_sleeve_entry_filter_sensitivity import (
    diversity_at_least, find_gated_entries_with_diagnostics, ma50_slope_at_least,
    period_n_matched, rs_margin_at_least, summarize, vix_calm,
)


def _prices(start, values):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


# ── simple predicate tests ───────────────────────────────────────────────────

def test_rs_margin_at_least():
    assert rs_margin_at_least({"rs_margin": 0.03}, 0.02) is True
    assert rs_margin_at_least({"rs_margin": 0.01}, 0.02) is False


def test_ma50_slope_at_least_handles_none():
    assert ma50_slope_at_least({"ma50_slope": None}, 0.5) is False
    assert ma50_slope_at_least({"ma50_slope": 1.0}, 0.5) is True
    assert ma50_slope_at_least({"ma50_slope": 0.2}, 0.5) is False


def test_vix_calm_only_true_on_explicit_true():
    assert vix_calm({"vix_calm": True}) is True
    assert vix_calm({"vix_calm": False}) is False
    assert vix_calm({"vix_calm": None}) is False


def test_diversity_at_least():
    assert diversity_at_least({"n_matched": 50}, 30) is True
    assert diversity_at_least({"n_matched": 20}, 30) is False


# ── period_n_matched ──────────────────────────────────────────────────────────

def test_period_n_matched_counts_only_pre_transition_matches():
    idx = pd.date_range("2020-01-01", periods=20, freq="D")
    df = pd.DataFrame({
        "ry_regime":     ["HIGH"] * 10 + ["LOW"] * 10,
        "baa10y_regime": ["TIGHT"] * 20,
    }, index=idx)
    # t_date at index 15 -- only pre-transition history (index < 15) counts,
    # and only rows matching (LOW, TIGHT) -- indices 10-14 (5 rows).
    n = period_n_matched(df, idx[15], "LOW", "TIGHT")
    assert n == 5


def test_period_n_matched_zero_when_no_history_matches():
    idx = pd.date_range("2020-01-01", periods=10, freq="D")
    df = pd.DataFrame({
        "ry_regime":     ["HIGH"] * 10,
        "baa10y_regime": ["TIGHT"] * 10,
    }, index=idx)
    assert period_n_matched(df, idx[5], "LOW", "LOOSE") == 0


# ── summarize ─────────────────────────────────────────────────────────────────

def test_summarize_blanks_below_min_n_obs():
    prices = _prices("2020-01-01", [100 + i for i in range(60)])
    candidates = {"A": ("equities", prices)}
    entries = [{"ticker": "A", "date": pd.Timestamp("2020-01-01")}]
    stats = summarize(entries, candidates)
    assert stats["n"] <= 1
    assert stats["median_return"] is None


def test_summarize_computes_stats_above_min_n_obs():
    prices = _prices("2020-01-01", [100 + i * 0.5 for i in range(200)])
    candidates = {"A": ("equities", prices)}
    entries = [{"ticker": "A", "date": prices.index[i]} for i in range(0, 150, 5)]
    stats = summarize(entries, candidates)
    assert stats["n"] >= 10
    assert stats["median_return"] is not None
    assert stats["median_return"] > 0  # steadily rising series
    assert 0.0 <= stats["win_rate"] <= 1.0


# ── find_gated_entries_with_diagnostics ──────────────────────────────────────

def _flat_labeled_df(start, n):
    idx = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame({"ry_regime": ["HIGH"] * n, "baa10y_regime": ["TIGHT"] * n}, index=idx)


def test_find_gated_entries_attaches_diagnostics_and_excludes_negative_rs(monkeypatch):
    import run_sleeve_entry_reconstruction as recon
    monkeypatch.setattr(recon, "_earnings_dates", lambda ticker: np.array([], dtype="datetime64[ns]"))

    # Ticker A: steadily above its MA50 the whole period, outperforming a
    # flat benchmark -- should qualify with a positive rs_margin.
    n = 120
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    a_prices = pd.Series(100 + np.arange(n) * 0.3, index=idx)
    bm_prices = pd.Series(100.0, index=idx)  # flat benchmark -- A always beats it
    vix = pd.Series(15.0, index=idx)  # flat, calm VIX throughout

    candidates = {"A": ("equities", a_prices)}
    labeled_df = _flat_labeled_df("2020-01-01", n)
    selections = [{
        "t_date": idx[60], "ry": "HIGH", "baa": "TIGHT",
        "top": ["A"], "p67": {"A": 0.5},  # generous extension allowance
    }]

    events = find_gated_entries_with_diagnostics(selections, candidates, bm_prices, labeled_df, vix)
    assert len(events) > 0
    e = events[0]
    assert e["ticker"] == "A"
    assert e["rs_margin"] > 0  # A steadily beats the flat benchmark
    assert e["vix_calm"] is True  # flat VIX == its own 20d average -> calm
    assert e["n_matched"] == 60  # all 60 pre-transition HIGH/TIGHT rows matched


def test_find_gated_entries_excludes_when_underperforming_benchmark(monkeypatch):
    import run_sleeve_entry_reconstruction as recon
    monkeypatch.setattr(recon, "_earnings_dates", lambda ticker: np.array([], dtype="datetime64[ns]"))

    n = 120
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    a_prices = pd.Series(100 + np.arange(n) * 0.1, index=idx)         # A rises slowly
    bm_prices = pd.Series(100 + np.arange(n) * 0.5, index=idx)        # benchmark rises much faster
    vix = pd.Series(15.0, index=idx)

    candidates = {"A": ("equities", a_prices)}
    labeled_df = _flat_labeled_df("2020-01-01", n)
    selections = [{
        "t_date": idx[60], "ry": "HIGH", "baa": "TIGHT",
        "top": ["A"], "p67": {"A": 0.5},
    }]

    events = find_gated_entries_with_diagnostics(selections, candidates, bm_prices, labeled_df, vix)
    assert events == []  # A never beats the benchmark -- gate 3b (RS) excludes every date
