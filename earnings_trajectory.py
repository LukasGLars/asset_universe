"""earnings_trajectory.py

Two automatable pieces of the AVGO/LLY earnings-day checklist: beat/miss
streak and guidance-revision direction, both derivable from data already
pulled (yfinance's earnings_history / eps_trend).

Deliberately does NOT cover the other two checklist items -- actual AI
revenue vs. the guided $56B FY26/$100B FY27 pace, and Anthropic/OpenAI
contract-timing commentary. Neither is available as structured data from
any free API; both require reading the actual earnings release/call. This
module only automates what's genuinely checkable, so the checkpoint output
can be honest about what still needs a human instead of implying full
coverage.
"""
from __future__ import annotations


def beat_streak(actual_estimate_pairs_oldest_first: list[tuple[float, float]]) -> int:
    """Consecutive beats (actual > estimate) counting back from the most
    recent quarter. Input ordered oldest-first, matching yfinance's own
    earnings_history ordering -- reversed internally so callers don't have
    to remember to do it themselves."""
    streak = 0
    for actual, estimate in reversed(actual_estimate_pairs_oldest_first):
        if actual > estimate:
            streak += 1
        else:
            break
    return streak


def guidance_direction(current_estimate: float, baseline_estimate: float, tolerance: float = 0.01) -> str:
    """Compares the current +1yr consensus estimate to a baseline (e.g.
    90 days ago). `tolerance` is a relative band around the baseline
    treated as "flat", so noise-level moves aren't reported as a real
    direction change."""
    if baseline_estimate == 0:
        return "unknown"
    change = (current_estimate - baseline_estimate) / abs(baseline_estimate)
    if change > tolerance:
        return "revising up"
    if change < -tolerance:
        return "revising down"
    return "flat"
