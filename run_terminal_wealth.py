"""
Terminal Wealth Optimizer

Objective : maximize median terminal wealth at year 12 subject to drawdown tolerance.
            This is the correct objective for FI@50 vs Sharpe ratio maximization.

Method    : Monte Carlo (vectorized, 10k paths for eval) + SLSQP optimizer.
            Two path sets: fast (1500) for optimization, accurate (10k) for final eval.

Usage     : python run_terminal_wealth.py
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
from asset_universe.store import reader

# ── Parameters ────────────────────────────────────────────────────────────────
DCA_MONTHLY   = 25_000
YEARS         = 12
N_SIM_OPT     = 1_500    # paths used during optimization (speed)
N_SIM_EVAL    = 10_000   # paths used for final evaluation (accuracy)
N_RESTARTS    = 10
HISTORY_START = "2018-08-02"   # VRT earliest available date
SPILTAN_ANN   = 0.035

TICKERS = ["GC_F", "SI_F", "LLY", "WMT", "CCJ", "VRT", "AVGO"]
NAMES   = {
    "GC_F": "Gold",   "SI_F": "Silver",    "LLY": "Eli Lilly",
    "WMT":  "Walmart","CCJ":  "Cameco",     "VRT": "Vertiv",  "AVGO": "Broadcom",
}
CAT = {
    "GC_F": ("commodities","GC_F"), "SI_F": ("commodities","SI_F"),
    "LLY":  ("equities","LLY"),     "WMT":  ("equities","WMT"),
    "CCJ":  ("equities","CCJ"),     "VRT":  ("equities","VRT"),
    "AVGO": ("equities","AVGO"),
}

# V3 target weights within equity sleeve (sum to 1.0)
V3_W  = np.array([0.250, 0.100, 0.210, 0.150, 0.100, 0.100, 0.090])
V3_SP = 0.15

# ── Load data & compute parameters ───────────────────────────────────────────
DATA_DIR = config.raw_data_dir()
prices = {}
for tkr, (cat, fname) in CAT.items():
    df = pd.read_parquet(reader.ticker_path(DATA_DIR, cat, fname))
    df["date"] = pd.to_datetime(df["date"])
    prices[tkr] = df.set_index("date")["close"].sort_index().dropna()

price_df = pd.DataFrame(prices).dropna()
price_df = price_df[price_df.index >= HISTORY_START]
log_ret  = np.log(price_df / price_df.shift(1)).dropna()

MU   = log_ret.mean().values * 252          # annual mean log-return
COV  = log_ret.cov().values  * 252          # annual covariance
VOL  = np.sqrt(np.diag(COV))               # annual vol
CAGR = np.exp(MU) - 1                      # geometric mean return (no vol drag)
DRAG = VOL**2 / 2                          # variance drag on geometric mean

# ── TPV ───────────────────────────────────────────────────────────────────────
# TPV = sum of config/portfolio.toml positions (2026-07-24 -- the sheet's
# separate dedicated TPV cell was found to lag the real broker balance more
# than the position sum does, once idle cash and War Chest were correctly
# tracked; the cell is no longer used anywhere in this codebase).
from asset_universe.portfolio import snapshot
TPV0: float = snapshot(DATA_DIR)["value_sek"].sum()

# ── Pre-generate Monte Carlo path matrices ────────────────────────────────────
MONTHS  = YEARS * 12
N       = len(TICKERS)
mu_m    = MU / 12
cov_m   = COV / 12
L       = np.linalg.cholesky(cov_m + 1e-9 * np.eye(N))

def _make_factors(n_sim: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    z   = rng.standard_normal((n_sim, MONTHS, N))
    return np.exp((z @ L.T) + mu_m)          # (n_sim, months, N) multiplicative factors

print("Pre-generating Monte Carlo paths ...", flush=True)
F_OPT  = _make_factors(N_SIM_OPT,  seed=42)
F_EVAL = _make_factors(N_SIM_EVAL, seed=99)

# Spiltan compound factors (same every path)
r_m  = SPILTAN_ANN / 12
_t   = np.arange(1, MONTHS + 1, dtype=float)
SP_COMPOUND = (1 + r_m) ** _t               # (months,) growth of 1 kr invested at t=0
SP_ANNUITY  = (1 + r_m) * ((SP_COMPOUND - 1) / r_m)  # (months,) FV of 1 kr/month DCA

# ── Core simulation (fully vectorised — no Python month loop) ─────────────────
def _simulate(equity_w: np.ndarray, sp_w: float,
              factors: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns (terminal_wealth, max_drawdown) each shape (n_sim,).
    Handles monthly DCA split equity/spiltan proportionally to sp_w.
    """
    n_sim   = factors.shape[0]
    V0_eq   = TPV0 * (1.0 - sp_w)
    V0_sp   = TPV0 * sp_w
    dca_eq  = DCA_MONTHLY * (1.0 - sp_w)
    dca_sp  = DCA_MONTHLY * sp_w

    # Portfolio factor per path per month: (n_sim, months)
    pf = (factors * equity_w[np.newaxis, np.newaxis, :]).sum(axis=2)

    # Cumulative product of portfolio factors: C_t = F_1*...*F_t  (n_sim, months)
    cum = np.cumprod(pf, axis=1)

    # Equity DCA formula:
    #   equity_t = C_t * (V0_eq + dca_eq * sum_{s=0}^{t-1} 1/C_s),  C_0 = 1
    inv_cum        = np.empty((n_sim, MONTHS), dtype=np.float64)
    inv_cum[:, 0]  = 1.0
    inv_cum[:, 1:] = 1.0 / cum[:, :-1]
    equity_path    = cum * (V0_eq + dca_eq * np.cumsum(inv_cum, axis=1))  # (n_sim, months)

    # Spiltan path (deterministic, same across paths): (months,)
    spiltan_path = V0_sp * SP_COMPOUND + dca_sp * SP_ANNUITY   # (months,)

    # Total wealth path: (n_sim, months)
    total = equity_path + spiltan_path[np.newaxis, :]

    # Running max drawdown (include initial TPV0 as first peak)
    init_col   = np.full((n_sim, 1), TPV0)
    total_ext  = np.concatenate([init_col, total], axis=1)          # (n_sim, months+1)
    run_max    = np.maximum.accumulate(total_ext, axis=1)[:, 1:]    # (n_sim, months)
    max_dd     = (total / run_max - 1.0).min(axis=1)                # (n_sim,) negative values

    return total[:, -1], max_dd


