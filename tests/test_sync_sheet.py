import urllib.error

import sync_sheet


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


CSV_BODY = "Asset,shares,value\nBroadcom,49,\n".encode("utf-8-sig")


def test_fetch_sheet_rows_succeeds_first_try(monkeypatch):
    monkeypatch.setattr(sync_sheet.urllib.request, "urlopen",
                         lambda req, timeout=None: _FakeResponse(CSV_BODY))
    rows = sync_sheet.fetch_sheet_rows()
    assert rows[0]["Asset"] == "Broadcom"


def test_fetch_sheet_rows_retries_transient_timeout_then_succeeds(monkeypatch):
    """Regression for the real 2026-07-16 failure: a single timeout on
    Google's export endpoint previously killed the whole watchdog job with
    no second attempt."""
    calls = {"n": 0}

    def flaky_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("The read operation timed out")
        return _FakeResponse(CSV_BODY)

    monkeypatch.setattr(sync_sheet.urllib.request, "urlopen", flaky_urlopen)
    monkeypatch.setattr(sync_sheet.time, "sleep", lambda s: None)

    rows = sync_sheet.fetch_sheet_rows(retries=3, backoff_seconds=0.01)

    assert calls["n"] == 3
    assert rows[0]["Asset"] == "Broadcom"


def test_fetch_sheet_rows_raises_after_exhausting_retries(monkeypatch):
    def always_fails(req, timeout=None):
        raise urllib.error.URLError("connection reset")

    monkeypatch.setattr(sync_sheet.urllib.request, "urlopen", always_fails)
    monkeypatch.setattr(sync_sheet.time, "sleep", lambda s: None)

    try:
        sync_sheet.fetch_sheet_rows(retries=3, backoff_seconds=0.01)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "3 attempts" in str(exc)
        assert isinstance(exc.__cause__, urllib.error.URLError)


def test_fetch_sheet_rows_does_not_retry_html_content_error(monkeypatch):
    """A wrong-sharing-setting HTML response is a content error, not a
    transient one -- retrying it wastes time and won't fix anything."""
    calls = {"n": 0}

    def returns_html(req, timeout=None):
        calls["n"] += 1
        return _FakeResponse(b"<html>login required</html>", content_type="text/html")

    monkeypatch.setattr(sync_sheet.urllib.request, "urlopen", returns_html)

    try:
        sync_sheet.fetch_sheet_rows(retries=3, backoff_seconds=0.01)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "HTML" in str(exc)
    assert calls["n"] == 1


# ── ASSET_MAP / _lookup: sheet asset names -> portfolio.toml names ─────────
# (2026-07-24 -- "Cash" is a real, named row in the sheet's config tab
# for Reactor Core's idle cash, previously untracked here and set as a
# one-off manual value; wired into ASSET_MAP so it auto-syncs like every
# other position instead of going stale again.)

def test_lookup_maps_cash_to_reactor_core_cash():
    assert sync_sheet._lookup("Cash") == "Reactor Core Cash"


def test_lookup_exact_match_takes_priority_over_prefix_fuzz():
    """"Cash" is a short, generic key -- confirm an exact sheet cell match
    resolves directly via the ASSET_MAP dict lookup, not the fuzzier
    startswith() loop, so it can't accidentally match an unrelated future
    row that merely starts with or contains "Cash"."""
    assert sync_sheet._lookup("Cash") == "Reactor Core Cash"
    assert sync_sheet._lookup("cash") == "Reactor Core Cash"  # case-insensitive


def test_lookup_still_maps_existing_assets_after_cash_added():
    assert sync_sheet._lookup("PPFB.DE") == "Gold"
    assert sync_sheet._lookup("War Chest") == "War Chest"
    assert sync_sheet._lookup("Spiltan Räntefond Sverige") == "Spiltan Räntefond"


# ── Crypto trend sleeve ETPs, and the silent-failure modes ────────────────
def test_asset_map_resolves_both_etp_spellings():
    assert sync_sheet._lookup("Virtune Bitcoin") == "Virtune Bitcoin"
    assert sync_sheet._lookup("Virtune BTC") == "Virtune Bitcoin"
    assert sync_sheet._lookup("Virtune Staked ETH") == "Virtune Staked ETH"
    assert sync_sheet._lookup("Virtune ETH") == "Virtune Staked ETH"


def test_asset_map_resolves_etp_with_trailing_text():
    """The sheet's Asset cells carry suffixes ('Spiltan Räntefond Sverige ')."""
    assert sync_sheet._lookup("Virtune Bitcoin ETP") == "Virtune Bitcoin"


def test_unknown_sheet_row_warns_instead_of_passing_silently(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sync_sheet, "fetch_sheet_rows",
                        lambda *a, **k: [{"Asset": "Solana ETP", "value": "5 000 kr"}])
    rc = sync_sheet.main()
    err = capsys.readouterr().err
    assert "not in ASSET_MAP" in err
    assert "Solana ETP" in err
    assert rc == 0          # a stray row is a warning, not a job failure


def test_mapped_name_without_a_positions_block_fails_loudly(monkeypatch, capsys, tmp_path):
    """The old behaviour printed the change and returned success while
    patch_toml() silently matched nothing."""
    toml = tmp_path / "portfolio.toml"
    toml.write_text('[buckets]\nreactor_core = 1.0\n\n'
                    '[[positions]]\nname = "Gold"\nshares = 1\nbucket = "reactor_core"\n',
                    encoding="utf-8")
    monkeypatch.setattr(sync_sheet, "TOML_PATH", toml)
    monkeypatch.setattr(sync_sheet, "fetch_sheet_rows",
                        lambda *a, **k: [{"Asset": "Virtune Bitcoin", "value": "27 225 kr"}])
    rc = sync_sheet.main()
    assert rc == 1
    assert "no [[positions]] block" in capsys.readouterr().err


def test_etp_value_reaches_the_toml(monkeypatch, capsys, tmp_path):
    toml = tmp_path / "portfolio.toml"
    toml.write_text('[buckets]\ncrypto_sleeve = 0.05\n\n'
                    '[[positions]]\nname = "Virtune Bitcoin"\nshares = 0\n'
                    'bucket = "crypto_sleeve"\nvalue_sek = 0\n',
                    encoding="utf-8")
    monkeypatch.setattr(sync_sheet, "TOML_PATH", toml)
    monkeypatch.setattr(sync_sheet, "fetch_sheet_rows",
                        lambda *a, **k: [{"Asset": "Virtune Bitcoin", "value": "31 400 kr"}])
    assert sync_sheet.main() == 0
    import tomllib
    with open(toml, "rb") as f:
        pos = {p["name"]: p for p in tomllib.load(f)["positions"]}
    assert pos["Virtune Bitcoin"]["value_sek"] == 31400
