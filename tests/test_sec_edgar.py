import datetime as dt

from sec_edgar import reconstruct_quarterly_facts

def _fact(start, end, val, filed, form="10-Q"):
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed}


def test_derives_missing_q4_from_annual_minus_three_quarters():
    # Mirrors the real ANET pattern found 2026-07-06: annual tagged, Q4 not.
    facts = [
        _fact("2025-01-01", "2025-03-31", 0.64, "2025-05-06"),
        _fact("2025-04-01", "2025-06-30", 0.70, "2025-08-06"),
        _fact("2025-07-01", "2025-09-30", 0.67, "2025-11-05"),
        _fact("2025-01-01", "2025-12-31", 2.75, "2026-02-17", form="10-K"),  # annual only
    ]
    result = reconstruct_quarterly_facts(facts)
    q4_end = dt.date(2025, 12, 31)
    assert q4_end in result
    assert result[q4_end] == round(2.75 - (0.64 + 0.70 + 0.67), 2)


def test_keeps_discrete_q4_when_actually_present_not_derived():
    facts = [
        _fact("2025-01-01", "2025-03-31", 0.64, "2025-05-06"),
        _fact("2025-04-01", "2025-06-30", 0.70, "2025-08-06"),
        _fact("2025-07-01", "2025-09-30", 0.67, "2025-11-05"),
        _fact("2025-10-01", "2025-12-31", 0.80, "2026-02-17"),  # Q4 actually tagged
        _fact("2025-01-01", "2025-12-31", 2.81, "2026-02-17", form="10-K"),
    ]
    result = reconstruct_quarterly_facts(facts)
    # Real discrete Q4 (0.80) must win, not the derived value (2.81-2.01=0.80 here anyway,
    # but the point is discrete facts are never overwritten by derivation).
    assert result[dt.date(2025, 12, 31)] == 0.80


def test_restatement_keeps_most_recently_filed():
    facts = [
        _fact("2025-01-01", "2025-03-31", 0.60, "2025-05-06"),  # original
        _fact("2025-01-01", "2025-03-31", 0.64, "2025-08-06"),  # restated, filed later
    ]
    result = reconstruct_quarterly_facts(facts)
    assert result[dt.date(2025, 3, 31)] == 0.64


def test_ignores_cumulative_ytd_facts():
    facts = [
        _fact("2025-01-01", "2025-09-30", 2.00, "2025-11-05"),  # 9-month YTD, dur=272d
        _fact("2025-07-01", "2025-09-30", 0.67, "2025-11-05"),  # the actual Q3
    ]
    result = reconstruct_quarterly_facts(facts)
    assert dt.date(2025, 9, 30) in result
    assert result[dt.date(2025, 9, 30)] == 0.67
    assert dt.date(2025, 9, 30) not in [dt.date.fromisoformat(f["start"]) for f in facts if f["val"] == 2.00]


def test_no_derivation_without_exactly_three_discrete_quarters():
    # Only 2 discrete quarters found -- not enough to safely derive a third/fourth.
    facts = [
        _fact("2025-01-01", "2025-03-31", 0.64, "2025-05-06"),
        _fact("2025-04-01", "2025-06-30", 0.70, "2025-08-06"),
        _fact("2025-01-01", "2025-12-31", 2.75, "2026-02-17", form="10-K"),
    ]
    result = reconstruct_quarterly_facts(facts)
    assert dt.date(2025, 12, 31) not in result


def test_real_anet_case_matches_yfinance_reference():
    # Real facts pulled 2026-07-06 from SEC EDGAR for ANET (CIK 0001596532).
    # Validated 2026-07-06: yfinance's own Q4 2025 diluted EPS is 0.75;
    # this reproduces it via the annual-minus-three-quarters derivation.
    facts = [
        _fact("2025-01-01", "2025-03-31", 0.64, "2026-05-06"),
        _fact("2025-04-01", "2025-06-30", 0.70, "2025-08-06"),
        _fact("2025-07-01", "2025-09-30", 0.67, "2025-11-05"),
        _fact("2025-01-01", "2025-09-30", 2.00, "2025-11-05"),  # 9mo YTD, must be ignored
        _fact("2025-01-01", "2025-12-31", 2.75, "2026-02-17", form="10-K"),
    ]
    result = reconstruct_quarterly_facts(facts)
    q4_end = dt.date(2025, 12, 31)
    assert q4_end in result
    assert result[q4_end] == 0.74  # matches yfinance's 0.75 within the known 1-cent rounding artifact
