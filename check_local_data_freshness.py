"""
check_local_data_freshness.py

Guards against the failure mode from 2026-07-07: the local `data/` parquet
store (gitignored, never synced anywhere -- see .gitignore) only refreshes
when someone explicitly runs `python -m asset_universe.update`. Nothing
checked its age before local analysis scripts trusted it, and it sat a full
week stale (last updated 2026-06-30) without any warning, which nearly
produced a wrong "HWM has breached its stop" claim during a session that
used it directly.

This is UNRELATED to the live GitHub Actions pipeline (daily-sync /
sync-sheet / check_sync_health.py), which has its own fresh cache per run
and was never affected -- this script only guards local, ad-hoc analysis.

Usage: run this FIRST, before any local script that reads from data/raw/.
Auto-refreshes if stale (more than 1 trading day behind, weekends
excluded) rather than just warning, since the fix is one command either way.
"""
from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from asset_universe import config
from asset_universe.store import reader

REFERENCE_TICKER = ("equities", "SPY")
MAX_STALE_TRADING_DAYS = 1


def _last_trading_day_before(today: dt.date) -> dt.date:
    """Most recent weekday before today (yesterday, or Friday if today is
    Mon/weekend) -- doesn't need holiday-awareness, just needs to not
    falsely flag a fresh Friday close as stale over the weekend."""
    d = today - dt.timedelta(days=1)
    while d.weekday() >= 5:  # Saturday=5, Sunday=6
        d -= dt.timedelta(days=1)
    return d


def check_freshness(data_dir: Path, today: dt.date | None = None) -> tuple[bool, dt.date, dt.date]:
    """Returns (is_fresh, latest_date_in_store, required_since)."""
    today = today or dt.date.today()
    cat, ticker = REFERENCE_TICKER
    path = reader.ticker_path(data_dir, cat, ticker)
    prices = reader.load(path)["close"].dropna().sort_index()
    latest = prices.index[-1].date()
    required_since = _last_trading_day_before(today) - dt.timedelta(days=MAX_STALE_TRADING_DAYS - 1)
    return latest >= required_since, latest, required_since


def main() -> int:
    data_dir = config.raw_data_dir()
    is_fresh, latest, required_since = check_freshness(data_dir)

    if is_fresh:
        print(f"LOCAL DATA: fresh (latest {latest}, required since {required_since}).")
        return 0

    print(f"LOCAL DATA: stale -- latest is {latest}, required since {required_since}. Refreshing...")
    result = subprocess.run([sys.executable, "-m", "asset_universe.update"],
                             cwd=Path(__file__).parent, capture_output=True, text=True)
    if result.returncode != 0:
        print("LOCAL DATA: refresh FAILED -- do not trust local analysis until this is fixed.")
        print(result.stderr[-2000:])
        return 1

    is_fresh_now, latest_now, _ = check_freshness(data_dir)
    if not is_fresh_now:
        print(f"LOCAL DATA: still stale after refresh (latest {latest_now}) -- "
              f"market may just not have a newer close yet, or check yfinance access.")
        return 1
    print(f"LOCAL DATA: refreshed, now fresh (latest {latest_now}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
