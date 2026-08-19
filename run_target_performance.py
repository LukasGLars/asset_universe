"""
run_target_performance.py

Performance table for the LIVE target portfolio -- the Reactor Core base mix,
as actually held: buy-and-hold with a band rebalance, no overlays.

What this is NOT: a strategy test. Nothing here is being selected or decided.
It exists so the standing question "how has the target mix done?" has one
reproducible answer instead of a number restated from an old session's prose
-- the same rule that produced PR #100.

Two things must travel with every figure this prints, and both are printed
with them:

  1. IN-SAMPLE. The 25/40/35 mix was chosen on 2026-08-16 with this exact
     window visible. run_clean_sheet_search.py (PR #99) established that
     search-based selection does not transfer out of sample; that finding
     applies to these numbers too. The honest claim is "no findable
     alternative beat it", not "validated".
  2. REGIME-CONCENTRATED. 2009-2022 and 2023-2026 are different portfolios
     by the numbers. The full-sample CAGR is not a planning input on its own,
     which is why the sub-period block is not optional output.

Convention note: this uses REAL drift -- shares are held and weights are
allowed to move until a leg breaches the band, with TC charged per traded
leg. That is deliberately NOT run_combined_system.py's convention, which
reapplies the locked target every day at zero cost and so hands a static mix
free daily rebalancing. Both are printed side by side in section 2 so the
gap between them stays visible rather than being rediscovered a third time.

Weights and band are READ from vol_target.py, never restated here, so this
script cannot drift from the live config.

Price only, no dividends -- LLY and AVGO yields are excluded, so CAGR is
understated by roughly 1pp.

Usage:
    python run_target_performance.py

Output: comparison_results/target_performance.csv
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from vol_target import BASE_WEIGHTS, REBAL_BAND

DATA_DIR = config.raw_data_dir()
OUT_CSV = PROJECT_ROOT / "comparison_results" / "target_performance.csv"

TC = 0.0010          # per traded leg, matches run_combined_system.py
MIN_TRADE = 0.005    # don't charge TC on a leg that barely moves


def load_prices(category: str, stem: str) -> pd.Series:
    df = pd.read_parquet(DATA_DIR / category / f"{stem}.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index().dropna()


def perf(equity: pd.Series) -> dict:
    r = equity.pct_change().dropna()
    yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    total = equity.iloc[-1] / equity.iloc[0]
    cagr = total ** (1 / yrs) - 1 if yrs > 0 else np.nan
    dd = equity / equity.cummax() - 1
    maxdd = float(dd.min())
    downside = r[r < 0].std() * np.sqrt(252)
    return {
        "cagr": cagr,
        "vol": float(r.std() * np.sqrt(252)),
        "sharpe": float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else np.nan,
        "sortino": float(r.mean() * 252 / downside) if downside > 0 else np.nan,
        "maxdd": maxdd,
        "calmar": cagr / abs(maxdd) if maxdd != 0 else np.nan,
        "years": yrs,
        "multiple": float(total),
    }


def band_equity(prices: pd.DataFrame, weights: dict[str, float],
                band: float = REBAL_BAND, tc: float = TC) -> tuple[pd.Series, int]:
    """Held shares, real drift, rebalance only on a band breach.

    Weights move with prices between rebalances -- unlike
    run_combined_system.simulate(), which relocks the target daily for free.
    """
    prices = prices.dropna()
    tickers = list(weights)
    shares = {t: weights[t] / prices[t].iloc[0] for t in tickers}
    equity, trades = [], 0

    for _, px_row in prices.iterrows():
        values = {t: shares[t] * px_row[t] for t in tickers}
        total = sum(values.values())
        drift = {t: values[t] / total - weights[t] for t in tickers}
        if max(abs(v) for v in drift.values()) > band:
            total -= total * sum(tc for t in tickers if abs(drift[t]) > MIN_TRADE)
            shares = {t: total * weights[t] / px_row[t] for t in tickers}
            trades += 1
        equity.append(total)

    return pd.Series(equity, index=prices.index), trades


def daily_equity(prices: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """run_combined_system.py's convention: target reapplied daily, no cost."""
    prices = prices.dropna()
    r = (prices.pct_change().fillna(0) * pd.Series(weights)).sum(axis=1)
    return (1 + r).cumprod()


