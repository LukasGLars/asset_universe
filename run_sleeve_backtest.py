"""
Rotation Sleeve Backtest — Full Universe

Walk-forward regime-conditional sleeve on top of Gold25/AVGO55/LLY20 base.
Universe: 500+ US equities + commodities (futures as proxies).
No intl ETFs (US-listed, not available on Avanza).

Method:
  1. Build ry x baa10y regime history
  2. Find confirmed regime transitions (5-day window)
  3. At each transition: rank all assets by median 252d return in the new
     regime using ONLY pre-transition historical data (no lookahead)
  4. Select top K assets as sleeve for next regime period
  5. Grid: sleeve_pct (20-50%) x K (1-5), 10bps TC per rotation
  6. Compare Calmar vs static Gold25/AVGO55/LLY20 base

Output: console + comparison_results/sleeve_backtest.csv
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

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "sleeve_backtest.csv"

BASE      = {"GC_F": 0.25, "AVGO": 0.55, "LLY": 0.20}
BASE_CATS = {"GC_F": "commodities", "AVGO": "equities", "LLY": "equities"}
TC        = 0.0010   # 10bps per asset per rotation

# Exclude from sleeve candidates
EXCLUDE = {
    "GC_F", "AVGO", "LLY",    # in base
    "PPFB_DE", "PHAG_L",       # ETC tickers with TV data / limited history
    "SI_F",                    # silver — covered by T1/T2 tactical rule separately
}

MIN_HISTORY_DAYS  = 756   # 3 years before selecting an asset
MIN_REGIME_DATES  = 15    # minimum matched dates to compute reliable stats
CONFIRM_DAYS      = 5     # regime must persist N days to confirm transition


def load_prices(category: str, stem: str) -> pd.Series | None:
    path = DATA_DIR / category / f"{stem}.parquet"
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        s = df.set_index("date")["close"].sort_index().dropna()
        return s if len(s) > MIN_HISTORY_DAYS else None
    except Exception:
        return None


def perf(equity: pd.Series) -> dict:
    r    = equity.pct_change().dropna()
    yrs  = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = float(equity.iloc[-1] ** (1 / yrs) - 1)
    dd   = equity / equity.cummax() - 1
    maxdd  = float(dd.min())
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0
    calmar = cagr / abs(maxdd) if maxdd != 0 else 0
    return {"cagr": round(cagr, 4), "sharpe": round(sharpe, 3),
            "maxdd": round(maxdd, 4), "calmar": round(calmar, 3)}


def regime_median_return(prices: pd.Series, matched_dates: pd.DatetimeIndex,
                          fwd_days: int = 252) -> float | None:
    rets = []
    for d in matched_dates:
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


def main() -> None:
    print("Building regime labels...")
    labeled_df, _ = regime_module.build(DATA_DIR)

    # ── Load all candidate prices ─────────────────────────────────────────────
    print("Loading prices...")
    candidates: dict[str, tuple[str, pd.Series]] = {}  # ticker -> (category, prices)

    for stem in sorted((DATA_DIR / "equities").glob("*.parquet")):
        t = stem.stem
        if t in EXCLUDE:
            continue
        s = load_prices("equities", t)
        if s is not None:
            candidates[t] = ("equities", s)

    for stem in sorted((DATA_DIR / "commodities").glob("*.parquet")):
        t = stem.stem
        if t in EXCLUDE:
            continue
        s = load_prices("commodities", t)
        if s is not None:
            candidates[t] = ("commodities", s)

    print(f"Candidates loaded: {len(candidates)} "
          f"({sum(1 for c,_ in candidates.values() if c=='equities')} equities, "
          f"{sum(1 for c,_ in candidates.values() if c=='commodities')} commodities)")

    # Load base asset prices
    base_prices: dict[str, pd.Series] = {}
    for t, cat in BASE_CATS.items():
        s = load_prices(cat, t)
        if s is None:
            print(f"ERROR: base asset {t} not found")
            return
        base_prices[t] = s

    # ── Regime transition detection ───────────────────────────────────────────
    combo = (labeled_df["ry_regime"].astype(str) + "_" +
             labeled_df["baa10y_regime"].astype(str))
    combo = combo.dropna()

    transitions: list[tuple[pd.Timestamp, str, str]] = []
    i = 0
    while i < len(combo):
        if i == 0:
            label = combo.iloc[i]
            ry, baa = label.split("_", 1)
            transitions.append((combo.index[i], ry, baa))
            i += 1
            continue
        if combo.iloc[i] != combo.iloc[i - 1]:
            new_label = combo.iloc[i]
            # Confirm: must persist CONFIRM_DAYS
            end = min(i + CONFIRM_DAYS, len(combo))
            if all(combo.iloc[j] == new_label for j in range(i, end)):
                ry, baa = new_label.split("_", 1)
                transitions.append((combo.index[i], ry, baa))
        i += 1

    print(f"Regime transitions detected: {len(transitions)}")

    # ── Walk-forward ranking at each transition ───────────────────────────────
    print("Running walk-forward ranking...")
    transition_selections: list[dict] = []

    for t_idx, (t_date, ry_new, baa_new) in enumerate(transitions):
        # Historical matched dates: pre-transition, matching new regime
        hist = labeled_df[labeled_df.index < t_date]
        mask = (hist["ry_regime"] == ry_new) & (hist["baa10y_regime"] == baa_new)
        matched = hist.index[mask]

        if len(matched) < MIN_REGIME_DATES:
            # Not enough history for new regime — hold previous selection
            if transition_selections:
                prev = transition_selections[-1].copy()
                prev["t_date"] = t_date
                transition_selections.append(prev)
            continue

        # Rank candidates available at t_date
        ranked: list[tuple[str, float]] = []
        for ticker, (cat, prices) in candidates.items():
            # Must have MIN_HISTORY_DAYS of data before t_date
            pre_prices = prices[prices.index < t_date]
            if len(pre_prices) < MIN_HISTORY_DAYS:
                continue
            med = regime_median_return(pre_prices, matched)
            if med is not None:
                ranked.append((ticker, med))

        ranked.sort(key=lambda x: x[1], reverse=True)
        transition_selections.append({
            "t_date":     t_date,
            "ry":         ry_new,
            "baa":        baa_new,
            "n_matched":  len(matched),
            "n_ranked":   len(ranked),
            "top10":      [r[0] for r in ranked[:10]],
            "top10_rets": [round(r[1], 4) for r in ranked[:10]],
        })

        if t_idx % 20 == 0:
            top3 = [r[0] for r in ranked[:3]]
            print(f"  [{t_idx+1}/{len(transitions)}] {t_date.date()} "
                  f"ry={ry_new} baa={baa_new}  n_matched={len(matched)}  "
                  f"top3={top3}")

    # ── Grid backtest ─────────────────────────────────────────────────────────
    print("\nRunning grid backtest...")

    # Build common date index from base assets
    common = base_prices["GC_F"].index
    for s in base_prices.values():
        common = common.intersection(s.index)
    common = common.sort_values()
    common = common[common >= transitions[0][0]]

    # Align base prices
    g_ret  = base_prices["GC_F"].reindex(common).pct_change()
    av_ret = base_prices["AVGO"].reindex(common).pct_change()
    ll_ret = base_prices["LLY"].reindex(common).pct_change()

    # Pre-load sleeve asset returns (only assets that appear in any top-10)
    all_sleeve_tickers = set()
    for sel in transition_selections:
        all_sleeve_tickers.update(sel.get("top10", []))

    print(f"Pre-loading {len(all_sleeve_tickers)} sleeve asset returns...")
    sleeve_rets: dict[str, pd.Series] = {}
    for t in all_sleeve_tickers:
        if t not in candidates:
            continue
        cat, prices = candidates[t]
        ret = prices.reindex(common).pct_change()
        sleeve_rets[t] = ret

    grid_rows = []

    for sleeve_pct in [0.20, 0.25, 0.30, 0.35, 0.40, 0.50]:
        for K in [1, 2, 3, 4, 5]:
            base_scale = 1 - sleeve_pct

            port_ret = (BASE["GC_F"] * base_scale * g_ret +
                        BASE["AVGO"] * base_scale * av_ret +
                        BASE["LLY"]  * base_scale * ll_ret).fillna(0)

            prev_sleeve: list[str] = []

            for i, date in enumerate(common):
                # Find current selection: last transition on or before this date
                cur_sel = None
                for sel in reversed(transition_selections):
                    if sel["t_date"] <= date:
                        cur_sel = sel
                        break
                if cur_sel is None:
                    continue

                top_k = cur_sel.get("top10", [])[:K]
                if not top_k:
                    continue

                # TC on rotation
                rotated_in  = set(top_k) - set(prev_sleeve)
                rotated_out = set(prev_sleeve) - set(top_k)
                tc_cost     = (len(rotated_in) + len(rotated_out)) * TC

                # Sleeve return (equal weight among top K)
                sl_ret_sum = 0.0
                n_valid = 0
                for t in top_k:
                    if t in sleeve_rets:
                        r = sleeve_rets[t].iloc[i] if i < len(sleeve_rets[t]) else float("nan")
                        if not pd.isna(r):
                            sl_ret_sum += r
                            n_valid += 1
                if n_valid > 0:
                    sl_ret_mean = sl_ret_sum / n_valid
                    port_ret.iloc[i] += sleeve_pct * sl_ret_mean - tc_cost / 252

                prev_sleeve = top_k

            equity = (1 + port_ret).cumprod()
            p = perf(equity)
            grid_rows.append({
                "sleeve_pct": sleeve_pct,
                "K":          K,
                **p,
            })
            print(f"  sleeve={sleeve_pct:.0%}  K={K}  "
                  f"CAGR={p['cagr']:+.1%}  Sharpe={p['sharpe']:.3f}  "
                  f"MaxDD={p['maxdd']:+.1%}  Calmar={p['calmar']:.3f}")

    # Base performance
    base_eq = (1 + (BASE["GC_F"]*g_ret + BASE["AVGO"]*av_ret +
                    BASE["LLY"]*ll_ret).fillna(0)).cumprod()
    base_p  = perf(base_eq)
    print(f"\n  Base (no sleeve):  "
          f"CAGR={base_p['cagr']:+.1%}  Sharpe={base_p['sharpe']:.3f}  "
          f"MaxDD={base_p['maxdd']:+.1%}  Calmar={base_p['calmar']:.3f}")

    gdf = pd.DataFrame(grid_rows)
    best = gdf.loc[gdf["calmar"].idxmax()]
    print(f"\n>>> BEST: sleeve={best['sleeve_pct']:.0%}  K={int(best['K'])}  "
          f"Calmar={best['calmar']:.3f}  vs base {base_p['calmar']:.3f}  "
          f"({'IMPROVES' if best['calmar'] > base_p['calmar'] else 'NO IMPROVEMENT'})")

    # ── Today's ranking ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("TODAY'S REGIME RANKING (current regime selection)")
    print("=" * 80)
    if transition_selections:
        latest = transition_selections[-1]
        print(f"Regime: ry={latest['ry']}  baa={latest['baa']}  "
              f"n_matched={latest['n_matched']}  n_ranked={latest['n_ranked']}")
        print(f"Top 10 assets for current regime:")
        for rank, (t, r) in enumerate(zip(latest["top10"], latest["top10_rets"]), 1):
            cat = candidates[t][0] if t in candidates else "?"
            print(f"  {rank:2}. {t:12} ({cat:12})  med_252d={r:+.1%}")

    OUT_CSV.parent.mkdir(exist_ok=True)
    gdf.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")


if __name__ == "__main__":
    main()
