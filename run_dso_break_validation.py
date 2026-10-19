"""TEMPORARY (2026-10-19). Does the collections BREAK rule predict anything?

The AVGO DSO monitor (collections_monitor.py) has never fired on AVGO, so its
BREAK has zero evidence behind it. This applies the SAME rule, unchanged, to
every name in the US equity universe and asks whether a BREAK precedes
underperformance.

PRE-REGISTERED, before the run:
  Rule        : collections_monitor.derive_state with config/collections.toml's
                AVGO parameters, verbatim.
  Point in time: each quarter's AR is the ORIGINALLY filed value (earliest
                `filed`), and the event date is that filing date -- the day
                the market could first know. Revenue uses the reconstructed
                series (restatements of revenue are rare; noted, not fixed).
  Events      : BREAK ONSET (state BREAK at quarter t, not BREAK at t-1), so
                one episode counts once. WARN onset reported as secondary.
  Control     : every company-quarter whose state is OK.
  Outcome     : forward 126d and 252d return from the first close after the
                event date, minus the equal-weighted universe forward return
                over the same window (market-relative excess).
  Sub-periods : event year 2010-2015, 2016-2020, 2021-now.
  Verdict     : PREDICTIVE only if, at 252d, BREAK-onset median excess is
                >= 5pp below the control median, AND below it in every
                sub-period with n >= 5, AND Mann-Whitney one-sided p < 0.05.
                Otherwise NOT SHOWN -> the monitor stays informational only.

Known biases, stated: the universe is CURRENT constituents (survivorship),
which drops the worst outcomes and biases AGAINST finding an effect. No
sector control (no sector data in the store); excess is vs the whole
universe. Banks/insurers mostly lack the AR concept and drop out naturally.

Delete after logging.
"""
from __future__ import annotations
import io, sys, time
from pathlib import Path
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", write_through=True)
sys.path.insert(0, str(Path(__file__).parent / "src"))
import datetime as dt
import numpy as np, pandas as pd
from scipy.stats import mannwhitneyu

import collections_monitor as cm
import sec_edgar
from asset_universe import config
from asset_universe.store import reader

HORIZONS = (126, 252)
PERIODS = {"2010-15": (2010, 2015), "2016-20": (2016, 2020), "2021-now": (2021, 2100)}
UNIVERSE = Path(__file__).parent / "config" / "universes" / "us_equities.txt"


def first_filed_instants(facts: list[dict]) -> dict[dt.date, tuple[float, dt.date]]:
    """{period_end: (value, filed)} using the ORIGINAL filing per balance-sheet
    date -- the point-in-time value, not a later restatement."""
    best: dict[str, dict] = {}
    for e in facts:
        if "start" in e:
            continue
        if e["end"] not in best or e["filed"] < best[e["end"]]["filed"]:
            best[e["end"]] = e
    return {dt.date.fromisoformat(k): (float(v["val"]), dt.date.fromisoformat(v["filed"]))
            for k, v in best.items()}


def company_events(ar: dict, rev: dict, cfg: dict) -> list[tuple[dt.date, str]]:
    """[(event_date, state)] for every quarter with enough history, the state
    computed only from quarters up to and including that one."""
    series = cm.dso_series({d: v for d, (v, _) in ar.items()}, rev)
    out = []
    for i in range(len(series)):
        st, _ = cm.derive_state(series[: i + 1], cfg)
        if st == cm.INSUFFICIENT:
            continue
        out.append((ar[series[i][0]][1], st))
    return out


def load_closes(tickers: list[str]) -> pd.DataFrame:
    d = config.raw_data_dir()
    cols = {}
    for t in tickers:
        p = reader.ticker_path(d, "equities", t)
        if p.exists():
            cols[t] = reader.load(p)["close"]
    return pd.DataFrame(cols).sort_index().loc["2009-01-01":]


def fwd_excess(px: pd.DataFrame, t: str, date: dt.date, h: int) -> float | None:
    idx = px.index.searchsorted(pd.Timestamp(date), side="right")
    if idx + h >= len(px.index):
        return None
    a, b = px.iloc[idx], px.iloc[idx + h]
    if pd.isna(a[t]) or pd.isna(b[t]):
        return None
    r = b / a - 1
    return float(r[t] - r.drop(t).mean())


