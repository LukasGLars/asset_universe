"""
run_avgo_guard_basket_crash_overlap.py -- ONE-OFF diagnostic, delete after use.

Operator's unease (2026-08-04), following up on the backlogged item in
MEMORY.md ("Backlogged: decompose the AVGO crash-ROC trigger's false-alarm
rate", 2026-08-03): when AVGO's crash-ROC guard fires (5d ROC <=-10%, same
threshold as fi_tracker.py's live guard), is AVGO's OWN crash more often a
solo idiosyncratic move or part of a sector-wide (semiconductor) selloff --
and does AVGO's own forward return differ between the two? This is the
direct version of "the guard flips AVGO to 0% on a sector crash, right
where basket_crash exists to buy the rebound on other names -- does AVGO
itself behave like a basket_crash candidate in that scenario, or like a
real breakdown?"

Peer set: a fixed list of large, liquid, long-history semiconductor peers
(same real-company approach as the existing sector-capitulation
reconstruction, not a fabricated list). Basket = AVGO crashing AND >=2 of
these peers ALSO in a 5d/-10% crash the same date (same MIN_PEERS_CRASHING
convention as run_sleeve_sector_capitulation_reconstruction.py). Solo =
AVGO crashing alone. Events declustered (min 30 trading days apart) so one
crash episode isn't counted many times.

Read-only. No commits, no state changes.
"""
from __future__ import annotations
import sys, io, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import pandas as pd

from asset_universe import config
from asset_universe.store import reader

TICKER = "AVGO"
CATEGORY = "equities"
PEERS = ["NVDA", "AMD", "INTC", "TXN", "QCOM", "MU", "AMAT", "LRCX", "KLAC", "ADI", "MRVL", "ON"]

CRASH_ROC_WINDOW    = 5
CRASH_ROC_THRESHOLD = -0.10
MIN_PEERS_CRASHING  = 2
DECLUSTER_MIN_GAP   = 30
FWD_HORIZONS        = [21, 63]


def _roc_series(prices: pd.Series, window: int) -> pd.Series:
    return prices / prices.shift(window) - 1


def _fetch_peer_prices(ticker: str) -> pd.Series | None:
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).history(period="max", auto_adjust=True)
        if df.empty:
            return None
        s = df["Close"].dropna()
        s.index = pd.to_datetime(s.index.date)
        return s.sort_index()
    except Exception:
        return None


def decluster(dates: list[pd.Timestamp], min_gap: int) -> list[pd.Timestamp]:
    kept = []
    for d in sorted(dates):
        if not kept or (d - kept[-1]).days > min_gap * 1.45:  # calendar-day proxy for trading-day gap
            kept.append(d)
    return kept


def main() -> None:
    data_dir = config.raw_data_dir()
    prices = reader.load(reader.ticker_path(data_dir, CATEGORY, TICKER))["close"].dropna().sort_index()
    roc = _roc_series(prices, CRASH_ROC_WINDOW)
    crash_dates_all = roc.index[roc <= CRASH_ROC_THRESHOLD]
    crash_dates = decluster(list(crash_dates_all), DECLUSTER_MIN_GAP)
    print(f"AVGO crash-ROC events (5d <=-10%), declustered: {len(crash_dates)}")

    peer_rocs = {}
    for p in PEERS:
        s = _fetch_peer_prices(p)
        if s is not None:
            peer_rocs[p] = _roc_series(s, CRASH_ROC_WINDOW)
    print(f"Peers with usable data: {sorted(peer_rocs)}")

    rows = []
    for d in crash_dates:
        peers_crashing = 0
        for p, proc in peer_rocs.items():
            idx = proc.index.searchsorted(d)
            if idx < len(proc.index) and abs((proc.index[idx] - d).days) <= 2:
                val = proc.iloc[idx]
                if pd.notna(val) and val <= CRASH_ROC_THRESHOLD:
                    peers_crashing += 1
        bucket = "basket" if peers_crashing >= MIN_PEERS_CRASHING else "solo"

        idx = prices.index.searchsorted(d)
        row = {"date": d.date(), "bucket": bucket, "peers_crashing": peers_crashing}
        for h in FWD_HORIZONS:
            fwd_idx = idx + h
            row[f"fwd_{h}d"] = (prices.iloc[fwd_idx] / prices.iloc[idx] - 1) if fwd_idx < len(prices) else None
        rows.append(row)

    df = pd.DataFrame(rows)
    print(f"\nEvents by bucket: {df['bucket'].value_counts().to_dict()}")

    def summarize(sub: pd.DataFrame, label: str) -> None:
        if len(sub) == 0:
            print(f"{label}: n=0")
            return
        print(f"\n{label} (n={len(sub)})")
        for h in FWD_HORIZONS:
            col = sub[f"fwd_{h}d"].dropna()
            if len(col) == 0:
                print(f"  {h}d: no usable observations")
                continue
            print(f"  {h}d: median {col.median():+.1%}  win {(col > 0).mean():.0%}  n={len(col)}")

    print("=" * 64)
    summarize(df[df["bucket"] == "solo"], "SOLO crash (AVGO alone)")
    summarize(df[df["bucket"] == "basket"], "BASKET crash (>=2 semi peers also crashing)")
    print("=" * 64)

    out_csv = Path(__file__).parent / "comparison_results" / "avgo_guard_basket_crash_overlap.csv"
    out_csv.parent.mkdir(exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_csv}")
    print("\nInformational only -- not wired into any live gate.")


if __name__ == "__main__":
    main()
