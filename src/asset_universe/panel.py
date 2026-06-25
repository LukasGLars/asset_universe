"""
Panel layer: load cross-sectional price and return panels from the parquet store.
Uses DuckDB to read all files in a single query — fast even across 500+ tickers.

Typical usage:
    from asset_universe import panel, config

    data_dir = config.raw_data_dir()
    prices  = panel.load_panel(data_dir, "equities", start="2010-01-01")
    returns = panel.load_returns(data_dir, "equities", start="2010-01-01")
    meta    = panel.universe_metadata(data_dir, ["equities", "commodities", "fx"])
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


def _to_list(x: str | list[str]) -> list[str]:
    return [x] if isinstance(x, str) else list(x)


def _build_union_sql(
    data_dir: Path,
    categories: list[str],
    field: str,
    start: str | None,
    end: str | None,
) -> tuple[str, int]:
    """Build UNION ALL SQL across all parquet files. Returns (sql, file_count)."""
    parts = []
    for category in categories:
        cat_dir = data_dir / category
        if not cat_dir.exists():
            continue
        for f in sorted(cat_dir.glob("*.parquet")):
            path = str(f).replace("\\", "/")
            parts.append(
                f"SELECT CAST(date AS DATE) AS date, "
                f"'{f.stem}' AS ticker, "
                f"CAST({field} AS DOUBLE) AS val "
                f"FROM read_parquet('{path}')"
            )

    if not parts:
        return "", 0

    union = " UNION ALL ".join(parts)
    filters = []
    if start:
        filters.append(f"date >= DATE '{start}'")
    if end:
        filters.append(f"date <= DATE '{end}'")
    where = f"WHERE {' AND '.join(filters)}" if filters else ""

    sql = (
        f"SELECT date, ticker, val "
        f"FROM ({union}) sub "
        f"{where} "
        f"ORDER BY date, ticker"
    )
    return sql, len(parts)


def load_panel(
    data_dir: Path,
    categories: str | list[str],
    field: str = "close",
    start: str | None = None,
    end: str | None = None,
    min_history_days: int = 0,
    ffill: bool = True,
    ffill_limit: int = 5,
) -> pd.DataFrame:
    """
    Load a wide price panel from the parquet store.

    Returns a DataFrame:
        index   = date (daily, union of all trading calendars)
        columns = tickers
        values  = `field` (default: adjusted close)

    Tickers with ragged starts show NaN until their first available date.
    Forward-fill (ffill=True) closes gaps from differing holiday calendars.

    Parameters
    ----------
    categories : str or list of str
        Category name(s) matching subdirectories under data_dir.
        E.g. "equities", ["equities", "commodities", "fixed_income"].
    field : str
        Column to extract — "close", "open", "high", "low", "volume".
    start, end : str | None
        ISO date strings to filter the panel.
    min_history_days : int
        Drop tickers with fewer rows than this threshold. Useful to exclude
        very recent IPOs from long-horizon analysis.
    ffill : bool
        Forward-fill up to ffill_limit periods to handle cross-calendar gaps.
    ffill_limit : int
        Maximum consecutive NaN periods to fill.
    """
    sql, n_files = _build_union_sql(data_dir, _to_list(categories), field, start, end)
    if n_files == 0:
        return pd.DataFrame()

    con = duckdb.connect()
    try:
        raw = con.execute(sql).df()
    finally:
        con.close()

    if raw.empty:
        return pd.DataFrame()

    panel = (
        raw.pivot(index="date", columns="ticker", values="val")
        .rename_axis(None, axis=1)
        .sort_index()
    )
    panel.index = pd.to_datetime(panel.index)

    if min_history_days > 0:
        panel = panel.loc[:, panel.count() >= min_history_days]

    if ffill:
        panel = panel.ffill(limit=ffill_limit)

    return panel


def load_returns(
    data_dir: Path,
    categories: str | list[str],
    field: str = "close",
    start: str | None = None,
    end: str | None = None,
    min_history_days: int = 0,
    log: bool = False,
) -> pd.DataFrame:
    """
    Daily returns panel.

    log=False (default): simple returns  r_t = (p_t / p_{t-1}) - 1
    log=True           : log returns     r_t = ln(p_t / p_{t-1})

    Log returns are preferred for:
      - summing across time (compounding)
      - normality assumptions in risk models
    Simple returns are preferred for:
      - cross-sectional portfolio arithmetic
      - comparing with benchmark attribution
    """
    prices = load_panel(
        data_dir, categories, field=field,
        start=start, end=end,
        min_history_days=min_history_days,
        ffill=True,
    )
    if prices.empty:
        return pd.DataFrame()

    if log:
        return np.log(prices / prices.shift(1))
    return prices.pct_change(fill_method=None)


def universe_metadata(
    data_dir: Path,
    categories: str | list[str],
) -> pd.DataFrame:
    """
    Summary table for the stored universe.

    Returns one row per ticker with columns:
        ticker, category, first_date, last_date, n_rows
    """
    rows = []
    for category in _to_list(categories):
        cat_dir = data_dir / category
        if not cat_dir.exists():
            continue
        for f in sorted(cat_dir.glob("*.parquet")):
            df = pd.read_parquet(f, columns=["date"])
            df["date"] = pd.to_datetime(df["date"])
            rows.append({
                "ticker":     f.stem,
                "category":   category,
                "first_date": df["date"].min().date(),
                "last_date":  df["date"].max().date(),
                "n_rows":     len(df),
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["ticker", "category", "first_date", "last_date", "n_rows"]
    )
