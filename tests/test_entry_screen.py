import pandas as pd

from run_entry_screen import binding_stop, select_best_candidate


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
