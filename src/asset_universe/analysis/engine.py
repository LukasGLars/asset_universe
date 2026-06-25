"""
Conditional return engine.

Query historical return distributions conditioned on macro regime
and/or price-action state. All outputs include N and confidence flag.
See INTEGRITY.md for evidence standards.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import regimes as regime_module
from .. import config
from ..store import reader

# Minimum observations before a distribution is reportable
MIN_N = 10

TICKER_LOOKUP: dict[str, tuple[str, str]] = {
    "GC_F":   ("commodities", "GC_F"),
    "SI_F":   ("commodities", "SI_F"),
    "LLY":    ("equities",    "LLY"),
    "WMT":    ("equities",    "WMT"),
    "CCJ":    ("equities",    "CCJ"),
    "VRT":    ("equities",    "VRT"),
    "AVGO":   ("equities",    "AVGO"),
    "PPFB.DE": ("commodities", "PPFB_DE"),
    "PHAG.L": ("commodities", "PHAG_L"),
}


def _load_prices(data_dir: Path, category: str, ticker: str) -> pd.Series:
    path = reader.ticker_path(data_dir, category, ticker)
    if not path.exists():
        return pd.Series(dtype=float)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index()


def _forward_return(prices: pd.Series, date: pd.Timestamp, fwd_days: int) -> float | None:
    idx = prices.index.searchsorted(date)
    if idx >= len(prices):
        return None
    # Verify the matched date is close (within 5 cal days) to avoid large gaps
    if abs((prices.index[idx] - date).days) > 5:
        return None
    fwd_idx = idx + fwd_days
    if fwd_idx >= len(prices):
        return None
    p0, p1 = prices.iloc[idx], prices.iloc[fwd_idx]
    return (p1 - p0) / p0 if p0 > 0 else None


def _stats(returns: list[float], n: int) -> dict[str, Any]:
    if n < MIN_N:
        return {"n": n, "insufficient": True, "min_required": MIN_N}
    s = pd.Series(returns)
    return {
        "n":        n,
        "mean":     round(float(s.mean()), 4),
        "median":   round(float(s.median()), 4),
        "p10":      round(float(s.quantile(0.10)), 4),
        "p25":      round(float(s.quantile(0.25)), 4),
        "p75":      round(float(s.quantile(0.75)), 4),
        "p90":      round(float(s.quantile(0.90)), 4),
        "win_rate": round(float((s > 0).mean()), 4),
        "std":      round(float(s.std()), 4),
    }


def query(
    conditions: dict[str, str],
    tickers: list[str],
    forward_days: list[int] | None = None,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Compute conditional return distributions.

    conditions  -- regime labels, e.g.:
                   {"ry_regime": "HIGH", "baa10y_regime": "TIGHT"}
                   Multiple conditions are AND-ed together.
    tickers     -- keys from TICKER_LOOKUP, e.g. ["GC_F", "LLY"]
    forward_days -- trading-day horizons (default [21, 63, 126, 252])

    Returns:
        results[ticker]["{N}d"] -> stat dict (n, mean, median, p25, p75,
                                              p10, p90, win_rate, std)
        _meta                  -> matched dates, confidence, thresholds
    """
    if forward_days is None:
        forward_days = [21, 63, 126, 252]
    if data_dir is None:
        data_dir = config.raw_data_dir()

    labeled_df, thresholds = regime_module.build(data_dir)

    # Filter to dates matching ALL conditions
    mask = pd.Series(True, index=labeled_df.index)
    for key, val in conditions.items():
        if key not in labeled_df.columns:
            raise ValueError(
                f"Condition key '{key}' not in feature set. "
                f"Available: {[c for c in labeled_df.columns if c.endswith('_regime')]}"
            )
        mask &= labeled_df[key] == val

    matched_dates = labeled_df.index[mask]

    # Current regime confidence and HY velocity
    last = labeled_df.iloc[-1]
    confidence   = str(last.get("regime_confidence", "HIGH"))
    hy_velocity  = None
    if "hy_20d_delta" in last.index and pd.notna(last["hy_20d_delta"]):
        hy_velocity = f"{last['hy_20d_delta']:+.1f} bps/20d"

    # Per-ticker forward return distributions
    results: dict[str, Any] = {}
    for ticker in tickers:
        if ticker not in TICKER_LOOKUP:
            results[ticker] = {"error": f"unknown ticker — add to TICKER_LOOKUP"}
            continue

        cat, raw = TICKER_LOOKUP[ticker]
        prices   = _load_prices(data_dir, cat, raw)
        if prices.empty:
            results[ticker] = {"error": "no price data in parquet store"}
            continue

        ticker_out: dict[str, Any] = {}
        for fwd in forward_days:
            rets = [
                r for dt in matched_dates
                if (r := _forward_return(prices, dt, fwd)) is not None
            ]
            ticker_out[f"{fwd}d"] = _stats(rets, len(rets))

        results[ticker] = ticker_out

    return {
        "results": results,
        "_meta": {
            "n_dates_matched":   len(matched_dates),
            "conditions":        conditions,
            "thresholds":        thresholds,
            "regime_confidence": confidence,
            "hy_velocity":       hy_velocity,
            "feature_window":    (
                str(labeled_df.index[0].date()),
                str(labeled_df.index[-1].date()),
            ),
        },
    }


def current_regime(data_dir: Path | None = None) -> dict[str, Any]:
    """
    Return today's regime state across all conditioning features.
    Includes raw feature values, regime labels, and confidence flag.
    """
    if data_dir is None:
        data_dir = config.raw_data_dir()

    labeled_df, thresholds = regime_module.build(data_dir)
    today = labeled_df.iloc[-1]

    regime_cols  = [c for c in labeled_df.columns if c.endswith("_regime")]
    raw_features = ["ry", "baa10y", "t10y3m", "t10y3m_inverted", "usd",
                    "hy_oas", "hy_5d_delta", "hy_10d_delta", "hy_20d_delta",
                    "hy_ig_divergence", "ry_rising"]

    state: dict[str, Any] = {
        "date":               str(labeled_df.index[-1].date()),
        "regimes":            {c: today[c] for c in regime_cols if pd.notna(today.get(c))},
        "confidence":         str(today.get("regime_confidence", "HIGH")),
        "raw":                {
            f: round(float(today[f]), 3)
            for f in raw_features
            if f in today.index and pd.notna(today[f])
        },
        "thresholds":         thresholds,
        "feature_window":     (
            str(labeled_df.index[0].date()),
            str(labeled_df.index[-1].date()),
        ),
    }
    return state
