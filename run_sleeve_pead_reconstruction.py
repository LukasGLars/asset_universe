"""
run_sleeve_pead_reconstruction.py

Tests the first candidate raised in the opp-sleeve "what other edge types
could this sleeve run" review (2026-07-29): post-earnings-announcement
drift (PEAD) -- does an earnings beat predict continued forward drift, the
same way the earnings-verdict message design already logged in MEMORY.md
assumed it might?

Deliberately independent of the live screen's existing gates (above-MA50,
extension<=p67): PEAD is a momentum-continuation mechanism, the existing
gates are mean-reversion. Stacking them here would muddy which mechanism
is doing the work. The only gate reused is gate 1 (regime top-N,
walk-forward, no lookahead) -- the population is "tickers the sleeve would
have already been watching," not the full market, since the question is
whether this fits INSIDE the existing sleeve, not whether PEAD exists
generically (it's a well-documented anomaly; that's not in question here).

Trigger: a real EPS surprise from yfinance's get_earnings_dates() (same
source + tz-handling fix already validated in
run_sleeve_entry_reconstruction._earnings_dates(), extended here to also
keep the Surprise(%) column instead of discarding it), for any ticker that
was in the live gate-1 top-N list at the time of the print. Entries are
bucketed by surprise magnitude; forward return and win rate reuse
run_sleeve_entry_reconstruction.duration_stats() unchanged (same duration
grid, same MIN_N_OBS bar) so results are directly comparable to the
existing reconstruction's numbers. Early-stop-out rate simulates the
CURRENT live binding_stop() (buffered MA50 / armed trailing stop, imported
directly from run_entry_screen.py -- not re-derived -- so this can't drift
out of sync with the live constants the way a copy-pasted value could).

Report-only. No gate, display flag, or live screen change made or implied
by running this script.

Usage:
    python run_sleeve_pead_reconstruction.py
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

import run_sleeve_entry_reconstruction as recon
from run_entry_screen import MA50_BUFFER_PCT, TRAILING_TRIGGER_PCT, TRAILING_PCT, binding_stop

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "sleeve_pead_reconstruction_grid.csv"

DECLUSTER_MIN_GAP = 60   # safety net only -- real earnings prints are ~90d apart per ticker
STOP_HORIZON_DAYS = 21   # matches HOLD_DAYS elsewhere in this backlog

# (label, lower_exclusive, upper_inclusive) on Surprise(%) as reported by yfinance
SURPRISE_BUCKETS = [
    ("miss_or_flat",    -np.inf, 0.0),
    ("beat_0_2",        0.0,     2.0),
    ("beat_2_5",        2.0,     5.0),
    ("beat_5_10",       5.0,     10.0),
    ("beat_10_plus",    10.0,    np.inf),
]


def _bucket_for(surprise: float) -> str | None:
    for label, lo, hi in SURPRISE_BUCKETS:
        if lo < surprise <= hi:
            return label
    return None


# ── Gate: real EPS surprise history, same tz-handling fix as recon._earnings_dates ──

_surprise_cache: dict[str, pd.DataFrame] = {}


def _earnings_surprises(ticker: str) -> pd.DataFrame:
    """Full historical (date, surprise_pct) for `ticker`, sorted, tz-naive.
    Same source and same tz-localize fix as
    run_sleeve_entry_reconstruction._earnings_dates(), but keeps the
    Surprise(%) column that function discards. Returns an empty frame on
    any fetch failure or missing column (gate then contributes no events,
    same fail-open convention as the rest of this backlog)."""
    if ticker in _surprise_cache:
        return _surprise_cache[ticker]
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).get_earnings_dates(limit=60)
        if df is None or df.empty or "Surprise(%)" not in df.columns:
            out = pd.DataFrame(columns=["date", "surprise"])
        else:
            idx = [d.replace(tzinfo=None) if d.tzinfo else d for d in df.index.to_pydatetime()]
            out = pd.DataFrame({
                "date": pd.to_datetime(idx),
                "surprise": df["Surprise(%)"].to_numpy(),
            }).dropna(subset=["surprise"]).sort_values("date").reset_index(drop=True)
    except Exception:
        out = pd.DataFrame(columns=["date", "surprise"])
    _surprise_cache[ticker] = out
    return out


# ── Entry extraction: gate-1 membership at print time + a real surprise ────

def find_pead_entries(
    selections: list[dict],
    candidates: dict[str, tuple[str, pd.Series]],
) -> list[dict]:
    """A print counts only if the ticker was in that period's frozen gate-1
    top-N list on the print date -- this is "would the sleeve have already
    been watching this name," not a market-wide PEAD scan."""
    events: list[dict] = []
    all_top_tickers = sorted({t for sel in selections for t in sel["top"]})
    n_tickers = len(all_top_tickers)
    print(f"  {n_tickers} unique gate-1 tickers to fetch earnings history for...")
    for i, ticker in enumerate(all_top_tickers, 1):
        print(f"  [{i}/{n_tickers}] {ticker}", flush=True)
        surprises = _earnings_surprises(ticker)
        if surprises.empty:
            continue
        for _, row in surprises.iterrows():
            d = row["date"]
            sel = recon.current_selection(selections, d)
            if sel is None or ticker not in sel["top"]:
                continue
            bucket = _bucket_for(float(row["surprise"]))
            if bucket is None:
                continue
            events.append({"ticker": ticker, "date": d, "surprise": float(row["surprise"]), "bucket": bucket})
    return events


