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
from scipy.optimize import brentq

from . import config
from .store import reader

# TPV is computed as sum(snapshot().value_sek) -- see fi_pace() below.
# Previously fetched from a dedicated Google Sheet cell (GID 0); dropped
# 2026-07-24 after broker-screenshot reconciliation showed that cell lags
# the real balance more than the position sum does, once idle cash and
# War Chest were correctly tracked in config/portfolio.toml. No code in
# this repo should reintroduce a sheet-cell TPV fetch -- the position sum
# is the only source now.

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


def _annuity_due_fv_factor(monthly_rate: float, n_months: float) -> float:
    """
    Future-value factor for 1 kr/month contributed at the start of each
    month (annuity-due -- matches run_terminal_wealth.py's SP_ANNUITY
    convention), compounded at monthly_rate for n_months.
    """
    if n_months <= 0:
        return 0.0
    if abs(monthly_rate) < 1e-12:
        return n_months
    return (1 + monthly_rate) * ((1 + monthly_rate) ** n_months - 1) / monthly_rate


def future_value_with_contributions(
    tpv: float, annual_rate: float, years: float, monthly_contribution: float,
) -> float:
    """FV of current TPV plus ongoing monthly contributions, both compounded
    at annual_rate (contributions compounded via the monthly-equivalent
    rate)."""
    monthly_rate = (1 + annual_rate) ** (1 / 12) - 1
    n_months = years * 12
    return (tpv * (1 + annual_rate) ** years
            + monthly_contribution * _annuity_due_fv_factor(monthly_rate, n_months))


def _solve_required_cagr(
    tpv: float, target: float, years: float, monthly_contribution: float,
) -> float:
    """
    Required annual CAGR such that TPV + ongoing monthly contributions reach
    target in `years`. Falls back to pure-compounding (no contributions) if
    monthly_contribution is 0, reproducing the prior formula exactly.
    """
    if years <= 0:
        return float("nan")
    if monthly_contribution <= 0:
        return (target / tpv) ** (1 / years) - 1

    def f(r: float) -> float:
        return future_value_with_contributions(tpv, r, years, monthly_contribution) - target

    # Required CAGR is well inside (-99%, 1000%) for any sane FI@50 scenario;
    # brentq needs a bracketing sign change.
    lo, hi = -0.99, 10.0
    if f(lo) > 0:
        return lo  # target already reachable even with a near-total-loss rate
    if f(hi) < 0:
        return hi  # target not reachable even at an absurd rate -- report the cap
    return brentq(f, lo, hi, xtol=1e-6)


def years_to_reach_target(
    tpv: float, annual_rate: float, monthly_contribution: float, target: float,
) -> float:
    """
    Years (possibly fractional) for TPV + ongoing monthly contributions,
    compounded at annual_rate, to reach target. inf if unreachable within a
    century even at the given rate (e.g. rate <= 0 and contributions too
    small).
    """
    if tpv >= target:
        return 0.0

    def f(years: float) -> float:
        return future_value_with_contributions(tpv, annual_rate, years, monthly_contribution) - target

    lo, hi = 0.0, 100.0
    if f(hi) < 0:
        return float("inf")
    return brentq(f, lo, hi, xtol=1e-4)


def fi_pace(data_dir: Path | None = None) -> dict:
    """
    Returns FI@50 pace metrics:
        tpv_sek, start_value, start_date, target_sek, years_remaining,
        days_elapsed, awar, required_cagr, on_pace, projected_value,
        surplus_deficit_sek, monthly_contribution_sek

    required_cagr and projected_sek both account for the ongoing monthly
    contribution (config: fi.monthly_contribution_sek), not just compounding
    of the current TPV -- ignoring it overstates how far behind pace the
    portfolio actually is (confirmed materially: dropped the required-CAGR
    bar from 24.88% to 22.06% in the 2026-07-02 rebalance sizing exercise,
    the largest single lever found in that analysis, previously never wired
    back into this live tracker).

    TPV = sum(snapshot().value_sek) -- config/portfolio.toml positions,
    nothing else (2026-07-24, see module docstring/note above). Raises if
    any share position (shares > 0) has no computable value_sek (missing
    price/FX data) rather than silently summing a partial, undercounted
    total -- a missing price should fail loud here, not quietly understate
    TPV by however much that position was worth.
    """
    if data_dir is None:
        data_dir = config.raw_data_dir()

    cfg = _load_portfolio_config()
    fi = cfg["fi"]

    snap = snapshot(data_dir)
    missing = snap[(snap["shares"] > 0) & snap["value_sek"].isna()]
    if not missing.empty:
        names = ", ".join(missing["name"])
        raise RuntimeError(f"TPV sum incomplete -- missing price data for: {names}")
    tpv = float(snap["value_sek"].sum())

    start_date  = pd.Timestamp(fi["start_date"])
    start_value = fi["start_value_sek"]
    target      = fi["target_sek"]
    years_total = fi["years"]
    monthly_contribution = fi.get("monthly_contribution_sek", 0)

    today         = pd.Timestamp(date.today())
    days_elapsed  = (today - start_date).days
    years_elapsed = days_elapsed / 365.25
    years_left    = years_total - years_elapsed

    awar          = (tpv / start_value) ** (365.25 / days_elapsed) - 1 if days_elapsed > 0 else 0.0
    required_cagr = _solve_required_cagr(tpv, target, years_left, monthly_contribution)
    projected     = (future_value_with_contributions(tpv, awar, years_left, monthly_contribution)
                      if years_left > 0 else tpv)
    surplus       = projected - target

    return {
        "tpv_sek":              tpv,
        "start_value_sek":      start_value,
        "start_date":           fi["start_date"],
        "target_sek":           target,
        "years_remaining":      years_left,
        "days_elapsed":         days_elapsed,
        "awar":                 awar,
        "required_cagr":        required_cagr,
        "on_pace":              awar >= required_cagr,
        "projected_sek":        projected,
        "surplus_deficit":      surplus,
        "monthly_contribution_sek": monthly_contribution,
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