def sim_opt(w: np.ndarray, sp: float)  -> tuple[np.ndarray, np.ndarray]:
    return _simulate(w, sp, F_OPT)

def sim_eval(w: np.ndarray, sp: float) -> tuple[np.ndarray, np.ndarray]:
    return _simulate(w, sp, F_EVAL)


# ── Optimizer ─────────────────────────────────────────────────────────────────
def optimize(sp_w: float, dd_max: float) -> dict | None:
    """
    Maximize median terminal wealth subject to P75(max_drawdown) >= -dd_max.
    dd_max  : positive, e.g. 0.50 = tolerate up to 50% drawdown
    penalty : quadratic; violation = max(0, -dd_max - p75_dd)
    """
    LAM = 5e7

    def obj(w_raw: np.ndarray) -> float:
        w = np.clip(w_raw, 0.0, None)
        s = w.sum()
        if s < 1e-9:
            return 1e12
        w = w / s
        tw, mdd      = sim_opt(w, sp_w)
        p75_dd       = float(np.percentile(mdd, 75))
        violation    = max(0.0, -dd_max - p75_dd)          # >0 when DD too severe
        return -float(np.median(tw)) + LAM * violation ** 2

    bounds = [(0.0, 0.55)] * N
    cons   = [{"type": "eq", "fun": lambda w: np.clip(w, 0, None).sum() - 1.0}]
    best   = None

    for _ in range(N_RESTARTS):
        w0  = np.random.dirichlet(np.ones(N))
        res = minimize(obj, w0, method="SLSQP", bounds=bounds, constraints=cons,
                       options={"maxiter": 500, "ftol": 1e-9})
        if best is None or res.fun < best.fun:
            best = res

    if best is None:
        return None

    w = np.clip(best.x, 0.0, None); w /= w.sum()
    tw, mdd = sim_eval(w, sp_w)
    return {
        "w":         w,
        "sp_w":      sp_w,
        "dd_max":    dd_max,
        "median_tw": float(np.median(tw)),
        "p10_tw":    float(np.percentile(tw, 10)),
        "p90_tw":    float(np.percentile(tw, 90)),
        "p75_dd":    float(np.percentile(mdd, 75)),
        "mean_dd":   float(np.mean(mdd)),
    }


