"""
run_opp_sleeve_vol_scaled_trailing_sensitivity.py

Direct follow-on to the now-live exit logic (MA50 buffer 5%, hard stop off,
21d time exit -- see MEMORY.md 2026-07-26). The combined stop x duration
study tested trailing stops as a fixed global rule (5% trigger / 5%
trailing) and found it won in every volatility bucket, but never swept
trailing PARAMETERS separately per bucket -- only two fixed pairs (5/5,
5/8) were ever tried. This tests whether a volatility-SCALED trailing stop
(tighter for calm names, wider for choppy ones) beats the current global
5%/5% rule, bucket by bucket, holding everything else at its live value
(MA50 buffer 5%, hard stop off, 21d duration).

Same real 4-gate entry population as every other study in this backlog
(run_sleeve_entry_reconstruction.py / PR #45), stratified by realized-20d-
vol tercile at entry (reusing run_opp_sleeve_combined_sensitivity.py's
bucketing).

Grid: trigger x trailing_pct in {3%, 5%, 8%} each, 9 combos, evaluated
within each vol bucket independently. If a bucket's own best combo beats
the current 5%/5% rule's result on that SAME bucket's entries, that's
evidence for a vol-scaled rule; if 5%/5% already wins (or ties) in every
bucket, the current global rule stays as-is -- no added complexity for no
gain, same discipline as the entry-filter study that just preceded this.

Analysis only: no live rule changes without explicit operator go-ahead.

Usage:
    python run_opp_sleeve_vol_scaled_trailing_sensitivity.py
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.store import reader

import run_sleeve_entry_reconstruction as recon
from run_opp_sleeve_combined_sensitivity import realized_vol_at_entry, vol_bucket

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "opp_sleeve_vol_scaled_trailing_sensitivity.csv"

MA50_BUFFER_PCT = 0.05   # current live value (run_entry_screen.py)
DURATION_DAYS   = 21     # current live TIME_EXIT_DAYS
MIN_N_OBS       = 10
VOL_LOOKBACK    = 20

TRIGGER_GRID  = [0.03, 0.05, 0.08]
TRAILING_GRID = [0.03, 0.05, 0.08]


def simulate_trade(
    prices: pd.Series,
    ma50: pd.Series,
    entry_date: pd.Timestamp,
    trailing_trigger: float,
    trailing_pct: float,
) -> dict | None:
    """Live exit logic (buffered MA50, no hard stop, 21d duration) with
    trailing_trigger/trailing_pct as the only variables under test."""
    entry_idx = prices.index.searchsorted(entry_date)
    if entry_idx >= len(prices) or abs((prices.index[entry_idx] - entry_date).days) > 5:
        return None

    entry_price = float(prices.iloc[entry_idx])
    peak = entry_price
    target_date = entry_date + pd.Timedelta(days=DURATION_DAYS)

    exit_price, stopped = None, False
    i = entry_idx
    while True:
        i += 1
        if i >= len(prices) or prices.index[i] > target_date:
            break
        price = float(prices.iloc[i])
        peak = max(peak, price)

        levels = []
        ma = ma50.iloc[i]
        if pd.notna(ma):
            levels.append(float(ma) * (1 - MA50_BUFFER_PCT))
        if (peak / entry_price - 1) >= trailing_trigger:
            levels.append(peak * (1 - trailing_pct))

        binding = max(levels) if levels else -np.inf
        if price <= binding:
            exit_price, stopped = price, True
            break

    if exit_price is None:
        idx = prices.index.searchsorted(target_date)
        if idx >= len(prices):
            idx = len(prices) - 1
        if prices.index[idx] > target_date and idx > entry_idx:
            idx -= 1
        if idx <= entry_idx:
            return None
        exit_price = float(prices.iloc[idx])

    return {"return": (exit_price - entry_price) / entry_price, "stopped": stopped}


def summarize(trades: list[dict]) -> dict:
    n = len(trades)
    if n < MIN_N_OBS:
        return {"n": n, "median_return": None, "win_rate": None,
                "annualized": None, "calmar_like": None}
    rets = np.array([t["return"] for t in trades])
    med = float(np.median(rets))
    downside = rets[rets < 0]
    med_dd = float(np.median(downside)) if len(downside) else 0.0
    calmar = (med / abs(med_dd)) if med_dd != 0 else float("nan")
    return {
        "n": n,
        "median_return": round(med, 4),
        "win_rate": round(float((rets > 0).mean()), 3),
        "annualized": round((1 + med) ** (365.25 / DURATION_DAYS) - 1, 4),
        "calmar_like": round(calmar, 3) if not np.isnan(calmar) else None,
    }


def main() -> None:
    print("=" * 72)
    print("Opportunistic sleeve: volatility-scaled trailing-stop sensitivity")
    print(f"(live exit logic otherwise: MA50 buffer {MA50_BUFFER_PCT:.0%}, "
          f"no hard stop, {DURATION_DAYS}d duration)")
    print("=" * 72)

    print("\nBuilding regime labels...")
    labeled_df, _ = regime_module.build(DATA_DIR)

    print("Loading full candidate universe...")
    candidates = recon.load_candidates(DATA_DIR)
    print(f"Candidates: {len(candidates)}")

    print("Detecting regime transitions + walk-forward ranking...")
    transitions = recon.detect_transitions(labeled_df)
    selections = recon.rank_at_transitions(transitions, labeled_df, candidates)

    print("Loading benchmark (SPY)...")
    bm_path = reader.ticker_path(DATA_DIR, "equities", recon.BENCHMARK)
    bm_prices = reader.load(bm_path)["close"].dropna().sort_index()

    print("Scanning full history for the real 4-gate entry population...")
    raw_events = recon.find_gated_entries(selections, candidates, bm_prices)
    entries = recon.decluster(raw_events)
    print(f"Declustered real gated-entry population: {len(entries)}")

    tickers_used = {e["ticker"] for e in entries}
    ma50_by_ticker = {t: candidates[t][1].rolling(50, min_periods=25).mean() for t in tickers_used}

    vols = []
    for e in entries:
        prices = candidates[e["ticker"]][1]
        e["vol"] = realized_vol_at_entry(prices, e["date"])
        if e["vol"] is not None:
            vols.append(e["vol"])
    q33, q67 = np.quantile(np.array(vols), [1 / 3, 2 / 3])
    for e in entries:
        e["vol_bucket"] = vol_bucket(e["vol"], q33, q67)
    print(f"Vol tercile cutoffs (trailing {VOL_LOOKBACK}d daily-return stdev): "
          f"q33={q33:.4f}, q67={q67:.4f}")

    rows = []
    for trigger in TRIGGER_GRID:
        for pct in TRAILING_GRID:
            by_bucket: dict[str, list[dict]] = {"pooled": [], "low_vol": [], "mid_vol": [], "high_vol": []}
            for e in entries:
                prices = candidates[e["ticker"]][1]
                ma50 = ma50_by_ticker[e["ticker"]]
                trade = simulate_trade(prices, ma50, e["date"], trigger, pct)
                if trade is None:
                    continue
                by_bucket["pooled"].append(trade)
                if e["vol_bucket"] != "unknown":
                    by_bucket[e["vol_bucket"]].append(trade)

            for bucket_name, trades in by_bucket.items():
                stats = summarize(trades)
                rows.append({"trigger": trigger, "trailing_pct": pct,
                             "vol_bucket": bucket_name, **stats})

    df = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n")
    print(df.to_string(index=False))

    print("\nBest (trigger, trailing_pct) per bucket by calmar_like:")
    for bucket_name in ["pooled", "low_vol", "mid_vol", "high_vol"]:
        sub = df[(df["vol_bucket"] == bucket_name) & df["calmar_like"].notna()]
        if sub.empty:
            print(f"  {bucket_name}: no cell had enough observations")
            continue
        best = sub.loc[sub["calmar_like"].idxmax()]
        current = sub[(sub["trigger"] == 0.05) & (sub["trailing_pct"] == 0.05)]
        cur_calmar = current["calmar_like"].iloc[0] if not current.empty else None
        print(f"  {bucket_name}: best=({best['trigger']:.0%}/{best['trailing_pct']:.0%}) "
              f"calmar={best['calmar_like']}  vs current (5%/5%) calmar={cur_calmar}")

    print(
        "\nReading this: if a bucket's best pair clearly beats the current 5%/5% "
        "result on calmar_like (not just noise -- check n too), that's evidence "
        "for a vol-scaled trailing stop. If 5%/5% is already at or near the best "
        "in every bucket, the current single global rule stays -- no added "
        "complexity for no real gain. Analysis only: no change to "
        "run_entry_screen.py without explicit operator go-ahead."
    )


if __name__ == "__main__":
    main()
