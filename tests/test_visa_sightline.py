import tomllib

import sightline
import sightline_reader as sr
from check_signal_changes import build_actionable_message, extract_fingerprint

RELEASE = (
    "Payments volume for the three months ended June 30, 2026, on which fiscal fourth quarter "
    "service revenue is recognized, increased 10% over the prior year on a constant-dollar basis. "
    "Payments volume for the three months ended September 30, 2026 increased 9% over the prior "
    "year on a constant-dollar basis."
)


def test_parse_visa_takes_the_latest_quarter_and_its_sign():
    assert sr.parse_visa(RELEASE) == ("2026Q3", 9.0)
    down = RELEASE.replace("September 30, 2026 increased 9%", "September 30, 2026 decreased 2%")
    assert sr.parse_visa(down) == ("2026Q3", -2.0)
    assert sr.parse_visa("no volume sentence here") is None


def test_growth_kind_rules():
    r = lambda *v: [{"quarter": f"2026Q{i + 1}", "value": x} for i, x in enumerate(v)]
    assert sightline.derive_state(r(9, 10, 9), kind="growth") == ("HOLD", "2026Q3: +9% YoY")
    assert sightline.derive_state(r(9, -1), kind="growth")[0] == "CUT"
    assert sightline.derive_state(r(9, -1, 2, 3), kind="growth")[0] == "REQUALIFIED"
    # a level entry is unchanged: needs the prior-year pair
    assert sightline.derive_state(r(9, 10), kind="level")[1] == "no YoY pair recorded yet"


def test_write_round_trips_kind(tmp_path):
    p = tmp_path / "s.toml"
    cfg = {"V": {"name": "Visa", "observable": "pv", "unit": "%", "kind": "growth", "eroding": "e",
                 "constructive": "c", "cadence": "q", "action": "CUT",
                 "readings": [{"quarter": "2026Q3", "value": -1.0}]}}
    sightline._write(cfg, p)
    back = sightline.load_config(p)["V"]
    assert back["kind"] == "growth" and sightline.entry_state(back)[0] == "CUT"


def _panel(v_value):
    cfg = sightline.load_config()
    cfg["V"]["readings"] = cfg["V"]["readings"][:-1] + [{"quarter": "2026Q4", "value": v_value}]
    return "\n".join(sightline.format_dashboard_lines(cfg)) + "\n"


def test_visa_cut_alert_quotes_the_action():
    subject, body = build_actionable_message(extract_fingerprint(_panel(8)), extract_fingerprint(_panel(-1)))
    assert "Sightline V CUT" in subject and "CUT: sell the full position" in body
    assert build_actionable_message(extract_fingerprint(_panel(8)), extract_fingerprint(_panel(7))) is None


def test_live_config_has_visa_wired_end_to_end():
    pos = {p["name"]: p for p in tomllib.load(open("config/portfolio.toml", "rb"))["positions"]}
    assert pos["Visa"]["ticker"] == "V" and pos["Visa"]["target_weight"] == 0.05
    assert pos["Broadcom"]["target_weight"] == 0.15
    assert abs(sum(float(p.get("target_weight") or 0) for p in pos.values()) - 1.0) < 1e-9
    import sync_sheet
    assert sync_sheet._lookup("Visa") == "Visa"
    entry = sightline.load_config()["V"]
    assert entry["kind"] == "growth" and sightline.entry_state(entry)[0] == "HOLD"
    assert "V" in sr.PARSERS and "V" in sr.CIKS
