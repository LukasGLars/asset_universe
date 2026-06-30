"""
run_universe_frequency.py

Runs walk-forward asset selection across all regime transitions on the full
universe. Outputs selection frequency per asset — how often each asset is
picked in the top-N per transition. This drives anchor vs rotation decisions.

No assumptions about anchor composition. Let the data speak.
"""
from __future__ import annotations

import io, sys
from collections import Counter
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

MIN_DATES    = 5
CONFIRM_DAYS = 3
START_DATE   = "2004-01-01"
TOP_N        = 8      # selection size — same as Strategy B
MIN_HIST_YR  = 15     # minimum history for universe inclusion


# ── Load universe ─────────────────────────────────────────────────────────────

def load_all_universe(data_dir: Path) -> dict[str, pd.Series]:
    screen = PROJECT_ROOT / "universe_screen_results.csv"
    df = pd.read_csv(screen)
    df = df[df["history_yr"] >= MIN_HIST_YR].copy()
    print(f"  Universe screen: {len(df)} assets with >={MIN_HIST_YR}yr history")

    prices: dict[str, pd.Series] = {}
    missing = 0

    for _, row in df.iterrows():
        tkr = row["ticker"]
        cat_raw = str(row.get("category", "")).lower()
        if "commodity" in cat_raw:
            cat = "commodities"
        elif "ucits" in cat_raw or "etf" in cat_raw:
            cat = "intl_etfs"
        elif "swedish" in cat_raw:
            cat = "swedish"
        else:
            cat = "equities"

        safe = reader.safe_name(tkr)
        path = reader.ticker_path(data_dir, cat, safe)
        if not path.exists():
            missing += 1
            continue

        try:
            d = pd.read_parquet(path)
            d["date"] = pd.to_datetime(d["date"])
            s = d.set_index("date")["close"].sort_index()
            if len(s) > 100:
                prices[tkr] = s
        except Exception:
            missing += 1

    print(f"  Loaded: {len(prices)} assets  |  missing from parquet: {missing}")
    return prices


# ── Regime helpers (copied from comparison script) ────────────────────────────

def get_transitions(labeled_df: pd.DataFrame) -> list[tuple]:
    out: list[tuple] = []
    prev_ry = prev_baa = None
    for date, row in labeled_df[["ry_regime", "baa10y_regime"]].iterrows():
        ry, baa = row["ry_regime"], row["baa10y_regime"]
        if pd.isna(ry) or pd.isna(baa):
            continue
        if prev_ry is None:
            out.append((date, ry, baa))
            prev_ry, prev_baa = ry, baa
            continue
        if ry != prev_ry or baa != prev_baa:
            end = date + pd.Timedelta(days=CONFIRM_DAYS)
            fut = labeled_df.loc[date:end, ["ry_regime", "baa10y_regime"]]
            if (len(fut) >= 2
                    and (fut["ry_regime"] == ry).all()
                    and (fut["baa10y_regime"] == baa).all()):
                out.append((date, ry, baa))
                prev_ry, prev_baa = ry, baa
    return out


