"""
run_opp_sleeve_entry_filter_sensitivity.py

Follow-on to the 2026-07-26 stop-logic work: with the exit side now fixed
(buffered MA50 + trailing stop + 21d time exit), this tests whether
TIGHTENING THE ENTRY side further -- beyond the 4 existing gates -- would
raise the win rate. Prompted directly by two live near-misses the same
day: STLD failed only on RS margin (RS vs SPY was -2.2%, just below the
existing >=0% bar) and GM failed on cluster health + a flattening MA50.

Tests four additional filters, individually and combined, on top of the
existing 4-gate real entry population (same reconstruction as
run_sleeve_entry_reconstruction.py / PR #45):

  1. RS margin -- currently the RS gate only requires >=0% (barely beating
     the benchmark). Tests requiring a real margin (>=2%/3%/5%).
  2. MA50 slope strength -- currently only requires the 50d average itself
     to be rising (any positive slope). Tests requiring top-tercile slope
     magnitude (a genuinely strong trend, not a barely-positive one).
  3. VIX-calm gate -- VIX is currently shown for context only, never a
     gate. Tests requiring VIX <= its own trailing 20d average at entry
     (the same "calm vs elevated" comparison already used post-entry).
  4. n_matched (diversity proxy) -- the live screen's ROBUST/MODERATE/THIN
     diversity label isn't reconstructable exactly here (it's built by a
     different live pipeline, universe_screen_results.csv). This uses the
     number of pre-transition regime-matched dates backing each period's
     gate-1 ranking as an approximate stand-in: more matched history should
     mean a more trustworthy ranking. NOT the same number the live system
     shows -- treat this filter's result as directional only.

Cluster health (GM's second failure reason) is NOT tested here -- point-
in-time sector-peer discovery across thousands of historical entries is a
separate, more expensive reconstruction, out of scope for this pass.

All configs measured at the sleeve's actual live duration (21 calendar
days, TIME_EXIT_DAYS as of 2026-07-26) -- this is about entry quality, not
duration, which was already settled in the stop-logic work.

Analysis only: no live rule changes without explicit operator go-ahead,
same discipline as every other study in this backlog.

Usage:
    python run_opp_sleeve_entry_filter_sensitivity.py
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
from asset_universe.analysis import regimes as regime_module
from asset_universe.store import reader

import run_sleeve_entry_reconstruction as recon

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "opp_sleeve_entry_filter_sensitivity.csv"

DURATION_DAYS = 21   # matches TIME_EXIT_DAYS as of 2026-07-26
MIN_N_OBS     = 10


def period_n_matched(labeled_df: pd.DataFrame, t_date: pd.Timestamp, ry: str, baa: str) -> int:
    """Recomputes the pre-transition matched-date count for one regime
    period -- the same population rank_at_transitions() uses internally to
    rank candidates, but not returned by it. Used here only as a rough
    diversity/robustness proxy (see module docstring caveat)."""
    hist = labeled_df[labeled_df.index < t_date]
    mask = (hist["ry_regime"] == ry) & (hist["baa10y_regime"] == baa)
    return int(mask.sum())


def find_gated_entries_with_diagnostics(
    selections: list[dict],
    candidates: dict[str, tuple[str, pd.Series]],
    bm_prices: pd.Series,
    labeled_df: pd.DataFrame,
    vix: pd.Series,
) -> list[dict]:
    """Same 4-gate logic as recon.find_gated_entries, but additionally
    records rs_margin, ma50_slope, n_matched, and vix_calm at each passing
    (ticker, date) -- the diagnostics this script's filters are built on."""
    bm_ret_20d = bm_prices.pct_change(20)
    vix_20d_avg = vix.rolling(20).mean()

    all_top_tickers = {t for sel in selections for t in sel["top"]}
    ma50_by_ticker: dict[str, pd.Series] = {}
    ret20_by_ticker: dict[str, pd.Series] = {}
    for ticker in all_top_tickers:
        _cat, prices = candidates[ticker]
        ma50_by_ticker[ticker] = prices.rolling(50, min_periods=25).mean()
        ret20_by_ticker[ticker] = prices.pct_change(20)

    n_matched_by_period = {
        sel["t_date"]: period_n_matched(labeled_df, sel["t_date"], sel["ry"], sel["baa"])
        for sel in selections
    }

    events: list[dict] = []
    for sel_idx, sel in enumerate(selections):
        start = sel["t_date"]
        end = selections[sel_idx + 1]["t_date"] if sel_idx + 1 < len(selections) else None
        n_matched = n_matched_by_period[start]
        for ticker in sel["top"]:
            if ticker not in sel["p67"]:
                continue
            p67 = sel["p67"][ticker]
            _cat, prices = candidates[ticker]
            ma50 = ma50_by_ticker[ticker]
            ret20 = ret20_by_ticker[ticker]

            period_dates = prices.index[(prices.index >= start) & (prices.index < end if end is not None else True)]
            for d in period_dates:
                price, ma = prices.loc[d], ma50.loc[d]
                if pd.isna(ma) or price <= ma:
                    continue
                ext = price / ma - 1
                if ext > p67:
                    continue
                r20 = ret20.loc[d] if d in ret20.index else None
                b20 = bm_ret_20d.loc[d] if d in bm_ret_20d.index else None
                if r20 is None or b20 is None or pd.isna(r20) or pd.isna(b20):
                    continue
                rs_margin = r20 - b20
                if rs_margin <= 0:
                    continue
                if not recon.earnings_clear(ticker, d):
                    continue

                pos = ma50.index.searchsorted(d)
                ma50_slope = (float(ma) - float(ma50.iloc[pos - 21])
                              if pos >= 21 and not pd.isna(ma50.iloc[pos - 21]) else None)

                vpos = vix.index.searchsorted(d)
                if vpos < len(vix) and abs((vix.index[vpos] - d).days) <= 5 and not pd.isna(vix_20d_avg.iloc[vpos]):
                    vix_calm = bool(vix.iloc[vpos] <= vix_20d_avg.iloc[vpos])
                else:
                    vix_calm = None

                events.append({
                    "ticker": ticker, "date": d,
                    "rs_margin": float(rs_margin), "ma50_slope": ma50_slope,
                    "n_matched": n_matched, "vix_calm": vix_calm,
                })
    return events


