"""sleeve_duration_sensitivity.py

Pure aggregation logic for testing whether run_entry_screen.py's
TIME_EXIT_DAYS=30 is actually a good exit window, or just inherited from
the informal HWM precedent and never validated (MEMORY.md backlog,
logged 2026-07-06).

Scope, stated honestly: this tests the FLAT-WINDOW component only
(15/30/45/60/90 calendar days), reusing the same regime-conditioned,
uncapped forward-return machinery already validated for per-candidate
duration-matched win rates (duration_matched_return() in
run_entry_screen.py).

Does NOT backtest the EARNINGS_BUFFER_DAYS=3 component the same way --
yfinance only exposes each ticker's CURRENT earnings calendar, not a
point-in-time historical one, so there's no way to know what "next
earnings date" the strategy would have seen looking forward from an
arbitrary historical date. Same class of limitation as the missing
historical-analyst-estimates gap found earlier this session (see
eps_ratio.py / MEMORY.md). Flagged in the report rather than faked with a
test that would silently assume data that doesn't exist.
"""
from __future__ import annotations

import statistics

DURATIONS_TO_TEST = [15, 30, 45, 60, 90]


def annualize(period_return: float, days: int) -> float | None:
    """Converts a period return into an annualized-equivalent rate, so
    windows of different lengths can be compared fairly. Without this,
    raw per-trade return trivially increases with holding period for any
    generally-appreciating stock -- that's measuring more calendar time,
    not a better exit rule. (1 + r)^(365/days) - 1, proper compounding,
    not a linear day-count scaling."""
    if days <= 0:
        return None
    base = 1 + period_return
    if base <= 0:
        return None  # a >=100% loss over the period -- annualizing is meaningless
    return base ** (365 / days) - 1


def aggregate_duration_results(
    per_ticker: dict[int, list[tuple[float, float, int]]],
) -> dict[int, dict]:
    """per_ticker: {duration: [(median_return, win_rate, n), ...]} -- one
    tuple per ticker that had enough matched observations at that
    duration (candidates below the minimum are simply absent from the
    list, not included as zeros).

    Returns {duration: {"median": pooled median-of-medians (raw, period
    return -- informational only, NOT the comparison metric), "annualized":
    the same pooled median converted to an annualized-equivalent rate
    (the actual apples-to-apples comparison across different-length
    windows), "win_rate": N-weighted average across contributing tickers,
    "n_total": summed N, "n_tickers": count of tickers that contributed}}."""
    result: dict[int, dict] = {}
    for duration, rows in per_ticker.items():
        if not rows:
            result[duration] = {"median": None, "annualized": None, "win_rate": None,
                                 "n_total": 0, "n_tickers": 0}
            continue
        medians = [r[0] for r in rows]
        n_total = sum(r[2] for r in rows)
        weighted_win = sum(r[1] * r[2] for r in rows) / n_total if n_total else None
        pooled_median = statistics.median(medians)
        result[duration] = {
            "median": pooled_median,
            "annualized": annualize(pooled_median, duration),
            "win_rate": weighted_win,
            "n_total": n_total,
            "n_tickers": len(rows),
        }
    return result


def best_duration_by_median(aggregated: dict[int, dict]) -> int | None:
    """Which tested duration has the highest ANNUALIZED pooled return --
    the fair, time-normalized comparison, not the raw per-trade median
    (which trivially favors longer windows). Returns None if nothing has
    data. Name kept for backward compatibility; ranks on 'annualized'."""
    candidates = {d: v["annualized"] for d, v in aggregated.items() if v["annualized"] is not None}
    if not candidates:
        return None
    return max(candidates, key=candidates.get)
