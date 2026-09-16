from unittest.mock import patch

import sightline_reader as sr
from sightline import load_config

# Verbatim phrasing from the real EDGAR exhibits, stripped the way
# fetch_filing_text does it. One fixture per distinct phrasing seen.

AVGO_Q3_FY26 = (
    "Broadcom Inc. Announces Third Quarter Fiscal Year 2026 Financial Results and Quarterly Dividend "
    "... Q3 AI semiconductor revenue of $16.7 billion grew 221% year-over-year, and 54% quarter-over-quarter, "
    "said Hock Tan ... we expect AI semiconductor revenue of approximately $21.7 billion in Q4 ..."
)
AVGO_Q2_FY26 = (
    "Broadcom Inc. Announces Second Quarter Fiscal Year 2026 Financial Results ... "
    "Q2 semiconductor revenue from AI of $10.8 billion grew 143% year-over-year, above our forecast ... "
    "The momentum continues and in Q3 we expect semiconductor revenue from AI to grow over 200 percent "
    "year-over-year to $16.0 billion"
)
AVGO_Q1_FY26 = (
    "Broadcom Inc. Announces First Quarter Fiscal Year 2026 Financial Results ... "
    "Q1 AI revenue of $8.4 billion grew 106% year-over-year, above our forecast ... "
    "we expect AI semiconductor revenue to be $10.7 billion in Q2"
)
AVGO_Q3_FY25 = (
    "Broadcom Inc. Announces Third Quarter Fiscal Year 2025 Financial Results ... "
    "Q3 AI revenue growth accelerated to 63% year-over-year to $5.2 billion, said Hock Tan ... "
    "We expect growth in AI semiconductor revenue to accelerate to $6.2 billion in Q4"
)
# Q4 FY25: the release only carried the guide, no actual -- must be None.
AVGO_Q4_FY25 = (
    "Broadcom Inc. Announces Fourth Quarter and Fiscal Year 2025 Financial Results ... "
    "We see the momentum continuing in Q1 and expect AI semiconductor revenue to double "
    "year-over-year to $8.2 billion, driven by custom AI accelerators"
)

LLY_Q2_26 = (
    "Mounjaro For Q2 2026, worldwide Mounjaro revenue increased 91% to $9.9 billion. U.S. revenue was "
    "$4.8 billion, an increase of 45% ... Zepbound For Q2 2026, U.S. Zepbound revenue increased 44% "
    "to $4.9 billion, primarily driven by strong demand"
)
LLY_ERODING = (
    "Mounjaro For Q3 2027, worldwide Mounjaro revenue decreased 8% to $9.1 billion. ... "
    "Zepbound For Q3 2027, U.S. Zepbound revenue declined 12% to $4.3 billion"
)


# -- parsers ------------------------------------------------------------------

def test_parse_avgo_all_seen_phrasings():
    assert sr.parse_avgo(AVGO_Q3_FY26) == ("FY26Q3", 16.7)
    assert sr.parse_avgo(AVGO_Q2_FY26) == ("FY26Q2", 10.8)
    assert sr.parse_avgo(AVGO_Q1_FY26) == ("FY26Q1", 8.4)
    assert sr.parse_avgo(AVGO_Q3_FY25) == ("FY25Q3", 5.2)


def test_parse_avgo_never_takes_the_guide():
    """Q4 FY25 release had no actual, only 'expect ... $8.2 billion'."""
    assert sr.parse_avgo(AVGO_Q4_FY25) is None


def test_parse_avgo_without_title_is_none():
    assert sr.parse_avgo("Q3 AI semiconductor revenue of $16.7 billion grew") is None


def test_parse_lly_sums_both_products():
    assert sr.parse_lly(LLY_Q2_26) == ("2026Q2", 14.8)


def test_parse_lly_still_parses_when_revenue_falls():
    assert sr.parse_lly(LLY_ERODING) == ("2027Q3", 13.4)


def test_parse_lly_needs_both_products():
    assert sr.parse_lly("For Q2 2026, worldwide Mounjaro revenue increased 91% to $9.9 billion.") is None


def test_strip_html_collapses_tags_and_entities():
    assert sr.strip_html("<p>Q3&nbsp;AI <b>revenue</b> of&#160;$1.0 billion</p>") == " Q3 AI revenue of $1.0 billion "


# -- orchestration (network mocked) -------------------------------------------

FIXTURE = """\
[AVGO]
name         = "Broadcom"
observable   = "AI semiconductor revenue"
unit         = "USD bn"
eroding      = "YoY < 0"
constructive = "2q"
cadence      = "earnings"
action       = "CUT: sell the full position"

[[AVGO.readings]]
quarter = "FY25Q3"
value   = 5.2

[[AVGO.readings]]
quarter = "FY25Q4"
value   = 6.5
"""

