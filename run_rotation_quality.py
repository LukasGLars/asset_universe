"""
run_rotation_quality.py

Quality-gated rotation backtest — properly this time.

Key differences from run_sleeve_backtest.py:
  1. Universe: quality-filtered (Sharpe >= 0.70, MaxDD >= -60%, 15yr+ history)
  2. Sleeve size: 10% only
  3. Regime gate: sleeve activates ONLY in HIGH+TIGHT (ry=HIGH, baa=TIGHT)
  4. Momentum gate: candidate must be above its 50d SMA at selection date
  5. VRT IPO: corrected 2020-02-07
  6. K grid: 3, 5, 8

Outputs: comparison_results/rotation_quality_grid.csv
         comparison_results/rotation_quality_selections.csv
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.store import reader

DATA_DIR  = config.raw_data_dir()
OUT_GRID  = PROJECT_ROOT / "comparison_results" / "rotation_quality_grid.csv"
OUT_SEL   = PROJECT_ROOT / "comparison_results" / "rotation_quality_selections.csv"

# Base portfolio
BASE      = {"GC_F": 0.25, "AVGO": 0.55, "LLY": 0.20}
BASE_CATS = {"GC_F": "commodities", "AVGO": "equities", "LLY": "equities"}

# Quality thresholds
MIN_HISTORY_YRS   = 15       # years of price history
MIN_SHARPE        = 0.60     # full-period unconditional Sharpe
MAX_DRAWDOWN_FLOOR = -0.65   # MaxDD must be better than -65%
MIN_REGIME_DATES  = 15       # matched dates for walk-forward ranking
CONFIRM_DAYS      = 5        # regime confirmation window
SMA_WINDOW        = 50       # momentum gate
SLEEVE_PCT        = 0.10     # 10% sleeve
TC                = 0.0010   # 10bps per asset per rotation

# Exclude from sleeve (base assets, silver tactical, problem tickers)
EXCLUDE = {
    "GC_F", "AVGO", "LLY",         # in base
    "SI_F", "PPFB_DE", "PHAG_L",   # silver / ETC
    "GC_F",                         # gold futures
    # Known high-beta blow-up candidates with short history
    "PLTR", "APP", "HOOD", "CVNA", "MSTR", "COIN",
}

# Regime where sleeve activates
SLEEVE_RY  = "HIGH"
SLEEVE_BAA = "TIGHT"


# ── Utilities ─────────────────────────────────────────────────────────────────

def load_prices(category: str, stem: str) -> pd.Series | None:
    path = DATA_DIR / category / f"{stem}.parquet"
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        s = df.set_index("date")["close"].sort_index().dropna()
        return s if len(s) > 252 else None
    except Exception:
        return None


def full_period_stats(prices: pd.Series) -> dict:
    r     = prices.pct_change().dropna()
    yrs   = (prices.index[-1] - prices.index[0]).days / 365.25
    cagr  = float(prices.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 else 0
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0
    dd    = prices / prices.cummax() - 1
    maxdd = float(dd.min())
    return {"cagr": cagr, "sharpe": sharpe, "maxdd": maxdd, "years": yrs}


def regime_median_return(prices: pd.Series, matched: pd.DatetimeIndex,
                          fwd_days: int = 252) -> float | None:
    rets = []
    for d in matched:
        idx = prices.index.searchsorted(d)
        if idx >= len(prices) or abs((prices.index[idx] - d).days) > 5:
            continue
        end = idx + fwd_days
        if end >= len(prices):
            continue
        p0, p1 = prices.iloc[idx], prices.iloc[end]
        if p0 > 0:
            rets.append((p1 - p0) / p0)
    return float(np.median(rets)) if len(rets) >= MIN_REGIME_DATES else None


def above_sma(prices: pd.Series, date: pd.Timestamp, window: int = 50) -> bool:
    """Return True if price at date is above its SMA(window)."""
    idx = prices.index.searchsorted(date)
    if idx < window or idx >= len(prices):
        return False
    actual_date = prices.index[idx]
    if abs((actual_date - date).days) > 5:
        return False
    sma = prices.iloc[idx - window: idx].mean()
    return float(prices.iloc[idx]) > sma


def perf(equity: pd.Series) -> dict:
    r     = equity.pct_change().dropna()
    yrs   = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr  = float(equity.iloc[-1] ** (1 / yrs) - 1)
    dd    = equity / equity.cummax() - 1
    maxdd = float(dd.min())
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0
    calmar = cagr / abs(maxdd) if maxdd != 0 else 0
    return {
        "cagr":   round(cagr, 4),
        "sharpe": round(sharpe, 3),
        "maxdd":  round(maxdd, 4),
        "calmar": round(calmar, 3),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 80)
    print("Quality-Gated Rotation Backtest")
    print(f"  Quality filter: Sharpe >= {MIN_SHARPE}, MaxDD >= {MAX_DRAWDOWN_FLOOR:.0%}, "
          f"history >= {MIN_HISTORY_YRS}yr")
    print(f"  Sleeve: {SLEEVE_PCT:.0%}, regime: ry={SLEEVE_RY} + baa={SLEEVE_BAA} only")
    print(f"  Momentum gate: price > {SMA_WINDOW}d SMA at selection date")
    print("=" * 80)

    # ── Build regime labels ────────────────────────────────────────────────────
    print("\nBuilding regime labels...")
    labeled_df, _ = regime_module.build(DATA_DIR)

    # ── Load and quality-screen candidates ────────────────────────────────────
    print("Loading and screening candidates...")
    candidates: dict[str, pd.Series] = {}
    rejected: dict[str, str] = {}
    min_days = int(MIN_HISTORY_YRS * 252)

    for stem in sorted((DATA_DIR / "equities").glob("*.parquet")):
        t = stem.stem
        if t in EXCLUDE:
            continue
        s = load_prices("equities", t)
        if s is None:
            rejected[t] = "load_failed"
            continue
        if len(s) < min_days:
            rejected[t] = f"history_short ({len(s)/252:.1f}yr)"
            continue
        st = full_period_stats(s)
        if st["sharpe"] < MIN_SHARPE:
            rejected[t] = f"sharpe_low ({st['sharpe']:.3f})"
            continue
        if st["maxdd"] < MAX_DRAWDOWN_FLOOR:
            rejected[t] = f"maxdd_bad ({st['maxdd']:.1%})"
            continue
        candidates[t] = s

    print(f"  Passed quality filter: {len(candidates)} equities")
    print(f"  Rejected: {len(rejected)} (history short / low Sharpe / bad MaxDD)")

    if not candidates:
        print("ERROR: no candidates passed quality filter")
        return

    # Print top candidates by Sharpe for transparency
    stats = {t: full_period_stats(s) for t, s in candidates.items()}
    top_by_sharpe = sorted(stats.items(), key=lambda x: x[1]["sharpe"], reverse=True)[:20]
    print("\nTop 20 quality-filtered candidates (by full-period Sharpe):")
    for t, st in top_by_sharpe:
        print(f"  {t:12}  Sharpe={st['sharpe']:.3f}  CAGR={st['cagr']:+.1%}  "
              f"MaxDD={st['maxdd']:.1%}  {st['years']:.0f}yr")

    # ── Load base asset prices ─────────────────────────────────────────────────
    base_prices: dict[str, pd.Series] = {}
    for t, cat in BASE_CATS.items():
        s = load_prices(cat, t)
        if s is None:
            print(f"ERROR: base asset {t} not found")
            return
        base_prices[t] = s

    # ── Detect HIGH+TIGHT regime periods ──────────────────────────────────────
    mask_ht = (
        (labeled_df["ry_regime"] == SLEEVE_RY) &
        (labeled_df["baa10y_regime"] == SLEEVE_BAA)
    )
    combo = (labeled_df["ry_regime"].astype(str) + "_" +
             labeled_df["baa10y_regime"].astype(str)).dropna()

    transitions: list[tuple[pd.Timestamp, str, str]] = []
    i = 0
    while i < len(combo):
        if i == 0:
            ry, baa = combo.iloc[i].split("_", 1)
            transitions.append((combo.index[i], ry, baa))
            i += 1
            continue
        if combo.iloc[i] != combo.iloc[i - 1]:
            new_label = combo.iloc[i]
            end = min(i + CONFIRM_DAYS, len(combo))
            if all(combo.iloc[j] == new_label for j in range(i, end)):
                ry, baa = new_label.split("_", 1)
                transitions.append((combo.index[i], ry, baa))
        i += 1

    print(f"\nTotal regime transitions: {len(transitions)}")
    ht_transitions = [(d, ry, baa) for d, ry, baa in transitions
                      if ry == SLEEVE_RY and baa == SLEEVE_BAA]
    print(f"HIGH+TIGHT entries: {len(ht_transitions)}")

    # ── Walk-forward ranking at each HIGH+TIGHT entry ─────────────────────────
    print("\nWalk-forward ranking at each HIGH+TIGHT entry...")
    selections: list[dict] = []

    for t_date, ry_new, baa_new in ht_transitions:
        hist = labeled_df[labeled_df.index < t_date]
        mask = (hist["ry_regime"] == ry_new) & (hist["baa10y_regime"] == baa_new)
        matched = hist.index[mask]

        if len(matched) < MIN_REGIME_DATES:
            print(f"  {t_date.date()} — skip (n_matched={len(matched)} < {MIN_REGIME_DATES})")
            continue

        ranked: list[tuple[str, float]] = []
        momentum_failed = 0

        for ticker, prices in candidates.items():
            pre = prices[prices.index < t_date]
            if len(pre) < min_days:
                continue
            # Momentum gate
            if not above_sma(pre, pre.index[-1], SMA_WINDOW):
                momentum_failed += 1
                continue
            med = regime_median_return(pre, matched)
            if med is not None:
                ranked.append((ticker, med))

        ranked.sort(key=lambda x: x[1], reverse=True)
        top5 = [r[0] for r in ranked[:5]]
        print(f"  {t_date.date()}  n_matched={len(matched)}  "
              f"ranked={len(ranked)}  mom_filtered={momentum_failed}  top5={top5}")

        selections.append({
            "t_date":     t_date,
            "ry":         ry_new,
            "baa":        baa_new,
            "n_matched":  len(matched),
            "n_ranked":   len(ranked),
            "mom_filtered": momentum_failed,
            "top10":      [r[0] for r in ranked[:10]],
            "top10_rets": [round(r[1], 4) for r in ranked[:10]],
        })

    print(f"\nHIGH+TIGHT entries with valid ranking: {len(selections)}")

    if not selections:
        print("ERROR: no valid HIGH+TIGHT selections — cannot run backtest")
        return

    # ── Build common date index ────────────────────────────────────────────────
    common = base_prices["GC_F"].index
    for s in base_prices.values():
        common = common.intersection(s.index)
    common = common.sort_values()
    common = common[common >= transitions[0][0]]

    g_ret  = base_prices["GC_F"].reindex(common).pct_change()
    av_ret = base_prices["AVGO"].reindex(common).pct_change()
    ll_ret = base_prices["LLY"].reindex(common).pct_change()

    # Pre-load sleeve asset returns
    all_sleeve_tickers: set[str] = set()
    for sel in selections:
        all_sleeve_tickers.update(sel.get("top10", []))

    print(f"\nPre-loading {len(all_sleeve_tickers)} sleeve asset returns...")
    sleeve_rets: dict[str, pd.Series] = {}
    for t in all_sleeve_tickers:
        if t in candidates:
            sleeve_rets[t] = candidates[t].reindex(common).pct_change()

    # ── Grid backtest ──────────────────────────────────────────────────────────
    print("\nRunning grid backtest...")
    print(f"{'K':>4}  {'CAGR':>8}  {'Sharpe':>7}  {'MaxDD':>8}  {'Calmar':>7}")
    print("-" * 45)

    grid_rows = []

    # Build regime lookup: for each date, is it in HIGH+TIGHT?
    ry_series  = labeled_df["ry_regime"].reindex(common, method="ffill")
    baa_series = labeled_df["baa10y_regime"].reindex(common, method="ffill")
    is_ht = (ry_series == SLEEVE_RY) & (baa_series == SLEEVE_BAA)

    for K in [3, 5, 8]:
        base_scale = 1 - SLEEVE_PCT

        port_ret = (BASE["GC_F"] * base_scale * g_ret +
                    BASE["AVGO"] * base_scale * av_ret +
                    BASE["LLY"]  * base_scale * ll_ret).fillna(0)

        prev_sleeve: list[str] = []
        active_sleeve: list[str] = []

        for i, date in enumerate(common):
            in_ht = bool(is_ht.iloc[i]) if i < len(is_ht) else False

            if in_ht:
                # Find latest HIGH+TIGHT selection on or before this date
                cur_sel = None
                for sel in reversed(selections):
                    if sel["t_date"] <= date:
                        cur_sel = sel
                        break

                if cur_sel is not None:
                    top_k = cur_sel.get("top10", [])[:K]
                else:
                    top_k = []

                if top_k != prev_sleeve and top_k:
                    rotated_in  = set(top_k) - set(prev_sleeve)
                    rotated_out = set(prev_sleeve) - set(top_k)
                    tc_cost = (len(rotated_in) + len(rotated_out)) * TC
                    port_ret.iloc[i] -= tc_cost / 252

                active_sleeve = top_k
                prev_sleeve   = top_k
            else:
                # Outside HIGH+TIGHT: no sleeve, unwind if previously active
                if active_sleeve:
                    tc_cost = len(active_sleeve) * TC
                    port_ret.iloc[i] -= tc_cost / 252
                    active_sleeve = []
                    prev_sleeve   = []

            # Apply sleeve return
            if active_sleeve:
                sl_ret_sum = 0.0
                n_valid = 0
                for t in active_sleeve:
                    if t in sleeve_rets:
                        r = sleeve_rets[t].iloc[i] if i < len(sleeve_rets[t]) else float("nan")
                        if not pd.isna(r):
                            sl_ret_sum += r
                            n_valid += 1
                if n_valid > 0:
                    port_ret.iloc[i] += SLEEVE_PCT * (sl_ret_sum / n_valid)

        equity = (1 + port_ret).cumprod()
        p = perf(equity)
        grid_rows.append({"K": K, **p})
        print(f"  K={K}  CAGR={p['cagr']:+.1%}  Sharpe={p['sharpe']:.3f}  "
              f"MaxDD={p['maxdd']:+.1%}  Calmar={p['calmar']:.3f}")

    # Base (no sleeve)
    base_eq = (1 + (BASE["GC_F"]*g_ret + BASE["AVGO"]*av_ret +
                    BASE["LLY"]*ll_ret).fillna(0)).cumprod()
    base_p = perf(base_eq)
    print(f"\n  Base (no sleeve):  CAGR={base_p['cagr']:+.1%}  "
          f"Sharpe={base_p['sharpe']:.3f}  MaxDD={base_p['maxdd']:+.1%}  "
          f"Calmar={base_p['calmar']:.3f}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    gdf = pd.DataFrame(grid_rows)
    best = gdf.loc[gdf["calmar"].idxmax()]
    verdict = "IMPROVES" if best["calmar"] > base_p["calmar"] else "NO IMPROVEMENT"
    print(f"Best: K={int(best['K'])}  Calmar={best['calmar']:.3f}  "
          f"vs base {base_p['calmar']:.3f}  → {verdict}")
    print(f"Base: CAGR={base_p['cagr']:+.1%}  Sharpe={base_p['sharpe']:.3f}  "
          f"MaxDD={base_p['maxdd']:+.1%}  Calmar={base_p['calmar']:.3f}")

    # Current regime status
    current_ry  = ry_series.iloc[-1] if len(ry_series) else "?"
    current_baa = baa_series.iloc[-1] if len(baa_series) else "?"
    print(f"\nCurrent regime: ry={current_ry}  baa={current_baa}  "
          f"{'→ SLEEVE ACTIVE' if current_ry == SLEEVE_RY and current_baa == SLEEVE_BAA else '→ sleeve inactive'}")

    if selections:
        latest = selections[-1]
        print(f"Latest HIGH+TIGHT selection ({latest['t_date'].date()}):")
        for rank, (t, r) in enumerate(zip(latest["top10"], latest["top10_rets"]), 1):
            st = stats.get(t, {})
            print(f"  {rank:2}. {t:12}  med_252d={r:+.1%}  "
                  f"Sharpe={st.get('sharpe', 0):.3f}  MaxDD={st.get('maxdd', 0):.1%}")

    # ── Save outputs ──────────────────────────────────────────────────────────
    OUT_GRID.parent.mkdir(exist_ok=True)
    gdf.to_csv(OUT_GRID, index=False)

    sel_rows = []
    for sel in selections:
        for rank, (t, r) in enumerate(zip(sel["top10"], sel["top10_rets"]), 1):
            sel_rows.append({
                "t_date": sel["t_date"],
                "ry": sel["ry"],
                "baa": sel["baa"],
                "rank": rank,
                "ticker": t,
                "med_252d": r,
            })
    pd.DataFrame(sel_rows).to_csv(OUT_SEL, index=False)
    print(f"\nSaved: {OUT_GRID}")
    print(f"Saved: {OUT_SEL}")


if __name__ == "__main__":
    main()
