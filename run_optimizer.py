"""
Portfolio Optimizer — Regime-Conditional (v2)

Objective: maximize approximate portfolio geometric mean
  g(w) ~ sum(w_i * mu_i) - 0.5 * sum(w_i^2 * sigma_i^2)

No covariance matrix — per-asset distributions on full history.
Shrinkage toward cross-sectional prior for short-history assets.
Returns capped at regime end date (no bleed into next regime).

Usage:
    python run_optimizer.py
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

DATA_DIR = config.raw_data_dir()

# ── Configuration ─────────────────────────────────────────────────────────────
CONDITIONS     = {"ry_regime": "HIGH", "baa10y_regime": "TIGHT"}
N_CANDIDATES   = 50       # top N from universe screen to consider
MAX_W          = 0.35     # max weight per asset
MIN_GOLD_W     = 0.05     # minimum allocation to gold proxy
SHRINK_LAMBDA  = 100      # shrinkage: effective weight = N / (N + lambda)
MIN_N_OBS        = 20     # minimum matched observations to include an asset
MIN_HISTORY_YR   = 10     # minimum price history to be trusted (filters recent IPOs)
MAX_SINGLE_DAY_UP = 0.50  # exclude assets with any single-day gain above this (M&A / halt-to-buy)
GOLD_PROXY       = "GC_F" # gold proxy — 26yr history in parquet (commodities)
N_RESTARTS     = 50

# Tickers excluded from optimization — add any asset whose historical return
# is dominated by a single non-repeatable episode (M&A, commodity supercycle, etc.)
EXCLUDE_TICKERS: set[str] = {"CF"}  # 2006-2007 fertilizer supercycle drives mu; not a thesis we can validate


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_prices(cat: str, safe: str) -> pd.Series:
    path = reader.ticker_path(DATA_DIR, cat, safe)
    if not path.exists():
        return pd.Series(dtype=float)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index().dropna()


def fwd_return(
    prices: pd.Series,
    date: pd.Timestamp,
    days: int,
    regime_end: pd.Timestamp | None = None,
) -> float | None:
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
    """
    Returns (max_3yr_fraction, label).
    Checks what share of valid return observations fall in any rolling 3-year window.

    The HIGH/TIGHT regime naturally clusters in two periods (pre-2008 and 2023-present),
    so any single-episode asset will show ~100% concentration. Labels reflect this:
      ROBUST   < 50%  — spans multiple regime episodes, strong cross-validation
      MODERATE 50-80% — partial cross-episode coverage, normal shrinkage
      THIN     80-95% — mostly one episode, lambda * 2
      SINGLE   > 95%  — entirely one episode, lambda * 4 (no cross-validation)
    """
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


def map_category(cat_raw: str) -> str:
    cat_raw = cat_raw.lower()
    if "commodit" in cat_raw:   # matches both "commodity" and "commodities"
        return "commodities"
    if "etf" in cat_raw or "ucits" in cat_raw:
        return "intl_etfs"
    return "equities"


# ── Build universe ────────────────────────────────────────────────────────────

screen_path = Path(__file__).parent / "universe_screen_results.csv"
if not screen_path.exists():
    print("ERROR: universe_screen_results.csv not found. Run run_universe_screen.py first.")
    sys.exit(1)

screen_df = pd.read_csv(screen_path)
top_n = screen_df.head(N_CANDIDATES)[["ticker", "category"]].to_dict("records")

# Ensure gold proxy is included
if not any(e["ticker"] == GOLD_PROXY for e in top_n):
    top_n.append({"ticker": GOLD_PROXY, "category": "commodities"})

# ── Regime labels + matched dates ─────────────────────────────────────────────
print("Building regime labels ...", flush=True)
labeled_df, _ = regime_module.build(DATA_DIR)

mask = pd.Series(True, index=labeled_df.index)
for k, v in CONDITIONS.items():
    mask &= labeled_df[k] == v
matched_dates = labeled_df.index[mask]

regime_ends = _regime_end_dates(labeled_df, CONDITIONS, matched_dates)

span_yr = (matched_dates[-1] - matched_dates[0]).days / 365.25
pct_3y  = float((matched_dates >= matched_dates[-1] - pd.DateOffset(years=3)).mean())
diversity = (
    "ROBUST" if span_yr >= 10 and pct_3y < 0.50 else
    "THIN"   if span_yr < 5  or pct_3y > 0.80   else
    "MODERATE"
)

print(f"  Conditions    : {CONDITIONS}")
print(f"  Matched dates : {len(matched_dates)}  "
      f"({matched_dates[0].date()} - {matched_dates[-1].date()})  {diversity}")

# ── Per-asset return distributions (capped, full history) ─────────────────────
print(f"\nComputing capped 252d distributions for {len(top_n)} candidates ...", flush=True)

candidates: list[dict] = []

for entry in top_n:
    tkr = entry["ticker"]
    if tkr in EXCLUDE_TICKERS:
        print(f"  {tkr:<8}  excluded (see EXCLUDE_TICKERS)")
        continue
    cat = map_category(entry.get("category", ""))
    prices = load_prices(cat, reader.safe_name(tkr))
    if prices.empty:
        print(f"  {tkr:<8}  no data")
        continue

    history_yr = len(prices) / 252

    if history_yr < MIN_HISTORY_YR:
        print(f"  {tkr:<8}  hist={history_yr:.0f}yr  (below min {MIN_HISTORY_YR}yr, skipped)")
        continue

    max_up = prices.pct_change().max()
    if max_up > MAX_SINGLE_DAY_UP:
        print(f"  {tkr:<8}  max_up={max_up:.0%}  (M&A / corporate event detected, skipped)")
        continue

    ret_pairs = [
        (dt, r) for dt in matched_dates
        if (r := fwd_return(prices, dt, 252, regime_ends.get(dt))) is not None
    ]
    rets        = [r  for _, r in ret_pairs]
    valid_dates = [dt for dt, _ in ret_pairs]

    if len(rets) < MIN_N_OBS:
        print(f"  {tkr:<8}  N={len(rets):>3}  (below min obs {MIN_N_OBS}, skipped)")
        continue

    conc, div_label = temporal_concentration(valid_dates)

    lambda_mult = {"SINGLE": 4.0, "THIN": 2.0, "MODERATE": 1.0, "ROBUST": 1.0}[div_label]
    s = pd.Series(rets)

    candidates.append({
        "ticker":      tkr,
        "mu":          float(s.mean()),
        "sigma":       float(s.std()),
        "median":      float(s.median()),
        "win":         float((s > 0).mean()),
        "n":           len(rets),
        "history_yr":  history_yr,
        "div_label":   div_label,
        "conc":        conc,
        "lambda_mult": lambda_mult,
    })
    print(f"  {tkr:<8}  N={len(rets):>4}  mu={s.mean():>+7.1%}  "
          f"sigma={s.std():>6.1%}  hist={history_yr:.0f}yr  [{div_label}]")

if len(candidates) < 6:
    print(f"\nERROR: only {len(candidates)} candidates with sufficient data. Cannot optimize.")
    sys.exit(1)

# ── Shrinkage toward cross-sectional prior ────────────────────────────────────
prior_mu = float(np.mean([c["mu"] for c in candidates]))
print(f"\nCross-sectional prior mu : {prior_mu:+.1%}  (shrinkage target)")
print(f"Shrinkage lambda         : {SHRINK_LAMBDA}  "
      f"(asset needs N>>{SHRINK_LAMBDA} to be fully trusted)")

for c in candidates:
    eff_lambda    = SHRINK_LAMBDA * c["lambda_mult"]
    shrink        = c["n"] / (c["n"] + eff_lambda)
    c["mu_final"] = shrink * c["mu"] + (1 - shrink) * prior_mu
    c["shrink"]   = shrink

# ── Check gold proxy is present ───────────────────────────────────────────────
gold_idx = next((i for i, c in enumerate(candidates) if c["ticker"] == GOLD_PROXY), None)
if gold_idx is None:
    print(f"\nWARNING: {GOLD_PROXY} not in candidates — gold constraint relaxed.")
    min_gold_constraint = []
else:
    min_gold_constraint = [
        {"type": "ineq", "fun": lambda w, gi=gold_idx: w[gi] - MIN_GOLD_W}
    ]

# ── Optimizer ─────────────────────────────────────────────────────────────────
n    = len(candidates)
mus  = np.array([c["mu_final"] for c in candidates])
sigs = np.array([c["sigma"]    for c in candidates])


def neg_geomean(w: np.ndarray) -> float:
    # g(w) ~ sum(w_i * mu_i) - 0.5 * sum(w_i^2 * sigma_i^2)
    return -(np.dot(w, mus) - 0.5 * np.dot(w ** 2, sigs ** 2))


bounds      = [(0.0, MAX_W)] * n
constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}] + min_gold_constraint

print(f"\nOptimizing ({N_RESTARTS} restarts, {n} candidates) ...", flush=True)
best = None
rng  = np.random.default_rng(42)

for _ in range(N_RESTARTS):
    w0  = rng.dirichlet(np.ones(n))
    res = minimize(
        neg_geomean, w0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 2000, "ftol": 1e-12},
    )
    if res.success and (best is None or res.fun < best.fun):
        best = res

if best is None:
    print("Optimization failed — no successful run.")
    sys.exit(1)

w_opt  = np.clip(best.x, 0.0, None)
w_opt /= w_opt.sum()

# ── Evaluation ────────────────────────────────────────────────────────────────
g_opt     = -best.fun
n_active  = int((w_opt >= 0.01).sum())

# Equal-weight benchmark
w_eq  = np.ones(n) / n
g_eq  = float(np.dot(w_eq, mus) - 0.5 * np.dot(w_eq ** 2, sigs ** 2))

# ── Output ────────────────────────────────────────────────────────────────────
W = 72
print()
print("=" * W)
print("PORTFOLIO OPTIMIZER  --  Regime: RY=HIGH + BAA10Y=TIGHT")
print("=" * W)
print(f"  Universe       : top {N_CANDIDATES} screen candidates + {GOLD_PROXY}")
print(f"  Matched dates  : {len(matched_dates)}  {diversity}")
print(f"  Shrinkage      : lambda={SHRINK_LAMBDA}  prior={prior_mu:+.1%}")
print()
print(f"  {'Ticker':<8}  {'Weight':>7}  {'mu(raw)':>8}  {'mu(shr)':>8}  "
      f"{'sigma':>7}  {'N':>5}  {'Hist':>5}  {'Div':>8}")
print("  " + "-" * 65)

sorted_idx = np.argsort(-w_opt)
for i in sorted_idx:
    w = w_opt[i]
    if w < 0.005:
        continue
    c = candidates[i]
    gold_tag = "  [gold]" if c["ticker"] == GOLD_PROXY else ""
    print(f"  {c['ticker']:<8}  {w:>7.1%}  {c['mu']:>+8.1%}  {c['mu_final']:>+8.1%}  "
          f"{c['sigma']:>7.1%}  {c['n']:>5}  {c['history_yr']:>4.0f}yr"
          f"  {c['div_label']:>8}{gold_tag}")

print()
print(f"  Active positions   : {n_active}  (weight >= 1%)")
print(f"  Equal-weight g(w)  : {g_eq:>+.1%}  (benchmark)")
print(f"  Optimized g(w)     : {g_opt:>+.1%}")
print()
if n_active < 6:
    print(f"  WARNING: only {n_active} active positions — below recommended minimum of 6.")
    print(f"  Consider reducing MAX_W or increasing N_CANDIDATES.")
print()
print("  NOTE: g(w) is an approximation. mu/sigma are regime-conditional,")
print("  capped at regime end. Shrinkage applied for short-history assets.")
print("=" * W)
