"""
Walk-forward backtest.

At each regime transition, re-fits the optimizer using only data available
at that point in time. Holds the resulting portfolio until the next
transition. Removes lookahead bias from asset selection.

Progress: two lines per transition (fitting start + result + ETA).
Results: walk-forward CAGR / Sharpe / MaxDD vs SPY.

Usage:
    python run_walkforward.py
"""
from __future__ import annotations

import io
import sys
import time
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
CATEGORIES  = ["equities", "commodities", "intl_etfs"]

# Optimizer settings — must match run_optimizer_all_regimes.py
MAX_W            = 0.35
MIN_N_OBS        = 20
MIN_HISTORY_YR   = 10
MAX_SINGLE_DAY_UP = 0.50
SHRINK_LAMBDA    = 100
N_RESTARTS       = 50
FWD_DAYS         = 252
EXCLUDE_TICKERS  = {"CF"}
GOLD_PROXY       = "GC_F"
MIN_GOLD_W       = 0.05

# Backtest settings
START_DATE      = "2004-01-01"
TC_BPS          = 10
MIN_REGIME_DAYS = 5   # confirmation window before switching


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
    if max_frac > 0.95: return max_frac, "SINGLE"
    if max_frac > 0.80: return max_frac, "THIN"
    if max_frac > 0.50: return max_frac, "MODERATE"
    return max_frac, "ROBUST"


def compute_metrics(returns: pd.Series, label: str) -> dict:
    r = returns.dropna()
    if r.empty:
        return {"label": label, "cagr": np.nan, "sharpe": np.nan, "maxdd": np.nan, "total": np.nan}
    total   = (1 + r).prod() - 1
    n_years = len(r) / 252
    cagr    = (1 + total) ** (1 / n_years) - 1 if n_years > 0 else np.nan
    sharpe  = (r.mean() / r.std()) * np.sqrt(252) if r.std() > 0 else np.nan
    cum     = (1 + r).cumprod()
    maxdd   = float(((cum - cum.cummax()) / cum.cummax()).min())
    return {"label": label, "cagr": cagr, "sharpe": sharpe, "maxdd": maxdd, "total": total}


def neg_geomean(w, mus, sigs):
    return -(np.dot(w, mus) - 0.5 * np.dot(w ** 2, sigs ** 2))


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
        if hist_yr < MIN_HISTORY_YR:
            continue
        if prices.pct_change().max() > MAX_SINGLE_DAY_UP:
            continue
        all_assets.append({"ticker": stem, "cat": cat, "prices": prices, "hist_yr": hist_yr})

print(f"  {len(all_assets)} assets passed quality filters")

# Load SPY
spy_prices = load_prices("equities", "SPY")
spy_ret    = spy_prices.pct_change() if not spy_prices.empty else pd.Series(dtype=float)

# ── Build regime labels ───────────────────────────────────────────────────────
print("Building regime labels ...", flush=True)
labeled_df, _ = regime_module.build(DATA_DIR)

# Build full return matrix for portfolio tracking
all_ret = pd.DataFrame({
    a["ticker"]: a["prices"].pct_change()
    for a in all_assets
}).loc[START_DATE:].dropna(how="all")

# ── Detect transitions (same logic as run_backtest.py) ───────────────────────
print("Detecting regime transitions ...", flush=True)
transitions: list[dict] = []
current_regime = None
pending_regime = None
pending_days   = 0

for date in all_ret.index:
    if date not in labeled_df.index:
        continue
    row = labeled_df.loc[date]
    ry  = str(row.get("ry_regime", ""))
    baa = str(row.get("baa10y_regime", ""))
    if not ry or not baa or ry == "nan" or baa == "nan":
        continue
    key = f"{ry}_{baa}"
    if key != current_regime:
        if key == pending_regime:
            pending_days += 1
        else:
            pending_regime = key
            pending_days   = 1
        if pending_days >= MIN_REGIME_DAYS:
            transitions.append({"date": date, "ry": ry, "baa": baa, "key": key})
            current_regime = key
            pending_regime = None
            pending_days   = 0
    else:
        pending_regime = None
        pending_days   = 0