def select_wf(
    labeled_df: pd.DataFrame,
    universe_prices: dict[str, pd.Series],
    before: pd.Timestamp,
    ry: str,
    baa: str,
    n: int,
) -> list[tuple[str, float]]:
    """Returns top-N (ticker, median_return) pairs, walk-forward."""
    cond = {"ry_regime": ry, "baa10y_regime": baa}
    hist = labeled_df[labeled_df.index < before]
    mask = pd.Series(True, index=hist.index)
    for k, v in cond.items():
        mask &= hist[k] == v
    matched = hist.index[mask]

    if len(matched) < MIN_DATES:
        return []

    ends = _regime_end_dates(hist, cond, matched)
    rows: list[tuple[str, float]] = []

    for tkr, prices in universe_prices.items():
        rets: list[float] = []
        for dt in matched:
            idx = prices.index.searchsorted(dt)
            if idx >= len(prices) or abs((prices.index[idx] - dt).days) > 5:
                continue
            fwd = idx + 252
            end_dt = ends.get(dt)
            if end_dt is not None:
                fwd = min(fwd, prices.index.searchsorted(end_dt))
            if fwd >= len(prices) or fwd <= idx:
                continue
            p0, p1 = prices.iloc[idx], prices.iloc[fwd]
            if p0 > 0:
                rets.append((p1 - p0) / p0)
        if len(rets) >= MIN_DATES:
            rows.append((tkr, float(np.median(rets))))

    rows.sort(key=lambda x: x[1], reverse=True)
    return rows[:n]


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    data_dir = config.raw_data_dir()

    print("Building regime labels...")
    labeled_df, _ = regime_module.build(data_dir)
    labeled_df = labeled_df.loc[START_DATE:]
    print(f"  {labeled_df.index[0].date()} → {labeled_df.index[-1].date()}")

    print("\nLoading full universe prices...")
    universe_prices = load_all_universe(data_dir)

    print("\nComputing transitions...")
    transitions = get_transitions(labeled_df)
    print(f"  {len(transitions)} transitions")

    # Per-regime frequency tables
    freq_top1  = Counter()
    freq_top3  = Counter()
    freq_top5  = Counter()
    freq_top8  = Counter()
    regime_freq: dict[str, Counter] = {}  # (ry, baa) → Counter

    detail_rows: list[dict] = []

    print(f"\nRunning walk-forward selection (top {TOP_N}) across all transitions...")
    for i, (trans_date, ry, baa) in enumerate(transitions):
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(transitions)}")

        selected = select_wf(labeled_df, universe_prices, trans_date, ry, baa, TOP_N)
        if not selected:
            continue

        regime_key = f"{ry}_{baa}"
        if regime_key not in regime_freq:
            regime_freq[regime_key] = Counter()

        for rank, (tkr, med_ret) in enumerate(selected):
            freq_top8[tkr] += 1
            if rank < 5:
                freq_top5[tkr] += 1
            if rank < 3:
                freq_top3[tkr] += 1
            if rank < 1:
                freq_top1[tkr] += 1
            regime_freq[regime_key][tkr] += 1
            detail_rows.append({
                "date": trans_date.date(), "ry": ry, "baa": baa,
                "rank": rank + 1, "ticker": tkr, "med_ret": round(med_ret, 4),
            })

    n_trans = len(transitions)

    # ── Overall frequency table ───────────────────────────────────────────────
    print("\n" + "=" * 75)
    print(f"ASSET SELECTION FREQUENCY  (out of {n_trans} transitions)")
    print("=" * 75)
    print(f"  {'Ticker':<10}  {'Top1':>6}  {'Top3':>6}  {'Top5':>6}  {'Top8':>6}  "
          f"{'Top8%':>7}  {'Top3%':>7}")
    print("  " + "-" * 55)

    # Sort by top-8 frequency
    all_tickers = set(freq_top8)
    rows = []
    for tkr in all_tickers:
        rows.append((
            tkr,
            freq_top1.get(tkr, 0),
            freq_top3.get(tkr, 0),
            freq_top5.get(tkr, 0),
            freq_top8.get(tkr, 0),
        ))
    rows.sort(key=lambda x: x[4], reverse=True)

    for tkr, t1, t3, t5, t8 in rows[:40]:
        pct8 = t8 / n_trans * 100
        pct3 = t3 / n_trans * 100
        print(f"  {tkr:<10}  {t1:>6}  {t3:>6}  {t5:>6}  {t8:>6}  "
              f"{pct8:>6.1f}%  {pct3:>6.1f}%")

    # ── Per-regime breakdown for top assets ───────────────────────────────────
    print("\n" + "=" * 75)
    print("PER-REGIME FREQUENCY  (top 15 assets, by regime)")
    print("=" * 75)
    top15 = [r[0] for r in rows[:15]]
    regime_keys = sorted(regime_freq.keys())

    # Count transitions per regime
    regime_counts: dict[str, int] = {}
    for _, ry, baa in transitions:
        k = f"{ry}_{baa}"
        regime_counts[k] = regime_counts.get(k, 0) + 1

    hdr = f"  {'Ticker':<10}" + "".join(f"  {k:>12}" for k in regime_keys)
    print(hdr)
    print(f"  {'n_trans':<10}" + "".join(
        f"  {regime_counts.get(k, 0):>12}" for k in regime_keys))
    print("  " + "-" * (len(hdr) - 2))
    for tkr in top15:
        row = f"  {tkr:<10}"
        for k in regime_keys:
            cnt = regime_freq[k].get(tkr, 0)
            tot = regime_counts.get(k, 1)
            row += f"  {cnt:>5}/{tot:<5}"
        print(row)

    # ── Save outputs ──────────────────────────────────────────────────────────
    out = PROJECT_ROOT / "comparison_results"
    out.mkdir(exist_ok=True)

    detail_df = pd.DataFrame(detail_rows)
    detail_df.to_csv(out / "universe_selection_detail.csv", index=False)

    freq_df = pd.DataFrame(rows, columns=["ticker", "top1", "top3", "top5", "top8"])
    freq_df["top8_pct"] = freq_df["top8"] / n_trans * 100
    freq_df["top3_pct"] = freq_df["top3"] / n_trans * 100
    freq_df.to_csv(out / "universe_selection_frequency.csv", index=False)

    print(f"\nSaved:")
    print(f"  comparison_results/universe_selection_frequency.csv")
    print(f"  comparison_results/universe_selection_detail.csv")
    print("=" * 75)


if __name__ == "__main__":
    main()
