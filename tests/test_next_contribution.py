import pytest

from next_contribution import next_contribution_target

ALL_OPEN = {"GC_F": True, "AVGO": True, "LLY": True}


def test_picks_most_underweight_among_allowed():
    current = {"GC_F": 0.216, "AVGO": 0.070, "LLY": 0.148}
    target = {"GC_F": 0.250, "AVGO": 0.550, "LLY": 0.200}

    best, detail = next_contribution_target(current, target, ALL_OPEN)

    assert best == "AVGO"
    assert detail["AVGO"]["gap"] > detail["LLY"]["gap"] > detail["GC_F"]["gap"]


def test_skips_gated_asset_even_if_most_underweight():
    current = {"GC_F": 0.216, "AVGO": 0.070, "LLY": 0.148}
    target = {"GC_F": 0.250, "AVGO": 0.550, "LLY": 0.200}
    allowed = {"GC_F": True, "AVGO": False, "LLY": True}  # AVGO guard active

    best, detail = next_contribution_target(current, target, allowed)

    assert best == "LLY"  # next-biggest gap among allowed
    assert detail["AVGO"]["allowed"] is False


def test_joint_stress_falls_through_to_gold():
    # AVGO guard active AND LLY independently stressed -> both gated closed.
    current = {"GC_F": 0.216, "AVGO": 0.070, "LLY": 0.148}
    target = {"GC_F": 1.000, "AVGO": 0.000, "LLY": 0.000}  # JOINT_WEIGHTS["INACTIVE"]
    allowed = {"GC_F": True, "AVGO": False, "LLY": False}

    best, detail = next_contribution_target(current, target, allowed)

    assert best == "GC_F"
    assert detail["AVGO"]["allowed"] is False
    assert detail["LLY"]["allowed"] is False


def test_all_at_or_above_target_picks_least_overweight():
    current = {"GC_F": 0.260, "AVGO": 0.650, "LLY": 0.300}
    target = {"GC_F": 0.250, "AVGO": 0.550, "LLY": 0.200}

    best, detail = next_contribution_target(current, target, ALL_OPEN)

    # All gaps negative -- least-overweight (closest to zero) should win.
    assert best == "GC_F"
    assert round(detail["GC_F"]["gap"], 2) == -0.01


def test_no_allowed_candidate_falls_back_to_the_largest_gap():
    """Changed 2026-10-09. This used to fall back to a hardcoded "GC_F",
    which was safe only while the candidate set was literally Gold/AVGO/LLY.
    The set now comes from the live per-asset targets, so a hardcoded ticker
    could name an asset that is not in them at all. Falls back to the widest
    gap instead."""
    current = {"GC_F": 0.216, "AVGO": 0.070, "LLY": 0.148}
    target = {"GC_F": 0.250, "AVGO": 0.550, "LLY": 0.200}
    allowed = {"GC_F": False, "AVGO": False, "LLY": False}  # shouldn't happen in practice

    best, _ = next_contribution_target(current, target, allowed)

    assert best == "AVGO"  # gap +0.480, vs GC_F +0.034 and LLY +0.052


def test_empty_targets_raise_rather_than_guessing_an_asset():
    """An empty target is a config failure. Returning some asset anyway is how
    a broken portfolio.toml would turn into a real trade instruction."""
    import pytest

    with pytest.raises(ValueError, match="no target weights"):
        next_contribution_target({}, {}, ALL_OPEN)


def test_candidate_set_comes_from_the_targets_not_a_hardcoded_list():
    """The whole point of the 2026-10-09 change: assets the old CANDIDATES
    list had never heard of must be routable."""
    current = {"LF Global Index": 0.10, "Reactor Core Cash": 0.02}
    target = {"LF Global Index": 0.25, "Reactor Core Cash": 0.10}
    best, detail = next_contribution_target(
        current, target, {"LF Global Index": True, "Reactor Core Cash": True})

    assert best == "LF Global Index"      # gap +0.15 vs +0.08
    assert set(detail) == {"LF Global Index", "Reactor Core Cash"}


def test_an_excluded_asset_still_reports_its_real_gap():
    """Callers exclude via allowed=False, not by omitting the target, so the
    operator can still see that e.g. the crypto sleeve is underweight even
    though contributions never fund it."""
    current = {"AVGO": 0.24, "BTC": 0.01}
    target = {"AVGO": 0.20, "BTC": 0.025}
    best, detail = next_contribution_target(
        current, target, {"AVGO": True, "BTC": False})

    assert best == "AVGO"
    assert detail["BTC"]["allowed"] is False
    assert detail["BTC"]["gap"] == pytest.approx(0.015)
