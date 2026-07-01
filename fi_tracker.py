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

# ── Tactical rules ──────────────────────────────────────────────────────────────

print(f"\n{'='*62}")
print("TACTICAL RULES")
print(f"{'='*62}")

# ── Silver GSR tactical ─────────────────────────────────────────────────────────
GSR_T1              = 83.36   # p85
GSR_T2              = 86.45   # p90
GSR_EXIT            = 62.56   # p33 cycle-complete (100% WR on 162 instances)
GSR_PEAK_WINDOW     = 60      # days for rolling peak
GSR_PEAK_FALL_PCT   = 0.05    # must fall ≥5% from peak before signal valid

try:
    import warnings
    warnings.filterwarnings("ignore")

    _gc_path = DATA_DIR / "commodities" / "GC_F.parquet"
    _si_path = DATA_DIR / "commodities" / "SI_F.parquet"

    _gc = pd.read_parquet(_gc_path)
    _gc["date"] = pd.to_datetime(_gc["date"])
    _gc = _gc.set_index("date")["close"].sort_index().dropna()

    _si = pd.read_parquet(_si_path)
    _si["date"] = pd.to_datetime(_si["date"])
    _si = _si.set_index("date")["close"].sort_index().dropna()

    _common = _gc.index.intersection(_si.index)
    _gsr    = (_gc.reindex(_common) / _si.reindex(_common)).dropna()

    _gsr_now      = float(_gsr.iloc[-1])
    _gsr_date     = _gsr.index[-1].date()
    _peak_60d     = float(_gsr.iloc[-GSR_PEAK_WINDOW:].max())
    _fall_from_pk = (_peak_60d - _gsr_now) / _peak_60d  # positive = fallen

    _fallen_enough = _fall_from_pk >= GSR_PEAK_FALL_PCT

    if _gsr_now >= GSR_T2 and _fallen_enough:
        _silver_signal = "T2 ACTIVE"
        _silver_action = "ADD +17% silver (fund from AVGO: AVGO -> 38%, Silver -> 17%)"
    elif _gsr_now >= GSR_T1 and _fallen_enough:
        _silver_signal = "T1 ACTIVE"
        _silver_action = "ADD +12% silver (fund from AVGO: AVGO -> 43%, Silver -> 12%)"
    elif _gsr_now < GSR_EXIT:
        _silver_signal = "EXIT"
        _silver_action = "SELL silver, return to base (AVGO back to 55%, Silver -> 0%)"
    else:
        _silver_signal = "INACTIVE"
        _silver_action = "No action -- hold base"

    print(f"\n  Silver GSR Tactical")
    print(f"    GSR now        : {_gsr_now:.2f}  (as of {_gsr_date})")
    print(f"    60d GSR peak   : {_peak_60d:.2f}")
    print(f"    Fall from peak : {_fall_from_pk:.1%}  "
          f"({'yes' if _fallen_enough else 'no (need >=5% fall for signal)'})")
    print(f"    T1 threshold   : {GSR_T1}  |  T2: {GSR_T2}  |  Exit: {GSR_EXIT}")
    print(f"    Signal         : {_silver_signal}")
    print(f"    Action         : {_silver_action}")

except Exception as _e:
    print(f"\n  Silver GSR Tactical : [unavailable — {_e}]")

# ── AVGO 200d guard ─────────────────────────────────────────────────────────────
AVGO_MA = 200

try:
    _av_path = DATA_DIR / "equities" / "AVGO.parquet"
    _av      = pd.read_parquet(_av_path)
    _av["date"] = pd.to_datetime(_av["date"])
    _av      = _av.set_index("date")["close"].sort_index().dropna()

    _av_now   = float(_av.iloc[-1])
    _av_date  = _av.index[-1].date()
    _sma200   = float(_av.iloc[-AVGO_MA:].mean())
    _above    = _av_now >= _sma200
    _gap_pct  = (_av_now - _sma200) / _sma200

    if _above:
        _avgo_signal = "BASE"
        _avgo_action = "Hold base (Gold 25%, AVGO 55%, LLY 20%)"
    else:
        _avgo_signal = "DEFENSIVE"
        _avgo_action = "Rotate AVGO -> Gold+LLY (Gold 52.5%, AVGO 0%, LLY 47.5%)"

    print(f"\n  AVGO 200d Guard")
    print(f"    AVGO now       : ${_av_now:.2f}  (as of {_av_date})")
    print(f"    200d SMA       : ${_sma200:.2f}  ({_gap_pct:+.1%} gap)")
    print(f"    Signal         : {_avgo_signal}")
    print(f"    Action         : {_avgo_action}")

except Exception as _e:
    print(f"\n  AVGO 200d Guard : [unavailable — {_e}]")

# ── AVGO earnings checkpoint (manual — guard is price-lagging, this is not) ─────
# 2026-07-01 baseline: fwd/trail EPS ratio 3.23x, vs 1.1-1.5x for quality peers
# (AAPL, GOOG, MA, TDG, MNST, ANET, COST) — AVGO is uniquely priced for a near-
# tripling of EPS. Guard reacts to sustained price decline; this catches a
# guided-trajectory miss before SMA200 would.
try:
    import datetime
    import yfinance as yf

    _av_info   = yf.Ticker("AVGO").info
    _trail_eps = _av_info.get("trailingEps")
    _fwd_eps   = _av_info.get("forwardEps")
    _eps_ratio = (_fwd_eps / _trail_eps) if (_trail_eps and _fwd_eps) else None
    _next_ts   = _av_info.get("earningsTimestampStart")
    _next_date = (datetime.datetime.fromtimestamp(_next_ts, datetime.timezone.utc).date()
                  if _next_ts else None)

    print(f"\n  AVGO Earnings Checkpoint")
    print(f"    Trailing EPS   : ${_trail_eps:.2f}" if _trail_eps else "    Trailing EPS   : n/a")
    print(f"    Forward EPS    : ${_fwd_eps:.2f}" if _fwd_eps else "    Forward EPS    : n/a")
    if _eps_ratio:
        print(f"    Fwd/Trail ratio: {_eps_ratio:.2f}x  (baseline 2026-07-01: 3.23x)")
    print(f"    Next earnings  : {_next_date}" if _next_date else "    Next earnings  : n/a")
    print(f"    Action         : after the print, check actual AI revenue/EPS against the")
    print(f"                     $56B FY26 / $100B FY27 guided path. Meaningfully short of")
    print(f"                     trajectory -> revisit conviction, even if price > SMA200.")

except Exception as _e:
    print(f"\n  AVGO Earnings Checkpoint : [unavailable — {_e}]")

# ── Opportunistic sleeve (war-chest tactical layer, separate from base) ─────
try:
    import run_entry_screen
    run_entry_screen.sleeve_daily_summary()
except Exception as _e:
    print(f"\n  Opportunistic Sleeve : [unavailable — {_e}]")

print(f"\n{'='*62}")