HDR = (f"{'':34}{'CAGR':>8}{'Vol':>8}{'Sharpe':>8}"
       f"{'Sortino':>9}{'MaxDD':>9}{'Calmar':>8}")


def fmt(label: str, p: dict, extra: str = "") -> str:
    return (f"{label:34}{p['cagr']*100:7.1f}% {p['vol']*100:7.1f}% {p['sharpe']:7.2f} "
            f"{p['sortino']:8.2f} {p['maxdd']*100:8.1f}% {p['calmar']:7.2f}{extra}")


def main() -> None:
    gold = load_prices("commodities", "GC_F")
    avgo = load_prices("equities", "AVGO")
    lly = load_prices("equities", "LLY")
    spy = load_prices("equities", "SPY")
    qqq = load_prices("equities", "QQQ")
    usdsek = load_prices("fx", "USDSEK_X")

    start = avgo.index[0]  # AVGO's IPO bounds the joint history
    px = pd.DataFrame({"GC_F": gold, "AVGO": avgo, "LLY": lly}).dropna()
    px = px[px.index >= start]
    common = px.index
    end = common[-1]

    w = {k: BASE_WEIGHTS[k] for k in ("GC_F", "AVGO", "LLY")}
    mix = " / ".join(f"{k.replace('GC_F', 'Gold')} {v:.0%}" for k, v in w.items())

    rows: list[dict] = []

    print("=" * 100)
    print(f"TARGET PORTFOLIO -- {mix}, {REBAL_BAND:.0%} rebalance band, "
          f"{TC*1e4:.0f}bps per traded leg")
    print("Buy-and-hold with band rebalancing. No guard, no silver overlay, no timing.")
    print(f"USD, price only (no dividends). {start.date()} -> {end.date()}")
    print("=" * 100)

    # -- 1. by period ---------------------------------------------------------
    periods = [
        ("Full sample (2009-08 - 2026-08)", start, end),
        ("First half (2009 - 2017)", start, pd.Timestamp("2017-09-30")),
        ("Second half (2017 - 2026)", pd.Timestamp("2017-10-01"), end),
        ("Pre-AI melt-up (2009 - 2022)", start, pd.Timestamp("2022-12-31")),
        ("AI melt-up only (2023 - 2026)", pd.Timestamp("2023-01-01"), end),
        ("Post-2020 (2020 - 2026)", pd.Timestamp("2020-01-01"), end),
    ]
    print("\n1. TARGET PORTFOLIO BY PERIOD")
    print(HDR + "   Trades/yr")
    print("-" * 112)
    for name, a, b in periods:
        eq, n = band_equity(px.loc[a:b], w)
        p = perf(eq)
        print(fmt(name, p, f"{n / p['years']:11.1f}"))
        rows.append({"section": "period", "label": name, **p, "trades": n})

    # -- 2. components and benchmarks -----------------------------------------
    print("\n2. FULL SAMPLE vs COMPONENTS AND BENCHMARKS (USD)")
    print(HDR)
    print("-" * 100)
    eq_target, n_target = band_equity(px, w)
    p_target = perf(eq_target)
    print(fmt(f"TARGET ({REBAL_BAND:.0%} band)", p_target))
    rows.append({"section": "usd", "label": "target", **p_target, "trades": n_target})

    p_daily = perf(daily_equity(px, w))
    print(fmt("  same, daily rebal (repo conv.)", p_daily))
    rows.append({"section": "usd", "label": "target_daily_rebal", **p_daily, "trades": np.nan})

    eq_ew, n_ew = band_equity(px, {k: 1 / 3 for k in w})
    p_ew = perf(eq_ew)
    print(fmt("  equal weight 1/3 each", p_ew))
    rows.append({"section": "usd", "label": "equal_weight", **p_ew, "trades": n_ew})

    print("-" * 100)
    singles = [("Gold (GC=F)", gold), ("Broadcom (AVGO)", avgo), ("Eli Lilly (LLY)", lly),
               ("S&P 500 (SPY)", spy), ("Nasdaq 100 (QQQ)", qqq)]
    for label, series in singles:
        s = series.reindex(common).dropna()
        p = perf(s / s.iloc[0])
        print(fmt(label, p))
        rows.append({"section": "usd", "label": label, **p, "trades": 0})

    # Single names are context for the mix's risk shape, NOT forgone
    # alternatives. AVGO's full-sample multiple is a hindsight pick -- it was
    # a freshly-IPO'd semi in 2009 -- so the shortfall against it is not a
    # cost that was ever available to avoid, and must not be reported as one.

    # -- 3. SEK ---------------------------------------------------------------
    print("\n3. SEK BASIS (translated at USDSEK -- the currency the plan is denominated in)")
    print(HDR)
    print("-" * 100)
    fx = usdsek.reindex(common).ffill()
    eq_sek, n_sek = band_equity(px.mul(fx, axis=0).dropna(), w)
    p_sek = perf(eq_sek)
    print(fmt("TARGET in SEK", p_sek))
    rows.append({"section": "sek", "label": "target", **p_sek, "trades": n_sek})
    for label, series in singles[:4]:
        s = (series.reindex(common) * fx).dropna()
        p = perf(s / s.iloc[0])
        print(fmt(f"{label} in SEK", p))
        rows.append({"section": "sek", "label": label, **p, "trades": 0})

    # -- 4. calendar years ----------------------------------------------------
    print("\n4. CALENDAR-YEAR RETURNS (%)  -- first and last years are partial")
    yearly = pd.DataFrame({
        "Target USD": eq_target.resample("YE").last().pct_change(),
        "Target SEK": eq_sek.resample("YE").last().pct_change(),
        "Gold": gold.reindex(common).resample("YE").last().pct_change(),
        "AVGO": avgo.reindex(common).resample("YE").last().pct_change(),
        "LLY": lly.reindex(common).resample("YE").last().pct_change(),
        "SPY": spy.reindex(common).resample("YE").last().pct_change(),
    })
    first = yearly.index[0]
    yearly.loc[first, "Target USD"] = eq_target.loc[:first].iloc[-1] - 1
    yearly.loc[first, "Target SEK"] = eq_sek.loc[:first].iloc[-1] - 1
    yearly.index = yearly.index.year
    print((yearly * 100).round(1).to_string())

    # -- 5. drawdown profile --------------------------------------------------
    dd = eq_target / eq_target.cummax() - 1
    r = eq_target.pct_change().dropna()
    print("\n5. DRAWDOWN PROFILE (target, USD)")
    print(f"  Max drawdown            : {dd.min()*100:.1f}%  on {dd.idxmin().date()}")
    print(f"  Current drawdown        : {dd.iloc[-1]*100:.1f}%")
    print(f"  Days below -10%         : {(dd < -0.10).sum()} of {len(dd)}  "
          f"({(dd < -0.10).mean()*100:.1f}%)")
    print(f"  Days below -20%         : {(dd < -0.20).sum()} of {len(dd)}  "
          f"({(dd < -0.20).mean()*100:.1f}%)")
    print(f"  Best / worst day        : {r.max()*100:+.1f}% / {r.min()*100:+.1f}%")
    print(f"  Total return            : {p_target['multiple']:.1f}x")
    print(f"  Rebalance trades        : {n_target} in {p_target['years']:.1f} yrs")

    print("\nREAD WITH: (1) in-sample -- mix chosen 2026-08-16 knowing this window;")
    print("           (2) regime-concentrated -- see the 2009-2022 vs 2023-2026 split.")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
    print(f"\nWrote {OUT_CSV.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
