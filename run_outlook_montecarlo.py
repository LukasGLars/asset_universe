"""
run_outlook_montecarlo.py

Forward-looking outlook test for the live system (static base Gold 25 /
AVGO 40 / LLY 35 + silver GSR tactical), run to the operator's actual FI@50
date of 2038-10-10 (12.15 years from 2026-08-18) at the decided bucket split
(Reactor Core 85%, Home Base 15%, War Chest suspended), with 6,000 kr/month
contributions continuing.

The AVGO 200d guard, crash trigger and joint-stress escalation are all OFF.
This script originally modelled them ON ("Strategy E"); that was refreshed
2026-08-18 after the guard's edge was found to be lookahead bias and it was
disconnected from live routing (PR #88/#90). Projecting forward with a
mechanism whose backtested edge cannot be realised would overstate every
number below.

Method: block bootstrap (21-trading-day blocks, preserves some
autocorrelation/trend structure rather than i.i.d. daily draws) resampled
from Strategy E's actual historical daily-return series, run for 10,000
simulated 12-year paths, contributions injected monthly along each path
(not a closed-form annuity -- this is path-dependent, sequence-of-returns
risk is the whole point).

Two source regimes tested separately, not blended:
  1. AVGO actual (2009-2026) -- the regime the live system has actually
     lived through. Exceptional bull market, per MEMORY.md's own caveat.
  2. TXN analog (2000-2026) -- includes 2001 dot-com + 2008 GFC, regimes
     AVGO's own history has never been tested against.

Home Base modeled at a flat 2.5%/yr (same placeholder assumption used in
the 2026-07-02 rebalance sizing exercise -- no real data available). War
Chest modeled the same way for simplicity (it's a small, currently-
opportunistic-only sleeve; not the focus of this test).

Exploratory script -- not wired into daily automation.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from asset_universe import config

import run_combined_system as rcs

DATA_DIR = config.raw_data_dir()

# War Chest SUSPENDED (2026-08-04), and the bucket split was DECIDED at
# 85/15 on 2026-08-17 -- superseding the 83.3/4.5/12.2 target this script
# was originally written against.
RC_WEIGHT, WC_WEIGHT, HB_WEIGHT = 0.85, 0.0, 0.15
HOME_BASE_ANNUAL = 0.025
HOME_BASE_DAILY = (1 + HOME_BASE_ANNUAL) ** (1 / 252) - 1

MONTHLY_CONTRIBUTION = 6000.0
# Horizon runs to the actual FI@50 date (2038-10-10, operator turns 50),
# not a round 12 years. Matches config/portfolio.toml's `years`.
HORIZON_YEARS = 12.15
TRADING_DAYS_PER_YEAR = 252
BLOCK_LEN = 21
N_PATHS = 10_000
TARGET_SEK = 12_934_706.0

# Assume rebalance completes by fall 2026 -- start the clock from today's
# TPV, at target weights (not the current mid-transition weights).
START_TPV = 1_104_009.0  # latest live snapshot (2026-08-17 close, via CI status.md)

rng = np.random.default_rng(20260702)


def strategy_returns(x_series, gold, lly, silver, start) -> pd.Series:
    """Live system's return series: static base + silver GSR tactical.

    The AVGO 200d guard and the joint-stress escalation are both OFF. Their
    backtested edge was lookahead bias (every trade priced at the
    signal-generating close), so simulating forward with them on would
    project an edge that cannot be realised -- see MEMORY.md, "the AVGO 200d
    guard's entire validated edge is lookahead bias" and PR #88/#90, which
    disconnected the guard from live routing.
    """
    common = (gold.index.intersection(x_series.index)
              .intersection(lly.index).intersection(silver.index))
    common = common[common >= start].sort_values()
    prices = {"GC_F": gold, "AVGO": x_series, "LLY": lly, "SI_F": silver}
    signals = rcs.build_signals(x_series, gold, silver, lly, common)
    eq, _ = rcs.run_strategy(prices, signals, use_guard=False, use_silver=True,
                              label="C", use_joint=False)
    return eq.pct_change().dropna()


def block_bootstrap_path(daily_rets: np.ndarray, n_days: int) -> np.ndarray:
    n_src = len(daily_rets)
    out = np.empty(n_days)
    filled = 0
    while filled < n_days:
        start = rng.integers(0, n_src - BLOCK_LEN)
        block = daily_rets[start:start + BLOCK_LEN]
        take = min(BLOCK_LEN, n_days - filled)
        out[filled:filled + take] = block[:take]
        filled += take
    return out


def simulate(rc_daily_rets: np.ndarray, label: str) -> dict:
    # HORIZON_YEARS is fractional (runs to a real calendar date), so round to
    # a whole number of trading days rather than truncating a partial one.
    n_days = int(round(HORIZON_YEARS * TRADING_DAYS_PER_YEAR))
    days_per_month = TRADING_DAYS_PER_YEAR / 12

    terminal_values = np.empty(N_PATHS)
    max_drawdowns = np.empty(N_PATHS)
    hit_25dd = np.zeros(N_PATHS, dtype=bool)

    for p in range(N_PATHS):
        rc_path = block_bootstrap_path(rc_daily_rets, n_days)
        tpv = START_TPV
        peak = tpv
        max_dd = 0.0
        next_contrib_day = days_per_month
        for d in range(n_days):
            blended_ret = (RC_WEIGHT * rc_path[d]
                           + HB_WEIGHT * HOME_BASE_DAILY
                           + WC_WEIGHT * HOME_BASE_DAILY)
            tpv *= (1 + blended_ret)
            if d + 1 >= next_contrib_day:
                tpv += MONTHLY_CONTRIBUTION
                next_contrib_day += days_per_month
            peak = max(peak, tpv)
            dd = tpv / peak - 1
            max_dd = min(max_dd, dd)
        terminal_values[p] = tpv
        max_drawdowns[p] = max_dd
        hit_25dd[p] = max_dd <= -0.25

    pct = lambda q: np.percentile(terminal_values, q)
    print(f"=== {label} ({N_PATHS:,} paths, {HORIZON_YEARS:g}y, block bootstrap n={BLOCK_LEN}d) ===")
    print(f"  Terminal TPV:  p5 {pct(5):>13,.0f} kr   p25 {pct(25):>13,.0f} kr   "
          f"median {pct(50):>13,.0f} kr")
    print(f"                 p75 {pct(75):>13,.0f} kr   p95 {pct(95):>13,.0f} kr")
    implied_cagr_median = (pct(50) / START_TPV) ** (1 / HORIZON_YEARS) - 1
    print(f"  Median implied blended CAGR (TPV-growth basis, incl. contributions): {implied_cagr_median:+.1%}")
    print(f"  P(reach {TARGET_SEK:,.0f} kr nominal target): {np.mean(terminal_values >= TARGET_SEK):.1%}")
    print(f"  P(max drawdown worse than -25% at some point in {HORIZON_YEARS:g}y): {np.mean(hit_25dd):.1%}")
    print(f"  Median max drawdown over the {HORIZON_YEARS:g}y path: {np.median(max_drawdowns):+.1%}")
    print(f"  Worst 5% of paths' max drawdown (p5 of max_dd): {np.percentile(max_drawdowns, 5):+.1%}")
    print()
    return dict(terminal_values=terminal_values, max_drawdowns=max_drawdowns)


def main():
    gold = rcs.load_prices("commodities", "GC_F")
    silver = rcs.load_prices("commodities", "SI_F")
    lly = rcs.load_prices("equities", "LLY")
    avgo = rcs.load_prices("equities", "AVGO")
    txn = rcs.load_prices("equities", "TXN")

    avgo_rets = strategy_returns(avgo, gold, lly, silver, pd.Timestamp("2009-08-06")).values
    txn_rets = strategy_returns(txn, gold, lly, silver, pd.Timestamp("2000-08-30")).values

    print(f"Starting TPV: {START_TPV:,.0f} kr | Horizon: {HORIZON_YEARS:g}y (to 2038-10-10) | "
          f"Monthly contribution: {MONTHLY_CONTRIBUTION:,.0f} kr")
    print(f"Target weights assumed: Reactor Core {RC_WEIGHT:.1%} / War Chest {WC_WEIGHT:.1%} "
          f"/ Home Base {HB_WEIGHT:.1%} (flat {HOME_BASE_ANNUAL:.1%}/yr for HB+WC)")
    print("Guard/joint-stress: OFF (retired as lookahead bias) | Silver GSR: ON\n")

    # Sanity check against run_vol_target_robustness.py's static_band_sweep:
    # the AVGO-actual source series should reproduce roughly its NORMAL-regime
    # CAGR (~30%). A large divergence means the two implementations disagree
    # and one is wrong -- this repo has shipped an unvalidated backtest three
    # times, so the check is cheap insurance, not ceremony.
    for label, rets in (("AVGO actual", avgo_rets), ("TXN analog", txn_rets)):
        ann = (1 + rets.mean()) ** TRADING_DAYS_PER_YEAR - 1
        print(f"  [check] {label} source series: {len(rets):,} days, "
              f"annualized mean {ann:+.1%}")
    print()

    simulate(avgo_rets, "Source regime: AVGO actual history (2009-2026)")
    simulate(txn_rets, "Source regime: TXN analog (2000-2026, incl. 2001+2008)")


if __name__ == "__main__":
    main()
