import numpy as np
import pandas as pd

import recession_mode as rm
from check_signal_changes import build_actionable_message, extract_fingerprint

CFG = {"enabled": True, "source": "LF Global Index", "sink": "Reactor Core Cash", "shift": 0.20}
BASE_T = {"Broadcom": .2, "Eli Lilly": .2, "Gold": .2, "LF Global Index": .3, "Reactor Core Cash": .1}


def _daily_from_monthly(levels, start="2024-01-31"):
    """Business-day closes that sit at `levels` on each month end."""
    me = pd.date_range(start, periods=len(levels), freq="ME")
    days = pd.bdate_range(me[0] - pd.offsets.MonthBegin(1), me[-1])
    s = pd.Series(np.nan, index=days)
    for d, v in zip(me, levels):
        s[s.index[s.index <= d][-1]] = v
    return s.ffill().bfill()


def _unrate(values, start="2024-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="MS"), dtype=float)


def test_on_when_trend_below_average_and_unemployment_rising():
    spx = _daily_from_monthly([100] * 14 + [80])                 # last completed month far below 10m avg
    un = _unrate([4.0] * 13 + [4.6, 4.6])                         # rising; the print for month M-1 is what counts
    st = rm.recession_state(spx, un, pd.Timestamp("2025-04-15"))  # last completed month: 2025-03
    assert st["state"] == rm.ON and st["trend_neg"] and st["labour_neg"]
    assert st["as_of"] == pd.Timestamp("2025-03-31")


def test_off_when_only_one_leg_fires():
    spx = _daily_from_monthly([100] * 14 + [80])
    assert rm.recession_state(spx, _unrate([4.0] * 15), pd.Timestamp("2025-04-15"))["state"] == rm.OFF
    spx_up = _daily_from_monthly([100] * 14 + [120])
    un_up = _unrate([4.0] * 13 + [4.6, 4.6])
    assert rm.recession_state(spx_up, un_up, pd.Timestamp("2025-04-15"))["state"] == rm.OFF


def test_current_month_is_never_used():
    # The crash happens in the CURRENT month (April); March closed normal -> OFF.
    spx = _daily_from_monthly([100] * 15)
    spx = pd.concat([spx, pd.Series(50.0, index=pd.bdate_range("2025-04-01", "2025-04-15"))])
    un = _unrate([4.0] * 13 + [4.6, 4.6])
    st = rm.recession_state(spx, un, pd.Timestamp("2025-04-15"))
    assert st["state"] == rm.OFF and st["as_of"] == pd.Timestamp("2025-03-31")


def test_unemployment_uses_previous_months_print():
    # A spike in the print FOR the evaluation month itself must not count yet.
    spx = _daily_from_monthly([100] * 14 + [80])
    un = _unrate([4.0] * 14 + [6.0])                              # 2025-03 print = 6.0, 2025-02 print = 4.0
    assert rm.recession_state(spx, un, pd.Timestamp("2025-04-15"))["labour_neg"] is False


def test_missing_unemployment_month_does_not_break_the_average():
    spx = _daily_from_monthly([100] * 14 + [80])
    vals = [4.0] * 13 + [4.6, 4.6]
    vals[8] = np.nan                                              # e.g. the 2025-10 shutdown gap
    st = rm.recession_state(spx, _unrate(vals), pd.Timestamp("2025-04-15"))
    assert st["state"] == rm.ON


def test_no_data_with_short_history():
    assert rm.recession_state(_daily_from_monthly([100] * 5), _unrate([4.0] * 5),
                              pd.Timestamp("2024-07-15"))["state"] == rm.NO_DATA


def test_targets_shift_only_when_on_and_never_mutate_the_base():
    on = rm.apply_targets(BASE_T, CFG, rm.ON)
    assert round(on["LF Global Index"], 10) == 0.10 and round(on["Reactor Core Cash"], 10) == 0.30
    assert abs(sum(on.values()) - 1.0) < 1e-12
    assert rm.apply_targets(BASE_T, CFG, rm.OFF) == BASE_T
    assert rm.apply_targets(BASE_T, {**CFG, "enabled": False}, rm.ON) == BASE_T
    assert BASE_T["LF Global Index"] == 0.3                        # base untouched -> crash plan sizing safe
    assert rm.apply_targets({"LF Global Index": .05, "Reactor Core Cash": .1}, CFG, rm.ON)["LF Global Index"] == 0.0


def _rs(on):
    return {"state": rm.ON if on else rm.OFF, "as_of": pd.Timestamp("2026-10-31"), "spx": 6900.0,
            "spx_avg": 7300.0, "trend_neg": on, "unrate": 4.6, "unrate_avg": 4.3, "labour_neg": on}


def test_action_amounts_are_computed_from_values():
    lines = "\n".join(rm.format_recession_lines(_rs(True), CFG, 300_000, 100_000, 1_000_000, BASE_T))
    assert "sell ~200,000 kr of LF Global Index (to 10%)" in lines and "cash target 30%" in lines
    lines = "\n".join(rm.format_recession_lines(_rs(False), CFG, 120_000, 300_000, 1_000_000, BASE_T))
    assert "~180,000 kr below its target" in lines


def _panel(on, lf_status="HOLD"):
    rec = "\n".join(rm.format_recession_lines(_rs(on), CFG, 300_000, 100_000, 1_000_000, BASE_T))
    rebal = ("  Rebalance Check  [existing capital, band: 10pp absolute gap to target]\n"
             f"    LF Global Index status: {lf_status}  (30.0% actual vs 10.0% target, gap -20.0%) -- ~200,000 kr\n")
    return "    Note: see the Recession Mode block below\n\n" + rec + "\n\n" + rebal


def test_recession_alert_on_flip_and_band_alert_suppressed():
    subject, body = build_actionable_message(extract_fingerprint(_panel(False)),
                                             extract_fingerprint(_panel(True, lf_status="SELL")))
    assert "Recession mode ON" in subject and "sell ~200,000 kr of LF Global Index" in body
    assert "REBALANCE CHECK" not in body                          # same trade, not a second alert
    subject, body = build_actionable_message(extract_fingerprint(_panel(True)), extract_fingerprint(_panel(False)))
    assert "Recession mode OFF" in subject


def test_recession_silent_without_flip_or_baseline():
    assert build_actionable_message(extract_fingerprint(_panel(True)), extract_fingerprint(_panel(True))) is None
    assert build_actionable_message(extract_fingerprint(""), extract_fingerprint(_panel(True))) is None


def _watch(**states):
    rows = [{"name": n, "state": states.get(n, "OFF"), "detail": f"{n} detail"}
            for n in ("Trend break", "Labour cracking", "Curve inverted", "Volatility stress", "Oil shock")]
    return "\n".join(rm.format_watch_lines(rows)) + "\n"


def test_watch_alerts_on_turning_on_and_clearing_only():
    subject, body = build_actionable_message(extract_fingerprint(_watch()), extract_fingerprint(_watch(**{"Trend break": "ON"})))
    assert "Watch: Trend break" in subject and "No action" in body
    subject, body = build_actionable_message(extract_fingerprint(_watch(**{"Oil shock": "ON"})), extract_fingerprint(_watch()))
    assert "Watch cleared: Oil shock" in subject
    assert build_actionable_message(extract_fingerprint(_watch(**{"Oil shock": "ON"})),
                                    extract_fingerprint(_watch(**{"Oil shock": "ON"}))) is None
    assert build_actionable_message(extract_fingerprint(_watch(**{"Oil shock": "NO_DATA"})),
                                    extract_fingerprint(_watch(**{"Oil shock": "ON"}))) is None


def test_watch_rows_from_series():
    idx = pd.bdate_range("2024-01-01", periods=420)
    spx = pd.Series(np.r_[np.linspace(100, 130, 417), [90, 90, 90]], index=idx)
    weeks = pd.date_range("2025-01-04", periods=60, freq="W-SAT")
    claims = pd.Series(np.r_[[200e3] * 56, [260e3] * 4], index=weeks)
    curve = pd.Series([0.5] * 10, index=idx[-10:])
    vix = pd.Series([15.0] * 10, index=idx[-10:])
    oil = pd.Series(np.r_[[60.0] * 380, [100.0] * 40], index=idx)
    rows = {r["name"]: r for r in rm.watch_rows(spx, None, claims, curve, vix, None, oil)}
    assert rows["Trend break"]["state"] == "ON"
    assert rows["Labour cracking"]["state"] == "ON"               # claims +30% off the low
    assert rows["Curve inverted"]["state"] == "OFF"
    assert rows["Volatility stress"]["state"] == "NO_DATA"        # VIX3M missing degrades on its own row
    assert "unavailable" not in rows["Volatility stress"]["detail"]  # the smoke test greps for it
    assert rows["Oil shock"]["state"] == "ON"


def test_preview_scenarios_deliver():
    from preview_all_triggers import BASE, SCENARIOS
    sc = dict(SCENARIOS)
    for name, expect in (("Recession mode ON", "Recession mode ON"), ("Market watch trend break", "Watch: Trend break")):
        subject, _ = build_actionable_message(extract_fingerprint(BASE), extract_fingerprint(sc[name]))
        assert expect in subject


def test_every_gauge_handles_a_missing_series():
    rows = rm.watch_rows(None, None, None, None, None, None, None)
    assert [r["state"] for r in rows] == ["NO_DATA"] * 5
    assert not any("unavailable" in r["detail"] for r in rows)


def test_preview_imports_without_pandas():
    # The Telegram preview workflow installs no packages: preview_all_triggers
    # (and the recession_mode formatting it uses) must import without pandas.
    import subprocess, sys, textwrap
    code = textwrap.dedent("""
        import sys
        class _Block:
            def find_spec(self, name, path=None, target=None):
                if name == "pandas" or name.startswith("pandas."):
                    raise ModuleNotFoundError("blocked: pandas")
        sys.meta_path.insert(0, _Block())
        import preview_all_triggers
        from check_signal_changes import extract_fingerprint, build_actionable_message
        sc = dict(preview_all_triggers.SCENARIOS)
        r = build_actionable_message(extract_fingerprint(preview_all_triggers.BASE),
                                     extract_fingerprint(sc["Recession mode ON"]))
        assert r and "Recession mode ON" in r[0], r
        print("ok")
    """)
    from pathlib import Path
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=Path(__file__).parent.parent)
    assert out.returncode == 0 and "ok" in out.stdout, out.stderr