print(f"  {len(transitions)} transitions detected")

# ── Core: optimize at a given cutoff date ────────────────────────────────────

def optimize_at_cutoff(ry: str, baa: str, cutoff: pd.Timestamp) -> pd.Series | None:
    """
    Re-fit optimizer for (ry, baa) using only regime dates before cutoff.
    Returns ticker -> weight Series, or None if insufficient data.
    """
    conditions = {"ry_regime": ry, "baa10y_regime": baa}
    mask = pd.Series(True, index=labeled_df.index)
    for k, v in conditions.items():
        mask &= labeled_df[k] == v
    all_matched = labeled_df.index[mask]
    # Only use dates strictly before the cutoff
    matched = all_matched[all_matched < cutoff]

    if len(matched) < MIN_N_OBS:
        return None  # fallback to equal-weight handled by caller

    regime_ends = _regime_end_dates(labeled_df, conditions, matched)

    candidates: list[dict] = []
    for a in all_assets:
        prices = a["prices"]
        ret_pairs = [
            (dt, r) for dt in matched
            if (r := fwd_return(prices, dt, FWD_DAYS, regime_ends.get(dt))) is not None
        ]
        if len(ret_pairs) < MIN_N_OBS:
            continue
        valid_dates = [dt for dt, _ in ret_pairs]
        rets        = [r  for _, r in ret_pairs]
        conc, div_label = temporal_concentration(valid_dates)
        lambda_mult = {"SINGLE": 4.0, "THIN": 2.0, "MODERATE": 1.0, "ROBUST": 1.0}[div_label]
        s = pd.Series(rets)
        candidates.append({
            "ticker":      a["ticker"],
            "mu":          float(s.mean()),
            "sigma":       float(s.std()),
            "n":           len(rets),
            "lambda_mult": lambda_mult,
        })

    if len(candidates) < 4:
        return None

    prior_mu = float(np.mean([c["mu"] for c in candidates]))
    for c in candidates:
        eff_lambda    = SHRINK_LAMBDA * c["lambda_mult"]
        shrink        = c["n"] / (c["n"] + eff_lambda)
        c["mu_final"] = shrink * c["mu"] + (1 - shrink) * prior_mu

    n    = len(candidates)
    mus  = np.array([c["mu_final"] for c in candidates])
    sigs = np.array([c["sigma"]    for c in candidates])

    gold_idx = next((i for i, c in enumerate(candidates) if c["ticker"] == GOLD_PROXY), None)
    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]
    if gold_idx is not None:
        constraints.append({"type": "ineq", "fun": lambda w, gi=gold_idx: w[gi] - MIN_GOLD_W})

    bounds = [(0.0, MAX_W)] * n
    rng    = np.random.default_rng(42)
    best   = None

    for _ in range(N_RESTARTS):
        w0  = rng.dirichlet(np.ones(n))
        res = minimize(
            neg_geomean, w0, args=(mus, sigs),
            method="SLSQP", bounds=bounds, constraints=constraints,
            options={"maxiter": 2000, "ftol": 1e-12},
        )
        if res.success and (best is None or res.fun < best.fun):
            best = res

    if best is None:
        return None

    w_opt  = np.clip(best.x, 0.0, None)
    w_opt /= w_opt.sum()

    return pd.Series(
        {c["ticker"]: w_opt[i] for i, c in enumerate(candidates) if w_opt[i] >= 0.005}
    )


# ── Walk-forward loop ─────────────────────────────────────────────────────────
print(f"\nWalk-forward: {len(transitions)} transitions  (~{len(transitions)*5//60}h estimate)\n", flush=True)
print(f"  {'#':>4}  {'Date':<12}  {'Regime':<14}  {'HistDates':>9}  "
      f"{'Positions':>9}  {'g(w)':>7}  {'Elapsed':>8}  {'ETA':>8}")
print("  " + "-" * 80)

wf_returns  : list[float] = []
ew_returns  : list[float] = []
spy_returns : list[float] = []
dates_out   : list        = []
period_log  : list[dict]  = []

