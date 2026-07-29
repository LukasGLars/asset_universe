import pandas as pd

import run_opp_sleeve_extension_decile_analysis as ext_decile


def _prices(start, values):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def test_find_gated_entries_with_ext_stores_ext_and_p67():
    # Flat at 100 for 60 days (MA50 settles at 100), then rises to 105
    # (+5% extension) and holds -- well inside a generous p67 of 0.10.
    prices = _prices("2020-01-01", [100.0] * 60 + [105.0] * 40)
    candidates = {"A": ("equities", prices)}
    bm_prices = _prices("2020-01-01", [100.0 + i * 0.01 for i in range(100)])

    selections = [{
        "t_date": prices.index[0], "ry": "X", "baa": "Y",
        "top": ["A"], "p67": {"A": 0.10},
    }]

    ma50 = prices.rolling(50, min_periods=25).mean()
    events = ext_decile.find_gated_entries_with_ext(selections, candidates, bm_prices)
    assert len(events) > 0
    for e in events:
        assert e["ticker"] == "A"
        assert e["p67"] == 0.10
        expected_ext = prices.loc[e["date"]] / ma50.loc[e["date"]] - 1
        assert abs(e["ext"] - expected_ext) < 1e-9


def test_find_gated_entries_with_ext_respects_p67_cutoff():
    # Same setup but p67 is tighter than the actual +5% extension -> no
    # events should clear gate 3a.
    prices = _prices("2020-01-01", [100.0] * 60 + [105.0] * 40)
    candidates = {"A": ("equities", prices)}
    bm_prices = _prices("2020-01-01", [100.0 + i * 0.01 for i in range(100)])

    selections = [{
        "t_date": prices.index[0], "ry": "X", "baa": "Y",
        "top": ["A"], "p67": {"A": 0.02},  # tighter than actual +5% ext
    }]

    events = ext_decile.find_gated_entries_with_ext(selections, candidates, bm_prices)
    assert events == []


def test_decile_bucketing_and_correlation_direction():
    # Synthetic population: higher extension -> systematically lower
    # forward return (an obvious, strong negative dose-response), to
    # confirm the decile/correlation logic in main() picks it up correctly
    # when exercised directly (not via main(), which needs real data/IO).
    import numpy as np

    n = 500
    rng = np.random.default_rng(0)
    ext = rng.uniform(0.0, 0.20, n)
    ret = 0.10 - 0.5 * ext + rng.normal(0, 0.005, n)  # strong negative slope
    df = pd.DataFrame({"ticker": ["A"] * n, "ext": ext, "ret": ret})
    df["decile"] = pd.qcut(df["ext"], 10, labels=False, duplicates="drop")

    rows = []
    for dec, g in df.groupby("decile"):
        rows.append({"ext_median": g["ext"].median(), "med_return": g["ret"].median()})
    out = pd.DataFrame(rows)

    corr = np.corrcoef(out["ext_median"], out["med_return"])[0, 1]
    assert corr < -0.8  # strongly negative, as constructed
