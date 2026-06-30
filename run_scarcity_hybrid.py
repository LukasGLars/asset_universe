"""
run_scarcity_hybrid.py

Scarcity Hybrid portfolio:
  BASE  (fixed): Gold, AVGO, LLY — optimized weights (25/55/20 of base allocation)
  SLEEVE (rotating): VRT, Silver, CCJ — walk-forward regime selection

Grid: sleeve_pct (20/30/40/50%) × n_sleeve (1/2/3 assets) = 12 combinations.
10bps TC on turnover. AVGO pre-IPO 2009, VRT pre-IPO 2018 → weight redistributed.
"""
from __future__ import annotations

import io, sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.analysis.engine import _regime_end_dates
from asset_universe.store import reader

START_DATE    = "2004-01-01"
TC_BPS        = 10
REBAL_TRIGGER = 0.05
CONFIRM_DAYS  = 3
MIN_DATES     = 5

PRE_IPO = {
    "AVGO": pd.Timestamp("2009-08-06"),
    "VRT":  pd.Timestamp("2018-08-02"),
}

# Base weights (within base allocation)
BASE_W = {"Gold": 0.25, "AVGO": 0.55, "LLY": 0.20}

# Sleeve candidates
SLEEVE_ASSETS = ["VRT", "Silver", "CCJ"]

ASSET_PATHS = {
    "Gold":   ("commodities", "GC_F"),
    "Silver": ("commodities", "SI_F"),
    "AVGO":   ("equities",    "AVGO"),
    "LLY":    ("equities",    "LLY"),
    "VRT":    ("equities",    "VRT"),
    "CCJ":    ("equities",    "CCJ"),
    "SPY":    ("equities",    "SPY"),
}


# ── Data ──────────────────────────────────────────────────────────────────────

def load_prices(data_dir: Path) -> pd.DataFrame:
    series = {}
    for name, (cat, safe) in ASSET_PATHS.items():
        path = reader.ticker_path(data_dir, cat, safe)
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        series[name] = df.set_index("date")["close"].sort_index()
    return pd.DataFrame(series).sort_index().loc[START_DATE:].ffill(limit=3)


# ── Regime transitions ────────────────────────────────────────────────────────

def get_transitions(labeled_df: pd.DataFrame) -> list[tuple]:
    out, prev_ry, prev_baa = [], None, None
    for date, row in labeled_df[["ry_regime", "baa10y_regime"]].iterrows():
        ry, baa = row["ry_regime"], row["baa10y_regime"]
        if pd.isna(ry) or pd.isna(baa):
            continue
        if prev_ry is None:
            out.append((date, ry, baa)); prev_ry, prev_baa = ry, baa; continue
        if ry != prev_ry or baa != prev_baa:
            end = date + pd.Timedelta(days=CONFIRM_DAYS)
            fut = labeled_df.loc[date:end, ["ry_regime", "baa10y_regime"]]
            if (len(fut) >= 2
                    and (fut["ry_regime"] == ry).all()
                    and (fut["baa10y_regime"] == baa).all()):
                out.append((date, ry, baa)); prev_ry, prev_baa = ry, baa
    return out


# ── Walk-forward sleeve selection ─────────────────────────────────────────────

def select_sleeve(
    labeled_df: pd.DataFrame,
    prices: pd.DataFrame,
    before: pd.Timestamp,
    ry: str,
    baa: str,
    n: int,
) -> list[str]:
    cond = {"ry_regime": ry, "baa10y_regime": baa}
    hist  = labeled_df[labeled_df.index < before]
    mask  = pd.Series(True, index=hist.index)
    for k, v in cond.items():
        mask &= hist[k] == v
    matched = hist.index[mask]

    if len(matched) < MIN_DATES:
        return SLEEVE_ASSETS[:n]

    ends = _regime_end_dates(hist, cond, matched)
    rows = []

    for tkr in SLEEVE_ASSETS:
        if tkr not in prices.columns:
            continue
        p = prices[tkr]
        rets = []
        for dt in matched:
            idx = p.index.searchsorted(dt)
            if idx >= len(p) or abs((p.index[idx] - dt).days) > 5:
                continue
            fwd = idx + 252
            end_dt = ends.get(dt)
            if end_dt is not None:
                fwd = min(fwd, p.index.searchsorted(end_dt))
            if fwd >= len(p) or fwd <= idx:
                continue
            p0, p1 = p.iloc[idx], p.iloc[fwd]
            if p0 > 0:
                rets.append((p1 - p0) / p0)
        if len(rets) >= MIN_DATES:
            rows.append((tkr, float(np.median(rets))))

    if not rows:
        return SLEEVE_ASSETS[:n]

    rows.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in rows[:n]]


# ── Effective weights (pre-IPO redistribution) ────────────────────────────────

