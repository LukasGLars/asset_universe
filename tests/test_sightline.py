from pathlib import Path

import pytest

from sightline import (
    CUT,
    HOLD,
    REQUALIFIED,
    derive_state,
    format_dashboard_lines,
    load_config,
    parse_quarter,
    prior_year_label,
    record_reading,
    yoy_series,
)

FIXTURE = """\
# header comment that must survive a rewrite

[AVGO]
name         = "Broadcom"
observable   = "AI semiconductor revenue"
unit         = "USD bn"
eroding      = "YoY < 0 in any quarter"
constructive = "two consecutive YoY > 0 after a CUT"
cadence      = "earnings"
action       = "CUT: sell the full position"

[[AVGO.readings]]
quarter = "FY25Q3"
value   = 5.2

[[AVGO.readings]]
quarter = "FY26Q3"
value   = 16.7

[exemptions.gold]
reason = "strategic anchor"
"""


def _readings(*pairs):
    return [{"quarter": q, "value": v} for q, v in pairs]


# -- quarter labels -----------------------------------------------------------

def test_parse_fiscal_and_calendar_labels():
    assert parse_quarter("FY26Q3") == ("FY", 26, 3)
    assert parse_quarter("2026q2") == ("", 2026, 2)


def test_parse_rejects_junk():
    with pytest.raises(ValueError):
        parse_quarter("Q3 2026")


def test_prior_year_label_keeps_width_and_prefix():
    assert prior_year_label("FY26Q3") == "FY25Q3"
    assert prior_year_label("2026Q1") == "2025Q1"


# -- YoY math -----------------------------------------------------------------

def test_yoy_is_none_without_prior_year_pair():
    series = yoy_series(_readings(("FY26Q3", 16.7)))
    assert series == [("FY26Q3", 16.7, None)]


def test_yoy_computed_against_same_quarter_prior_year():
    series = yoy_series(_readings(("FY26Q3", 16.7), ("FY25Q3", 5.2), ("FY26Q2", 10.8)))
    assert [q for q, _, _ in series] == ["FY25Q3", "FY26Q2", "FY26Q3"]
    assert series[-1][2] == pytest.approx(16.7 / 5.2 - 1)
    assert series[1][2] is None


# -- state machine ------------------------------------------------------------

def test_hold_with_no_yoy_pair_yet():
    assert derive_state(_readings(("FY26Q3", 16.7))) == (HOLD, "no YoY pair recorded yet")


def test_hold_while_yoy_positive():
    state, detail = derive_state(_readings(("FY25Q3", 5.2), ("FY26Q3", 16.7)))
    assert state == HOLD
    assert detail == "FY26Q3: 16.7 (+221% YoY)"


def test_single_negative_quarter_is_cut():
    state, _ = derive_state(_readings(("FY25Q3", 5.2), ("FY26Q3", 4.0)))
    assert state == CUT


def test_one_positive_quarter_after_cut_is_still_cut():
    state, _ = derive_state(_readings(
        ("FY25Q3", 5.2), ("FY25Q4", 6.5),
        ("FY26Q3", 4.0), ("FY26Q4", 7.0),
    ))
    assert state == CUT


def test_two_consecutive_positive_quarters_after_cut_requalify():
    state, _ = derive_state(_readings(
        ("FY25Q3", 5.2), ("FY25Q4", 6.5), ("FY26Q1", 8.4),
        ("FY26Q3", 4.0), ("FY26Q4", 7.0), ("FY27Q1", 9.0),
    ))
    assert state == REQUALIFIED


def test_negative_quarter_between_positives_resets_streak():
    state, _ = derive_state(_readings(
        ("FY25Q3", 5.2), ("FY25Q4", 6.5), ("FY26Q1", 8.4), ("FY26Q2", 10.8),
        ("FY26Q3", 4.0), ("FY26Q4", 7.0), ("FY27Q1", 8.0), ("FY27Q2", 11.0),
    ))
    assert state == CUT


def test_requalified_drops_back_to_cut_on_new_negative():
    state, _ = derive_state(_readings(
        ("FY25Q3", 5.2), ("FY25Q4", 6.5), ("FY26Q1", 8.4), ("FY26Q2", 10.8),
        ("FY26Q3", 4.0), ("FY26Q4", 7.0), ("FY27Q1", 9.0), ("FY27Q2", 9.0),
    ))
    assert state == CUT


# -- file roundtrip -----------------------------------------------------------

def test_record_appends_and_preserves_header(tmp_path):
    path = tmp_path / "sightline.toml"
    path.write_text(FIXTURE, encoding="utf-8")

    state, detail = record_reading("AVGO", "FY26Q4", 21.7, path)
    assert state == HOLD

    text = path.read_text(encoding="utf-8")
    assert text.startswith("# header comment that must survive a rewrite")
    cfg = load_config(path)
    assert [r["quarter"] for r in cfg["AVGO"]["readings"]] == ["FY25Q3", "FY26Q3", "FY26Q4"]
    assert cfg["AVGO"]["action"] == "CUT: sell the full position"
    assert cfg["exemptions"]["gold"]["reason"] == "strategic anchor"


