import datetime as dt

import crash_plan as cp
from check_signal_changes import build_actionable_message, extract_fingerprint

BASE, TARGET = 1_000_000, 100_000  # tranche 33,333 -> half 16,667


def _row(name, roc, value, close=100.0, since=None):
    return {"name": name, "roc": roc, "close": close, "value": value, "since": since}


def _plan(rows, cash=96_000, used=None, pending=None):
    return {r["name"]: r for r in cp.plan(rows, cash, BASE, TARGET, used, pending)}


def test_roc_needs_six_closes():
    assert abs(cp.roc([100] * 5 + [90]) + 0.10) < 1e-12
    assert cp.roc([100] * 5) is None


def test_trigger_buys_half_a_tranche():
    out = _plan([_row("Broadcom", -0.11, 200_000), _row("Eli Lilly", -0.02, 200_000)])
    assert round(out["Broadcom"]["buy_kr"]) == 16_667
    assert out["Broadcom"]["next_price"] == 90.0
    assert "first half of tranche 1" in out["Broadcom"]["why"]
    assert out["Eli Lilly"]["state"] == cp.ARMED


def test_open_tranche_waits_then_second_half_after_21_sessions():
    pend = {"Broadcom": {"date": "2026-11-05", "close": 100.0, "half_kr": 16_667}}
    wait = _plan([_row("Broadcom", -0.02, 200_000, close=97, since=10)], used={"Broadcom": 1}, pending=pend)
    assert wait["Broadcom"]["state"] == cp.WAITING and wait["Broadcom"]["buy_kr"] == 0
    due = _plan([_row("Broadcom", 0.03, 200_000, close=105, since=21)], used={"Broadcom": 1}, pending=pend)
    assert due["Broadcom"]["state"] == cp.SECOND_HALF and round(due["Broadcom"]["buy_kr"]) == 16_667


def test_second_half_early_on_a_further_ten_percent_drop():
    pend = {"Broadcom": {"date": "2026-11-05", "close": 100.0, "half_kr": 16_667}}
    out = _plan([_row("Broadcom", -0.05, 180_000, close=89.9, since=4)], used={"Broadcom": 1}, pending=pend)
    assert out["Broadcom"]["state"] == cp.SECOND_HALF


def test_open_second_half_is_reserved_from_new_triggers():
    pend = {"Broadcom": {"date": "2026-11-05", "close": 100.0, "half_kr": 16_667}}
    out = _plan([_row("Broadcom", -0.02, 200_000, since=3), _row("Eli Lilly", -0.11, 200_000)],
                cash=20_000, used={"Broadcom": 1}, pending=pend)
    assert round(out["Eli Lilly"]["buy_kr"]) == 3_333  # 20,000 minus the reserved 16,667


def test_max_two_tranches_per_holding():
    out = _plan([_row("Broadcom", -0.12, 200_000)], used={"Broadcom": 2})
    assert out["Broadcom"]["buy_kr"] == 0 and "2 tranches already used" in out["Broadcom"]["why"]


def test_cap_limits_the_buy():
    out = _plan([_row("Eli Lilly", -0.15, 275_000)])
    assert round(out["Eli Lilly"]["buy_kr"]) == 5_000  # room to 28% of 1M


def test_state_round_trip_and_cli(tmp_path, monkeypatch):
    p = tmp_path / "s.toml"
    monkeypatch.setattr(cp, "STATE_PATH", p)
    cp.main(["bought", "Broadcom"], today=dt.date(2026, 11, 6), close=312.5, half_kr=16_667)
    st = cp.load_state(p)
    assert st["used"]["Broadcom"] == 1
    assert st["pending"]["Broadcom"] == {"date": "2026-11-06", "close": 312.5, "half_kr": 16_667}
    cp.main(["bought-second", "Broadcom"])
    assert cp.load_state(p)["pending"] == {} and cp.load_state(p)["used"]["Broadcom"] == 1
    cp.main(["reset"])
    assert cp.load_state(p)["used"]["Broadcom"] == 0


def _panel(rows, cash=96_000, used=None, pending=None):
    return "\n".join(cp.format_lines(cp.plan(rows, cash, BASE, TARGET, used, pending), cash, TARGET))


def test_alerts_for_trigger_and_for_second_half():
    calm = _panel([_row("Eli Lilly", -0.01, 200_000)])
    crash = _panel([_row("Eli Lilly", -0.11, 200_000)])
    subject, body = build_actionable_message(extract_fingerprint(calm), extract_fingerprint(crash))
    assert "Crash trigger Eli Lilly" in subject and "BUY 16,667 kr" in body and "--close 100" in body
    pend = {"Eli Lilly": {"date": "2026-11-05", "close": 100.0, "half_kr": 16_667}}
    waiting = _panel([_row("Eli Lilly", 0.01, 210_000, since=20)], used={"Eli Lilly": 1}, pending=pend)
    due = _panel([_row("Eli Lilly", 0.01, 210_000, since=21)], used={"Eli Lilly": 1}, pending=pend)
    subject, body = build_actionable_message(extract_fingerprint(waiting), extract_fingerprint(due))
    assert "second half Eli Lilly" in subject and "BUY 16,667 kr" in body


def test_crash_rows_do_not_leak_into_rebalance_rows():
    fp = extract_fingerprint(_panel([_row("Broadcom", -0.03, 200_000)]))
    assert fp["rebal_rows"] == {} and "Broadcom" in fp["crash_rows"]


def test_crash_rows_survive_avgo_action_mentioning_the_block():
    # Regression (2026-11-06): the AVGO Action line names "the Crash Plan
    # block", which the parser used to match instead of the block header.
    pre = ("    Action         : No rotation. The 5d/-10% trigger has fired -- see the Crash Plan "
           "block below for the amount (MEMORY.md 'Crash plan').\n\n")
    fp = extract_fingerprint(pre + _panel([_row("Broadcom", -0.15, 184_000)]))
    assert fp["crash_rows"]["Broadcom"]["status"] == "FIRED"
    assert "BUY" in fp["crash_rows"]["Broadcom"]["detail"]


def test_live_state_file_is_valid():
    st = cp.load_state()
    assert set(st["used"]) == set(cp.HOLDINGS) and st["pending"] == {}


def test_index_is_exempt_in_sightline():
    from sightline import load_config
    assert "global_index" in load_config()["exemptions"]
