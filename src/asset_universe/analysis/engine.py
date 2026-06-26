"""
Conditional return engine.

Query historical return distributions conditioned on macro regime
and/or price-action state. All outputs include N and confidence flag.
See INTEGRITY.md for evidence standards.
"""
from __future__ import annotations

from datetime import date as _date, datetime as _datetime
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


def _next_earnings(ticker: str) -> "_date | None":
    """Fetch next earnings date for ticker via yfinance. Returns None on failure."""
    today = _date.today()
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        try:
            df = t.earnings_dates
            if df is not None and not df.empty:
                future = [idx.date() for idx in df.index
                          if hasattr(idx, "date") and idx.date() >= today]
                if future:
                    return min(future)
        except Exception:
            pass
        cal = t.calendar
        if cal:
            val = cal.get("Earnings Date")
            if isinstance(val, list):
                val = val[0] if val else None
            if val is not None:
                d = (val.date() if hasattr(val, "date")
                     else _datetime.strptime(str(val)[:10], "%Y-%m-%d").date())
                if d >= today:
                    return d
    except Exception:
        pass
    return None


def _benchmark_prices(data_dir: Path, benchmark: str) -> pd.Series:
    """Load benchmark close prices. Tries parquet store first, then yfinance."""
    for cat in ("equities", "intl_etfs"):
        path = reader.ticker_path(data_dir, cat, benchmark)
        if path.exists():
            df = pd.read_parquet(path)
            df["date"] = pd.to_datetime(df["date"])
            return df.set_index("date").sort_index()["close"]
    try:
        import yfinance as yf
        hist = yf.download(benchmark, period="1y", auto_adjust=True, progress=False)
        if not hist.empty:
            s = hist["Close"].squeeze()
            s.index = pd.to_datetime(s.index)
            return s.sort_index().rename(benchmark)
    except Exception:
        pass
    return pd.Series(dtype=float, name=benchmark)


