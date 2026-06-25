"""
Compute macro and price-action features for every available date.

All features are computed without look-ahead bias — every rolling window
closes at date T using only data available at T.

Returns a DataFrame indexed by date. NaN where data is unavailable
(e.g. HY OAS before 2023-06-26, DTWEXBGS before 2006-01-02).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .. import config
from ..store import reader

# Portfolio tickers for price-action features
PRICE_TICKERS: dict[str, tuple[str, str]] = {
    "GC_F":  ("commodities", "GC_F"),
    "SI_F":  ("commodities", "SI_F"),
    "LLY":   ("equities",    "LLY"),
    "WMT":   ("equities",    "WMT"),
    "CCJ":   ("equities",    "CCJ"),
    "VRT":   ("equities",    "VRT"),
    "AVGO":  ("equities",    "AVGO"),
    "PPFB":  ("commodities", "PPFB_DE"),
    "PHAG":  ("commodities", "PHAG_L"),
}

MACRO_IDS = ["DFII10", "BAA10Y", "T10Y3M", "DTWEXBGS", "BAMLH0A0HYM2"]


def _price(data_dir: Path, category: str, ticker: str) -> pd.Series:
    path = reader.ticker_path(data_dir, category, ticker)
    if not path.exists():
        return pd.Series(dtype=float, name=ticker)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index().rename(ticker)


def _macro(data_dir: Path, sid: str) -> pd.Series:
    path = reader.ticker_path(data_dir, "macro", sid)
    if not path.exists():
        return pd.Series(dtype=float, name=sid)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["value"].sort_index().rename(sid)


def build(data_dir: Path | None = None) -> pd.DataFrame:
    """
    Build the full feature DataFrame indexed by date.
    Use ffill() on FRED series to bridge weekend/holiday gaps.
    """
    if data_dir is None:
        data_dir = config.raw_data_dir()

    cols: dict[str, pd.Series] = {}

    # ── Macro ────────────────────────────────────────────────────────────────

    ry = _macro(data_dir, "DFII10")
    cols["ry"]         = ry
    cols["ry_10d_ma"]  = ry.rolling(10, min_periods=5).mean()
    cols["ry_90d_ma"]  = ry.rolling(90, min_periods=45).mean()
    # 1 = rising (10d MA above 90d MA), 0 = falling
    cols["ry_rising"]  = (cols["ry_10d_ma"] > cols["ry_90d_ma"]).astype(float)

    baa = _macro(data_dir, "BAA10Y")
    cols["baa10y"]          = baa
    cols["baa10y_20d_delta"] = baa.diff(20)

    curve = _macro(data_dir, "T10Y3M")
    cols["t10y3m"] = curve

    usd = _macro(data_dir, "DTWEXBGS")
    cols["usd"] = usd

    # HY OAS — limited history, monitoring/divergence only
    hy     = _macro(data_dir, "BAMLH0A0HYM2") * 100   # decimal -> bps
    baa_bps = baa * 100
    cols["hy_oas"]          = hy
    cols["hy_5d_delta"]     = hy.diff(5)
    cols["hy_10d_delta"]    = hy.diff(10)
    cols["hy_20d_delta"]    = hy.diff(20)
    # Divergence: HY 20d change minus IG 20d change (bps).
    # Positive = HY widening faster than IG = stress building at speculative end.
    cols["hy_ig_divergence"] = hy.diff(20) - baa_bps.diff(20)

    # ── Price action ─────────────────────────────────────────────────────────

    prices: dict[str, pd.Series] = {}
    for name, (cat, tkr) in PRICE_TICKERS.items():
        s = _price(data_dir, cat, tkr)
        if not s.empty:
            prices[name] = s

    for name, s in prices.items():
        daily_ret = s.pct_change()

        for w in (21, 63, 126, 252):
            cols[f"{name}_mom_{w}d"] = s.pct_change(w)

        for w in (20, 60):
            cols[f"{name}_rvol_{w}d"] = daily_ret.rolling(w, min_periods=w // 2).std() * np.sqrt(252)

        for w in (50, 200):
            ma = s.rolling(w, min_periods=w // 2).mean()
            cols[f"{name}_ma{w}_dist"] = (s - ma) / ma

    # Gold/silver ratio
    if "GC_F" in prices and "SI_F" in prices:
        gs = prices["GC_F"] / prices["SI_F"]
        cols["gs_ratio"] = gs
        # Rolling 252d percentile rank (no look-ahead)
        cols["gs_ratio_prank_1y"] = gs.rolling(252, min_periods=126).rank(pct=True)

    # ── Assemble & forward-fill macro gaps (weekends/holidays) ───────────────

    df = pd.DataFrame(cols).sort_index()

    macro_cols = ["ry", "ry_10d_ma", "ry_90d_ma", "ry_rising",
                  "baa10y", "baa10y_20d_delta", "t10y3m", "usd",
                  "hy_oas", "hy_5d_delta", "hy_10d_delta",
                  "hy_20d_delta", "hy_ig_divergence"]
    existing_macro = [c for c in macro_cols if c in df.columns]
    df[existing_macro] = df[existing_macro].ffill(limit=5)

    return df
