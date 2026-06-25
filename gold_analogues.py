"""
Gold historical analogue analysis.

Finds dates in history where gold's environment most closely resembled today
across 10 features, then shows what happened to gold over the next 3/6/12 months.
"""

import sys
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "src"))
from asset_universe import config
from asset_universe.store import reader

DATA_DIR = config.raw_data_dir()

# ── load ──────────────────────────────────────────────────────────────────────

def load_ohlcv(category, ticker):
    path = reader.ticker_path(DATA_DIR, category, ticker)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index().dropna()

def load_fred(series_id):
    path = reader.ticker_path(DATA_DIR, "macro", series_id)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["value"].sort_index()

gold   = load_ohlcv("commodities", "GC=F")
silver = load_ohlcv("commodities", "SI=F")
ry     = load_fred("DFII10").reindex(gold.index).ffill()    # 10yr real yield
usd    = load_fred("DTWEXBGS").reindex(gold.index).ffill()  # USD trade-weighted

gsr = (gold / silver).rename("gsr")

# ── build feature matrix ──────────────────────────────────────────────────────

f = pd.DataFrame(index=gold.index)

f["gold_ret_3m"]     = gold.pct_change(63)
f["gold_ret_6m"]     = gold.pct_change(126)
f["gold_ret_12m"]    = gold.pct_change(252)
f["gold_vol_21d"]    = gold.pct_change().rolling(21).std() * np.sqrt(252)
f["gold_vs_200ma"]   = gold / gold.rolling(200).mean() - 1
f["gsr_level"]       = gsr
f["gsr_12m_chg"]     = gsr.pct_change(252)
f["real_yield"]      = ry
f["real_yield_chg"]  = ry.diff(252)        # 1yr change in real yield
f["usd_12m_chg"]     = usd.pct_change(252)

# Require all features + DFII10 availability → start 2005
f = f["2005-01-01":].dropna()

# ── current state ─────────────────────────────────────────────────────────────

TODAY       = f.index[-1]
current_raw = f.loc[TODAY]

print("=" * 65)
print("GOLD HISTORICAL ANALOGUE ANALYSIS")
print(f"Reference date: {TODAY.date()}")
print("=" * 65)

print("\nCurrent environment:")
print(f"  Gold price          : ${gold[TODAY]:,.0f}/oz")
print(f"  3-month return      : {current_raw['gold_ret_3m']:+.1%}")
print(f"  6-month return      : {current_raw['gold_ret_6m']:+.1%}")
print(f"  12-month return     : {current_raw['gold_ret_12m']:+.1%}")
print(f"  21-day ann. vol     : {current_raw['gold_vol_21d']:.1%}")
print(f"  vs 200-day MA       : {current_raw['gold_vs_200ma']:+.1%}")
print(f"  Gold/Silver ratio   : {current_raw['gsr_level']:.1f}")
print(f"  GSR 12m change      : {current_raw['gsr_12m_chg']:+.1%}")
print(f"  10yr real yield     : {current_raw['real_yield']:+.2f}%")
print(f"  Real yield 1yr chg  : {current_raw['real_yield_chg']:+.2f}pp")
print(f"  USD 12m change      : {current_raw['usd_12m_chg']:+.1%}")

# ── normalize + match ─────────────────────────────────────────────────────────

mu  = f.mean()
sig = f.std()
normed   = (f - mu) / sig
curr_n   = (current_raw - mu) / sig

# Exclude last 252 days — insufficient forward data for 12m lookforward
candidates = normed.iloc[:-252]
dist = ((candidates - curr_n) ** 2).sum(axis=1).pow(0.5)
dist = dist.sort_values()

# Pick top analogues with minimum 252-day spacing between selections
analogues = []
for date, d in dist.items():
    if any(abs((date - a).days) < 252 for a in analogues):
        continue
    analogues.append(date)
    if len(analogues) >= 12:
        break

# ── compute forward returns ───────────────────────────────────────────────────