def eff_w(w: dict[str, float], date: pd.Timestamp) -> dict[str, float]:
    out = dict(w)
    for tkr, ipo in PRE_IPO.items():
        if tkr in out and date < ipo:
            dropped = out.pop(tkr)
            s = sum(out.values())
            if s > 0:
                out = {k: v / s * (s + dropped) for k, v in out.items()}
    s = sum(out.values())
    return {k: v / s for k, v in out.items()} if s > 0 else out


def tc(old: dict, new: dict) -> float:
    all_t    = set(old) | set(new)
    turnover = sum(abs(new.get(t, 0) - old.get(t, 0)) for t in all_t) / 2
    return turnover * TC_BPS / 10_000


def daily_ret(prices: pd.DataFrame, i: int, w: dict) -> float:
    ret = 0.0
    for tkr, wt in w.items():
        if tkr in prices.columns:
            p0, p1 = prices[tkr].iloc[i - 1], prices[tkr].iloc[i]
            if pd.notna(p0) and pd.notna(p1) and p0 > 0:
                ret += wt * (p1 - p0) / p0
    return ret


# ── Simulate ──────────────────────────────────────────────────────────────────

def simulate(
    prices: pd.DataFrame,
    labeled_df: pd.DataFrame,
    transitions: list[tuple],
    sleeve_pct: float,
    n_sleeve: int,
) -> tuple[pd.Series, list[dict]]:
    base_pct = 1.0 - sleeve_pct
    nav, nav_out, sel_log = 1.0, {}, []
    prev_h: dict[str, float] = {}

    for idx, (trans_date, ry, baa) in enumerate(transitions):
        next_date = (transitions[idx + 1][0]
                     if idx + 1 < len(transitions) else prices.index[-1])

        selected = select_sleeve(labeled_df, prices, trans_date, ry, baa, n_sleeve)
        sleeve_w = sleeve_pct / len(selected) if selected else 0.0

        new_h = {tkr: BASE_W[tkr] * base_pct for tkr in BASE_W}
        for tkr in selected:
            new_h[tkr] = new_h.get(tkr, 0.0) + sleeve_w

        sel_log.append({
            "date": trans_date.date(), "ry": ry, "baa": baa,
            "sleeve": ", ".join(selected),
        })

        nav *= (1 - tc(prev_h, new_h))

        period = prices.loc[trans_date:next_date]
        for i in range(1, len(period)):
            w_day = eff_w(new_h, period.index[i])
            nav  *= (1 + daily_ret(period, i, w_day))
            nav_out[period.index[i]] = nav

        prev_h = new_h

    return pd.Series(nav_out).sort_index(), sel_log


# ── Metrics ───────────────────────────────────────────────────────────────────

