"""
run_opp_sleeve_execution_drift_analysis.py

Follow-on to the extension-decile analysis (which found extension level,
within the existing gate, has no dose-response with forward return). This
tests a different variable: does the price move BETWEEN when a candidate
qualifies (the screen's signal close) and when you can realistically
execute (the next session's open) predict trade outcome? Directly models
a real situation from this session -- STLD qualified off one day's close,
then gapped further overnight/premarket before it could be acted on.

Reuses the exact same walk-forward, no-lookahead reconstruction as
run_sleeve_entry_reconstruction.py (PR #45) for the gated-entry population
(same gates 1-4, same declustering) -- NOT a new backtest population.
Instead of measuring forward return from the qualifying close itself,
this measures it from the NEXT session's OPEN (a more realistic execution
price than the signal close), and buckets by the gap between the two --
the same gap_pct convention as run_avgo_gap_down_analysis.py, applied
here to entry timing instead of random days.

For each bucket, reports:
  - n
  - median forward return (21d, matching TIME_EXIT_DAYS, measured from
    the delayed execution price)
  - win rate
  - early-stop-out rate: fraction of entries whose CURRENT live stop
    logic (binding_stop() -- buffered MA50 or armed trailing stop,
    whichever binds) would trigger within the first EARLY_STOP_WINDOW
    trading days -- the SAME stop logic already validated and live in
    run_entry_screen.py, not a new stop rule invented for this study.

Usage:
    python run_opp_sleeve_execution_drift_analysis.py
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
import run_entry_screen as es

DATA_DIR = config.raw_data_dir()
OUT_CSV = PROJECT_ROOT / "comparison_results" / "opp_sleeve_execution_drift.csv"

BENCHMARK = "SPY"
TIME_EXIT_DAYS = 21          # matches run_entry_screen.py's live TIME_EXIT_DAYS
EARLY_STOP_WINDOW = 10       # trading days -- "quick failure" horizon, ~half the hold
N_BUCKETS = 8
MIN_N_OBS = 10


def load_candidates_with_open(data_dir: Path) -> tuple[dict, dict]:
    """Same universe/filtering as recon.load_candidates, but keeps both
    open and close (close for gate logic + MA50, open for the realistic
    delayed-execution price)."""
    candidates: dict[str, tuple[str, pd.Series]] = {}
    opens: dict[str, pd.Series] = {}
    for cat_dir in ("equities", "commodities"):
        d = data_dir / cat_dir
        if not d.exists():
            continue
        for path in sorted(d.glob("*.parquet")):
            t = path.stem
            if t in recon.EXCLUDE:
                continue
            df = reader.load(path)[["open", "close"]].dropna().sort_index()
            if len(df) >= 50:
                candidates[t] = (cat_dir, df["close"])
                opens[t] = df["open"]
    return candidates, opens


def forward_return_from_price(close: pd.Series, entry_idx: int, entry_price: float, calendar_days: int) -> float | None:
    """Same target-matching convention as recon.forward_return, but from
    an explicit entry price (the delayed-execution OPEN) rather than the
    close at entry_idx."""
    target = close.index[entry_idx] + pd.Timedelta(days=calendar_days)
    idx = close.index.searchsorted(target)
    if idx >= len(close) or abs((close.index[idx] - target).days) > 5:
        return None
    p1 = close.iloc[idx]
    return (p1 - entry_price) / entry_price if entry_price > 0 else None


def early_stop_out(close: pd.Series, ma50: pd.Series, entry_idx: int, entry_price: float, window: int) -> bool:
    """Walks forward `window` trading days using the live binding_stop()
    logic (buffered MA50 or armed trailing stop, whichever binds) --
    True if the position would have been stopped out within that window."""
    peak = entry_price
    for i in range(entry_idx + 1, min(entry_idx + 1 + window, len(close))):
        price_t = float(close.iloc[i])
        peak = max(peak, price_t)
        ma50_t = ma50.iloc[i]
        if pd.isna(ma50_t):
            continue
        stop_price, _ = es.binding_stop(entry_price, float(ma50_t), peak)
        if price_t < stop_price:
            return True
    return False


def main() -> None:
    print("Building regime labels...")
    labeled_df, _ = regime_module.build(DATA_DIR)

    print("Loading full candidate universe (open+close)...")
    candidates, opens = load_candidates_with_open(DATA_DIR)
    print(f"Candidates: {len(candidates)}")

    print("Detecting regime transitions...")
    transitions = recon.detect_transitions(labeled_df)
    print(f"Transitions: {len(transitions)}")

    print("Walk-forward ranking at each transition...")
    selections = recon.rank_at_transitions(transitions, labeled_df, candidates)

    print("Loading benchmark (SPY)...")
    bm_path = reader.ticker_path(DATA_DIR, "equities", BENCHMARK)
    bm_prices = reader.load(bm_path)["close"].dropna().sort_index()

    print("Scanning full history for gate-clearing (ticker, date) events...")
    raw_events = recon.find_gated_entries(selections, candidates, bm_prices)
    print(f"Raw gate-clearing events: {len(raw_events)}")

    entries = recon.decluster(raw_events)
    print(f"Declustered entry population: {len(entries)}")

    print("Precomputing MA50 per ticker...")
    ma50_by_ticker = {
        t: close.rolling(50, min_periods=25).mean()
        for t, (_cat, close) in candidates.items()
    }

    print("Computing execution-drift buckets...")
    rows = []
    for e in entries:
        ticker, d0 = e["ticker"], e["date"]
        close = candidates[ticker][1]
        open_ = opens.get(ticker)
        if open_ is None:
            continue
        idx0 = close.index.searchsorted(d0)
        if idx0 >= len(close) or abs((close.index[idx0] - d0).days) > 5:
            continue
        entry_idx = idx0 + 1
        if entry_idx >= len(close):
            continue
        signal_close = float(close.iloc[idx0])
        exec_date = close.index[entry_idx]
        if exec_date not in open_.index or signal_close <= 0:
            continue
        entry_price = float(open_.loc[exec_date])
        drift = entry_price / signal_close - 1

        fwd_ret = forward_return_from_price(close, entry_idx, entry_price, TIME_EXIT_DAYS)
        if fwd_ret is None:
            continue
        stopped_early = early_stop_out(close, ma50_by_ticker[ticker], entry_idx, entry_price, EARLY_STOP_WINDOW)

        rows.append({"ticker": ticker, "drift": drift, "ret": fwd_ret, "stopped_early": stopped_early})

    df = pd.DataFrame(rows)
    print(f"Entries with valid drift + forward return: {len(df)}")

    df["bucket"] = pd.qcut(df["drift"], N_BUCKETS, labels=False, duplicates="drop")

    out_rows = []
    for b, g in df.groupby("bucket"):
        out_rows.append({
            "bucket": int(b) + 1,
            "drift_min": round(float(g["drift"].min()), 4),
            "drift_max": round(float(g["drift"].max()), 4),
            "drift_median": round(float(g["drift"].median()), 4),
            "n": len(g),
            "med_return": round(float(g["ret"].median()), 4) if len(g) >= MIN_N_OBS else None,
            "win_rate": round(float((g["ret"] > 0).mean()), 3) if len(g) >= MIN_N_OBS else None,
            "early_stop_rate": round(float(g["stopped_early"].mean()), 3) if len(g) >= MIN_N_OBS else None,
        })
    out = pd.DataFrame(out_rows)

    OUT_CSV.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n")
    print(out.to_string(index=False))

    valid = out.dropna(subset=["med_return"])
    corr_ret = float(np.corrcoef(valid["drift_median"], valid["med_return"])[0, 1]) if len(valid) >= 3 else None
    valid_stop = out.dropna(subset=["early_stop_rate"])
    corr_stop = float(np.corrcoef(valid_stop["drift_median"], valid_stop["early_stop_rate"])[0, 1]) if len(valid_stop) >= 3 else None
    print(f"\nCorrelation (bucket drift_median vs med_return): {corr_ret}")
    print(f"Correlation (bucket drift_median vs early_stop_rate): {corr_stop}")
    print(
        "\nReading this: drift = next session's OPEN vs. the signal day's "
        "CLOSE -- how much the price already moved before a realistic "
        "execution. A negative return-correlation / positive "
        "stop-rate-correlation means chasing a candidate that's already "
        "moved costs you return AND raises the odds of an early stop-out. "
        "early_stop_rate uses the SAME live binding_stop() logic as "
        f"run_entry_screen.py, checked over the first {EARLY_STOP_WINDOW} "
        "trading days. Informational only -- no change proposed without a "
        "follow-up go-ahead."
    )


if __name__ == "__main__":
    main()
