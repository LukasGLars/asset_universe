"""
run_scarcity_profile.py

Regime-conditional return profile for the 6 core scarcity assets.
For each asset × regime combination: median 252d return, win rate, N.
Uses regime-capped returns (no bleed into next regime).

Purpose: validate each asset as a base holding vs regime-specific rotation candidate.
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

START_DATE = "2004-01-01"
FWD_DAYS   = 252

SCARCITY_ASSETS = {
    "Gold":   ("commodities", "GC_F"),
    "Silver": ("commodities", "SI_F"),
    "CCJ":    ("equities",    "CCJ"),
    "VRT":    ("equities",    "VRT"),
    "AVGO":   ("equities",    "AVGO"),
    "LLY":    ("equities",    "LLY"),
}

REGIMES = [
    ("HIGH", "TIGHT"), ("HIGH", "MID"), ("HIGH", "WIDE"),
    ("MID",  "TIGHT"), ("MID",  "MID"), ("MID",  "WIDE"),
    ("LOW",  "TIGHT"), ("LOW",  "MID"), ("LOW",  "WIDE"),
]


def load_prices(data_dir: Path) -> dict[str, pd.Series]:
    prices = {}
    for name, (cat, safe) in SCARCITY_ASSETS.items():
        path = reader.ticker_path(data_dir, cat, safe)
        if not path.exists():
            print(f"  {name}: NOT FOUND")
            continue
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        s = df.set_index("date")["close"].sort_index()
        prices[name] = s
        print(f"  {name:<8} {s.index[0].date()} → {s.index[-1].date()}  ({len(s):,}d)")
    return prices


def regime_profile(
    labeled_df: pd.DataFrame,
    prices: pd.Series,
    ry: str,
    baa: str,
) -> dict:
    cond = {"ry_regime": ry, "baa10y_regime": baa}
    mask = pd.Series(True, index=labeled_df.index)
    for k, v in cond.items():
        mask &= labeled_df[k] == v
    matched = labeled_df.index[mask]

    if len(matched) < 3:
        return {"med": None, "wr": None, "n": 0}

    ends = _regime_end_dates(labeled_df, cond, matched)
    rets = []

    for dt in matched:
        idx = prices.index.searchsorted(dt)
        if idx >= len(prices) or abs((prices.index[idx] - dt).days) > 5:
            continue
        fwd = idx + FWD_DAYS
        end_dt = ends.get(dt)
        if end_dt is not None:
            fwd = min(fwd, prices.index.searchsorted(end_dt))
        if fwd >= len(prices) or fwd <= idx:
            continue
        p0, p1 = prices.iloc[idx], prices.iloc[fwd]
        if p0 > 0:
            rets.append((p1 - p0) / p0)

    if not rets:
        return {"med": None, "wr": None, "n": 0}

    return {
        "med": float(np.median(rets)),
        "wr":  float(np.mean([r > 0 for r in rets])),
        "n":   len(rets),
    }


def main() -> None:
    data_dir = config.raw_data_dir()

    print("Building regime labels...")
    labeled_df, _ = regime_module.build(data_dir)
    labeled_df = labeled_df.loc[START_DATE:]

    # Count transitions per regime
    regime_counts = {}
    for (ry, baa) in REGIMES:
        mask = (labeled_df["ry_regime"] == ry) & (labeled_df["baa10y_regime"] == baa)
        regime_counts[(ry, baa)] = mask.sum()

    print("\nLoading scarcity asset prices...")
    prices = load_prices(data_dir)

    # ── Median return matrix ───────────────────────────────────────────────────
    results: dict[str, dict] = {name: {} for name in prices}

    for name, p in prices.items():
        for (ry, baa) in REGIMES:
            results[name][(ry, baa)] = regime_profile(labeled_df, p, ry, baa)

    regime_labels = [f"{ry}\n{baa}" for ry, baa in REGIMES]
    col_w = 12

    # ── Print median return table ──────────────────────────────────────────────
    print("\n" + "=" * 90)
    print(f"252d MEDIAN RETURN (regime-capped)   START_DATE={START_DATE}")
    print("=" * 90)

    header = f"  {'Asset':<8}" + "".join(
        f"  {ry+'|'+baa:>{col_w}}" for ry, baa in REGIMES
    )
    print(header)

    n_row = f"  {'n_days':<8}" + "".join(
        f"  {regime_counts[(ry,baa)]:>{col_w},}" for ry, baa in REGIMES
    )
    print(n_row)
    print("  " + "-" * (len(header) - 2))

    for name in SCARCITY_ASSETS:
        if name not in results:
            continue
        row = f"  {name:<8}"
        for (ry, baa) in REGIMES:
            r = results[name][(ry, baa)]
            if r["med"] is None:
                row += f"  {'n/a':>{col_w}}"
            else:
                row += f"  {r['med']:>{col_w}.1%}"
        print(row)

    # ── Print win rate table ───────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("WIN RATE (% of matched dates with positive 252d return)")
    print("=" * 90)
    print(header)
    print(n_row)
    print("  " + "-" * (len(header) - 2))

    for name in SCARCITY_ASSETS:
        if name not in results:
            continue
        row = f"  {name:<8}"
        for (ry, baa) in REGIMES:
            r = results[name][(ry, baa)]
            if r["wr"] is None:
                row += f"  {'n/a':>{col_w}}"
            else:
                row += f"  {r['wr']:>{col_w}.0%}"
        print(row)

    # ── Print N table ──────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("N (matched dates with valid forward return)")
    print("=" * 90)
    print(header)
    print("  " + "-" * (len(header) - 2))

    for name in SCARCITY_ASSETS:
        if name not in results:
            continue
        row = f"  {name:<8}"
        for (ry, baa) in REGIMES:
            r = results[name][(ry, baa)]
            row += f"  {r['n']:>{col_w}}"
        print(row)

    # ── Regime robustness summary ──────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("REGIME ROBUSTNESS SUMMARY")
    print("Positive median in X of 9 regimes  |  Mean median across all regimes  |  Min median")
    print("=" * 90)
    print(f"  {'Asset':<8}  {'Pos/9':>6}  {'Mean med':>10}  {'Min med':>10}  {'Worst regime'}")
    print("  " + "-" * 60)

    for name in SCARCITY_ASSETS:
        if name not in results:
            continue
        meds = [(ry, baa, results[name][(ry, baa)]["med"])
                for ry, baa in REGIMES
                if results[name][(ry, baa)]["med"] is not None]
        if not meds:
            continue
        vals = [m for _, _, m in meds]
        pos  = sum(1 for v in vals if v > 0)
        mean = np.mean(vals)
        mn   = min(vals)
        worst_regime = min(meds, key=lambda x: x[2])
        worst_label  = f"{worst_regime[0]}|{worst_regime[1]}"
        print(f"  {name:<8}  {pos:>4}/9  {mean:>10.1%}  {mn:>10.1%}  {worst_label}")

    print("=" * 90)


if __name__ == "__main__":
    main()
