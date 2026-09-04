"""
Crypto trend sleeve -- the ensemble MA rule that replaced the opportunistic
sleeve on 2026-09-04.

Rule, per asset, run independently:

    Take the asset's WEEKDAY closes only (Sat/Sun dropped -- the ETPs trade
    Nasdaq Stockholm hours, and the whole rule was validated on a business-day
    series; using 24/7 closes shifts every lookback by ~40% and is a different,
    untested rule). Compute the 50/100/200-day SMAs on that series.

    Each window independently:
        close > MA * (1 + BAND)  -> LONG
        close < MA * (1 - BAND)  -> FLAT
        in between               -> hold whatever it was (hysteresis)

    Target exposure = mean of the three states -> 0%, 33%, 67% or 100%.

Why an ensemble and not the single best MA: adjacent single-MA cells swung
0.73-1.19 on Calmar in the 2026-09-04 selection run. Picking the winner is
exactly how the previous sleeve's gates got fitted to noise (see MEMORY.md
"Opp sleeve gates unproven"). The ensemble lands at 0.99 -- within noise of the
best single rule -- without requiring anyone to have picked it in advance.

Why the 2% band is load-bearing: without hysteresis the rule loses to
buy-and-hold in the 2023-26 era (whipsaw). With it, the rule beats B&H on
Calmar in 3/3 eras net of the 1.49% ETP fee and 0.5% round-trip spread.

Validation summary (2026-09-04, vs EXPOSURE-MATCHED buy-and-hold, which is the
control the old sleeve was never measured against):
  - 3/3 eras (2015-18, 2019-22, 2023-26)
  - 12/13 rule variants (MA / breakout / dual-MA / ROC)
  - BTC, ETH and SOL independently
  - survives 3%/side costs at low-turnover settings (~2.2 round trips/yr)
SOL is deliberately NOT in the live universe: its backtest is hindsight
selection (chosen because it won; most 2020-era L1s are worthless) and that
tier fails in days, which a daily rule cannot exit ahead of.
"""
from __future__ import annotations

import pandas as pd

MA_WINDOWS = (50, 100, 200)
BAND = 0.02

# Live sleeve universe. Kept deliberately short -- see the SOL note above.
ASSETS = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
}
CATEGORY = "crypto"


def weekday_closes(df: pd.DataFrame) -> pd.Series:
    """Weekday-only close series. The store holds 7-day crypto bars; the rule
    was validated on business days, so the weekend bars are dropped rather
    than resampled (resampling would invent a Friday close on a holiday)."""
    close = df["close"].dropna()
    return close[close.index.dayofweek < 5]


def _state_series(closes: pd.Series, window: int) -> pd.Series:
    """0/1 state with hysteresis: only the bands set a state, everything
    between them inherits the previous one. Leading NaNs (before the MA has
    enough history, and before the first band touch) resolve to FLAT."""
    ma = closes.rolling(window).mean()
    state = pd.Series(float("nan"), index=closes.index)
    state[closes > ma * (1 + BAND)] = 1.0
    state[closes < ma * (1 - BAND)] = 0.0
    return state.ffill().fillna(0.0)


def rule_states(closes: pd.Series) -> list[dict]:
    """Per-window detail for today: the MA, both band edges, and the state."""
    out = []
    for w in MA_WINDOWS:
        ma = closes.rolling(w).mean()
        out.append({
            "window": w,
            "ma": float(ma.iloc[-1]) if pd.notna(ma.iloc[-1]) else None,
            "upper": float(ma.iloc[-1] * (1 + BAND)) if pd.notna(ma.iloc[-1]) else None,
            "lower": float(ma.iloc[-1] * (1 - BAND)) if pd.notna(ma.iloc[-1]) else None,
            "long": bool(_state_series(closes, w).iloc[-1]),
        })
    return out


def exposure_series(closes: pd.Series) -> pd.Series:
    """Full history of target exposure -- used for the last-change lookup and
    by the tests, so the daily number and the history can't drift apart."""
    return sum(_state_series(closes, w) for w in MA_WINDOWS) / len(MA_WINDOWS)


def target_exposure(closes: pd.Series) -> float:
    return float(exposure_series(closes).iloc[-1])


def last_change(closes: pd.Series) -> tuple[str, float] | None:
    """(date, new exposure) of the most recent tier change, or None."""
    exp = exposure_series(closes)
    ch = exp[exp.diff() != 0]
    if len(ch) < 2:
        return None
    return str(ch.index[-1].date()), float(ch.iloc[-1])


def asset_signal(closes: pd.Series) -> dict:
    return {
        "close": float(closes.iloc[-1]),
        "as_of": str(closes.index[-1].date()),
        "states": rule_states(closes),
        "exposure": target_exposure(closes),
        "last_change": last_change(closes),
    }
