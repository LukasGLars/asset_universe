import numpy as np
import pandas as pd
import pytest

from asset_universe.store import reader, writer


def _make_ohlcv(start: str = "2020-01-01", n: int = 5) -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=n)
    rng = np.random.default_rng(42)
    close = rng.uniform(90, 110, n)
    return pd.DataFrame({
        "date":   dates,
        "open":   close * rng.uniform(0.99, 1.01, n),
        "high":   close * rng.uniform(1.00, 1.02, n),
        "low":    close * rng.uniform(0.98, 1.00, n),
        "close":  close,
        "volume": rng.integers(1_000_000, 9_999_999, n).astype(float),
    })


def test_write_creates_file(tmp_path):
    path = tmp_path / "equities" / "AAPL.parquet"
    df = _make_ohlcv(n=5)
    n = writer.write_or_append(path, df)
    assert n == 5
    assert path.exists()


def test_append_non_overlapping(tmp_path):
    path = tmp_path / "equities" / "AAPL.parquet"
    df1 = _make_ohlcv("2020-01-01", 5)
    df2 = _make_ohlcv("2020-01-08", 5)
    writer.write_or_append(path, df1)
    n = writer.write_or_append(path, df2)
    assert n == 5
    assert len(pd.read_parquet(path)) == 10


def test_append_deduplicates(tmp_path):
    path = tmp_path / "equities" / "AAPL.parquet"
    df = _make_ohlcv(n=5)
    writer.write_or_append(path, df)
    n = writer.write_or_append(path, df)   # same data
    assert n == 0
    assert len(pd.read_parquet(path)) == 5


def test_last_date_missing_file(tmp_path):
    path = tmp_path / "equities" / "AAPL.parquet"
    assert reader.last_date(path) is None


def test_last_date_after_write(tmp_path):
    path = tmp_path / "equities" / "AAPL.parquet"
    df = _make_ohlcv("2020-06-01", 5)
    writer.write_or_append(path, df)
    last = reader.last_date(path)
    assert last is not None
    assert last >= "2020-06-01"


def test_load_date_filter(tmp_path):
    path = tmp_path / "equities" / "AAPL.parquet"
    df = _make_ohlcv("2020-01-01", 20)
    writer.write_or_append(path, df)
    loaded = reader.load(path, start="2020-01-20")
    assert len(loaded) < 20
    assert loaded.index.min() >= pd.Timestamp("2020-01-20")


def test_safe_name():
    assert reader.safe_name("GC=F")    == "GC_F"
    assert reader.safe_name("^VIX")    == "VIX"
    assert reader.safe_name("EURUSD=X") == "EURUSD_X"
    assert reader.safe_name("AAPL")    == "AAPL"


def test_ticker_path(tmp_path):
    path = reader.ticker_path(tmp_path, "commodities", "GC=F")
    assert path.name == "GC_F.parquet"
    assert path.parent.name == "commodities"
