import pandas as pd

import run_avgo_guard_graduated_response as gr


def test_interp_weights_endpoints_and_midpoint():
    none_w = gr.NONE_WEIGHTS["INACTIVE"]
    full_w = gr.FULL_WEIGHTS["INACTIVE"]
    assert gr._interp_weights("INACTIVE", 0.0) == none_w
    assert gr._interp_weights("INACTIVE", 1.0) == full_w
    mid = gr._interp_weights("INACTIVE", 0.5)
    assert abs(mid["X"] - (none_w["X"] + full_w["X"]) / 2) < 1e-9
    assert abs(mid["G"] - (none_w["G"] + full_w["G"]) / 2) < 1e-9


def test_basket_confirmed_series_flags_days_with_enough_crashing_peers():
    dates = pd.date_range("2020-01-01", periods=20, freq="D")
    avgo = pd.Series([100.0] * 20, index=dates)

    peer1 = pd.Series([100.0] * 20, index=dates)
    peer1.iloc[10] = 85.0  # -15% over 5d at date 10 -> crashing
    peer2 = pd.Series([100.0] * 20, index=dates)
    peer2.iloc[10] = 88.0  # -12% over 5d at date 10 -> crashing
    peer3 = pd.Series([100.0] * 20, index=dates)  # never crashes

    basket = gr.basket_confirmed_series(avgo, {"P1": peer1, "P2": peer2, "P3": peer3})
    assert bool(basket.loc[dates[10]]) is True
    assert bool(basket.loc[dates[5]]) is False


def test_run_at_rotation_one_matches_full_flip_on_a_basket_day(monkeypatch):
    # Rising ramp (not flat) so the 200d MA trails well BELOW the crash-day
    # price even after a -12% drop -- isolates the crash-ROC trigger from
    # the 200d MA guard, which a flat series can't do (any dip below a
    # near-constant price trivially also breaches a near-constant MA).
    n = 310
    dates = pd.date_range("2020-01-01", periods=n, freq="D")
    avgo = pd.Series([100.0 + i * 0.5 for i in range(n)], index=dates)
    gold = pd.Series([100.0] * n, index=dates)
    lly = pd.Series([100.0] * n, index=dates)
    silver = pd.Series([2.0] * n, index=dates)  # GSR = 100/2 = 50, well below T1 -> INACTIVE

    crash_day = 300
    avgo.iloc[crash_day] = avgo.iloc[crash_day - 5] * 0.88  # exactly -12% over 5d
    basket = pd.Series(False, index=dates)
    basket.iloc[crash_day] = True

    eq_full = gr.run(avgo, gold, lly, silver, basket, dates[0], rotation_fraction=1.0)
    eq_none = gr.run(avgo, gold, lly, silver, basket, dates[0], rotation_fraction=0.0)

    ret_full = eq_full.pct_change().loc[dates[crash_day]]
    ret_none = eq_none.pct_change().loc[dates[crash_day]]
    # AVGO down -12% that day: NONE keeps 55% AVGO exposure (worse hit),
    # FULL removes it entirely (better that specific day) -- confirms the
    # rotation_fraction actually changes exposure on a basket day, i.e.
    # the crash-ROC trigger fired without also tripping the 200d MA guard.
    assert ret_full > ret_none
