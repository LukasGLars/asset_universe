import datetime as dt

import pandas as pd

import run_entry_screen
from run_entry_screen import (
    binding_stop, select_best_candidate, suggested_duration_days, _vix_stats,
    sleeve_risk_state, _tripwire_detail_line, _risk_to_stop_str,
    basket_crash_binding_stop,
    cap_basket_crash_concentration, select_best_basket_crash,
)


def _tw(rs_20d=0.091, rs_ok=True, regime_changed=False, cluster_breakdown=False,
        cluster_avg=-0.069, peer_rets=None, ma50_now=264.99, ma50_slope=10.68, ma50_rising=True):
    return {
        "rs_20d": rs_20d, "rs_ok": rs_ok,
        "regime_changed": regime_changed,
        "peer_rets": peer_rets if peer_rets is not None else {"GEV": -0.088, "VRT": -0.051, "PWR": -0.075, "CMI": -0.062},
        "cluster_avg": cluster_avg, "cluster_breakdown": cluster_breakdown,
        "ma50_now": ma50_now, "ma50_slope": ma50_slope, "ma50_rising": ma50_rising,
    }


def test_tripwire_detail_line_all_clean():
    line = _tripwire_detail_line(_tw())
    assert "RS +9.1% [OK]" in line
    assert "Regime stable [OK]" in line
    assert "MA50 $264.99 (slope +10.68) [OK]" in line
    assert "Cluster avg -6.9% [OK]" in line


def test_tripwire_detail_line_flags_cluster_as_low_confidence():
    # The real 2026-07-09 HWM case: only cluster fires, and it must be
    # visibly caveated as a coarse sector-only match, not read as
    # equal-confidence with the other three checks.
    line = _tripwire_detail_line(_tw(cluster_breakdown=True))
    assert "RS +9.1% [OK]" in line
    assert "Cluster avg -6.9% [WATCH, sector-only match -- low-confidence]" in line


def test_tripwire_detail_line_no_peers_on_record():
    line = _tripwire_detail_line(_tw(peer_rets={}))
    assert "Cluster n/a (no peers on record)" in line


def test_tripwire_detail_line_missing_rs_and_ma50():
    line = _tripwire_detail_line(_tw(rs_20d=None, ma50_slope=None))
    assert "RS n/a" in line
    assert "MA50 n/a" in line


def test_risk_to_stop_str_computes_kr_and_pct():
    trig = {"current_price": 271.58, "binding_stop": 271.39}
    result = _risk_to_stop_str(trig, shares=11, fx_at_entry=9.734390258789062, capital_sek=29653.19)
    assert result is not None
    assert "kr" in result and "%" in result


def test_risk_to_stop_str_none_when_missing_data():
    assert _risk_to_stop_str({"current_price": None, "binding_stop": 271.39}, 11, 9.73, 29653.19) is None


def test_binding_stop_ma50_buffered_binds_when_trailing_not_armed():
    # No unrealized gain yet (peak == entry) -- trailing stop never
    # considered, only the 5%-buffered MA50 floor.
    stop, label = binding_stop(720.04, 708.66, peak_price=720.04)
    assert label == "MA50"
    assert abs(stop - 708.66 * 0.95) < 1e-6


def test_binding_stop_trailing_binds_once_armed_and_higher_than_ma50():
    # Peak is 10% above entry (past the 5% trigger); trailing level
    # (peak * 0.97, 3% trailing distance) sits well above the buffered
    # MA50 floor, so it binds.
    entry, ma50, peak = 100.0, 90.0, 110.0
    stop, label = binding_stop(entry, ma50, peak_price=peak)
    assert label == "TRAILING"
    assert abs(stop - peak * 0.97) < 1e-6


def test_binding_stop_ma50_still_wins_when_higher_than_armed_trailing():
    # Trailing is armed (peak 6% above entry) but MA50 has since risen
    # above the peak (a strong prior uptrend continuing) -- its buffered
    # level is still the higher (closer) floor even with trailing active.
    entry, ma50, peak = 100.0, 112.0, 106.0
    stop, label = binding_stop(entry, ma50, peak_price=peak)
    assert label == "MA50"
    assert abs(stop - ma50 * 0.95) < 1e-6


