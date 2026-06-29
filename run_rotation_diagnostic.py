"""
Rotation diagnostic: empirical inputs for exit/rotation logic design.

Three sections:
  1. Degradation matrix  — 8 holdings x 4 scenarios x 3 horizons (21/63/252d)
  2. Regime flip stability — RY and BAA10Y label persistence
  3. New-regime screen overlap — top 15 re-ranked under each flip scenario
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
from asset_universe.analysis.engine import _regime_end_dates
from asset_universe.store import reader

# ── Holdings ──────────────────────────────────────────────────────────────────
HOLDINGS = [
    {"name": "Gold",  "ticker": "PPFB.DE", "safe": "PPFB_DE", "cat": "commodities"},
    {"name": "Silver","ticker": "PHAG.L",  "safe": "PHAG_L",  "cat": "commodities"},
    {"name": "LLY",   "ticker": "LLY",     "safe": "LLY",     "cat": "equities"},
    {"name": "WMT",   "ticker": "WMT",     "safe": "WMT",     "cat": "equities"},
    {"name": "CCJ",   "ticker": "CCJ",     "safe": "CCJ",     "cat": "equities"},
    {"name": "VRT",   "ticker": "VRT",     "safe": "VRT",     "cat": "equities"},
    {"name": "AVGO",  "ticker": "AVGO",    "safe": "AVGO",    "cat": "equities"},
    {"name": "HWM",   "ticker": "HWM",     "safe": "HWM",     "cat": "equities"},
]

HORIZONS = [21, 63, 252]

SCENARIOS = {
    "Current": {"ry_regime": "HIGH", "baa10y_regime": "TIGHT"},
    "ScenA (RY→LOW)":  {"ry_regime": "LOW",  "baa10y_regime": "TIGHT"},
    "ScenB (BAA→WIDE)":{"ry_regime": "HIGH", "baa10y_regime": "WIDE"},
    "ScenC (both)":    {"ry_regime": "LOW",  "baa10y_regime": "WIDE"},
}

FLIP_SCENARIOS = ["ScenA (RY→LOW)", "ScenB (BAA→WIDE)", "ScenC (both)"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_prices(data_dir: Path, cat: str, safe: str) -> pd.Series:
    path = reader.ticker_path(data_dir, cat, safe)
    if not path.exists():
        return pd.Series(dtype=float)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index()


def fwd_return(
    prices: pd.Series,
    date: pd.Timestamp,
    days: int,
    regime_end: pd.Timestamp | None = None,
) -> float | None:
    idx = prices.index.searchsorted(date)
    if idx >= len(prices):
        return None
    if abs((prices.index[idx] - date).days) > 5:
        return None
    fwd_idx = idx + days
    if regime_end is not None:
        end_idx = prices.index.searchsorted(regime_end)
        fwd_idx = min(fwd_idx, end_idx)
    if fwd_idx >= len(prices) or fwd_idx <= idx:
        return None
    p0, p1 = prices.iloc[idx], prices.iloc[fwd_idx]
    return (p1 - p0) / p0 if p0 > 0 else None


def stats(rets: list[float]) -> tuple[float, float, int]:
    """Returns (median_pct, win_rate_pct, n)."""
    if len(rets) < 10:
        return float("nan"), float("nan"), len(rets)
    s = pd.Series(rets)
    return round(s.median() * 100, 1), round((s > 0).mean() * 100, 0), len(rets)


def matched_dates(labeled_df: pd.DataFrame, conditions: dict) -> pd.DatetimeIndex:
    mask = pd.Series(True, index=labeled_df.index)
    for k, v in conditions.items():
        mask &= labeled_df[k] == v
    return labeled_df.index[mask]


# ── Section 1: Degradation matrix ────────────────────────────────────────────

def print_degradation_matrix(labeled_df: pd.DataFrame, data_dir: Path) -> None:
    print("\n" + "=" * 80)
    print("1. DEGRADATION MATRIX")
    print("   Format: med% (win%) [N]   |  d = scenario minus current")
    print("=" * 80)

    scen_dates = {name: matched_dates(labeled_df, conds) for name, conds in SCENARIOS.items()}

    # Pre-compute regime end dates per scenario — caps returns at regime boundary
    scen_ends = {
        name: _regime_end_dates(labeled_df, conds, scen_dates[name])
        for name, conds in SCENARIOS.items()
    }

    # Pre-load all prices
    prices_map = {
        h["name"]: load_prices(data_dir, h["cat"], h["safe"])
        for h in HOLDINGS
    }

    for horizon in HORIZONS:
        print(f"\n  ── {horizon}d forward ──────────────────────────────────────────────────")
        hdr = f"  {'Name':<8}  {'Current':>18}"
        for s in FLIP_SCENARIOS:
            hdr += f"  {s:>18}  {'dmed':>6}"
        print(hdr)
        print("  " + "-" * (len(hdr) - 2))

        for h in HOLDINGS:
            prices = prices_map[h["name"]]
            if prices.empty:
                print(f"  {h['name']:<8}  no data")
                continue

            row_parts: dict[str, tuple] = {}
            for scen_name, dates in scen_dates.items():
                ends = scen_ends[scen_name]
                rets = [
                    r for dt in dates
                    if (r := fwd_return(prices, dt, horizon, ends.get(dt))) is not None
                ]
                row_parts[scen_name] = stats(rets)

            cur_med, cur_win, cur_n = row_parts["Current"]
            line = f"  {h['name']:<8}  {cur_med:>+6.1f}% ({cur_win:>3.0f}%) [{cur_n:>3}]"

            for s in FLIP_SCENARIOS:
                s_med, s_win, s_n = row_parts[s]
                if np.isnan(s_med):
                    cell = f"  {'N<10':>18}  {'---':>6}"
                else:
                    delta = s_med - cur_med if not np.isnan(cur_med) else float("nan")
                    cell_val = f"{s_med:>+6.1f}% ({s_win:>3.0f}%) [{s_n:>3}]"
                    d_str = f"{delta:>+5.1f}" if not np.isnan(delta) else "  n/a"
                    cell = f"  {cell_val:>18}  {d_str:>6}"
                line += cell
            print(line)

        # Print N for scenario matched dates
        print(f"\n  Matched dates — Current: {len(scen_dates['Current'])}  ", end="")
        for s in FLIP_SCENARIOS:
            print(f"{s}: {len(scen_dates[s])}  ", end="")
        print()


# ── Section 2: Regime flip stability ─────────────────────────────────────────

def print_flip_stability(labeled_df: pd.DataFrame) -> None:
    print("\n" + "=" * 80)
    print("2. REGIME FLIP STABILITY")
    print("   How often does a regime label flip revert within 1/3/5 trading days?")
    print("=" * 80)

    for feat, label in [("ry", "RY"), ("baa10y", "BAA10Y")]:
        col = f"{feat}_regime"
        if col not in labeled_df.columns:
            print(f"\n  {label}: {col} not found")
            continue

        series = labeled_df[col].dropna()
        # Detect flip dates
        shifted = series.shift(1)
        flip_mask = (series != shifted) & shifted.notna()
        flip_idx = series.index[flip_mask]

        total = len(flip_idx)
        reversals = {1: 0, 3: 0, 5: 0}

        for fd in flip_idx:
            loc = series.index.get_loc(fd)
            pre = series.iloc[loc - 1] if loc > 0 else None
            if pre is None:
                continue
            for w in [1, 3, 5]:
                end_loc = min(loc + w, len(series) - 1)
                window_labels = series.iloc[loc + 1: end_loc + 1]
                if pre in window_labels.values:
                    reversals[w] += 1

        # Also compute average regime duration
        # Group consecutive same-label runs
        runs = (series != series.shift()).cumsum()
        run_lengths = series.groupby(runs).size()
        median_duration = run_lengths.median()
        max_duration = run_lengths.max()

        print(f"\n  {label} ({col}):")
        print(f"    Total flips in history : {total}")
        print(f"    Median regime duration : {median_duration:.0f} trading days "
              f"(~{median_duration/21:.1f} months)")
        print(f"    Longest run            : {max_duration:.0f} trading days "
              f"(~{max_duration/21:.1f} months)")
        for w in [1, 3, 5]:
            pct = reversals[w] / total * 100 if total > 0 else 0
            verdict = "confirmation window worth it" if pct > 25 else "day-1 trigger fine"
            print(f"    Reverts within {w}d      : {reversals[w]}/{total} ({pct:.0f}%)  → {verdict}")

        # Per-label breakdown
        print(f"    Per-label flip counts  :", end="")
        for lbl in series.unique():
            n = flip_mask[series.shift(1) == lbl].sum() if lbl else 0
            print(f"  {lbl}→other: {n}", end="")
        print()


# ── Section 3: New-regime screen overlap ─────────────────────────────────────

def print_screen_overlap(labeled_df: pd.DataFrame, data_dir: Path) -> None:
    print("\n" + "=" * 80)
    print("3. NEW-REGIME SCREEN OVERLAP  (top 15 by 252d median, from top-50 screen)")
    print("   ★ = current holding")
    print("=" * 80)

    screen_path = PROJECT_ROOT / "universe_screen_results.csv"
    if not screen_path.exists():
        print("\n  universe_screen_results.csv not found — skipping")
        return

    screen_df = pd.read_csv(screen_path)
    top50 = screen_df.head(50)[["ticker", "category"]].to_dict("records")
    current_tickers = {h["ticker"] for h in HOLDINGS}

    scen_dates = {name: matched_dates(labeled_df, conds) for name, conds in SCENARIOS.items()}
    scen_ends  = {
        name: _regime_end_dates(labeled_df, conds, scen_dates[name])
        for name, conds in SCENARIOS.items()
    }

    for scen_name in FLIP_SCENARIOS:
        dates = scen_dates[scen_name]
        ends  = scen_ends[scen_name]
        print(f"\n  {scen_name}  (N={len(dates)} matched dates in history)")

        if len(dates) < 10:
            print("    Insufficient history for this combination.")
            continue

        rows = []
        for entry in top50:
            tkr = entry["ticker"]
            cat_raw = entry.get("category", "")
            if "equity" in cat_raw.lower() or "us equity" in cat_raw.lower():
                cat = "equities"
            elif "swedish" in cat_raw.lower():
                cat = "equities"
            elif "commodity" in cat_raw.lower() or "commodit" in cat_raw.lower():
                cat = "commodities"
            elif "etf" in cat_raw.lower() or "ucits" in cat_raw.lower():
                cat = "intl_etfs"
            else:
                cat = "equities"

            prices = load_prices(data_dir, cat, reader.safe_name(tkr))
            if prices.empty:
                continue

            rets_252 = [r for dt in dates if (r := fwd_return(prices, dt, 252, ends.get(dt))) is not None]
            rets_63  = [r for dt in dates if (r := fwd_return(prices, dt, 63,  ends.get(dt))) is not None]
            med252, win252, n252 = stats(rets_252)
            med63,  win63,  _    = stats(rets_63)

            if n252 < 10:
                continue

            rows.append({
                "ticker":  tkr,
                "med252":  med252,
                "win252":  win252,
                "med63":   med63,
                "win63":   win63,
                "n":       n252,
                "hold":    "★" if tkr in current_tickers else "",
            })

        if not rows:
            print("    No qualifying assets.")
            continue

        df_out = (pd.DataFrame(rows)
                  .sort_values("med252", ascending=False)
                  .reset_index(drop=True)
                  .head(15))

        print(f"  {'#':<3} {'Ticker':<10} {'63d med':>8} {'63d win':>8} "
              f"{'252d med':>9} {'252d win':>9} {'N':>5}  {'Hold':>4}")
        print("  " + "-" * 65)
        for i, row in df_out.iterrows():
            print(f"  {i+1:<3} {row.ticker:<10} {row.med63:>+7.1f}% {row.win63:>7.0f}%  "
                  f"{row.med252:>+8.1f}% {row.win252:>7.0f}%  {row.n:>4}  {row.hold:>4}")


# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    data_dir = config.raw_data_dir()
    labeled_df, _ = regime_module.build(data_dir)

    print_degradation_matrix(labeled_df, data_dir)
    print_flip_stability(labeled_df)
    print_screen_overlap(labeled_df, data_dir)

    print("\n" + "=" * 80)
    print("END ROTATION DIAGNOSTIC")
    print("=" * 80)


if __name__ == "__main__":
    main()
