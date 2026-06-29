"""
Regime-switching portfolio backtest.

Walks through full price history day by day. At each date, applies the
optimizer weights for the current regime (RY x BAA combination).
Compares to SPY buy-and-hold and equal-weight of the same universe.

Three questions answered:
  1. Does regime detection add value vs static equal-weight?
  2. Does the optimizer add value within each regime vs equal-weight?
  3. Does the full system beat SPY buy-and-hold?

Usage:
    python run_backtest.py

Requires:
    - optimizer_results/{RY}_{BAA}.csv  (from run_optimizer_all_regimes.py)
    - data/raw/equities/SPY.parquet     (benchmark)
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

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.store import reader

DATA_DIR    = config.raw_data_dir()
RESULTS_DIR = Path(__file__).parent / "optimizer_results"
CATEGORIES  = ["equities", "commodities", "intl_etfs"]
START_DATE       = "2004-01-01"
TC_BPS           = 10    # transaction cost per rotation: 0.10%
MIN_REGIME_DAYS  = 5     # new regime must hold this many days before switching portfolio


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_prices(cat: str, stem: str) -> pd.Series:
    path = reader.ticker_path(DATA_DIR, cat, stem)
    if not path.exists():
        return pd.Series(dtype=float)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index().dropna()


def load_regime_weights(ry: str, baa: str) -> pd.Series:
    """Load saved optimizer weights for a regime. Returns ticker -> weight Series."""
    path = RESULTS_DIR / f"{ry}_{baa}.csv"
    if not path.exists():
        return pd.Series(dtype=float)
    df = pd.read_csv(path)
    return df.set_index("ticker")["weight"]


def compute_metrics(returns: pd.Series, label: str) -> dict:
    """Compute CAGR, Sharpe, max drawdown from daily return series."""
    if returns.empty or returns.isna().all():
        return {"label": label, "cagr": np.nan, "sharpe": np.nan, "maxdd": np.nan, "total": np.nan}
    r = returns.dropna()
    total   = (1 + r).prod() - 1
    n_years = len(r) / 252
    cagr    = (1 + total) ** (1 / n_years) - 1 if n_years > 0 else np.nan
    sharpe  = (r.mean() / r.std()) * np.sqrt(252) if r.std() > 0 else np.nan
    cum     = (1 + r).cumprod()
    roll_max = cum.cummax()
    drawdown = (cum - roll_max) / roll_max
    maxdd   = float(drawdown.min())
    return {"label": label, "cagr": cagr, "sharpe": sharpe, "maxdd": maxdd, "total": total}


# ── Load all prices ───────────────────────────────────────────────────────────
print("Loading prices ...", flush=True)
price_map: dict[str, pd.Series] = {}
for cat in CATEGORIES:
    cat_dir = DATA_DIR / cat
    if not cat_dir.exists():
        continue
    for f in sorted(cat_dir.glob("*.parquet")):
        s = load_prices(cat, f.stem)
        if not s.empty:
            price_map[f.stem] = s

print(f"  {len(price_map)} assets loaded")

# Load SPY
spy = price_map.get("SPY")
if spy is None:
    print("WARNING: SPY not found — benchmark will be skipped")

# ── Build regime labels ───────────────────────────────────────────────────────
print("Building regime labels ...", flush=True)
labeled_df, _ = regime_module.build(DATA_DIR)

# ── Load all regime weights ───────────────────────────────────────────────────
print("Loading regime portfolios ...", flush=True)
ry_labels  = ["HIGH", "MID", "LOW"]
baa_labels = ["TIGHT", "MID", "WIDE"]
regime_portfolios: dict[str, pd.Series] = {}

for ry in ry_labels:
    for baa in baa_labels:
        key = f"{ry}_{baa}"
        w = load_regime_weights(ry, baa)
        if not w.empty:
            regime_portfolios[key] = w
            print(f"  {ry}+{baa}: {len(w)} positions  top: {w.idxmax()} ({w.max():.1%})")
        else:
            print(f"  {ry}+{baa}: no portfolio (skipped)")

if not regime_portfolios:
    print("ERROR: no regime portfolios found. Run run_optimizer_all_regimes.py first.")
    sys.exit(1)

# ── Build daily return matrix ─────────────────────────────────────────────────
print("\nBuilding return matrix ...", flush=True)
all_tickers = sorted({t for w in regime_portfolios.values() for t in w.index})
ret_df = pd.DataFrame({
    tkr: price_map[tkr].pct_change()
    for tkr in all_tickers if tkr in price_map
})
ret_df = ret_df.loc[START_DATE:].dropna(how="all")
print(f"  {len(ret_df)} trading days  x  {len(ret_df.columns)} assets")

# Build equal-weight universe return (all available assets each day)
ew_universe = pd.DataFrame({
    tkr: price_map[tkr].pct_change()
    for tkr in price_map
}).loc[START_DATE:].dropna(how="all")
ew_daily = ew_universe.mean(axis=1)  # equal-weight of all available assets

# ── Walk-forward simulation ───────────────────────────────────────────────────
print("Running backtest ...", flush=True)

opt_returns   = []   # regime-switching optimizer
ew_reg_returns = []  # equal-weight within current regime portfolio assets
spy_returns    = []  # SPY buy-and-hold
ew_all_returns = []  # equal-weight all universe assets

dates_out      = []
regime_log     = []

current_regime_key  = None
current_weights     = None
prev_weights        = None
pending_regime_key  = None   # regime seen but not yet confirmed
pending_days        = 0      # how many consecutive days the pending regime has held

for date in ret_df.index:
    # Get regime for this date
    if date not in labeled_df.index:
        continue
    row = labeled_df.loc[date]
    ry  = str(row.get("ry_regime",  ""))
    baa = str(row.get("baa10y_regime", ""))
    if not ry or not baa or ry == "nan" or baa == "nan":
        continue

    regime_key = f"{ry}_{baa}"

    # Confirmation window: new regime must hold MIN_REGIME_DAYS before switching
    tc = 0.0
    if regime_key != current_regime_key:
        if regime_key == pending_regime_key:
            pending_days += 1
        else:
            pending_regime_key = regime_key
            pending_days = 1

        if pending_days >= MIN_REGIME_DAYS:
            # Confirmed — switch portfolio
            if regime_key in regime_portfolios:
                new_weights = regime_portfolios[regime_key]
                if prev_weights is not None:
                    combined = new_weights.align(prev_weights, fill_value=0.0)
                    turnover = float((combined[0] - combined[1]).abs().sum()) / 2
                    tc = turnover * (TC_BPS / 10000)
                current_weights    = new_weights
                current_regime_key = regime_key
                prev_weights       = new_weights
                pending_regime_key = None
                pending_days       = 0
                regime_log.append({"date": date, "regime": f"{ry}+{baa}", "tc": tc})
            else:
                current_weights    = None
                current_regime_key = regime_key
                pending_regime_key = None
                pending_days       = 0
    else:
        pending_regime_key = None
        pending_days       = 0

    # Compute daily returns
    day_rets = ret_df.loc[date]

    # Optimizer portfolio return
    if current_weights is not None:
        avail   = current_weights.index.intersection(day_rets.index)
        w_avail = current_weights[avail]
        if w_avail.sum() > 0:
            w_avail = w_avail / w_avail.sum()
        port_ret = float((day_rets[avail] * w_avail).sum()) - tc
        tc = 0.0  # apply once on switch day only
    else:
        port_ret = float(ew_all_returns[-1]) if ew_all_returns else 0.0

    # Equal-weight of same assets (regime portfolio's tickers, equal-weighted)
    if current_weights is not None:
        avail_ew = current_weights.index.intersection(day_rets.index)
        ew_ret   = float(day_rets[avail_ew].mean()) if len(avail_ew) > 0 else 0.0
    else:
        ew_ret = float(ew_daily.get(date, 0.0))

    # SPY
    spy_ret = float(spy.pct_change().get(date, np.nan)) if spy is not None else np.nan

    # Equal-weight all
    ew_all = float(ew_daily.get(date, 0.0))

    opt_returns.append(port_ret)
    ew_reg_returns.append(ew_ret)
    spy_returns.append(spy_ret)
    ew_all_returns.append(ew_all)
    dates_out.append(date)

# ── Build result series ───────────────────────────────────────────────────────
idx = pd.DatetimeIndex(dates_out)
r_opt    = pd.Series(opt_returns,    index=idx, name="optimizer")
r_ew_reg = pd.Series(ew_reg_returns, index=idx, name="ew_regime")
r_spy    = pd.Series(spy_returns,    index=idx, name="spy").dropna()
r_ew_all = pd.Series(ew_all_returns, index=idx, name="ew_all")

# ── Per-regime breakdown ──────────────────────────────────────────────────────
regime_series = labeled_df[["ry_regime", "baa10y_regime"]].dropna()
regime_series = regime_series.loc[regime_series.index.intersection(idx)]

# ── Output ────────────────────────────────────────────────────────────────────
W = 72
print()
print("=" * W)
print("BACKTEST RESULTS")
print(f"  Period  : {idx[0].date()} — {idx[-1].date()}  ({len(idx)/252:.1f} years)")
print(f"  TC      : {TC_BPS}bps per rotation")
print(f"  Switches: {len(regime_log)}")
print("=" * W)

metrics = [
    compute_metrics(r_opt,    "Regime optimizer"),
    compute_metrics(r_ew_reg, "EW (regime assets)"),
    compute_metrics(r_ew_all, "EW (full universe)"),
    compute_metrics(r_spy,    "SPY"),
]

print(f"\n  {'Strategy':<22}  {'CAGR':>7}  {'Sharpe':>7}  {'MaxDD':>7}  {'Total':>8}")
print("  " + "-" * 55)
for m in metrics:
    cagr   = f"{m['cagr']:>+7.1%}"   if not np.isnan(m['cagr'])   else "    n/a"
    sharpe = f"{m['sharpe']:>7.2f}"  if not np.isnan(m['sharpe']) else "    n/a"
    maxdd  = f"{m['maxdd']:>+7.1%}"  if not np.isnan(m['maxdd'])  else "    n/a"
    total  = f"{m['total']:>+8.1%}"  if not np.isnan(m['total'])  else "     n/a"
    print(f"  {m['label']:<22}  {cagr}  {sharpe}  {maxdd}  {total}")

# ── Per-regime stats ──────────────────────────────────────────────────────────
print(f"\n  Per-regime breakdown (optimizer CAGR vs EW regime assets):")
print(f"  {'Regime':<14}  {'Days':>5}  {'Opt CAGR':>9}  {'EW CAGR':>9}  {'Edge':>7}")
print("  " + "-" * 50)

for ry in ry_labels:
    for baa in baa_labels:
        rkey = f"{ry}_{baa}"
        reg_mask = (
            (regime_series["ry_regime"]    == ry) &
            (regime_series["baa10y_regime"] == baa)
        )
        reg_dates = regime_series.index[reg_mask].intersection(idx)
        if len(reg_dates) < 20:
            continue
        m_opt = compute_metrics(r_opt[reg_dates],    "opt")
        m_ew  = compute_metrics(r_ew_reg[reg_dates], "ew")
        edge  = (m_opt["cagr"] - m_ew["cagr"]) if not (np.isnan(m_opt["cagr"]) or np.isnan(m_ew["cagr"])) else np.nan
        edge_s = f"{edge:>+7.1%}" if not np.isnan(edge) else "    n/a"
        print(f"  {ry}+{baa:<10}  {len(reg_dates):>5}  "
              f"{m_opt['cagr']:>+9.1%}  {m_ew['cagr']:>+9.1%}  {edge_s}")

# ── Regime transition log ─────────────────────────────────────────────────────
print(f"\n  Regime transitions ({len(regime_log)} total):")
for r in regime_log[:20]:
    print(f"    {r['date'].date()}  -> {r['regime']}  tc={r['tc']:.3%}")
if len(regime_log) > 20:
    print(f"    ... and {len(regime_log) - 20} more")

# ── Save equity curves ────────────────────────────────────────────────────────
curves = pd.DataFrame({
    "optimizer":  (1 + r_opt).cumprod(),
    "ew_regime":  (1 + r_ew_reg).cumprod(),
    "ew_all":     (1 + r_ew_all).cumprod(),
    "spy":        (1 + r_spy).reindex(idx).cumprod(),
})
curves.to_csv(RESULTS_DIR / "backtest_equity_curves.csv")
print(f"\n  Equity curves saved to: {RESULTS_DIR}/backtest_equity_curves.csv")
print("=" * W)
