"""
Opportunistic entry screen — thin CLI wrapper around screen_tactical()
in src/asset_universe/analysis/engine.py.

Tactical layer, separate from the 3-asset scarcity base (Gold/AVGO/LLY).
Deploys war-chest / home-base capital opportunistically when a candidate
clears four gates:

  1. Regime top-N  — ticker ranks in the top N of the CURRENT macro regime's
                      (ry_regime + baa10y_regime) conditional-return ranking.
                      Sourced from universe_screen_results.csv when it
                      matches the live regime (validated with a one-ticker
                      GC_F spot-check, not just by trusting the label),
                      otherwise computed fresh for the live regime only
                      (see _rank_universe_fresh).
  2. Above MA50     — price > 50d SMA (momentum confirmed). Checked
                      directly here. screen_tactical's own extension gate
                      (#3) allows negative extension too — a ticker below
                      its MA50 can still land in the "LOW" bucket — so this
                      explicit check is the one piece of gate logic this
                      script adds rather than reuses.
  3. Not extended   — delegated entirely to screen_tactical(): MA50
                      extension below the regime's own empirical p67,
                      combined with its relative-strength-vs-benchmark gate.
  4. No earnings    — delegated entirely to screen_tactical()'s earnings
                      gate (hold_days window, default 21 = 3 weeks).

Gates 3 and 4 are NOT reimplemented. screen_tactical() already existed in
engine.py and was the basis for the HWM entry (2026-06-24) via run_screen.py.
This script adds gate 1 (regime-ranking source) and gate 2 (explicit
above-MA50 check), runs screen_tactical() for gates 3-4, and formats the
combined result as one table.

Usage:
    python run_entry_screen.py
    python run_entry_screen.py --top-n 30 --hold-days 21 --benchmark SPY
    python run_entry_screen.py --as-of 2026-06-24 --data-dir <snapshot dir>
"""
from __future__ import annotations

import argparse
import sys
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import warnings
warnings.filterwarnings("ignore")

import pandas as pd

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.analysis.engine import (
    _next_earnings,
    current_regime,
    screen_tactical,
)
from asset_universe.store import reader

ROOT = Path(__file__).parent
UNIVERSE_CSV = ROOT / "universe_screen_results.csv"

CATEGORY_DIR = {
    "US Equity":  "equities",
    "Commodity":  "commodities",
    "UCITS ETF":  "intl_etfs",
    "Swedish":    "intl_etfs",
}

# Matches universe_screen_results.csv's own methodology (run_universe_screen.py):
# no history-length cutoff (DFII10's 2003 start is the binding data constraint —
# excluding shorter-history names like HWM at 9.6yr would defeat the purpose of
# this fallback), MIN_N=10 matched dates as the only quality bar.
MIN_N_OBS = 10
FWD_DAYS  = 252


# ── Gate 1: regime-appropriate candidate list ───────────────────────────────

def _uncapped_forward_return(prices: pd.Series, dt: pd.Timestamp, fwd_days: int) -> float | None:
    """Forward return, NOT capped at regime end — intentionally mirrors
    run_universe_screen.py's own _forward_return (the script that produces
    universe_screen_results.csv) rather than engine.py's regime-capped
    version, so the freshness check and the fallback ranking both stay
    apples-to-apples with the cached CSV. (engine.py's capped helper was a
    later, more conservative fix applied to the conditional-return *engine*;
    the universe screen was never migrated to it — see MEMORY.md. Comparing
    against the capped engine.query() here would make a same-regime CSV look
    "stale" purely from the methodology gap, not from an actual regime
    change — confirmed empirically: GC_F med_252d is 34% uncapped vs 5%
    capped for the same HIGH+TIGHT regime.)"""
    idx = prices.index.searchsorted(dt)
    if idx >= len(prices) or abs((prices.index[idx] - dt).days) > 5:
        return None
    fwd_idx = idx + fwd_days
    if fwd_idx >= len(prices):
        return None
    p0, p1 = prices.iloc[idx], prices.iloc[fwd_idx]
    return (p1 - p0) / p0 if p0 > 0 else None


def _matched_dates(conditions: dict, data_dir: Path) -> pd.DatetimeIndex:
    labeled_df, _ = regime_module.build(data_dir)
    mask = pd.Series(True, index=labeled_df.index)
    for k, v in conditions.items():
        mask &= labeled_df[k] == v
    return labeled_df.index[mask]


