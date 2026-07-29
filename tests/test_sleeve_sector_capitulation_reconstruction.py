import pandas as pd

import run_sleeve_sector_capitulation_reconstruction as cap


def _prices(start, values):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def _flat_then_crash(crash_at, drop_pct, n=120, level=100.0):
    """Flat series that drops drop_pct over CRASH_ROC_WINDOW days starting at
    index crash_at, then stays flat -- guarantees a clean 5d-ROC crash read
    exactly at crash_at + CRASH_ROC_WINDOW."""
    values = [level] * n
    per_day = (1 + drop_pct) ** (1 / cap.CRASH_ROC_WINDOW)
    for i in range(cap.CRASH_ROC_WINDOW):
        values[crash_at + 1 + i] = values[crash_at] * per_day ** (i + 1)
    for i in range(crash_at + 1 + cap.CRASH_ROC_WINDOW, n):
        values[i] = values[crash_at + cap.CRASH_ROC_WINDOW]
    return _prices("2020-01-01", values)


def test_find_capitulation_entries_buckets_solo_vs_basket(monkeypatch):
    crash_at = 60
    prices_a = _flat_then_crash(crash_at, -0.15)  # A and B crash together, same sector
    prices_b = _flat_then_crash(crash_at, -0.15)
    prices_c = _flat_then_crash(crash_at, -0.15)  # C crashes alone, different sector

    candidates = {
        "A": ("equities", prices_a),
        "B": ("equities", prices_b),
        "C": ("equities", prices_c),
    }
    selections = [{
        "t_date": pd.Timestamp("2020-01-01"),
        "top": ["A", "B", "C"],
        "p67": {},
    }]

    sectors = {"A": "Tech", "B": "Tech", "C": "Energy"}
    monkeypatch.setattr(cap, "_sector_of", lambda t: sectors[t])
    monkeypatch.setattr(cap, "MIN_PEERS_CRASHING", 1)

    events = cap.find_capitulation_entries(selections, candidates)
    by_ticker = {e["ticker"]: e["bucket"] for e in events}

    assert by_ticker["A"] == "basket_crash"  # B (same sector) also crashing
    assert by_ticker["B"] == "basket_crash"  # A (same sector) also crashing
    assert by_ticker["C"] == "solo_crash"    # no same-sector peer crashing


def test_find_capitulation_entries_skips_tickers_with_no_sector(monkeypatch):
    crash_at = 60
    prices = _flat_then_crash(crash_at, -0.15)
    candidates = {"A": ("equities", prices), "B": ("equities", prices)}
    selections = [{"t_date": pd.Timestamp("2020-01-01"), "top": ["A", "B"], "p67": {}}]

    monkeypatch.setattr(cap, "_sector_of", lambda t: None)

    events = cap.find_capitulation_entries(selections, candidates)
    assert events == []


def test_find_capitulation_entries_no_crash_no_events(monkeypatch):
    values = [100.0 + i * 0.01 for i in range(120)]  # gentle uptrend, never crashes
    prices = _prices("2020-01-01", values)
    candidates = {"A": ("equities", prices), "B": ("equities", prices)}
    selections = [{"t_date": pd.Timestamp("2020-01-01"), "top": ["A", "B"], "p67": {}}]

    monkeypatch.setattr(cap, "_sector_of", lambda t: "Tech")

    events = cap.find_capitulation_entries(selections, candidates)
    assert events == []


def test_find_capitulation_entries_requires_min_two_tickers_in_period():
    candidates = {"A": ("equities", _prices("2020-01-01", [100.0] * 60))}
    selections = [{"t_date": pd.Timestamp("2020-01-01"), "top": ["A"], "p67": {}}]

    events = cap.find_capitulation_entries(selections, candidates)
    assert events == []
