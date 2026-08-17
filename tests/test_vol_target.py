import numpy as np
import pandas as pd
import pytest

from vol_target import (
    BASE_WEIGHTS,
    MAX_MULT,
    MIN_MULT,
    REBAL_BAND,
    VOL_WINDOW,
    apply_silver_funding,
    compute_vol_target_weights,
    rebalance_instructions,
)


def _prices_from_returns(returns, start="2010-01-01"):
    idx = pd.date_range(start, periods=len(returns) + 1, freq="B")
    prices = [100.0]
    for r in returns:
        prices.append(prices[-1] * (1 + r))
    return pd.Series(prices, index=idx)


def test_insufficient_history_raises():
    prices = _prices_from_returns([0.01] * 5)
    with pytest.raises(ValueError):
        compute_vol_target_weights(prices)


def test_constant_vol_scalar_near_one_and_weights_match_base():
    # Alternating +/-2% every day: every rolling window has identical std,
    # so the expanding long-run average converges to the same value as the
    # trailing window -- scalar should land at ~1.0, weights at ~base.
    n = 300
    returns = [0.02 if i % 2 == 0 else -0.02 for i in range(n)]
    prices = _prices_from_returns(returns)

    result = compute_vol_target_weights(prices)

    assert result["scalar"] == pytest.approx(1.0, abs=0.01)
    assert result["weights"]["AVGO"] == pytest.approx(BASE_WEIGHTS["AVGO"], abs=0.01)
    assert result["weights"]["GC_F"] == pytest.approx(BASE_WEIGHTS["GC_F"], abs=0.01)
    assert result["weights"]["LLY"] == pytest.approx(BASE_WEIGHTS["LLY"], abs=0.01)


def test_recent_vol_spike_cuts_avgo_weight_to_the_floor():
    # Long calm history, then a violent burst for the final VOL_WINDOW days --
    # trailing vol is dominated by the burst, long-run average is not.
    calm = [0.002 if i % 2 == 0 else -0.002 for i in range(250)]
    burst = [0.10 if i % 2 == 0 else -0.10 for i in range(VOL_WINDOW)]
    prices = _prices_from_returns(calm + burst)

    result = compute_vol_target_weights(prices)

    assert result["scalar"] == pytest.approx(MIN_MULT, abs=1e-6)
    assert result["weights"]["AVGO"] == pytest.approx(BASE_WEIGHTS["AVGO"] * MIN_MULT, abs=1e-6)
    # freed weight lands on Gold/LLY in their 25:35 ratio
    freed = BASE_WEIGHTS["AVGO"] - result["weights"]["AVGO"]
    assert result["weights"]["GC_F"] == pytest.approx(BASE_WEIGHTS["GC_F"] + freed * (0.25 / 0.60), abs=1e-6)
    assert result["weights"]["LLY"] == pytest.approx(BASE_WEIGHTS["LLY"] + freed * (0.35 / 0.60), abs=1e-6)


def test_recent_calm_after_choppy_history_raises_avgo_weight_to_the_cap():
    # Long choppy history, then a very calm final VOL_WINDOW days --
    # trailing vol is far below the long-run average.
    choppy = [0.06 if i % 2 == 0 else -0.06 for i in range(250)]
    calm = [0.001 if i % 2 == 0 else -0.001 for i in range(VOL_WINDOW)]
    prices = _prices_from_returns(choppy + calm)

    result = compute_vol_target_weights(prices)

    assert result["scalar"] == pytest.approx(MAX_MULT, abs=1e-6)
    assert result["weights"]["AVGO"] == pytest.approx(BASE_WEIGHTS["AVGO"] * MAX_MULT, abs=1e-6)


def test_weights_always_sum_to_one():
    rng = np.random.default_rng(7)
    returns = rng.normal(0.0005, 0.03, 400)
    prices = _prices_from_returns(list(returns))

    result = compute_vol_target_weights(prices)

    assert sum(result["weights"].values()) == pytest.approx(1.0, abs=1e-9)


def test_never_uses_the_most_recent_return_alone_to_spike_trailing_vol():
    # A single huge one-day move at the very end should be smoothed by the
    # 21-day rolling window, not treated as if it alone determines vol --
    # sanity check that this is a rolling std, not a single-bar read.
    calm = [0.001 if i % 2 == 0 else -0.001 for i in range(250)]
    prices = _prices_from_returns(calm + [0.001, -1.0])  # one -100% single-day print
    # (unrealistic magnitude deliberately -- just proving it's not a 1-bar signal)

    result = compute_vol_target_weights(prices)

    # trailing_vol reflects a 21-day window containing one extreme bar among
    # otherwise calm ones -- material but not the entire scalar's basis.
    assert result["trailing_vol"] > result["long_run_vol"]
    assert result["scalar"] < 1.0


