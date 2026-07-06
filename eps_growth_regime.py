"""eps_growth_regime.py

Pure logic for the realized-EPS-growth regime study (see MEMORY.md /
session notes 2026-07-06). Answers: "when a stock's realized TTM EPS
growth is in the same regime AVGO is in today, what do subsequent price
returns look like -- especially following a deceleration out of that
regime." Mirrors this project's existing regime conventions (p33/p67
percentile thresholds, neutral LOW/MID/HIGH labels per INTEGRITY.md Rule
8, capped forward returns so a measurement never bleeds past a regime
change) rather than inventing a new methodology.

Explicitly does NOT answer whether a growth rate was already priced in by
the market -- that needs historical analyst-consensus data, which isn't
available (see session notes). This conditions on realized past growth
only.
"""
from __future__ import annotations

import datetime as dt
import statistics

# Any single-quarter or TTM figure with |YoY growth| beyond this is treated
# as an M&A/restructuring/turnaround artifact (e.g. a merger-driven loss
# quarter), not organic growth -- same spirit as run_entry_screen.py's
# M&A-event skip (SATS/COHR), applied to EPS instead of price.
ANOMALY_GROWTH_THRESHOLD = 3.0  # |growth| > 300%


def ttm_series(quarterly_eps: dict[dt.date, float]) -> dict[dt.date, float]:
    """Rolling trailing-4-quarter sum, keyed by the most recent quarter's
    end date. Uses quarter *count*, not fixed calendar spacing, so each
    filer's own fiscal-quarter-end pattern is respected as-is."""
    dates_sorted = sorted(quarterly_eps.keys())
    ttm = {}
    for i in range(3, len(dates_sorted)):
        window = dates_sorted[i - 3:i + 1]
        ttm[dates_sorted[i]] = sum(quarterly_eps[d] for d in window)
    return ttm


def yoy_growth_series(
    ttm: dict[dt.date, float],
    tolerance_days: int = 45,
    anomaly_threshold: float = ANOMALY_GROWTH_THRESHOLD,
) -> dict[dt.date, float]:
    """YoY growth = TTM_now / TTM_1yr_ago - 1, matched to the closest prior
    TTM date ~365 days back (tolerance absorbs fiscal-calendar drift).
    Skips dates where no year-ago match exists, where the year-ago TTM
    isn't positive (division would be nonsensical, not just noisy), or
    where the resulting growth rate exceeds anomaly_threshold in magnitude
    (treated as an M&A/restructuring artifact, not organic growth)."""
    dates_sorted = sorted(ttm.keys())
    growth = {}
    for d in dates_sorted:
        target = d - dt.timedelta(days=365)
        candidates = [d2 for d2 in dates_sorted if d2 < d and abs((d2 - target).days) <= tolerance_days]
        if not candidates:
            continue
        prior_date = min(candidates, key=lambda d2: abs((d2 - target).days))
        prior_ttm = ttm[prior_date]
        if prior_ttm <= 0:
            continue
        g = ttm[d] / prior_ttm - 1
        if abs(g) > anomaly_threshold:
            continue
        growth[d] = g
    return growth


def label_regimes(growth_values: list[float]) -> tuple[float, float]:
    """Fits p33/p67 thresholds on a pooled growth-rate distribution.
    Returns (p33, p67); callers label LOW (<p33) / MID / HIGH (>=p67)."""
    if len(growth_values) < 3:
        raise ValueError("need at least 3 values to fit percentile thresholds")
    sorted_vals = sorted(growth_values)
    n = len(sorted_vals)
    p33 = sorted_vals[int(n * 0.33)]
    p67 = sorted_vals[int(n * 0.67)]
    return p33, p67


def regime_label(growth: float, p33: float, p67: float) -> str:
    if growth < p33:
        return "LOW"
    if growth >= p67:
        return "HIGH"
    return "MID"


def capped_forward_return(
    prices: dict[dt.date, float],
    start_date: dt.date,
    horizon_days: int,
    regime_end_date: dt.date | None,
) -> float | None:
    """Forward return from start_date over horizon_days trading-adjacent
    calendar days, capped at regime_end_date if the regime changes before
    the horizon elapses -- mirrors engine.py's regime_end capping (the
    2026-06-29 fix that stopped AVGO's 252d returns from bleeding into the
    next regime). Returns None if data is insufficient."""
    dates_sorted = sorted(d for d in prices if d >= start_date)
    if not dates_sorted or dates_sorted[0] != start_date:
        # allow start_date to be the first available date on/after the requested one
        candidates = [d for d in prices if d >= start_date]
        if not candidates:
            return None
        start_date = min(candidates)
        dates_sorted = sorted(d for d in prices if d >= start_date)

    target_date = start_date + dt.timedelta(days=horizon_days)
    if regime_end_date is not None and regime_end_date < target_date:
        target_date = regime_end_date

    end_candidates = [d for d in dates_sorted if d <= target_date]
    if not end_candidates:
        return None
    end_date = max(end_candidates)
    if end_date == start_date:
        return None

    start_price = prices[start_date]
    end_price = prices[end_date]
    if start_price <= 0:
        return None
    return end_price / start_price - 1


def summarize_returns(returns: list[float]) -> dict:
    """Median/win-rate/N summary, matching the format used everywhere else
    in this project's dashboards."""
    if not returns:
        return {"n": 0, "median": None, "win_rate": None}
    return {
        "n": len(returns),
        "median": statistics.median(returns),
        "win_rate": sum(1 for r in returns if r > 0) / len(returns),
    }


def diversity_flag(n_tickers: int) -> str:
    """Mirrors the SINGLE/THIN/MODERATE/ROBUST convention used throughout
    this project -- here keyed off distinct-ticker count, since a single
    name contributing many overlapping quarterly observations isn't the
    same as genuine cross-sectional diversity."""
    if n_tickers <= 1:
        return "SINGLE"
    if n_tickers <= 3:
        return "THIN"
    if n_tickers <= 8:
        return "MODERATE"
    return "ROBUST"
