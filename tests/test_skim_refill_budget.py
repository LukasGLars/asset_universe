"""Accounting guards for run_skim_refill_budget.py.

The run reports a skim RATE and a cash-at-trigger distribution. Both are
worthless if a skim leaks value, if cash can go negative, or if anything acts
on the bar that generated its own signal. If these fail, do not read the
tables.

Delete alongside run_skim_refill_budget.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import run_skim_refill_budget as m


def frame(**cols) -> pd.DataFrame:
    n = len(next(iter(cols.values())))
    return pd.DataFrame(cols, index=pd.bdate_range("2010-01-04", periods=n))


# ── targets ──────────────────────────────────────────────────────────────────

def test_targets_renormalise_to_one_with_cash():
    for cols in (["AVGO", "LLY", "GOLD", "INDEX"],
                 ["AVGO", "LLY", "GOLD", "INDEX", "BTC", "ETH"],
                 ["AVGO", "GOLD"]):
        tgt = m.targets_for(cols)
        assert set(tgt) == set(cols)
        assert sum(tgt.values()) + m.CASH_TARGET == pytest.approx(1.0, abs=1e-12)


def test_full_target_matches_the_operator_stated_weights():
    tgt = m.targets_for(["AVGO", "LLY", "GOLD", "INDEX", "BTC", "ETH"])
    assert tgt["AVGO"] == pytest.approx(0.20)
    assert tgt["LLY"] == pytest.approx(0.20)
    assert tgt["GOLD"] == pytest.approx(0.20)
    assert tgt["INDEX"] == pytest.approx(0.25)
    assert tgt["BTC"] + tgt["ETH"] == pytest.approx(0.05)


# ── the skim arithmetic ──────────────────────────────────────────────────────

def test_no_skim_at_target():
    tgt = {"A": 0.45, "B": 0.45}
    assert m.skim_excess({"A": 45.0, "B": 45.0}, 10.0, tgt) == {}


def test_no_skim_just_inside_the_band():
    """0.45 x 1.10 = 0.495. A weight of 0.494 must not fire."""
    tgt = {"A": 0.45, "B": 0.45}
    assert m.skim_excess({"A": 49.4, "B": 45.0}, 5.6, tgt) == {}


def test_skim_fires_just_outside_the_band():
    tgt = {"A": 0.45, "B": 0.45}
    out = m.skim_excess({"A": 49.6, "B": 45.0}, 5.4, tgt)
    assert set(out) == {"A"}


def test_skim_moves_the_position_exactly_to_target():
    """Proceeds stay in the account, so total is unchanged and the post-skim
    weight is exactly the target. This is the core identity."""
    tgt = {"A": 0.45, "B": 0.45}
    values, cash = {"A": 60.0, "B": 40.0}, 10.0
    total = sum(values.values()) + cash
    out = m.skim_excess(values, cash, tgt)
    values["A"] -= out["A"]
    cash += out["A"]
    assert sum(values.values()) + cash == pytest.approx(total, abs=1e-12)
    assert values["A"] / total == pytest.approx(tgt["A"], abs=1e-12)


def test_skim_is_never_negative():
    """A breach means the position is ABOVE target, so the excess is positive.
    A negative skim would be a disguised purchase."""
    tgt = {"A": 0.45, "B": 0.45}
    for a_val in (49.7, 60.0, 85.0):
        out = m.skim_excess({"A": a_val, "B": 100 - a_val}, 10.0, tgt)
        assert all(v > 0 for v in out.values())


def test_cash_is_exempt_from_the_band():
    """Cash is the sleeve and the sink. If it were banded at 11% a 10% sleeve
    could never be rebuilt, which is a different question."""
    tgt = {"A": 0.45, "B": 0.45}
    out = m.skim_excess({"A": 20.0, "B": 20.0}, 60.0, tgt)
    assert "CASH" not in out and "cash" not in out
    assert out == {}


def test_zero_total_does_not_divide_by_zero():
    assert m.skim_excess({"A": 0.0}, 0.0, {"A": 0.9}) == {}


# ── declustering and signal timing ───────────────────────────────────────────

def test_declustered_triggers_are_at_least_21_sessions_apart():
    """A steady -3%/day slide makes EVERY session from the 5th onward a raw
    trigger (0.97^5-1 = -14.1%). Declustering must thin that to one every 21
    sessions, which is the only thing keeping a single crash from counting as
    forty events."""
    path = [100.0 * 0.97 ** k for k in range(80)]
    px = frame(AVGO=path, LLY=[100.0] * len(path))
    idxs = sorted(m.trigger_signal_days(px)["AVGO"])
    assert len(idxs) >= 3, idxs
    assert all(b - a >= m.DECLUSTER_DAYS for a, b in zip(idxs, idxs[1:]))
    assert idxs[0] == m.CRASH_WINDOW      # first session the ROC can be computed


def test_trigger_threshold_is_the_live_one():
    assert m.CRASH_WINDOW == 5
    assert m.CRASH_THRESHOLD == -0.10


def test_deploy_happens_strictly_after_the_signal_session():
    """The signal is computed from close(i). If the deploy landed on day i it
    would be trading on a bar it could not have seen complete."""
    drop = [100, 100, 100, 100, 100, 100, 85] + [85] * 30
    px = frame(AVGO=drop, GOLD=[100.0] * len(drop))
    sig = sorted(m.trigger_signal_days(px)["AVGO"])
    assert sig, "expected a trigger"
    res = m.simulate(px, skim=False, contribute=False)
    fired = res["fires"]
    assert not fired.empty
    first_fire_idx = px.index.get_loc(fired["date"].iloc[0])
    assert first_fire_idx == sig[0] + 1


def test_skim_executes_on_the_session_after_the_breach():
    """A breach seen at close(i) is a decision; the sale is at close(i+1)."""
    ramp = [100.0] + [100 * 1.25 ** k for k in range(1, 6)] + [160.0] * 10
    px = frame(AVGO=ramp, GOLD=[100.0] * len(ramp))
    res = m.simulate(px, skim=True, contribute=False)
    sk = res["skims"]
    assert not sk.empty
    # Nothing can be sold on the very first session -- there is no prior close.
    assert px.index.get_loc(sk["date"].iloc[0]) >= 1


# ── whole-run invariants ─────────────────────────────────────────────────────

def test_no_skim_no_contrib_no_trigger_reproduces_buy_and_hold(monkeypatch):
    monkeypatch.setattr(m, "CASH_DAILY", 0.0)
    rise = [100.0 * 1.001 ** k for k in range(60)]
    px = frame(AVGO=rise, GOLD=rise)
    res = m.simulate(px, skim=False, contribute=False)
    assert res["fires"].empty and res["skims"].empty
    growth = rise[-1] / rise[0]
    tgt = m.targets_for(["AVGO", "GOLD"])
    expected = m.START_RC_SEK * (sum(tgt.values()) * growth + m.CASH_TARGET)
    assert res["final"] == pytest.approx(expected, rel=1e-12)


def test_cash_never_goes_negative(monkeypatch):
    monkeypatch.setattr(m, "CASH_DAILY", 0.0)
    rng = np.random.default_rng(7)
    n = 900
    a = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))
    g = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    px = frame(AVGO=list(a), GOLD=list(g))
    res = m.simulate(px, skim=True, contribute=True)
    assert not res["fires"].empty, "expected triggers in a 3%-vol path"
    assert (res["fires"]["cash"] >= -1e-9).all()
    assert (res["fires"]["sleeve_frac"] >= 0).all()


def test_a_fire_deploys_all_cash_so_the_next_fire_starts_from_near_zero(monkeypatch):
    """The budget constraint being measured: full deployment means the sleeve
    is empty afterwards, so a second fire soon after must be underfunded."""
    monkeypatch.setattr(m, "CASH_DAILY", 0.0)
    monkeypatch.setattr(m, "ANNUAL_CONTRIB", 0.0)
    path = [100.0] * 6 + [85.0] * 22 + [70.0] * 22 + [70.0] * 20
    px = frame(AVGO=path, GOLD=[100.0] * len(path))
    res = m.simulate(px, skim=False, contribute=False)
    fr = res["fires"]
    assert len(fr) >= 2, "expected two declustered fires"
    assert fr["sleeve_frac"].iloc[0] > 0.5
    assert fr["cash"].iloc[1] == pytest.approx(0.0, abs=1e-6)


def test_skim_arm_has_at_least_as_much_cash_at_fires_as_no_skim(monkeypatch):
    """Not a claim that skimming pays -- only that adding a cash SOURCE cannot
    reduce cash on hand. If it does, the skim is leaking."""
    monkeypatch.setattr(m, "CASH_DAILY", 0.0)
    rng = np.random.default_rng(11)
    n = 1200
    a = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.028, n)))
    g = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.010, n)))
    px = frame(AVGO=list(a), GOLD=list(g))
    no_skim = m.simulate(px, skim=False, contribute=True)
    with_skim = m.simulate(px, skim=True, contribute=True)
    assert with_skim["skims"].shape[0] > 0
    assert with_skim["fires"]["cash"].sum() >= no_skim["fires"]["cash"].sum()
