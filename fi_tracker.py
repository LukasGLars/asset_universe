"""
FI@50 portfolio dashboard.

Usage:
    python fi_tracker.py
"""

import sys
import math
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
from asset_universe import config, portfolio
from asset_universe.analysis.engine import current_regime, query as engine_query

DATA_DIR = config.raw_data_dir()

# ── Pre-compute regime state (used by both macro and signals sections) ──────────

try:
    reg = current_regime(DATA_DIR)
except Exception as _e:
    reg = None

# ── Portfolio snapshot ──────────────────────────────────────────────────────────

snap = portfolio.snapshot(DATA_DIR)
fi   = portfolio.fi_pace(DATA_DIR)
tpv  = fi["tpv_sek"]

print("=" * 62)
print("REACTOR CORE -- PORTFOLIO SNAPSHOT")
print("=" * 62)
print(f"{'Position':<22} {'Shares':>7} {'Price':>10} {'Value SEK':>12} {'Wt':>6}")
print("-" * 62)

for _, row in snap.iterrows():
    shares_str = f"{int(row['shares'])}" if row["shares"] else "-"
    price_str  = f"{row['price_sek']:,.0f} kr" if pd.notna(row["price_sek"]) else "manual"
    value_str  = f"{row['value_sek']:,.0f} kr" if pd.notna(row["value_sek"]) else "-"
    wt_str     = f"{row['weight']:.1%}"
    print(f"  {row['name']:<20} {shares_str:>7} {price_str:>10} {value_str:>12} {wt_str:>6}")

print("-" * 62)
print(f"  {'TPV':<20} {'':>7} {'':>10} {tpv:>12,.0f} kr")

for bucket, label in [("reactor_core", "Reactor Core"), ("home_base", "Home Base"), ("war_chest", "War Chest")]:
    sub = snap[snap["bucket"] == bucket]["value_sek"].sum()
    pct = sub / tpv if tpv else 0
    print(f"    {label:<18} {sub:>12,.0f} kr  ({pct:.0%})")

# ── FI@50 pace ──────────────────────────────────────────────────────────────────

print(f"\n{'='*62}")
print("FI@50 PACE TRACKER")
print(f"{'='*62}")

pace_icon = "ON PACE" if fi["on_pace"] else "BEHIND"
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

print()
print(f"  {'Scenario':<14} {'CAGR':>6}  {'Projected':>14}  {'FI date':>10}")
print(f"  {'-'*50}")
for label, rate in [("Bear", 0.10), ("Conservative", 0.15), ("Base", 0.20),
                    ("Current AWAR", fi["awar"]), ("Bull", 0.30)]:
    proj      = tpv * (1 + rate) ** fi["years_remaining"]
    yrs_to_fi = math.log(fi["target_sek"] / tpv) / math.log(1 + rate) if rate > 0 else float("inf")
    fi_year   = 2026 + yrs_to_fi
    fi_str    = f"~{fi_year:.0f}" if fi_year < 2100 else ">2100"
    print(f"  {label:<14} {rate:>+.0%}  {proj:>14,.0f} kr  {fi_str:>10}")

# ── Macro regime table ──────────────────────────────────────────────────────────

print(f"\n{'='*62}")
print("MACRO REGIME")
print(f"{'='*62}")

if reg:
    raw     = reg["raw"]
    regimes = reg["regimes"]

    ROWS = [
        ("Nominal 10Y",  "nominal_10y", f"{raw.get('nominal_10y', float('nan')):.2f}%",          "nominal_10y_regime"),
        ("Real Yield",   "ry",          f"{raw.get('ry', float('nan')):+.2f}%",                  "ry_regime"),
        ("Breakeven",    "breakeven",   f"{raw.get('breakeven', float('nan')):.2f}%",             "breakeven_regime"),
        ("HY OAS",       "hy_oas",      f"{raw.get('hy_oas', float('nan')):.0f} bps",             "hy_oas_regime"),
        ("IG Credit",    "baa10y",      f"{raw.get('baa10y', float('nan')):.2f}%",                "baa10y_regime"),
        ("Curve 10Y-3M", "t10y3m",      f"{raw.get('t10y3m', float('nan'))*100:+.0f} bps",       "t10y3m_regime"),
        ("Curve 10Y-2Y", "t10y2y",      f"{raw.get('t10y2y', float('nan'))*100:+.0f} bps",       "t10y2y_regime"),
        ("SE 10Y",       "se_10y",      f"{raw.get('se_10y', float('nan')):.2f}%",                "se_10y_regime"),
        ("USD",          "usd",         f"{raw.get('usd', float('nan')):.1f}",                    "usd_regime"),
    ]

    ry_dir = "  ^" if raw.get("ry_rising") == 1.0 else "  v"
    print(f"\n  {'Feature':<18} {'Value':>10}   {'Regime':<8}")
    print(f"  {'-'*42}")
    for label, key, val_str, regime_key in ROWS:
        regime = regimes.get(regime_key, "--")
        suffix = ry_dir if key == "ry" else ""
        print(f"  {label:<18} {val_str:>10}   {regime}{suffix}")

    hy_20d    = raw.get("hy_20d_delta")
    direction = "widening" if hy_20d and hy_20d > 5 else ("tightening" if hy_20d and hy_20d < -5 else "flat")
    print(f"\n  HY 20d delta  : {hy_20d:+.0f} bps  ({direction})")
    print(f"  Confidence    : {reg['confidence']}")
    print(f"  Data through  : {reg['date']}")