def main() -> None:
    cfg = cm.load_config()["AVGO"]
    tickers = [l.strip() for l in UNIVERSE.read_text().splitlines()
               if l.strip() and not l.startswith("#")]
    px = load_closes(tickers)
    cik = sec_edgar.fetch_ticker_cik_map()

    rows, skipped = [], 0
    for n, t in enumerate(tickers):
        c = cik.get(t) or cik.get(t.replace("-", "."))
        if t not in px.columns or c is None:
            skipped += 1
            continue
        try:
            ar = first_filed_instants(sec_edgar._fetch_company_concept(c, cm.AR_CONCEPT, "USD"))
            time.sleep(0.12)
            rev = sec_edgar.reconstruct_quarterly_facts(sec_edgar.fetch_revenue_facts(c))
            time.sleep(0.12)
        except Exception:
            skipped += 1
            continue
        prev = None
        for date, st in company_events(ar, rev, cfg):
            # OK quarters are the control; BREAK/WARN count only at onset so
            # one episode is one event.
            kind = "OK" if st == cm.OK else (st if st != prev else None)
            prev = st
            if kind is None:
                continue
            rec = {"ticker": t, "date": date, "kind": kind}
            for h in HORIZONS:
                rec[h] = fwd_excess(px, t, date, h)
            rows.append(rec)
        if n % 50 == 0:
            print(f"  ...{n}/{len(tickers)}", flush=True)

    df = pd.DataFrame(rows)
    print(f"\nTickers used: {df['ticker'].nunique()} (skipped {skipped})")
    print(f"Company-quarters: OK {int((df.kind == 'OK').sum())}, "
          f"WARN onsets {int((df.kind == 'WARN').sum())}, BREAK onsets {int((df.kind == 'BREAK').sum())}")

    ok = df[df.kind == "OK"]
    for kind in ("BREAK", "WARN"):
        ev = df[df.kind == kind]
        print(f"\n{kind} onset vs OK control -- median market-relative excess")
        for h in HORIZONS:
            e, c = ev[h].dropna(), ok[h].dropna()
            p = mannwhitneyu(e, c, alternative="less").pvalue if len(e) >= 5 else float("nan")
            print(f"  {h}d: n={len(e):4d}  event {e.median():+7.1%}  control {c.median():+7.1%}  "
                  f"diff {e.median() - c.median():+7.1%}  hit(<0) {(e < 0).mean():5.0%}  p={p:.3f}")
        for name, (y0, y1) in PERIODS.items():
            m = lambda d: (pd.to_datetime(d.date).dt.year >= y0) & (pd.to_datetime(d.date).dt.year <= y1)
            e, c = ev[m(ev)][252].dropna(), ok[m(ok)][252].dropna()
            print(f"    {name}  252d: n={len(e):3d}  event {e.median() if len(e) else float('nan'):+7.1%}  "
                  f"control {c.median():+7.1%}")

    ev, c = df[df.kind == "BREAK"][252].dropna(), ok[252].dropna()
    diff = ev.median() - c.median() if len(ev) else float("nan")
    p = mannwhitneyu(ev, c, alternative="less").pvalue if len(ev) >= 5 else 1.0
    sub_ok = True
    for y0, y1 in PERIODS.values():
        sel = lambda d: (pd.to_datetime(d.date).dt.year >= y0) & (pd.to_datetime(d.date).dt.year <= y1)
        e = df[(df.kind == "BREAK")][sel(df[df.kind == "BREAK"])][252].dropna()
        cc = ok[sel(ok)][252].dropna()
        if len(e) >= 5 and not e.median() < cc.median():
            sub_ok = False
    verdict = "PREDICTIVE" if (diff <= -0.05 and sub_ok and p < 0.05) else "NOT SHOWN"
    print(f"\nVerdict (pre-registered): {verdict}  "
          f"[252d diff {diff:+.1%}, every sub-period below: {sub_ok}, p={p:.3f}]")


if __name__ == "__main__":
    main()
