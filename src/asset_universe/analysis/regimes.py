"""
Fit empirical regime thresholds and label the historical date record.

Thresholds are derived from data distributions (p33/p67 tertile splits).
Never hardcoded. See INTEGRITY.md.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import features as feat_module
from .. import config

# Features used for regime conditioning and their human-readable labels
REGIME_FEATURES: dict[str, dict[str, str]] = {
    "ry":     {"LOW": "LOW",      "MID": "MID",    "HIGH": "HIGH"},
    "baa10y": {"LOW": "TIGHT",    "MID": "MID",    "HIGH": "WIDE"},
    "t10y3m": {"LOW": "INVERTED", "MID": "FLAT",   "HIGH": "STEEP"},
    "usd":    {"LOW": "WEAK",     "MID": "MID",    "HIGH": "STRONG"},
}

# Confidence flag: HY-IG divergence beyond this many std devs -> UNCERTAIN
HY_DIVERGENCE_STD_THRESHOLD = 1.5

# Minimum N to compute meaningful thresholds
MIN_N_THRESHOLD = 100


def fit_thresholds(df: pd.DataFrame) -> dict[str, tuple[float, float]]:
    """
    Compute p33/p67 tertile thresholds for each conditioning feature.
    Uses only data in df — caller controls the window (no look-ahead).

    Returns {feature_name: (p33, p67)}.
    """
    thresholds: dict[str, tuple[float, float]] = {}
    for feat in REGIME_FEATURES:
        s = df[feat].dropna()
        if len(s) < MIN_N_THRESHOLD:
            continue
        thresholds[feat] = (
            float(np.percentile(s, 33.33)),
            float(np.percentile(s, 66.67)),
        )
    return thresholds


def label(
    df: pd.DataFrame,
    thresholds: dict[str, tuple[float, float]] | None = None,
) -> tuple[pd.DataFrame, dict[str, tuple[float, float]]]:
    """
    Add *_regime columns to df based on fitted thresholds.
    Also adds regime_confidence based on HY-IG divergence.

    Returns (labeled_df, thresholds).
    """
    if thresholds is None:
        thresholds = fit_thresholds(df)

    out = df.copy()

    for feat, label_map in REGIME_FEATURES.items():
        if feat not in df.columns or feat not in thresholds:
            continue
        p33, p67 = thresholds[feat]
        conditions = [
            df[feat] <= p33,
            (df[feat] > p33) & (df[feat] <= p67),
            df[feat] > p67,
        ]
        choices = [label_map["LOW"], label_map["MID"], label_map["HIGH"]]
        out[f"{feat}_regime"] = np.select(conditions, choices, default=pd.NA)

    # Regime confidence from HY-IG divergence
    out["regime_confidence"] = "HIGH"
    if "hy_ig_divergence" in df.columns:
        div = df["hy_ig_divergence"].dropna()
        if len(div) >= 30:
            div_std = float(div.std())
            threshold = HY_DIVERGENCE_STD_THRESHOLD * div_std
            uncertain = df["hy_ig_divergence"] > threshold
            out.loc[uncertain, "regime_confidence"] = "UNCERTAIN"

    return out, thresholds


def build(data_dir: Path | None = None) -> tuple[pd.DataFrame, dict]:
    """
    Full pipeline: build features -> fit thresholds -> label.
    Returns (labeled_df, thresholds).
    """
    if data_dir is None:
        data_dir = config.raw_data_dir()
    df = feat_module.build(data_dir)
    return label(df)


def describe_thresholds(thresholds: dict[str, tuple[float, float]]) -> str:
    """Human-readable threshold summary for inspection/logging."""
    lines = ["Regime thresholds (data-derived, p33/p67):"]
    for feat, (p33, p67) in thresholds.items():
        label_map = REGIME_FEATURES.get(feat, {})
        lo = label_map.get("LOW", "LOW")
        mid = label_map.get("MID", "MID")
        hi = label_map.get("HIGH", "HIGH")
        lines.append(f"  {feat:10}  {lo} (<{p33:.2f}) | {mid} ({p33:.2f}-{p67:.2f}) | {hi} (>{p67:.2f})")
    return "\n".join(lines)
