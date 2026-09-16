"""sightline_reader.py

Reads each Sightline observable straight out of the earnings press
release on EDGAR, so the quarterly reading no longer has to be typed in.
Neither figure is available as structured data (XBRL has no "AI
semiconductor revenue" or per-product line -- confirmed 2026-07-06 and
again 2026-09-16), but both companies state them in fixed-enough prose
in the 8-K item 2.02 exhibit, checked against the last 5 AVGO and 3 LLY
releases before this was written.

The parsers are pure functions over the stripped exhibit text and are
deliberately narrow: each anchors on the reported quarter so a guidance
sentence ("we expect AI semiconductor revenue to be $10.7 billion in
Q2") can never be taken for the actual. When the phrasing drifts the
result is a PARSE_FAILED status and a "record manually" alert, never a
wrong number -- the manual path (record_sightline.py) is the fallback,
not a competitor.

Fetch state (`auto_last_accession`, `auto_last_status`) lives in
config/sightline.toml next to the readings so the daily run makes one
cheap submissions call per ticker and only pulls documents when a new
earnings 8-K has appeared.
"""
from __future__ import annotations

import html
import json
import re
import urllib.request
from pathlib import Path

from sec_edgar import USER_AGENT
from sightline import CONFIG_PATH, load_config, record_reading, save_auto_state

CIKS = {"AVGO": "0001730168", "LLY": "0000059478"}

NO_NEW_FILING, RECORDED, ALREADY_RECORDED, PARSE_FAILED, FETCH_FAILED = (
    "no_new_filing", "recorded", "already_recorded", "parse_failed", "fetch_failed")

_ORDINAL = {"first": 1, "second": 2, "third": 3, "fourth": 4}


# ── network ───────────────────────────────────────────────────────────────────

def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def find_latest_earnings_8k(cik: str) -> tuple[str, str] | None:
    """(accession, filing date) of the most recent 8-K carrying item 2.02
    (Results of Operations) -- that item, not the exhibit name, is what
    identifies an earnings release: LLY's exhibit is named
    q226lillysalesandearningsp.htm, not ex99."""
    sub = json.loads(_get(f"https://data.sec.gov/submissions/CIK{cik}.json"))
    r = sub["filings"]["recent"]
    for form, items, acc, date in zip(r["form"], r["items"], r["accessionNumber"], r["filingDate"]):
        if form == "8-K" and "2.02" in items:
            return acc, date
    return None


def fetch_filing_text(cik: str, accession: str) -> str:
    """Every .htm in the filing (minus the XBRL viewer's R*.htm pages),
    stripped to plain text and concatenated. Small enough (<300KB) that
    scanning all of them beats guessing which one is the release."""
    accn = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn}"
    idx = json.loads(_get(f"{base}/index.json"))
    parts = []
    for item in idx["directory"]["item"]:
        name = item["name"]
        if name.endswith(".htm") and not re.match(r"R\d+\.htm$|.*-index", name):
            parts.append(strip_html(_get(f"{base}/{name}").decode("utf-8", "replace")))
    return "\n".join(parts)


def strip_html(h: str) -> str:
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", h, flags=re.S | re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(h))


# ── parsers (pure) ────────────────────────────────────────────────────────────

def parse_avgo(text: str) -> tuple[str, float] | None:
    """('FY26Q3', 16.7) from the Broadcom release, or None.

    Quarter comes from the title ("Third Quarter Fiscal Year 2026"). The
    figure must sit in a sentence that STARTS with that same quarter
    ("Q3 AI semiconductor revenue of $16.7 billion ..."), which is how
    every actual has been phrased and how no guide ever has. Phrasing of
    the noun has varied across releases -- all three seen forms accepted.
    """
    m = re.search(r"\b(First|Second|Third|Fourth) Quarter (?:of )?Fiscal (?:Year )?(\d{4})\b", text, re.I)
    if not m:
        return None
    q, fy = _ORDINAL[m.group(1).lower()], int(m.group(2))
    pat = (rf"\bQ{q}\s+(?:AI semiconductor revenue|semiconductor revenue from AI|AI revenue)"
           rf"[^$.]{{0,80}}\$\s*([\d.]+)\s*billion")
    v = re.search(pat, text)
    if not v:
        return None
    return f"FY{fy % 100:02d}Q{q}", float(v.group(1))


