"""next_contribution.py

Decides where the next kr of new capital (a monthly/bi-monthly contribution)
should go, among the Reactor Core base assets (Gold/AVGO/LLY). Silver is
deliberately excluded -- it has its own GSR trigger and its own funding
mechanism (currently AVGO/Gold sale on signal; see MEMORY.md's backlog for
the proposed War-Chest-funded alternative), not new contributions.

Rule: among assets whose own gate is open right now (Gold's gate never
closes; AVGO/LLY gate on their own guard/stress state, reused as-is from
the AVGO 200d guard block in fi_tracker.py), route to the one furthest
below its OWN current target weight. Target weights already come from
run_combined_system.WEIGHTS/JOINT_WEIGHTS, which account for guard/silver
state -- e.g. LLY's target jumps to 47.5% when AVGO's guard alone is
active, so it naturally becomes the destination without any special-casing
here.

Deliberately a pure function (no I/O) so it's trivially testable;
fi_tracker.py supplies the live weights/gates it already computes.
"""
from __future__ import annotations

CANDIDATES = ["GC_F", "AVGO", "LLY"]


def next_contribution_target(
    current_weights: dict[str, float],
    target_weights: dict[str, float],
    allowed: dict[str, bool],
) -> tuple[str, dict[str, dict[str, float]]]:
    detail: dict[str, dict] = {}
    best_ticker: str | None = None
    best_gap: float | None = None

    for tkr in CANDIDATES:
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
        # Defensive only -- Gold's gate is never closed in practice, so every
        # real call has at least one allowed candidate.
        best_ticker = "GC_F"

    return best_ticker, detail
