"""
run_opp_sleeve_basket_execution_drift_analysis.py

Does basket_crash need its OWN execution-drift threshold, or is the
extension gate's 0.9% (built 2026-07-29) a reasonable fit? Direct
follow-on to a live case (SNDK, 2026-07-30): signal close $1015.89,
reversed +24.2% to $1261.80 by the very next session. The basket_crash
execution-drift filter was just shipped reusing the extension gate's
threshold verbatim, explicitly flagged as an unvalidated stopgap (see
MEMORY.md "Execution-drift filter added to basket_crash"). This measures
whether that number actually fits, using the SAME methodology as the
original execution-drift study (MEMORY.md "Opp sleeve execution-drift
analysis", 2026-07-29):

  1. Bucket real basket_crash entries by (next session's OPEN / signal
     CLOSE - 1) -- the realistic gap between when a candidate is flagged
     and when you can actually fill an order.
  2. Simulate forward outcome from that REALISTIC entry point (next
     session's open, not the signal close), using basket_crash's own
     validated stop -- trailing-only, 8%/8%, NO floor (a floor destroys
     this population's edge, see "Capitulation stop-sensitivity",
     2026-07-29). Duration 21 calendar days, matching the live pathway.
  3. Report median return, win rate, and early-stop rate (stopped within
     the first 10 trading days -- the "quick failure" signal that
     revealed the U-shape in the original study) per drift bucket.

Population: the real declustered basket_crash entries from
run_sleeve_sector_capitulation_reconstruction.py (reruns that
reconstruction's pipeline -- ~15-20 min, dominated by
rank_at_transitions(), same long pole logged throughout this backlog).

Report-only. No gate, threshold, or live screen change made or implied
by running this script.

Usage:
    python run_opp_sleeve_basket_execution_drift_analysis.py
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", write_through=True)
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.store import reader

import run_sleeve_entry_reconstruction as recon
import run_sleeve_sector_capitulation_reconstruction as cap

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "opp_sleeve_basket_execution_drift_grid.csv"

DURATION_DAYS        = 21    # matches the live basket_crash flat-21d exit
TRAILING_TRIGGER_PCT = 0.08  # live basket_crash params -- validated, not re-tuned here
TRAILING_PCT         = 0.08
N_BUCKETS            = 5     # ~60 entries/bucket at n=299 -- thinner than the extension
                              # study's 8 buckets (n=3,641) but the smallest workable split
EARLY_STOP_WINDOW_DAYS = 10  # trading days -- same "quick failure" window as the original study

_open_cache: dict[str, pd.Series] = {}


def _open_prices(ticker: str, category: str) -> pd.Series | None:
    if ticker in _open_cache:
        return _open_cache[ticker]
    path = reader.ticker_path(DATA_DIR, category, ticker)
    if not path.exists():
        _open_cache[ticker] = None
        return None
    s = reader.load(path)["open"].dropna().sort_index()
    _open_cache[ticker] = s
    return s


def compute_drift(entry: dict, candidates: dict[str, tuple[str, pd.Series]]) -> float | None:
    """(next session's open / signal close - 1) -- same convention as the
    original execution-drift study, applied to the basket_crash trigger
    date instead of the extension gate's qualifying date."""
    category, close_prices = candidates[entry["ticker"]]
    signal_idx = close_prices.index.searchsorted(entry["date"])
    if signal_idx >= len(close_prices) or abs((close_prices.index[signal_idx] - entry["date"]).days) > 5:
        return None
    entry_idx = signal_idx + 1
    if entry_idx >= len(close_prices):
        return None
    signal_close = float(close_prices.iloc[signal_idx])
    next_date = close_prices.index[entry_idx]

    open_prices = _open_prices(entry["ticker"], category)
    if open_prices is None or next_date not in open_prices.index:
        return None
    next_open = float(open_prices.loc[next_date])
    if signal_close <= 0 or next_open <= 0:
        return None
    return next_open / signal_close - 1


def simulate_trade_from_next_open(
    close_prices: pd.Series,
    open_prices: pd.Series,
    signal_date: pd.Timestamp,
    duration_days: int,
    trailing_trigger_pct: float,
    trailing_pct: float,
) -> dict | None:
    """Same walk-forward mechanics as run_opp_sleeve_capitulation_stop_
    sensitivity.simulate_trade() with hard_stop_pct=None (the only
    validated basket_crash config), but entry is realistically filled at
    the NEXT session's OPEN instead of the signal close -- matching the
    original execution-drift study's convention. Returns days_to_stop
    (trading-day offset from entry) so the caller can classify "early"
    (quick-failure) stops, same distinction the original study made."""
    signal_idx = close_prices.index.searchsorted(signal_date)
    if signal_idx >= len(close_prices) or abs((close_prices.index[signal_idx] - signal_date).days) > 5:
        return None
    entry_idx = signal_idx + 1
    if entry_idx >= len(close_prices):
        return None
    entry_date = close_prices.index[entry_idx]
    if entry_date not in open_prices.index:
        return None
    entry_price = float(open_prices.loc[entry_date])
    if entry_price <= 0:
        return None
    peak = entry_price
    target_date = entry_date + pd.Timedelta(days=duration_days)

    exit_price, stopped, days_to_stop = None, False, None
    i = entry_idx
    while True:
        i += 1
        if i >= len(close_prices) or close_prices.index[i] > target_date:
            break
        price = float(close_prices.iloc[i])
        peak = max(peak, price)
        if (peak / entry_price - 1) >= trailing_trigger_pct:
            binding = peak * (1 - trailing_pct)
            if price <= binding:
                exit_price, stopped, days_to_stop = price, True, i - entry_idx
                break

    if exit_price is None:
        idx = close_prices.index.searchsorted(target_date)
        if idx >= len(close_prices):
            idx = len(close_prices) - 1
        if close_prices.index[idx] > target_date and idx > entry_idx:
            idx -= 1
        if idx <= entry_idx:
            return None
        exit_price = float(close_prices.iloc[idx])

    return {
        "return": (exit_price - entry_price) / entry_price,
        "stopped": stopped,
        "days_to_stop": days_to_stop,
    }


def main() -> None:
    print("=" * 72, flush=True)
    print("Basket-crash execution-drift bucket analysis", flush=True)
    print("Report-only -- no gate/threshold change implied by this run.", flush=True)
    print("=" * 72, flush=True)

    print("\nBuilding regime labels...", flush=True)
    labeled_df, _ = regime_module.build(DATA_DIR)

    print("Loading candidate universe...", flush=True)
    candidates = recon.load_candidates(DATA_DIR)
    print(f"Candidates: {len(candidates)}", flush=True)

    print("Detecting transitions + walk-forward gate-1 ranking (long pole, ~15-20min)...", flush=True)
    transitions = recon.detect_transitions(labeled_df)
    selections = recon.rank_at_transitions(transitions, labeled_df, candidates, verbose=True)

    print(f"\nScanning for {cap.CRASH_ROC_WINDOW}d/{cap.CRASH_ROC_THRESHOLD:.0%} crashes, "
          f"tagging same-sector peer-crash counts...", flush=True)
    raw_events = cap.find_capitulation_entries(selections, candidates)
    entries = recon.decluster(raw_events, min_gap_days=cap.DECLUSTER_MIN_GAP)
    basket_entries = [e for e in entries if e["bucket"] == "basket_crash"]
    print(f"basket_crash entries: {len(basket_entries)}", flush=True)

    print("\nComputing next-open/signal-close drift for each entry...", flush=True)
    rows = []
    for i, e in enumerate(basket_entries, 1):
        if i % 50 == 0:
            print(f"  [{i}/{len(basket_entries)}]...", flush=True)
        drift = compute_drift(e, candidates)
        if drift is None:
            continue
        category, close_prices = candidates[e["ticker"]]
        open_prices = _open_prices(e["ticker"], category)
        trade = simulate_trade_from_next_open(
            close_prices, open_prices, e["date"], DURATION_DAYS,
            TRAILING_TRIGGER_PCT, TRAILING_PCT,
        )
        if trade is None:
            continue
        rows.append({
            "ticker": e["ticker"], "date": e["date"], "drift": drift,
            "return": trade["return"], "stopped": trade["stopped"],
            "days_to_stop": trade["days_to_stop"],
        })

    df = pd.DataFrame(rows)
    print(f"\nUsable entries (drift + simulated trade both available): {len(df)}", flush=True)
    if len(df) < N_BUCKETS * 10:
        print("WARNING: thin population for the requested bucket count -- read results with caution.", flush=True)

    df = df.sort_values("drift").reset_index(drop=True)
    df["bucket"] = pd.qcut(df["drift"], N_BUCKETS, labels=False, duplicates="drop")

    out_rows = []
    for b in sorted(df["bucket"].unique()):
        sub = df[df["bucket"] == b]
        n = len(sub)
        med_drift = float(sub["drift"].median())
        med_return = float(sub["return"].median())
        win_rate = float((sub["return"] > 0).mean())
        stopped_pct = float(sub["stopped"].mean())
        early_stop = sub[(sub["stopped"]) & (sub["days_to_stop"] <= EARLY_STOP_WINDOW_DAYS)]
        early_stop_rate = len(early_stop) / n if n else float("nan")
        out_rows.append({
            "bucket": int(b) + 1, "n": n, "drift_median": round(med_drift, 4),
            "med_return": round(med_return, 4), "win_rate": round(win_rate, 3),
            "stopped_pct": round(stopped_pct, 3),
            f"early_stop_rate_{EARLY_STOP_WINDOW_DAYS}d": round(early_stop_rate, 3),
        })

    out = pd.DataFrame(out_rows)
    OUT_CSV.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n", flush=True)
    print(out.to_string(index=False), flush=True)
    print(
        "\nReading this: look for the bucket(s) with the LOWEST early_stop_rate -- that's the "
        "'sweet spot' drift range the original extension-gate study used to derive its 0.9% "
        "threshold. If a similar sweet spot exists here, its outer edge is the candidate "
        "threshold for basket_crash specifically. If early_stop_rate is high and flat across "
        "ALL buckets (not U-shaped), that suggests drift isn't the driver for this population "
        "and a different filter (or none) may be more appropriate -- report honestly either way, "
        "this is not a search for a specific answer.",
        flush=True,
    )

    # Raw per-entry rows -- a bucket median can hide its own tail (e.g. a
    # SNDK-magnitude +24% drift could sit inside the top bucket's +3.17%
    # MEDIAN without being visible in the aggregate table above). Saved so
    # the extreme-drift entries specifically can be inspected directly,
    # without re-running the ~15-20min pipeline again.
    entries_csv = PROJECT_ROOT / "comparison_results" / "opp_sleeve_basket_execution_drift_entries.csv"
    df.to_csv(entries_csv, index=False)
    print(f"\nSaved raw per-entry rows: {entries_csv}", flush=True)

    print(f"\n{'='*72}\nTAIL DRILLDOWN: the 15 entries with the LARGEST absolute drift\n"
          f"(closest in magnitude to the SNDK live case, +24.2%)\n{'='*72}", flush=True)
    tail = df.reindex(df["drift"].abs().sort_values(ascending=False).index).head(15)
    for _, r in tail.iterrows():
        stop_note = f"stopped day {int(r['days_to_stop'])}" if r["stopped"] else "held to 21d exit"
        print(f"  {r['ticker']:<8} {str(r['date'].date()):<12} drift={r['drift']:+7.1%}  "
              f"return={r['return']:+7.1%}  {stop_note}", flush=True)
    n_extreme = int((df["drift"].abs() >= 0.10).sum())
    print(f"\nEntries with |drift| >= 10% (same order of magnitude as SNDK): {n_extreme} of {len(df)}", flush=True)
    if n_extreme > 0:
        extreme = df[df["drift"].abs() >= 0.10]
        print(f"  Of those: median return {extreme['return'].median():+.1%}, "
              f"win rate {(extreme['return'] > 0).mean():.1%}, "
              f"stopped {extreme['stopped'].mean():.1%}", flush=True)


if __name__ == "__main__":
    main()