# ── Early-stop-out rate against the CURRENT live binding_stop() ────────────

def early_stop_rate(
    entries: list[dict],
    candidates: dict[str, tuple[str, pd.Series]],
    horizon_days: int = STOP_HORIZON_DAYS,
) -> tuple[float, int]:
    """Fraction of entries whose live binding_stop() (buffered MA50 /
    armed trailing stop, imported from run_entry_screen.py) would have
    been breached within horizon_days of entry. Returns (rate, n)."""
    stopped = 0
    n = 0
    for e in entries:
        _cat, prices = candidates[e["ticker"]]
        ma50 = prices.rolling(50, min_periods=25).mean()
        entry_idx = prices.index.searchsorted(e["date"])
        if entry_idx >= len(prices) or abs((prices.index[entry_idx] - e["date"]).days) > 5:
            continue
        entry_price = float(prices.iloc[entry_idx])
        peak = entry_price
        target_date = e["date"] + pd.Timedelta(days=horizon_days)
        n += 1
        i = entry_idx
        while True:
            i += 1
            if i >= len(prices) or prices.index[i] > target_date:
                break
            price = float(prices.iloc[i])
            peak = max(peak, price)
            ma = ma50.iloc[i]
            if pd.isna(ma):
                continue
            stop_price, _label = binding_stop(entry_price, float(ma), peak)
            if price <= stop_price:
                stopped += 1
                break
    return (stopped / n if n else float("nan")), n


def main() -> None:
    print("=" * 72)
    print("Opportunistic sleeve: post-earnings-drift (PEAD) reconstruction")
    print("Report-only -- no gate/display change implied by this run.")
    print("=" * 72)

    print("\nBuilding regime labels...")
    labeled_df, _ = regime_module.build(DATA_DIR)

    print("Loading full candidate universe (same as extension study)...")
    candidates = recon.load_candidates(DATA_DIR)
    print(f"Candidates: {len(candidates)}")

    print("Detecting regime transitions + walk-forward gate-1 ranking...")
    transitions = recon.detect_transitions(labeled_df)
    selections = recon.rank_at_transitions(transitions, labeled_df, candidates)
    print(f"Transitions: {len(transitions)}")

    print("Scanning gate-1 candidates' full earnings history for real EPS surprises...")
    raw_events = find_pead_entries(selections, candidates)
    print(f"Raw surprise-bucket events: {len(raw_events)}")

    entries = recon.decluster(raw_events, min_gap_days=DECLUSTER_MIN_GAP)
    print(f"Declustered (safety net, >= {DECLUSTER_MIN_GAP}d apart per ticker): {len(entries)}")

    rows = []
    for label, _lo, _hi in SURPRISE_BUCKETS:
        bucket_entries = [e for e in entries if e["bucket"] == label]
        stats = recon.duration_stats(bucket_entries, candidates)
        stop_rate, stop_n = early_stop_rate(bucket_entries, candidates)
        for _, r in stats.iterrows():
            rows.append({
                "bucket": label, "n_entries": len(bucket_entries),
                "calendar_days": r["calendar_days"], "n": r["n"],
                "median_return": r["median_return"], "win_rate": r["win_rate"],
                "annualized_median": r["annualized_median"],
                f"early_stop_rate_{STOP_HORIZON_DAYS}d": round(stop_rate, 4) if not np.isnan(stop_rate) else float("nan"),
                "early_stop_n": stop_n,
            })

    out = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n")
    print(out.to_string(index=False))
    print(
        "\nReading this: compare median_return/win_rate across buckets -- a rising "
        "or plateauing curve from miss_or_flat to beat_10_plus supports PEAD; flat "
        "or inverted does not. early_stop_rate uses the CURRENT live binding_stop(), "
        "so it's directly comparable to the drift study's early-stop numbers in "
        "MEMORY.md. This is independent of the existing extension/MA50 gates by "
        "design -- combining them is a follow-on question, not answered here."
    )


if __name__ == "__main__":
    main()