def rs_margin_at_least(e: dict, threshold: float) -> bool:
    return e["rs_margin"] >= threshold


def ma50_slope_at_least(e: dict, threshold: float) -> bool:
    return e["ma50_slope"] is not None and e["ma50_slope"] >= threshold


def vix_calm(e: dict) -> bool:
    return e["vix_calm"] is True


def diversity_at_least(e: dict, threshold: float) -> bool:
    return e["n_matched"] >= threshold


def summarize(entries: list[dict], candidates: dict[str, tuple[str, pd.Series]]) -> dict:
    rets = []
    for e in entries:
        _cat, prices = candidates[e["ticker"]]
        r = recon.forward_return(prices, e["date"], DURATION_DAYS)
        if r is not None:
            rets.append(r)
    n = len(rets)
    if n < MIN_N_OBS:
        return {"n": n, "median_return": None, "win_rate": None, "annualized": None}
    s = pd.Series(rets)
    med = float(s.median())
    return {
        "n": n,
        "median_return": round(med, 4),
        "win_rate": round(float((s > 0).mean()), 3),
        "annualized": round((1 + med) ** (365.25 / DURATION_DAYS) - 1, 4),
    }


def main() -> None:
    print("=" * 72)
    print("Opportunistic sleeve: entry-filter tightening sensitivity")
    print(f"(real 4-gate entry population, forward return at {DURATION_DAYS}d)")
    print("=" * 72)

    print("\nBuilding regime labels...")
    labeled_df, _ = regime_module.build(DATA_DIR)

    print("Loading full candidate universe...")
    candidates = recon.load_candidates(DATA_DIR)
    print(f"Candidates: {len(candidates)}")

    print("Detecting regime transitions + walk-forward ranking...")
    transitions = recon.detect_transitions(labeled_df)
    selections = recon.rank_at_transitions(transitions, labeled_df, candidates)

    print("Loading benchmark (SPY) and VIX...")
    bm_path = reader.ticker_path(DATA_DIR, "equities", recon.BENCHMARK)
    bm_prices = reader.load(bm_path)["close"].dropna().sort_index()
    vix = reader.load(reader.ticker_path(DATA_DIR, "volatility", "VIX"))["close"].dropna().sort_index()

    print("Scanning full history for the real 4-gate entry population + diagnostics...")
    raw_events = find_gated_entries_with_diagnostics(selections, candidates, bm_prices, labeled_df, vix)
    entries = recon.decluster(raw_events)
    print(f"Declustered real gated-entry population: {len(entries)}")

    slopes = [e["ma50_slope"] for e in entries if e["ma50_slope"] is not None]
    n_matched_vals = [e["n_matched"] for e in entries]
    slope_q67 = float(np.quantile(slopes, 2 / 3)) if slopes else None
    nmatch_q67 = float(np.quantile(n_matched_vals, 2 / 3))
    print(f"MA50 slope top-tercile cutoff: {slope_q67}")
    print(f"n_matched (diversity proxy) top-tercile cutoff: {nmatch_q67:.0f}")

    configs = [
        ("current (baseline)", lambda e: True),
        ("rs_margin>=2%", lambda e: rs_margin_at_least(e, 0.02)),
        ("rs_margin>=3%", lambda e: rs_margin_at_least(e, 0.03)),
        ("rs_margin>=5%", lambda e: rs_margin_at_least(e, 0.05)),
        ("ma50_slope_top_tercile", lambda e: ma50_slope_at_least(e, slope_q67)),
        ("vix_calm_only", vix_calm),
        ("diversity_proxy_top_tercile", lambda e: diversity_at_least(e, nmatch_q67)),
        ("combined_moderate (rs>=2% + vix_calm)",
         lambda e: rs_margin_at_least(e, 0.02) and vix_calm(e)),
        ("combined_strict (rs>=3% + vix_calm + slope + diversity)",
         lambda e: (rs_margin_at_least(e, 0.03) and vix_calm(e)
                    and ma50_slope_at_least(e, slope_q67) and diversity_at_least(e, nmatch_q67))),
    ]

    rows = []
    for label, f in configs:
        filtered = [e for e in entries if f(e)]
        stats = summarize(filtered, candidates)
        rows.append({"config": label, **stats})

    df = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n")
    print(df.to_string(index=False))
    print(
        "\nReading this: compare each row's median_return/win_rate/annualized/n against "
        "'current (baseline)' (today's live rule, all 4 gates, no extra filter). A real "
        "improvement should raise win_rate/median without n collapsing below ~30-50 (too "
        "few real trades a year to matter). diversity_proxy uses n_matched (pre-transition "
        "regime-matched date count) as a stand-in for the live ROBUST/MODERATE/THIN label -- "
        "not the same number the live screen shows, directional only. Cluster health is not "
        "tested here (out of scope this pass). Analysis only: no change to run_entry_screen.py "
        "without explicit operator go-ahead."
    )


if __name__ == "__main__":
    main()
