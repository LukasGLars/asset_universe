"""
Regime survey: top assets in each of the 9 regime combinations.

Runs the conditional return engine across all 524 assets in the parquet store
for all RY x BAA combinations. Used to decide which regimes need separate
optimizers and which can be merged.

Usage:
    python run_regime_survey.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent / "src"))

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.analysis.engine import _regime_end_dates
from asset_universe.store import reader

DATA_DIR   = config.raw_data_dir()
TOP_N      = 10       # top assets to show per regime
MIN_N_OBS  = 20
MIN_HIST_YR = 10
MAX_UP      = 0.50
FWD_DAYS    = 252

CATEGORIES = ["equities", "commodities", "intl_etfs"]

REGIMES = [
    {"ry": "HIGH", "baa": "TIGHT"},
    {"ry": "HIGH", "baa": "MID"},
    {"ry": "HIGH", "baa": "WIDE"},
    {"ry": "MID",  "baa": "TIGHT"},
    {"ry": "MID",  "baa": "MID"},
    {"ry": "MID",  "baa": "WIDE"},
    {"ry": "LOW",  "baa": "TIGHT"},
    {"ry": "LOW",  "baa": "MID"},
    {"ry": "LOW",  "baa": "WIDE"},
]


def load_prices(cat: str, name: str) -> pd.Series:
    path = reader.ticker_path(DATA_DIR, cat, name)
    if not path.exists():
        return pd.Series(dtype=float)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index().dropna()


def fwd_return(prices, date, days, regime_end=None):
    idx = prices.index.searchsorted(date)
    if idx >= len(prices) or abs((prices.index[idx] - date).days) > 5:
        return None
    fwd_idx = idx + days
    if regime_end is not None:
        end_idx = prices.index.searchsorted(regime_end)
        fwd_idx = min(fwd_idx, end_idx)
    if fwd_idx >= len(prices) or fwd_idx <= idx:
        return None
    p0, p1 = prices.iloc[idx], prices.iloc[fwd_idx]
    return (p1 - p0) / p0 if p0 > 0 else None


# ── Load all assets once ──────────────────────────────────────────────────────
print("Loading all assets ...", flush=True)
assets: list[dict] = []
for cat in CATEGORIES:
    cat_dir = DATA_DIR / cat
    if not cat_dir.exists():
        continue
    for f in sorted(cat_dir.glob("*.parquet")):
        prices = load_prices(cat, f.stem)
        if prices.empty:
            continue
        hist_yr = len(prices) / 252
        if hist_yr < MIN_HIST_YR:
            continue
        max_up = prices.pct_change().max()
        if max_up > MAX_UP:
            continue
        assets.append({"name": f.stem, "cat": cat, "prices": prices, "hist_yr": hist_yr})

print(f"  {len(assets)} assets passed quality filters\n", flush=True)

# ── Build regime labels ───────────────────────────────────────────────────────
labeled_df, _ = regime_module.build(DATA_DIR)

# ── Survey each regime combination ───────────────────────────────────────────
results: dict[str, list[dict]] = {}

for reg in REGIMES:
    ry, baa = reg["ry"], reg["baa"]
    key = f"{ry}+{baa}"
    conditions = {"ry_regime": ry, "baa10y_regime": baa}

    mask = pd.Series(True, index=labeled_df.index)
    for k, v in conditions.items():
        mask &= labeled_df[k] == v
    matched = labeled_df.index[mask]

    if len(matched) < MIN_N_OBS:
        results[key] = []
        continue

    regime_ends = _regime_end_dates(labeled_df, conditions, matched)

    rows = []
    for a in assets:
        prices = a["prices"]
        ret_pairs = [
            (dt, r) for dt in matched
            if (r := fwd_return(prices, dt, FWD_DAYS, regime_ends.get(dt))) is not None
        ]
        if len(ret_pairs) < MIN_N_OBS:
            continue
        rets = [r for _, r in ret_pairs]
        s = pd.Series(rets)
        rows.append({
            "ticker":  a["name"],
            "cat":     a["cat"],
            "n":       len(rets),
            "median":  float(s.median()),
            "mu":      float(s.mean()),
            "sigma":   float(s.std()),
            "win":     float((s > 0).mean()),
            "hist_yr": a["hist_yr"],
        })

    rows.sort(key=lambda x: -x["median"])
    results[key] = rows
    print(f"  {key}: {len(matched):>4} dates, {len(rows):>3} qualifying assets", flush=True)

# ── Output ────────────────────────────────────────────────────────────────────
W = 76
print()
print("=" * W)
print("REGIME SURVEY  --  Top assets by 252d median return, regime-capped")
print("=" * W)

for reg in REGIMES:
    ry, baa = reg["ry"], reg["baa"]
    key = f"{ry}+{baa}"
    conditions = {"ry_regime": ry, "baa10y_regime": baa}

    mask = pd.Series(True, index=labeled_df.index)
    for k, v in conditions.items():
        mask &= labeled_df[k] == v
    matched = labeled_df.index[mask]

    rows = results.get(key, [])

    print(f"\n  {key}  ({len(matched)} matched dates", end="")
    if len(matched) > 0:
        print(f", {matched[0].date()} - {matched[-1].date()})", end="")
    print(")")

    if not rows:
        print("    Insufficient data.")
        continue

    print(f"  {'#':<3} {'Ticker':<12} {'Cat':<12} {'Median':>8} {'Mu':>8} "
          f"{'Sigma':>7} {'Win%':>6} {'N':>5} {'Hist':>5}")
    print("  " + "-" * 70)
    for i, r in enumerate(rows[:TOP_N], 1):
        print(f"  {i:<3} {r['ticker']:<12} {r['cat']:<12} "
              f"{r['median']:>+7.1%} {r['mu']:>+7.1%} "
              f"{r['sigma']:>6.1%} {r['win']:>5.0%} "
              f"{r['n']:>5} {r['hist_yr']:>4.0f}yr")

print()
print("=" * W)
print("END REGIME SURVEY")
print("=" * W)