t_start     = time.time()
elapsed_per : list[float] = []

for i, tr in enumerate(transitions):
    t0         = time.time()
    tr_date    = tr["date"]
    ry, baa    = tr["ry"], tr["baa"]
    next_date  = transitions[i + 1]["date"] if i + 1 < len(transitions) else all_ret.index[-1]

    # Count historical dates for this regime before cutoff
    conditions = {"ry_regime": ry, "baa10y_regime": baa}
    mask = pd.Series(True, index=labeled_df.index)
    for k, v in conditions.items():
        mask &= labeled_df[k] == v
    hist_count = int((labeled_df.index[mask] < tr_date).sum())

    # Fit optimizer
    weights = optimize_at_cutoff(ry, baa, tr_date)
    fallback = weights is None

    if fallback:
        # Equal-weight of all available assets for this day
        avail   = [a["ticker"] for a in all_assets if a["ticker"] in all_ret.columns]
        weights = pd.Series(1.0 / len(avail), index=avail) if avail else pd.Series(dtype=float)

    # Track daily returns in holding period [tr_date, next_date)
    period_idx = all_ret.index[(all_ret.index >= tr_date) & (all_ret.index < next_date)]
    g_w = np.nan

    for date in period_idx:
        day_rets = all_ret.loc[date]
        avail_w  = weights.index.intersection(day_rets.index)
        w_norm   = weights[avail_w]
        if w_norm.sum() > 0:
            w_norm = w_norm / w_norm.sum()
        port_ret = float((day_rets[avail_w] * w_norm).sum())

        # Apply TC on first day of period
        if date == period_idx[0] and len(period_log) > 0:
            prev_w = pd.Series(period_log[-1]["weights"])
            combined = weights.align(prev_w, fill_value=0.0)
            turnover = float((combined[0] - combined[1]).abs().sum()) / 2
            port_ret -= turnover * (TC_BPS / 10000)

        ew_ret  = float(day_rets[avail_w].mean()) if len(avail_w) > 0 else 0.0
        spy_ret_val = float(spy_ret.get(date, np.nan))

        wf_returns.append(port_ret)
        ew_returns.append(ew_ret)
        spy_returns.append(spy_ret_val)
        dates_out.append(date)

    # g(w) estimate for display
    if not fallback and len(period_idx) > 0:
        n_pos = int((weights >= 0.005).sum())
    else:
        n_pos = len(weights)

    # Compute realized period CAGR for log
    if len(period_idx) > 0:
        period_r = pd.Series(wf_returns[-len(period_idx):])
        realized = float((1 + period_r).prod() - 1)
    else:
        realized = np.nan

    elapsed_per.append(time.time() - t0)
    avg_sec = np.mean(elapsed_per)
    remaining = avg_sec * (len(transitions) - i - 1)
    eta_str  = f"{int(remaining//3600)}h{int((remaining%3600)//60):02d}m" if remaining > 60 else f"{int(remaining)}s"
    el_str   = f"{int((time.time()-t_start)//60)}m{int((time.time()-t_start)%60):02d}s"
    fb_tag   = "[EW]" if fallback else ""

    print(f"  {i+1:>4}  {tr_date.date()!s:<12}  {ry}+{baa:<8}  "
          f"{hist_count:>9}  {n_pos:>6}{fb_tag:>3}  "
          f"{realized:>+7.1%}  {el_str:>8}  {eta_str:>8}", flush=True)

    period_log.append({
        "transition": i + 1,
        "date":       tr_date,
        "ry":         ry,
        "baa":        baa,
        "hist_dates": hist_count,
        "n_pos":      n_pos,
        "fallback":   fallback,
        "realized":   realized,
        "weights":    weights.to_dict(),
    })

# ── Build result series ───────────────────────────────────────────────────────
idx      = pd.DatetimeIndex(dates_out)
r_wf     = pd.Series(wf_returns, index=idx, name="walkforward")
r_ew     = pd.Series(ew_returns,  index=idx, name="ew_regime")
r_spy    = pd.Series(spy_returns, index=idx, name="spy").dropna()

