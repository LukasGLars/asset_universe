"""
run_basket_crash_subperiod_control.py

TEMPORARY DIAGNOSTIC (2026-09-17). The one test basket_crash never got.

Background. The opportunistic sleeve was retired 2026-09-04 because its four
extension gates were never better than random entry: ungated control (all 504
names, every date) +1.07% median / 57.8% win at 21d, against gates that bought
+0.2 to +0.5pp of median and a LOWER win rate. But **none of the 13 closed live
trades behind that verdict were basket_crash** -- 20 of 21 live recommendations
were extension, and the single basket_crash one (WDC, 2026-08-25) was still open
at the cutoff. The retirement evidence is silent on this entry type.

What the reconstruction claimed (2026-07-29, n=299 basket / 953 solo):
  21d  basket +4.41% / 66.6% win   vs  solo +1.13% / 54.7%
  90d  basket +10.22% / 72.2% win  vs  solo +5.51% / 59.8%
solo_crash is statistically indistinguishable from the ungated baseline, so on
its face the whole effect sits in ">=2 same-sector peers also crashing".

Why that is not yet believable. CLAUDE.md: "Sub-period any full-sample statistic
before believing it. SAAB screened at 0.11 beta ... by sub-period 0.23 / 0.27 /
-0.02, entirely post-Ukraine. One regime can carry a whole number." Sector-wide
capitulations CLUSTER -- 2009, 2011, 2015-16, 2018Q4, 2020-03, 2022 -- and
2009-2026 is one long bull with V-shaped recoveries. If the entries pile into
2009 and 2020, "basket crashes mean-revert" is really "dip-buying worked in the
recovery era".

This run adds the two things the original lacked:

1. SUB-PERIOD SPLIT. basket vs solo per era, plus the entry-count distribution
   so clustering is visible rather than assumed.

2. A DATE-MATCHED MARKET CONTROL, which matters more than the sub-period split
   and has never been run at all. basket_crash fires in market-wide selloffs, so
   its forward return is contaminated by the market's own rebound. For every
   entry date the universe median forward return over the SAME horizon is
   computed, and basket's EXCESS over it reported. If the excess is ~0, the
   +4.41% is market timing, not stock selection, and the "edge" is beta.
   SPY is reported alongside as a second, cruder reference.

KILL CRITERIA, pre-committed before any output is seen (stated to the operator
before this was written):
  - the basket-over-solo edge must hold in the MAJORITY of sub-periods
    EXCLUDING 2020, and
  - the date-matched excess at 21d must stay clearly positive.
Fail either and this is regime, not signal -- no threshold hunting, no rescue.

Read-only. Delete script, tests and workflow once logged to MEMORY.md.
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    # write_through alone does not stream -- every print needs flush=True too
    # (see MEMORY.md / run_sleeve_pead_reconstruction.py).
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", write_through=True)
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module

import run_sleeve_entry_reconstruction as recon
import run_sleeve_sector_capitulation_reconstruction as cap

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "basket_crash_subperiod_control.csv"

# The two durations the original headline was quoted at. Keeping the grid small
# keeps the date-matched control (the expensive part) affordable.
HORIZONS = [21, 90]

# Eras chosen so each contains at least one capitulation episode and no single
# era can carry the result on its own. 2020 is deliberately its OWN era so it
# can be excluded wholesale, which is what the kill criterion turns on.
ERAS = [
    ("2009-2012", "2009-01-01", "2012-12-31"),
    ("2013-2015", "2013-01-01", "2015-12-31"),
    ("2016-2018", "2016-01-01", "2018-12-31"),
    ("2019-2021", "2019-01-01", "2021-12-31"),   # contains COVID
    ("2022-2026", "2022-01-01", None),
]
COVID_ERA = "2019-2021"

MIN_N = 10   # same floor as recon.MIN_N_OBS -- below this a cell is not reported


def _stats(rets: list[float]) -> dict:
    if len(rets) < MIN_N:
        return {"n": len(rets), "median": float("nan"), "win": float("nan")}
    s = pd.Series(rets)
    return {"n": len(rets), "median": float(s.median()), "win": float((s > 0).mean())}


def universe_median_forward(candidates: dict, dates: list[pd.Timestamp],
                            horizon: int) -> dict[pd.Timestamp, float]:
    """Median forward return of the WHOLE candidate universe from each date.

    This is the control that decides the question. basket_crash entries land in
    market-wide selloffs; if every stock bounced the same amount over the next
    21 days, the bucket's return is the market's, not the signal's. Computed on
    the same `forward_return` the study itself uses, so the comparison is
    apples-to-apples rather than against an index with different mechanics.
    """
    out: dict[pd.Timestamp, float] = {}
    tickers = list(candidates)
    for i, d in enumerate(dates, 1):
        rets = []
        for t in tickers:
            _cat, prices = candidates[t]
            r = recon.forward_return(prices, d, horizon)
            if r is not None:
                rets.append(r)
        out[d] = float(pd.Series(rets).median()) if len(rets) >= MIN_N else float("nan")
        if i % 100 == 0:
            print(f"    control {i}/{len(dates)} dates ({horizon}d)...", flush=True)
    return out


def main() -> None:
    print("=" * 74, flush=True)
    print("BASKET-CRASH: sub-period split + date-matched market control", flush=True)
    print("=" * 74, flush=True)
    print("KILL CRITERIA (pre-committed, before any output):", flush=True)
    print("  1. basket-over-solo edge holds in a MAJORITY of eras EXCLUDING 2020", flush=True)
    print("  2. date-matched excess at 21d stays clearly positive", flush=True)
    print("  Fail either -> regime, not signal. No rescue attempts.\n", flush=True)

    print("Building regime labels...", flush=True)
    labeled_df, _ = regime_module.build(DATA_DIR)
    print("Loading candidate universe...", flush=True)
    candidates = recon.load_candidates(DATA_DIR)
    print(f"Candidates: {len(candidates)}", flush=True)

    transitions = recon.detect_transitions(labeled_df)
    print(f"Transitions: {len(transitions)}", flush=True)
    selections = recon.rank_at_transitions(transitions, labeled_df, candidates, verbose=True)

    print("\nRebuilding capitulation entries (same trigger as the 2026-07-29 study)...", flush=True)
    raw = cap.find_capitulation_entries(selections, candidates)
    entries = recon.decluster(raw, min_gap_days=cap.DECLUSTER_MIN_GAP)
    print(f"Raw {len(raw)} -> declustered {len(entries)}", flush=True)

    solo = [e for e in entries if e["bucket"] == "solo_crash"]
    basket = [e for e in entries if e["bucket"] == "basket_crash"]
    print(f"  solo_crash {len(solo)}   basket_crash {len(basket)}", flush=True)

    # ── 1. Where do the entries actually sit in time? ─────────────────────
    print("\n" + "-" * 74, flush=True)
    print("1. ENTRY DISTRIBUTION BY YEAR -- is the sample clustered?", flush=True)
    print("-" * 74, flush=True)
    years = sorted({e["date"].year for e in entries})
    print(f"{'year':>6}{'solo':>8}{'basket':>9}{'basket %':>11}", flush=True)
    for y in years:
        s = sum(1 for e in solo if e["date"].year == y)
        b = sum(1 for e in basket if e["date"].year == y)
        share = b / len(basket) if basket else 0
        print(f"{y:>6}{s:>8}{b:>9}{share:>10.1%}", flush=True)

    # ── 2. Sub-period split ───────────────────────────────────────────────
    print("\n" + "-" * 74, flush=True)
    print("2. SUB-PERIOD SPLIT -- basket vs solo, per era", flush=True)
    print("-" * 74, flush=True)
    rows = []
    era_verdicts = {}
    for h in HORIZONS:
        print(f"\n  === {h}d horizon ===", flush=True)
        print(f"  {'era':<12}{'solo n':>8}{'solo med':>10}{'solo win':>10}"
              f"{'bskt n':>8}{'bskt med':>10}{'bskt win':>10}{'edge':>9}", flush=True)
        for name, a, b_ in ERAS:
            def _in(e):
                if a and e["date"] < pd.Timestamp(a):
                    return False
                if b_ and e["date"] > pd.Timestamp(b_):
                    return False
                return True
            sr = [r for e in solo if _in(e)
                  for r in [recon.forward_return(candidates[e["ticker"]][1], e["date"], h)]
                  if r is not None]
            br = [r for e in basket if _in(e)
                  for r in [recon.forward_return(candidates[e["ticker"]][1], e["date"], h)]
                  if r is not None]
            ss, bs = _stats(sr), _stats(br)
            edge = (bs["median"] - ss["median"]) if (bs["median"] == bs["median"]
                                                    and ss["median"] == ss["median"]) else float("nan")
            if h == 21:
                era_verdicts[name] = edge
            print(f"  {name:<12}{ss['n']:>8}{ss['median']:>10.2%}{ss['win']:>10.1%}"
                  f"{bs['n']:>8}{bs['median']:>10.2%}{bs['win']:>10.1%}{edge:>9.2%}", flush=True)
            rows.append({"horizon": h, "era": name,
                         "solo_n": ss["n"], "solo_median": ss["median"], "solo_win": ss["win"],
                         "basket_n": bs["n"], "basket_median": bs["median"], "basket_win": bs["win"],
                         "edge": edge})

    # ── 3. Date-matched market control ────────────────────────────────────
    print("\n" + "-" * 74, flush=True)
    print("3. DATE-MATCHED MARKET CONTROL -- is it selection, or the rebound?", flush=True)
    print("-" * 74, flush=True)
    print("For every entry date, the median forward return of the ENTIRE universe", flush=True)
    print("over the same horizon. Excess = bucket median - matched universe median.", flush=True)

    control_rows = []
    for h in HORIZONS:
        uniq = sorted({e["date"] for e in entries})
        print(f"\n  Computing universe median on {len(uniq)} dates at {h}d...", flush=True)
        umed = universe_median_forward(candidates, uniq, h)

        for label, bucket in (("solo_crash", solo), ("basket_crash", basket)):
            ex, raw_r, ctl_r = [], [], []
            for e in bucket:
                r = recon.forward_return(candidates[e["ticker"]][1], e["date"], h)
                m = umed.get(e["date"], float("nan"))
                if r is None or m != m:
                    continue
                raw_r.append(r); ctl_r.append(m); ex.append(r - m)
            st_raw, st_ex = _stats(raw_r), _stats(ex)
            ctl_med = float(pd.Series(ctl_r).median()) if ctl_r else float("nan")
            print(f"  {h:>3}d {label:<13} n={st_raw['n']:>4}  raw {st_raw['median']:>7.2%}"
                  f"   universe {ctl_med:>7.2%}   EXCESS {st_ex['median']:>7.2%}"
                  f"   excess-win {st_ex['win']:>6.1%}", flush=True)
            control_rows.append({"horizon": h, "bucket": label, "n": st_raw["n"],
                                 "raw_median": st_raw["median"], "universe_median": ctl_med,
                                 "excess_median": st_ex["median"], "excess_win": st_ex["win"]})

    out = pd.DataFrame(rows)
    ctl = pd.DataFrame(control_rows)
    OUT_CSV.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    ctl.to_csv(OUT_CSV.with_name("basket_crash_control.csv"), index=False)

    # ── Verdict against the pre-committed criteria ─────────────────────────
    print("\n" + "=" * 74, flush=True)
    print("VERDICT", flush=True)
    print("=" * 74, flush=True)
    non_covid = {k: v for k, v in era_verdicts.items() if k != COVID_ERA and v == v}
    pos = sum(1 for v in non_covid.values() if v > 0)
    print(f"Criterion 1 -- eras excluding {COVID_ERA} with a positive basket edge at 21d: "
          f"{pos}/{len(non_covid)}", flush=True)
    for k, v in non_covid.items():
        print(f"    {k}: {v:+.2%}", flush=True)
    c1 = len(non_covid) > 0 and pos > len(non_covid) / 2

    ex21 = ctl[(ctl.horizon == 21) & (ctl.bucket == "basket_crash")]["excess_median"]
    ex21 = float(ex21.iloc[0]) if len(ex21) else float("nan")
    print(f"\nCriterion 2 -- date-matched excess at 21d: {ex21:+.2%}", flush=True)
    c2 = ex21 == ex21 and ex21 > 0.01   # >1pp, i.e. clears a round trip

    print(f"\n  1. majority of non-COVID eras positive : {'PASS' if c1 else 'FAIL'}", flush=True)
    print(f"  2. date-matched excess clearly positive : {'PASS' if c2 else 'FAIL'}", flush=True)
    print(f"\nVERDICT: {'PASS' if (c1 and c2) else 'FAIL'}", flush=True)
    print(f"\nWrote {OUT_CSV} and {OUT_CSV.with_name('basket_crash_control.csv')}", flush=True)


if __name__ == "__main__":
    main()
