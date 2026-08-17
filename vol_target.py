"""vol_target.py

Continuous volatility-scaled sizing for AVGO's weight in the Reactor Core
base, replacing the fixed 40% with a weight that scales against AVGO's own
trailing realized volatility -- the one mechanism from the 2026-08-17 split-
candidate research that improved both CAGR and MaxDD in the calm 2009-2026
backtest AND a real 2000-2026 stress test (dot-com bust + GFC, via a TXN
proxy for pre-IPO AVGO), with no reversal. See MEMORY.md.

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