# ── Baseline eval ─────────────────────────────────────────────────────────────
v3_tw, v3_mdd = sim_eval(V3_W, V3_SP)
V3 = {
    "w": V3_W, "sp_w": V3_SP,
    "median_tw": float(np.median(v3_tw)),
    "p10_tw":    float(np.percentile(v3_tw, 10)),
    "p90_tw":    float(np.percentile(v3_tw, 90)),
    "p75_dd":    float(np.percentile(v3_mdd, 75)),
    "mean_dd":   float(np.mean(v3_mdd)),
}


# ── Reporting helpers ─────────────────────────────────────────────────────────
def _wrow(w: np.ndarray) -> str:
    return "  ".join(f"{x:>5.1%}" for x in w)

def _tw(r: dict) -> str:
    med = r["median_tw"] / 1e6
    p10 = r["p10_tw"]    / 1e6
    p90 = r["p90_tw"]    / 1e6
    return f"{med:>6.2f}M  P10={p10:>5.2f}M  P90={p90:>5.2f}M"


# ── Main output ───────────────────────────────────────────────────────────────
data_start = log_ret.index[0].date()
data_end   = log_ret.index[-1].date()
n_yrs_data = len(log_ret) / 252

print()
print("=" * 72)
print("TERMINAL WEALTH OPTIMIZER")
print("=" * 72)
print(f"  Starting TPV : {TPV0:>10,.0f} kr")
print(f"  DCA          : {DCA_MONTHLY:>10,} kr / month")
print(f"  Horizon      : {YEARS} years  ({YEARS*12} months)")
print(f"  Paths (opt)  : {N_SIM_OPT:,}    Paths (eval): {N_SIM_EVAL:,}")
print(f"  Data window  : {data_start} to {data_end}  ({n_yrs_data:.1f} yr)")
print()

# Asset parameters
print("Asset parameters  (historical from data window)")
print("-" * 62)
print(f"  {'Tkr':>5}  {'Name':>12}  {'CAGR':>7}  {'Vol':>7}  "
      f"{'VarDrag':>8}  {'History':>8}")
print("  " + "-" * 58)
for i, tkr in enumerate(TICKERS):
    n_yrs_tkr = len(prices[tkr][prices[tkr].index >= HISTORY_START].dropna()) / 252
    flag = "  *thin" if n_yrs_tkr < 8 else ""
    print(f"  {tkr:>5}  {NAMES[tkr]:>12}  {CAGR[i]:>+6.1%}  {VOL[i]:>6.1%}  "
          f"{-DRAG[i]:>+7.1%}  {n_yrs_tkr:>5.1f} yr{flag}")
print(f"  {'Spilt':>5}  {'Spiltan':>12}  {SPILTAN_ANN:>+6.1%}  {'fixed':>7}  {'n/a':>8}")
print()
print("  CAGR = geometric mean return (log-return mean annualised)")
print("  VarDrag = -vol^2/2, the vol tax on compounding (negative = hurts)")
print("  *thin: VRT/AVGO history < 8yr; CAGR influenced by AI-era bull run")
print()

# V3 baseline
print("V3 Baseline  (current construction)")
print("-" * 62)
print("  " + "  ".join(f"{NAMES[t][:5]:>5}" for t in TICKERS) + "  Spilt")
print("  " + _wrow(V3_W) + f"  {V3_SP:>5.1%}")
print(f"  Median TW : {_tw(V3)}")
print(f"  P75 max DD: {V3['p75_dd']:>+.1%}")
print()

# Run optimizations
SCENARIOS = [
    ("DD<=50%  Spiltan=15%", V3_SP, 0.50),
    ("DD<=50%  Spiltan=10%", 0.10,  0.50),
    ("DD<=50%  Spiltan= 5%", 0.05,  0.50),
    ("DD<=50%  Spiltan= 0%", 0.00,  0.50),
    ("DD<=40%  Spiltan= 0%", 0.00,  0.40),
    ("DD<=60%  Spiltan= 0%", 0.00,  0.60),
]

