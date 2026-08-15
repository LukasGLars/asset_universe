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
    _regime_error = None
except Exception as _e:
    reg = None
    _regime_error = _e

# ── Portfolio snapshot ──────────────────────────────────────────────────────────
# fi_pace() derives TPV as sum(snapshot().value_sek) and raises if any share
# position is missing price data (see its docstring), so it's wrapped the
# same way current_regime() already is: a data outage blanks only the
# TPV-dependent lines below, not the whole dashboard (guard/signals/earnings
# sections don't need TPV and must keep working).

snap = portfolio.snapshot(DATA_DIR)
try:
    fi = portfolio.fi_pace(DATA_DIR)
    _fi_error = None
except Exception as _e:
    fi = None
    _fi_error = _e
tpv = fi["tpv_sek"] if fi else None

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
if tpv is not None:
    print(f"  {'TPV':<20} {'':>7} {'':>10} {tpv:>12,.0f} kr")
    for bucket, label in [("reactor_core", "Reactor Core"), ("home_base", "Home Base"), ("war_chest", "War Chest")]:
        sub = snap[snap["bucket"] == bucket]["value_sek"].sum()
        pct = sub / tpv if tpv else 0
        print(f"    {label:<18} {sub:>12,.0f} kr  ({pct:.0%})")
else:
    print(f"  TPV : [unavailable — {_fi_error}]")

# ── FI@50 pace ──────────────────────────────────────────────────────────────────

print(f"\n{'='*62}")
print("FI@50 PACE TRACKER")
print(f"{'='*62}")

if fi:
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

    monthly_contrib = fi["monthly_contribution_sek"]
    print()
    print(f"  {'Scenario':<14} {'CAGR':>6}  {'Projected':>14}  {'FI date':>10}"
          f"   (incl. {monthly_contrib:,.0f} kr/mo contributions)")
    print(f"  {'-'*72}")
    for label, rate in [("Bear", 0.10), ("Conservative", 0.15), ("Base", 0.20),
                        ("Current AWAR", fi["awar"]), ("Bull", 0.30)]:
        proj      = portfolio.future_value_with_contributions(tpv, rate, fi["years_remaining"], monthly_contrib)
        yrs_to_fi = portfolio.years_to_reach_target(tpv, rate, monthly_contrib, fi["target_sek"])
        fi_year   = 2026 + yrs_to_fi
        fi_str    = f"~{fi_year:.0f}" if fi_year < 2100 else ">2100"
        print(f"  {label:<14} {rate:>+.0%}  {proj:>14,.0f} kr  {fi_str:>10}")
else:
    print(f"  FI@50 Pace : [unavailable — {_fi_error}]")

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
    print(f"  Macro Regime : [unavailable — {_regime_error}]")

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
    print(f"  Portfolio Signals : [unavailable — regime unavailable: {_regime_error}]")

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

# ── AVGO 200d guard (+ crash guard, + joint-stress escalation) ───────────────
AVGO_MA = 200
LLY_MA  = 200
# Joint-stress escalation (2026-07-02): LLY's diversification vs AVGO is
# regime-dependent -- real in liquidity crashes (COVID), absent in macro/
# trade-driven selloffs (2022 rates, 2025 tariffs) where LLY fell alongside
# or worse than AVGO. When LLY independently trips the SAME validated guard
# logic used for AVGO (no new parameters) while AVGO's guard is also active,
# that's the diversification breaking down -- escalate fully into Gold.
# Validated on AVGO's own history + a TXN analog (2000-2026, incl. 2001/2008):
# monotonic improvement with more Gold, best at 100%. See
# run_joint_stress_validation.py and MEMORY.md.
# Crash guard (2026-07-02): early-activation layer on the SAME guard, not a
# separate strategy -- the 200d SMA can't react to a fast, sharp break (the
# TXN analog test showed -35.3% MaxDD even with the SMA guard active during
# the 2001 dot-com crash). If AVGO drops more than CRASH_ROC_THRESHOLD over
# CRASH_ROC_WINDOW trading days, treat the guard as active immediately.
# Re-entry unchanged -- still governed by price back above the 200d SMA.
# Validated: 20-cell parameter grid, every cell matched or beat the SMA-only
# guard on both AVGO's own history and the TXN analog (2000-2026). See
# run_combined_system.py and MEMORY.md for the full validation.
CRASH_ROC_WINDOW    = 5
CRASH_ROC_THRESHOLD = -0.10

