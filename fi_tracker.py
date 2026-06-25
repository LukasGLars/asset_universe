"""
FI@50 portfolio dashboard.

Usage:
    python fi_tracker.py
"""

import sys
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
from asset_universe import config, portfolio

DATA_DIR = config.raw_data_dir()

# ── Portfolio snapshot ─────────────────────────────────────────────────────────

snap = portfolio.snapshot(DATA_DIR)
fi   = portfolio.fi_pace(DATA_DIR)
trig = portfolio.trigger_states(DATA_DIR)

tpv = fi["tpv_sek"]

print("=" * 62)
print("REACTOR CORE  —  PORTFOLIO SNAPSHOT")
print("=" * 62)
print(f"{'Position':<22} {'Shares':>7} {'Price':>10} {'Value SEK':>12} {'Wt':>6}")
print("-" * 62)

for _, row in snap.iterrows():
    shares_str = f"{int(row['shares'])}" if row["shares"] else "—"
    if pd.notna(row["price_sek"]):
        price_str = f"{row['price_sek']:,.0f} kr"
    else:
        price_str = "manual"
    value_str = f"{row['value_sek']:,.0f} kr" if pd.notna(row["value_sek"]) else "—"
    wt_str    = f"{row['weight']:.1%}"
    print(f"  {row['name']:<20} {shares_str:>7} {price_str:>10} {value_str:>12} {wt_str:>6}")

print("-" * 62)
print(f"  {'TPV':<20} {'':>7} {'':>10} {tpv:>12,.0f} kr")

# Bucket totals
for bucket, label in [("reactor_core","Reactor Core"), ("home_base","Home Base"), ("war_chest","War Chest")]:
    sub = snap[snap["bucket"] == bucket]["value_sek"].sum()
    pct = sub / tpv if tpv else 0
    print(f"    {label:<18} {sub:>12,.0f} kr  ({pct:.0%})")

# ── FI@50 pace ────────────────────────────────────────────────────────────────

print(f"\n{'='*62}")
print("FI@50 PACE TRACKER")
print(f"{'='*62}")

on_pace = fi["on_pace"]
pace_icon = "ON PACE" if on_pace else "BEHIND"

print(f"  Start  ({fi['start_date']})  :  {fi['start_value_sek']:>12,.0f} kr")
print(f"  Now                     :  {fi['tpv_sek']:>12,.0f} kr")
print(f"  Target (FI@50)          :  {fi['target_sek']:>12,.0f} kr")
print(f"  Years remaining         :  {fi['years_remaining']:.1f}")
print()
print(f"  AWAR (trailing)         :  {fi['awar']:>+.1%}")
print(f"  Required CAGR           :  {fi['required_cagr']:>+.1%}")
print(f"  Status                  :  {pace_icon}  ({fi['awar'] - fi['required_cagr']:+.1%} margin)")
print()
print(f"  Projected @ AWAR        :  {fi['projected_sek']:>12,.0f} kr")
surplus = fi["surplus_deficit"]
label = "surplus" if surplus >= 0 else "deficit"
print(f"  vs target               :  {surplus:>+12,.0f} kr  ({label})")

# Scenario table
print()
print(f"  {'Scenario':<14} {'CAGR':>6}  {'Projected':>14}  {'FI date':>10}")
print(f"  {'-'*50}")
for label, rate in [("Bear", 0.10), ("Conservative", 0.15), ("Base", 0.20),
                    ("Current AWAR", fi["awar"]), ("Bull", 0.30)]:
    proj = tpv * (1 + rate) ** fi["years_remaining"]
    # years to target at this rate
    if rate > 0:
        yrs_to_fi = (fi["target_sek"] / tpv) ** (1 / rate) - 1 if rate != 0 else float("inf")
        import math
        yrs_to_fi = math.log(fi["target_sek"] / tpv) / math.log(1 + rate)
    else:
        yrs_to_fi = float("inf")
    fi_year = 2026 + yrs_to_fi
    fi_str  = f"~{fi_year:.0f}" if fi_year < 2100 else ">2100"
    print(f"  {label:<14} {rate:>+.0%}  {proj:>14,.0f} kr  {fi_str:>10}")

# ── Macro trigger states ───────────────────────────────────────────────────────

print(f"\n{'='*62}")
print("MACRO SIGNALS")
print(f"{'='*62}")

ry_arrow = "v" if trig["ry_signal"] == "COMPRESSING" else "^"
print(f"\n  HY-IG spread  : {trig['hy_spread_bps']:.0f} bps")
print(f"  Real yield    : {trig['ry_current']:+.2f}%  (10d {trig['ry_10d_ma']:+.2f}%  |  90d {trig['ry_90d_ma']:+.2f}%)  {ry_arrow}")
print(f"  Yield curve   : T10Y3M {trig['curve_t10y3m']:+.0f} bps")

print(f"\n{'='*62}")
