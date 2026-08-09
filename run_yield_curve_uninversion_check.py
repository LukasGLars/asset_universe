"""
run_yield_curve_uninversion_check.py -- ONE-OFF diagnostic, delete after use.

Operator's question: exact dates T10Y2Y and T10Y3M (FRED) went from
negative (inverted) to positive (uninverted/normal) in this cycle, plus
current values -- to assess recession-imminence given the well-known
pattern that uninversion (steepening after a long inversion), not the
inversion itself, has historically preceded/coincided with recession
onset (Fed cutting short rates faster than long rates fall).

Reports every negative->positive sign-flip in the full series history
(so the real, current-cycle uninversion date is unambiguous, not a
guess), plus days since uninversion and current spread level.

Read-only. No commits, no state changes.
"""
from __future__ import annotations
import sys, io, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd

from asset_universe import config
from asset_universe.store import reader

SERIES = ["T10Y2Y", "T10Y3M"]
CATEGORY = "macro"


def find_sign_flips(s: pd.Series) -> list[tuple[pd.Timestamp, float, float]]:
    """Every date where the series crosses from <=0 to >0 (uninversion)."""
    flips = []
    prev = None
    for dt, val in s.items():
        if prev is not None and prev <= 0 and val > 0:
            flips.append((dt, prev, val))
        prev = val
    return flips


def main() -> None:
    data_dir = config.raw_data_dir()
    today = pd.Timestamp.today().normalize()

    for sid in SERIES:
        path = reader.ticker_path(data_dir, CATEGORY, sid)
        s = reader.load(path)["value"].dropna().sort_index()
        print(f"\n{'=' * 64}\n{sid}  ({s.index.min().date()} to {s.index.max().date()})\n{'=' * 64}")

        flips = find_sign_flips(s)
        print(f"All negative->positive crossings in full history: {len(flips)}")
        for dt, prev, val in flips[-5:]:
            print(f"  {dt.date()}  {prev:+.2f} -> {val:+.2f}")

        if flips:
            last_flip_date, _, _ = flips[-1]
            days_since = (today - last_flip_date).days
            print(f"\nMost recent uninversion: {last_flip_date.date()}  ({days_since} days ago)")
            # Confirm it hasn't re-inverted since
            since = s[s.index > last_flip_date]
            reinverted = (since <= 0).any()
            print(f"Re-inverted since then: {'YES -- ' + str(since[since <= 0].index[0].date()) if reinverted else 'no'}")
        else:
            print("\nNo negative->positive crossing found in available history.")

        print(f"Current ({s.index[-1].date()}): {s.iloc[-1]:+.2f}")

    print("\nInformational only -- not wired into any live gate.")


if __name__ == "__main__":
    main()