NEW_8K = ("0001730168-26-000099", "2026-12-09")


def _cfg(tmp_path, body=FIXTURE):
    p = tmp_path / "sightline.toml"
    p.write_text(body, encoding="utf-8")
    return p


def test_auto_read_records_new_quarter_and_persists_accession(tmp_path):
    path = _cfg(tmp_path)
    text = AVGO_Q3_FY26.replace("Third Quarter Fiscal Year 2026", "Fourth Quarter Fiscal Year 2026") \
                       .replace("Q3 AI semiconductor revenue of $16.7", "Q4 AI semiconductor revenue of $21.7")
    with patch.object(sr, "find_latest_earnings_8k", return_value=NEW_8K), \
         patch.object(sr, "fetch_filing_text", return_value=text):
        r = sr.auto_read("AVGO", path)
    assert r["status"] == sr.RECORDED
    assert (r["label"], r["value"], r["state"]) == ("FY26Q4", 21.7, "HOLD")
    cfg = load_config(path)
    assert cfg["AVGO"]["auto_last_accession"] == NEW_8K[0]
    assert cfg["AVGO"]["auto_last_status"] == "recorded FY26Q4 (8-K 2026-12-09)"
    assert [x["quarter"] for x in cfg["AVGO"]["readings"]] == ["FY25Q3", "FY25Q4", "FY26Q4"]


def test_auto_read_eroding_quarter_reports_cut(tmp_path):
    path = _cfg(tmp_path)
    text = ("Fourth Quarter Fiscal Year 2026 ... Q4 AI semiconductor revenue of $4.0 billion fell")
    with patch.object(sr, "find_latest_earnings_8k", return_value=NEW_8K), \
         patch.object(sr, "fetch_filing_text", return_value=text):
        r = sr.auto_read("AVGO", path)
    assert r["status"] == sr.RECORDED and r["state"] == "CUT"


def test_auto_read_same_filing_is_no_new_filing_and_no_fetch(tmp_path):
    path = _cfg(tmp_path, FIXTURE + '\n[AVGO]\n' if False else FIXTURE)
    with patch.object(sr, "find_latest_earnings_8k", return_value=NEW_8K), \
         patch.object(sr, "fetch_filing_text", return_value=AVGO_Q3_FY26):
        sr.auto_read("AVGO", path)
        with patch.object(sr, "fetch_filing_text", side_effect=AssertionError("must not fetch")):
            r = sr.auto_read("AVGO", path)
    assert r["status"] == sr.NO_NEW_FILING
    assert sr.format_auto_line(r) == "recorded FY26Q3 (8-K 2026-12-09)"


def test_auto_read_parse_failure_marks_filing_seen(tmp_path):
    path = _cfg(tmp_path)
    with patch.object(sr, "find_latest_earnings_8k", return_value=NEW_8K), \
         patch.object(sr, "fetch_filing_text", return_value=AVGO_Q4_FY25):
        r = sr.auto_read("AVGO", path)
    assert r["status"] == sr.PARSE_FAILED
    assert sr.format_auto_line(r) == "parse_failed 8-K 2026-12-09 -- record manually"
    assert load_config(path)["AVGO"]["auto_last_accession"] == NEW_8K[0]
    assert len(load_config(path)["AVGO"]["readings"]) == 2  # nothing recorded


def test_auto_read_already_recorded_does_not_overwrite_manual_value(tmp_path):
    path = _cfg(tmp_path)
    text = "Third Quarter Fiscal Year 2025 ... Q3 AI revenue growth accelerated to 63% year-over-year to $5.9 billion"
    with patch.object(sr, "find_latest_earnings_8k", return_value=NEW_8K), \
         patch.object(sr, "fetch_filing_text", return_value=text):
        r = sr.auto_read("AVGO", path)
    assert r["status"] == sr.ALREADY_RECORDED
    assert [x["value"] for x in load_config(path)["AVGO"]["readings"]] == [5.2, 6.5]


def test_auto_read_network_failure_leaves_state_untouched(tmp_path):
    path = _cfg(tmp_path)
    with patch.object(sr, "find_latest_earnings_8k", side_effect=OSError("timeout")):
        r = sr.auto_read("AVGO", path)
    assert r["status"] == sr.FETCH_FAILED
    assert "auto_last_accession" not in load_config(path)["AVGO"]
    assert sr.format_auto_line(r).startswith("fetch_failed")
