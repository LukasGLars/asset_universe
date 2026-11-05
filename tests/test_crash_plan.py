import crash_plan as cp
from check_signal_changes import build_actionable_message, extract_fingerprint

BASE, TARGET = 1_000_000, 100_000  # cash target 10% -> tranche 33,333


def _row(name, roc, value, close=100.0):
    return {"name": name, "roc": roc, "close": close, "value": value}


def _plan(rows, cash=96_000, used=None):
    return {r["name"]: r for r in cp.plan(rows, cash, BASE, TARGET, used)}


def test_roc_needs_six_closes():
    assert abs(cp.roc([100] * 5 + [90]) + 0.10) < 1e-12
    assert cp.roc([100] * 5) is None


def test_one_trigger_buys_one_equal_tranche():
    out = _plan([_row("Broadcom", -0.11, 200_000), _row("Eli Lilly", -0.02, 200_000)])
    assert round(out["Broadcom"]["buy_kr"]) == 33_333
    assert out["Broadcom"]["next_price"] == 90.0
    assert out["Eli Lilly"]["state"] == cp.ARMED


def test_tranche_size_does_not_shrink_as_cash_is_spent():
    first = _plan([_row("Broadcom", -0.11, 200_000)], cash=96_000)["Broadcom"]["buy_kr"]
    second = _plan([_row("Broadcom", -0.11, 200_000)], cash=62_000,
                   used={"Broadcom": 1})["Broadcom"]["buy_kr"]
    assert round(first) == round(second) == 33_333


def test_max_two_tranches_per_holding():
    out = _plan([_row("Broadcom", -0.12, 200_000)], cash=30_000, used={"Broadcom": 2})
    assert out["Broadcom"]["buy_kr"] == 0
    assert "2 tranches already used" in out["Broadcom"]["why"]


def test_third_tranche_is_whatever_cash_is_left():
    out = _plan([_row("Eli Lilly", -0.12, 200_000)], cash=29_000,
                used={"Broadcom": 2, "Eli Lilly": 0})
    assert out["Eli Lilly"]["buy_kr"] == 29_000


def test_several_triggers_split_when_cash_is_short():
    out = _plan([_row("Broadcom", -0.12, 150_000), _row("Eli Lilly", -0.10, 150_000)], cash=40_000)
    assert out["Broadcom"]["buy_kr"] == out["Eli Lilly"]["buy_kr"] == 20_000


def test_cap_limits_the_buy():
    out = _plan([_row("Eli Lilly", -0.15, 270_000)])
    assert round(out["Eli Lilly"]["buy_kr"]) == 10_000  # room to 28% of 1M


def test_spent_reserve_says_so():
    out = _plan([_row("Broadcom", -0.12, 150_000)], cash=0)
    assert out["Broadcom"]["buy_kr"] == 0 and "spent" in out["Broadcom"]["why"]


def test_counter_round_trip(tmp_path, monkeypatch):
    p = tmp_path / "s.toml"
    monkeypatch.setattr(cp, "STATE_PATH", p)
    cp.save_used({"Broadcom": 1}, p)
    assert cp.load_used(p) == {"Broadcom": 1, "Eli Lilly": 0, "LF Global Index": 0}
    assert cp.load_used(tmp_path / "missing.toml")["Broadcom"] == 0


def _panel(rows, cash=96_000, used=None):
    return "\n".join(cp.format_lines(cp.plan(rows, cash, BASE, TARGET, used), cash, TARGET))


def test_alert_fires_once_and_quotes_the_tranche():
    calm = _panel([_row("Broadcom", -0.03, 200_000), _row("Eli Lilly", -0.01, 200_000)])
    crash = _panel([_row("Broadcom", -0.03, 200_000), _row("Eli Lilly", -0.11, 200_000)])
    subject, body = build_actionable_message(extract_fingerprint(calm), extract_fingerprint(crash))
    assert "Crash trigger Eli Lilly" in subject
    assert "BUY 33,333 kr (tranche 1 of max 2" in body and "$90.00" in body
    assert build_actionable_message(extract_fingerprint(crash), extract_fingerprint(crash)) is None


def test_crash_rows_do_not_leak_into_rebalance_rows():
    fp = extract_fingerprint(_panel([_row("Broadcom", -0.03, 200_000)]))
    assert fp["rebal_rows"] == {} and "Broadcom" in fp["crash_rows"]


def test_live_state_file_is_valid():
    assert set(cp.load_used()) == set(cp.HOLDINGS)


def test_index_is_exempt_in_sightline():
    from sightline import load_config
    assert "global_index" in load_config()["exemptions"]
