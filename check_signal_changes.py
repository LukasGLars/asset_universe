"""
check_signal_changes.py

Extracts an "actionable signal fingerprint" from a status.md dashboard
snapshot (AVGO guard state, LLY-stress, joint-stress, silver GSR state,
opportunistic sleeve status, confirmed regime flip) and compares two
snapshots. Used by sync.yml to decide whether the daily run is worth an
email: silence when nothing actionable changed, a one-line summary when
something did. Price/valuation noise (which changes every day) is
deliberately not part of the fingerprint.

Usage:
    python check_signal_changes.py <prev_status.md> <curr_status.md>

Exit code 0 always. Prints nothing (no output) if unchanged. Prints a
one-line, human-readable summary to stdout if something changed -- that
output is used directly as the notification email body by sync.yml.
Missing/unparseable fields degrade to "unknown" rather than crashing --
check_sync_health.py already fails the job loudly on genuinely broken
status.md content; this script's job is signal comparison, not validation.
"""
from __future__ import annotations

import re
import sys


def _find(pattern: str, text: str, default: str = "unknown") -> str:
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else default


def extract_fingerprint(text: str) -> dict:
    return {
        "avgo_guard": _find(r"AVGO 200d Guard.*?Signal\s*:\s*(\S+)", text),
        "avgo_trigger": _find(r"AVGO 200d Guard.*?trigger:\s*(\S+)\)", text),
        "lly_stress": _find(r"LLY stress\s*:\s*(\S+)", text),
        "joint_stress": _find(r"Joint stress\s*:\s*(\S+)", text),
        "silver_signal": _find(r"Silver GSR Tactical.*?Signal\s*:\s*(\S+)", text),
        "sleeve_status": _find(r"Opportunistic Sleeve.*?Status\s*:\s*(\S+)", text),
        "regime_flip": "FLIP" if re.search(r"REGIME CHANGE ALERT", text) else "stable",
    }


LABELS = {
    "avgo_guard": "AVGO guard",
    "avgo_trigger": "AVGO guard trigger",
    "lly_stress": "LLY stress",
    "joint_stress": "Joint stress",
    "silver_signal": "Silver GSR",
    "sleeve_status": "Opportunistic sleeve",
    "regime_flip": "Regime",
}


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: check_signal_changes.py <prev_status.md> <curr_status.md>", file=sys.stderr)
        sys.exit(0)  # fail open -- never block the sync job over this check

    prev_path, curr_path = sys.argv[1], sys.argv[2]
    try:
        with open(prev_path, "r", encoding="utf-8", errors="replace") as f:
            prev = extract_fingerprint(f.read())
        with open(curr_path, "r", encoding="utf-8", errors="replace") as f:
            curr = extract_fingerprint(f.read())
    except FileNotFoundError:
        # No previous snapshot (first run ever) -- nothing to compare against.
        sys.exit(0)

    changes = [
        f"{LABELS[k]}: {prev[k]} -> {curr[k]}"
        for k in LABELS
        if prev[k] != curr[k] and "unknown" not in (prev[k], curr[k])
    ]

    if changes:
        print("Asset Universe signal change: " + "; ".join(changes))


if __name__ == "__main__":
    main()