def fwd_return(anchor, n_days):
    future = gold.index[gold.index > anchor]
    if len(future) >= n_days:
        return gold.iloc[gold.index.get_loc(future[n_days - 1])] / gold[anchor] - 1
    return np.nan

rows = []
for date in analogues:
    row = f.loc[date].to_dict()
    row["date"]       = date
    row["distance"]   = round(dist[date], 3)
    row["gold_price"] = round(gold[date], 0)
    row["fwd_3m"]     = fwd_return(date, 63)
    row["fwd_6m"]     = fwd_return(date, 126)
    row["fwd_12m"]    = fwd_return(date, 252)
    rows.append(row)

results = pd.DataFrame(rows).set_index("date")

# ── print analogue table ──────────────────────────────────────────────────────

print(f"\n{'='*65}")
print("TOP ANALOGUES  (sorted by similarity to today)")
print(f"{'='*65}")
print(f"{'Date':<12} {'Gold $':>8} {'12m ret':>8} {'Vs200MA':>8} "
      f"{'GSR':>6} {'RealYld':>8} {'Dist':>6} {'→3m':>7} {'→6m':>7} {'→12m':>7}")
print("-" * 86)

for date, row in results.iterrows():
    fwd3  = f"{row['fwd_3m']:+.1%}"  if pd.notna(row['fwd_3m'])  else "  n/a"
    fwd6  = f"{row['fwd_6m']:+.1%}"  if pd.notna(row['fwd_6m'])  else "  n/a"
    fwd12 = f"{row['fwd_12m']:+.1%}" if pd.notna(row['fwd_12m']) else "  n/a"
    print(f"{str(date.date()):<12} "
          f"{row['gold_price']:>8,.0f} "
          f"{row['gold_ret_12m']:>8.1%} "
          f"{row['gold_vs_200ma']:>8.1%} "
          f"{row['gsr_level']:>6.1f} "
          f"{row['real_yield']:>8.2f}% "
          f"{row['distance']:>6.3f} "
          f"{fwd3:>7} "
          f"{fwd6:>7} "
          f"{fwd12:>7}")

# ── forward return distribution ───────────────────────────────────────────────

valid_3m  = results["fwd_3m"].dropna()
valid_6m  = results["fwd_6m"].dropna()
valid_12m = results["fwd_12m"].dropna()

def dist_row(label, s):
    if s.empty:
        return f"  {label}: no data"
    pos = (s > 0).sum()
    return (f"  {label}:  "
            f"median {s.median():+.1%}  |  "
            f"p25 {s.quantile(0.25):+.1%}  p75 {s.quantile(0.75):+.1%}  |  "
            f"worst {s.min():+.1%}  best {s.max():+.1%}  |  "
            f"{pos}/{len(s)} positive")

print(f"\n{'='*65}")
print("FORWARD RETURN DISTRIBUTION  (from analogue dates)")
print(f"{'='*65}")
print(dist_row("3-month  (63d) ", valid_3m))
print(dist_row("6-month (126d) ", valid_6m))
print(dist_row("12-month(252d) ", valid_12m))

# ── regime description ────────────────────────────────────────────────────────

print(f"\n{'='*65}")
print("REGIME CONTEXT  (what these analogues had in common)")
print(f"{'='*65}")
for col, label in [
    ("gold_ret_12m",  "Gold 12m return at entry"),
    ("gold_vs_200ma", "Gold vs 200MA at entry"),
    ("real_yield",    "Real yield at entry (%)"),
    ("gsr_level",     "GSR at entry"),
]:
    s = results[col]
    print(f"  {label:<32}  "
          f"median {s.median():.2f}  "
          f"range [{s.min():.2f}, {s.max():.2f}]  "
          f"(today: {current_raw[col]:.2f})")

print(f"\n  Note: {len(analogues)} analogues found. "
      f"Minimum 252-day spacing enforced between selections.")
print(f"  Analogue universe: 2005-01-01 to "
      f"{candidates.index[-1].date()} (252d buffer before today).")