try:
    _av_path = DATA_DIR / "equities" / "AVGO.parquet"
    _av      = pd.read_parquet(_av_path)
    _av["date"] = pd.to_datetime(_av["date"])
    _av      = _av.set_index("date")["close"].sort_index().dropna()

    _av_now   = float(_av.iloc[-1])
    _av_date  = _av.index[-1].date()
    _sma200   = float(_av.iloc[-AVGO_MA:].mean())
    _ma_above = _av_now >= _sma200
    _gap_pct  = (_av_now - _sma200) / _sma200

    _roc_now     = float(_av.iloc[-1] / _av.iloc[-(CRASH_ROC_WINDOW + 1)] - 1)
    _crash_fired = _roc_now <= CRASH_ROC_THRESHOLD

    _above = _ma_above and not _crash_fired
    _guard_active = not _above

    if _crash_fired:
        _avgo_signal = "DEFENSIVE"
        _trigger     = "CRASH"
    elif not _ma_above:
        _avgo_signal = "DEFENSIVE"
        _trigger     = "MA"
    else:
        _avgo_signal = "BASE"
        _trigger     = "none"

    # LLY-stress check (same guard logic, reused as-is) + joint-stress override
    _lly_path  = DATA_DIR / "equities" / "LLY.parquet"
    _lly       = pd.read_parquet(_lly_path)
    _lly["date"] = pd.to_datetime(_lly["date"])
    _lly       = _lly.set_index("date")["close"].sort_index().dropna()

    _lly_now    = float(_lly.iloc[-1])
    _lly_sma    = float(_lly.iloc[-LLY_MA:].mean())
    _lly_ma_ok  = _lly_now >= _lly_sma
    _lly_roc    = float(_lly.iloc[-1] / _lly.iloc[-(CRASH_ROC_WINDOW + 1)] - 1)
    _lly_stress = (not _lly_ma_ok) or (_lly_roc <= CRASH_ROC_THRESHOLD)
    _joint      = _guard_active and _lly_stress

    # Gap-down tranche reminder (2026-08-14, MEMORY.md "Gap-down tranche
    # validated"): only on the CRASH trigger specifically (not a plain MA
    # breach) -- that's the trigger class the tranche plan is tied to.
    # No state tracking exists for whether the tranche was already spent --
    # this note reappears on every future CRASH trigger regardless. Operator
    # must track deployment status manually.
    _tranche_note = (
        " | If the gap-down tranche (50k into AVGO) hasn't been deployed "
        "yet, deploy it now -- see MEMORY.md 'Gap-down tranche validated'."
        if _trigger == "CRASH" else ""
    )

    if _joint:
        _avgo_action = f"JOINT STRESS -> full flight to Gold (Gold 100%, AVGO 0%, LLY 0%){_tranche_note}"
    elif _guard_active:
        _avgo_action = f"Rotate AVGO -> Gold+LLY (Gold 52.5%, AVGO 0%, LLY 47.5%){_tranche_note}"
    else:
        _avgo_action = "Hold base (Gold 25%, AVGO 55%, LLY 20%)"

    print(f"\n  AVGO 200d Guard")
    print(f"    AVGO now       : ${_av_now:.2f}  (as of {_av_date})")
    print(f"    200d SMA       : ${_sma200:.2f}  ({_gap_pct:+.1%} gap)")
    print(f"    {CRASH_ROC_WINDOW}d ROC         : {_roc_now:+.1%}  (crash threshold: {CRASH_ROC_THRESHOLD:.0%})")
    print(f"    Signal         : {_avgo_signal}  (trigger: {_trigger})")
    print(f"    LLY stress     : {'ACTIVE' if _lly_stress else 'inactive'}  "
          f"(${_lly_now:.2f} vs 200d SMA ${_lly_sma:.2f}, {CRASH_ROC_WINDOW}d ROC {_lly_roc:+.1%})")
    print(f"    Joint stress   : {'ACTIVE' if _joint else 'inactive'}  "
          f"(guard AND LLY stress both active)")
    print(f"    Action         : {_avgo_action}")