def parse_lly(text: str) -> tuple[str, float] | None:
    """('2026Q2', 14.8) = Mounjaro + Zepbound from the Lilly release, or
    None. Both products are quoted as "<product> revenue increased 91% to
    $9.9 billion"; the verb is left open (decreased/declined/was) because
    the eroding case is exactly the one this must still parse."""
    q = re.search(r"\bFor Q([1-4]) (\d{4}),\s*worldwide Mounjaro revenue", text)
    if not q:
        return None
    verb = r"(?:increased|decreased|grew|declined|rose|fell|was|of)"
    mj = re.search(rf"worldwide Mounjaro revenue {verb}[^$.]{{0,40}}\$\s*([\d.]+)\s*(billion|million)", text)
    zp = re.search(rf"Zepbound revenue {verb}[^$.]{{0,40}}\$\s*([\d.]+)\s*(billion|million)", text)
    if not (mj and zp):
        return None
    total = sum(float(x.group(1)) / (1000 if x.group(2) == "million" else 1) for x in (mj, zp))
    return f"{q.group(2)}Q{q.group(1)}", round(total, 1)


PARSERS = {"AVGO": parse_avgo, "LLY": parse_lly}


# ── orchestration ─────────────────────────────────────────────────────────────

def auto_read(ticker: str, path: Path = CONFIG_PATH) -> dict:
    """One daily step for one ticker. Returns a status dict; persists the
    accession + status to the config so the dashboard line stays constant
    between filings (the notifier fires on change, not on repetition).

    A PARSE_FAILED filing is still marked as seen -- retrying the same
    regex on the same text every day would only refire the alert.
    """
    cfg = load_config(path)
    entry = cfg[ticker]
    try:
        latest = find_latest_earnings_8k(CIKS[ticker])
    except Exception as e:  # network -- leave state untouched, retry tomorrow
        return {"status": FETCH_FAILED, "detail": str(e)[:80]}
    if latest is None:
        return {"status": FETCH_FAILED, "detail": "no item-2.02 8-K in recent filings"}
    accession, date = latest
    if accession == entry.get("auto_last_accession"):
        return {"status": NO_NEW_FILING, "accession": accession, "date": date,
                "last": entry.get("auto_last_status", "")}
    try:
        text = fetch_filing_text(CIKS[ticker], accession)
    except Exception as e:
        return {"status": FETCH_FAILED, "detail": str(e)[:80]}

    parsed = PARSERS[ticker](text)
    if parsed is None:
        line = f"parse_failed 8-K {date} -- record manually"
        save_auto_state(ticker, accession, line, path)
        return {"status": PARSE_FAILED, "accession": accession, "date": date, "line": line}
    label, value = parsed
    known = {r["quarter"].upper() for r in entry.get("readings", [])}
    if label in known:
        line = f"already_recorded {label} (8-K {date})"
        save_auto_state(ticker, accession, line, path)
        return {"status": ALREADY_RECORDED, "label": label, "value": value,
                "accession": accession, "date": date, "line": line}
    state, detail = record_reading(ticker, label, value, path)
    line = f"recorded {label} (8-K {date})"
    save_auto_state(ticker, accession, line, path)
    return {"status": RECORDED, "label": label, "value": value, "state": state,
            "detail": detail, "accession": accession, "date": date, "line": line}


def format_auto_line(result: dict) -> str:
    """The dashboard's 'Auto-read :' line -- the whole line is a
    fingerprint field, so it must be identical day-to-day for an unchanged
    filing and differ between filings (hence the 8-K date in every
    persisted form). fetch_failed is transient and never persisted."""
    if result["status"] == NO_NEW_FILING:
        return result["last"] or f"seen (8-K {result['date']})"
    if result["status"] == FETCH_FAILED:
        return f"fetch_failed -- {result.get('detail', '')}"
    return result["line"]
