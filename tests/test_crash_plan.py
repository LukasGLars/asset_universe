import crash_plan as cp
from check_signal_changes import build_actionable_message, extract_fingerprint


def _row(name, roc, value, close=100.0):
    return {"name": name, "roc": roc, "close": close, "value": value}


def test_roc_needs_six_closes():
    assert abs(cp.roc([100] * 5 + [90]) + 0.10) < 1e-12
    assert cp.roc([100] * 5) is None


def test_single_trigger_buys_sixty_percent_of_cash():
    out = {r["name"]: r for r in cp.plan(
        [_row("Broadcom", -0.11, 200_000), _row("Eli Lilly", -0.02, 200_000),
         _row("LF Global Index", -0.01, 250_000)], cash=100_000, base=1_000_000)}
    assert out["Broadcom"]["state"] == cp.FIRED
    assert out["Broadcom"]["buy_kr"] == 60_000
    assert out["Broadcom"]["stage2_price"] == 85.0
    assert out["Eli Lilly"]["state"] == cp.ARMED and out["Eli Lilly"]["buy_kr"] == 0


def test_several_triggers_split_the_sixty_percent():
    out = cp.plan([_row("Broadcom", -0.12, 150_000), _row("Eli Lilly", -0.10, 150_000),
                   _row("LF Global Index", -0.03, 250_000)], cash=100_000, base=1_000_000)
    assert [r["buy_kr"] for r in out[:2]] == [30_000, 30_000]


def test_cap_limits_the_buy():
    # Lilly at 26% of 1M: room to the 28% cap is 20k, though 60k is offered.
    out = cp.plan([_row("Eli Lilly", -0.15, 260_000)], cash=100_000, base=1_000_000)
    assert round(out[0]["buy_kr"]) == 20_000


def test_boundary_is_inclusive_and_missing_data_never_fires():
    out = cp.plan([_row("Broadcom", -0.10, 100), _row("Eli Lilly", None, 100)], cash=10, base=1000)
    assert out[0]["state"] == cp.FIRED and out[1]["state"] == cp.NO_DATA


def _panel(rows, cash=100_000, base=1_000_000):
    return "\n".join(cp.format_lines(cp.plan(rows, cash, base), cash))


def test_alert_fires_once_on_armed_to_fired_and_quotes_the_amount():
    calm = _panel([_row("Broadcom", -0.03, 200_000), _row("Eli Lilly", -0.01, 200_000)])
    crash = _panel([_row("Broadcom", -0.11, 200_000), _row("Eli Lilly", -0.01, 200_000)])
    subject, body = build_actionable_message(extract_fingerprint(calm), extract_fingerprint(crash))
    assert "Crash trigger Broadcom" in subject
    assert "BUY 60,000 kr" in body and "$85.00" in body
    assert build_actionable_message(extract_fingerprint(crash), extract_fingerprint(crash)) is None


def test_crash_rows_do_not_leak_into_rebalance_rows():
    fp = extract_fingerprint(_panel([_row("Broadcom", -0.03, 200_000)]))
    assert fp["rebal_rows"] == {} and "Broadcom" in fp["crash_rows"]


def test_index_is_exempt_in_sightline():
    from sightline import load_config
    assert "global_index" in load_config()["exemptions"]