except Exception as _e:
    print(f"\n  AVGO 200d Guard : [unavailable — {_e}]")

# ── AVGO earnings checkpoint (manual — guard is price-lagging, this is not) ─────
# Fixed 2026-07-06: yfinance's raw trailingEps (GAAP) vs forwardEps (non-GAAP
# consensus) mixes conventions -- for AVGO specifically, VMware-acquisition
# amortization depresses the GAAP side, which inflated the ratio to 3.22x.
# Normalized (non-GAAP TTM actual vs non-GAAP +1yr estimate, both from
# earnings_history/eps_trend), the real ratio is ~2.39x. The original
# "outlier" framing against 1.17-1.41x (AAPL/TDG/ANET) was itself a
# peer-selection artifact -- against real AI/semi peers, AVGO is mid-pack,
# not an outlier. See eps_ratio.py and run_peer_valuation.py.
try:
    import datetime
    import yfinance as yf
    from earnings_reminder import earnings_reminder_state
    from earnings_trajectory import beat_streak, guidance_direction
    from eps_growth_regime import ttm_series, yoy_growth_series
    from eps_ratio import normalized_eps_ratio
    from sec_edgar import fetch_revenue_facts, reconstruct_quarterly_facts

    AVGO_CIK = "0001730168"

    _today_utc = datetime.datetime.now(datetime.timezone.utc).date()

    _av_tk       = yf.Ticker("AVGO")
    _av_info     = _av_tk.info
    _av_hist     = _av_tk.earnings_history
    _av_trend    = _av_tk.eps_trend
    _av_ttm      = _av_hist["epsActual"].tolist() if _av_hist is not None and not _av_hist.empty else []
    _av_fwd_1y   = (_av_trend.loc["+1y", "current"]
                    if _av_trend is not None and "+1y" in _av_trend.index else None)
    _eps_ratio   = normalized_eps_ratio(_av_ttm, _av_fwd_1y)
    _next_ts     = _av_info.get("earningsTimestampStart")
    _next_date   = (datetime.datetime.fromtimestamp(_next_ts, datetime.timezone.utc).date()
                    if _next_ts else None)
    _reminder    = earnings_reminder_state(_next_date, _today_utc)

    # Automatable half of the earnings-day checklist. The other half (actual
    # AI revenue vs. the $56B/$100B guided pace, Anthropic/OpenAI contract
    # commentary) isn't -- no API exposes segment revenue or call transcripts,
    # so that stays a manual read of the release (see earnings_verdict.py).
    _av_streak    = (beat_streak(list(zip(_av_hist["epsActual"], _av_hist["epsEstimate"])))
                      if _av_hist is not None and not _av_hist.empty else None)
    _av_fwd_90d   = (_av_trend.loc["+1y", "90daysAgo"]
                      if _av_trend is not None and "+1y" in _av_trend.index else None)
    _av_guidance  = (guidance_direction(_av_fwd_1y, _av_fwd_90d)
                      if _av_fwd_1y is not None and _av_fwd_90d is not None else "unknown")
    _av_latest_q  = (str(_av_hist.index[-1].date()) if _av_hist is not None and not _av_hist.empty else "n/a")

    # Total-company revenue (NOT the AI-specific segment -- confirmed not
    # available anywhere structured). Actual via SEC EDGAR, TTM YoY growth
    # via the same machinery the research study used. No "revising up/down"
    # trend shown for revenue -- yfinance's revenue_estimate has no
    # historical revision snapshot (unlike eps_trend's 7/30/60/90-day
    # columns), confirmed by checking, not assumed.
    _av_rev_quarters = reconstruct_quarterly_facts(fetch_revenue_facts(AVGO_CIK))
    _av_rev_latest    = next(iter(_av_rev_quarters.values()), None)
    _av_rev_growth_series = yoy_growth_series(ttm_series(_av_rev_quarters))
    _av_rev_growth    = (_av_rev_growth_series[max(_av_rev_growth_series)]
                          if _av_rev_growth_series else None)
    _av_rev_table     = _av_tk.revenue_estimate
    # "0q" is yfinance's label for the upcoming (not-yet-reported) quarter --
    # confirmed against the actual next-earnings date, not assumed. "+1q"
    # would be the quarter AFTER that, one too many periods ahead.
    _av_rev_next_q    = (_av_rev_table.loc["0q", "avg"]
                          if _av_rev_table is not None and "0q" in _av_rev_table.index else None)
    _av_rev_next_g    = (_av_rev_table.loc["0q", "growth"]
                          if _av_rev_table is not None and "0q" in _av_rev_table.index else None)

    # Latest reported quarter's actual EPS vs. what it beat/missed --
    # distinct from TTM EPS above (a trailing sum, not a single print).
    # This is "the actual earnings" in the literal sense: what got
    # reported, against what was expected, for the most recent quarter.
    _av_q_actual   = _av_hist["epsActual"].iloc[-1] if _av_hist is not None and not _av_hist.empty else None
    _av_q_est      = _av_hist["epsEstimate"].iloc[-1] if _av_hist is not None and not _av_hist.empty else None
    _av_q_surprise = _av_hist["surprisePercent"].iloc[-1] if _av_hist is not None and not _av_hist.empty else None

    print(f"\n  AVGO Earnings Checkpoint")
    if _av_q_actual is not None and _av_q_est is not None:
        _surprise_str = f"  ({_av_q_surprise:+.1%} surprise)" if _av_q_surprise is not None else ""
        print(f"    Latest qtr EPS (actual vs est.): ${_av_q_actual:.2f} vs ${_av_q_est:.2f}{_surprise_str}")
    else:
        print(f"    Latest qtr EPS (actual vs est.): n/a")
    print(f"    TTM EPS (non-GAAP actual)  : ${sum(_av_ttm):.2f}" if _av_ttm else "    TTM EPS (non-GAAP actual)  : n/a")
    print(f"    Forward EPS (+1yr est.)    : ${_av_fwd_1y:.2f}" if _av_fwd_1y else "    Forward EPS (+1yr est.)    : n/a")
    if _eps_ratio:
        print(f"    Fwd/Trail ratio (normalized): {_eps_ratio:.2f}x  (mid-pack vs. real AI/semi "
              f"peers; corrected 2026-07-06 from a GAAP/non-GAAP mismatched 3.22x)")
    if _av_rev_latest:
        _av_rev_growth_str = f"  (TTM YoY: {_av_rev_growth:+.1%})" if _av_rev_growth is not None else ""
        print(f"    Revenue (latest qtr, actual): ${_av_rev_latest/1e9:.2f}B{_av_rev_growth_str}")
    else:
        print(f"    Revenue (latest qtr, actual): n/a")
    print(f"    Next-qtr revenue consensus : ${_av_rev_next_q/1e9:.2f}B (implied YoY {_av_rev_next_g:+.1%})"
          if _av_rev_next_q is not None and _av_rev_next_g is not None else "    Next-qtr revenue consensus : n/a")
    print(f"    Next earnings  : {_next_date}" if _next_date else "    Next earnings  : n/a")
    print(f"    Reminder       : {_reminder}")
    print(f"    Latest quarter : {_av_latest_q}")
    print(f"    Beat streak    : {_av_streak}" if _av_streak is not None else "    Beat streak    : n/a")
    print(f"    Guidance trend : {_av_guidance}  (+1yr estimate vs. 90 days ago)")

    from earnings_verdict import format_verdict_line
    _av_verdict_line = format_verdict_line("AVGO")
    if _av_verdict_line:
        print(f"    Last verdict   : {_av_verdict_line}")

