import datetime as dt

import pandas as pd

import run_entry_screen
from run_entry_screen import binding_stop, select_best_candidate, suggested_duration_days


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
