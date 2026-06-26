"""
Portfolio Optimizer — Regime-Conditional

Maximizes CAGR (geometric mean) using empirical 252d forward return
distributions conditioned on the current macro regime.

No DCA. No Gaussian assumptions. Uses actual historical matched returns.

Conditions : RY=HIGH + BAA10Y=TIGHT  (empirically validated Core 2)
Candidates : entry-filtered assets from run_universe_screen + screen_tactical
Objective  : maximize geometric mean of portfolio 252d returns
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from asset_universe import config
from asset_universe.analysis import regimes as regime_module

DATA_DIR = config.raw_data_dir()

CONDITIONS = {"ry_regime": "HIGH", "baa10y_regime": "TIGHT"}

# Entry-filtered candidates (passed all 4 gates) + mandatory gold
CANDIDATES: dict[str, tuple[str, str]] = {
    "CMI":  ("equities",    "CMI"),
    "NRG":  ("equities",    "NRG"),
    "WBD":  ("equities",    "WBD"),
    "GRMN": ("equities",    "GRMN"),
    "ETR":  ("equities",    "ETR"),
    "EME":  ("equities",    "EME"),
    "COHR": ("equities",    "COHR"),
    "CHRW": ("equities",    "CHRW"),
    "DE":   ("equities",    "DE"),
    "CCJ":  ("equities",    "CCJ"),
    "TPR":  ("equities",    "TPR"),
    "L":    ("equities",    "L"),
    "CBRE": ("equities",    "CBRE"),
    "VTR":  ("equities",    "VTR"),
    "GC_F": ("commodities", "GC_F"),   # mandatory non-equity
}

MAX_W      = 0.35   # max 35% per asset
N_RESTARTS = 30


def _load_prices(cat: str, ticker: str) -> pd.Series:
    path = DATA_DIR / cat / f"{ticker}.parquet"
    if not path.exists():
        return pd.Series(dtype=float)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index().dropna()


def _fwd_return(prices: pd.Series, date: pd.Timestamp, fwd: int) -> float | None:
    idx = prices.index.searchsorted(date)
    if idx >= len(prices) or abs((prices.index[idx] - date).days) > 5:
        return None
    fwd_idx = idx + fwd
    if fwd_idx >= len(prices):
        return None
    p0, p1 = prices.iloc[idx], prices.iloc[fwd_idx]
    return (p1 - p0) / p0 if p0 > 0 else None


# ── Regime labels + matched dates ─────────────────────────────────────────────
print("Building regime labels ...", flush=True)
labeled_df, _ = regime_module.build(DATA_DIR)

mask = pd.Series(True, index=labeled_df.index)
for k, v in CONDITIONS.items():
    mask &= labeled_df[k] == v
matched_dates = labeled_df.index[mask]
print(f"  Conditions    : {CONDITIONS}", flush=True)
print(f"  Matched dates : {len(matched_dates)}  "
      f"({matched_dates[0].date()} — {matched_dates[-1].date()})", flush=True)

# ── Build 252d return series per asset ────────────────────────────────────────
print("\nComputing 252d forward returns per asset ...", flush=True)
series: dict[str, pd.Series] = {}

for tkr, (cat, fname) in CANDIDATES.items():
    prices = _load_prices(cat, fname)
    if prices.empty:
        print(f"  {tkr:<8}  no data", flush=True)
        continue
    rets = {dt: r for dt in matched_dates
            if (r := _fwd_return(prices, dt, 252)) is not None}
    s = pd.Series(rets)
    series[tkr] = s
    nyrs = len(prices) / 252
    print(f"  {tkr:<8}  N={len(s):>4}  history={nyrs:.1f}yr  "
          f"({prices.index[0].date()} — {prices.index[-1].date()})", flush=True)

# ── Return matrix on common dates ─────────────────────────────────────────────
df_ret = pd.DataFrame(series).dropna()

if len(df_ret) < 30:
    print(f"\nERROR: only {len(df_ret)} common dates — cannot optimize.")
    sys.exit(1)

tickers = list(df_ret.columns)
R       = df_ret.values          # (n_dates, n_assets)
n       = len(tickers)
dates   = df_ret.index

span_yr = (dates[-1] - dates[0]).days / 365.25
pct_3y  = float((dates >= dates[-1] - pd.DateOffset(years=3)).mean())
diversity = ("ROBUST" if span_yr >= 10 and pct_3y < 0.50
             else "THIN" if span_yr < 5 or pct_3y > 0.80
             else "MODERATE")

print(f"\nReturn matrix : {len(df_ret)} dates x {n} assets  "
      f"span={span_yr:.1f}yr  pct_3yr={pct_3y:.0%}  {diversity}", flush=True)

# ── Optimizer ─────────────────────────────────────────────────────────────────
def neg_geomean(w: np.ndarray) -> float:
    port = np.clip(R @ w, -0.999, None)
    return -float(np.exp(np.log1p(port).mean()) - 1)

bounds      = [(0.0, MAX_W)] * n
constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]

print(f"\nOptimizing ({N_RESTARTS} restarts) ...", flush=True)
best = None
rng  = np.random.default_rng(42)
for _ in range(N_RESTARTS):
    w0  = rng.dirichlet(np.ones(n))
    res = minimize(neg_geomean, w0, method="SLSQP",
                   bounds=bounds, constraints=constraints,
                   options={"maxiter": 2000, "ftol": 1e-12})
    if res.success and (best is None or res.fun < best.fun):
        best = res

if best is None:
    print("Optimization failed.")
    sys.exit(1)

w_opt      = np.clip(best.x, 0.0, None)
w_opt     /= w_opt.sum()

# ── Evaluation ────────────────────────────────────────────────────────────────
port_rets  = R @ w_opt
port_clip  = np.clip(port_rets, -0.999, None)
port_cagr  = float(np.exp(np.log1p(port_clip).mean()) - 1)
port_med   = float(np.median(port_rets))
port_win   = float((port_rets > 0).mean())
port_p10   = float(np.percentile(port_rets, 10))
port_p90   = float(np.percentile(port_rets, 90))

# Equal-weight benchmark
w_eq       = np.ones(n) / n
eq_rets    = np.clip(R @ w_eq, -0.999, None)
eq_cagr    = float(np.exp(np.log1p(eq_rets).mean()) - 1)

# ── Output ────────────────────────────────────────────────────────────────────
W = 80
print()
print("=" * W)
print("PORTFOLIO OPTIMIZER  —  Regime: RY=HIGH + BAA10Y=TIGHT")
print("=" * W)
print(f"  Return matrix  : {len(df_ret)} dates  "
      f"({dates[0].date()} — {dates[-1].date()})  {diversity}")
print(f"  Span           : {span_yr:.1f}yr  |  Last-3yr: {pct_3y:.0%}")
print()
print(f"  {'Ticker':<8}  {'Weight':>7}  {'Ind.CAGR':>9}  {'Ind.Med':>8}  {'Note'}")
print("  " + "-" * 55)

for i, tkr in enumerate(tickers):
    w = w_opt[i]
    ind_rets  = np.clip(R[:, i], -0.999, None)
    ind_cagr  = float(np.exp(np.log1p(ind_rets).mean()) - 1)
    ind_med   = float(np.median(R[:, i]))
    note      = "gold" if tkr == "GC_F" else ""
    marker    = " <<" if w >= 0.10 else ""
    if w >= 0.005:
        print(f"  {tkr:<8}  {w:>7.1%}  {ind_cagr:>+9.1%}  {ind_med:>+8.1%}  {note}{marker}")

print()
print(f"  Equal-weight CAGR  : {eq_cagr:>+.1%}  (benchmark)")
print(f"  Optimized CAGR     : {port_cagr:>+.1%}")
print(f"  Median 252d return : {port_med:>+.1%}")
print(f"  Win rate           : {port_win:>5.0%}")
print(f"  P10 / P90          : {port_p10:>+.1%}  /  {port_p90:>+.1%}")
print()
print(f"  Max weight cap : {MAX_W:.0%} per asset")
print(f"  Zero-weighted assets are excluded from the table above.")
print()
print("  NOTE: CAGR figures are conditioned on RY=HIGH + BAA10Y=TIGHT regime.")
print("  They reflect what happened in matched historical episodes, not unconditional.")
