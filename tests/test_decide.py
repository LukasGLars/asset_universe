import decide
from asset_universe import portfolio

HOLD_READINGS = [{"quarter": "2025Q1", "value": 10}, {"quarter": "2026Q1", "value": 12}]
CUT_READINGS = [{"quarter": "2025Q1", "value": 10}, {"quarter": "2026Q1", "value": 9}]
REQ_READINGS = CUT_READINGS + [
    {"quarter": "2025Q2", "value": 10}, {"quarter": "2026Q2", "value": 11},
    {"quarter": "2025Q3", "value": 10}, {"quarter": "2026Q3", "value": 11},
]


def _pos(name, ticker, value, target, bucket="reactor_core", price=100.0):
    return {"name": name, "ticker": ticker, "bucket": bucket,
            "value_sek": value, "price_sek": price, "target": target}


def _cfg(avgo=HOLD_READINGS):
    return {"AVGO": {"readings": avgo},
            "exemptions": {"gold": {"reason": "x"}, "crypto_sleeve": {"reason": "y"}}}


def _book():
    return [
        _pos("Broadcom", "AVGO", 400.0, 0.4),
        _pos("Gold", "1634504", 300.0, 0.3),
        _pos("Index", "417655", 200.0, 0.2, bucket="global_index"),
        _pos("Reactor Core Cash", "", 100.0, 0.1, price=None),
        _pos("Spiltan", "94867", 50.0, 0.0, bucket="home_base"),
    ]


def _rows(res):
    return {r["name"]: r for r in res["rows"]}


def test_hold_in_band_trades_nothing():
    res = decide.decide(_book(), _cfg(), {}, {})
    rows = _rows(res)
    assert rows["Broadcom"]["verdict"] == "OWN"
    assert all(r["trade_kr"] == 0 for r in res["rows"])
    assert res["denom"] == 1000.0  # Spiltan (no target) excluded


def test_cut_sells_all_and_blocks_contributions():
    res = decide.decide(_book(), _cfg(CUT_READINGS), {}, {})
    r = _rows(res)["Broadcom"]
    assert r["verdict"] == "CUT"
    assert r["trade_kr"] == -400.0
    assert res["next"] != "Broadcom"


def test_requalified_is_not_a_buy():
    res = decide.decide(_book(), _cfg(REQ_READINGS), {}, {})
    r = _rows(res)["Broadcom"]
    assert r["verdict"] == "ENTRY"
    assert r["trade_kr"] == 0
    assert res["next"] != "Broadcom"


def test_out_of_band_sizes_trade_to_target():
    book = _book()
    book[0]["value_sek"] = 700.0  # 700/1300 = 53.8% -> out of band
    res = decide.decide(book, _cfg(), {}, {}, band=0.10)
    r = _rows(res)["Broadcom"]
    assert r["action"].startswith("SELL")
    assert round(r["trade_kr"], 6) == round((0.4 - 700 / 1300) * 1300, 6)


def test_exemptions_and_missing_rule():
    rows = _rows(decide.decide(_book(), _cfg(), {}, {}))
    assert rows["Gold"]["rule"].startswith("exempt")
    assert rows["Index"]["verdict"] == "OWN?"
    assert rows["Reactor Core Cash"]["rule"] == "cash"


def test_crypto_uses_trend_rule_not_band():
    book = _book() + [_pos("Virtune Bitcoin", "1639655", 40.0, 0.025, bucket="crypto_sleeve")]
    sig = {"BTC-USD": {"exposure": 2 / 3, "as_of": "2026-10-16"}}
    r = _rows(decide.decide(book, _cfg(), sig, {"BTC-USD": 60.0}))["Virtune Bitcoin"]
    assert r["rule"].startswith("trend 67%")
    assert r["target_kr"] == 40.0
    assert r["trade_kr"] == 0


def test_held_untargeted_cut_is_surfaced():
    book = _book() + [_pos("Old AVGO lot", "AVGO", 30.0, 0.0)]
    rows = _rows(decide.decide(book, _cfg(CUT_READINGS), {}, {}))
    assert rows["Old AVGO lot"]["trade_kr"] == -30.0


def test_sleeve_rows_exist_in_portfolio():
    names = {p["name"] for p in portfolio._load_portfolio_config()["positions"]}
    assert set(decide.SLEEVE_ROWS.values()) <= names


def test_collections_break_is_review_not_sell():
    res = decide.decide(_book(), _cfg(), {}, {},
                        collections={"AVGO": ("BREAK", "80 days (1.60x)")})
    r = _rows(res)["Broadcom"]
    assert r["verdict"] == "REVIEW"
    assert r["rule"].startswith("Collections BREAK")
    assert r["trade_kr"] == 0
    assert res["next"] != "Broadcom"


def test_sightline_cut_outranks_collections_review():
    res = decide.decide(_book(), _cfg(CUT_READINGS), {}, {},
                        collections={"AVGO": ("BREAK", "x")})
    assert _rows(res)["Broadcom"]["verdict"] == "CUT"


def test_collections_warn_does_not_cut():
    res = decide.decide(_book(), _cfg(), {}, {}, collections={"AVGO": ("WARN", "x")})
    assert _rows(res)["Broadcom"]["verdict"] == "OWN"
