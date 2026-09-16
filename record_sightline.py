#!/usr/bin/env python3
"""record_sightline.py

CLI for sightline.py -- records one quarter's reading of a holding's
disclosed observable after actually reading the release, and prints the
hold-or-cut verdict the rule derives from it.

Usage:
    python record_sightline.py AVGO FY26Q3 16.7
    python record_sightline.py LLY  2026Q2 14.8

Values are in the unit config/sightline.toml declares (USD bn). The
verdict is HOLD / CUT / REQUALIFIED; CUT means the pre-committed action
in the config applies. Nothing else in the system reads this except the
dashboard block and its Telegram diff.
"""
from __future__ import annotations

import argparse
import sys

from sightline import load_config, record_reading


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ticker", help="e.g. AVGO or LLY")
    parser.add_argument("quarter", help="e.g. FY26Q3 (AVGO, fiscal) or 2026Q2 (LLY, calendar)")
    parser.add_argument("value", type=float, help="observable value, in the config's unit")
    args = parser.parse_args(argv)

    ticker = args.ticker.upper()
    state, detail = record_reading(ticker, args.quarter, args.value)
    entry = load_config()[ticker]
    print(f"{ticker}  {entry['observable']}")
    print(f"  {detail}")
    print(f"  Sightline: {state}")
    if state == "CUT":
        print(f"  ACTION: {entry['action']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
