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


def test_half_is_sized_off_the_cash_target_not_the_balance():
    # Operator rule (MEMORY.md "Crash plan", REVISED 2026-11-05): a tranche is
    # one third of the cash TARGET, bought in two halves, so every buy is the
    # same size however much cash is left. The balance only limits the buy
    # when there is not enough of it.
    for cash in (50_000, 96_000, 150_000):
        out = _plan([_row("Broadcom", -0.11, 200_000)], cash=cash)
        assert round(out["Broadcom"]["buy_kr"]) == 16_667, cash
    short = _plan([_row("Broadcom", -0.11, 200_000)], cash=10_000)
    assert round(short["Broadcom"]["buy_kr"]) == 10_000


def test_live_2026_11_06_alert_quotes_half_of_a_third_of_the_target():
    # The real numbers on the first live trigger: target base 956,411 kr,
    # cash target 10% = 95,641 -> tranche 31,880 -> first half 15,940 kr,
    # NOT a third of the 96,090 kr balance (16,015 kr).
    base, cash = 956_411, 96_090
    target = 0.10 * base
    rows = [
        {"name": "Broadcom", "roc": -0.155, "close": 291.53, "value": 184_396, "since": None},
        {"name": "Eli Lilly", "roc": -0.007, "close": 1364.73, "value": 252_323, "since": None},
        {"name": "LF Global Index", "roc": -0.017, "close": 608.0, "value": 241_702, "since": None},
    ]
    calm = [{**r, "roc": -0.01} for r in rows]
    panel = lambda rs: "\n".join(cp.format_lines(cp.plan(rs, cash, base, target), cash, target))
    subject, body = build_actionable_message(extract_fingerprint(panel(calm)), extract_fingerprint(panel(rows)))
    assert "Crash trigger Broadcom" in subject
    assert "BUY 15,940 kr (first half of tranche 1" in body
    assert "--half 15940" in body


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


def test_avgo_crash_day_sends_the_previewed_broadcom_alert():
    # Live shape of 2026-11-06: AVGO trigger flips and the Broadcom row fires
    # on the same run. The message must be the CRASH TRIGGER format, once.
    from preview_all_triggers import BASE, SCENARIOS
    curr = dict(SCENARIOS)["AVGO crash day (live shape)"]
    subject, body = build_actionable_message(extract_fingerprint(BASE), extract_fingerprint(curr))
    assert subject.endswith("Crash trigger Broadcom")
    assert body.count("CRASH TRIGGER -- Broadcom: (5d -11.0%) -- BUY 16,667 kr") == 1
    assert "AVGO GAP-DOWN" not in body
    assert "Crash plan: act once; the band is the backstop after cash runs out." in body


def test_live_state_file_is_valid():
    st = cp.load_state()
    assert set(st["used"]) == set(cp.HOLDINGS)
    assert all(0 <= n <= cp.MAX_PER_HOLDING for n in st["used"].values())
    assert sum(st["used"].values()) <= cp.TRANCHES
    for name, p in st["pending"].items():
        # An open second half belongs to a tranche that was opened.
        assert st["used"][name] >= 1
        assert set(p) == {"date", "close", "half_kr"} and float(p["half_kr"]) > 0


def test_index_is_exempt_in_sightline():
    from sightline import load_config
    assert "global_index" in load_config()["exemptions"]


def test_basket_crash_alert_is_muted_when_the_crash_plan_alerts():
    # Operator, 2026-11-06: no basket-crash sleeve line in a crash-plan alert.
    from preview_all_triggers import BASE, SCENARIOS
    curr = dict(SCENARIOS)["AVGO crash day (live shape)"]
    basket = ("    Basket-crash   : LITE (Lumentum Holdings Inc.)  $509.70  (sector Technology)\n"
              "    Plan           : buy near $509.70, flat 21d exit\n"
              "    Open           : run_entry_screen.py --open LITE <fill_price> <shares> <capital_sek> --entry-type basket_crash\n")
    anchor = "  Opportunistic Sleeve\n    Status         : CLOSED (0/1 position)\n"
    assert anchor in BASE
    prev_fp = extract_fingerprint(BASE)
    prev_fp["sleeve_basket_candidate"] = "none"
    curr_fp = extract_fingerprint(curr.replace(anchor, anchor + basket))
    assert curr_fp["sleeve_basket_candidate"] == "LITE"
    subject, body = build_actionable_message(prev_fp, curr_fp)
    assert "Crash trigger Broadcom" in subject and "basket-crash" not in subject.lower()
    assert "BASKET-CRASH" not in body
    # Without a crash-plan alert the basket line still goes out as before.
    calm_fp = extract_fingerprint(BASE.replace(anchor, anchor + basket))
    subject, body = build_actionable_message(prev_fp, calm_fp)
    assert "Sleeve basket-crash candidate -> LITE" in subject