def test_binding_stop_trailing_not_armed_below_trigger():
    # Peak only 3% above entry -- below the 5% trigger, trailing must not
    # be considered even though it would technically be a valid dict entry.
    entry, ma50, peak = 100.0, 90.0, 103.0
    stop, label = binding_stop(entry, ma50, peak_price=peak)
    assert label == "MA50"


def _write_parquet_closes(path, dates, closes):
    pd.DataFrame({"date": dates, "close": closes}).to_parquet(path)


def test_peak_since_entry_returns_max_close_from_entry_onward(tmp_path, monkeypatch):
    from run_entry_screen import _peak_since_entry
    monkeypatch.setattr(run_entry_screen.reader, "ticker_path",
                         lambda data_dir, cat, tkr: tmp_path / "x.parquet")
    dates = pd.date_range("2026-06-01", periods=6, freq="D")
    _write_parquet_closes(tmp_path / "x.parquet", dates, [90, 100, 105, 98, 112, 108])
    # entry on day index 1 (2026-06-02, close 100) -- days before entry must
    # be excluded (90 on day 0 must NOT count even though it's the lowest).
    peak = _peak_since_entry(tmp_path, "equities", "X", "2026-06-02", entry_price=100.0)
    assert peak == 112.0


def test_peak_since_entry_floors_at_entry_price_when_never_exceeded(tmp_path, monkeypatch):
    from run_entry_screen import _peak_since_entry
    monkeypatch.setattr(run_entry_screen.reader, "ticker_path",
                         lambda data_dir, cat, tkr: tmp_path / "x.parquet")
    dates = pd.date_range("2026-06-01", periods=4, freq="D")
    _write_parquet_closes(tmp_path / "x.parquet", dates, [100, 95, 92, 97])
    peak = _peak_since_entry(tmp_path, "equities", "X", "2026-06-01", entry_price=100.0)
    assert peak == 100.0


def test_peak_since_entry_defaults_to_entry_price_when_file_missing(tmp_path):
    from run_entry_screen import _peak_since_entry
    peak = _peak_since_entry(tmp_path, "equities", "NOPE", "2026-06-01", entry_price=42.0)
    assert peak == 42.0


def _candidate_row(ticker, dist, diversity, win_21d, med_21d=0.04):
    return {
        "ticker": ticker, "verdict": "ENTER", "dist_num": dist,
        "dist_from_ma50": f"{dist:+.1%}", "diversity": diversity,
        "win_21d": win_21d, "med_21d": med_21d,
    }


def test_select_best_candidate_prefers_tightest_entry():
    out = pd.DataFrame([
        _candidate_row("A", 0.061, "THIN", 0.682, 0.051),   # best 21d return, but extended + THIN
        _candidate_row("B", 0.016, "ROBUST", 0.677, 0.040),  # tightest entry, ROBUST
        _candidate_row("C", 0.045, "ROBUST", 0.687, 0.035),
    ])
    pick = select_best_candidate(out, held=set())
    assert pick["ticker"] == "B"


def test_select_best_candidate_diversity_breaks_entry_ties():
    out = pd.DataFrame([
        _candidate_row("A", 0.030, "THIN", 0.900),
        _candidate_row("B", 0.030, "ROBUST", 0.500),  # same extension, ROBUST wins over THIN
    ])
    pick = select_best_candidate(out, held=set())
    assert pick["ticker"] == "B"


def test_select_best_candidate_excludes_already_held():
    out = pd.DataFrame([
        _candidate_row("HELD", 0.010, "ROBUST", 0.900),  # best on paper, but already held
        _candidate_row("NEW", 0.050, "THIN", 0.600),
    ])
    pick = select_best_candidate(out, held={"HELD"})
    assert pick["ticker"] == "NEW"


