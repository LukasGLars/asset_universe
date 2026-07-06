"""run_sleeve_duration_sensitivity.py

Runs the sleeve exit-duration sensitivity test for real, against the
current top-ranked candidates in universe_screen_results.csv -- reuses
run_entry_screen.py's own duration_matched_return() (same regime-
conditioned, uncapped forward-return machinery already validated for
per-candidate duration-matched win rates), swept across a grid of exit
windows instead of a single fixed one.

Report-only. Does not change the live TIME_EXIT_DAYS constant in
run_entry_screen.py -- that's a real change to how future sleeve trades
are managed and needs an explicit decision after seeing this result, not
an automatic change.

Usage:
    python run_sleeve_duration_sensitivity.py [--top N]
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

from asset_universe import config
from asset_universe.analysis.engine import current_regime
from run_entry_screen import CATEGORY_DIR, MIN_N_OBS, _matched_dates, duration_matched_return
from sleeve_duration_sensitivity import DURATIONS_TO_TEST, aggregate_duration_results, best_duration_by_median

UNIVERSE_CSV = Path(__file__).parent / "universe_screen_results.csv"


def load_candidates(top_n: int) -> list[tuple[str, str]]:
    """Top-N tickers from the universe screen, mapped to their parquet
    category -- same source run_entry_screen.py itself draws from."""
    df = pd.read_csv(UNIVERSE_CSV)
    top = df.head(top_n)
    return [(row.ticker, CATEGORY_DIR.get(row.category, "equities")) for row in top.itertuples()]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=50, help="how many top-ranked candidates to test (default 50)")
    args = parser.parse_args(argv)

    data_dir = config.raw_data_dir()

    reg = current_regime(data_dir)
    conditions = {
        k: reg["regimes"][k]
        for k in ["ry_regime", "nominal_10y_regime", "baa10y_regime", "usd_regime"]
        if k in reg["regimes"]
    }
    print(f"Regime conditions: {conditions}")

    matched = _matched_dates(conditions, data_dir)
    print(f"Matched dates: {len(matched)}")

    candidates = load_candidates(args.top)
    print(f"Testing {len(candidates)} candidates from universe_screen_results.csv\n")

    per_ticker: dict[int, list[tuple[float, float, int]]] = {d: [] for d in DURATIONS_TO_TEST}

    for ticker, category in candidates:
        for duration in DURATIONS_TO_TEST:
            median, win_rate, n = duration_matched_return(ticker, category, matched, duration, data_dir)
            if median is not None and n >= MIN_N_OBS:
                per_ticker[duration].append((median, win_rate, n))

    aggregated = aggregate_duration_results(per_ticker)

    print("=" * 72)
    print("SLEEVE EXIT-DURATION SENSITIVITY (flat-window component only)")
    print("=" * 72)
    print("\n  Raw median is period return over that window -- NOT comparable across")
    print("  windows on its own (more calendar time trivially means more return for")
    print("  any generally-appreciating stock). Annualized is the real comparison.")
    print(f"\n  {'Window':<12} {'Raw median':>11} {'Annualized':>11} {'Win rate':>9} {'N':>7} {'Tickers':>8}")
    print(f"  {'-'*62}")
    for duration in DURATIONS_TO_TEST:
        r = aggregated[duration]
        tag = f"{duration}d" + (" (cur)" if duration == 30 else "")
        if r["median"] is None:
            print(f"  {tag:<12} {'n/a':>11} {'n/a':>11} {'n/a':>9} {0:>7} {0:>8}")
        else:
            ann_str = f"{r['annualized']:+.1%}" if r["annualized"] is not None else "n/a"
            print(f"  {tag:<12} {r['median']:>+10.1%} {ann_str:>11} {r['win_rate']:>8.0%} "
                  f"{r['n_total']:>7} {r['n_tickers']:>8}")

    best = best_duration_by_median(aggregated)
    if best is not None:
        print(f"\n  Best ANNUALIZED return: {best}d window")
        if best != 30:
            print(f"  30d (current) is NOT the strongest window in this sample once time-normalized.")
        else:
            print(f"  30d (current) IS the strongest window in this sample once time-normalized.")

    print("\n  NOTE 1: this tests the flat-window component only. The earnings-buffer")
    print("  component (EARNINGS_BUFFER_DAYS=3) can't be backtested the same way --")
    print("  yfinance only exposes each ticker's CURRENT earnings calendar, not a")
    print("  point-in-time historical one, so there's no way to know what \"next")
    print("  earnings date\" the strategy would have seen looking forward from an")
    print("  arbitrary past date. Not tested here rather than faked.")
    print("\n  NOTE 2 (important): this measures returns from ALL regime-matched dates")
    print("  for top-ranked momentum candidates -- NOT specifically from dates that")
    print("  would have passed the sleeve's actual entry gate (MA50 not extended,")
    print("  momentum conditioning). A smooth monotonic improvement out to 90d likely")
    print("  reflects \"strong momentum names keep compounding broadly\" more than it")
    print("  proves the sleeve's specific dip-entry setup benefits from a 90d hold.")
    print("  Directional finding only -- not decision-grade without re-running the")
    print("  actual entry-gate logic at each historical date, a bigger separate task.")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
