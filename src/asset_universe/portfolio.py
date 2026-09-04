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
            "needs_price": False,
        }

        if pos["ticker"] == "":
            # Manual position. Two shapes:
            #   shares == 0 -> value_sek is the holding (Cash, Spiltan)
            #   shares  > 0 -> shares * price_sek (instruments with no price
            #                  feed: Swedish fondbolag funds, Virtune ETPs).
            # The second shape exists because the sheet tracks those by share
            # count, and the old code ignored `shares` for tickerless rows
            # entirely -- so a share-tracked holding silently valued at its
            # stale value_sek, or at 0. price_sek is required in that case and
            # left as None if absent, so tpv()'s guard fails loudly.
            if pos.get("shares", 0) > 0:
                p = pos.get("price_sek")
                if p:
                    row["price_sek"] = float(p)
                    row["fx_rate"]   = 1.0
                    row["value_sek"] = float(p) * pos["shares"]
                else:
                    # No per-share price recorded yet. Fall back to the last
                    # known value so the dashboard still renders, but flag it:
                    # this number does NOT move with the market and will drift
                    # silently, which is exactly how the Virtune legs sat
                    # frozen at their seeded figure.
                    row["value_sek"]  = float(pos.get("value_sek", 0))
                    row["needs_price"] = True
            else:
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
    target_inflation: float = 0.0,
) -> float:
    """
    Years (possibly fractional) for TPV + ongoing monthly contributions,
    compounded at annual_rate, to reach target. inf if unreachable within a
    century even at the given rate (e.g. rate <= 0 and contributions too
    small).

    `target` is the threshold as of TODAY. With target_inflation > 0 the
    threshold is a moving bar -- it grows at that rate while the portfolio
    grows at annual_rate -- because the FI@50 trigger is inflation-indexed
    (the conversion date is unknown, so the number it fires on cannot be a
    fixed nominal one). Comparing a nominal portfolio against a frozen
    target is what made the old "FI date" column optimistic; a path that
    only beats inflation never crosses. Defaults to 0.0, which reproduces
    the prior fixed-target behaviour exactly.
    """
    if tpv >= target:
        return 0.0

    def f(years: float) -> float:
        return (future_value_with_contributions(tpv, annual_rate, years, monthly_contribution)
                - target * (1 + target_inflation) ** years)

    lo, hi = 0.0, 100.0
    if f(hi) < 0:
        return float("inf")
    return brentq(f, lo, hi, xtol=1e-4)


def _fi_target(fi: dict, years_ahead: float = 0.0) -> float:
    """The FI@50 conversion threshold in NOMINAL kr, `years_ahead` years from
    today.

    Preferred config form is a real (base-year kr) threshold plus an
    indexing rate, since the trigger is wealth-based and can fire in any
    year:

        target_real_sek * (1 + target_inflation) ** (year - target_base_year)

    Falls back to a flat `target_sek` when those keys are absent, so an
    older config (and the existing fixed-target tests) still work unchanged.
    """
    if "target_real_sek" not in fi:
        return float(fi["target_sek"])

    real      = float(fi["target_real_sek"])
    base_year = float(fi.get("target_base_year", 2026))
    infl      = float(fi.get("target_inflation", 0.0))

    today = pd.Timestamp(date.today())
    year_now = today.year + (today.dayofyear - 1) / 365.25
    return real * (1 + infl) ** (year_now + years_ahead - base_year)


def bucket_targets() -> dict[str, float]:
    """Target fraction of TPV per bucket, from config/portfolio.toml's
    [buckets] table. Empty dict if the table is absent -- callers should
    treat that as "no target recorded" and print actuals only, not
    substitute a hardcoded guess (a hardcoded 85/15 in
    run_outlook_montecarlo.py silently outliving a change to the real split
    is exactly what this table exists to prevent)."""
    return {k: float(v) for k, v in _load_portfolio_config().get("buckets", {}).items()}


def target_weights() -> dict[str, float]:
    """Target fraction of TPV per POSITION, from each [[positions]] block's
    `target_weight`. Authoritative from the 2026-09-04 restructure: the
    allocation is now stated per asset, and the bucket split is a grouping
    of these rather than the other way round.

    Positions without the key are omitted (not defaulted to 0) so a missing
    target reads as "not recorded" rather than "deliberately zero" -- the
    same reasoning as bucket_targets()."""
    out = {}
    for pos in _load_portfolio_config().get("positions", []):
        if "target_weight" in pos:
            out[pos["name"]] = float(pos["target_weight"])
    return out


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
    years_total = fi["years"]
    monthly_contribution = fi.get("monthly_contribution_sek", 0)

    today         = pd.Timestamp(date.today())
    days_elapsed  = (today - start_date).days
    years_elapsed = days_elapsed / 365.25
    years_left    = years_total - years_elapsed

    # Two different thresholds, both needed and easy to confuse:
    #   target_now -- what TPV would have to be TODAY to trigger conversion.
    #   target     -- the same bar grown to the horizon date, which is what
    #                 required_cagr and the surplus/deficit must be measured
    #                 against. Using target_now for those would understate
    #                 the requirement by the whole indexing factor (~27% at
    #                 a 12-year horizon and 2% inflation).
    target_now = _fi_target(fi, 0.0)
    target     = _fi_target(fi, max(years_left, 0.0))
    inflation  = float(fi.get("target_inflation", 0.0))

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
        "target_now_sek":       target_now,
        "target_real_sek":      float(fi.get("target_real_sek", target)),
        "target_base_year":     fi.get("target_base_year"),
        "target_inflation":     inflation,
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