def metrics(nav: pd.Series) -> dict:
    nav  = nav.dropna()
    rets = nav.pct_change().dropna()
    yrs  = (nav.index[-1] - nav.index[0]).days / 365.25
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1
    vol  = rets.std() * np.sqrt(252)
    sh   = rets.mean() * 252 / vol if vol > 0 else 0.0
    peak = nav.expanding().max()
    mdd  = ((nav - peak) / peak).min()
    cal  = cagr / abs(mdd) if mdd < 0 else 0.0
    return {"cagr": cagr, "vol": vol, "sharpe": sh, "mdd": mdd, "calmar": cal}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    data_dir = config.raw_data_dir()

    print("Building regime labels...")
    labeled_df, _ = regime_module.build(data_dir)
    labeled_df = labeled_df.loc[START_DATE:]

    print("Loading prices...")
    prices = load_prices(data_dir)
    common = labeled_df.index.intersection(prices.index)
    prices     = prices.reindex(common).ffill(limit=3)
    labeled_df = labeled_df.reindex(common)

    print("Computing transitions...")
    transitions = get_transitions(labeled_df)
    print(f"  {len(transitions)} transitions")

    # SPY benchmark
    spy = prices["SPY"].dropna()
    spy_nav = spy / spy.iloc[0]
    spy_m   = metrics(spy_nav)

    # Pure base (no sleeve) — 100% base allocation
    print("\nSimulating pure base (no sleeve)...")
    base_nav, _ = simulate(prices, labeled_df, transitions, sleeve_pct=0.0, n_sleeve=1)
    base_m       = metrics(base_nav)

    # Grid
    sleeve_pcts = [0.20, 0.30, 0.40, 0.50]
    n_sleeves   = [1, 2, 3]

    print("Running grid (12 combinations)...")
    grid_rows = []
    grid_navs: dict[str, pd.Series] = {}

    for sp in sleeve_pcts:
        for ns in n_sleeves:
            nav, log = simulate(prices, labeled_df, transitions, sp, ns)
            m   = metrics(nav)
            lbl = f"Base{round((1-sp)*100)}%+Rot{round(sp*100)}%(n={ns})"
            grid_rows.append({"label": lbl, "sleeve_pct": sp, "n_sleeve": ns, **m})
            grid_navs[lbl] = nav

    df = pd.DataFrame(grid_rows)

    # ── Print grid ────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print(f"SCARCITY HYBRID GRID  (Base: Gold25/AVGO55/LLY20 | Sleeve: VRT/Silver/CCJ)")
    print("=" * 80)
    print(f"  {'Strategy':<32}  {'CAGR':>7}  {'Sharpe':>7}  {'MaxDD':>8}  {'Calmar':>7}")
    print("  " + "-" * 68)

    for _, r in df.iterrows():
        print(f"  {r['label']:<32}  {r['cagr']:>7.2%}  {r['sharpe']:>7.3f}"
              f"  {r['mdd']:>8.2%}  {r['calmar']:>7.3f}")

    print(f"\n  {'--- Benchmarks ---':<32}")
    print(f"  {'Pure Base (Gold25/AVGO55/LLY20)':<32}  {base_m['cagr']:>7.2%}  "
          f"{base_m['sharpe']:>7.3f}  {base_m['mdd']:>8.2%}  {base_m['calmar']:>7.3f}")
    print(f"  {'SPY':<32}  {spy_m['cagr']:>7.2%}  "
          f"{spy_m['sharpe']:>7.3f}  {spy_m['mdd']:>8.2%}  {spy_m['calmar']:>7.3f}")

    # Best by each metric
    best_cagr   = df.loc[df["cagr"].idxmax()]
    best_sharpe = df.loc[df["sharpe"].idxmax()]
    best_calmar = df.loc[df["calmar"].idxmax()]

    print(f"\n  Best CAGR:   {best_cagr['label']}  →  {best_cagr['cagr']:.2%}")
    print(f"  Best Sharpe: {best_sharpe['label']}  →  {best_sharpe['sharpe']:.3f}")
    print(f"  Best Calmar: {best_calmar['label']}  →  {best_calmar['calmar']:.3f}")

    # ── Year-by-year for top 3 + base + SPY ──────────────────────────────────
    show = {
        best_cagr["label"]:   grid_navs[best_cagr["label"]],
        best_sharpe["label"]: grid_navs[best_sharpe["label"]],
        best_calmar["label"]: grid_navs[best_calmar["label"]],
        "Pure Base":          base_nav,
        "SPY":                spy_nav.reindex(prices.index).ffill(),
    }
    # Deduplicate if same label appears twice
    show = dict(dict.fromkeys(show.keys(), None) | show)

    yr     = {k: v.resample("YE").last().pct_change().dropna() for k, v in show.items()}
    labels = list(show.keys())
    yrs    = sorted({d.year for s in yr.values() for d in s.index})

    print(f"\n{'='*80}")
    print("YEAR-BY-YEAR")
    print(f"{'='*80}")
    col = 16
    print(f"  {'Year':<5}" + "".join(f"  {l:>{col}}" for l in labels))
    print(f"  {'-'*95}")
    for y in yrs:
        row = f"  {y:<5}"
        for lbl in labels:
            r = {d.year: v for d, v in yr[lbl].items()}.get(y)
            row += f"  {r:>{col}.2%}" if r is not None else f"  {'n/a':>{col}}"
        print(row)

    # ── Sleeve selection log for best Calmar ─────────────────────────────────
    _, best_log = simulate(
        prices, labeled_df, transitions,
        best_calmar["sleeve_pct"], int(best_calmar["n_sleeve"])
    )
    log_df = pd.DataFrame(best_log)

    print(f"\n{'='*80}")
    print(f"SLEEVE SELECTIONS — {best_calmar['label']}")
    print(f"{'='*80}")
    freq = log_df["sleeve"].str.split(", ").explode().value_counts()
    print("  Asset frequency in sleeve:")
    for asset, cnt in freq.items():
        print(f"    {asset:<10} {cnt:>4}x  ({cnt/len(log_df)*100:.0f}% of transitions)")

    print(f"\n  Last 10 transitions:")
    for _, r in log_df.tail(10).iterrows():
        print(f"    {r['date']}  {r['ry']:<4}|{r['baa']:<6}  → {r['sleeve']}")

    # Save
    out = PROJECT_ROOT / "comparison_results"
    out.mkdir(exist_ok=True)
    df.to_csv(out / "scarcity_hybrid_grid.csv", index=False)
    pd.DataFrame(grid_navs).to_csv(out / "scarcity_hybrid_curves.csv")
    print(f"\nSaved to comparison_results/")
    print("=" * 80)


if __name__ == "__main__":
    main()