def _trig(current_price=280.0, binding_stop=271.39, time_exit_days_remaining=10):
    return {"current_price": current_price, "binding_stop": binding_stop,
            "time_exit_days_remaining": time_exit_days_remaining}


def test_sleeve_risk_stopped_when_price_at_or_below_binding_stop():
    assert sleeve_risk_state(_trig(current_price=271.0), any_watch=False) == "STOPPED"
    assert sleeve_risk_state(_trig(current_price=271.39), any_watch=False) == "STOPPED"  # exactly at stop


def test_sleeve_risk_time_exit_due_outranks_tripwire():
    trig = _trig(current_price=280.0, time_exit_days_remaining=0)
    assert sleeve_risk_state(trig, any_watch=True) == "TIME-EXIT-DUE"


def test_sleeve_risk_stopped_outranks_time_exit_due():
    trig = _trig(current_price=271.0, time_exit_days_remaining=0)
    assert sleeve_risk_state(trig, any_watch=False) == "STOPPED"


def test_sleeve_risk_tripwire_when_only_soft_flags():
    trig = _trig(current_price=280.0, time_exit_days_remaining=5)
    assert sleeve_risk_state(trig, any_watch=True) == "TRIPWIRE"


def test_sleeve_risk_clean_when_nothing_flagged():
    trig = _trig(current_price=280.0, time_exit_days_remaining=5)
    assert sleeve_risk_state(trig, any_watch=False) == "CLEAN"


def test_select_best_candidate_excludes_non_enter():
    out = pd.DataFrame([
        {**_candidate_row("PASS_ONLY", 0.005, "ROBUST", 0.99), "verdict": "PASS"},
        _candidate_row("ENTER_OK", 0.050, "THIN", 0.500),
    ])
    pick = select_best_candidate(out, held=set())
    assert pick["ticker"] == "ENTER_OK"


def test_select_best_candidate_no_eligible_returns_none():
    out = pd.DataFrame([
        {**_candidate_row("X", 0.02, "ROBUST", 0.9), "verdict": "PASS"},
    ])
    assert select_best_candidate(out, held=set()) is None


def test_select_best_candidate_ranks_on_duration_win_when_present():
    # duration_win (exact, matched to each candidate's own runway) should
    # override the fixed win_21d for ranking when both are available.
    out = pd.DataFrame([
        {**_candidate_row("A", 0.030, "ROBUST", 0.90), "duration_win": 0.40},  # high win_21d, poor duration_win
        {**_candidate_row("B", 0.030, "ROBUST", 0.50), "duration_win": 0.85},  # low win_21d, strong duration_win
    ])
    pick = select_best_candidate(out, held=set())
    assert pick["ticker"] == "B"


def test_select_best_candidate_falls_back_to_win_21d_when_duration_win_missing():
    out = pd.DataFrame([
        {**_candidate_row("A", 0.030, "ROBUST", 0.90), "duration_win": None},  # insufficient N at exact duration
        {**_candidate_row("B", 0.030, "ROBUST", 0.50), "duration_win": None},
    ])
    pick = select_best_candidate(out, held=set())
    assert pick["ticker"] == "A"  # falls back to win_21d, A's 0.90 beats B's 0.50


def test_suggested_duration_capped_by_earnings():
    today = dt.date(2026, 6, 30)
    earn = dt.date(2026, 7, 15)  # 15 calendar days out
    # min(21 flat, (15 - 3) earnings-buffer) = 12
    assert suggested_duration_days(earn, today) == 12


def test_suggested_duration_flat_21_when_earnings_far_out():
    today = dt.date(2026, 6, 30)
    earn = dt.date(2026, 9, 1)  # far beyond the flat 21d window
    assert suggested_duration_days(earn, today) == 21


def test_suggested_duration_no_earnings_date_defaults_flat_21():
    assert suggested_duration_days(None, dt.date(2026, 6, 30)) == 21


