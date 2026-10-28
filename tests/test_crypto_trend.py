"""Tests for the crypto trend sleeve rule (crypto_trend.py).

Focus is on the parts that are easy to get silently wrong: the hysteresis
band, the weekday filter, and the ensemble arithmetic.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from asset_universe.analysis import crypto_trend as ct


def _series(vals, start="2020-01-01", freq="D"):
    return pd.Series(vals, index=pd.date_range(start, periods=len(vals), freq=freq))


def test_weekday_closes_drops_weekend_bars():
    idx = pd.date_range("2026-08-31", periods=7, freq="D")  # Mon..Sun
    df = pd.DataFrame({"close": range(7)}, index=idx)
    out = ct.weekday_closes(df)
    assert len(out) == 5
    assert set(out.index.dayofweek) <= {0, 1, 2, 3, 4}


def test_state_series_needs_band_to_flip_long():
    """Sitting just above the MA but inside the band must NOT go long."""
    flat = _series([100.0] * 60)
    st = ct._state_series(flat, 50)
    assert st.iloc[-1] == 0.0                      # never touched the upper band

    nudged = _series([100.0] * 59 + [100.0 * (1 + ct.BAND / 2)])
    assert ct._state_series(nudged, 50).iloc[-1] == 0.0


def test_state_series_flips_and_then_holds_through_the_band():
    """Once long, drifting back inside the band keeps the position -- that
    hysteresis is what stops the 2023-26 whipsaw."""
    vals = [100.0] * 55 + [130.0] * 5              # decisively above -> LONG
    st = ct._state_series(_series(vals), 50)
    assert st.iloc[-1] == 1.0

    # now drift to just below the MA but inside the lower band: still LONG
    closes = _series(vals + [float(_series(vals).rolling(50).mean().iloc[-1]) * (1 - ct.BAND / 2)])
    assert ct._state_series(closes, 50).iloc[-1] == 1.0


def test_state_series_exits_below_lower_band():
    vals = [100.0] * 55 + [130.0] * 5 + [50.0] * 3
    assert ct._state_series(_series(vals), 50).iloc[-1] == 0.0


def test_exposure_is_mean_of_the_three_windows():
    """Rising ramp: fast MA long before the slow one -> a partial tier."""
    vals = list(range(1, 260))                      # monotonic rise
    closes = _series([float(v) for v in vals])
    exp = ct.target_exposure(closes)
    assert exp in (0.0, 1/3, 2/3, 1.0)
    assert exp == pytest.approx(1.0)                # a clean uptrend = all three long


def test_exposure_tiers_are_only_the_four_values():
    vals = [100.0] * 200 + [140.0] * 30 + [90.0] * 20 + [200.0] * 40
    exp = ct.exposure_series(_series([float(v) for v in vals]))
    assert set(exp.unique()) <= {0.0, 1/3, 2/3, 1.0}


def test_target_exposure_matches_exposure_series_tail():
    """The daily number and the history must not drift apart."""
    vals = [100.0 + (i % 40) * 3 for i in range(400)]
    closes = _series([float(v) for v in vals])
    assert ct.target_exposure(closes) == ct.exposure_series(closes).iloc[-1]


def test_last_change_reports_the_most_recent_tier_move():
    vals = [100.0] * 210 + [200.0] * 30
    closes = _series([float(v) for v in vals])
    lc = ct.last_change(closes)
    assert lc is not None
    date, level = lc
    assert level > 0.0
    assert pd.Timestamp(date) in closes.index


def test_rule_states_reports_band_edges_around_the_ma():
    closes = _series([float(100 + i) for i in range(260)])
    for st in ct.rule_states(closes):
        assert st["lower"] < st["ma"] < st["upper"]
        assert st["upper"] == pytest.approx(st["ma"] * (1 + ct.BAND))


def test_sol_is_not_in_the_live_universe():
    """Deliberate: its backtest is hindsight selection and that tier can fail
    faster than a daily rule can exit. Guard against a casual re-add."""
    assert "SOL-USD" not in ct.ASSETS
    assert set(ct.ASSETS) == {"BTC-USD", "ETH-USD"}


# ── Dashboard section (the text check_signal_changes.py parses) ─────────────

def _write_store(tmp_path, ticker, closes):
    import pandas as pd
    d = tmp_path / "crypto"
    d.mkdir(parents=True, exist_ok=True)
    idx = pd.bdate_range("2022-01-03", periods=len(closes))
    pd.DataFrame({"date": idx, "close": closes}).to_parquet(
        d / f"{ticker.replace('-', '_')}.parquet", index=False)


def test_summary_kr_amount_is_the_TARGET_not_the_holding(tmp_path, capsys, monkeypatch):
    """The alert quotes this line verbatim, so the kr figure must be
    held * target_exposure. Getting this wrong would tell the operator to
    hold the full position on a de-risk signal."""
    import run_crypto_trend as rct

    _write_store(tmp_path, "BTC-USD", [100.0] * 210 + [300.0] * 40)
    _write_store(tmp_path, "ETH-USD", [100.0] * 210 + [300.0] * 40)
    monkeypatch.setattr(rct, "_sleeve_capital", lambda *a, **k: {"BTC-USD": 27225, "ETH-USD": 27225})

    rct.crypto_trend_daily_summary(tmp_path)
    out = capsys.readouterr().out

    sig = rct.signals(tmp_path)
    for ticker, s in sig.items():
        expected = f"{s['exposure']:.0%}  = {27225 * s['exposure']:,.0f} kr of 27 225 kr".replace(",", " ")
        assert expected in out, f"{ticker}: expected {expected!r} in\n{out}"


def test_summary_survives_an_asset_missing_from_the_store(tmp_path, capsys):
    """A missing file must be skipped, never reported as 0% -- a silent FLAT
    would read as a sell signal in the daily diff."""
    import run_crypto_trend as rct

    _write_store(tmp_path, "BTC-USD", [100.0] * 210 + [300.0] * 40)
    rct.crypto_trend_daily_summary(tmp_path)
    out = capsys.readouterr().out
    assert "BTC-USD" in out
    assert "ETH-USD" not in out
    assert "Ethereum" not in out
    assert "Target       : 0%" not in out


def test_summary_says_so_when_the_store_is_empty(tmp_path, capsys):
    import run_crypto_trend as rct
    rct.crypto_trend_daily_summary(tmp_path)
    assert "no crypto data in store" in capsys.readouterr().out


def test_sleeve_capital_is_target_weight_times_base():
    import run_crypto_trend as rct
    pos = [
        {"name": "Broadcom", "value_sek": 600.0, "target": 0.6},
        {"name": "Virtune Bitcoin", "value_sek": 30.0, "target": 0.025},
        {"name": "Virtune Staked ETH", "value_sek": 10.0, "target": 0.025},
        {"name": "Spiltan", "value_sek": 500.0, "target": 0.0},  # outside the base
        {"name": "Cash", "value_sek": 360.0, "target": 0.35},
    ]
    cap = rct.sleeve_capital(pos)
    assert cap == {"BTC-USD": 0.025 * 1000.0, "ETH-USD": 0.025 * 1000.0}


def test_sleeve_capital_skips_missing_or_untargeted_rows():
    import run_crypto_trend as rct
    pos = [{"name": "Broadcom", "value_sek": 100.0, "target": 1.0},
           {"name": "Virtune Bitcoin", "value_sek": 5.0, "target": 0.0}]
    assert rct.sleeve_capital(pos) == {}


def test_no_hand_kept_capital_left_in_config():
    import tomllib
    import run_crypto_trend as rct
    with open(rct.PORTFOLIO_TOML, "rb") as f:
        assert "crypto_sleeve" not in tomllib.load(f)


def _toml(tmp_path, btc, eth):
    p = tmp_path / "portfolio.toml"
    p.write_text(
        '[[positions]]\nname = "Virtune Bitcoin"\ntarget_weight = %s\n'
        '[[positions]]\nname = "Virtune Staked ETH"\ntarget_weight = %s\n' % (btc, eth))
    return p


def test_active_legs_follow_target_not_holdings(tmp_path):
    import run_crypto_trend as rct
    assert rct.active_legs(_toml(tmp_path, 0.025, 0.0)) == {"BTC-USD"}
    assert rct.active_legs(_toml(tmp_path, 0.0, 0.0)) == set()


def test_unreadable_config_keeps_alerting(tmp_path):
    import run_crypto_trend as rct
    assert rct.active_legs(tmp_path / "missing.toml") == set(rct.SLEEVE_ROWS)


def test_inactive_sleeve_prints_no_target_line_and_never_alerts(tmp_path, capsys, monkeypatch):
    import run_crypto_trend as rct
    from check_signal_changes import build_actionable_message, extract_fingerprint
    _write_store(tmp_path, "BTC-USD", [100.0] * 210 + [300.0] * 40)
    _write_store(tmp_path, "ETH-USD", [100.0] * 210 + [300.0] * 40)
    monkeypatch.setattr(rct, "_sleeve_capital", lambda *a, **k: {})
    rct.crypto_trend_daily_summary(tmp_path)
    before = capsys.readouterr().out
    monkeypatch.setattr(rct, "active_legs", lambda *a, **k: set())
    rct.crypto_trend_daily_summary(tmp_path)
    after = capsys.readouterr().out
    assert "Target" not in after and "inactive" in after
    # Going from an active 100% to inactive must not read as a sell signal.
    assert build_actionable_message(extract_fingerprint(before), extract_fingerprint(after)) is None
