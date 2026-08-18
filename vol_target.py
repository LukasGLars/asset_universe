"""vol_target.py

*** THE VOL-TARGETING MECHANISM IS RETIRED AS OF 2026-08-18. ***
*** compute_vol_target_weights() is DIAGNOSTIC-ONLY -- it must not drive  ***
*** routing or rebalance instructions. rebalance_instructions() remains   ***
*** LIVE, but against the STATIC base weights.                            ***

Retired because the result that justified shipping it (2026-08-17, PR #91:
normal CAGR 30.15%->30.79%, Calmar 1.288->1.426) did not replicate. A
self-checked rebuild -- verified bit-exact against this module's own
compute_vol_target_weights() at 25 dates across the full history -- found
the mechanism LOSES to plain static weights, and that finding survived every
robustness test applied to it:
  - every sub-period, including with AVGO's 2023-2026 melt-up excluded;
  - 0 wins in a 30-cell VOL_WINDOW x REBAL_BAND grid, both regimes;
  - and under identical realistic-drift mechanics (the original comparison
    had silently given the fixed static target free daily rebalancing).
In the stress window it made drawdown WORSE (-57.2% vs -48.7% at a 5% band),
so it was not buying protection in the regime it existed for.

Kept rather than deleted, following the same precedent as the retired AVGO
200d guard: the dashboard still prints the reading as a diagnostic, and the
validation scripts (run_vol_target_validation.py,
run_vol_target_robustness.py) need the live function to check themselves
against. Full detail in MEMORY.md.

Original design intent, for reference: continuous volatility-scaled sizing
for AVGO's weight in the Reactor Core base, replacing the fixed 40% with a
weight scaled against AVGO's own trailing realized volatility.

Mechanism: today's weight is sized from AVGO's trailing VOL_WINDOW-day
realized volatility (through the latest available close) relative to its
own long-run average volatility (an EXPANDING window from AVGO's IPO through
that same latest close). Both vol series only ever use data already known as
of "today" -- same convention as every other live signal in this repo (e.g.
the AVGO Trend Diagnostic's 200d SMA), where "today's" reading is the
instruction for the NEXT session, not a same-session trade. This is why it
does not repeat the retired guard's lookahead bug: that bug came from
trading the SAME close that generated the signal, not from reading the
latest close at all.

The scalar is clipped to [MIN_MULT, MAX_MULT] x the base 40% AVGO weight;
freed or added weight moves to/from Gold and LLY, preserving their 25:35
ratio. Deliberately continuous, not a binary in/out threshold like the
retired guard -- it never needs to catch a clean re-entry signal to
participate in a recovery.

NOTE on backtest vs live methodology: the 2026-08-17 backtest used the
FULL-SAMPLE average vol as the "long-run" reference -- a legitimate
simplification for a research backtest, but lookahead if used live. This
module uses an EXPANDING window instead, so today's weight only ever
depends on data that was actually available today.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

VOL_WINDOW = 21          # trading days, trailing realized vol
MIN_MULT   = 0.3
MAX_MULT   = 1.3

BASE_WEIGHTS = {"GC_F": 0.25, "AVGO": 0.40, "LLY": 0.35}

# Widened 5% -> 10% on 2026-08-18. The original 5% came from the same
# 2026-08-17 research whose headline result did not survive replication (see
# MEMORY.md, "AVGO vol-targeting: shipped edge does NOT reproduce"), so it was
# re-derived from scratch against the STATIC base under realistic weight drift
# (run_vol_target_robustness.py section C + comparison_results/
# static_band_sweep.csv, buy&hold row cross-validated against an independent
# fixed-share computation):
#
#   band    NORMAL CAGR/Calmar     STRESS CAGR/Calmar
#    3%     27.45% / 1.136         10.88% / 0.224
#    5%     29.03% / 1.220         12.02% / 0.263   <- previous
#    8%     29.72% / 1.329         12.43% / 0.281
#   10%     30.29% / 1.296         12.87% / 0.294   <- now
#   15%     31.01% / 1.383         13.46% / 0.306
#
# Wider beats 5% on BOTH CAGR and Calmar in both regimes, and the ranking is
# stable across sub-periods (15% best in 4 of 5 tested). 10% rather than 15%
# deliberately, for two reasons: the 2026-08-17 band sweep found >20%
# non-monotonic and unstable, so 10% keeps real distance from that edge; and a
# wider band lets AVGO drift further before trimming (10% band -> AVGO can
# reach ~50% of Reactor Core; 15% -> ~55%), which interacts badly with the
# documented single-name concentration risk in AVGO specifically. Most of the
# available gain is captured by 8-10% regardless.
REBAL_BAND = 0.10


def compute_vol_target_weights(avgo_prices: pd.Series) -> dict:
    """
    avgo_prices: AVGO close prices, sorted ascending by date, at least
    VOL_WINDOW + 1 return observations of history. Returns the current
    (as of the latest available close) vol-targeted weights for
    GC_F/AVGO/LLY, plus the diagnostic inputs (trailing_vol, long_run_vol,
    scalar) for display.
    """
    rets = avgo_prices.pct_change().dropna()
    if len(rets) < VOL_WINDOW + 1:
        raise ValueError(f"need at least {VOL_WINDOW + 1} return observations, got {len(rets)}")

    trailing_vol_series = rets.rolling(VOL_WINDOW).std() * np.sqrt(252)
    long_run_vol_series = trailing_vol_series.expanding().mean()

    trailing_vol = float(trailing_vol_series.iloc[-1])
    long_run_vol = float(long_run_vol_series.iloc[-1])

    scalar = (float(np.clip(long_run_vol / trailing_vol, MIN_MULT, MAX_MULT))
              if trailing_vol > 0 else 1.0)

    avgo_w = BASE_WEIGHTS["AVGO"] * scalar
    freed  = BASE_WEIGHTS["AVGO"] - avgo_w
    denom  = BASE_WEIGHTS["GC_F"] + BASE_WEIGHTS["LLY"]
    gold_share = BASE_WEIGHTS["GC_F"] / denom
    lly_share  = BASE_WEIGHTS["LLY"] / denom

    weights = {
        "AVGO": avgo_w,
        "GC_F": BASE_WEIGHTS["GC_F"] + freed * gold_share,
        "LLY":  BASE_WEIGHTS["LLY"] + freed * lly_share,
    }

    return {
        "weights": weights,
        "trailing_vol": trailing_vol,
        "long_run_vol": long_run_vol,
        "scalar": scalar,
    }


def apply_silver_funding(vt_weights: dict[str, float], silver_pct: float) -> dict[str, float]:
    """Fund a silver GSR-tactical allocation (0.12 for T1, 0.17 for T2, 0.0
    when inactive) out of AVGO's vol-targeted weight, matching the existing
    "silver funded from AVGO" rule in run_combined_system.WEIGHTS -- Gold and
    LLY are left untouched, same as that table.

    AVGO's vol-targeted weight has a floor of MIN_MULT x its base weight
    (0.12 at the current 0.3x floor), which can be LESS than T2's 0.17
    funding need. In that case silver is capped at whatever AVGO's weight
    actually allows rather than reaching into Gold/LLY -- an untested rule
    change -- or going negative. AVGO floors at 0 in that scenario.
    """
    avgo_w = vt_weights["AVGO"]
    funded_silver = min(silver_pct, avgo_w)
    return {
        "GC_F": vt_weights["GC_F"],
        "AVGO": avgo_w - funded_silver,
        "LLY":  vt_weights["LLY"],
        "SI_F": funded_silver,
    }


def rebalance_instructions(
    current_weights: dict[str, float],
    target_weights: dict[str, float],
    prices: dict[str, float],
    rc_total: float,
    band: float = REBAL_BAND,
) -> dict[str, dict]:
    """For each of GC_F/AVGO/LLY: whether ALREADY-HELD capital has drifted
    more than `band` from `target_weights` (distinct from next_contribution's
    routing of NEW money only) and, if so, the trade size to close that
    asset's OWN gap back to target -- sized independently per asset, not
    netted against what a simultaneous sell elsewhere would fund. Simpler
    and more robust for an automated alert than a "who funds whom" allocator
    that has to keep working as the number of in/out-of-band assets varies.

    Strict '>' against the band (exactly at the boundary does not trigger),
    matching run_base_optimizer.py's existing drift-rebalance convention.
    Missing price data cannot silently corrupt the trade instruction: a
    missing/zero price forces the shares figure to 0 rather than raising or
    dividing by zero, but out_of_band and gap_kr are still computed and
    reported -- "must be accurate always" means never presenting a wrong
    share count, not never surfacing a real gap.
    """
    result: dict[str, dict] = {}
    for tkr in ("GC_F", "AVGO", "LLY"):
        cur = current_weights.get(tkr, 0.0)
        tgt = target_weights.get(tkr, 0.0)
        gap = tgt - cur
        # Round before the boundary comparison -- raw float subtraction can
        # land a hair past an intended-exact band (e.g. 0.40-0.35 ==
        # 0.05000000000000004), which would wrongly trigger a trade at
        # exactly the edge. 1e-9 precision is far tighter than any real
        # portfolio weight needs, so this only ever corrects float noise.
        out_of_band = round(abs(gap), 9) > band
        gap_kr = gap * rc_total
        price = prices.get(tkr) or 0.0
        shares = round(abs(gap_kr) / price) if (out_of_band and price > 0) else 0

        result[tkr] = {
            "current": cur,
            "target": tgt,
            "gap": gap,
            "gap_kr": gap_kr,
            "out_of_band": out_of_band,
            "action": ("BUY" if gap > 0 else "SELL") if out_of_band else "HOLD",
            "shares": shares,
        }
    return result
