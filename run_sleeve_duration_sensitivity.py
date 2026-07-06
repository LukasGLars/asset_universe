"""run_sleeve_duration_sensitivity.py

PIPELINE CHECK, NOT YET AN ANSWER. Runs the sleeve exit-duration
sensitivity test against the current top-ranked candidates in
universe_screen_results.csv -- reuses run_entry_screen.py's own
duration_matched_return() (same regime-conditioned, uncapped
forward-return machinery already validated for per-candidate
duration-matched win rates), swept across a grid of exit windows instead
of a single fixed one.

This measures returns from ALL regime-matched dates, NOT specifically
from dates that would have passed the sleeve's actual 4-gate entry logic
(screen_tactical() in engine.py: regime, MA50-not-extended, relative
strength, earnings-clear). That's a materially different, narrower
population -- a dip-entry and a random date in an ongoing uptrend are not
the same setup. Confirms the pipeline and annualization math work; does
NOT establish whether TIME_EXIT_DAYS=30 is actually right for the
sleeve's real trades. See the printed NEXT STEP for what that would need.

Report-only regardless. Does not change the live TIME_EXIT_DAYS constant.

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
from sleeve_duration_sensitivity import DURATIONS_TO_TEST, aggregate_duration_results

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
    print("SLEEVE EXIT-DURATION SENSITIVITY -- PIPELINE CHECK, NOT AN ANSWER YET")
    print("=" * 72)
    print("\n  READ THIS FIRST: this does NOT test whether 30 days is right for the")
    print("  sleeve's actual trades. It measures returns from ALL regime-matched")
    print("  dates for top-ranked momentum names -- NOT specifically from dates that")
    print("  would have passed the sleeve's real entry gate (MA50 not extended,")
    print("  momentum conditioning, RS-vs-benchmark, earnings clear). Those are a")
    print("  different, much narrower population. A dip-entry and a random date in")
    print("  an ongoing uptrend are not the same setup, and this test can't tell them")
    print("  apart -- it never conditions on non-extension at all.")
    print("\n  What this DOES establish: the pipeline works (real data, real N, no")
    print("  crashes) and the annualization math is correct (raw per-trade return")
    print("  trivially favors longer windows for any appreciating stock -- fixed by")
    print("  comparing annualized-equivalent rates instead, below). What it does NOT")
    print("  establish: whether 30d, 60d, or any other window is actually better for")
    print("  the sleeve's real dip-entries. That needs the entry-gate logic")
    print("  reconstructed at each historical date -- a bigger, separate task, not")
    print("  done here. Numbers below are shown for pipeline verification only --")
    print("  do not use them to justify changing TIME_EXIT_DAYS.")
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

    print("\n  NOTE: EARNINGS_BUFFER_DAYS=3 also can't be backtested the same way --")
    print("  yfinance only exposes each ticker's CURRENT earnings calendar, not a")
    print("  point-in-time historical one. Not tested here rather than faked.")
    print("\n  NEXT STEP (not done here): reconstruct the sleeve's 4-gate entry logic")
    print("  (screen_tactical() in engine.py) at each historical date instead of")
    print("  today only, collect the dates that would have actually qualified, and")
    print("  re-run this same duration sweep restricted to those dates. Until that")
    print("  exists, treat 30d as unvalidated but NOT as shown-worse -- this table")
    print("  doesn't settle that question either way.")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
