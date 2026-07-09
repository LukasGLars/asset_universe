import datetime as dt

import pandas as pd

import run_entry_screen
from run_entry_screen import (
    binding_stop, select_best_candidate, suggested_duration_days, _vix_stats,
    sleeve_risk_state, _tripwire_detail_line, _risk_to_stop_str,
)


def _tw(rs_20d=0.091, rs_ok=True, regime_changed=False, cluster_breakdown=False,
        cluster_avg=-0.069, peer_rets=None, ma50_slope=10.68, ma50_rising=True):
    return {
        "rs_20d": rs_20d, "rs_ok": rs_ok,
        "regime_changed": regime_changed,
        "peer_rets": peer_rets if peer_rets is not None else {"GEV": -0.088, "VRT": -0.051, "PWR": -0.075, "CMI": -0.062},
        "cluster_avg": cluster_avg, "cluster_breakdown": cluster_breakdown,
        "ma50_slope": ma50_slope, "ma50_rising": ma50_rising,
    }


def test_tripwire_detail_line_all_clean():
    line = _tripwire_detail_line(_tw())
    assert "RS +9.1% [OK]" in line
    assert "Regime stable [OK]" in line
    assert "MA50 slope +10.68 [OK]" in line
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
    assert "MA50 slope n/a" in line


def test_risk_to_stop_str_computes_kr_and_pct():
    trig = {"current_price": 271.58, "binding_stop": 271.39}
    result = _risk_to_stop_str(trig, shares=11, fx_at_entry=9.734390258789062, capital_sek=29653.19)
    assert result is not None
    assert "kr" in result and "%" in result


def test_risk_to_stop_str_none_when_missing_data():
    assert _risk_to_stop_str({"current_price": None, "binding_stop": 271.39}, 11, 9.73, 29653.19) is None


def test_binding_stop_ma50_binds_below_crossover():
    # entry $720.04, MA50 $708.66 -> hard stop $705.64 < MA50, so MA50 is
    # the closer/binding stop (hit first as price falls from entry).
    stop, label = binding_stop(720.04, 708.66)
    assert label == "MA50"
    assert stop == 708.66


def test_binding_stop_hard_stop_binds_above_crossover():
    # entry $730, MA50 $708.66 -> hard stop $715.40 > MA50, so the hard
    # stop is now closer to entry and binds first instead.
    stop, label = binding_stop(730.0, 708.66)
    assert label == "HARD"
    assert stop == 715.40


def test_binding_stop_at_exact_crossover():
    # entry chosen so hard_stop == ma50 exactly (708.66 / 0.98 = 723.1224...)
    entry = 708.66 / 0.98
    stop, label = binding_stop(entry, 708.66)
    assert abs(stop - 708.66) < 1e-6
    # at the exact crossover either label is defensible; MA50 wins ties
    assert label == "MA50"


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
    earn = dt.date(2026, 7, 30)  # 30 calendar days out
    # min(30 flat, (30 - 3) earnings-buffer) = 27
    assert suggested_duration_days(earn, today) == 27


def test_suggested_duration_flat_30_when_earnings_far_out():
    today = dt.date(2026, 6, 30)
    earn = dt.date(2026, 9, 1)  # far beyond the flat 30d window
    assert suggested_duration_days(earn, today) == 30


def test_suggested_duration_no_earnings_date_defaults_flat_30():
    assert suggested_duration_days(None, dt.date(2026, 6, 30)) == 30


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
