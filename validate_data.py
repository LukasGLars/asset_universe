"""
Data quality validation across all downloaded parquet files.
Checks: OHLC integrity, extreme returns, long gaps, staleness, FRED ranges.
"""

import warnings
warnings.filterwarnings("ignore")

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ── bootstrap package path ────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent / "src"))
from asset_universe import config
from asset_universe.store import reader

# ── config ────────────────────────────────────────────────────────────────────
DATA_DIR  = config.raw_data_dir()
TODAY     = pd.Timestamp(date.today())
STALE_THRESHOLD  = 5   # flag if last date > N bdays before today
GAP_THRESHOLD    = 10  # flag runs of missing bdays longer than this
RETURN_THRESHOLD = 0.5 # flag single-day |return| > 50%

KNOWN_EVENTS = {
    # ticker: [(date, reason)] — suppress false-positive flags
    "CL_F":    [("2020-04-20", "WTI negative price event")],
    "VIX":     [("2018-02-05", "Volmageddon spike")],
}

FRED_RANGES = {
    "T10Y3M":       (-3,   6),
    "T10Y2Y":       (-3,   4),
    "DFII10":       (-2,   5),
    "DTWEXBGS":     (80, 140),
    "BAMLH0A0HYM2": (1,   25),
    "PCEPILFE":     (50, 200),   # index level (not pct)
    "UNRATE":       (2,   15),
    "ICSA":         (150_000, 7_000_000),
}

OHLCV_CATEGORIES = ["equities", "intl_etfs", "commodities", "fixed_income", "fx", "volatility"]

# ── helpers ───────────────────────────────────────────────────────────────────

def bdays_before_today(last: pd.Timestamp) -> int:
    return len(pd.bdate_range(last + timedelta(days=1), TODAY))


def check_ohlcv_file(path: Path, ticker: str) -> list[dict]:
    issues = []

    try:
        df = pd.read_parquet(path)
    except Exception as e:
        return [{"ticker": ticker, "check": "read", "severity": "ERROR", "detail": str(e)}]

    if df.empty:
        return [{"ticker": ticker, "check": "empty", "severity": "ERROR", "detail": "no rows"}]

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    safe = reader.safe_name(ticker)
    known_dates = {d for d, _ in KNOWN_EVENTS.get(safe, [])}

    def flag(check, severity, detail):
        issues.append({"ticker": ticker, "check": check, "severity": severity, "detail": detail})

    # 1. Staleness
    last_date = df["date"].max()
    lag = bdays_before_today(last_date)
    if lag > STALE_THRESHOLD:
        flag("staleness", "WARN", f"last date {last_date.date()} ({lag} bdays ago)")

    # 2. Row count sanity (< 100 rows and > 2 years since first date)
    first_date = df["date"].min()
    years = (last_date - first_date).days / 365.25
    if years > 2 and len(df) < 200:
        flag("row_count", "WARN", f"only {len(df)} rows over {years:.1f} years")

    # 3. Non-positive close (excluding known events)
    if "close" in df.columns:
        bad = df[df["close"] <= 0]
        bad = bad[~bad["date"].dt.strftime("%Y-%m-%d").isin(known_dates)]
        if len(bad):
            flag("nonpositive_close", "ERROR",
                 f"{len(bad)} rows: {bad['date'].dt.strftime('%Y-%m-%d').tolist()[:3]}")

    # 4. OHLC integrity: high >= open/close, low <= open/close
    if all(c in df.columns for c in ["open", "high", "low", "close"]):
        bad_high = df[(df["high"] < df["close"] - 0.01) | (df["high"] < df["open"] - 0.01)]
        bad_low  = df[(df["low"]  > df["close"] + 0.01) | (df["low"]  > df["open"] + 0.01)]
        if len(bad_high):
            flag("ohlc_high", "ERROR",
                 f"high < open/close on {len(bad_high)} rows: {bad_high['date'].dt.strftime('%Y-%m-%d').tolist()[:3]}")
        if len(bad_low):
            flag("ohlc_low", "ERROR",
                 f"low > open/close on {len(bad_low)} rows: {bad_low['date'].dt.strftime('%Y-%m-%d').tolist()[:3]}")

    # 5. Extreme single-day returns (potential bad split)
    if "close" in df.columns:
        rets = df["close"].pct_change().abs()
        extreme = df[rets > RETURN_THRESHOLD]
        extreme = extreme[~extreme["date"].dt.strftime("%Y-%m-%d").isin(known_dates)]
        if len(extreme):
            dates_str = extreme["date"].dt.strftime("%Y-%m-%d").tolist()[:3]
            flag("extreme_return", "WARN",
                 f"|return| > 50% on {len(extreme)} days: {dates_str}")

    # 6. Long gaps
    bday_idx = pd.bdate_range(first_date, last_date)
    actual   = pd.DatetimeIndex(df["date"].values)
    missing  = bday_idx.difference(actual)
    if len(missing):
        # group into runs
        runs, run_start, prev = [], missing[0], missing[0]
        for d in missing[1:]:
            if (d - prev).days > 3:
                runs.append((run_start, prev))
                run_start = d
            prev = d
        runs.append((run_start, prev))
        long = [(s, e) for s, e in runs if len(pd.bdate_range(s, e)) > GAP_THRESHOLD]
        if long:
            detail = "; ".join(f"{s.date()}–{e.date()} ({len(pd.bdate_range(s,e))}bd)"
                               for s, e in long[:3])
            flag("long_gap", "WARN", detail)

    return issues


