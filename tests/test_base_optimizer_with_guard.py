import run_combined_system as rcs
from run_base_optimizer_with_guard import build_weight_tables


def test_build_weight_tables_reproduces_live_strategy_exactly():
    """The whole point of this generalization is that it must be provably
    faithful to the hand-built, already-validated WEIGHTS/JOINT_WEIGHTS
    tables at the live 25/55/20 split -- not just "close enough"."""
    weights, joint_weights = build_weight_tables(0.25, 0.55, 0.20)

    for key, expected in rcs.WEIGHTS.items():
        got = weights[key]
        for asset, w in expected.items():
            assert abs(got[asset] - w) < 1e-9, f"{key} {asset}: {got[asset]} != {w}"

    for key, expected in rcs.JOINT_WEIGHTS.items():
        got = joint_weights[key]
        for asset, w in expected.items():
            assert abs(got[asset] - w) < 1e-9, f"{key} {asset}: {got[asset]} != {w}"


def test_build_weight_tables_base_states_sum_to_one():
    for gold, avgo, lly in [(0.30, 0.50, 0.20), (0.10, 0.80, 0.10), (0.0, 1.0, 0.0), (0.5, 0.0, 0.5)]:
        weights, joint_weights = build_weight_tables(gold, avgo, lly)
        for key, w in weights.items():
            assert abs(sum(w.values()) - 1.0) < 1e-9, f"{key} at ({gold},{avgo},{lly}) sums to {sum(w.values())}"
        for key, w in joint_weights.items():
            assert abs(sum(w.values()) - 1.0) < 1e-9, f"joint {key} sums to {sum(w.values())}"


def test_build_weight_tables_guard_redistributes_avgo_50_50():
    # A base split with AVGO=0.40 should send 0.20 to Gold and 0.20 to LLY
    # on guard, regardless of the original Gold/LLY ratio (same 50/50 rule
    # the live 25/55/20 table follows, not proportional to base weights).
    weights, _ = build_weight_tables(0.10, 0.40, 0.50)
    guard_state = weights[(True, "INACTIVE")]
    assert abs(guard_state["GC_F"] - 0.30) < 1e-9  # 0.10 + 0.40/2
    assert abs(guard_state["LLY"] - 0.70) < 1e-9   # 0.50 + 0.40/2
    assert guard_state["AVGO"] == 0.0


def test_build_weight_tables_silver_funds_from_avgo_in_base_from_gold_in_guard():
    weights, _ = build_weight_tables(0.25, 0.55, 0.20)
    # Base mode: silver funds from AVGO, Gold/LLY untouched.
    assert weights[(False, "T1")]["GC_F"] == 0.25
    assert weights[(False, "T1")]["LLY"] == 0.20
    assert abs(weights[(False, "T1")]["AVGO"] - 0.43) < 1e-9
    # Guard mode: silver funds from Gold, LLY untouched.
    assert weights[(True, "T1")]["LLY"] == weights[(True, "INACTIVE")]["LLY"]
    assert abs(weights[(True, "T1")]["GC_F"] - (weights[(True, "INACTIVE")]["GC_F"] - 0.12)) < 1e-9


def test_joint_weights_full_flight_to_gold_minus_silver():
    _, joint_weights = build_weight_tables(0.10, 0.70, 0.20)
    # Joint-stress weights don't depend on the base split at all.
    assert joint_weights["INACTIVE"]["GC_F"] == 1.0
    assert abs(joint_weights["T1"]["GC_F"] - 0.88) < 1e-9
    assert abs(joint_weights["T2"]["GC_F"] - 0.83) < 1e-9
