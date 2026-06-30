"""
run_base_optimizer.py

Grid search over all weight combinations for the scarcity base:
Gold, AVGO, LLY.

Tests every combination at 5% steps (231 portfolios).
Simulates 2004-present with ±5pp drift rebalance, 10bps TC.
AVGO pre-IPO (2009-08-06): weight redistributes to Gold + LLY.

Outputs: best by CAGR, Sharpe, Calmar. Pareto frontier.
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
from asset_universe.store import reader

START_DATE    = "2004-01-01"
TC_BPS        = 10
REBAL_TRIGGER = 0.05
AVGO_IPO      = pd.Timestamp("2009-08-06")

ASSETS = {
    "Gold": ("commodities", "GC_F"),
    "AVGO": ("equities",    "AVGO"),
    "LLY":  ("equities",    "LLY"),
}


# ── Data ──────────────────────────────────────────────────────────────────────

def load_prices(data_dir: Path) -> pd.DataFrame:
    series = {}
    for name, (cat, safe) in ASSETS.items():
        path = reader.ticker_path(data_dir, cat, safe)
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        series[name] = df.set_index("date")["close"].sort_index()
    df = pd.DataFrame(series).sort_index().loc[START_DATE:]
    df = df.ffill(limit=3)
    return df


# ── Simulation ────────────────────────────────────────────────────────────────

def eff_weights(w: dict[str, float], date: pd.Timestamp) -> dict[str, float]:
    """Redistribute AVGO weight to Gold+LLY (proportional) before IPO."""
    if date >= AVGO_IPO:
        return w
    avgo_w = w.get("AVGO", 0.0)
    if avgo_w == 0:
        return w
    remaining = {k: v for k, v in w.items() if k != "AVGO"}
    s = sum(remaining.values())
    if s <= 0:
        return remaining
    return {k: v / s * (1 - avgo_w) + (v / s * avgo_w) for k, v in remaining.items()}


def simulate(prices: pd.DataFrame, target_w: dict[str, float]) -> pd.Series:
    nav = 1.0
    nav_out: list[float] = []
    w_cur: dict[str, float] = {}

    for i, date in enumerate(prices.index):
        w_tgt = eff_weights(target_w, date)

        if not w_cur:
            w_cur = dict(w_tgt)
            nav_out.append(nav)
            continue

        # Daily return
        ret = 0.0
        for tkr, wt in w_cur.items():
            p0 = prices[tkr].iloc[i - 1]
            p1 = prices[tkr].iloc[i]
            if pd.notna(p0) and pd.notna(p1) and p0 > 0:
                ret += wt * (p1 - p0) / p0
        nav *= (1 + ret)

        # Drift weights forward
        w_new = {}
        for tkr, wt in w_cur.items():
            p0 = prices[tkr].iloc[i - 1]
            p1 = prices[tkr].iloc[i]
            if pd.notna(p0) and pd.notna(p1) and p0 > 0:
                w_new[tkr] = wt * (1 + (p1 - p0) / p0)
            else:
                w_new[tkr] = wt
        s = sum(w_new.values())
        if s > 0:
            w_cur = {k: v / s for k, v in w_new.items()}

        # Rebalance on drift
        drift = max(abs(w_cur.get(t, 0) - w_tgt.get(t, 0)) for t in w_tgt)
        if drift > REBAL_TRIGGER:
            all_t = set(w_cur) | set(w_tgt)
            turnover = sum(abs(w_tgt.get(t, 0) - w_cur.get(t, 0)) for t in all_t) / 2
            nav *= (1 - turnover * TC_BPS / 10_000)
            w_cur = dict(w_tgt)

        nav_out.append(nav)

    return pd.Series(nav_out, index=prices.index)


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

    print("Loading prices...")
    prices = load_prices(data_dir)
    print(f"  {prices.index[0].date()} → {prices.index[-1].date()}  ({len(prices):,}d)")

    # SPY benchmark
    spy_path = reader.ticker_path(data_dir, "equities", "SPY")
    spy_df   = pd.read_parquet(spy_path)
    spy_df["date"] = pd.to_datetime(spy_df["date"])
    spy = spy_df.set_index("date")["close"].sort_index().loc[START_DATE:]
    spy_nav = spy / spy.iloc[0]
    spy_m   = metrics(spy_nav)

    print("\nRunning grid search (231 weight combinations)...")

    step   = 5
    rows   = []
    values = range(0, 101, step)

    for g in values:
        for a in values:
            l = 100 - g - a
            if l < 0:
                continue
            w = {"Gold": g / 100, "AVGO": a / 100, "LLY": l / 100}
            nav = simulate(prices, w)
            m   = metrics(nav)
            rows.append({
                "gold": g, "avgo": a, "lly": l,
                **m,
                "label": f"Gold{g}/AVGO{a}/LLY{l}",
            })

    df = pd.DataFrame(rows)

    # ── Results ───────────────────────────────────────────────────────────────

    def print_top(title: str, col: str, n: int = 10) -> None:
        top = df.nlargest(n, col)
        print(f"\n{'='*72}")
        print(f"TOP {n} BY {title}")
        print(f"{'='*72}")
        print(f"  {'Weights':<28}  {'CAGR':>7}  {'Sharpe':>7}  {'MaxDD':>8}  {'Calmar':>7}")
        print(f"  {'-'*65}")
        for _, r in top.iterrows():
            print(f"  {r['label']:<28}  {r['cagr']:>7.2%}  {r['sharpe']:>7.3f}"
                  f"  {r['mdd']:>8.2%}  {r['calmar']:>7.3f}")

    print_top("CAGR",   "cagr")
    print_top("SHARPE", "sharpe")
    print_top("CALMAR", "calmar")

    # Equal weight baseline
    ew_w   = {"Gold": 1/3, "AVGO": 1/3, "LLY": 1/3}
    ew_nav = simulate(prices, ew_w)
    ew_m   = metrics(ew_nav)

    # Current RC v3 approximate (Gold 24%, LLY 19%, AVGO 10% → renormalise to 3-asset)
    rc_raw = {"Gold": 0.239, "AVGO": 0.099, "LLY": 0.192}
    rc_s   = sum(rc_raw.values())
    rc_w   = {k: v / rc_s for k, v in rc_raw.items()}
    rc_nav = simulate(prices, rc_w)
    rc_m   = metrics(rc_nav)

    print(f"\n{'='*72}")
    print("BASELINES")
    print(f"{'='*72}")
    print(f"  {'Strategy':<28}  {'CAGR':>7}  {'Sharpe':>7}  {'MaxDD':>8}  {'Calmar':>7}")
    print(f"  {'-'*65}")

    rc_lbl = f"Gold{round(rc_w['Gold']*100)}/AVGO{round(rc_w['AVGO']*100)}/LLY{round(rc_w['LLY']*100)} (RC v3 3-asset)"
    print(f"  {rc_lbl:<28}  {rc_m['cagr']:>7.2%}  {rc_m['sharpe']:>7.3f}"
          f"  {rc_m['mdd']:>8.2%}  {rc_m['calmar']:>7.3f}")
    print(f"  {'Equal weight (33/33/33)':<28}  {ew_m['cagr']:>7.2%}  {ew_m['sharpe']:>7.3f}"
          f"  {ew_m['mdd']:>8.2%}  {ew_m['calmar']:>7.3f}")
    print(f"  {'SPY':<28}  {spy_m['cagr']:>7.2%}  {spy_m['sharpe']:>7.3f}"
          f"  {spy_m['mdd']:>8.2%}  {spy_m['calmar']:>7.3f}")

    # Year-by-year for top CAGR, top Sharpe, EW, SPY
    best_cagr   = df.nlargest(1, "cagr").iloc[0]
    best_sharpe = df.nlargest(1, "sharpe").iloc[0]

    w_bc = {"Gold": best_cagr["gold"]/100, "AVGO": best_cagr["avgo"]/100, "LLY": best_cagr["lly"]/100}
    w_bs = {"Gold": best_sharpe["gold"]/100, "AVGO": best_sharpe["avgo"]/100, "LLY": best_sharpe["lly"]/100}

    navs = {
        best_cagr["label"]:   simulate(prices, w_bc),
        best_sharpe["label"]: simulate(prices, w_bs),
        "EW 33/33/33":        ew_nav,
        "SPY":                spy_nav.reindex(prices.index).ffill(),
    }

    yr = {k: v.resample("YE").last().pct_change().dropna() for k, v in navs.items()}
    all_yrs = sorted({d.year for s in yr.values() for d in s.index})
    labels  = list(navs.keys())

    print(f"\n{'='*72}")
    print("YEAR-BY-YEAR  (best CAGR | best Sharpe | EW | SPY)")
    print(f"{'='*72}")
    print(f"  {'Year':<5}" + "".join(f"  {l:>22}" for l in labels))
    print(f"  {'-'*95}")
    for yr_ in all_yrs:
        row = f"  {yr_:<5}"
        for lbl in labels:
            r = {d.year: v for d, v in yr[lbl].items()}.get(yr_)
            row += f"  {r:>22.2%}" if r is not None else f"  {'n/a':>22}"
        print(row)

    # Save
    out = PROJECT_ROOT / "comparison_results"
    out.mkdir(exist_ok=True)
    df.to_csv(out / "base_optimizer_grid.csv", index=False)
    print(f"\nGrid saved to comparison_results/base_optimizer_grid.csv")
    print("=" * 72)


if __name__ == "__main__":
    main()
