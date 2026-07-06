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


def test_no_allowed_candidate_defensively_falls_back_to_gold():
    current = {"GC_F": 0.216, "AVGO": 0.070, "LLY": 0.148}
    target = {"GC_F": 0.250, "AVGO": 0.550, "LLY": 0.200}
    allowed = {"GC_F": False, "AVGO": False, "LLY": False}  # shouldn't happen in practice

    best, _ = next_contribution_target(current, target, allowed)

    assert best == "GC_F"


def test_missing_ticker_in_inputs_defaults_to_zero():
    best, detail = next_contribution_target({}, {}, ALL_OPEN)

    assert best == "GC_F"  # all gaps 0.0 -- first candidate in iteration order wins ties
    assert detail["GC_F"]["gap"] == 0.0
