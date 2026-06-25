"""
Portfolio valuation and FI@50 pace tracker.

Reads config/portfolio.toml + parquet price store → computes TPV in SEK,
FI@50 AWAR vs required CAGR, and live macro trigger states.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .store import reader

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


def _load_portfolio_config() -> dict:
    path = config._ROOT / "config" / "portfolio.toml"
    with open(path, "rb") as f:
        return tomllib.load(f)


def _latest_price(data_dir: Path, category: str, ticker: str) -> float | None:
    path = reader.ticker_path(data_dir, category, ticker)
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    col = "close" if "close" in df.columns else "value"
    return float(df[col].dropna().iloc[-1])


def _latest_fx(data_dir: Path, pair: str) -> float | None:
    return _latest_price(data_dir, "fx", pair)


def snapshot(data_dir: Path | None = None) -> pd.DataFrame:
    """
    Returns a DataFrame with one row per position:
        name, ticker, bucket, shares, price_local, currency,
        fx_rate, price_sek, value_sek, weight
    """
    if data_dir is None:
        data_dir = config.raw_data_dir()

    cfg = _load_portfolio_config()

    usdsek = _latest_fx(data_dir, "USDSEK=X")
    eursek = _latest_fx(data_dir, "EURSEK=X")

    rows = []
    for pos in cfg["positions"]:
        row: dict = {
            "name":        pos["name"],
            "ticker":      pos["ticker"],
            "bucket":      pos["bucket"],
            "shares":      pos["shares"],
            "currency":    pos["currency"],
            "price_local": None,
            "fx_rate":     None,
            "price_sek":   None,
            "value_sek":   None,
        }

        if pos["ticker"] == "":
            row["value_sek"] = float(pos.get("value_sek", 0))
        else:
            price = _latest_price(data_dir, pos["category"], pos["ticker"])
            if price is not None:
                row["price_local"] = price
                if pos["currency"] == "USD":
                    row["fx_rate"]   = usdsek
                    row["price_sek"] = price * usdsek if usdsek else None
                elif pos["currency"] == "EUR":
                    row["fx_rate"]   = eursek
                    row["price_sek"] = price * eursek if eursek else None
                else:
                    row["fx_rate"]   = 1.0
                    row["price_sek"] = price
                if row["price_sek"] is not None:
                    row["value_sek"] = row["price_sek"] * pos["shares"]

        rows.append(row)

    df = pd.DataFrame(rows)
    total = df["value_sek"].sum()
    df["weight"] = df["value_sek"] / total if total > 0 else 0.0
    return df


def fi_pace(data_dir: Path | None = None) -> dict:
    """
    Returns FI@50 pace metrics:
        tpv_sek, start_value, start_date, target_sek, years_remaining,
        days_elapsed, awar, required_cagr, on_pace, projected_value,
        surplus_deficit_sek
    """
    if data_dir is None:
        data_dir = config.raw_data_dir()

    cfg = _load_portfolio_config()
    fi = cfg["fi"]

    snap = snapshot(data_dir)
    tpv = snap["value_sek"].sum()

    start_date  = pd.Timestamp(fi["start_date"])
    start_value = fi["start_value_sek"]
    target      = fi["target_sek"]
    years_total = fi["years"]

    today         = pd.Timestamp(date.today())
    days_elapsed  = (today - start_date).days
    years_elapsed = days_elapsed / 365.25
    years_left    = years_total - years_elapsed

    awar          = (tpv / start_value) ** (365.25 / days_elapsed) - 1 if days_elapsed > 0 else 0.0
    required_cagr = (target / tpv) ** (1 / years_left) - 1 if years_left > 0 else float("nan")
    projected     = tpv * (1 + awar) ** years_left
    surplus       = projected - target

    return {
        "tpv_sek":          tpv,
        "start_value_sek":  start_value,
        "start_date":       fi["start_date"],
        "target_sek":       target,
        "years_remaining":  years_left,
        "days_elapsed":     days_elapsed,
        "awar":             awar,
        "required_cagr":    required_cagr,
        "on_pace":          awar >= required_cagr,
        "projected_sek":    projected,
        "surplus_deficit":  surplus,
    }


def trigger_states(data_dir: Path | None = None) -> dict:
    """
    Returns current macro trigger states used in the SOP.
    """
    if data_dir is None:
        data_dir = config.raw_data_dir()

    def _macro(series_id: str) -> pd.Series:
        path = reader.ticker_path(data_dir, "macro", series_id)
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")["value"].sort_index()

    # HY-IG spread (BAMLH0A0HYM2)
    hy = _macro("BAMLH0A0HYM2")
    hy_now = float(hy.iloc[-1]) * 100  # stored as decimal, convert to bps

    # Real yield (DFII10)
    ry = _macro("DFII10")
    ry_now     = float(ry.iloc[-1])
    ry_10d_ma  = float(ry.rolling(10).mean().iloc[-1])
    ry_90d_ma  = float(ry.rolling(90).mean().iloc[-1])
    ry_signal  = "COMPRESSING" if ry_10d_ma < ry_90d_ma else "ELEVATED"

    # Yield curve (T10Y3M)
    t10y3m    = _macro("T10Y3M")
    curve_now = float(t10y3m.iloc[-1])

    return {
        "hy_spread_bps": round(hy_now, 1),
        "ry_current":    round(ry_now, 2),
        "ry_10d_ma":     round(ry_10d_ma, 2),
        "ry_90d_ma":     round(ry_90d_ma, 2),
        "ry_signal":     ry_signal,
        "curve_t10y3m":  round(curve_now, 0),
    }
