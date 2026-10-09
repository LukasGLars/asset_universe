"""next_contribution.py

Decides where the next kr of new capital (a monthly/bi-monthly contribution)
should go: among the assets whose gate is open, the one furthest below its
own target weight.

The candidate set is whatever `target_weights` contains -- it is NOT a
hardcoded list. Until 2026-10-09 this module held `CANDIDATES = ["GC_F",
"AVGO", "LLY"]` and fi_tracker fed it run_combined_system.WEIGHTS, i.e. the
legacy 3-asset base of Gold 25 / AVGO 40 / LLY 35. After the 2026-09-27
restructure the real target is per-asset across the whole Reactor Core
account (AVGO 20 / LLY 20 / Gold 20 / Index 25 / Cash 10 / BTC 2.5 /
ETH 2.5, stored as target_weight in config/portfolio.toml), so routing was
answering against a base the portfolio no longer runs -- it could not see
the index leg or cash at all, and scored the other three against the wrong
denominator.

Callers exclude an asset by passing allowed[asset] = False rather than by
leaving it out of the targets, so an excluded asset still appears in the
returned detail with its real gap. Silver has its own GSR trigger and the
crypto legs have their own sleeve capital; neither is funded by
contributions.

Deliberately a pure function (no I/O) so it's trivially testable;
fi_tracker.py supplies the live weights/gates it already computes.
"""
from __future__ import annotations


def next_contribution_target(
    current_weights: dict[str, float],
    target_weights: dict[str, float],
    allowed: dict[str, bool],
) -> tuple[str, dict[str, dict[str, float]]]:
    if not target_weights:
        # A missing/empty target is a config failure, not a routing decision.
        # fi_tracker wraps this call, so it surfaces as an explicit
        # "[unavailable]" line rather than silently naming some asset.
        raise ValueError("no target weights supplied -- cannot route a contribution")

    detail: dict[str, dict] = {}
    best_ticker: str | None = None
    best_gap: float | None = None

    for tkr in sorted(target_weights):
        current = current_weights.get(tkr, 0.0)
        target = target_weights.get(tkr, 0.0)
        gap = target - current
        is_allowed = bool(allowed.get(tkr, False))
        detail[tkr] = {"current": current, "target": target, "gap": gap, "allowed": is_allowed}

        if not is_allowed:
            continue
        if best_gap is None or gap > best_gap:
            best_gap = gap
            best_ticker = tkr

    if best_ticker is None:
        # Defensive only -- in practice at least one candidate is always
        # allowed. Falls back to the largest gap ignoring gates rather than to
        # a hardcoded ticker, which would name an asset that may not even be
        # in the current target.
        best_ticker = max(detail, key=lambda t: detail[t]["gap"]) if detail else None

    return best_ticker, detail
