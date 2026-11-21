"""Avanza price source. The currency trap is the whole point of these tests:
Avanza quotes each instrument in its LISTING currency (LLY/AVGO in USD, the
iShares gold ETC in EUR, the Virtune ETPs in SEK). Treating every quote as SEK
would silently value a US holding at 1/9.6 of reality.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from asset_universe.download import avanza


def test_fetch_quote_returns_none_for_a_dead_id(monkeypatch):
    monkeypatch.setattr(avanza, "_get", lambda *a, **k: None)
    assert avanza.fetch_quote("999999999") is None


def test_fetch_quote_reads_price_and_listing_currency(monkeypatch):
    monkeypatch.setattr(avanza, "_get", lambda *a, **k: {
        "name": "Eli Lilly", "quote": {"last": 1159.6},
        "listing": {"currency": "USD", "marketPlaceName": "NYSE"}})
    q = avanza.fetch_quote("4026")
    assert q["close"] == 1159.6
    assert q["currency"] == "USD"      # NOT SEK


def test_fetch_builds_a_single_row_frame(monkeypatch):
    monkeypatch.setattr(avanza, "_get", lambda *a, **k: {
        "name": "Virtune Bitcoin", "quote": {"last": 128.36},
        "listing": {"currency": "SEK"}})
    df = avanza.fetch("1639655")
    assert len(df) == 1
    assert df["close"].iloc[0] == 128.36
    assert {"date", "open", "high", "low", "close", "volume"} <= set(df.columns)


def test_verify_currencies_flags_a_config_mismatch(monkeypatch):
    monkeypatch.setattr(avanza, "fetch_quote",
                        lambda oid: {"currency": "USD", "close": 1.0, "name": "x"})
    bad = avanza.verify_currencies([
        {"name": "Eli Lilly", "ticker": "4026", "category": "avanza", "currency": "SEK"}])
    assert len(bad) == 1
    assert "config says SEK" in bad[0] and "Avanza quotes USD" in bad[0]


def test_verify_currencies_silent_when_they_agree(monkeypatch):
    monkeypatch.setattr(avanza, "fetch_quote",
                        lambda oid: {"currency": "SEK", "close": 128.36, "name": "x"})
    assert avanza.verify_currencies([
        {"name": "Virtune Bitcoin", "ticker": "1639655",
         "category": "avanza", "currency": "SEK"}]) == []


def test_verify_currencies_ignores_non_avanza_positions(monkeypatch):
    def boom(_): raise AssertionError("should not fetch for a yfinance position")
    monkeypatch.setattr(avanza, "fetch_quote", boom)
    assert avanza.verify_currencies([
        {"name": "Broadcom", "ticker": "AVGO", "category": "equities", "currency": "USD"}]) == []


# ── dates (fixed 2026-11-21) ──────────────────────────────────────────────────
import pandas as _pd
from asset_universe.store import writer as _writer


def test_local_date_uses_stockholm_time_summer_and_winter():
    # CET midnight 2026-11-19 = 23:00 UTC the 18th; CEST midnight 2026-07-01 = 22:00 UTC the 30th
    assert avanza._local_date(1795042800000) == _pd.Timestamp("2026-11-19")
    assert avanza._local_date(1782856800000) == _pd.Timestamp("2026-07-01")


def test_quote_is_dated_by_its_own_timestamp_not_today(monkeypatch):
    monkeypatch.setattr(avanza, "_get", lambda *a, **k: {
        "quote": {"last": 594.18, "timeOfLast": 1795042800000}, "listing": {"currency": "SEK"}})
    assert avanza.fetch_quote("417655")["date"] == _pd.Timestamp("2026-11-19")


def test_fund_history_is_anchored_to_the_current_nav(monkeypatch):
    def fake(url, **k):
        if "fund-guide/chart" in url:
            return {"dataSerie": [{"x": 1794697200000, "y": 0.0},      # 2026-11-15 CET
                                  {"x": 1795042800000, "y": -10.0}]}   # 2026-11-19 CET
        return {"quote": {"last": 90.0, "timeOfLast": 1795042800000}, "listing": {}}
    monkeypatch.setattr(avanza, "_get", fake)
    h = avanza.fetch_history("417655")
    assert list(h.date) == [_pd.Timestamp("2026-11-15"), _pd.Timestamp("2026-11-19")]
    assert abs(h.close.iloc[0] - 100.0) < 1e-9 and h.close.iloc[-1] == 90.0


def test_write_replacing_repairs_misdated_rows(tmp_path):
    p = tmp_path / "x.parquet"
    old = avanza._frame([_pd.Timestamp(d) for d in ("2026-11-17", "2026-11-20", "2026-11-21")], [1.0, 2.0, 3.0])
    old.to_parquet(p, index=False)                                     # 11-21 is a Saturday, fetch-dated
    new = avanza._frame([_pd.Timestamp(d) for d in ("2026-11-18", "2026-11-19")], [5.0, 6.0])
    _writer.write_replacing(p, new)
    got = _pd.read_parquet(p)
    assert list(got.date) == [_pd.Timestamp("2026-11-17"), _pd.Timestamp("2026-11-18"), _pd.Timestamp("2026-11-19")]
    assert list(got.close) == [1.0, 5.0, 6.0]