print(f"Running {len(SCENARIOS)} optimization scenarios  ({N_RESTARTS} restarts each) ...")
print()
results: dict[str, dict | None] = {}
for label, sp_w, dd_max in SCENARIOS:
    print(f"  {label} ...", end="", flush=True)
    r = optimize(sp_w, dd_max)
    results[label] = r
    if r:
        delta = (r["median_tw"] - V3["median_tw"]) / 1e6
        print(f"  median {r['median_tw']/1e6:.2f}M  ({delta:+.2f}M vs V3)")
    else:
        print("  FAILED")

# ── Results table ─────────────────────────────────────────────────────────────
print()
print("=" * 72)
print("RESULTS")
print("=" * 72)
short = [NAMES[t][:5] for t in TICKERS]
header_w = "  ".join(f"{s:>5}" for s in short)
print(f"  {'Scenario':<28}  {header_w}   Splt  |  {'Med TW':>7}  {'Delta':>7}  {'P75dd':>6}")
print("  " + "-" * 98)

def _row(label: str, r: dict) -> None:
    delta = (r["median_tw"] - V3["median_tw"]) / 1e6
    print(f"  {label:<28}  {_wrow(r['w'])}   {r['sp_w']:>4.0%}  |  "
          f"{r['median_tw']/1e6:>6.2f}M  {delta:>+6.2f}M  {r['p75_dd']:>+5.1%}")

_row("V3 baseline", V3)
print("  " + "-" * 98)
for label, r in results.items():
    if r:
        _row(label, r)
    else:
        print(f"  {label:<28}  {'FAILED':>7}")

print()
print("  Med TW = median terminal wealth across 10,000 paths at year 12")
print("  Delta  = vs V3 baseline  |  P75dd = 75th-pct worst per-path drawdown")
print()

# ── Per-weight delta vs V3 (best scenario) ────────────────────────────────────
best_label = max(
    ((k, v["median_tw"]) for k, v in results.items() if v),
    key=lambda x: x[1],
    default=(None, 0),
)[0]

if best_label:
    br = results[best_label]
    print(f"Weight delta vs V3  (best scenario: {best_label})")
    print("-" * 50)
    for i, tkr in enumerate(TICKERS):
        diff    = br["w"][i] - V3_W[i]
        v3_pct  = V3_W[i] * (1 - V3_SP)
        opt_pct = br["w"][i] * (1 - br["sp_w"])
        print(f"  {NAMES[tkr]:>12}:  V3 {V3_W[i]:>5.1%} (TPV {v3_pct:.1%})  "
              f"->  Opt {br['w'][i]:>5.1%} (TPV {opt_pct:.1%})   D {diff:>+5.1%}")
    sp_diff = br["sp_w"] - V3_SP
    print(f"  {'Spiltan':>12}:  V3 {V3_SP:>5.1%}            "
          f"->  Opt {br['sp_w']:>5.1%}              D {sp_diff:>+5.1%}")
    print()
    delta_kr = br["median_tw"] - V3["median_tw"]
    print(f"  Terminal wealth gain: +{delta_kr:,.0f} kr  (median, year 12)")
    print()

# ── Spiltan cost curve ────────────────────────────────────────────────────────
spiltan_rows = [(k, v) for k, v in results.items() if "DD<=50%" in k and v]
if len(spiltan_rows) >= 2:
    print("Spiltan drag  (DD<=50%, optimal equity weights at each Spiltan level)")
    print("-" * 50)
    for label, r in sorted(spiltan_rows, key=lambda x: x[1]["sp_w"], reverse=True):
        delta = (r["median_tw"] - V3["median_tw"]) / 1e6
        print(f"  Spiltan {r['sp_w']:>4.0%}  ->  med TW {r['median_tw']/1e6:.2f}M  ({delta:>+.2f}M vs V3)")
    print()

print("Note: optimizer uses full in-sample history (2018-2026).")
print("VRT/AVGO weights reflect an AI-era bull that may not persist.")
print("Use this as directional guidance, not a precise prescription.")