def screen_tactical(
    conditions: dict[str, str],
    tickers: list[str],
    forward_days: list[int] | None = None,
    category: str = "equities",
    benchmark: str = "SPY",
    hold_days: int = 30,
    min_n: int = 30,
    data_dir: Path | None = None,
) -> pd.DataFrame:
    """
    Four-gate screen for tactical (21-30 day) entries.

    Gate 1 — Macro regime: AND all conditions, derived live from current_regime().
    Gate 2 — Entry quality: MA50 extension p33/p67 on matched dates; HIGH excluded.
    Gate 3 — Relative strength: rs_20d > 0, ticker must outperform benchmark.
    Gate 4 — Catalyst calendar: no earnings within hold_days of today.

    Forward returns conditioned on gates 1 + 2 simultaneously.
    Temporal diversity (THIN/MODERATE/ROBUST) is mandatory in every output row.

    Returns DataFrame sorted by rs_20d descending (strongest RS first).
    """
    if forward_days is None:
        forward_days = [21, 63, 252]
    if data_dir is None:
        data_dir = config.raw_data_dir()

    labeled_df, _ = regime_module.build(data_dir)

    mask = pd.Series(True, index=labeled_df.index)
    for key, val in conditions.items():
        if key not in labeled_df.columns:
            raise ValueError(
                f"Condition key '{key}' not in feature set. "
                f"Available: {[c for c in labeled_df.columns if c.endswith('_regime')]}"
            )
        mask &= labeled_df[key] == val
    base_dates = labeled_df.index[mask]

    # Gate 3 baseline: benchmark 20d and 63d returns
    bm = _benchmark_prices(data_dir, benchmark)
    bm_ret_20d = float(bm.iloc[-1] / bm.iloc[-22] - 1) if len(bm) >= 22 else None
    bm_ret_63d = float(bm.iloc[-1] / bm.iloc[-64] - 1) if len(bm) >= 64 else None

    today = _date.today()
    rows = []

    for tkr in tickers:
        path = reader.ticker_path(data_dir, category, tkr)
        if not path.exists():
            continue
        raw_df = pd.read_parquet(path)
        raw_df["date"] = pd.to_datetime(raw_df["date"])
        prices = raw_df.set_index("date").sort_index()["close"]
        if len(prices) < 200:
            continue

        # Gate 2: MA50 extension
        ma50     = prices.rolling(50, min_periods=25).mean()
        ma50_ext = prices / ma50 - 1

        current_ext = float(ma50_ext.iloc[-1])
        if pd.isna(current_ext):
            continue

        ext_on_matched = ma50_ext.reindex(base_dates).dropna()
        if len(ext_on_matched) < min_n:
            continue

        p33 = float(ext_on_matched.quantile(0.3333))
        p67 = float(ext_on_matched.quantile(0.6667))

        if current_ext > p67:
            continue  # HIGH extension — excluded
        bucket = "MID" if current_ext > p33 else "LOW"

        # Gate 3: relative strength — must outperform benchmark over 20d
        tkr_ret_20d = float(prices.iloc[-1] / prices.iloc[-22] - 1) if len(prices) >= 22 else None
        tkr_ret_63d = float(prices.iloc[-1] / prices.iloc[-64] - 1) if len(prices) >= 64 else None
        rs_20d = (tkr_ret_20d - bm_ret_20d
                  if tkr_ret_20d is not None and bm_ret_20d is not None else None)
        rs_63d = (tkr_ret_63d - bm_ret_63d
                  if tkr_ret_63d is not None and bm_ret_63d is not None else None)

        if rs_20d is None or rs_20d <= 0:
            continue  # underperforming benchmark over 20d

        # Gate 4: earnings calendar
        earn_date = _next_earnings(tkr)
        earn_days = (earn_date - today).days if earn_date else None
        if earn_days is not None and earn_days <= hold_days:
            continue  # earnings inside hold window
        earn_flag = f"earn {earn_days}d" if earn_days is not None else "earn:?"

        # Entry-quality-conditioned dates: gates 1 + 2 combined
        clean_dates = base_dates[
            ma50_ext.reindex(base_dates).fillna(float("inf")) <= p67
        ]

        # Momentum conditioning: filter clean_dates to where ticker was in
        # the same 21d momentum state as today (own-cycle positioning).
        # Falls back to clean_dates if N < min_n after filtering.
        mom_21d_series = prices.pct_change(21)
        current_mom_21d = float(prices.iloc[-1] / prices.iloc[-22] - 1) if len(prices) >= 22 else None
        mom_at_clean = mom_21d_series.reindex(clean_dates, method="nearest", tolerance=pd.Timedelta("5D")).dropna()

        mom_state: str | None = None
        entry_dates = clean_dates  # default: no momentum filter

        if current_mom_21d is not None and len(mom_at_clean) >= min_n * 2:
            mp33 = float(mom_at_clean.quantile(0.333))
            mp67 = float(mom_at_clean.quantile(0.667))
            if current_mom_21d <= mp33:
                mom_state = "LOW"
                filtered = mom_at_clean.index[mom_at_clean <= mp33]
            elif current_mom_21d <= mp67:
                mom_state = "MID"
                filtered = mom_at_clean.index[(mom_at_clean > mp33) & (mom_at_clean <= mp67)]
            else:
                mom_state = "HIGH"
                filtered = mom_at_clean.index[mom_at_clean > mp67]

            if len(filtered) >= min_n:
                entry_dates = filtered
            else:
                mom_state = f"{mom_state}~base"  # fell back
                entry_dates = clean_dates

        # Temporal diversity
        if len(entry_dates) >= 2:
            span_yr   = (entry_dates[-1] - entry_dates[0]).days / 365.25
            cutoff_3y = entry_dates[-1] - pd.DateOffset(years=3)
            pct_3y    = float((entry_dates >= cutoff_3y).mean())
        else:
            span_yr, pct_3y = 0.0, 1.0

        if span_yr >= 10 and pct_3y < 0.50:
            diversity = "ROBUST"
        elif span_yr < 5 or pct_3y > 0.80:
            diversity = "THIN"
        else:
            diversity = "MODERATE"

        row: dict[str, Any] = {
            "ticker":      tkr,
            "ma50_ext":    round(current_ext, 4),
            "ma50_bucket": bucket,
            "p67_ext":     round(p67, 4),
            "rs_20d":      round(rs_20d, 4),
            "rs_63d":      round(rs_63d, 4) if rs_63d is not None else float("nan"),
            "mom_state":   mom_state if mom_state is not None else "n/a",
            "earn_flag":   earn_flag,
            "yrs_span":    round(span_yr, 1),
            "pct_3yr":     round(pct_3y, 2),
            "diversity":   diversity,
        }

        for fwd in forward_days:
            rets = [
                r for dt in entry_dates
                if (r := _forward_return(prices, dt, fwd)) is not None
            ]
            if len(rets) >= min_n:
                s = pd.Series(rets)
                row[f"n_{fwd}d"]   = len(rets)
                row[f"med_{fwd}d"] = round(float(s.median()), 4)
                row[f"win_{fwd}d"] = round(float((s > 0).mean()), 4)
            else:
                row[f"n_{fwd}d"]   = len(rets)
                row[f"med_{fwd}d"] = float("nan")
                row[f"win_{fwd}d"] = float("nan")

        rows.append(row)

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows).dropna(subset=[f"med_{forward_days[-1]}d"])

    # Percentile ranks within surviving universe (context, not a gate)
    if len(out) > 1:
        out["rs_20d_pct"] = out["rs_20d"].rank(pct=True).round(2)
        out["rs_63d_pct"] = out["rs_63d"].rank(pct=True).round(2)
    else:
        out["rs_20d_pct"] = 1.0
        out["rs_63d_pct"] = 1.0

    return out.sort_values("rs_20d", ascending=False).reset_index(drop=True)


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
    raw_features = ["ry", "nominal_10y", "breakeven",
                    "nominal_10y_5d_delta", "nominal_10y_20d_delta", "breakeven_20d_delta",
                    "baa10y", "t10y3m", "t10y3m_inverted", "t10y2y", "t10y2y_inverted",
                    "se_10y", "se_10y_20d_delta",
                    "usd", "hy_oas", "hy_5d_delta", "hy_10d_delta", "hy_20d_delta",
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
