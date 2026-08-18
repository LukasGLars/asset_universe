"""
Incremental daily data refresh.

Usage:
    python -m asset_universe.update          # update everything
    python -m asset_universe.update --dry    # show what would be fetched
"""

import sys
import time
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from . import config
from .download import fred as fred_dl
from .download import yf as yf_dl
from .store import reader, writer

CATEGORIES = {
    "equities":     "us_equities",
    "se_equities":  "se_equities",
    "intl_etfs":    "intl_etfs",
    "commodities":  "commodities",
    "fixed_income": "fixed_income",
    "fx":           "fx",
    "volatility":   "volatility",
}

# 5-minute buffer past NYSE's 4:00pm ET close.
_MARKET_CLOSE_ET = dt_time(16, 5)


def _next_fetch_start(path: Path, default_start: str) -> str:
    last = reader.last_date(path)
    if last is None:
        return default_start
    return (pd.Timestamp(last) + timedelta(days=1)).strftime("%Y-%m-%d")


def _yf_fetch_end() -> str:
    """yfinance's `end` is exclusive (end="2023-01-01" -> last bar is
    2022-12-31), unlike FRED's `observation_end`, which is inclusive.
    Fetching with end=today therefore always drops today's own close --
    a real one-trading-day lag, not just a run-timing symptom.

    Only extend to tomorrow (so today's close is included) once NYSE has
    actually closed, checked in NY local time so it's correct across the
    US/EU DST mismatch weeks -- a fixed UTC cron offset alone doesn't
    reliably land after close year-round. Otherwise (e.g. a manual
    workflow_dispatch or watchdog re-trigger firing mid-session) fetching
    today would risk capturing a live, not-yet-final intraday print as if
    it were a completed close -- and since `_next_fetch_start` never
    revisits an already-recorded date, that bad value would stick until
    the next calendar day's fetch happens to overwrite it, which it won't."""
    ny_now = datetime.now(ZoneInfo("America/New_York"))
    if ny_now.time() < _MARKET_CLOSE_ET:
        return ny_now.date().isoformat()
    return (ny_now.date() + timedelta(days=1)).isoformat()


def run(dry: bool = False) -> None:
    settings = config.load_settings()
    start = settings["data"]["start_date"]
    data_dir = config.raw_data_dir()
    sleep_yf = settings["fetch"]["yf_sleep_seconds"]
    sleep_fred = settings["fetch"]["fred_sleep_seconds"]
    today = date.today().isoformat()
    yf_fetch_end = _yf_fetch_end()

    print(f"Update: {today}{'  [DRY RUN]' if dry else ''}")
    print("=" * 60)

    total_new = 0
    errors: list[tuple[str, str]] = []

    for category, universe_name in CATEGORIES.items():
        tickers = config.load_universe(universe_name)
        print(f"\n[{category}]  {len(tickers)} tickers")

        for ticker in tickers:
            path = reader.ticker_path(data_dir, category, ticker)
            fetch_start = _next_fetch_start(path, start)

            if fetch_start > today:
                print(f"  {ticker:<16} up-to-date")
                continue

            if dry:
                print(f"  {ticker:<16} would fetch {fetch_start} to {today}")
                continue

            try:
                df = yf_dl.fetch(ticker, fetch_start, yf_fetch_end)
                if df is None or df.empty:
                    print(f"  {ticker:<16} no data returned")
                else:
                    n = writer.write_or_append(path, df)
                    total_new += n
                    print(f"  {ticker:<16} +{n} rows")
            except Exception as exc:
                msg = str(exc)
                print(f"  {ticker:<16} ERROR: {msg}")
                errors.append((ticker, msg))

            time.sleep(sleep_yf)

    # FRED
    fred_key = config.fred_api_key()
    if not fred_key:
        print("\n[macro]  FRED_API_KEY not set — skipping")
    else:
        from fredapi import Fred
        fred = Fred(api_key=fred_key)
        fred_series = config.load_fred_series()
        print(f"\n[macro]  {len(fred_series)} series")

        for row in fred_series:
            sid = row["series_id"]
            path = reader.ticker_path(data_dir, "macro", sid)
            fetch_start = _next_fetch_start(path, start)

            if fetch_start > today:
                print(f"  {sid:<20} up-to-date")
                continue

            if dry:
                print(f"  {sid:<20} would fetch {fetch_start} to {today}")
                continue

            try:
                df = fred_dl.fetch(sid, fetch_start, today, fred)
                if df is None or df.empty:
                    print(f"  {sid:<20} no data returned")
                else:
                    n = writer.write_or_append(path, df)
                    total_new += n
                    print(f"  {sid:<20} +{n} rows")
            except Exception as exc:
                msg = str(exc)
                print(f"  {sid:<20} ERROR: {msg}")
                errors.append((sid, msg))

            time.sleep(sleep_fred)

    print(f"\n{'='*60}")
    if not dry:
        print(f"Done.  {total_new} new rows written.")
    if errors:
        print(f"{len(errors)} error(s):")
        for name, err in errors:
            print(f"  {name}: {err}")


if __name__ == "__main__":
    run(dry="--dry" in sys.argv)
