"""
run_sleeve_sector_capitulation_reconstruction.py

Second candidate from the opp-sleeve edge-type review (2026-07-29): does a
CORRELATED, sector-wide selloff predict a different (hopefully better)
forward outcome than an ordinary single-name crash? The existing sleeve
already has `discover_cluster_peers()` (run_entry_screen.py) for same-
sector grouping, but only uses it for stop-loss coordination on an
already-open position, never as its own entry signal. This tests whether
it should be one.

Trigger, reusing the ALREADY-VALIDATED crash convention from the AVGO/LLY
guard (CRASH_ROC_WINDOW=5, CRASH_ROC_THRESHOLD=-0.10, see
run_combined_system.py / run_crash_guard_validation.py) instead of
inventing a new threshold: a ticker qualifies if (a) it is itself in a
5-day/-10% crash, AND (b) it was in that period's frozen gate-1 top-N list
(same population discipline as the PEAD reconstruction -- "would the
sleeve already be watching this name," not a market-wide scan).

Entries are split into two buckets so solo idiosyncratic crashes can be
directly compared to correlated basket crashes on the SAME crash
definition and SAME population -- the open question from the original
review ("risk of just being a slower version of the existing extension
gate") is answered by whether the basket bucket looks meaningfully
different from solo, not by assumption:

  solo_crash   -- ticker crashing, no other same-sector gate-1 peer also
                  crashing the same day.
  basket_crash -- ticker crashing AND >=MIN_PEERS_CRASHING other same-
                  sector gate-1 peers ALSO crashing the same day.

Sector membership comes from yfinance's current `.info["sector"]` field
(one cached call per ticker), same source and same "current classification
applied retroactively" simplification `discover_cluster_peers()` already
uses live -- sector reassignment is rare enough for this candidate set
that the simplification is not expected to matter.

Forward return / win rate reuse run_sleeve_entry_reconstruction.
duration_stats() unchanged; early-stop-rate reuses
run_sleeve_pead_reconstruction.early_stop_rate() unchanged (both against
the CURRENT live binding_stop(), so results are directly comparable across
all three studies in this backlog).

Report-only. No gate, display flag, or live screen change made or implied
by running this script.

Usage:
    python run_sleeve_sector_capitulation_reconstruction.py
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    # write_through=True alone is NOT enough to make output stream live --
    # see MEMORY.md / run_sleeve_pead_reconstruction.py: it only bypasses
    # the text-encoding buffer, not the underlying binary buffer's own
    # batching. Every meaningful print below also needs flush=True.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", write_through=True)
warnings.filterwarnings("ignore")

import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module

import run_sleeve_entry_reconstruction as recon
from run_sleeve_pead_reconstruction import early_stop_rate, STOP_HORIZON_DAYS

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "sleeve_sector_capitulation_reconstruction_grid.csv"

# Same validated convention as the AVGO/LLY crash guard -- not a new threshold.
CRASH_ROC_WINDOW    = 5
CRASH_ROC_THRESHOLD = -0.10

MIN_PEERS_CRASHING = 2   # basket bucket requires >=2 other same-sector peers also crashing
DECLUSTER_MIN_GAP  = 30  # same as the original extension study


# ── Sector lookup: one cached call per ticker, current classification ──────

_sector_cache: dict[str, str | None] = {}


def _sector_of(ticker: str) -> str | None:
    if ticker in _sector_cache:
        return _sector_cache[ticker]
    try:
        import yfinance as yf
        sector = yf.Ticker(ticker).info.get("sector")
    except Exception:
        sector = None
    _sector_cache[ticker] = sector
    return sector


# ── Trigger: own crash + peer-crash count, per period ───────────────────────

def find_capitulation_entries(
    selections: list[dict],
    candidates: dict[str, tuple[str, pd.Series]],
) -> list[dict]:
    """For every period, build each top-N ticker's 5d ROC series once, then
    for every date check the ticker's own crash state plus how many OTHER
    same-sector top-N peers are also crashing that same date."""
    events: list[dict] = []
    n_periods = len(selections)

    for sel_idx, sel in enumerate(selections):
        start = sel["t_date"]
        end = selections[sel_idx + 1]["t_date"] if sel_idx + 1 < len(selections) else None
        top = sel["top"]
        print(f"  [{sel_idx + 1}/{n_periods}] period from {start.date()}, {len(top)} tickers "
              f"({len(_sector_cache)} sector lookups cached so far)...", flush=True)
        if len(top) < 1 + MIN_PEERS_CRASHING:
            continue  # not enough tickers in this period to ever form a basket

        sector_of_top = {t: _sector_of(t) for t in top}
        roc_by_ticker: dict[str, pd.Series] = {}
        for t in top:
            _cat, prices = candidates[t]
            period_prices = prices[(prices.index >= start) & (prices.index < end if end is not None else True)]
            roc_by_ticker[t] = period_prices.pct_change(CRASH_ROC_WINDOW)

        period_dates = sorted(set().union(*(s.index for s in roc_by_ticker.values()))) if roc_by_ticker else []
        for d in period_dates:
            crashing_today = {
                t for t, roc in roc_by_ticker.items()
                if d in roc.index and pd.notna(roc.loc[d]) and roc.loc[d] <= CRASH_ROC_THRESHOLD
            }
            for ticker in crashing_today:
                sector = sector_of_top.get(ticker)
                if sector is None:
                    continue
                peer_count = sum(
                    1 for other in crashing_today
                    if other != ticker and sector_of_top.get(other) == sector
                )
                bucket = "basket_crash" if peer_count >= MIN_PEERS_CRASHING else "solo_crash"
                events.append({"ticker": ticker, "date": d, "bucket": bucket, "n_peers_crashing": peer_count})
    return events


def main() -> None:
    print("=" * 72, flush=True)
    print("Opportunistic sleeve: sector-wide capitulation reconstruction", flush=True)
    print("Report-only -- no gate/display change implied by this run.", flush=True)
    print("=" * 72, flush=True)

    print("\nBuilding regime labels...", flush=True)
    labeled_df, _ = regime_module.build(DATA_DIR)

    print("Loading full candidate universe (same as extension study)...", flush=True)
    candidates = recon.load_candidates(DATA_DIR)
    print(f"Candidates: {len(candidates)}", flush=True)

    print("Detecting regime transitions + walk-forward gate-1 ranking...", flush=True)
    transitions = recon.detect_transitions(labeled_df)
    print(f"Transitions: {len(transitions)}", flush=True)
    selections = recon.rank_at_transitions(transitions, labeled_df, candidates, verbose=True)
    print("Gate-1 ranking done.", flush=True)

    print(f"Scanning for {CRASH_ROC_WINDOW}d/{CRASH_ROC_THRESHOLD:.0%} crashes "
          f"among gate-1 candidates, tagging same-sector peer-crash counts...", flush=True)
    raw_events = find_capitulation_entries(selections, candidates)
    print(f"Raw crash events: {len(raw_events)}", flush=True)

    entries = recon.decluster(raw_events, min_gap_days=DECLUSTER_MIN_GAP)
    print(f"Declustered (>= {DECLUSTER_MIN_GAP}d apart per ticker): {len(entries)}", flush=True)

    rows = []
    for label in ("solo_crash", "basket_crash"):
        bucket_entries = [e for e in entries if e["bucket"] == label]
        stats = recon.duration_stats(bucket_entries, candidates)
        stop_rate, stop_n = early_stop_rate(bucket_entries, candidates, horizon_days=STOP_HORIZON_DAYS)
        for _, r in stats.iterrows():
            rows.append({
                "bucket": label, "n_entries": len(bucket_entries),
                "calendar_days": r["calendar_days"], "n": r["n"],
                "median_return": r["median_return"], "win_rate": r["win_rate"],
                "annualized_median": r["annualized_median"],
                f"early_stop_rate_{STOP_HORIZON_DAYS}d": round(stop_rate, 4) if stop_rate == stop_rate else float("nan"),
                "early_stop_n": stop_n,
            })

    out = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n")
    print(out.to_string(index=False))
    print(
        "\nReading this: compare basket_crash to solo_crash at the same duration -- "
        "a lower early_stop_rate and/or higher median_return for basket_crash "
        "supports adding a basket-level signal; near-identical numbers mean this "
        "is just a slower version of the existing extension gate, not a new edge. "
        "Same live binding_stop() as the PEAD study, so both are directly "
        "comparable to each other and to MEMORY.md's execution-drift numbers."
    )


if __name__ == "__main__":
    main()