def test_suggested_duration_floors_at_one_day():
    today = dt.date(2026, 6, 30)
    earn = dt.date(2026, 7, 2)  # only 2 days out, earnings-3d would go negative
    assert suggested_duration_days(earn, today) == 1


# ── Pre-entry tripwire gate: a statically top-ranked candidate must ALSO
# clear the live tripwire check before being recommended -- these tests
# monkeypatch _pretrade_tripwire_check so the gating logic in
# select_best_candidate can be verified without live data/network access.

def _fake_tripwire(passed_map):
    def _check(ticker, category, gate1_candidates, held, regime_labels, data_dir, benchmark="SPY"):
        passed = passed_map.get(ticker, True)
        return passed, {"rs_20d": 0.05, "cluster_breakdown": not passed, "ma50_rising": passed}
    return _check


def test_pretrade_gate_disqualifies_top_rank_and_falls_to_next(monkeypatch):
    # A ranks best statically (tightest entry) but fails the live tripwire
    # check -- B should be recommended instead, not A.
    monkeypatch.setattr(run_entry_screen, "_pretrade_tripwire_check",
                         _fake_tripwire({"A": False, "B": True}))
    out = pd.DataFrame([
        {**_candidate_row("A", 0.010, "ROBUST", 0.90), "category": "equities"},
        {**_candidate_row("B", 0.050, "ROBUST", 0.60), "category": "equities"},
    ])
    pick = select_best_candidate(out, held=set(), data_dir="dummy", gate1_candidates=["A", "B"],
                                  regime_labels={"ry_regime": "HIGH", "baa10y_regime": "TIGHT"})
    assert pick["ticker"] == "B"
    assert pick["pretrade_tripwires"]["cluster_breakdown"] is False


def test_pretrade_gate_returns_none_when_everyone_fails(monkeypatch):
    monkeypatch.setattr(run_entry_screen, "_pretrade_tripwire_check",
                         _fake_tripwire({"A": False, "B": False}))
    out = pd.DataFrame([
        {**_candidate_row("A", 0.010, "ROBUST", 0.90), "category": "equities"},
        {**_candidate_row("B", 0.050, "ROBUST", 0.60), "category": "equities"},
    ])
    pick = select_best_candidate(out, held=set(), data_dir="dummy", gate1_candidates=["A", "B"],
                                  regime_labels={"ry_regime": "HIGH", "baa10y_regime": "TIGHT"})
    assert pick is None


def test_pretrade_gate_skipped_without_data_dir():
    # No data_dir/gate1_candidates/regime_labels -- falls back to the
    # static ranking alone (used by the existing synthetic-data tests).
    out = pd.DataFrame([_candidate_row("A", 0.010, "ROBUST", 0.90)])
    pick = select_best_candidate(out, held=set())
    assert pick["ticker"] == "A"
    assert pick["pretrade_tripwires"] is None
    assert pick["execution_drift"] is None


# ── Execution-drift filter (see EXECUTION_DRIFT_THRESHOLD in run_entry_
# screen.py): a candidate that's already moved meaningfully since
# qualifying is riskier to enter in EITHER direction (real 3,644-entry
# population: early-stop-out ~2-3x higher at both extremes vs. near-zero
# drift, no compensating return). Filters out, doesn't just flag.

def test_execution_drift_ok_true_when_signal_close_missing():
    ok, drift = run_entry_screen._execution_drift_ok("X", None)
    assert ok is True
    assert drift is None


def test_execution_drift_ok_true_when_live_price_unavailable(monkeypatch):
    monkeypatch.setattr(run_entry_screen, "_live_price", lambda ticker: None)
    ok, drift = run_entry_screen._execution_drift_ok("X", 100.0)
    assert ok is True
    assert drift is None


def test_execution_drift_ok_within_threshold(monkeypatch):
    # +0.5% drift, well inside the 0.9% threshold.
    monkeypatch.setattr(run_entry_screen, "_live_price", lambda ticker: 100.5)
    ok, drift = run_entry_screen._execution_drift_ok("X", 100.0)
    assert ok is True
    assert abs(drift - 0.005) < 1e-9


