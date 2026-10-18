import datetime as dt

import collections_monitor as cm
from check_signal_changes import build_actionable_message, extract_fingerprint

CFG = {"warn_multiple": 1.25, "break_multiple": 1.5, "baseline_quarters": 8, "confirm_quarters": 2}


def _series(values):
    start = dt.date(2020, 1, 31)
    return [(start + dt.timedelta(days=91 * i), v) for i, v in enumerate(values)]


def test_latest_instants_keeps_newest_filing_and_skips_durations():
    facts = [
        {"end": "2026-08-02", "val": 100, "filed": "2026-09-10"},
        {"end": "2026-08-02", "val": 110, "filed": "2026-12-15"},  # restated
        {"start": "2026-05-04", "end": "2026-08-02", "val": 999, "filed": "2026-09-10"},
    ]
    assert cm.latest_instants(facts) == {dt.date(2026, 8, 2): 110.0}


def test_dso_matches_exact_dates_only():
    d1, d2 = dt.date(2026, 5, 3), dt.date(2026, 8, 2)
    ar = {d1: 50.0, d2: 60.0}
    rev = {d2: 91.0, dt.date(2026, 8, 3): 91.0}
    assert cm.dso_series(ar, rev) == [(d2, 60.0)]


def test_insufficient_history():
    assert cm.derive_state(_series([50] * 8), CFG)[0] == cm.INSUFFICIENT


def test_ok_warn_break():
    base = [50] * 8
    assert cm.derive_state(_series(base + [55]), CFG)[0] == cm.OK
    assert cm.derive_state(_series(base + [65]), CFG)[0] == cm.WARN       # 1.30x
    # One quarter above 1.5x is only a WARN -- the acquisition false positive.
    assert cm.derive_state(_series(base + [50, 80]), CFG)[0] == cm.WARN
    assert cm.derive_state(_series(base + [80, 80]), CFG)[0] == cm.BREAK


def test_break_is_not_sticky():
    assert cm.derive_state(_series([50] * 8 + [80, 80, 50]), CFG)[0] == cm.OK


def test_boundary_is_strict():
    assert cm.derive_state(_series([50] * 8 + [62.5]), CFG)[0] == cm.OK  # exactly 1.25x


def _panel(state, action="CUT: sell the full position"):
    lines = cm.format_dashboard_lines(
        {"AVGO": (state, "2026-08-02: 80 days (1.60x 8Q median 50)")},
        {"AVGO": CFG}, {"AVGO": {"action": action}})
    return "\n".join(lines)


def test_panel_is_parseable_and_safe_for_sync_health():
    text = _panel("BREAK")
    fp = extract_fingerprint(text)
    assert fp["collections_avgo_state"] == "BREAK"
    assert fp["collections_avgo_action"] == "CUT: sell the full position"
    assert "[unavailable" not in text and "Error" not in text


def test_fetch_failure_text_is_safe_for_sync_health(monkeypatch):
    def boom(_):
        raise ConnectionError("x")
    monkeypatch.setattr(cm, "fetch_series", boom)
    states = cm.live_states({"AVGO": CFG})
    assert states["AVGO"][0] == "fetch_failed"
    assert "Error" not in "\n".join(cm.format_dashboard_lines(states, {"AVGO": CFG}, {}))


def _alert(prev_state, curr_state):
    prev = extract_fingerprint(_panel(prev_state))
    curr = extract_fingerprint(_panel(curr_state))
    return build_actionable_message(prev, curr)


def test_break_alert_quotes_action():
    subject, body = _alert("OK", "BREAK")
    assert "Collections AVGO BREAK" in subject
    assert "ACTION: CUT: sell the full position" in body


def test_fetch_failed_never_alerts():
    assert _alert("OK", "fetch_failed") is None
    assert _alert("fetch_failed", "BREAK") is None
