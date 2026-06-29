"""
Multi-regime portfolio optimizer.

Runs the regime-conditional optimizer for all 9 RY x BAA combinations.
Uses the full parquet store (no screen pre-filter) per INTEGRITY.md.
Saves weights to optimizer_results/{RY}_{BAA}.csv for use by the backtest.

Usage:
    python run_optimizer_all_regimes.py
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent / "src"))
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.analysis.engine import _regime_end_dates
from asset_universe.store import reader

DATA_DIR    = config.raw_data_dir()
RESULTS_DIR = Path(__file__).parent / "optimizer_results"
RESULTS_DIR.mkdir(exist_ok=True)

# ── Configuration ─────────────────────────────────────────────────────────────
MAX_W           = 0.35
MIN_GOLD_W      = 0.05
SHRINK_LAMBDA   = 100
MIN_N_OBS       = 20
MIN_HIST_YR     = 10
MAX_SINGLE_DAY_UP = 0.50
GOLD_PROXY      = "GC_F"
N_RESTARTS      = 50
CATEGORIES      = ["equities", "commodities", "intl_etfs"]
FWD_DAYS        = 252

EXCLUDE_TICKERS: set[str] = {"CF"}

ALL_REGIMES = [
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_prices(cat: str, stem: str) -> pd.Series:
    path = reader.ticker_path(DATA_DIR, cat, stem)
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


def temporal_concentration(dates: list) -> tuple[float, str]:
    if not dates:
        return 1.0, "SINGLE"
    arr = pd.DatetimeIndex(sorted(dates))
    n = len(arr)
    three_yr = pd.Timedelta(days=3 * 365)
    max_frac = 0.0
    for start in arr:
        end = start + three_yr
        count = int(arr.searchsorted(end, side="right")) - int(arr.searchsorted(start, side="left"))
        if count / n > max_frac:
            max_frac = count / n
    if max_frac > 0.95:
        return max_frac, "SINGLE"
    if max_frac > 0.80:
        return max_frac, "THIN"
    if max_frac > 0.50:
        return max_frac, "MODERATE"
    return max_frac, "ROBUST"


# ── Load all assets once ──────────────────────────────────────────────────────
print("Loading assets ...", flush=True)
all_assets: list[dict] = []
for cat in CATEGORIES:
    cat_dir = DATA_DIR / cat
    if not cat_dir.exists():
        continue
    for f in sorted(cat_dir.glob("*.parquet")):
        stem = f.stem
        if stem in EXCLUDE_TICKERS:
            continue
        prices = load_prices(cat, stem)
        if prices.empty:
            continue
        hist_yr = len(prices) / 252
        if hist_yr < MIN_HIST_YR:
            continue
        if prices.pct_change().max() > MAX_SINGLE_DAY_UP:
            continue
        all_assets.append({"ticker": stem, "cat": cat, "prices": prices, "hist_yr": hist_yr})

print(f"  {len(all_assets)} assets passed quality filters\n", flush=True)

# ── Build regime labels ───────────────────────────────────────────────────────
labeled_df, _ = regime_module.build(DATA_DIR)


# ── Optimize one regime ───────────────────────────────────────────────────────

def optimize_regime(ry: str, baa: str) -> pd.DataFrame | None:
    key = f"{ry}+{baa}"
    conditions = {"ry_regime": ry, "baa10y_regime": baa}

    mask = pd.Series(True, index=labeled_df.index)
    for k, v in conditions.items():
        mask &= labeled_df[k] == v
    matched = labeled_df.index[mask]

    if len(matched) < MIN_N_OBS:
        print(f"  {key}: only {len(matched)} matched dates — skipped")
        return None

    regime_ends = _regime_end_dates(labeled_df, conditions, matched)

    # ── Per-asset distributions ───────────────────────────────────────────────
    print(f"  {key}: {len(matched)} dates — computing distributions ...", flush=True)
    candidates: list[dict] = []
    for i, a in enumerate(all_assets):
        prices = a["prices"]
        ret_pairs = [
            (dt, r) for dt in matched
            if (r := fwd_return(prices, dt, FWD_DAYS, regime_ends.get(dt))) is not None
        ]
        if (i + 1) % 100 == 0:
            print(f"    {i + 1}/{len(all_assets)} assets ...", flush=True)
        if len(ret_pairs) < MIN_N_OBS:
            continue

        rets        = [r  for _, r in ret_pairs]
        valid_dates = [dt for dt, _ in ret_pairs]
        conc, div   = temporal_concentration(valid_dates)
        lam_mult    = {"SINGLE": 4.0, "THIN": 2.0, "MODERATE": 1.0, "ROBUST": 1.0}[div]

        s = pd.Series(rets)
        candidates.append({
            "ticker":      a["ticker"],
            "cat":         a["cat"],
            "mu":          float(s.mean()),
            "sigma":       float(s.std()),
            "n":           len(rets),
            "hist_yr":     a["hist_yr"],
            "div_label":   div,
            "lambda_mult": lam_mult,
        })

    if len(candidates) < 4:
        print(f"  {key}: only {len(candidates)} qualifying assets — skipped")
        return None

    # ── Shrinkage ─────────────────────────────────────────────────────────────
    prior_mu = float(np.mean([c["mu"] for c in candidates]))
    for c in candidates:
        eff_lam       = SHRINK_LAMBDA * c["lambda_mult"]
        shrink        = c["n"] / (c["n"] + eff_lam)
        c["mu_final"] = shrink * c["mu"] + (1 - shrink) * prior_mu
        c["shrink"]   = shrink

    # ── Gold constraint ───────────────────────────────────────────────────────
    gold_idx = next((i for i, c in enumerate(candidates) if c["ticker"] == GOLD_PROXY), None)
    min_gold = (
        [{"type": "ineq", "fun": lambda w, gi=gold_idx: w[gi] - MIN_GOLD_W}]
        if gold_idx is not None else []
    )

    # ── Optimize ──────────────────────────────────────────────────────────────
    n    = len(candidates)
    mus  = np.array([c["mu_final"] for c in candidates])
    sigs = np.array([c["sigma"]    for c in candidates])

    def neg_geomean(w):
        return -(np.dot(w, mus) - 0.5 * np.dot(w ** 2, sigs ** 2))

    bounds      = [(0.0, MAX_W)] * n
    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}] + min_gold

    rng  = np.random.default_rng(42)
    best = None
    for _ in range(N_RESTARTS):
        w0  = rng.dirichlet(np.ones(n))
        res = minimize(neg_geomean, w0, method="SLSQP", bounds=bounds,
                       constraints=constraints, options={"maxiter": 2000, "ftol": 1e-12})
        if res.success and (best is None or res.fun < best.fun):
            best = res

    if best is None:
        print(f"  {key}: optimization failed")
        return None

    w_opt  = np.clip(best.x, 0.0, None)
    w_opt /= w_opt.sum()
    g_opt  = -best.fun

    w_eq  = np.ones(n) / n
    g_eq  = float(np.dot(w_eq, mus) - 0.5 * np.dot(w_eq ** 2, sigs ** 2))

    # ── Build result DataFrame ────────────────────────────────────────────────
    rows = []
    for i, c in enumerate(candidates):
        if w_opt[i] >= 0.005:
            rows.append({
                "ticker":    c["ticker"],
                "weight":    round(float(w_opt[i]), 6),
                "mu_raw":    round(c["mu"],       4),
                "mu_shrunk": round(c["mu_final"], 4),
                "sigma":     round(c["sigma"],    4),
                "n":         c["n"],
                "hist_yr":   round(c["hist_yr"],  1),
                "div_label": c["div_label"],
                "ry":        ry,
                "baa":       baa,
            })

    df = pd.DataFrame(rows).sort_values("weight", ascending=False).reset_index(drop=True)

    n_active = int((w_opt >= 0.01).sum())
    print(f"  {key}: {len(matched):>4}d  {n_active} positions  "
          f"g(w)={g_opt:+.1%}  eq={g_eq:+.1%}  prior={prior_mu:+.1%}")

    return df, g_opt, g_eq, len(matched)


# ── Run all regimes ───────────────────────────────────────────────────────────
W = 72
print("=" * W)
print("MULTI-REGIME OPTIMIZER")
print("=" * W)

summary_rows = []

for reg in ALL_REGIMES:
    ry, baa = reg["ry"], reg["baa"]
    result = optimize_regime(ry, baa)
    if result is None:
        continue

    df, g_opt, g_eq, n_dates = result
    key = f"{ry}_{baa}"

    # Save weights
    out_path = RESULTS_DIR / f"{key}.csv"
    df.to_csv(out_path, index=False)

    summary_rows.append({
        "regime":     f"{ry}+{baa}",
        "n_dates":    n_dates,
        "n_pos":      len(df),
        "g_opt":      g_opt,
        "g_eq":       g_eq,
        "top3":       ", ".join(df.head(3)["ticker"].tolist()),
    })

# ── Summary table ─────────────────────────────────────────────────────────────
print()
print(f"\n{'Regime':<14} {'N':>5}  {'Pos':>4}  {'g(w)':>7}  {'EqW':>7}  Top 3")
print("-" * 72)
for r in summary_rows:
    print(f"  {r['regime']:<12} {r['n_dates']:>5}  {r['n_pos']:>4}  "
          f"{r['g_opt']:>+6.1%}  {r['g_eq']:>+6.1%}  {r['top3']}")

print(f"\nWeights saved to: {RESULTS_DIR}/")
print("=" * W)
