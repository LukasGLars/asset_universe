import re
from pathlib import Path

import pandas as pd


def safe_name(ticker: str) -> str:
    """Convert a ticker to a filesystem-safe filename stem."""
    return re.sub(r"[^\w]", "_", ticker).strip("_") or ticker


def ticker_path(data_dir: Path, category: str, ticker: str) -> Path:
    return data_dir / category / f"{safe_name(ticker)}.parquet"


def last_date(path: Path) -> str | None:
    """Return ISO date string of last row, or None if file doesn't exist."""
    if not path.exists():
        return None
    df = pd.read_parquet(path, columns=["date"])
    return df["date"].max().strftime("%Y-%m-%d")


def load(
    path: Path,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Load a parquet file, optionally filtered by date range. Date becomes index."""
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    if start:
        df = df[df["date"] >= pd.Timestamp(start)]
    if end:
        df = df[df["date"] <= pd.Timestamp(end)]
    return df.set_index("date").sort_index()


def load_by_ticker(
    data_dir: Path,
    category: str,
    ticker: str,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    return load(ticker_path(data_dir, category, ticker), start=start, end=end)


def available_tickers(data_dir: Path, category: str) -> list[str]:
    """List tickers that have data files in a category."""
    cat_dir = data_dir / category
    if not cat_dir.exists():
        return []
    return [p.stem for p in sorted(cat_dir.glob("*.parquet"))]
