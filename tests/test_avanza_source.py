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