def test_silver_funding_comes_from_avgo_only_gold_and_lly_untouched():
    vt = {"AVGO": 0.40, "GC_F": 0.25, "LLY": 0.35}
    funded = apply_silver_funding(vt, 0.12)
    assert funded == {"GC_F": 0.25, "AVGO": 0.28, "LLY": 0.35, "SI_F": 0.12}


def test_silver_funding_zero_when_inactive():
    vt = {"AVGO": 0.40, "GC_F": 0.25, "LLY": 0.35}
    funded = apply_silver_funding(vt, 0.0)
    assert funded == {"GC_F": 0.25, "AVGO": 0.40, "LLY": 0.35, "SI_F": 0.0}


def test_silver_funding_caps_at_available_avgo_weight_when_vol_target_floor_bites():
    # AVGO's vol-targeted weight can floor as low as MIN_MULT x base (0.12),
    # below T2's 0.17 need -- silver must cap at what's available, not go
    # negative and not reach into Gold/LLY.
    vt = {"AVGO": BASE_WEIGHTS["AVGO"] * MIN_MULT, "GC_F": 0.45, "LLY": 0.43}  # AVGO = 0.12
    funded = apply_silver_funding(vt, 0.17)
    assert funded["AVGO"] == pytest.approx(0.0, abs=1e-9)
    assert funded["SI_F"] == pytest.approx(0.12, abs=1e-9)  # capped, not 0.17
    assert funded["GC_F"] == pytest.approx(0.45, abs=1e-9)  # untouched
    assert funded["LLY"] == pytest.approx(0.43, abs=1e-9)   # untouched


# ── rebalance_instructions ──────────────────────────────────────────────────

_REAL_CURRENT = {"GC_F": 0.305, "AVGO": 0.468, "LLY": 0.223}
_REAL_TARGET  = {"GC_F": 0.277, "AVGO": 0.335, "LLY": 0.388}
_REAL_PRICES  = {"GC_F": 810.0, "AVGO": 3741.0, "LLY": 11235.0}
_REAL_RC_TOTAL = 807_501.0


def test_in_band_asset_holds_no_shares_no_action():
    result = rebalance_instructions(_REAL_CURRENT, _REAL_TARGET, _REAL_PRICES, _REAL_RC_TOTAL)
    assert result["GC_F"]["out_of_band"] is False
    assert result["GC_F"]["action"] == "HOLD"
    assert result["GC_F"]["shares"] == 0


def test_overweight_asset_out_of_band_recommends_sell():
    result = rebalance_instructions(_REAL_CURRENT, _REAL_TARGET, _REAL_PRICES, _REAL_RC_TOTAL)
    avgo = result["AVGO"]
    assert avgo["out_of_band"] is True
    assert avgo["action"] == "SELL"
    assert avgo["gap"] < 0
    assert avgo["shares"] > 0
    # gap ~ -13.3% of ~807,501 kr =~ -107,400 kr =~ 28-29 shares at 3,741 kr
    assert avgo["shares"] == pytest.approx(29, abs=1)


def test_underweight_asset_out_of_band_recommends_buy():
    result = rebalance_instructions(_REAL_CURRENT, _REAL_TARGET, _REAL_PRICES, _REAL_RC_TOTAL)
    lly = result["LLY"]
    assert lly["out_of_band"] is True
    assert lly["action"] == "BUY"
    assert lly["gap"] > 0
    assert lly["shares"] > 0


def test_boundary_exactly_at_band_does_not_trigger():
    # Strict '>' -- exactly at the band edge must NOT be out_of_band.
    current = {"GC_F": 0.25, "AVGO": 0.35, "LLY": 0.35}
    target = {"GC_F": 0.25, "AVGO": 0.40, "LLY": 0.35}  # AVGO gap exactly +0.05
    result = rebalance_instructions(current, target, _REAL_PRICES, _REAL_RC_TOTAL, band=0.05)
    assert result["AVGO"]["out_of_band"] is False
    assert result["AVGO"]["action"] == "HOLD"


def test_just_past_boundary_triggers():
    current = {"GC_F": 0.25, "AVGO": 0.3499, "LLY": 0.4001}
    target = {"GC_F": 0.25, "AVGO": 0.40, "LLY": 0.35}  # AVGO gap +0.0501
    result = rebalance_instructions(current, target, _REAL_PRICES, _REAL_RC_TOTAL, band=0.05)
    assert result["AVGO"]["out_of_band"] is True


def test_missing_price_gives_zero_shares_but_still_reports_gap():
    result = rebalance_instructions(_REAL_CURRENT, _REAL_TARGET, {}, _REAL_RC_TOTAL)
    avgo = result["AVGO"]
    assert avgo["out_of_band"] is True          # gap is still real and reported
    assert avgo["action"] == "SELL"
    assert avgo["shares"] == 0                  # but never a fabricated share count