def _csv_matches_live_regime(df_full: pd.DataFrame, matched: pd.DatetimeIndex, data_dir: Path) -> bool:
    """Spot-check: does universe_screen_results.csv reflect the regime that's
    live right now? Recomputes GC_F's median 252d return with the SAME
    (uncapped) methodology the CSV was built with, rather than trusting a
    stale file blindly or comparing against a differently-capped method."""
    if "GC_F" not in df_full["ticker"].values:
        return False
    csv_row = df_full.loc[df_full["ticker"] == "GC_F"].iloc[0]
    if pd.isna(csv_row.get("med_252d")):
        return False
    path = reader.ticker_path(data_dir, "commodities", "GC_F")
    if not path.exists():
        return False
    prices = reader.load(path)["close"].dropna().sort_index()
    rets = [r for dt in matched if (r := _uncapped_forward_return(prices, dt, FWD_DAYS)) is not None]
    if len(rets) < MIN_N_OBS:
        return False
    same_n   = abs(len(rets) - csv_row["n_matched"]) <= 5
    same_med = abs(float(pd.Series(rets).median()) - csv_row["med_252d"]) < 0.01
    return same_n and same_med


def _rank_universe_fresh(matched: pd.DatetimeIndex, data_dir: Path, top_n: int) -> tuple[list[str], dict[str, str]]:
    """Fallback gate-1 ranking — same conditional-median-252d-return ranking
    used by run_universe_screen.py, computed only for the live regime (not
    the full universe screen's broader yfinance-fetched Swedish/UCITS set).
    Only runs when no valid cached ranking exists on disk for the current
    regime. No history-length cutoff, by design (see MIN_N_OBS comment above)."""
    rows = []
    cat_of: dict[str, str] = {}
    for cat_dir in ("equities", "commodities", "intl_etfs"):
        d = data_dir / cat_dir
        if not d.exists():
            continue
        for f in sorted(d.glob("*.parquet")):
            prices = reader.load(f)["close"].dropna().sort_index()
            if len(prices) < 50:
                continue
            rets = [
                r for dt in matched
                if (r := _uncapped_forward_return(prices, dt, FWD_DAYS)) is not None
            ]
            if len(rets) < MIN_N_OBS:
                continue
            rows.append({"ticker": f.stem, "median": float(pd.Series(rets).median())})
            cat_of[f.stem] = cat_dir

    rows.sort(key=lambda r: -r["median"])
    top = rows[:top_n]
    return [r["ticker"] for r in top], cat_of


def get_regime_candidates(conditions: dict, top_n: int, data_dir: Path) -> tuple[list[str], dict[str, str], str]:
    """Returns (tickers, ticker->category_dir map, source description)."""
    matched = _matched_dates(conditions, data_dir)
    if UNIVERSE_CSV.exists():
        df_full = pd.read_csv(UNIVERSE_CSV)
        if _csv_matches_live_regime(df_full, matched, data_dir):
            ranked = df_full.sort_values("rank").head(top_n)
            cat_of = {row.ticker: CATEGORY_DIR.get(row.category, "equities") for row in ranked.itertuples()}
            return ranked["ticker"].tolist(), cat_of, f"{UNIVERSE_CSV.name} (validated against live regime)"
    tickers, cat_of = _rank_universe_fresh(matched, data_dir, top_n)
    return tickers, cat_of, "computed fresh (no valid cached ranking found for live regime)"


# ── Gate 2: explicit above-MA50 check + display stats ───────────────────────

def _ma50_stats(data_dir: Path, cat_dir: str, ticker: str) -> dict | None:
    path = reader.ticker_path(data_dir, cat_dir, ticker)
    if not path.exists():
        return None
    prices = reader.load(path)["close"].dropna().sort_index()
    if len(prices) < 50:
        return None
    ma50 = prices.rolling(50, min_periods=25).mean()
    price, ma = float(prices.iloc[-1]), float(ma50.iloc[-1])
    if pd.isna(ma):
        return None
    return {
        "price":     price,
        "ma50":      ma,
        "dist_pct":  price / ma - 1,
        "above_ma50": price > ma,
        "as_of":     str(prices.index[-1].date()),
    }


# ── Main screen ───────────────────────────────────────────────────────────

