"""
Regime transition analysis and CAGR scenario modelling.

  1. Historical HIGH RY episode durations
  2. Daily transition matrix
  3. Monte Carlo: P(RY compression within N months)
  4. Portfolio CAGR under different compression timings

Usage:
    python run_transitions.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import warnings
warnings.filterwarnings("ignore")

import numpy as np

from asset_universe import config
from asset_universe.analysis.transitions import (
    episode_stats,
    transition_matrix,
    simulate_compression,
    cagr_scenarios,
    probability_weighted_cagr,
)

DATA_DIR = config.raw_data_dir()

# ── 1. Episode stats ──────────────────────────────────────────────────────────

stats = episode_stats(DATA_DIR, feature="ry", target_state="HIGH")

print("=" * 62)
print("REAL YIELD REGIME TRANSITION ANALYSIS")
print("=" * 62)
print()
print("1. Historical HIGH RY Episodes")
print("-" * 50)
for e in stats["episodes"]:
    print(f"  {str(e['start'].date()):>12}  to  {str(e['end'].date()):>12}  "
          f"({e['duration_months']:.0f} months)")

ce = stats.get("current_episode")
if ce:
    print(f"  {str(ce['start'].date()):>12}  to  {'(ongoing)':>12}  "
          f"({ce['duration_months']:.0f} months so far)  <-- current")

print()
print(f"  Complete episodes : N={stats['n_complete']}  [{stats['diversity']}]")
if "median_months" in stats:
    print(f"  Median duration   : {stats['median_months']:.0f} months")
    print(f"  P25 - P75         : {stats['p25_months']:.0f} - {stats['p75_months']:.0f} months")
    print(f"  Min / Max         : {stats['min_months']:.0f} / {stats['max_months']:.0f} months")

# ── 2. Transition matrix ──────────────────────────────────────────────────────

probs, counts = transition_matrix(DATA_DIR, feature="ry", period="monthly")

print()
print("2. Monthly Transition Probabilities (RY regime)")
print("-" * 50)
print(f"  {'From':>6}   {'->LOW':>7}  {'->MID':>7}  {'->HIGH':>7}   "
      f"{'N(LOW)':>5}  {'N(MID)':>5}  {'N(HIGH)':>5}")
for s in ["LOW", "MID", "HIGH"]:
    p = probs[s]
    c = counts[s]
    print(f"  {s:>6}   {p['LOW']:>6.2%}  {p['MID']:>6.2%}  {p['HIGH']:>6.2%}   "
          f"  {c['LOW']:>4}   {c['MID']:>4}   {c['HIGH']:>4}")

# ── 3. Monte Carlo (months as steps) ─────────────────────────────────────────

# Simulate in monthly steps; horizon = 120 months (10 years)
sim_months = simulate_compression(
    probs, from_state="HIGH", to_states=("MID", "LOW"),
    n_sim=10_000, horizon_days=120,  # horizon_days reused as steps
)
arr = np.array(sim_months)
never_pct = (arr > 120).mean()

print()
print("3. Monte Carlo: P(RY compression) from HIGH  [N=10,000 paths, monthly steps]")
print("-" * 50)
for months in [3, 6, 12, 18, 24, 36, 60]:
    p = (arr <= months).mean()
    bar = "#" * int(p * 30)
    print(f"  Within {months:>3}m : {p:>5.1%}  {bar}")

print(f"  Never >10yr : {never_pct:>5.1%}")

completed = arr[arr <= 120]
if len(completed):
    pct = np.percentile(completed, [25, 50, 75])
    print()
    print(f"  Median time to compression : {pct[1]:.0f} months  "
          f"(p25={pct[0]:.0f}m, p75={pct[2]:.0f}m)")

# ── 4. CAGR scenarios ─────────────────────────────────────────────────────────

df, meta = cagr_scenarios(DATA_DIR)

print()
print("4. Portfolio CAGR Scenarios")
print("-" * 50)
print(f"  Current TPV          : {meta['tpv']:>12,.0f} kr")
print(f"  Required CAGR        : {meta['required_cagr']:>+8.1%}/yr")
print()
print(f"  Drag-phase blend     (HIGH RY, current weights) : {meta['r_drag']:>+7.1%}/yr")
print(f"  Post-compress blend  (LOW RY,  target weights)  : {meta['r_compressed']:>+7.1%}/yr")
print()

print(f"  Per-asset expected returns:")
print(f"  {'Ticker':>6}  {'Drag(ann)':>10}  {'N':>4}    {'Post-compress':>14}  {'N':>4}  Note")
print("  " + "-" * 62)
for tkr, d in meta["asset_data"].items():
    note = "*fallback" if d.get("compressed_fallback") else ""
    print(f"  {tkr:>6}  {d['drag_return']:>+9.1%}  {d['drag_n']:>4}    "
          f"{d['compressed_return']:>+13.1%}  {d['compressed_n']:>4}  {note}")

print()
print(f"  {'Compress':>9}  {'TPV at T':>14}  {'Final TPV':>14}  "
      f"{'CAGR':>7}  {'vs req':>8}  {'Status'}")
print("  " + "-" * 72)
for _, r in df.iterrows():
    status = "ON PACE" if r["vs_required"] >= 0 else "BEHIND"
    print(f"  {int(r['compress_months']):>7}m  {r['v_at_compress']:>13,.0f} kr  "
          f"{r['v_final']:>13,.0f} kr  {r['cagr']:>+6.1%}  "
          f"{r['vs_required']:>+7.1%}  {status}")

print()
print(f"  Drag:          63d regime-pure returns within HIGH episodes, annualized.")
print(f"                 Only windows where RY stayed HIGH throughout.")
print(f"  Post-compress: 252d returns starting from each episode end date.")
print(f"                 What assets actually did after RY compression fired.")
print(f"  *fallback:     N<5 post-compress observations -- drag return used (conservative).")

# ── 5. Probability-weighted CAGR ─────────────────────────────────────────────

YEARS_REMAINING = 11.1
TARGET_SEK      = 12_934_706

pw = probability_weighted_cagr(
    sim_months     = sim_months,
    r_pre          = meta["r_drag"],
    r_post         = meta["r_compressed"],
    tpv            = meta["tpv"],
    years_remaining= YEARS_REMAINING,
    target_sek     = TARGET_SEK,
)

print()
print("5. Probability-Weighted CAGR  [10,000 Monte Carlo paths]")
print("-" * 50)
print(f"  E[CAGR]  (mean)  : {pw['mean']:>+7.1%}/yr")
print(f"  Median CAGR      : {pw['median']:>+7.1%}/yr")
print(f"  P10 / P90        : {pw['p10']:>+6.1%}  /  {pw['p90']:>+6.1%}")
print(f"  Required CAGR    : {pw['required']:>+7.1%}/yr")
print(f"  P(on pace)       : {pw['pct_on_pace']:>6.1%}  of paths end above target")

# ── 6. Stress test — thin-asset cap at 25%/yr ────────────────────────────────

df_stress, meta_stress = cagr_scenarios(DATA_DIR, thin_pre_cap=0.25)

pw_stress = probability_weighted_cagr(
    sim_months     = sim_months,
    r_pre          = meta_stress["r_drag"],
    r_post         = meta_stress["r_compressed"],
    tpv            = meta_stress["tpv"],
    years_remaining= YEARS_REMAINING,
    target_sek     = TARGET_SEK,
)

print()
print("6. Stress Test  VRT/AVGO Returns Capped at 25%/yr")
print("-" * 50)
print(f"  Drag-phase blend     : {meta_stress['r_drag']:>+7.1%}/yr")
print(f"  Post-compress blend  : {meta_stress['r_compressed']:>+7.1%}/yr")
print()
print(f"  {'Compress':>9}  {'TPV at T':>14}  {'Final TPV':>14}  "
      f"{'CAGR':>7}  {'vs req':>8}  {'Status'}")
print("  " + "-" * 72)
for _, r in df_stress.iterrows():
    status = "ON PACE" if r["vs_required"] >= 0 else "BEHIND"
    print(f"  {int(r['compress_months']):>7}m  {r['v_at_compress']:>13,.0f} kr  "
          f"{r['v_final']:>13,.0f} kr  {r['cagr']:>+6.1%}  "
          f"{r['vs_required']:>+7.1%}  {status}")

print()
print(f"  E[CAGR] stressed  : {pw_stress['mean']:>+7.1%}/yr")
print(f"  P(on pace)        : {pw_stress['pct_on_pace']:>6.1%}  of paths end above target")
print(f"  Cap applied to    : thin-N assets (VRT, AVGO) pre- and post-compression returns")
