#!/usr/bin/env python3
"""record_earnings_verdict.py

CLI for earnings_verdict.py -- records the judgment call formed after
actually reading an earnings release/call (typically with Claude, the
same way any other analysis in this project gets read), so it shows up
on the daily dashboard afterward instead of living only in memory across
the gap until the remaining AVGO tranche actually executes.

Usage:
    python record_earnings_verdict.py AVGO --cleared "AI revenue tracking
        the guided pace, Anthropic contract on schedule."
    python record_earnings_verdict.py AVGO --not-cleared "AI revenue
        missed pace by 8%, Anthropic contract slipped to 2028."

Not meant to be filled in without reading the actual release/call first --
this records the verdict, it doesn't form it.
"""
from __future__ import annotations

import argparse
import sys

from earnings_verdict import save_verdict


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", help="e.g. AVGO or LLY")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cleared", metavar="REASONING", help="record a CLEARED verdict")
    group.add_argument("--not-cleared", metavar="REASONING", help="record a NOT_CLEARED verdict")
    args = parser.parse_args(argv)

    verdict = "CLEARED" if args.cleared is not None else "NOT_CLEARED"
    reasoning = args.cleared if args.cleared is not None else args.not_cleared

    save_verdict(args.ticker.upper(), verdict, reasoning)
    print(f"Verdict recorded: {args.ticker.upper()} {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
