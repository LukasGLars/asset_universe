"""
check_stld_live_price.py — ONE-OFF diagnostic, delete after use.

STLD showed up as the opp sleeve's ENTER candidate off yesterday's close
($259.74, +5.2% MA50 extension). User reports it then jumped +3.78%
overnight and is +2% further in premarket today -- asks whether buying now
means chasing well past the extension level that actually earned the
signal. This re-runs the same gate-3/4 tripwire check (RS-vs-benchmark,
cluster health, MA50 slope) and the MA50 extension calc, but with today's
LIVE quote spliced onto the historical series in-memory (never written to
the real parquet store), instead of yesterday's stale close.

Read-only. No commits, no state changes.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis.engine import current_regime
from asset_universe.store import reader

import run_entry_screen as es

DATA_DIR = config.raw_data_dir()
TICKER = "STLD"
BENCHMARK = "SPY"
CATEGORY = "equities"


def live_quote(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    info = t.info
    pre = info.get("preMarketPrice")
    post = info.get("postMarketPrice")
    reg = info.get("regularMarketPrice") or info.get("currentPrice")
    price = pre or post or reg
    return {"price": float(price), "pre": pre, "post": post, "regular": reg,
            "prev_close": info.get("previousClose")}


def main() -> None:
    stld_live = live_quote(TICKER)
    spy_live = live_quote(BENCHMARK)

    print("=" * 72)
    print("STLD live-price re-check (splicing today's quote onto stored history)")
    print("=" * 72)
    print(f"\nSTLD live quote : {stld_live}")
    print(f"SPY  live quote : {spy_live}\n")

    # Load real stored history.
    stld_path = reader.ticker_path(DATA_DIR, CATEGORY, TICKER)
    spy_path = reader.ticker_path(DATA_DIR, "equities", BENCHMARK)
    stld_hist = reader.load(stld_path)
    spy_hist = reader.load(spy_path)

    stld_stale_close = float(stld_hist["close"].dropna().iloc[-1])
    stld_stale_date = stld_hist.index[-1]

    # Splice today's live price on as a synthetic new row (in-memory only).
    today = pd.Timestamp.now().normalize()
    if today <= stld_stale_date:
        today = stld_stale_date + pd.Timedelta(days=1)
    stld_live_hist = stld_hist.copy()
    stld_live_hist.loc[today, "close"] = stld_live["price"]
    spy_live_hist = spy_hist.copy()
    if spy_live["price"]:
        spy_live_hist.loc[today, "close"] = spy_live["price"]

    # Monkeypatch reader.load so every downstream call transparently sees
    # the live-spliced series for STLD/SPY, unchanged for everything else
    # (VIX, cluster peers).
    _real_load = reader.load

    def _patched_load(path):
        if path == stld_path:
            return stld_live_hist
        if path == spy_path:
            return spy_live_hist
        return _real_load(path)

    reader.load = _patched_load
    es.reader.load = _patched_load

    try:
        # Extension vs MA50 at the live price.
        ma_stale = es._ma50_stats(DATA_DIR, CATEGORY, TICKER)
        # Force fresh MA50 stats using the live-spliced series too.
        ma_live_prices = stld_live_hist["close"].dropna().sort_index()
        ma50_live = ma_live_prices.rolling(50, min_periods=25).mean().iloc[-1]
        dist_live = stld_live["price"] / ma50_live - 1

        print(f"Stale (2026-07-28 close) : price=${stld_stale_close:.2f}  "
              f"MA50=${ma_stale['ma50']:.2f}  ext={ma_stale['dist_pct']:+.1%}")
        print(f"Live  (spliced today)    : price=${stld_live['price']:.2f}  "
              f"MA50=${ma50_live:.2f}  ext={dist_live:+.1%}\n")

        # Re-run the exact pre-entry tripwire gate (RS-vs-benchmark, cluster
        # health, MA50 slope) with the live-spliced series.
        regime = current_regime(DATA_DIR)
        conditions = regime["regimes"]
        gate1_candidates, cat_of, source, _ = es.get_regime_candidates(conditions, 30, DATA_DIR)
        held = es.already_held_tickers()

        passed, tw = es._pretrade_tripwire_check(
            TICKER, CATEGORY, gate1_candidates, held, conditions, DATA_DIR, BENCHMARK,
        )

        print("Gate 3+4 (pre-entry tripwire) re-checked at live price:")
        print(f"  RS vs {BENCHMARK} (20d)   : {tw['rs_20d']:+.1%}  (ok={tw['rs_ok']})")
        print(f"  Cluster breakdown     : {tw['cluster_breakdown']}  (peers: {tw['peer_rets']})")
        print(f"  MA50 slope rising     : {tw['ma50_rising']}  (slope={tw['ma50_slope']})")
        print(f"  Overall pre-entry gate: {'PASS' if passed else 'FAIL'}")
    finally:
        reader.load = _real_load
        es.reader.load = _real_load


if __name__ == "__main__":
    main()
