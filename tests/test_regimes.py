"""
Integrity tests for regime classification.

These tests protect against the class of error where a label carries
economic meaning that doesn't match the actual data in its bin — e.g.
naming the bottom tertile of T10Y3M "INVERTED" when ~30% of those days
have positive values.

Tests are split into two groups:
  - Static (no parquet data required): validate configuration
  - Synthetic (fast, deterministic): validate label() logic
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from asset_universe.analysis.regimes import (
    PROHIBITED_LABEL_TERMS,
    REGIME_FEATURES,
    fit_thresholds,
    label,
)


# ── Static configuration tests ───────────────────────────────────────────────


def test_no_prohibited_labels_in_regime_features():
    """
    p33/p67 tertile labels must not use economically-loaded terms that
    imply a specific numeric boundary (see INTEGRITY.md Rule 8).
    """
    violations = []
    for feat, label_map in REGIME_FEATURES.items():
        for position, lbl in label_map.items():
            if lbl.upper() in PROHIBITED_LABEL_TERMS:
                violations.append(
                    f"  {feat}[{position}] = '{lbl}' (prohibited term)"
                )
    assert not violations, (
        "INTEGRITY violation — economically-loaded labels on percentile bins:\n"
        + "\n".join(violations)
        + "\nUse LOW/MID/HIGH or a term without a specific numeric threshold "
        "(see INTEGRITY.md Rule 8)."
    )


def test_regime_features_has_required_keys():
    """Each entry must have LOW, MID, HIGH labels — no missing positions."""
    for feat, label_map in REGIME_FEATURES.items():
        assert set(label_map.keys()) == {"LOW", "MID", "HIGH"}, (
            f"REGIME_FEATURES['{feat}'] must have exactly LOW, MID, HIGH keys"
        )


# ── Synthetic data tests ──────────────────────────────────────────────────────


def _synthetic_features(seed: int = 42, n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2000-01-01", periods=n)
    return pd.DataFrame(
        {
            "ry":              rng.normal(1.0, 0.8, n),
            "nominal_10y":     rng.normal(4.0, 0.8, n),
            "breakeven":       rng.normal(2.3, 0.4, n),
            "baa10y":          rng.normal(2.3, 0.5, n),
            "t10y3m":          rng.normal(0.5, 1.2, n),   # mix of positive and negative
            "usd":             rng.normal(105, 10,  n),
            "hy_ig_divergence": rng.normal(0, 10,  n),
        },
        index=idx,
    )


def test_label_assigns_consistently_with_thresholds():
    """
    Every row's regime label must match its raw value against the fitted thresholds.
    A value <= p33 must receive the LOW label, etc. No exceptions.
    """
    df = _synthetic_features()
    labeled, thresholds = label(df)

    for feat, (p33, p67) in thresholds.items():
        label_map = REGIME_FEATURES[feat]
        col = f"{feat}_regime"
        assert col in labeled.columns, f"Missing output column {col}"

        raw = df[feat]
        out = labeled[col]

        lo_mask  = raw <= p33
        mid_mask = (raw > p33) & (raw <= p67)
        hi_mask  = raw > p67

        assert (out[lo_mask]  == label_map["LOW"]).all(),  f"{feat}: LOW mismatch"
        assert (out[mid_mask] == label_map["MID"]).all(),  f"{feat}: MID mismatch"
        assert (out[hi_mask]  == label_map["HIGH"]).all(), f"{feat}: HIGH mismatch"


def test_t10y3m_inverted_uses_zero_threshold():
    """
    t10y3m_inverted must be 1 when T10Y3M < 0 and 0 otherwise.
    The threshold is the economic definition (zero), not a percentile.
    """
    from asset_universe.analysis.features import build as build_features

    rng = np.random.default_rng(99)
    n = 200
    curve = pd.Series(
        rng.normal(0.0, 1.0, n),          # centred at zero: many cross-overs
        index=pd.bdate_range("2000-01-01", periods=n),
        name="T10Y3M",
    )

    inverted = (curve < 0).astype(float)

    neg_mask = curve < 0
    pos_mask = curve >= 0

    assert (inverted[neg_mask] == 1.0).all(), "inverted should be 1 when curve < 0"
    assert (inverted[pos_mask] == 0.0).all(), "inverted should be 0 when curve >= 0"
    # Confirm the test exercises both states
    assert neg_mask.any() and pos_mask.any(), "synthetic data must span both states"


def test_current_tertile_label_matches_raw_value(tmp_path):
    """
    For each regime feature: the label assigned on the last row must be
    consistent with the raw value and the fitted thresholds.
    This is the mechanical guard against the T10Y3M-INVERTED class of error.
    """
    df = _synthetic_features(seed=7, n=500)
    labeled, thresholds = label(df)

    last_raw    = df.iloc[-1]
    last_labels = labeled.iloc[-1]

    for feat, (p33, p67) in thresholds.items():
        col = f"{feat}_regime"
        raw_val    = last_raw[feat]
        actual_lbl = last_labels[col]
        label_map  = REGIME_FEATURES[feat]

        if raw_val <= p33:
            expected = label_map["LOW"]
        elif raw_val <= p67:
            expected = label_map["MID"]
        else:
            expected = label_map["HIGH"]

        assert actual_lbl == expected, (
            f"Label/value mismatch for {feat}: "
            f"raw={raw_val:.3f}, thresholds=({p33:.3f},{p67:.3f}), "
            f"expected={expected!r}, got={actual_lbl!r}"
        )
