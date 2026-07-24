import math
import urllib.error

import pytest

import asset_universe.portfolio as portfolio
from asset_universe.portfolio import (
    future_value_with_contributions,
    years_to_reach_target,
    _fetch_sheet_tpv,
    _solve_required_cagr,
)


class _FakeResponse:
    def __init__(self, body: bytes, content_type: str = "text/csv"):
        self._body = body
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


TPV_CSV_BODY = "date,value\n2026-07-24,1102207\n".encode("utf-8-sig")


def test_required_cagr_zero_contribution_matches_pure_compounding():
    # Regression: monthly_contribution=0 must reproduce the exact prior
    # formula, (target/tpv)**(1/years) - 1.
    tpv, target, years = 1_000_000.0, 5_000_000.0, 10.0
    expected = (target / tpv) ** (1 / years) - 1
    assert math.isclose(_solve_required_cagr(tpv, target, years, 0.0), expected, rel_tol=1e-9)


def test_required_cagr_with_contributions_is_lower_than_without():
    # The whole point of the fix: ongoing contributions must lower the bar,
    # not leave it unchanged. This was previously silently ignored.
    tpv, target, years = 1_090_000.0, 12_930_000.0, 11.1
    no_contrib = _solve_required_cagr(tpv, target, years, 0.0)
    with_contrib = _solve_required_cagr(tpv, target, years, 6000.0)
    assert with_contrib < no_contrib
    # Sanity-check the magnitude is in the right ballpark (confirmed
    # 2026-07-02: ~24.9% -> ~22.1% at similar inputs), not just "lower".
    assert 0.20 < with_contrib < 0.23


def test_future_value_with_contributions_zero_contribution_is_pure_compounding():
    tpv, rate, years = 1_000_000.0, 0.15, 10.0
    fv = future_value_with_contributions(tpv, rate, years, 0.0)
    assert math.isclose(fv, tpv * (1 + rate) ** years, rel_tol=1e-9)


def test_future_value_with_contributions_adds_meaningful_value():
    # 6,000 kr/month for ~11 years is real money -- confirm it's not a
    # rounding-level effect (silently dropping it would understate the
    # true projection).
    tpv, rate, years = 1_000_000.0, 0.20, 11.0
    fv_no_contrib = future_value_with_contributions(tpv, rate, years, 0.0)
    fv_with_contrib = future_value_with_contributions(tpv, rate, years, 6000.0)
    assert fv_with_contrib - fv_no_contrib > 1_000_000.0


def test_years_to_reach_target_zero_when_already_there():
    assert years_to_reach_target(10_000_000.0, 0.10, 6000.0, 5_000_000.0) == 0.0


def test_years_to_reach_target_roundtrips_with_future_value():
    tpv, rate, monthly = 1_000_000.0, 0.20, 6000.0
    target = future_value_with_contributions(tpv, rate, 8.0, monthly)
    yrs = years_to_reach_target(tpv, rate, monthly, target)
    assert math.isclose(yrs, 8.0, abs_tol=1e-3)


# ── _fetch_sheet_tpv: TPV must always come from the sheet, nothing else ─────
# (2026-07-24 -- the operator's explicit rule after this session's live TPV
# figure turned out to not match the position-table sum, tracing back to a
# silent fallback in fi_pace()).

def test_fetch_sheet_tpv_succeeds_first_try(monkeypatch):
    monkeypatch.setattr(portfolio.urllib.request, "urlopen",
                         lambda req, timeout=None: _FakeResponse(TPV_CSV_BODY))
    assert _fetch_sheet_tpv() == 1102207.0


def test_fetch_sheet_tpv_retries_transient_timeout_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def flaky_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("The read operation timed out")
        return _FakeResponse(TPV_CSV_BODY)

    monkeypatch.setattr(portfolio.urllib.request, "urlopen", flaky_urlopen)
    monkeypatch.setattr(portfolio.time, "sleep", lambda s: None)

    tpv = _fetch_sheet_tpv(retries=3, backoff_seconds=0.01)

    assert calls["n"] == 3
    assert tpv == 1102207.0


def test_fetch_sheet_tpv_raises_after_exhausting_retries_no_fallback():
    """The core rule: exhausting retries must raise, never silently
    substitute a different number (e.g. summing config/portfolio.toml)."""
    def always_fails(req, timeout=None):
        raise urllib.error.URLError("connection reset")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(portfolio.urllib.request, "urlopen", always_fails)
        mp.setattr(portfolio.time, "sleep", lambda s: None)
        try:
            _fetch_sheet_tpv(retries=3, backoff_seconds=0.01)
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "3 attempts" in str(exc)
            assert isinstance(exc.__cause__, urllib.error.URLError)


def test_fetch_sheet_tpv_does_not_retry_html_content_error(monkeypatch):
    """Wrong sharing setting -> HTML response is a content error, not a
    transient one -- must fail fast, not waste 3 retries on it."""
    calls = {"n": 0}

    def returns_html(req, timeout=None):
        calls["n"] += 1
        return _FakeResponse(b"<html>login required</html>", content_type="text/html")

    monkeypatch.setattr(portfolio.urllib.request, "urlopen", returns_html)

    try:
        _fetch_sheet_tpv(retries=3, backoff_seconds=0.01)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "HTML" in str(exc)
    assert calls["n"] == 1


def test_fetch_sheet_tpv_raises_on_unparseable_row(monkeypatch):
    bad_body = "date,value\n2026-07-24,not-a-number\n".encode("utf-8-sig")
    monkeypatch.setattr(portfolio.urllib.request, "urlopen",
                         lambda req, timeout=None: _FakeResponse(bad_body))
    try:
        _fetch_sheet_tpv()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "no parseable digits" in str(exc)


# ── fi_pace(): no fallback to summing positions when the sheet fetch fails ──

def test_fi_pace_uses_sheet_tpv_exactly(monkeypatch, tmp_path):
    monkeypatch.setattr(portfolio, "_fetch_sheet_tpv", lambda: 1102207.0)
    monkeypatch.setattr(portfolio, "_load_portfolio_config", lambda: {
        "fi": {
            "start_date": "2025-07-21",
            "start_value_sek": 925983,
            "target_sek": 12934706,
            "years": 12,
            "monthly_contribution_sek": 6000,
        }
    })
    result = portfolio.fi_pace(tmp_path)
    assert result["tpv_sek"] == 1102207.0


def test_fi_pace_raises_when_sheet_fetch_fails_no_position_sum_fallback(monkeypatch, tmp_path):
    """The regression this whole fix targets: fi_pace() must NOT silently
    fall back to snapshot(data_dir)["value_sek"].sum() when the sheet fetch
    fails -- that's a materially different number computed a different way,
    and substituting it silently is exactly what caused this session's
    confusion over which TPV figure was "real"."""
    def raises():
        raise RuntimeError("TPV sheet fetch failed after 3 attempts")

    monkeypatch.setattr(portfolio, "_fetch_sheet_tpv", raises)
    monkeypatch.setattr(portfolio, "_load_portfolio_config", lambda: {
        "fi": {
            "start_date": "2025-07-21",
            "start_value_sek": 925983,
            "target_sek": 12934706,
            "years": 12,
            "monthly_contribution_sek": 6000,
        }
    })
    # snapshot() must never even be called as a fallback.
    def snapshot_should_not_be_called(data_dir=None):
        raise AssertionError("snapshot() fallback must not be used -- sheet is the only source")

    monkeypatch.setattr(portfolio, "snapshot", snapshot_should_not_be_called)

    try:
        portfolio.fi_pace(tmp_path)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "TPV sheet fetch failed" in str(exc)