def check_fred_file(path: Path, sid: str) -> list[dict]:
    issues = []

    try:
        df = pd.read_parquet(path)
    except Exception as e:
        return [{"ticker": sid, "check": "read", "severity": "ERROR", "detail": str(e)}]

    if df.empty:
        return [{"ticker": sid, "check": "empty", "severity": "ERROR", "detail": "no rows"}]

    df["date"] = pd.to_datetime(df["date"])

    def flag(check, severity, detail):
        issues.append({"ticker": sid, "check": check, "severity": severity, "detail": detail})

    # Staleness (more lenient for monthly series)
    last_date = df["date"].max()
    lag = bdays_before_today(last_date)
    threshold = 35 if len(df) < 500 else STALE_THRESHOLD
    if lag > threshold:
        flag("staleness", "WARN", f"last date {last_date.date()} ({lag} bdays ago)")

    # Value range
    if sid in FRED_RANGES and "value" in df.columns:
        lo, hi = FRED_RANGES[sid]
        out_of_range = df[(df["value"] < lo) | (df["value"] > hi)]
        if len(out_of_range):
            vals = out_of_range["value"].tolist()[:3]
            flag("range", "WARN", f"{len(out_of_range)} values outside [{lo}, {hi}]: {vals}")

    # NaN infiltration
    if "value" in df.columns:
        n_nan = df["value"].isna().sum()
        if n_nan:
            flag("nan_values", "WARN", f"{n_nan} NaN rows")

    return issues


# ── run ───────────────────────────────────────────────────────────────────────

all_issues: list[dict] = []
category_stats: list[dict] = []

print("=" * 70)
print("DATA QUALITY VALIDATION")
print(f"Run date: {date.today()}")
print("=" * 70)

for category in OHLCV_CATEGORIES:
    tickers = reader.available_tickers(DATA_DIR, category)
    cat_issues = []

    for ticker in tickers:
        # reverse safe_name back to display (best effort)
        path = DATA_DIR / category / f"{ticker}.parquet"
        file_issues = check_ohlcv_file(path, ticker)
        cat_issues.extend(file_issues)

    errors = [i for i in cat_issues if i["severity"] == "ERROR"]
    warns  = [i for i in cat_issues if i["severity"] == "WARN"]
    verdict = "PASS" if not errors and not warns else ("FAIL" if errors else "WARN")

    print(f"\n[{category}]  {len(tickers)} files  |  "
          f"{len(errors)} errors  {len(warns)} warnings  →  {verdict}")

    for i in errors:
        print(f"  ERROR  {i['ticker']:<16} {i['check']:<20} {i['detail']}")
    for i in warns:
        print(f"  warn   {i['ticker']:<16} {i['check']:<20} {i['detail']}")

    all_issues.extend(cat_issues)
    category_stats.append({
        "category": category,
        "files": len(tickers),
        "errors": len(errors),
        "warnings": len(warns),
        "verdict": verdict,
    })

# FRED
fred_series_conf = config.load_fred_series()
fred_issues = []
for row in fred_series_conf:
    sid = row["series_id"]
    path = DATA_DIR / "macro" / f"{sid}.parquet"
    if not path.exists():
        fred_issues.append({"ticker": sid, "check": "missing", "severity": "ERROR", "detail": "file not found"})
        continue
    fred_issues.extend(check_fred_file(path, sid))

errors = [i for i in fred_issues if i["severity"] == "ERROR"]
warns  = [i for i in fred_issues if i["severity"] == "WARN"]
verdict = "PASS" if not errors and not warns else ("FAIL" if errors else "WARN")
print(f"\n[macro]  {len(fred_series_conf)} series  |  "
      f"{len(errors)} errors  {len(warns)} warnings  →  {verdict}")
for i in errors:
    print(f"  ERROR  {i['ticker']:<20} {i['check']:<20} {i['detail']}")
for i in warns:
    print(f"  warn   {i['ticker']:<20} {i['check']:<20} {i['detail']}")

all_issues.extend(fred_issues)
category_stats.append({
    "category": "macro",
    "files": len(fred_series_conf),
    "errors": len(errors),
    "warnings": len(warns),
    "verdict": verdict,
})

# ── summary ───────────────────────────────────────────────────────────────────

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
df_summary = pd.DataFrame(category_stats)
print(df_summary.to_string(index=False))

total_errors = sum(r["errors"] for r in category_stats)
total_warns  = sum(r["warnings"] for r in category_stats)
print(f"\nTotal: {total_errors} errors, {total_warns} warnings across "
      f"{sum(r['files'] for r in category_stats)} instruments")

# ── spot-check: sample 5 tickers, print last 3 rows ──────────────────────────
print(f"\n{'='*70}")
print("SPOT CHECK — last 3 rows for 5 sample tickers")
print(f"{'='*70}")
for ticker, category in [("AAPL","equities"), ("GC_F","commodities"),
                          ("TLT","fixed_income"), ("EURUSD_X","fx"), ("VIX","volatility")]:
    path = DATA_DIR / category / f"{ticker}.parquet"
    if path.exists():
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        print(f"\n{ticker} ({category})")
        print(df.tail(3).to_string(index=False))
