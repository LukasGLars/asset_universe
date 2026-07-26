import numpy as np
import pandas as pd
import pytest

from asset_universe import panel
from asset_universe.store import writer


# ── fixtures ──────────────────────────────────────────────────────────────────

def _make_prices(start: str, n: int, base: float = 100.0, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=n)
    returns = rng.normal(0, 0.01, n)
    closes = base * np.cumprod(1 + returns)
    return pd.DataFrame({
        "date":   dates,
        "open":   closes * rng.uniform(0.99, 1.00, n),
        "high":   closes * rng.uniform(1.00, 1.01, n),
        "low":    closes * rng.uniform(0.99, 1.00, n),
        "close":  closes,
        "volume": rng.integers(1_000_000, 9_999_999, n).astype(float),
    })


@pytest.fixture
def data_dir(tmp_path):
    """Populate a minimal data_dir with 3 equity tickers of different lengths."""
    eq = tmp_path / "equities"
    eq.mkdir()

    for ticker, start, n in [("AAPL", "2020-01-01", 500),
                               ("MSFT", "2020-01-01", 500),
                               ("NEW",  "2021-06-01", 200)]:   # ragged start
        df = _make_prices(start, n, seed=hash(ticker) % 999)
        writer.write_or_append(eq / f"{ticker}.parquet", df)

    return tmp_path


# ── load_panel ────────────────────────────────────────────────────────────────

def test_panel_shape(data_dir):
    p = panel.load_panel(data_dir, "equities")
    assert set(p.columns) == {"AAPL", "MSFT", "NEW"}
    assert isinstance(p.index, pd.DatetimeIndex)
    assert p.index.is_monotonic_increasing


def test_panel_ragged_start(data_dir):
    p = panel.load_panel(data_dir, "equities", ffill=False)
    # NEW starts later — should have NaN at the beginning of the index
    assert p["NEW"].isna().any()
    # AAPL starts at the earliest date in the index — first row must not be NaN
    assert not pd.isna(p["AAPL"].iloc[0])


def test_panel_date_filter(data_dir):
    full = panel.load_panel(data_dir, "equities")
    filtered = panel.load_panel(data_dir, "equities", start="2021-01-01", end="2021-06-30")
    assert len(filtered) < len(full)
    assert filtered.index.min() >= pd.Timestamp("2021-01-01")
    assert filtered.index.max() <= pd.Timestamp("2021-06-30")


def test_panel_min_history(data_dir):
    p = panel.load_panel(data_dir, "equities", min_history_days=400)
    assert "NEW" not in p.columns   # only 200 rows
    assert "AAPL" in p.columns
    assert "MSFT" in p.columns


def test_panel_field_volume(data_dir):
    p = panel.load_panel(data_dir, "equities", field="volume")
    # Non-NaN volume values should all be positive. pandas 3.0's stack()
    # no longer drops the NaN cells from this panel's ragged ticker start
    # dates (and no longer accepts a dropna= argument at all, since its new
    # implementation never introduces NaN rows itself) -- drop them
    # explicitly afterward instead so NaN > 0 (False) can't leak in.
    assert (p.stack().dropna() > 0).all()


def test_panel_empty_category(data_dir):
    p = panel.load_panel(data_dir, "nonexistent_category")
    assert p.empty


# ── load_returns ──────────────────────────────────────────────────────────────

def test_returns_shape(data_dir):
    r = panel.load_returns(data_dir, "equities")
    p = panel.load_panel(data_dir, "equities")
    assert r.shape == p.shape


def test_returns_first_row_nan(data_dir):
    r = panel.load_returns(data_dir, "equities")
    # First row of returns is always NaN (no prior price)
    assert r.iloc[0].isna().all()


def test_returns_magnitude(data_dir):
    r = panel.load_returns(data_dir, "equities").dropna()
    # Simulated returns ~1% daily — 99th percentile should be < 10%
    assert r.abs().quantile(0.99).max() < 0.10


def test_log_returns(data_dir):
    simple = panel.load_returns(data_dir, "equities", log=False).dropna()
    log    = panel.load_returns(data_dir, "equities", log=True).dropna()
    # For small returns, log ≈ simple; relationship: log_r ≈ simple_r - simple_r²/2
    diff = (log - np.log(1 + simple)).abs()
    assert diff.max().max() < 1e-8


# ── universe_metadata ─────────────────────────────────────────────────────────

def test_metadata_columns(data_dir):
    meta = panel.universe_metadata(data_dir, "equities")
    assert set(meta.columns) >= {"ticker", "category", "first_date", "last_date", "n_rows"}
    assert len(meta) == 3


def test_metadata_ragged(data_dir):
    meta = panel.universe_metadata(data_dir, "equities").set_index("ticker")
    assert meta.loc["NEW", "first_date"] > meta.loc["AAPL", "first_date"]


def test_metadata_empty_category(data_dir):
    meta = panel.universe_metadata(data_dir, "does_not_exist")
    assert meta.empty
