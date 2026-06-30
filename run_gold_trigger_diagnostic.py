"""
Gold Overweight Trigger Diagnostic

Empirically finds which macro regime conditions predict gold outperformance.
No thesis imposed — data surfaces the triggers.

Method:
  1. Compute gold's unconditional forward return baseline (all dates)
  2. For every single macro condition (9 features x 3 levels = 27 combos),
     compute gold's forward return distribution at 21d, 63d, 252d
  3. For every pair of conditions with enough N, compute the same
  4. For ry + baa10y + X triples, compute the same
  5. Rank by 63d median lift above unconditional baseline
  6. Mark which conditions are currently active

No regime-end capping: we measure forward returns from signal date
forward (asking "what does gold do from here", not "what within-regime").

Output: console table + gold_trigger_diagnostic.csv
"""
from __future__ import annotations

import io
import itertools
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.store import reader

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "gold_trigger_diagnostic.csv"

HORIZONS = [21, 63, 252]
MIN_N_SINGLE = 30
MIN_N_PAIR   = 20
MIN_N_TRIPLE = 15

# Macro features only — no price action momentum (we want external triggers)
MACRO_FEATURES = [
    "ry", "nominal_10y", "breakeven",
    "baa10y", "hy_oas",
    "t10y3m", "t10y2y",
    "se_10y", "usd",
]


def load_gold(data_dir: Path) -> pd.Series:
    path = reader.ticker_path(data_dir, "commodities", "GC_F")
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index()


def forward_return(prices: pd.Series, date: pd.Timestamp, fwd_days: int) -> float | None:
    idx = prices.index.searchsorted(date)
    if idx >= len(prices):
        return None
    if abs((prices.index[idx] - date).days) > 5:
        return None
    fwd_idx = idx + fwd_days
    if fwd_idx >= len(prices):
        return None
    p0, p1 = prices.iloc[idx], prices.iloc[fwd_idx]
    return (p1 - p0) / p0 if p0 > 0 else None


def compute_stats(prices: pd.Series, dates: pd.DatetimeIndex) -> dict:
    result = {}
    for h in HORIZONS:
        rets = [r for d in dates if (r := forward_return(prices, d, h)) is not None]
        if not rets:
            result[h] = {"n": 0}
            continue
        s = pd.Series(rets)
        result[h] = {
            "n":       len(s),
            "median":  round(float(s.median()), 4),
            "wr":      round(float((s > 0).mean()), 4),
            "p25":     round(float(s.quantile(0.25)), 4),
            "p75":     round(float(s.quantile(0.75)), 4),
        }
    return result


def temporal_diversity(dates: pd.DatetimeIndex) -> str:
    if len(dates) < 2:
        return "THIN"
    span_yr  = (dates[-1] - dates[0]).days / 365.25
    cutoff   = dates[-1] - pd.DateOffset(years=3)
    pct_3y   = float((dates >= cutoff).mean())
    if span_yr >= 10 and pct_3y < 0.50:
        return "ROBUST"
    if span_yr < 5 or pct_3y > 0.80:
        return "THIN"
    return "MODERATE"


def row_from_stats(
    label: str,
    stats: dict,
    baseline: dict,
    dates: pd.DatetimeIndex,
    active: bool,
) -> dict:
    r: dict = {"condition": label, "active": active, "diversity": temporal_diversity(dates)}
    for h in HORIZONS:
        s = stats.get(h, {})
        b = baseline.get(h, {})
        n = s.get("n", 0)
        r[f"n_{h}d"]      = n
        r[f"med_{h}d"]    = s.get("median", float("nan"))
        r[f"wr_{h}d"]     = s.get("wr",     float("nan"))
        r[f"lift_{h}d"]   = (
            round(s["median"] - b.get("median", 0), 4)
            if n > 0 and "median" in s and "median" in b
            else float("nan")
        )
    return r


