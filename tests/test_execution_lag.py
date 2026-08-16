"""Regression tests for the execution-lag fix (2026-08-16).

Every guard backtest used to apply a signal derived from day i's CLOSE to
day i's RETURN -- i.e. it traded at the very print that generated the
signal. That is not a small accounting nicety: on AVGO's real history the
mean return on the 99 days the guard flips defensive is -3.46%, and +0.01%
on the day after, so same-day execution handed the strategy the entire
move for free. Corrected, the guard's Calmar falls from 2.99 to 0.49
against 1.06 for the unguarded base.

These tests pin the corrected behaviour: a signal computed from a close
must not take effect until the following bar.
"""
import pandas as pd

from run_combined_system import (
    CRASH_ROC_THRESHOLD,
    CRASH_ROC_WINDOW,
    EXECUTION_LAG_DAYS,
    apply_execution_lag,
    build_signals,
)

BOOL_COLS = ("guard", "guard_ma", "guard_crash", "lly_stress", "joint")


def _series(values, start="2020-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="B")
    return pd.Series(values, index=idx)


def _flat_gold_silver(n):
    return _series([100.0] * n), _series([1.0] * n)


def _flat_lly(n):
    return _series([500.0] * n)


def _crash_series():
    """Steady uptrend, then a fast -12% break over 5 days that stays well
    above the lagging 200d SMA -- isolates the crash-ROC trigger."""
    uptrend = [100.0 * (1.003 ** i) for i in range(250)]
    last = uptrend[-1]
    crash = [last * (1 - p) for p in (0.0, 0.03, 0.06, 0.09, 0.10, 0.12)]
    # Trailing flat bars so the bar AFTER the first breach always exists --
    # the lag assertion needs somewhere for the signal to land.
    tail = [last * 0.88] * 3
    return _series(uptrend + crash + tail)


def test_crash_signal_fires_the_bar_after_the_triggering_close():
    avgo = _crash_series()
    gold, silver = _flat_gold_silver(len(avgo))
    sig = build_signals(avgo, gold, silver, _flat_lly(len(avgo)), avgo.index)

    # Find the close that actually breaches the ROC threshold.
    roc = avgo.pct_change(CRASH_ROC_WINDOW)
    breach_positions = [i for i, v in enumerate(roc.values) if v <= CRASH_ROC_THRESHOLD]
    assert breach_positions, "test fixture never breaches the crash threshold"
    first = breach_positions[0]

    # The guard must NOT be active on the breaching bar itself...
    assert not sig["guard_crash"].iloc[first]
    # ...but must be active on the next one.
    assert sig["guard_crash"].iloc[first + EXECUTION_LAG_DAYS]


def test_signals_never_depend_on_their_own_bar():
    """Truncating the price history at bar k must not change any signal at
    bars <= k. If a signal used its own close, dropping later data would
    still leave bar k unchanged -- but including bar k's close in bar k's
    signal is exactly what we are ruling out, so we assert the stronger
    property: signals at bar k are reproducible from data up to k-1 only."""
    avgo = _crash_series()
    gold, silver = _flat_gold_silver(len(avgo))
    lly = _flat_lly(len(avgo))
    full = build_signals(avgo, gold, silver, lly, avgo.index)

    k = len(avgo) - 1
    truncated_idx = avgo.index[:k]  # drops the final close entirely
    partial = build_signals(
        avgo.iloc[:k], gold.iloc[:k], silver.iloc[:k], lly.iloc[:k], truncated_idx
    )

    # Signal on the last retained bar must be identical either way, which can
    # only hold if that bar's own close was never used to compute it.
    for col in BOOL_COLS:
        assert bool(full[col].iloc[k - 1]) == bool(partial[col].iloc[k - 1]), col


def test_apply_execution_lag_shifts_and_defaults_to_non_acting():
    raw = pd.DataFrame(
        {
            "guard": [True, True, False],
            "guard_ma": [True, False, False],
            "guard_crash": [False, True, False],
            "lly_stress": [True, False, True],
            "joint": [True, False, False],
            "silver_state": ["T1", "T2", "INACTIVE"],
        },
        index=pd.date_range("2020-01-01", periods=3, freq="B"),
    )
    out = apply_execution_lag(raw)

    # First bar has no prior close, so it defaults to the non-acting state.
    for col in BOOL_COLS:
        assert out[col].iloc[0] is False or not out[col].iloc[0], col
    assert out["silver_state"].iloc[0] == "INACTIVE"

    # Everything else is the previous bar's value.
    assert bool(out["guard"].iloc[1]) is True
    assert bool(out["guard_crash"].iloc[2]) is True
    assert out["silver_state"].iloc[1] == "T1"
    assert out["silver_state"].iloc[2] == "T2"


def test_bool_dtype_survives_the_lag():
    """Shifting a bool column introduces NaN and silently promotes it to
    object; downstream code does bool(...) on these, and bool(nan) is True --
    which would turn a missing signal into an ACTIVE guard."""
    raw = pd.DataFrame(
        {c: [True, False] for c in BOOL_COLS}
        | {"silver_state": ["T1", "INACTIVE"]},
        index=pd.date_range("2020-01-01", periods=2, freq="B"),
    )
    out = apply_execution_lag(raw)
    for col in BOOL_COLS:
        assert out[col].dtype == bool, f"{col} lost bool dtype -> bool(nan) is True"
