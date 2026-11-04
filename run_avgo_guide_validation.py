"""TEMPORARY (2026-11-04). Validate a forward Sightline trigger for AVGO:
CUT if management guides next quarter's AI revenue BELOW the same quarter a
year earlier.

PRE-REGISTERED checks, over every AVGO earnings 8-K (item 2.02) since 2024:
  1. Parser accuracy -- a guide is extracted from every release that has an
     AI-revenue outlook sentence, it is never the release's own actual, and
     the printed sentence matches the number (checked by eye).
  2. Guide reliability -- next quarter's actual >= guide in every case
     (Broadcom's beat history), so a guided decline would likely be real.
  3. No historical false fire -- guided YoY never < 0.
Delete after logging.
"""
from __future__ import annotations
import io, json, re, sys, time
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)
import sightline_reader as sr
from sightline import load_config

GUIDE = re.compile(
    r"(?:expect|guid|forecast|outlook)[^.]{0,160}?"
    r"(?:Q([1-4])\s+)?(?:AI semiconductor revenue|semiconductor revenue from AI|AI revenue)"
    r"[^$.]{0,80}\$\s*([\d.]+)\s*billion", re.I)


def parse_avgo_guide(text: str):
    """(guided quarter label, value, matched snippet) or None. The guided
    quarter is the one after the release's own quarter."""
    # Quarter from the release TITLE, not from the parsed actual: the
    # FY25Q4 release has no parseable actual, and its guide was missed.
    m = re.search(r"\b(First|Second|Third|Fourth) Quarter (?:of )?Fiscal (?:Year )?(\d{4})\b", text, re.I)
    if not m:
        return None
    q, fy = sr._ORDINAL[m.group(1).lower()], int(m.group(2)) % 100
    act = sr.parse_avgo(text)
    actual = act[1] if act else None
    nq, nfy = (q % 4) + 1, fy + (1 if q == 4 else 0)
    for m in GUIDE.finditer(text):
        v = float(m.group(2))
        if m.group(1) and int(m.group(1)) != nq:
            continue
        if actual is not None and abs(v - actual) < 1e-9:
            continue
        return f"FY{nfy:02d}Q{nq}", v, text[max(0, m.start() - 40): m.end() + 10]
    return None


def main():
    cik = sr.CIKS["AVGO"]
    sub = json.loads(sr._get(f"https://data.sec.gov/submissions/CIK{cik}.json"))
    r = sub["filings"]["recent"]
    filings = [(a, d) for f, it, a, d in zip(r["form"], r["items"], r["accessionNumber"], r["filingDate"])
               if f == "8-K" and "2.02" in it and d >= "2024-01-01"]
    actuals = {x["quarter"]: x["value"] for x in load_config()["AVGO"]["readings"]}
    rows = []
    for acc, date in sorted(filings, key=lambda x: x[1]):
        time.sleep(0.2)
        try:
            text = sr.fetch_filing_text(cik, acc)
        except Exception as e:
            print(f"{date} {acc}: fetch failed {e}"); continue
        act = sr.parse_avgo(text)
        g = parse_avgo_guide(text)
        has_outlook = bool(re.search(r"expect[^.]{0,200}AI", text, re.I))
        rows.append((date, act, g, has_outlook))
        print(f"\n{date}  actual {act}  outlook-sentence-present={has_outlook}")
        if g:
            print(f"   guide {g[0]} = {g[1]}   <<{g[2]}>>")
    print("\n=== checks ===")
    missed = [d for d, a, g, h in rows if h and not g]
    print(f"1. outlook present but no guide parsed: {missed or 'none'}")
    beats, fires = [], []
    for d, a, g, h in rows:
        if not g:
            continue
        gq, gv, _ = g
        nxt = actuals.get(gq)
        yago = actuals.get(f"FY{int(gq[2:4]) - 1:02d}Q{gq[-1]}")
        if nxt is not None:
            beats.append((gq, gv, nxt, nxt / gv - 1))
        if yago is not None:
            yoy = gv / yago - 1
            fires.append((gq, gv, yago, yoy))
    print("2. guide vs next actual:")
    for gq, gv, nxt, b in beats:
        print(f"   {gq}: guide {gv} -> actual {nxt}  ({b:+.1%})")
    print(f"   all actual >= guide: {all(b >= 0 for *_, b in beats) if beats else 'n/a'}")
    print("3. guided YoY (rule fires if < 0):")
    for gq, gv, y, yoy in fires:
        print(f"   {gq}: guide {gv} vs year-ago {y}  ({yoy:+.0%}){'  FIRE' if yoy < 0 else ''}")
    print(f"   historical fires: {sum(1 for *_, y in fires if y < 0)}")


if __name__ == "__main__":
    main()
