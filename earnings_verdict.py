"""earnings_verdict.py

Persists the one part of the earnings-day checklist that can't be
automated: the judgment call on whether AI revenue is tracking the
guided pace and whether Anthropic/OpenAI contract timing still holds
(see MEMORY.md backlog, logged 2026-07-06 -- confirmed neither is
available as structured data anywhere).

Intended workflow: read the actual release/call (typically with Claude,
pasted in for a bottom-line read the same way as any other analysis),
form the verdict together, THEN record it -- this module is the "write
it down" step, not a substitute for the reading. It is not meant to be
something you fill in independently without that read happening first.

No new dependency: writes plain TOML text by hand (one flat table per
ticker) rather than pulling in a TOML-writing library for something this
simple -- same pattern as sync_sheet.py's direct text patching.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

VERDICTS_PATH = Path(__file__).parent / "config" / "earnings_verdicts.toml"

HEADER = """\
# Earnings-day verdicts -- the manual (or Claude-assisted) judgment call
# that can't be automated: AI revenue vs. guided pace, Anthropic/OpenAI
# contract-timing commentary. Written after actually reading the release/
# call, not a substitute for it. See earnings_verdict.py / MEMORY.md.
#
# Updated via:
#   python record_earnings_verdict.py TICKER --cleared "reasoning"
#   python record_earnings_verdict.py TICKER --not-cleared "reasoning"

"""


def load_verdicts(path: Path = VERDICTS_PATH) -> dict[str, dict]:
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def save_verdict(
    ticker: str,
    verdict: str,
    reasoning: str,
    date: dt.date | None = None,
    path: Path = VERDICTS_PATH,
) -> None:
    if verdict not in ("CLEARED", "NOT_CLEARED"):
        raise ValueError(f"verdict must be CLEARED or NOT_CLEARED, got {verdict!r}")

    verdicts = load_verdicts(path)
    verdicts[ticker] = {
        "verdict": verdict,
        "date": str(date or dt.date.today()),
        "reasoning": reasoning,
    }

    lines = [HEADER]
    for tkr, v in verdicts.items():
        lines.append(f"[{tkr}]")
        lines.append(f'verdict   = "{_escape(v["verdict"])}"')
        lines.append(f'date      = "{_escape(v["date"])}"')
        lines.append(f'reasoning = "{_escape(v["reasoning"])}"')
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def format_verdict_line(ticker: str, verdicts: dict[str, dict] | None = None) -> str | None:
    """Returns the dashboard display line for a ticker's latest verdict, or
    None if no verdict has ever been recorded (the common case -- most days,
    nothing to show)."""
    verdicts = verdicts if verdicts is not None else load_verdicts()
    v = verdicts.get(ticker)
    if not v:
        return None
    return f"{v['verdict']}  ({v['date']}) -- {v['reasoning']}"
