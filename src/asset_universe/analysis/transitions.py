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
from .engine import query as _engine_query, TICKER_LOOKUP

SPILTAN_RETURN = 0.03

# Current and target weights — source: config sheet GID 928856970
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


def _asset_252d_return(
    ticker: str,
    conditions: dict[str, str],
    data_dir: Path,
) -> tuple[float, int]:
    """Query 252d empirical median return for ticker under conditions."""
    if ticker not in TICKER_LOOKUP:
        return 0.0, 0
    res = _engine_query(conditions, [ticker], forward_days=[252], data_dir=data_dir)
    r = res["results"].get(ticker, {}).get("252d", {})
    if r.get("insufficient"):
        return 0.0, r.get("n", 0)
    return float(r.get("median", 0.0)), int(r.get("n", 0))


def cagr_scenarios(
    data_dir: Path | None = None,
    compression_months: list[int] | None = None,
    years_remaining: float = 11.1,
    target_sek: float = 12_934_706,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Portfolio CAGR under different RY compression timings.

    Drag phase   (0 → T):    current weights, HIGH RY regime returns
    Compressed   (T → end):  target weights, LOW RY + TIGHT credit returns

    Returns (scenarios_df, metadata) where metadata includes per-asset returns and N.
    """
    if data_dir is None:
        data_dir = config.raw_data_dir()
    if compression_months is None:
        compression_months = [6, 12, 18, 24, 36, 60]

    drag_cond = {
        "ry_regime": "HIGH", "nominal_10y_regime": "HIGH",
        "baa10y_regime": "TIGHT", "usd_regime": "STRONG",
    }
    # Post-compression: RY has fallen; keep credit tight (likely) but relax RY
    compressed_cond = {
        "ry_regime": "LOW", "baa10y_regime": "TIGHT",
    }

    tickers = [t for t in CURRENT_WEIGHTS if not t.startswith("_")]

    asset_data: dict[str, dict] = {}
    for tkr in tickers:
        dr, dn = _asset_252d_return(tkr, drag_cond, data_dir)
        cr, cn = _asset_252d_return(tkr, compressed_cond, data_dir)
        asset_data[tkr] = {
            "drag_return": dr, "drag_n": dn,
            "compressed_return": cr, "compressed_n": cn,
        }

    r_drag = (
        sum(CURRENT_WEIGHTS[t] * asset_data[t]["drag_return"] for t in tickers)
        + CURRENT_WEIGHTS["_spiltan"] * SPILTAN_RETURN
    )
    r_compressed = (
        sum(TARGET_WEIGHTS[t] * asset_data[t]["compressed_return"] for t in tickers)
        + TARGET_WEIGHTS["_spiltan"] * SPILTAN_RETURN
    )

    try:
        from ..portfolio import _fetch_sheet_tpv
        tpv = _fetch_sheet_tpv() or 1_101_671
    except Exception:
        tpv = 1_101_671

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