def run_entry_screen(
    top_n: int = 30,
    hold_days: int = 21,
    benchmark: str = "SPY",
    data_dir: Path | None = None,
    as_of: str | None = None,
) -> pd.DataFrame:
    if data_dir is None:
        data_dir = config.raw_data_dir()

    regime = current_regime(data_dir)
    conditions = {
        "ry_regime":     regime["regimes"]["ry_regime"],
        "baa10y_regime": regime["regimes"]["baa10y_regime"],
    }

    candidates, cat_of, source = get_regime_candidates(conditions, top_n, data_dir)

    print("=" * 100)
    print("OPPORTUNISTIC ENTRY SCREEN")
    print("=" * 100)
    print(f"  Data as of      : {regime['date']}" + (f"  (--as-of {as_of} requested)" if as_of else ""))
    print(f"  Regime          : ry={conditions['ry_regime']}  baa10y={conditions['baa10y_regime']}  "
          f"(confidence: {regime['confidence']})")
    print(f"  Gate 1 source   : {source}")
    print(f"  Gate 1 candidates (top {top_n}): {', '.join(candidates)}")
    if as_of:
        print("  NOTE: --as-of replays MA50/regime from snapshot data, but the earnings-date")
        print("        gate (engine._next_earnings) always queries yfinance's LIVE calendar —")
        print("        it cannot be replayed retroactively. Treat gate 4 here as illustrative only.")
    print()

    # Group candidates by category dir, run screen_tactical (gates 3+4) per group
    survivors_frames = []
    by_cat: dict[str, list[str]] = {}
    for t in candidates:
        by_cat.setdefault(cat_of.get(t, "equities"), []).append(t)

    for cat_dir, tickers in by_cat.items():
        df = screen_tactical(
            conditions, tickers,
            category=cat_dir, benchmark=benchmark, hold_days=hold_days,
            data_dir=data_dir,
        )
        if not df.empty:
            survivors_frames.append(df)

    survivors = pd.concat(survivors_frames, ignore_index=True) if survivors_frames else pd.DataFrame()
    survivor_set = set(survivors["ticker"]) if not survivors.empty else set()

    # Build the combined table for every gate-1 candidate
    rows = []
    today = _date.today()
    for i, t in enumerate(candidates, 1):
        ma = _ma50_stats(data_dir, cat_of.get(t, "equities"), t)
        earn_date = _next_earnings(t)
        earn_days = (earn_date - today).days if earn_date else None
        gate2_pass = bool(ma and ma["above_ma50"])
        gate34_pass = t in survivor_set  # not-extended + RS + earnings, per screen_tactical
        verdict = "ENTER" if (gate2_pass and gate34_pass) else "PASS"

        row = {
            "rank":          i,
            "ticker":        t,
            "price":         round(ma["price"], 2) if ma else None,
            "ma50":          round(ma["ma50"], 2) if ma else None,
            "dist_from_ma50": f"{ma['dist_pct']:+.1%}" if ma else "n/a",
            "ma50_status":   ("ABOVE" if gate2_pass else "BELOW") if ma else "no data",
            "next_earnings": str(earn_date) if earn_date else "n/a",
            "earn_in_days":  earn_days if earn_days is not None else "n/a",
            "gate2_ma50":    "PASS" if gate2_pass else "FAIL",
            "gate34_screen_tactical": "PASS" if gate34_pass else "FAIL",
            "verdict":       verdict,
        }
        rows.append(row)

    out = pd.DataFrame(rows)

    print(f"{'Rk':>3} {'Ticker':<9} {'Price':>9} {'MA50':>9} {'Dist':>8} {'Status':<8} "
          f"{'NextEarn':<12} {'Gate2':<6} {'Gate3+4':<8} {'Verdict':<7}")
    print("-" * 100)
    for _, r in out.iterrows():
        price_s = f"{r['price']:.2f}" if r["price"] is not None else "n/a"
        ma_s    = f"{r['ma50']:.2f}" if r["ma50"] is not None else "n/a"
        print(f"{r['rank']:>3} {r['ticker']:<9} {price_s:>9} {ma_s:>9} {r['dist_from_ma50']:>8} "
              f"{r['ma50_status']:<8} {r['next_earnings']:<12} {r['gate2_ma50']:<6} "
              f"{r['gate34_screen_tactical']:<8} {r['verdict']:<7}")

    entries = out[out["verdict"] == "ENTER"]["ticker"].tolist()
    print()
    print(f"  ENTER candidates (all 4 gates passed): {entries if entries else 'none'}")
    print("=" * 100)

    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Opportunistic entry screen (4-gate, war chest / home base capital).")
    parser.add_argument("--top-n", type=int, default=30, help="Gate-1 regime ranking depth (default 30)")
    parser.add_argument("--hold-days", type=int, default=21, help="Earnings avoidance window in days (default 21 = 3 weeks)")
    parser.add_argument("--benchmark", default="SPY", help="Benchmark for screen_tactical's RS gate (default SPY)")
    parser.add_argument("--data-dir", default=None, help="Override parquet data dir (e.g. a point-in-time snapshot)")
    parser.add_argument("--as-of", default=None, help="Label only — for documenting a retroactive replay (see --data-dir)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else None
    run_entry_screen(
        top_n=args.top_n,
        hold_days=args.hold_days,
        benchmark=args.benchmark,
        data_dir=data_dir,
        as_of=args.as_of,
    )