except Exception as _e:
    print(f"\n  AVGO Earnings Checkpoint : [unavailable — {_e}]")

# ── LLY earnings checkpoint (mirrors AVGO's, same normalized method) ────────
try:
    import datetime
    import yfinance as yf
    from earnings_reminder import earnings_reminder_state
    from earnings_trajectory import beat_streak, guidance_direction
    from eps_growth_regime import ttm_series, yoy_growth_series
    from eps_ratio import normalized_eps_ratio
    from sec_edgar import fetch_revenue_facts, reconstruct_quarterly_facts

    LLY_CIK = "0000059478"

    _today_utc = datetime.datetime.now(datetime.timezone.utc).date()

    _lly_tk      = yf.Ticker("LLY")
    _lly_info    = _lly_tk.info
    _lly_hist    = _lly_tk.earnings_history
    _lly_trend   = _lly_tk.eps_trend
    _lly_ttm     = _lly_hist["epsActual"].tolist() if _lly_hist is not None and not _lly_hist.empty else []
    _lly_fwd_1y  = (_lly_trend.loc["+1y", "current"]
                    if _lly_trend is not None and "+1y" in _lly_trend.index else None)
    _lly_ratio   = normalized_eps_ratio(_lly_ttm, _lly_fwd_1y)
    _lly_next_ts   = _lly_info.get("earningsTimestampStart")
    _lly_next_date = (datetime.datetime.fromtimestamp(_lly_next_ts, datetime.timezone.utc).date()
                      if _lly_next_ts else None)
    _lly_reminder  = earnings_reminder_state(_lly_next_date, _today_utc)

    _lly_streak   = (beat_streak(list(zip(_lly_hist["epsActual"], _lly_hist["epsEstimate"])))
                      if _lly_hist is not None and not _lly_hist.empty else None)
    _lly_fwd_90d  = (_lly_trend.loc["+1y", "90daysAgo"]
                      if _lly_trend is not None and "+1y" in _lly_trend.index else None)
    _lly_guidance = (guidance_direction(_lly_fwd_1y, _lly_fwd_90d)
                      if _lly_fwd_1y is not None and _lly_fwd_90d is not None else "unknown")
    _lly_latest_q = (str(_lly_hist.index[-1].date()) if _lly_hist is not None and not _lly_hist.empty else "n/a")

    _lly_rev_quarters = reconstruct_quarterly_facts(fetch_revenue_facts(LLY_CIK))
    _lly_rev_latest    = next(iter(_lly_rev_quarters.values()), None)
    _lly_rev_growth_series = yoy_growth_series(ttm_series(_lly_rev_quarters))
    _lly_rev_growth    = (_lly_rev_growth_series[max(_lly_rev_growth_series)]
                           if _lly_rev_growth_series else None)
    _lly_rev_table     = _lly_tk.revenue_estimate
    # "0q" is yfinance's label for the upcoming (not-yet-reported) quarter --
    # see the AVGO block above for the same confirmed convention.
    _lly_rev_next_q    = (_lly_rev_table.loc["0q", "avg"]
                           if _lly_rev_table is not None and "0q" in _lly_rev_table.index else None)
    _lly_rev_next_g    = (_lly_rev_table.loc["0q", "growth"]
                           if _lly_rev_table is not None and "0q" in _lly_rev_table.index else None)

    _lly_q_actual   = _lly_hist["epsActual"].iloc[-1] if _lly_hist is not None and not _lly_hist.empty else None
    _lly_q_est      = _lly_hist["epsEstimate"].iloc[-1] if _lly_hist is not None and not _lly_hist.empty else None
    _lly_q_surprise = _lly_hist["surprisePercent"].iloc[-1] if _lly_hist is not None and not _lly_hist.empty else None

    print(f"\n  LLY Earnings Checkpoint")
    if _lly_q_actual is not None and _lly_q_est is not None:
        _lly_surprise_str = f"  ({_lly_q_surprise:+.1%} surprise)" if _lly_q_surprise is not None else ""
        print(f"    Latest qtr EPS (actual vs est.): ${_lly_q_actual:.2f} vs ${_lly_q_est:.2f}{_lly_surprise_str}")
    else:
        print(f"    Latest qtr EPS (actual vs est.): n/a")
    print(f"    TTM EPS (non-GAAP actual)  : ${sum(_lly_ttm):.2f}" if _lly_ttm else "    TTM EPS (non-GAAP actual)  : n/a")
    print(f"    Forward EPS (+1yr est.)    : ${_lly_fwd_1y:.2f}" if _lly_fwd_1y else "    Forward EPS (+1yr est.)    : n/a")
    if _lly_ratio:
        print(f"    Fwd/Trail ratio (normalized): {_lly_ratio:.2f}x  (baseline established 2026-07-06)")
    if _lly_rev_latest:
        _lly_rev_growth_str = f"  (TTM YoY: {_lly_rev_growth:+.1%})" if _lly_rev_growth is not None else ""
        print(f"    Revenue (latest qtr, actual): ${_lly_rev_latest/1e9:.2f}B{_lly_rev_growth_str}")
    else:
        print(f"    Revenue (latest qtr, actual): n/a")
    print(f"    Next-qtr revenue consensus : ${_lly_rev_next_q/1e9:.2f}B (implied YoY {_lly_rev_next_g:+.1%})"
          if _lly_rev_next_q is not None and _lly_rev_next_g is not None else "    Next-qtr revenue consensus : n/a")
    print(f"    Next earnings  : {_lly_next_date}" if _lly_next_date else "    Next earnings  : n/a")
    print(f"    Reminder       : {_lly_reminder}")
    print(f"    Latest quarter : {_lly_latest_q}")
    print(f"    Beat streak    : {_lly_streak}" if _lly_streak is not None else "    Beat streak    : n/a")
    print(f"    Guidance trend : {_lly_guidance}  (+1yr estimate vs. 90 days ago)")

    from earnings_verdict import format_verdict_line
    _lly_verdict_line = format_verdict_line("LLY")
    if _lly_verdict_line:
        print(f"    Last verdict   : {_lly_verdict_line}")

