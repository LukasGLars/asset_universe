"""Guards for run_peer_valuation.py's history layer.

The point of this file is a time series that cannot be backfilled, so the
two things that must not break are: one row per ticker per day, and a
failure here never taking the sync down.

"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run_peer_valuation as V


@pytest.fixture
def tmp_history(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "HISTORY_CSV", tmp_path / "h.csv")
    return tmp_path / "h.csv"


def row(ticker="AVGO", fwd_pe=16.95):
    return {"ticker": ticker, "price": 328.75, "ttm_eps": 9.76, "fwd_eps": 19.40,
            "ratio": 1.99, "growth_pct": 99.0, "fwd_pe": fwd_pe, "peg_1y": 0.17}


def test_missing_file_reads_as_empty(tmp_history):
    assert V.read_history() == []


def test_roundtrip_preserves_every_field(tmp_history):
    V.write_history(V.append_history([row()], dt.date(2026, 10, 18), []))
    got = V.read_history()
    assert len(got) == 1
    assert set(got[0]) == set(V.HISTORY_FIELDS)
    assert got[0]["ticker"] == "AVGO"
    assert float(got[0]["fwd_pe"]) == pytest.approx(16.95)


def test_same_day_rerun_replaces_rather_than_duplicates(tmp_history):
    """sync.yml fires twice daily (06:07 and 20:37 UTC). Appending blindly
    would put two rows on every date and double-weight each day in any
    percentile computed from the file."""
    d = dt.date(2026, 10, 18)
    h = V.append_history([row(fwd_pe=16.95)], d, [])
    h = V.append_history([row(fwd_pe=17.10)], d, h)
    assert len(h) == 1
    assert float(h[0]["fwd_pe"]) == pytest.approx(17.10), "later run should win"


def test_distinct_days_accumulate(tmp_history):
    h = []
    for i in range(1, 6):
        h = V.append_history([row()], dt.date(2026, 10, i), h)
    assert len(h) == 5


def test_multiple_tickers_on_one_day_all_kept(tmp_history):
    h = V.append_history([row("AVGO"), row("LLY"), row("NVDA")],
                         dt.date(2026, 10, 18), [])
    assert sorted(r["ticker"] for r in h) == ["AVGO", "LLY", "NVDA"]


def test_rows_are_sorted_by_date_then_ticker(tmp_history):
    h = V.append_history([row("NVDA"), row("AVGO")], dt.date(2026, 10, 19), [])
    h = V.append_history([row("LLY")], dt.date(2026, 10, 18), h)
    assert [(r["date"], r["ticker"]) for r in h] == [
        ("2026-10-18", "LLY"), ("2026-10-19", "AVGO"), ("2026-10-19", "NVDA")]


# ── percentile ───────────────────────────────────────────────────────────────

def test_percentile_suppressed_below_the_minimum():
    thin = [{"ticker": "AVGO", "fwd_pe": "15"}] * (V.MIN_HISTORY_OBS - 1)
    pct, n = V.own_history_percentile(thin, "AVGO", "fwd_pe", 16.0)
    assert pct is None
    assert n == V.MIN_HISTORY_OBS - 1


def test_percentile_low_means_cheap():
    hist = [{"ticker": "AVGO", "fwd_pe": str(10 + i * 0.1)} for i in range(100)]
    cheap, _ = V.own_history_percentile(hist, "AVGO", "fwd_pe", 9.0)
    dear, _ = V.own_history_percentile(hist, "AVGO", "fwd_pe", 30.0)
    assert cheap == 0.0
    assert dear == 1.0


def test_percentile_only_counts_its_own_ticker():
    hist = ([{"ticker": "AVGO", "fwd_pe": "20"}] * V.MIN_HISTORY_OBS
            + [{"ticker": "NVDA", "fwd_pe": "1"}] * V.MIN_HISTORY_OBS)
    pct, n = V.own_history_percentile(hist, "AVGO", "fwd_pe", 15.0)
    assert n == V.MIN_HISTORY_OBS, "NVDA rows must not be counted"
    assert pct == 0.0


def test_unparseable_and_missing_values_are_skipped_not_fatal():
    hist = ([{"ticker": "AVGO", "fwd_pe": "n/a"}, {"ticker": "AVGO", "fwd_pe": ""},
             {"ticker": "AVGO", "fwd_pe": "None"}, {"ticker": "AVGO"}]
            + [{"ticker": "AVGO", "fwd_pe": "20"}] * V.MIN_HISTORY_OBS)
    pct, n = V.own_history_percentile(hist, "AVGO", "fwd_pe", 15.0)
    assert n == V.MIN_HISTORY_OBS
    assert pct == 0.0


def test_none_current_value_returns_none():
    hist = [{"ticker": "AVGO", "fwd_pe": "20"}] * 200
    assert V.own_history_percentile(hist, "AVGO", "fwd_pe", None) == (None, 0)


# ── the sync must survive a broken history ───────────────────────────────────

def test_history_failure_does_not_raise_out_of_main(monkeypatch, capsys):
    """status.md is checked for the string "Traceback" and the whole daily job
    fails on it. A disk problem here must not take the pipeline down over a
    column nothing acts on yet."""
    monkeypatch.setattr(V, "fetch_ticker_snapshot",
                        lambda t: {"price": 1.0, "ttm_quarters": [1.0] * 4, "forward_1y": 2.0})
    monkeypatch.setattr(V, "PEER_SET", ["AVGO"])

    def boom(*a, **k):
        raise OSError("read-only file system")

    monkeypatch.setattr(V, "read_history", boom)
    V.main()
    out = capsys.readouterr().out
    assert "valuation history unavailable" in out
    assert "Traceback" not in out
