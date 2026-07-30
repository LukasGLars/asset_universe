"""
run_gap_up_forward_return_analysis.py

Direct follow-on to the basket_crash execution-drift study: that study's
299-entry population had almost no data anywhere near SNDK's live
magnitude (+24.2% overnight gap) -- the largest upward drift observed was
only +7.7%, and the tail drilldown found a moderate +6.3% gap-up entry
(XYZ, 2020-02-26) still lost -50.9% with no floor to catch it. That's too
thin a sample to say anything about a 20-30% gap specifically.

This broadens the population: instead of only basket_crash-qualified
entries (crash + peer confirmation + gate-1 membership), scan the FULL
candidate universe (490+ tickers, full history) for ANY overnight gap-up
of this magnitude, regardless of context. Much bigger sample, and it
skips the expensive walk-forward gate-1 ranking entirely (~15-20min in
every other script in this backlog) since it isn't gate-1-conditioned --
should run in well under a minute.

Method:
  1. A "gap-up event" is a day whose OPEN is >= threshold above the PRIOR
     day's close (thresholds: 15%, 20%, 30% -- bracketing SNDK's +24.2%).
  2. Entry is realistically filled AT that day's open (you can't buy at
     the printed signal close once it's already gapped).
  3. Forward outcome simulated with the SAME trailing-only stop
     basket_crash actually uses live (8%/8% trigger/trailing, NO floor --
     a floor destroyed this population's edge, see "Capitulation
     stop-sensitivity", 2026-07-29), 21 calendar days.
  4. Declustered per ticker (>=30 calendar days apart, same convention as
     every other reconstruction in this backlog) so one volatile name in
     one stretch doesn't dominate the sample.

Not basket_crash-specific (no peer-crash confirmation, no gate-1
membership) -- this answers the narrower, general question "what tends
to happen after a huge overnight gap-up, regardless of cause," which is
the actual open question about SNDK's magnitude specifically.

Report-only. No gate, threshold, or live screen change made or implied
by running this script.

Usage:
    python run_gap_up_forward_return_analysis.py
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

import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.store import reader

import run_sleeve_entry_reconstruction as recon

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "gap_up_forward_return_grid.csv"

DURATION_DAYS        = 21
TRAILING_TRIGGER_PCT = 0.08  # same live basket_crash params -- not re-tuned here
TRAILING_PCT         = 0.08
DECLUSTER_MIN_GAP    = 30    # same convention as every other reconstruction in this backlog

GAP_BANDS = [(0.15, 0.20), (0.20, 0.30), (0.30, float("inf"))]  # brackets SNDK's +24.2%


def simulate_trade_from_own_open(
    close_prices: pd.Series,
    open_prices: pd.Series,
    event_date: pd.Timestamp,
    duration_days: int,
    trailing_trigger_pct: float,
    trailing_pct: float,
) -> dict | None:
    """Entry filled AT the gap-up day's own open (the event itself, not a
    signal-then-next-session split like the basket_crash drift study --
    here the gap IS the entry trigger). Same trailing-only, no-floor walk-
    forward mechanics as basket_crash_binding_stop()."""
    if event_date not in close_prices.index or event_date not in open_prices.index:
        return None
    entry_idx = close_prices.index.get_loc(event_date)
    entry_price = float(open_prices.loc[event_date])
    if entry_price <= 0:
        return None
    peak = entry_price
    target_date = event_date + pd.Timedelta(days=duration_days)

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


def find_gap_up_events(candidates: dict[str, tuple[str, pd.Series]]) -> list[dict]:
    events = []
    for ticker, (category, close_prices) in candidates.items():
        path = reader.ticker_path(DATA_DIR, category, ticker)
        if not path.exists():
            continue
        open_prices = reader.load(path)["open"].dropna().sort_index()
        common = close_prices.index.intersection(open_prices.index)
        if len(common) < 2:
            continue
        close_aligned = close_prices.loc[common]
        open_aligned = open_prices.loc[common]
        prior_close = close_aligned.shift(1)
        gap = open_aligned / prior_close - 1
        hits = gap[gap >= GAP_BANDS[0][0]].dropna()
        for dt, g in hits.items():
            events.append({"ticker": ticker, "date": dt, "gap": float(g), "category": category})
    return events


def main() -> None:
    print("=" * 72, flush=True)
    print("Gap-up forward-return analysis (full universe, not basket_crash-gated)", flush=True)
    print("Report-only -- no gate/threshold change implied by this run.", flush=True)
    print("=" * 72, flush=True)

    print("\nLoading candidate universe...", flush=True)
    candidates = recon.load_candidates(DATA_DIR)
    print(f"Candidates: {len(candidates)}", flush=True)

    print(f"\nScanning for overnight gap-ups >= {GAP_BANDS[0][0]:.0%}...", flush=True)
    raw_events = find_gap_up_events(candidates)
    print(f"Raw gap-up events: {len(raw_events)}", flush=True)

    entries = recon.decluster(raw_events, min_gap_days=DECLUSTER_MIN_GAP)
    print(f"Declustered (>= {DECLUSTER_MIN_GAP}d apart per ticker): {len(entries)}", flush=True)

    rows = []
    for e in entries:
        _cat, close_prices = candidates[e["ticker"]]
        path = reader.ticker_path(DATA_DIR, e["category"], e["ticker"])
        open_prices = reader.load(path)["open"].dropna().sort_index()
        trade = simulate_trade_from_own_open(
            close_prices, open_prices, e["date"], DURATION_DAYS,
            TRAILING_TRIGGER_PCT, TRAILING_PCT,
        )
        if trade is None:
            continue
        rows.append({
            "ticker": e["ticker"], "date": e["date"], "gap": e["gap"],
            "return": trade["return"], "stopped": trade["stopped"],
            "days_to_stop": trade["days_to_stop"],
        })

    df = pd.DataFrame(rows)
    print(f"\nUsable entries: {len(df)}", flush=True)

    entries_csv = PROJECT_ROOT / "comparison_results" / "gap_up_forward_return_entries.csv"
    df.to_csv(entries_csv, index=False)
    print(f"Saved raw entries: {entries_csv}", flush=True)

    print(f"\n{'='*72}\nBY GAP-SIZE BAND\n{'='*72}", flush=True)
    band_rows = []
    for lo, hi in GAP_BANDS:
        sub = df[(df["gap"] >= lo) & (df["gap"] < hi)]
        n = len(sub)
        if n == 0:
            band_rows.append({"band": f"{lo:.0%}-{hi:.0%}" if hi != float("inf") else f">={lo:.0%}",
                               "n": 0, "med_return": None, "win_rate": None, "stopped_pct": None})
            continue
        band_rows.append({
            "band": f"{lo:.0%}-{hi:.0%}" if hi != float("inf") else f">={lo:.0%}",
            "n": n,
            "med_return": round(float(sub["return"].median()), 4),
            "win_rate": round(float((sub["return"] > 0).mean()), 3),
            "stopped_pct": round(float(sub["stopped"].mean()), 3),
        })
    band_out = pd.DataFrame(band_rows)
    band_out.to_csv(OUT_CSV, index=False)
    print(band_out.to_string(index=False), flush=True)

    print(f"\n{'='*72}\nEntries closest to SNDK's own gap (+24.2%), within +/-5pp\n{'='*72}", flush=True)
    near_sndk = df[(df["gap"] >= 0.192) & (df["gap"] <= 0.292)].sort_values("gap")
    if near_sndk.empty:
        print("  None found in this band.", flush=True)
    else:
        for _, r in near_sndk.iterrows():
            stop_note = f"stopped day {int(r['days_to_stop'])}" if r["stopped"] else "held to 21d exit"
            print(f"  {r['ticker']:<8} {str(r['date'].date()):<12} gap={r['gap']:+7.1%}  "
                  f"return={r['return']:+7.1%}  {stop_note}", flush=True)

    print(
        "\nReading this: n at SNDK's own magnitude band may still be thin (real market history has "
        "far fewer 20%+ overnight gap-ups than smaller ones) -- report the actual n honestly, don't "
        "round up to a stronger claim than the sample supports. Compare med_return/win_rate ACROSS "
        "bands for a dose-response read: if outcomes get worse as gap size increases, that supports "
        "a magnitude cap; if flat or improving, the earlier bucket-based finding (upside drift isn't "
        "punished) extends further than the basket_crash-only population suggested.",
        flush=True,
    )


if __name__ == "__main__":
    main()