def test_execution_drift_ok_false_when_chased_up(monkeypatch):
    # +2% drift -- chasing a move up, beyond the 0.9% threshold.
    monkeypatch.setattr(run_entry_screen, "_live_price", lambda ticker: 102.0)
    ok, drift = run_entry_screen._execution_drift_ok("X", 100.0)
    assert ok is False
    assert abs(drift - 0.02) < 1e-9


def test_execution_drift_ok_false_when_gapped_down(monkeypatch):
    # -2% drift -- gapped down before execution, beyond the threshold
    # in the OTHER direction (both extremes are filtered, not just chasing up).
    monkeypatch.setattr(run_entry_screen, "_live_price", lambda ticker: 98.0)
    ok, drift = run_entry_screen._execution_drift_ok("X", 100.0)
    assert ok is False
    assert abs(drift - (-0.02)) < 1e-9


def test_select_best_candidate_skips_candidate_beyond_drift_threshold(monkeypatch):
    # A ranks best statically and clears the pre-entry tripwire, but has
    # already drifted +2% since qualifying -- B should be picked instead.
    monkeypatch.setattr(run_entry_screen, "_pretrade_tripwire_check",
                         _fake_tripwire({"A": True, "B": True}))

    def fake_drift(ticker, signal_close):
        return (False, 0.02) if ticker == "A" else (True, 0.001)
    monkeypatch.setattr(run_entry_screen, "_execution_drift_ok", fake_drift)

    out = pd.DataFrame([
        {**_candidate_row("A", 0.010, "ROBUST", 0.90), "category": "equities", "price": 100.0},
        {**_candidate_row("B", 0.050, "ROBUST", 0.60), "category": "equities", "price": 50.0},
    ])
    pick = select_best_candidate(out, held=set(), data_dir="dummy", gate1_candidates=["A", "B"],
                                  regime_labels={"ry_regime": "HIGH", "baa10y_regime": "TIGHT"})
    assert pick["ticker"] == "B"
    assert pick["execution_drift"] == 0.001


def test_select_best_candidate_none_when_all_fail_drift(monkeypatch):
    monkeypatch.setattr(run_entry_screen, "_pretrade_tripwire_check",
                         _fake_tripwire({"A": True, "B": True}))
    monkeypatch.setattr(run_entry_screen, "_execution_drift_ok",
                         lambda ticker, signal_close: (False, 0.02))
    out = pd.DataFrame([
        {**_candidate_row("A", 0.010, "ROBUST", 0.90), "category": "equities", "price": 100.0},
        {**_candidate_row("B", 0.050, "ROBUST", 0.60), "category": "equities", "price": 50.0},
    ])
    pick = select_best_candidate(out, held=set(), data_dir="dummy", gate1_candidates=["A", "B"],
                                  regime_labels={"ry_regime": "HIGH", "baa10y_regime": "TIGHT"})
    assert pick is None


# ── VIX review: informational, ranks today's level against its full
# history rather than a local 20d baseline (which would read "calm" even
# during a month-long elevated stretch).