except Exception as _e:
    print(f"\n  LLY Earnings Checkpoint : [unavailable — {_e}]")

# ── Opportunistic sleeve (war-chest tactical layer, separate from base) ─────
try:
    import run_entry_screen
    run_entry_screen.sleeve_daily_summary()
except Exception as _e:
    print(f"\n  Opportunistic Sleeve : [unavailable — {_e}]")

# ── Next contribution (where should the next kr go) ──────────────────────────
# Answers "where does new/monthly capital go today", not "should we hold what
# we already own" (that's the guard above). Gold/AVGO/LLY only -- Silver is
# excluded by design, it has its own GSR trigger and its own funding
# mechanism, not new contributions (see MEMORY.md backlog).
try:
    from run_combined_system import WEIGHTS, JOINT_WEIGHTS
    from next_contribution import next_contribution_target

    _rc_total = snap[snap["bucket"] == "reactor_core"]["value_sek"].sum()

    def _rc_weight(name):
        row = snap[snap["name"] == name]
        if row.empty or not _rc_total:
            return 0.0
        return float(row["value_sek"].iloc[0]) / _rc_total

    _current_weights = {
        "GC_F": _rc_weight("Gold"),
        "AVGO": _rc_weight("Broadcom"),
        "LLY":  _rc_weight("Eli Lilly"),
    }

    _silver_state = ("T2" if _silver_signal == "T2 ACTIVE"
                      else "T1" if _silver_signal == "T1 ACTIVE"
                      else "INACTIVE")
    _target_weights = JOINT_WEIGHTS[_silver_state] if _joint else WEIGHTS[(_guard_active, _silver_state)]

    _next_allowed = {"GC_F": True, "AVGO": not _guard_active, "LLY": not _lly_stress}

    _next_ticker, _next_detail = next_contribution_target(_current_weights, _target_weights, _next_allowed)
    _next_name = {"GC_F": "Gold", "AVGO": "Broadcom (AVGO)", "LLY": "Eli Lilly (LLY)"}[_next_ticker]
    _next_row  = _next_detail[_next_ticker]

    print(f"\n{'='*62}")
    print("NEXT CONTRIBUTION")
    print(f"{'='*62}")
    print(f"\n  Next kr        -> {_next_name}")
    print(f"    Current wt (of Reactor Core) : {_next_row['current']:.1%}")
    print(f"    Target wt (current regime)   : {_next_row['target']:.1%}")
    print(f"    Gap                          : {_next_row['gap']:+.1%}")
    print(f"    Gate                         : {'OPEN' if _next_row['allowed'] else 'CLOSED (fallback)'}")
    print(f"    Note: Silver excluded -- funded by its own GSR trigger, not new contributions")

except Exception as _e:
    print(f"\n  Next Contribution : [unavailable — {_e}]")

print(f"\n{'='*62}")