else:
    print("  [regime unavailable]")

# ── Portfolio signals ───────────────────────────────────────────────────────────

print(f"\n{'='*62}")
print("PORTFOLIO SIGNALS")
print(f"{'='*62}")

# Map: (display_name, engine_ticker, momentum_feature_prefix)
# Momentum prefix matches REGIME_FEATURES keys: PPFB_mom_21d, PHAG_mom_21d, etc.
POSITION_MAP = [
    ("Gold",      "PPFB.DE", "PPFB"),
    ("Silver",    "PHAG.L",  "PHAG"),
    ("Eli Lilly", "LLY",     "LLY"),
    ("Walmart",   "WMT",     "WMT"),
    ("Cameco",    "CCJ",     "CCJ"),
    ("Vertiv",    "VRT",     "VRT"),
    ("Broadcom",  "AVGO",    "AVGO"),
]

if reg:
    regimes = reg["regimes"]

    # Core 3 + USD macro base — dynamic, uses current labels
    BASE = {k: regimes[k] for k in
            ["ry_regime", "nominal_10y_regime", "baa10y_regime", "usd_regime"]
            if k in regimes}

    base_str = "  ".join(
        f"{k.replace('_regime','')}={v}" for k, v in BASE.items()
    )
    print(f"\n  Base: {base_str}\n")
    print(f"  {'Position':<14} {'Wt':>5}  {'21d':>5} {'63d':>5}  "
          f"{'63d med':>8} {'252d med':>9} {'W252':>5} {'N':>5}  Note")
    print(f"  {'-'*70}")

    for pos_name, engine_tkr, mom_prefix in POSITION_MAP:
        # Weight from snapshot
        wt_row = snap[snap["name"].str.startswith(pos_name[:5])]
        wt     = float(wt_row["weight"].iloc[0]) if not wt_row.empty else float("nan")

        # Current momentum regime labels for this ticker
        m21_key   = f"{mom_prefix}_mom_21d_regime"
        m63_key   = f"{mom_prefix}_mom_63d_regime"
        m21_label = regimes.get(m21_key, "--")
        m63_label = regimes.get(m63_key, "--")

        # Primary: BASE + per-ticker momentum
        note = ""
        if m21_label != "--" and m63_label != "--":
            conditions = {**BASE, m21_key: m21_label, m63_key: m63_label}
        else:
            conditions = BASE.copy()
            note = "no mom data"

        result  = engine_query(conditions, [engine_tkr], forward_days=[63, 252])
        tkr_out = result["results"].get(engine_tkr, {})
        s63     = tkr_out.get("63d", {})

        # Fallback to BASE only if N < 30 at 63d
        if not s63 or s63.get("insufficient") or s63.get("n", 0) < 30:
            conditions = BASE.copy()
            result     = engine_query(conditions, [engine_tkr], forward_days=[63, 252])
            tkr_out    = result["results"].get(engine_tkr, {})
            s63        = tkr_out.get("63d", {})
            note       = "~base fallback"

        s252 = tkr_out.get("252d", {})

        def _s(s, field, fmt="+.1%"):
            if not s or s.get("insufficient"):
                return "--"
            return format(s[field], fmt)

        n_show = str(s63["n"]) if s63 and not s63.get("insufficient") else "--"
        wt_str = f"{wt:.1%}" if not math.isnan(wt) else "--"

        print(f"  {pos_name:<14} {wt_str:>5}  {m21_label:>5} {m63_label:>5}  "
              f"{_s(s63,'median'):>8} {_s(s252,'median'):>9} "
              f"{_s(s252,'win_rate','.0%'):>5} {n_show:>5}  {note}")
else:
    print("  [signals unavailable — regime could not be computed]")

print(f"\n{'='*62}")
