"""
run_opp_sleeve_extension_decile_analysis.py

Follow-on to run_sleeve_entry_reconstruction.py (PR #45): that script
established the real, point-in-time-gated entry population (4,321
declustered entries, 2009-2026) and measured forward return BY DURATION.
It never asked the orthogonal question: within that same gated population,
does forward return actually DEGRADE as MA50 extension increases (a real
dose-response), or is extension just a pass/fail gate with no further
information once a candidate is already inside it?

This matters because run_entry_screen.py's selection rule treats extension
as a tiebreaker (prefer the least-extended ROBUST candidate) but that
preference has never been backed by a decile-level return curve -- only by
the intuition that "less extended = less chased". This either confirms
that intuition with real numbers or shows it's not doing much once a
candidate has already cleared the binary "not extended" gate.

Reuses run_sleeve_entry_reconstruction.py's gates 1/2/4 verbatim (regime
top-N, above-MA50, earnings-clear) and its walk-forward, no-lookahead
ranking + frozen p67 extension thresholds -- this is NOT a new backtest
population, it's the same one, with the discarded `ext` value at each
gate-clearing event kept instead of thrown away.

Method: bucket the declustered entry population into extension deciles
(computed on the raw ext = price/MA50 - 1 value at entry, pooled across
all tickers/regimes -- NOT normalized by each entry's own frozen p67,
since the live screen's own displayed "ext" figure to the user is this
same raw quantity), then compute forward return at TIME_EXIT_DAYS=21
calendar days (matching the LIVE sleeve's current time exit) per decile.

Usage:
    python run_opp_sleeve_extension_decile_analysis.py
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

from run_sleeve_entry_reconstruction import (
    load_candidates,
    detect_transitions,
    rank_at_transitions,
    decluster,
    earnings_clear,
    forward_return,
)

DATA_DIR = config.raw_data_dir()
OUT_CSV = PROJECT_ROOT / "comparison_results" / "opp_sleeve_extension_decile.csv"

BENCHMARK = "SPY"
TIME_EXIT_DAYS = 21  # matches run_entry_screen.py's live TIME_EXIT_DAYS
N_BUCKETS = 10
MIN_N_OBS = 10


def find_gated_entries_with_ext(
    selections: list[dict],
    candidates: dict[str, tuple[str, pd.Series]],
    bm_prices: pd.Series,
) -> list[dict]:
    """Verbatim copy of run_sleeve_entry_reconstruction.find_gated_entries,
    with the one addition of keeping `ext` (the MA50-extension value at the
    gate-clearing date) on each event instead of discarding it."""
    bm_ret_20d = bm_prices.pct_change(20)

    all_top_tickers = {t for sel in selections for t in sel["top"]}
    ma50_by_ticker: dict[str, pd.Series] = {}
    ret20_by_ticker: dict[str, pd.Series] = {}
    for ticker in all_top_tickers:
        _cat, prices = candidates[ticker]
        ma50_by_ticker[ticker] = prices.rolling(50, min_periods=25).mean()
        ret20_by_ticker[ticker] = prices.pct_change(20)

    events: list[dict] = []
    for sel_idx, sel in enumerate(selections):
        start = sel["t_date"]
        end = selections[sel_idx + 1]["t_date"] if sel_idx + 1 < len(selections) else None
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
                if r20 is None or b20 is None or pd.isna(r20) or pd.isna(b20) or (r20 - b20) <= 0:
                    continue
                if not earnings_clear(ticker, d):
                    continue
                events.append({"ticker": ticker, "date": d, "ext": float(ext), "p67": float(p67)})
    return events


def main() -> None:
    print("Building regime labels...")
    labeled_df, _ = regime_module.build(DATA_DIR)

    print("Loading full candidate universe...")
    candidates = load_candidates(DATA_DIR)
    print(f"Candidates: {len(candidates)}")

    print("Detecting regime transitions...")
    transitions = detect_transitions(labeled_df)
    print(f"Transitions: {len(transitions)}")

    print("Walk-forward ranking at each transition...")
    selections = rank_at_transitions(transitions, labeled_df, candidates)

    print("Loading benchmark (SPY)...")
    bm_path = reader.ticker_path(DATA_DIR, "equities", BENCHMARK)
    bm_prices = reader.load(bm_path)["close"].dropna().sort_index()

    print("Scanning full history for gate-clearing (ticker, date, ext) events...")
    raw_events = find_gated_entries_with_ext(selections, candidates, bm_prices)
    print(f"Raw gate-clearing events: {len(raw_events)}")

    entries = decluster(raw_events)
    print(f"Declustered entry population: {len(entries)}")

    print(f"Computing {TIME_EXIT_DAYS}d forward returns per entry...")
    rows = []
    for e in entries:
        _cat, prices = candidates[e["ticker"]]
        r = forward_return(prices, e["date"], TIME_EXIT_DAYS)
        if r is not None:
            rows.append({"ticker": e["ticker"], "date": e["date"], "ext": e["ext"], "ret": r})
    df = pd.DataFrame(rows)
    print(f"Entries with valid {TIME_EXIT_DAYS}d forward return: {len(df)}")

    df["decile"] = pd.qcut(df["ext"], N_BUCKETS, labels=False, duplicates="drop")

    out_rows = []
    for dec, g in df.groupby("decile"):
        out_rows.append({
            "decile": int(dec) + 1,
            "ext_min": round(float(g["ext"].min()), 4),
            "ext_max": round(float(g["ext"].max()), 4),
            "ext_median": round(float(g["ext"].median()), 4),
            "n": len(g),
            "med_return": round(float(g["ret"].median()), 4) if len(g) >= MIN_N_OBS else None,
            "win_rate": round(float((g["ret"] > 0).mean()), 3) if len(g) >= MIN_N_OBS else None,
        })
    out = pd.DataFrame(out_rows)

    OUT_CSV.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n")
    print(out.to_string(index=False))

    valid = out.dropna(subset=["med_return"])
    corr = float(np.corrcoef(valid["ext_median"], valid["med_return"])[0, 1]) if len(valid) >= 3 else None
    print(f"\nCorrelation (decile ext_median vs decile med_return): {corr}")
    print(
        "\nReading this: each row is one extension decile of the REAL "
        f"gate-cleared, declustered entry population, at the live "
        f"{TIME_EXIT_DAYS}d duration. A negative correlation / declining "
        "med_return across deciles means less-extended entries really do "
        "perform better (validates the selection rule's tiebreaker). A "
        "flat or noisy pattern means extension isn't adding information "
        "beyond the existing binary gate. Informational only -- no change "
        "proposed without a follow-up go-ahead."
    )


if __name__ == "__main__":
    main()
