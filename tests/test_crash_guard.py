import numpy as np
import pandas as pd

from run_combined_system import CRASH_ROC_THRESHOLD, CRASH_ROC_WINDOW, build_signals


def _series(values, start="2020-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="B")
    return pd.Series(values, index=idx)


def _flat_gold_silver(n):
    # Flat, unchanging GSR -- keeps the silver state machine INACTIVE
    # throughout so these tests isolate the guard logic only.
    gold = _series([100.0] * n)
    silver = _series([1.0] * n)
    return gold, silver


def _flat_lly(n):
    # Flat LLY, always above its own SMA/ROC thresholds -- keeps lly_stress
    # (and therefore joint) False throughout, isolating the AVGO guard tests
    # below from the newer joint-stress logic.
    return _series([500.0] * n)


def test_fast_crash_triggers_guard_before_ma_cross():
    # A steady uptrend leaves a real gap between price and its lagging 200d
    # SMA (the situation a fast crash actually happens in -- 2001-style,
    # dropping from well above trend). Then a fast -12% break over 5 days
    # that lands well short of the (much lower) SMA, isolating the crash
    # trigger from the MA trigger.
    n_up = 250
    uptrend = [100.0 * (1.003 ** i) for i in range(n_up)]
    last_price = uptrend[-1]
    crash = [last_price * (1 - pct) for pct in [0.0, 0.03, 0.06, 0.09, 0.10, 0.12]]
    # One trailing bar: signals carry a one-day execution lag (they are derived
    # from a close, so they can only act on the next bar), which means the
    # breach on the final crash bar surfaces here. Without it there is nowhere
    # for the signal to land. See run_combined_system.apply_execution_lag().
    avgo = _series(uptrend + crash + [crash[-1]])
    gold, silver = _flat_gold_silver(len(avgo))
    lly = _flat_lly(len(avgo))
    common = avgo.index

    sma200_last = avgo.rolling(200).mean().iloc[-1]
    assert crash[-1] > sma200_last, "test setup invariant: crash must land above the SMA"

    signals = build_signals(avgo, gold, silver, lly, common)
    last = signals.iloc[-1]

    assert last["guard_crash"] == True
    assert last["guard_ma"] == False  # confirmed above: price still above the 200d SMA
    assert last["guard"] == True      # combined guard fires via the crash path


def test_normal_volatility_does_not_trigger_crash_guard():
    # A typical day-to-day wobble, nowhere close to the crash threshold.
    rng = np.random.default_rng(42)
    n = 260
    rets = rng.normal(0.0005, 0.01, n)  # ~1% daily vol, no crash
    prices = 100 * np.cumprod(1 + rets)
    avgo = _series(prices.tolist())
    gold, silver = _flat_gold_silver(len(avgo))
    lly = _flat_lly(len(avgo))
    common = avgo.index

    signals = build_signals(avgo, gold, silver, lly, common)
    assert signals["guard_crash"].sum() == 0


def test_slow_decline_still_triggers_via_ma_path_not_crash():
    # A slow, grinding decline that eventually crosses the 200d SMA but
    # never drops fast enough to trip the crash-ROC threshold.
    n = 400
    # Slow linear decline: -0.15%/day, gentle enough to never hit -10%
    # over any CRASH_ROC_WINDOW-day stretch.
    prices = [100.0 * (1 - 0.0015) ** i for i in range(n)]
    avgo = _series(prices)
    gold, silver = _flat_gold_silver(len(avgo))
    lly = _flat_lly(len(avgo))
    common = avgo.index

    signals = build_signals(avgo, gold, silver, lly, common)
    last = signals.iloc[-1]

    assert last["guard_ma"] == True
    assert last["guard_crash"] == False
    assert last["guard"] == True  # combined guard still fires, via the MA path


def test_guard_crash_self_clears_after_recovery():
    # A sharp dip that recovers quickly, without ever breaching the 200d
    # SMA -- the crash flag should clear once the rolling window rolls
    # past the drop, not stay stuck active.
    n_flat = 250
    prices = [100.0] * n_flat
    dip_and_recover = [100.0, 88.0, 87.0, 89.0, 95.0, 100.0, 101.0, 102.0, 102.0, 102.0]
    avgo = _series(prices + dip_and_recover)
    gold, silver = _flat_gold_silver(len(avgo))
    lly = _flat_lly(len(avgo))
    common = avgo.index

    signals = build_signals(avgo, gold, silver, lly, common)
    # Some day in the dip should have fired the crash guard...
    assert signals["guard_crash"].any()
    # ...but the most recent days (after recovery) should not still be active.
    assert signals["guard_crash"].iloc[-3:].sum() == 0
    assert signals["guard"].iloc[-1] == False


def test_crash_threshold_constants_unchanged_from_validated_values():
    # Regression guard: these were empirically validated (20-cell grid,
    # robust across both AVGO's own history and the TXN analog) -- a
    # silent change here should fail loudly, not drift unnoticed.
    assert CRASH_ROC_WINDOW == 5
    assert CRASH_ROC_THRESHOLD == -0.10
