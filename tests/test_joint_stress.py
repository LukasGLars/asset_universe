import pandas as pd

from run_combined_system import (
    CRASH_ROC_THRESHOLD,
    CRASH_ROC_WINDOW,
    JOINT_WEIGHTS,
    WEIGHTS,
    build_signals,
    run_strategy,
)


def _series(values, start="2020-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="B")
    return pd.Series(values, index=idx)


def _flat_gold_silver(n):
    gold = _series([100.0] * n)
    silver = _series([1.0] * n)
    return gold, silver


def _steady_uptrend(n, daily=0.0005, start_price=100.0):
    return _series([start_price * (1 + daily) ** i for i in range(n)])


def _hold(values):
    """Append one trailing bar repeating the last price.

    build_signals() applies a one-day execution lag -- a signal derived from a
    close can only act on the NEXT bar -- so a fixture that ends on its
    triggering bar leaves the signal nowhere to surface. The extra bar is what
    `signals.iloc[-1]` then reads. See run_combined_system.apply_execution_lag().
    """
    return values + [values[-1]]


def test_joint_requires_both_avgo_guard_and_lly_stress():
    # AVGO crashes fast; LLY stays in a steady uptrend the whole time --
    # guard should fire, lly_stress should not, joint should not.
    n_up = 250
    avgo_up = [100.0 * (1.003 ** i) for i in range(n_up)]
    avgo_crash = [avgo_up[-1] * (1 - pct) for pct in [0.0, 0.05, 0.10, 0.12]]
    avgo = _series(_hold(avgo_up + avgo_crash))
    lly = _steady_uptrend(len(avgo), daily=0.001, start_price=500.0)
    gold, silver = _flat_gold_silver(len(avgo))
    common = avgo.index

    signals = build_signals(avgo, gold, silver, lly, common)
    last = signals.iloc[-1]

    assert last["guard"] == True
    assert last["lly_stress"] == False
    assert last["joint"] == False


def test_joint_fires_when_both_stressed_simultaneously():
    # Both AVGO and LLY crash together over the same window.
    n_up = 250
    up = [100.0 * (1.003 ** i) for i in range(n_up)]
    crash = [up[-1] * (1 - pct) for pct in [0.0, 0.05, 0.10, 0.12]]
    avgo = _series(_hold(up + crash))
    lly = _series(_hold([500.0 * (v / up[0]) for v in up] +
                  [500.0 * up[-1] / up[0] * (1 - pct) for pct in [0.0, 0.06, 0.11, 0.13]]))
    gold, silver = _flat_gold_silver(len(avgo))
    common = avgo.index

    signals = build_signals(avgo, gold, silver, lly, common)
    last = signals.iloc[-1]

    assert last["guard"] == True
    assert last["lly_stress"] == True
    assert last["joint"] == True


def test_lly_stress_alone_without_avgo_guard_is_not_joint():
    # LLY crashes; AVGO stays in a steady uptrend -- joint should not fire,
    # by design (the rule only escalates when AVGO's own guard is already
    # active, not on LLY weakness alone).
    n_up = 250
    lly_up = [500.0 * (1.003 ** i) for i in range(n_up)]
    lly_crash = [lly_up[-1] * (1 - pct) for pct in [0.0, 0.05, 0.10, 0.12]]
    lly = _series(_hold(lly_up + lly_crash))
    avgo = _steady_uptrend(len(lly), daily=0.001, start_price=100.0)
    gold, silver = _flat_gold_silver(len(avgo))
    common = avgo.index

    signals = build_signals(avgo, gold, silver, lly, common)
    last = signals.iloc[-1]

    assert last["guard"] == False
    assert last["lly_stress"] == True
    assert last["joint"] == False


def test_joint_weights_escalate_to_full_gold_and_fund_silver_from_gold():
    assert JOINT_WEIGHTS["INACTIVE"] == {"GC_F": 1.000, "AVGO": 0.000, "LLY": 0.000, "SI_F": 0.000}
    # Silver funded from Gold (not AVGO, which is already 0 in this state).
    assert JOINT_WEIGHTS["T1"]["SI_F"] == 0.120
    assert JOINT_WEIGHTS["T1"]["AVGO"] == 0.000
    assert JOINT_WEIGHTS["T1"]["GC_F"] == 1.000 - 0.120
    assert JOINT_WEIGHTS["T2"]["GC_F"] == 1.000 - 0.170


def test_run_strategy_uses_joint_weights_only_when_use_joint_true():
    n_up = 250
    up = [100.0 * (1.003 ** i) for i in range(n_up)]
    crash = [up[-1] * (1 - pct) for pct in [0.0, 0.06, 0.11, 0.13]]
    avgo = _series(up + crash)
    lly = _series([500.0 * (v / up[0]) for v in up] +
                  [500.0 * up[-1] / up[0] * (1 - pct) for pct in [0.0, 0.06, 0.11, 0.13]])
    gold, silver = _flat_gold_silver(len(avgo))
    common = avgo.index
    prices = {"GC_F": gold, "AVGO": avgo, "LLY": lly, "SI_F": silver}

    signals = build_signals(avgo, gold, silver, lly, common)
    assert signals.iloc[-1]["joint"] == True

    eq_no_joint, _ = run_strategy(prices, signals, use_guard=True, use_silver=True,
                                   label="D", use_joint=False)
    eq_joint, _ = run_strategy(prices, signals, use_guard=True, use_silver=True,
                                label="E", use_joint=True)

    # With joint stress active on the last day, the two strategies must
    # actually diverge (E holds 100% Gold, D holds Gold 52.5%/LLY 47.5%).
    assert eq_no_joint.iloc[-1] != eq_joint.iloc[-1]


def test_avgo_guard_alone_state_unaffected_when_joint_not_requested():
    # Regression: passing use_joint=False must reproduce the pre-existing
    # (True, silver_state) WEIGHTS lookup exactly, even on a day where joint
    # would have fired if requested.
    n_up = 250
    up = [100.0 * (1.003 ** i) for i in range(n_up)]
    crash = [up[-1] * (1 - pct) for pct in [0.0, 0.06, 0.11, 0.13]]
    avgo = _series(up + crash)
    lly = _series([500.0 * (v / up[0]) for v in up] +
                  [500.0 * up[-1] / up[0] * (1 - pct) for pct in [0.0, 0.06, 0.11, 0.13]])
    gold, silver = _flat_gold_silver(len(avgo))
    common = avgo.index
    prices = {"GC_F": gold, "AVGO": avgo, "LLY": lly, "SI_F": silver}

    signals = build_signals(avgo, gold, silver, lly, common)
    eq_no_joint, _ = run_strategy(prices, signals, use_guard=True, use_silver=False,
                                   label="B", use_joint=False)

    # Reconstruct expected return manually from the plain WEIGHTS table.
    rets = {t: prices[t].reindex(common).pct_change() for t in prices}
    expected = pd.Series(0.0, index=common)
    prev_w = None
    for i in range(len(common)):
        g = bool(signals["guard"].iloc[i])
        w = WEIGHTS[(g, "INACTIVE")]
        if prev_w is not None and w != prev_w:
            cost = sum(0.0010 for a in set(list(w) + list(prev_w))
                       if abs(w.get(a, 0) - prev_w.get(a, 0)) > 0.005)
            expected.iloc[i] -= cost
        r = sum(wt * (rets[a].iloc[i] if not pd.isna(rets[a].iloc[i]) else 0.0)
                for a, wt in w.items())
        expected.iloc[i] += r
        prev_w = w
    expected_eq = (1 + expected).cumprod()

    assert abs(eq_no_joint.iloc[-1] - expected_eq.iloc[-1]) < 1e-9
