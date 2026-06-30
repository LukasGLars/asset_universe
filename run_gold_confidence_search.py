"""
Gold Overweight Confidence Search

Exhaustive search for signals that confidently predict gold outperformance.
No thesis — any signal qualifies if the data supports it.

Signals tested:
  A. Macro regime conditions (from labeled_df)
  B. Gold own price state — momentum drawdown from N-day high
  C. Gold momentum (21d, 63d) x macro regime combos
  D. GSR (Gold-Silver Ratio) level as gold trigger
  E. Real yield level (current regime label) x gold drawdown

Confidence criteria (ranked):
  - Win rate >= 80% at 63d or 252d
  - N >= 25
  - Lift above unconditional baseline
  - ROBUST or MODERATE temporal diversity preferred

Output: ranked table by confidence score + gold_confidence_search.csv
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.store import reader

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "gold_confidence_search.csv"

HORIZONS  = [21, 63, 252]
MIN_N     = 25

MACRO_FEATURES = [
    "ry", "nominal_10y", "breakeven",
    "baa10y", "hy_oas",
    "t10y3m", "t10y2y",
    "se_10y", "usd",
]

# Current regime (for flagging active signals)
CURRENT_REGIME = {
    "ry_regime":          "HIGH",
    "nominal_10y_regime": "HIGH",
    "breakeven_regime":   "MID",
    "baa10y_regime":      "TIGHT",
    "hy_oas_regime":      "TIGHT",
    "t10y3m_regime":      "LOW",
    "t10y2y_regime":      "LOW",
    "se_10y_regime":      "MID",
    "usd_regime":         "STRONG",
}


def load_series(category: str, ticker: str) -> pd.Series:
    path = reader.ticker_path(DATA_DIR, category, ticker)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index()


def fwd_return(prices: pd.Series, date: pd.Timestamp, days: int) -> float | None:
    idx = prices.index.searchsorted(date)
    if idx >= len(prices) or abs((prices.index[idx] - date).days) > 5:
        return None
    end = idx + days
    if end >= len(prices):
        return None
    p0, p1 = prices.iloc[idx], prices.iloc[end]
    return (p1 - p0) / p0 if p0 > 0 else None


def stats_for(prices: pd.Series, dates: pd.DatetimeIndex) -> dict:
    out = {}
    for h in HORIZONS:
        rets = [r for d in dates if (r := fwd_return(prices, d, h)) is not None]
        if not rets:
            out[h] = {"n": 0, "median": float("nan"), "wr": float("nan")}
            continue
        s = pd.Series(rets)
        out[h] = {
            "n":      len(s),
            "median": round(float(s.median()), 4),
            "wr":     round(float((s > 0).mean()), 4),
            "p25":    round(float(s.quantile(0.25)), 4),
            "p75":    round(float(s.quantile(0.75)), 4),
        }
    return out


def diversity(dates: pd.DatetimeIndex) -> str:
    if len(dates) < 2:
        return "THIN"
    span = (dates[-1] - dates[0]).days / 365.25
    pct3 = float((dates >= dates[-1] - pd.DateOffset(years=3)).mean())
    if span >= 10 and pct3 < 0.50:
        return "ROBUST"
    if span < 5 or pct3 > 0.80:
        return "THIN"
    return "MODERATE"


def make_row(label: str, signal_type: str, stats: dict, baseline: dict,
             dates: pd.DatetimeIndex, active: bool) -> dict:
    r = {
        "signal":    label,
        "type":      signal_type,
        "active":    active,
        "diversity": diversity(dates),
    }
    for h in HORIZONS:
        s, b = stats[h], baseline[h]
        r[f"n_{h}d"]    = s["n"]
        r[f"med_{h}d"]  = s["median"]
        r[f"wr_{h}d"]   = s["wr"]
        r[f"lift_{h}d"] = (
            round(s["median"] - b["median"], 4)
            if s["n"] > 0 and not pd.isna(s["median"])
            else float("nan")
        )
    # Confidence score: wr_63d * 0.4 + wr_252d * 0.4 + lift_63d_normalised * 0.2
    wr63  = s["wr"] if not pd.isna(r["wr_63d"]) else 0
    wr252 = r["wr_252d"] if not pd.isna(r["wr_252d"]) else 0
    lift  = r["lift_63d"] if not pd.isna(r["lift_63d"]) else 0
    r["confidence"] = round(
        r["wr_63d"] * 0.40 + r["wr_252d"] * 0.40 + min(lift, 0.30) * 0.667,
        4,
    ) if r["n_63d"] >= MIN_N else 0.0
    return r


def main() -> None:
    print("Building regime labels...")
    labeled_df, _ = regime_module.build(DATA_DIR)

    gold = load_series("commodities", "GC_F")
    silver = load_series("commodities", "SI_F")

    # ── Unconditional baseline ─────────────────────────────────────────────────
    baseline = stats_for(gold, labeled_df.index)
    print("Unconditional baseline:")
    for h in HORIZONS:
        b = baseline[h]
        print(f"  {h}d  n={b['n']}  median={b['median']:+.1%}  wr={b['wr']:.0%}")
    print()

    rows: list[dict] = []

    # ── A: Macro single conditions ────────────────────────────────────────────
    print("A: macro single conditions...")
    for feat in MACRO_FEATURES:
        col = f"{feat}_regime"
        if col not in labeled_df.columns:
            continue
        for level in labeled_df[col].dropna().unique():
            dates = labeled_df.index[labeled_df[col] == level]
            s = stats_for(gold, dates)
            if s[63]["n"] < MIN_N:
                continue
            active = CURRENT_REGIME.get(col) == level
            rows.append(make_row(f"{feat}={level}", "macro_single", s, baseline, dates, active))

    # ── B: Gold drawdown from N-day high ──────────────────────────────────────
    print("B: gold drawdown from N-day high...")
    for lookback in [20, 40, 60, 120]:
        rolling_high = gold.rolling(lookback, min_periods=lookback // 2).max()
        drawdown     = (gold / rolling_high - 1).dropna()

        # Bin into tertiles
        p33 = float(drawdown.quantile(0.333))
        p67 = float(drawdown.quantile(0.667))

        current_dd = float(drawdown.iloc[-1])
        for label, mask in [
            ("DEEP",  drawdown <= p33),
            ("MID",   (drawdown > p33) & (drawdown <= p67)),
            ("SMALL", drawdown > p67),
        ]:
            dates = drawdown.index[mask]
            dates = dates[dates.isin(labeled_df.index)]
            s = stats_for(gold, dates)
            if s[63]["n"] < MIN_N:
                continue
            if label == "DEEP":
                active = current_dd <= p33
            elif label == "MID":
                active = p33 < current_dd <= p67
            else:
                active = current_dd > p67
            rows.append(make_row(
                f"gold_dd_{lookback}d={label}  (p33={p33:.1%} p67={p67:.1%})",
                "drawdown", s, baseline, dates, active,
            ))

    # ── C: Macro x gold momentum combos ──────────────────────────────────────
    print("C: macro x gold momentum...")
    # Gold 21d and 63d momentum, binned into tertiles
    for mom_days in [21, 63]:
        mom = gold.pct_change(mom_days).dropna()
        p33m = float(mom.quantile(0.333))
        p67m = float(mom.quantile(0.667))
        current_mom = float(mom.iloc[-1])

        for mom_label, mom_mask in [
            ("LOW",  mom <= p33m),
            ("MID",  (mom > p33m) & (mom <= p67m)),
            ("HIGH", mom > p67m),
        ]:
            mom_dates = mom.index[mom_mask]

            # Cross with each macro condition
            for feat in ["ry", "baa10y", "hy_oas"]:
                col = f"{feat}_regime"
                if col not in labeled_df.columns:
                    continue
                for level in labeled_df[col].dropna().unique():
                    macro_dates = labeled_df.index[labeled_df[col] == level]
                    combo_dates = mom_dates[mom_dates.isin(macro_dates)]
                    s = stats_for(gold, combo_dates)
                    if s[63]["n"] < MIN_N:
                        continue
                    if mom_label == "LOW":
                        mom_active = current_mom <= p33m
                    elif mom_label == "MID":
                        mom_active = p33m < current_mom <= p67m
                    else:
                        mom_active = current_mom > p67m
                    macro_active = CURRENT_REGIME.get(col) == level
                    active = mom_active and macro_active
                    rows.append(make_row(
                        f"gold_mom{mom_days}d={mom_label} + {feat}={level}",
                        "macro_x_momentum", s, baseline, combo_dates, active,
                    ))

    # ── D: GSR level as gold trigger ──────────────────────────────────────────
    print("D: GSR level as gold trigger...")
    # Align on common dates
    common = gold.index.intersection(silver.index)
    gsr    = (gold.reindex(common) / silver.reindex(common)).dropna()
    gsr.name = "GSR"

    # Compute tertile thresholds on full history
    p33g = float(gsr.quantile(0.333))
    p67g = float(gsr.quantile(0.667))
    # Also test known GSR extremes (p85, p90 from signal audit: 83.36, 86.45)
    p85g = float(gsr.quantile(0.85))
    p90g = float(gsr.quantile(0.90))

    current_gsr = float(gsr.iloc[-1])
    print(f"   Current GSR: {current_gsr:.1f}  (p33={p33g:.1f} p67={p67g:.1f} p85={p85g:.1f} p90={p90g:.1f})")

    for label, mask in [
        ("LOW (gold cheap vs silver)",  gsr <= p33g),
        ("MID",                          (gsr > p33g) & (gsr <= p67g)),
        ("HIGH (gold dear vs silver)",   gsr > p67g),
        ("p85+ (GSR extreme high)",      gsr >= p85g),
        ("p90+ (GSR extreme high)",      gsr >= p90g),
    ]:
        dates = gsr.index[mask]
        dates = dates[dates.isin(labeled_df.index)]
        s = stats_for(gold, dates)
        if s[63]["n"] < MIN_N:
            continue
        active = (label == "LOW (gold cheap vs silver)" and current_gsr <= p33g) or \
                 (label == "MID" and p33g < current_gsr <= p67g) or \
                 (label == "HIGH (gold dear vs silver)" and current_gsr > p67g) or \
                 (label == "p85+ (GSR extreme high)" and current_gsr >= p85g) or \
                 (label == "p90+ (GSR extreme high)" and current_gsr >= p90g)
        rows.append(make_row(f"GSR={label}", "gsr", s, baseline, dates, active))

    # ── E: Macro x gold drawdown ──────────────────────────────────────────────
    print("E: macro x gold drawdown...")
    dd60 = (gold / gold.rolling(60, min_periods=30).max() - 1).dropna()
    p33d = float(dd60.quantile(0.333))
    p67d = float(dd60.quantile(0.667))
    current_dd60 = float(dd60.iloc[-1])

    for dd_label, dd_mask in [
        ("DEEP", dd60 <= p33d),
        ("MID",  (dd60 > p33d) & (dd60 <= p67d)),
    ]:
        dd_dates = dd60.index[dd_mask]
        for feat in ["ry", "baa10y", "hy_oas"]:
            col = f"{feat}_regime"
            if col not in labeled_df.columns:
                continue
            for level in labeled_df[col].dropna().unique():
                macro_dates = labeled_df.index[labeled_df[col] == level]
                combo_dates = dd_dates[dd_dates.isin(macro_dates)]
                s = stats_for(gold, combo_dates)
                if s[63]["n"] < MIN_N:
                    continue
                if dd_label == "DEEP":
                    dd_active = current_dd60 <= p33d
                else:
                    dd_active = p33d < current_dd60 <= p67d
                macro_active = CURRENT_REGIME.get(col) == level
                active = dd_active and macro_active
                rows.append(make_row(
                    f"gold_dd60={dd_label} + {feat}={level}",
                    "macro_x_drawdown", s, baseline, combo_dates, active,
                ))

    # ── Results ───────────────────────────────────────────────────────────────
    df = pd.DataFrame(rows).drop_duplicates(subset=["signal"])
    df = df.sort_values("confidence", ascending=False).reset_index(drop=True)

    COLS = ["signal", "type", "active", "diversity",
            "n_63d", "med_63d", "wr_63d", "lift_63d",
            "n_252d", "med_252d", "wr_252d", "lift_252d",
            "confidence"]

    print()
    print("=" * 110)
    print("TOP 30 SIGNALS BY CONFIDENCE SCORE (wr_63d*0.4 + wr_252d*0.4 + lift_63d*0.2)")
    print(f"Baseline: 63d median={baseline[63]['median']:+.1%}  wr={baseline[63]['wr']:.0%} | "
          f"252d median={baseline[252]['median']:+.1%}  wr={baseline[252]['wr']:.0%}")
    print("=" * 110)
    print(df[COLS].head(30).to_string(index=True))

    print()
    print("=" * 110)
    print("CURRENTLY ACTIVE SIGNALS")
    print("=" * 110)
    active_df = df[df["active"]].reset_index(drop=True)
    if not active_df.empty:
        print(active_df[COLS].to_string(index=False))
    else:
        print("  None active.")

    print()
    print("=" * 110)
    print("HIGH-CONFIDENCE SIGNALS (wr_252d >= 0.90 AND n_252d >= 25 AND diversity != THIN)")
    print("=" * 110)
    hc = df[
        (df["wr_252d"] >= 0.90) &
        (df["n_252d"]  >= 25) &
        (df["diversity"] != "THIN")
    ].reset_index(drop=True)
    if not hc.empty:
        print(hc[COLS].to_string(index=False))
    else:
        print("  No signals meet all three criteria.")

    print()
    print("=" * 110)
    print("ACTIVE + HIGH CONFIDENCE")
    print("=" * 110)
    both = df[
        df["active"] &
        (df["wr_252d"] >= 0.85) &
        (df["n_252d"]  >= 25)
    ].reset_index(drop=True)
    if not both.empty:
        print(both[COLS].to_string(index=False))
    else:
        print("  None.")

    OUT_CSV.parent.mkdir(exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")


if __name__ == "__main__":
    main()