def _vix_series(values, start="2020-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def test_vix_stats_percentile_is_relative_to_full_history_not_local_window():
    # 95 low days followed by 5 elevated days -- today's level (30) is only
    # slightly above the recent 5-day stretch (all ~28-30) but is at the
    # top of the FULL history, which is what should be reported.
    vix = _vix_series([15.0] * 95 + [28, 29, 29.5, 29.8, 30.0])
    stats = _vix_stats(vix)
    assert stats["now"] == 30.0
    assert stats["percentile"] > 0.9  # elevated by full-history standards


def test_vix_stats_trend_spiking():
    vix = _vix_series([15.0] * 20 + [16, 17, 19, 21, 23, 24])
    stats = _vix_stats(vix)
    assert stats["chg_5d"] == 24 - 16  # today (24, last) vs iloc[-6] (16)
    assert stats["trend"] == "spiking"


def test_vix_stats_trend_falling():
    vix = _vix_series([25.0] * 20 + [24, 22, 20, 18, 16, 15])
    stats = _vix_stats(vix)
    assert stats["trend"] == "falling"


def test_vix_stats_trend_flat_within_noise_band():
    vix = _vix_series([15.0] * 20 + [15.2, 15.1, 15.3, 15.0, 14.9, 15.1])
    stats = _vix_stats(vix)
    assert stats["trend"] == "flat"


# ── Basket-crash: secondary entry pathway (see MEMORY.md "Sector-
# capitulation reconstruction" / "Capitulation stop-sensitivity",
# 2026-07-29). Below-MA50-by-construction entries get their own trailing-
# only stop (no floor -- a floor destroyed the edge on the real population)
# and their own 1-per-sector concentration cap ahead of selection.

def test_basket_crash_binding_stop_not_armed_below_trigger():
    # +5% unrealized gain -- below the 8% trigger, no floor to fall back on.
    stop, label = basket_crash_binding_stop(100.0, peak_price=105.0)
    assert stop is None
    assert "not yet armed" in label


def test_basket_crash_binding_stop_trailing_once_armed():
    stop, label = basket_crash_binding_stop(100.0, peak_price=110.0)  # +10%, past the 8% trigger
    assert label == "TRAILING"
    assert abs(stop - 110.0 * 0.92) < 1e-9  # BASKET_TRAILING_PCT = 0.08


def _basket_row(ticker, sector, roc, peers):
    return {"ticker": ticker, "sector": sector, "roc_5d": roc, "peer_count": peers, "category": "equities"}


def test_cap_basket_crash_concentration_keeps_deepest_crash_per_sector():
    rows = [
        _basket_row("A", "Tech", -0.12, 2),
        _basket_row("B", "Tech", -0.18, 3),   # deeper crash, same sector -- wins over A
        _basket_row("C", "Energy", -0.10, 2),
    ]
    capped = cap_basket_crash_concentration(rows)
    assert {r["ticker"] for r in capped} == {"B", "C"}


def test_cap_basket_crash_concentration_tie_breaks_on_peer_count():
    rows = [
        _basket_row("A", "Tech", -0.15, 2),
        _basket_row("B", "Tech", -0.15, 4),   # same crash depth, more peers crashing -- wins
    ]
    capped = cap_basket_crash_concentration(rows)
    assert len(capped) == 1 and capped[0]["ticker"] == "B"


def test_select_best_basket_crash_picks_deepest_crash():
    rows = [_basket_row("A", "Tech", -0.11, 2), _basket_row("B", "Energy", -0.19, 2)]
    assert select_best_basket_crash(rows, held=set())["ticker"] == "B"


def test_select_best_basket_crash_excludes_held():
    rows = [_basket_row("A", "Tech", -0.19, 2), _basket_row("B", "Energy", -0.11, 2)]
    assert select_best_basket_crash(rows, held={"A"})["ticker"] == "B"


def test_select_best_basket_crash_none_when_all_held():
    assert select_best_basket_crash([_basket_row("A", "Tech", -0.19, 2)], held={"A"}) is None


def test_select_best_basket_crash_none_when_empty():
    assert select_best_basket_crash([], held=set()) is None


# ── Basket-crash execution-drift filter (added 2026-07-30 after a live
# case: SNDK's signal close was $1015.89, but had already reversed +24% to
# $1261.80 by the next session -- select_best_basket_crash now applies the
# same drift check select_best_candidate uses, tries the next-ranked
# candidate instead of the one that's drifted too far.)

def test_select_best_basket_crash_skips_candidate_beyond_drift_threshold(monkeypatch):
    def fake_drift(ticker, signal_close):
        return (False, 0.24) if ticker == "A" else (True, 0.005)
    monkeypatch.setattr(run_entry_screen, "_execution_drift_ok", fake_drift)
    rows = [
        _basket_row("A", "Tech", -0.19, 3),      # deepest crash, ranks first, but drifted +24%
        _basket_row("B", "Energy", -0.11, 2),
    ]
    pick = select_best_basket_crash(rows, held=set())
    assert pick["ticker"] == "B"
    assert pick["execution_drift"] == 0.005


def test_select_best_basket_crash_none_when_all_fail_drift(monkeypatch):
    monkeypatch.setattr(run_entry_screen, "_execution_drift_ok", lambda ticker, signal_close: (False, 0.24))
    rows = [_basket_row("A", "Tech", -0.19, 3), _basket_row("B", "Energy", -0.11, 2)]
    assert select_best_basket_crash(rows, held=set()) is None


def test_select_best_basket_crash_missing_price_fails_open(monkeypatch):
    # No live-price data available (network failure etc.) -- doesn't exclude
    # the candidate, same convention as the extension gate's drift filter.
    monkeypatch.setattr(run_entry_screen, "_live_price", lambda ticker: None)
    rows = [_basket_row("A", "Tech", -0.19, 3)]  # no "price" key -- signal_close is None
    pick = select_best_basket_crash(rows, held=set())
    assert pick["ticker"] == "A"
    assert pick["execution_drift"] is None


def _write_close_series(path, closes):
    dates = pd.date_range("2026-01-01", periods=len(closes), freq="D")
    pd.DataFrame({"date": dates, "close": closes}).to_parquet(path)


def test_basket_crash_candidates_requires_min_peers_crashing(tmp_path, monkeypatch):
    # Three Technology tickers crash together (2 same-sector peers each --
    # meets MIN_PEERS_CRASHING=2). One Industrials ticker crashes just as
    # hard but alone in its sector -- excluded. One Technology ticker is
    # flat -- excluded, and doesn't count as a "peer crashing" for the others.
    _write_close_series(tmp_path / "TECH1.parquet", [100, 100, 100, 100, 100, 85, 84, 83, 82, 81])
    _write_close_series(tmp_path / "TECH2.parquet", [100, 100, 100, 100, 100, 88, 87, 86, 85, 84])
    _write_close_series(tmp_path / "TECH3.parquet", [100, 100, 100, 100, 100, 87, 86, 85, 84, 83])
    _write_close_series(tmp_path / "TECH4.parquet", [100, 100, 100, 100, 100, 101, 102, 103, 104, 105])
    _write_close_series(tmp_path / "IND1.parquet",  [100, 100, 100, 100, 100, 85, 84, 83, 82, 81])

    monkeypatch.setattr(run_entry_screen.reader, "ticker_path",
                         lambda data_dir, cat, tkr: tmp_path / f"{tkr}.parquet")
    sectors = {"TECH1": "Technology", "TECH2": "Technology", "TECH3": "Technology",
               "TECH4": "Technology", "IND1": "Industrials"}
    monkeypatch.setattr(run_entry_screen, "_sector_of", lambda t: sectors.get(t))

    cat_of = {t: "equities" for t in sectors}
    rows = run_entry_screen.basket_crash_candidates(list(sectors), cat_of, tmp_path)
    assert {r["ticker"] for r in rows} == {"TECH1", "TECH2", "TECH3"}
    for r in rows:
        assert r["peer_count"] == 2
        assert r["sector"] == "Technology"


def test_basket_crash_candidates_empty_when_nothing_crashing(tmp_path, monkeypatch):
    _write_close_series(tmp_path / "FLAT.parquet", [100] * 10)
    monkeypatch.setattr(run_entry_screen.reader, "ticker_path",
                         lambda data_dir, cat, tkr: tmp_path / f"{tkr}.parquet")
    monkeypatch.setattr(run_entry_screen, "_sector_of", lambda t: "Technology")
    rows = run_entry_screen.basket_crash_candidates(["FLAT"], {"FLAT": "equities"}, tmp_path)
    assert rows == []
