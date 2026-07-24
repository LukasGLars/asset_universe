"""
Regime transition analysis and CAGR scenario modelling.

Answers: given current RY=HIGH state, how long do episodes historically last,
what is the probability of compression within N months, and what does the
portfolio CAGR look like under different compression timings?
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import regimes as regime_module
from .. import config
from ..store import reader
from .engine import TICKER_LOOKUP

SPILTAN_RETURN = 0.03

# Maps portfolio.toml tickers → transitions analysis keys (TICKER_LOOKUP keys).
# Tactical positions (HWM) are intentionally excluded — they are excluded from
# long-run CAGR modelling. Manual positions (ticker="") roll up into "_spiltan".
PORTFOLIO_TICKER_MAP: dict[str, str] = {
    "PPFB.DE": "GC_F",
    "PHAG.L":  "SI_F",
    "LLY":     "LLY",
    "WMT":     "WMT",
    "CCJ":     "CCJ",
    "VRT":     "VRT",
    "AVGO":    "AVGO",
}

# Fallback weights used when live snapshot is unavailable.
# Keys match TICKER_LOOKUP; "_spiltan" = Spiltan + War Chest (fixed-rate bucket)
CURRENT_WEIGHTS: dict[str, float] = {
    "GC_F":      0.167,
    "SI_F":      0.030,
    "LLY":       0.134,
    "WMT":       0.129,
    "CCJ":       0.085,
    "VRT":       0.084,
    "AVGO":      0.069,
    "_spiltan":  0.246,
}

TARGET_WEIGHTS: dict[str, float] = {
    "GC_F":      0.2125,
    "SI_F":      0.085,
    "LLY":       0.1785,
    "WMT":       0.1275,
    "CCJ":       0.085,
    "VRT":       0.085,
    "AVGO":      0.0765,
    "_spiltan":  0.150,
}


def episode_stats(
    data_dir: Path | None = None,
    feature: str = "ry",
    target_state: str = "HIGH",
    min_duration_days: int = 20,
) -> dict[str, Any]:
    """
    Find sustained historical episodes of target_state for feature.
    min_duration_days filters out noise — brief crossings of the p67 threshold.
    THIN flag if fewer than 5 qualifying episodes.
    """
    if data_dir is None:
        data_dir = config.raw_data_dir()

    labeled_df, _ = regime_module.build(data_dir)
    col = f"{feature}_regime"
    if col not in labeled_df.columns:
        raise ValueError(f"Column '{col}' not found")

    series = labeled_df[col].dropna()
    raw_episodes: list[dict] = []
    in_episode = False
    start = None

    for dt, state in series.items():
        if state == target_state and not in_episode:
            in_episode = True
            start = dt
        elif state != target_state and in_episode:
            in_episode = False
            raw_episodes.append({
                "start":           start,
                "end":             dt,
                "duration_days":   (dt - start).days,
                "duration_months": (dt - start).days / 30.44,
                "ongoing":         False,
            })

    current_episode: dict | None = None
    if in_episode and start is not None:
        d = (series.index[-1] - start).days
        current_episode = {
            "start":           start,
            "end":             None,
            "duration_days":   d,
            "duration_months": d / 30.44,
            "ongoing":         True,
        }

    # Filter to sustained episodes only
    episodes = [e for e in raw_episodes if e["duration_days"] >= min_duration_days]

    n = len(episodes)
    diversity = "THIN" if n < 5 else "MODERATE" if n < 10 else "ROBUST"
    durations = [e["duration_months"] for e in episodes]

    out: dict[str, Any] = {
        "n_complete":      n,
        "diversity":       diversity,
        "min_duration_days": min_duration_days,
        "episodes":        episodes,
        "current_episode": current_episode,
    }

    if durations:
        s = pd.Series(durations)
        out.update({
            "median_months": float(s.median()),
            "p25_months":    float(s.quantile(0.25)),
            "p75_months":    float(s.quantile(0.75)),
            "min_months":    float(s.min()),
            "max_months":    float(s.max()),
        })

    return out


def transition_matrix(
    data_dir: Path | None = None,
    feature: str = "ry",
    period: str = "monthly",
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, int]]]:
    """
    Compute state-to-state transition probabilities.
    period: 'daily' | 'weekly' | 'monthly' — weekly/monthly reduce short-term noise.
    Returns (prob_matrix, count_matrix).
    """
    if data_dir is None:
        data_dir = config.raw_data_dir()

    labeled_df, _ = regime_module.build(data_dir)
    col = f"{feature}_regime"
    series = labeled_df[col].dropna()

    # Resample to reduce noise
    if period == "weekly":
        series = series.resample("W").last().dropna()
    elif period == "monthly":
        series = series.resample("ME").last().dropna()

    states = ["LOW", "MID", "HIGH"]
    counts: dict[str, dict[str, int]] = {s: {t: 0 for t in states} for s in states}

    prev: str | None = None
    for state in series:
        if prev is not None and prev in counts and state in counts[prev]:
            counts[prev][state] += 1
        prev = state

    probs: dict[str, dict[str, float]] = {}
    for s in states:
        total = sum(counts[s].values())
        probs[s] = {t: (counts[s][t] / total if total > 0 else 0.0) for t in states}

    return probs, counts


def simulate_compression(
    transition_probs: dict[str, dict[str, float]],
    from_state: str = "HIGH",
    to_states: tuple[str, ...] = ("MID", "LOW"),
    n_sim: int = 10_000,
    horizon_days: int = 2_500,
    seed: int = 42,
) -> list[int]:
    """
    Monte Carlo simulation of trading days until first transition out of from_state.
    Returns list of days-to-first-compression; horizon_days+1 means never within horizon.
    """
    rng = random.Random(seed)
    states = ["LOW", "MID", "HIGH"]

    results: list[int] = []
    for _ in range(n_sim):
        current = from_state
        compressed = False
        for day in range(1, horizon_days + 1):
            p = transition_probs[current]
            current = rng.choices(states, weights=[p[s] for s in states])[0]
            if current in to_states:
                results.append(day)
                compressed = True
                break
        if not compressed:
            results.append(horizon_days + 1)

    return results


def probability_weighted_cagr(
    sim_months: list[int],
    r_pre: float,
    r_post: float,
    tpv: float,
    years_remaining: float,
    target_sek: float,
) -> dict[str, float]:
    """
    Probability-weighted expected CAGR from Monte Carlo compression timing.

    Each simulated path contributes one CAGR outcome based on when compression
    fires within that path. Average across all 10,000 paths gives E[CAGR].
    Paths where compression never fires within years_remaining stay at r_pre.
    """
    required = (target_sek / tpv) ** (1 / years_remaining) - 1
    cagrs: list[float] = []

    for t_months in sim_months:
        t_yr = t_months / 12
        if t_yr >= years_remaining:
            v_final = tpv * (1 + r_pre) ** years_remaining
        else:
            remaining  = years_remaining - t_yr
            v_compress = tpv * (1 + r_pre) ** t_yr
            v_final    = v_compress * (1 + r_post) ** remaining
        cagrs.append((v_final / tpv) ** (1 / years_remaining) - 1)

    arr = np.array(cagrs)
    return {
        "mean":        float(arr.mean()),
        "median":      float(np.median(arr)),
        "p10":         float(np.percentile(arr, 10)),
        "p90":         float(np.percentile(arr, 90)),
        "pct_on_pace": float((arr >= required).mean()),
        "required":    required,
    }


def _load_prices(data_dir: Path, ticker: str) -> pd.Series:
    """Load close price series for a ticker from parquet store."""
    cat, raw = TICKER_LOOKUP[ticker]
    path = reader.ticker_path(data_dir, cat, raw)
    if not path.exists():
        return pd.Series(dtype=float)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index()


def _regime_pure_drag_return(
    prices: pd.Series,
    episodes: list[dict],
    fwd_days: int = 63,
) -> tuple[float, int]:
    """
    63d forward returns measured only on dates where RY stays HIGH for the
    full fwd_days window (regime-pure drag). Annualized to annual rate.
    Excludes the current ongoing episode (no future prices).
    """
    returns: list[float] = []

    for ep in episodes:
        if ep.get("ongoing"):
            continue
        start, end = ep["start"], ep["end"]

        start_idx = prices.index.searchsorted(start)
        end_idx   = prices.index.searchsorted(end)

        for i in range(start_idx, end_idx):
            fwd_i = i + fwd_days
            if fwd_i >= len(prices):
                break
            if prices.index[fwd_i] > end:
                break
            p0, p1 = float(prices.iloc[i]), float(prices.iloc[fwd_i])
            if p0 > 0:
                returns.append(p1 / p0 - 1)

    if not returns:
        return 0.0, 0

    median_fwd = float(np.median(returns))
    annualized = (1 + median_fwd) ** (252 / fwd_days) - 1
    return annualized, len(returns)


def _post_compression_return(
    prices: pd.Series,
    episodes: list[dict],
    fwd_days: int = 252,
) -> tuple[float, int]:
    """
    252d forward returns starting from each completed episode's end date.
    This captures what actually happened to each asset after RY compression fired.
    """
    returns: list[float] = []

    for ep in episodes:
        if ep.get("ongoing") or ep["end"] is None:
            continue
        end_date = ep["end"]

        idx = prices.index.searchsorted(end_date)
        if idx >= len(prices):
            continue
        if abs((prices.index[idx] - end_date).days) > 5:
            continue

        fwd_idx = idx + fwd_days
        if fwd_idx >= len(prices):
            continue

        p0, p1 = float(prices.iloc[idx]), float(prices.iloc[fwd_idx])
        if p0 > 0:
            returns.append(p1 / p0 - 1)

    if not returns:
        return 0.0, 0

    return float(np.median(returns)), len(returns)


def cagr_scenarios(
    data_dir: Path | None = None,
    compression_months: list[int] | None = None,
    years_remaining: float = 11.1,
    target_sek: float = 12_934_706,
    min_episode_days: int = 20,
    thin_pre_cap: float | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Portfolio CAGR under different RY compression timings.

    Drag returns:         63d regime-pure returns within HIGH episodes, annualized.
                          Only windows where RY stays HIGH throughout — no compression events.
    Post-compression:     252d returns starting from each episode's end date.
                          What assets actually did after RY compression fired historically.

    Drag phase   (0 → T):   current weights × drag returns
    Compressed   (T → end): target weights  × post-compression returns
    """
    if data_dir is None:
        data_dir = config.raw_data_dir()
    if compression_months is None:
        compression_months = [6, 12, 18, 24, 36, 60]

    eps = episode_stats(data_dir, feature="ry", target_state="HIGH",
                        min_duration_days=min_episode_days)
    episodes = eps["episodes"] + (
        [eps["current_episode"]] if eps.get("current_episode") else []
    )

    # Derive current weights from live portfolio snapshot; fall back to constants
    try:
        from ..portfolio import snapshot as _snapshot
        snap = _snapshot(data_dir)
        cw: dict[str, float] = {}
        for _, row in snap.iterrows():
            tkr = str(row["ticker"])
            w   = float(row["weight"]) if pd.notna(row["weight"]) else 0.0
            if tkr in PORTFOLIO_TICKER_MAP:
                cw[PORTFOLIO_TICKER_MAP[tkr]] = w
            elif tkr == "":
                cw["_spiltan"] = cw.get("_spiltan", 0.0) + w
        _cw_total = sum(cw.values())
        if _cw_total > 0:
            cw = {k: v / _cw_total for k, v in cw.items()}
        else:
            raise ValueError("empty snapshot")
    except Exception:
        _cw_total = sum(CURRENT_WEIGHTS.values())
        cw = {k: v / _cw_total for k, v in CURRENT_WEIGHTS.items()}

    # TARGET_WEIGHTS stay hardcoded — forward-looking intent, not market reality
    _tw_total = sum(TARGET_WEIGHTS.values())
    tw = {k: v / _tw_total for k, v in TARGET_WEIGHTS.items()}

    tickers = [t for t in cw if not t.startswith("_")]

    MIN_N_COMPRESSED = 5  # below this, fall back to drag return for post-compression

    asset_data: dict[str, dict] = {}
    for tkr in tickers:
        if tkr not in TICKER_LOOKUP:
            asset_data[tkr] = {"drag_return": 0.0, "drag_n": 0,
                                "compressed_return": 0.0, "compressed_n": 0,
                                "compressed_fallback": False}
            continue
        prices = _load_prices(data_dir, tkr)
        dr, dn = _regime_pure_drag_return(prices, episodes)
        cr, cn = _post_compression_return(prices, episodes)
        # Use drag return as conservative fallback when compressed N is too thin
        fallback = cn < MIN_N_COMPRESSED
        pre_r  = min(dr, thin_pre_cap) if (thin_pre_cap is not None and fallback) else dr
        post_r = min((dr if fallback else cr), thin_pre_cap) if (thin_pre_cap is not None and fallback) else (dr if fallback else cr)
        asset_data[tkr] = {
            "drag_return":         pre_r,  "drag_n": dn,
            "compressed_return":   post_r, "compressed_n": cn,
            "compressed_fallback": fallback,
        }

    r_drag = (
        sum(cw[t] * asset_data[t]["drag_return"] for t in tickers)
        + cw["_spiltan"] * SPILTAN_RETURN
    )
    r_compressed = (
        sum(tw[t] * asset_data[t]["compressed_return"] for t in tickers)
        + tw["_spiltan"] * SPILTAN_RETURN
    )

    # TPV = sum of config/portfolio.toml positions (2026-07-24 -- the
    # sheet's separate dedicated TPV cell was found to lag the real broker
    # balance more than the position sum does, once idle cash and War
    # Chest were correctly tracked; no longer used anywhere).
    from ..portfolio import snapshot
    tpv = snapshot(data_dir)["value_sek"].sum()

    required_cagr = (target_sek / tpv) ** (1 / years_remaining) - 1

    rows = []
    for T_months in compression_months:
        T_yr = T_months / 12
        remaining = years_remaining - T_yr
        if remaining <= 0:
            continue
        v_compress = tpv * (1 + r_drag) ** T_yr
        v_final    = v_compress * (1 + r_compressed) ** remaining
        cagr       = (v_final / tpv) ** (1 / years_remaining) - 1
        rows.append({
            "compress_months": int(T_months),
            "v_at_compress":   round(v_compress),
            "v_final":         round(v_final),
            "cagr":            round(cagr, 4),
            "vs_required":     round(cagr - required_cagr, 4),
        })

    meta = {
        "r_drag":        r_drag,
        "r_compressed":  r_compressed,
        "required_cagr": required_cagr,
        "tpv":           tpv,
        "asset_data":    asset_data,
    }

    return pd.DataFrame(rows), meta
