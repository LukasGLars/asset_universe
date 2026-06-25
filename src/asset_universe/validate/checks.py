import pandas as pd


def check_ohlcv(df: pd.DataFrame, ticker: str = "") -> list[str]:
    """
    Run basic sanity checks on an OHLCV DataFrame (date index, close column).
    Returns a list of issue strings; empty list means clean.
    """
    issues = []

    if "close" not in df.columns:
        return ["missing close column"]

    close = df["close"]

    n_zero = int((close <= 0).sum())
    if n_zero:
        # CL=F April 2020 is a known legitimate negative price event
        issues.append(f"non_positive_close: {n_zero} rows")

    rets = close.pct_change().dropna()
    extreme = rets[(rets > 0.90) | (rets < -0.70)]
    if len(extreme):
        dates = ", ".join(extreme.index.strftime("%Y-%m-%d").tolist()[:3])
        issues.append(f"extreme_returns: {len(extreme)} days ({dates})")

    return issues


def check_gaps(df: pd.DataFrame, ticker: str = "") -> list[str]:
    """
    Detect multi-day gaps in a date-indexed DataFrame.
    Only flags gaps > 5 business days (excludes normal holiday clusters).
    """
    if df.empty:
        return ["empty dataframe"]

    issues = []
    dates = pd.DatetimeIndex(df.index).sort_values()
    bday_gaps = pd.bdate_range(dates[0], dates[-1])
    missing = bday_gaps.difference(dates)

    # Group consecutive missing days into runs
    if len(missing) == 0:
        return []

    runs = []
    run_start = missing[0]
    prev = missing[0]
    for d in missing[1:]:
        if (d - prev).days > 3:
            runs.append((run_start, prev))
            run_start = d
        prev = d
    runs.append((run_start, prev))

    long_gaps = [(s, e) for s, e in runs if len(pd.bdate_range(s, e)) > 5]
    for s, e in long_gaps:
        issues.append(f"gap {s.date()} to {e.date()} ({len(pd.bdate_range(s,e))} bdays)")

    return issues