def main() -> None:
    print("Loading data...")
    labeled_df, thresholds = regime_module.build(DATA_DIR)
    gold = load_gold(DATA_DIR)

    # Available macro regime columns
    avail_features = [
        f for f in MACRO_FEATURES
        if f"{f}_regime" in labeled_df.columns
    ]
    print(f"Available macro features: {avail_features}")

    # Current regime state (for flagging active conditions)
    current = {f"{f}_regime": labeled_df[f"{f}_regime"].iloc[-1] for f in avail_features}
    print(f"\nCurrent regime: {current}\n")

    # ── Unconditional baseline ────────────────────────────────────────────────
    all_dates = labeled_df.index
    baseline = compute_stats(gold, all_dates)
    print("Unconditional baseline (all dates):")
    for h in HORIZONS:
        b = baseline[h]
        print(f"  {h:3}d  n={b['n']}  median={b['median']:+.1%}  wr={b['wr']:.0%}")
    print()

    rows: list[dict] = []

    # ── Single conditions ─────────────────────────────────────────────────────
    print("Computing single conditions...")
    for feat in avail_features:
        col = f"{feat}_regime"
        for level in labeled_df[col].dropna().unique():
            mask  = labeled_df[col] == level
            dates = labeled_df.index[mask]
            stats = compute_stats(gold, dates)
            n63 = stats.get(63, {}).get("n", 0)
            if n63 < MIN_N_SINGLE:
                continue
            label  = f"{feat}={level}"
            active = (current.get(col) == level)
            rows.append(row_from_stats(label, stats, baseline, dates, active))

    # ── Double conditions ─────────────────────────────────────────────────────
    print("Computing pair conditions...")
    for f1, f2 in itertools.combinations(avail_features, 2):
        c1, c2 = f"{f1}_regime", f"{f2}_regime"
        for l1 in labeled_df[c1].dropna().unique():
            for l2 in labeled_df[c2].dropna().unique():
                mask  = (labeled_df[c1] == l1) & (labeled_df[c2] == l2)
                dates = labeled_df.index[mask]
                stats = compute_stats(gold, dates)
                n63 = stats.get(63, {}).get("n", 0)
                if n63 < MIN_N_PAIR:
                    continue
                label  = f"{f1}={l1} + {f2}={l2}"
                active = (current.get(c1) == l1) and (current.get(c2) == l2)
                rows.append(row_from_stats(label, stats, baseline, dates, active))

    # ── Triple conditions: ry + baa10y + X ───────────────────────────────────
    print("Computing triple conditions (ry + baa10y + X)...")
    anchor_feats = ["ry", "baa10y"]
    extra_feats  = [f for f in avail_features if f not in anchor_feats]
    ca, cb = "ry_regime", "baa10y_regime"

    for la in labeled_df[ca].dropna().unique():
        for lb in labeled_df[cb].dropna().unique():
            base_mask = (labeled_df[ca] == la) & (labeled_df[cb] == lb)
            for fx in extra_feats:
                cx = f"{fx}_regime"
                for lx in labeled_df[cx].dropna().unique():
                    mask  = base_mask & (labeled_df[cx] == lx)
                    dates = labeled_df.index[mask]
                    stats = compute_stats(gold, dates)
                    n63 = stats.get(63, {}).get("n", 0)
                    if n63 < MIN_N_TRIPLE:
                        continue
                    label  = f"ry={la} + baa10y={lb} + {fx}={lx}"
                    active = (
                        current.get(ca) == la
                        and current.get(cb) == lb
                        and current.get(cx) == lx
                    )
                    rows.append(row_from_stats(label, stats, baseline, dates, active))

    # ── Results ───────────────────────────────────────────────────────────────
    df = pd.DataFrame(rows)
    df = df.sort_values("lift_63d", ascending=False).reset_index(drop=True)

    print(f"\n{'='*100}")
    print(f"GOLD OVERWEIGHT TRIGGERS — ranked by 63d median lift above unconditional baseline")
    print(f"  Baseline: 63d median={baseline[63]['median']:+.1%}  252d median={baseline[252]['median']:+.1%}")
    print(f"  * = currently active condition")
    print(f"{'='*100}")

    cols_show = ["condition", "active", "diversity",
                 "n_63d", "med_63d", "wr_63d", "lift_63d",
                 "n_252d", "med_252d", "wr_252d", "lift_252d"]
    print(df[cols_show].to_string(index=True, max_rows=60))

    # Active conditions summary
    active_df = df[df["active"]].reset_index(drop=True)
    print(f"\n{'='*100}")
    print("CURRENTLY ACTIVE CONDITIONS (today's regime state):")
    print(f"{'='*100}")
    if not active_df.empty:
        print(active_df[cols_show].to_string(index=False))
    else:
        print("  None of the tested conditions match today's regime.")

    print(f"\n{'='*100}")
    print("TOP 10 SINGLE CONDITIONS by 63d lift:")
    print(f"{'='*100}")
    singles = df[~df["condition"].str.contains(" \\+ ")].head(10)
    print(singles[cols_show].to_string(index=False))

    print(f"\n{'='*100}")
    print("TOP 10 PAIR CONDITIONS by 63d lift:")
    print(f"{'='*100}")
    pairs = df[df["condition"].str.count(" \\+ ") == 1].head(10)
    print(pairs[cols_show].to_string(index=False))

    print(f"\n{'='*100}")
    print("TOP 10 TRIPLE CONDITIONS by 63d lift:")
    print(f"{'='*100}")
    triples = df[df["condition"].str.count(" \\+ ") == 2].head(10)
    print(triples[cols_show].to_string(index=False))

    OUT_CSV.parent.mkdir(exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nFull results saved to: {OUT_CSV}")


if __name__ == "__main__":
    main()
