"""Staleness gate for run_universe_screen.py (added 2026-08-27).

Regression cover for the daily-sync failure where SATS -- delisted, last bar
2026-07-17 -- was still ranked #8 in universe_screen_results.csv. The entry
screen pulled it as a live gate-1 candidate, yfinance emitted a raw
'HTTP Error 404 ... Quote not found for symbol: SATS' into status.md, and
check_sync_health.py failed the whole run on the 'Error' signature.

The gate logic is inline in the script (module-level, not importable without
running the whole screen), so it is reproduced here exactly. These tests pin
the BEHAVIOUR; if the script's copy drifts from this one, that is itself the
bug worth catching.
"""
import pandas as pd
import pytest

MAX_STALE_DAYS = 10


def partition(rows, max_stale_days=MAX_STALE_DAYS):
    """Mirror of the gate in run_universe_screen.py."""
    ref = max(pd.Timestamp(r["last_bar"]) for r in rows)
    fresh, stale = [], []
    for r in rows:
        (stale if (ref - pd.Timestamp(r["last_bar"])).days > max_stale_days
         else fresh).append(r)
    return fresh, stale, ref


def _t(ticker, last_bar):
    return {"ticker": ticker, "last_bar": last_bar}


def test_drops_the_real_sats_case():
    """The actual failure: SATS 41 days behind a live universe."""
    rows = [_t("AAPL", "2026-08-26"), _t("MSFT", "2026-08-26"),
            _t("SATS", "2026-07-17"), _t("EA", "2026-08-10")]
    fresh, stale, ref = partition(rows)
    names = {r["ticker"] for r in stale}
    assert "SATS" in names
    assert "EA" in names            # 16d behind, also delisted
    assert {r["ticker"] for r in fresh} == {"AAPL", "MSFT"}
    assert ref == pd.Timestamp("2026-08-26")


def test_keeps_normal_weekend_and_holiday_lag():
    """A live ticker trailing by a long weekend must NOT be dropped -- the
    gate has to distinguish 'market was shut' from 'ticker is dead'."""
    rows = [_t("AAPL", "2026-08-26"), _t("KO", "2026-08-21")]   # 5d
    fresh, stale, _ = partition(rows)
    assert stale == []
    assert len(fresh) == 2


def test_boundary_is_inclusive_at_the_threshold():
    rows = [_t("FRESH", "2026-08-26"), _t("EDGE", "2026-08-16")]  # exactly 10d
    fresh, stale, _ = partition(rows)
    assert stale == [], "exactly MAX_STALE_DAYS must be kept, not dropped"
    rows = [_t("FRESH", "2026-08-26"), _t("OVER", "2026-08-15")]  # 11d
    fresh, stale, _ = partition(rows)
    assert [r["ticker"] for r in stale] == ["OVER"]


def test_gate_is_self_calibrating_not_wall_clock():
    """Reference is the freshest bar in the run, not today. If the entire
    store is old, nothing should be dropped -- otherwise a stale store would
    silently empty the universe."""
    rows = [_t("A", "2020-01-06"), _t("B", "2020-01-03"), _t("C", "2020-01-02")]
    fresh, stale, ref = partition(rows)
    assert stale == []
    assert len(fresh) == 3
    assert ref == pd.Timestamp("2020-01-06")


def test_freshest_ticker_always_survives():
    """The gate can never empty the universe: whatever defines the reference
    is by construction 0 days stale."""
    rows = [_t("ONLY", "2019-05-05")]
    fresh, stale, _ = partition(rows)
    assert [r["ticker"] for r in fresh] == ["ONLY"]
    assert stale == []


def test_all_stale_except_one_still_leaves_a_universe():
    rows = [_t("LIVE", "2026-08-26")] + [
        _t(f"DEAD{i}", "2025-01-01") for i in range(20)
    ]
    fresh, stale, _ = partition(rows)
    assert [r["ticker"] for r in fresh] == ["LIVE"]
    assert len(stale) == 20


@pytest.mark.parametrize("bad", [[], None])
def test_empty_input_is_a_programming_error_not_silent_pass(bad):
    """max() on an empty sequence must raise rather than quietly yield an
    empty universe -- the script guards `if not rows` before this point."""
    with pytest.raises((ValueError, TypeError)):
        partition(bad or [])