# ── Output ────────────────────────────────────────────────────────────────────
W = 72
print()
print("=" * W)
print("WALK-FORWARD RESULTS  (no lookahead bias)")
print(f"  Period  : {idx[0].date()} — {idx[-1].date()}  ({len(idx)/252:.1f} years)")
print(f"  TC      : {TC_BPS}bps per rotation")
print(f"  Switches: {len(transitions)}")
print("=" * W)

metrics = [
    compute_metrics(r_wf,  "Walk-forward optimizer"),
    compute_metrics(r_ew,  "EW (regime assets)"),
    compute_metrics(r_spy, "SPY"),
]

print(f"\n  {'Strategy':<24}  {'CAGR':>7}  {'Sharpe':>7}  {'MaxDD':>7}  {'Total':>8}")
print("  " + "-" * 57)
for m in metrics:
    cagr   = f"{m['cagr']:>+7.1%}"   if not np.isnan(m['cagr'])   else "    n/a"
    sharpe = f"{m['sharpe']:>7.2f}"  if not np.isnan(m['sharpe']) else "    n/a"
    maxdd  = f"{m['maxdd']:>+7.1%}"  if not np.isnan(m['maxdd'])  else "    n/a"
    total  = f"{m['total']:>+8.1%}"  if not np.isnan(m['total'])  else "     n/a"
    print(f"  {m['label']:<24}  {cagr}  {sharpe}  {maxdd}  {total}")

# Per-regime realized returns
print(f"\n  Per-regime realized (walk-forward):")
print(f"  {'Regime':<14}  {'Periods':>7}  {'WF CAGR':>9}  {'EW CAGR':>9}  {'Edge':>7}  {'Fallbacks':>9}")
print("  " + "-" * 60)

regime_series = labeled_df[["ry_regime", "baa10y_regime"]].dropna()
for ry in ["HIGH", "MID", "LOW"]:
    for baa in ["TIGHT", "MID", "WIDE"]:
        reg_periods = [p for p in period_log if p["ry"] == ry and p["baa"] == baa]
        if not reg_periods:
            continue
        reg_dates = regime_series.index[
            (regime_series["ry_regime"] == ry) &
            (regime_series["baa10y_regime"] == baa)
        ].intersection(idx)
        if len(reg_dates) < 20:
            continue
        m_wf  = compute_metrics(r_wf[reg_dates], "wf")
        m_ew  = compute_metrics(r_ew[reg_dates], "ew")
        edge  = (m_wf["cagr"] - m_ew["cagr"]) if not (np.isnan(m_wf["cagr"]) or np.isnan(m_ew["cagr"])) else np.nan
        n_fb  = sum(1 for p in reg_periods if p["fallback"])
        edge_s = f"{edge:>+7.1%}" if not np.isnan(edge) else "    n/a"
        print(f"  {ry}+{baa:<10}  {len(reg_periods):>7}  "
              f"{m_wf['cagr']:>+9.1%}  {m_ew['cagr']:>+9.1%}  {edge_s}  {n_fb:>9}")

# ── Save results ──────────────────────────────────────────────────────────────
curves = pd.DataFrame({
    "walkforward": (1 + r_wf).cumprod(),
    "ew_regime":   (1 + r_ew).cumprod(),
    "spy":         (1 + r_spy).reindex(idx).cumprod(),
})
curves.to_csv(RESULTS_DIR / "walkforward_equity_curves.csv")

log_df = pd.DataFrame([
    {k: v for k, v in p.items() if k != "weights"}
    for p in period_log
])
log_df.to_csv(RESULTS_DIR / "walkforward_period_log.csv", index=False)

print(f"\n  Equity curves  : {RESULTS_DIR}/walkforward_equity_curves.csv")
print(f"  Period log     : {RESULTS_DIR}/walkforward_period_log.csv")
print(f"  Total elapsed  : {int((time.time()-t_start)//60)}m{int((time.time()-t_start)%60):02d}s")
print("=" * W)