def test_record_same_quarter_overwrites_not_duplicates(tmp_path):
    path = tmp_path / "sightline.toml"
    path.write_text(FIXTURE, encoding="utf-8")
    record_reading("AVGO", "FY26Q3", 15.0, path)
    cfg = load_config(path)
    assert [r["value"] for r in cfg["AVGO"]["readings"]] == [5.2, 15.0]


def test_record_negative_yoy_reports_cut(tmp_path):
    path = tmp_path / "sightline.toml"
    path.write_text(FIXTURE, encoding="utf-8")
    state, _ = record_reading("AVGO", "FY26Q3", 4.0, path)
    assert state == CUT


def test_record_unknown_ticker_raises(tmp_path):
    path = tmp_path / "sightline.toml"
    path.write_text(FIXTURE, encoding="utf-8")
    with pytest.raises(KeyError):
        record_reading("NVDA", "2026Q2", 1.0, path)
    with pytest.raises(KeyError):
        record_reading("exemptions", "2026Q2", 1.0, path)


def test_record_bad_quarter_does_not_touch_file(tmp_path):
    path = tmp_path / "sightline.toml"
    path.write_text(FIXTURE, encoding="utf-8")
    with pytest.raises(ValueError):
        record_reading("AVGO", "Q3-2026", 1.0, path)
    assert path.read_text(encoding="utf-8") == FIXTURE


# -- dashboard block ----------------------------------------------------------

def test_dashboard_lines_carry_state_and_exemptions(tmp_path):
    path = tmp_path / "sightline.toml"
    path.write_text(FIXTURE, encoding="utf-8")
    lines = format_dashboard_lines(load_config(path))
    assert lines[0].startswith("  Sightline")
    assert "      State      : HOLD" in lines
    assert "      Latest     : FY26Q3: 16.7 (+221% YoY)" in lines
    assert any(l.startswith("    gold: EXEMPT") for l in lines)


def test_live_config_parses_and_both_holdings_hold():
    cfg = load_config()
    for tkr in ("AVGO", "LLY"):
        for field in ("observable", "eroding", "constructive", "cadence", "action"):
            assert cfg[tkr][field]
        state, _ = derive_state(cfg[tkr]["readings"])
        assert state == HOLD
    assert set(cfg["exemptions"]) == {"gold", "crypto_sleeve"}


def test_record_works_on_a_file_with_no_header_comment(tmp_path):
    """Regression: the header-preserving rewrite once treated '[AVGO]' on
    line 1 as part of the header and emitted the table twice."""
    path = tmp_path / "sightline.toml"
    path.write_text(FIXTURE[FIXTURE.index("[AVGO]"):], encoding="utf-8")
    record_reading("AVGO", "FY26Q4", 21.7, path)
    cfg = load_config(path)  # raises on a duplicated table
    assert len(cfg["AVGO"]["readings"]) == 3


# -- forward rule (guided YoY < 0 -> CUT), 2026-11-04 --------------------------

def _guides(*pairs):
    return [{"quarter": q, "value": v} for q, v in pairs]


def test_forward_rule_cuts_on_guided_decline():
    r = _readings(("FY25Q4", 6.5), ("FY26Q3", 16.7), ("FY25Q3", 5.2))
    state, detail = derive_state(r, _guides(("FY26Q4", 6.0)))
    assert state == CUT
    assert "GUIDED" in detail and "FY26Q4" in detail


def test_forward_rule_ignores_slower_but_positive_guide():
    r = _readings(("FY25Q4", 6.5), ("FY26Q3", 16.7), ("FY25Q3", 5.2))
    assert derive_state(r, _guides(("FY26Q4", 7.0)))[0] == HOLD


def test_guide_ignored_once_the_actual_lands():
    r = _readings(("FY25Q4", 6.5), ("FY26Q4", 21.9))
    assert derive_state(r, _guides(("FY26Q4", 6.0)))[0] == HOLD


def test_guide_without_year_ago_actual_is_ignored():
    assert derive_state(_readings(("FY26Q3", 16.7)), _guides(("FY26Q4", 1.0)))[0] == HOLD


def test_guides_round_trip_through_the_file(tmp_path):
    from sightline import load_config, record_guide
    p = tmp_path / "s.toml"
    p.write_text(SAMPLE if "SAMPLE" in globals() else
                 '[AVGO]\nname = "B"\nobservable = "o"\neroding = "e"\naction = "a"\n')
    record_guide("AVGO", "FY26Q4", 21.7, p)
    assert load_config(p)["AVGO"]["guides"] == [{"quarter": "FY26Q4", "value": 21.7}]
