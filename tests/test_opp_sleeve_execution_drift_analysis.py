import pandas as pd

import run_opp_sleeve_execution_drift_analysis as drift


def _series(start, values):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def test_forward_return_from_price_basic():
    close = _series("2020-01-01", [100.0, 101.0, 102.0, 103.0, 104.0, 110.0])
    # entry at idx=0's date, but priced off an explicit entry_price of 105
    # (simulating a delayed-execution open different from the close series)
    r = drift.forward_return_from_price(close, entry_idx=0, entry_price=105.0, calendar_days=5)
    assert r is not None
    # target lands on idx=5 (110.0): (110-105)/105
    assert abs(r - (110.0 - 105.0) / 105.0) < 1e-9


def test_forward_return_from_price_none_beyond_history():
    close = _series("2020-01-01", [100.0, 101.0, 102.0])
    assert drift.forward_return_from_price(close, entry_idx=0, entry_price=100.0, calendar_days=90) is None


def test_early_stop_out_triggers_on_ma50_breach():
    # Flat at 100 for 60 days (MA50 settles at 100), entry at day 60 at
    # 100, then price falls hard the next day -- well below a buffered
    # MA50 floor (100 * 0.95 = 95).
    values = [100.0] * 60 + [80.0] * 10
    close = _series("2020-01-01", values)
    ma50 = close.rolling(50, min_periods=25).mean()
    stopped = drift.early_stop_out(close, ma50, entry_idx=59, entry_price=100.0, window=10)
    assert stopped is True


def test_early_stop_out_false_when_price_holds_above_stop():
    # Steady uptrend -- price never falls below its own buffered MA50 or
    # a trailing stop in the window.
    values = [100.0 + i * 0.5 for i in range(80)]
    close = _series("2020-01-01", values)
    ma50 = close.rolling(50, min_periods=25).mean()
    stopped = drift.early_stop_out(close, ma50, entry_idx=59, entry_price=close.iloc[59], window=10)
    assert stopped is False


def test_load_candidates_with_open_shape(tmp_path, monkeypatch):
    # Not exercising real parquet I/O here (covered indirectly by running
    # against the real store in CI) -- just confirms EXCLUDE filtering and
    # the (cat, close)/open dict shapes are wired correctly using a fake
    # reader.load.
    import run_sleeve_entry_reconstruction as recon

    class FakePath:
        def __init__(self, stem):
            self.stem = stem

        def __lt__(self, other):
            return self.stem < other.stem

    fake_df = pd.DataFrame({
        "open": [100.0 + i for i in range(60)],
        "close": [101.0 + i for i in range(60)],
    }, index=pd.date_range("2020-01-01", periods=60, freq="D"))

    class FakeDir:
        def __init__(self, files):
            self._files = files

        def exists(self):
            return True

        def glob(self, pattern):
            return self._files

    monkeypatch.setattr(drift.reader, "load", lambda path: fake_df)

    class FakeDataDir:
        def __truediv__(self, other):
            if other == "equities":
                return FakeDir([FakePath("GOODCO"), FakePath(next(iter(recon.EXCLUDE)))])
            return FakeDir([])

    candidates, opens = drift.load_candidates_with_open(FakeDataDir())
    assert "GOODCO" in candidates
    assert next(iter(recon.EXCLUDE)) not in candidates
    assert "GOODCO" in opens
    assert candidates["GOODCO"][0] == "equities"
