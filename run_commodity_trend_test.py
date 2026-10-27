"""TEMPORARY (2026-10-27). Does a commodity trend rule earn a place, the way
the crypto trend rule did?

PRE-REGISTERED, before the run. Nothing here is borrowed from the crypto rule
(its 50/100/200 + 2% band were chosen on crypto):
  Rule      : time-series momentum from the published literature
              (Moskowitz/Ooi/Pedersen 2012): long when the trailing 252-day
              return > 0, else flat. Long-only (ETP, ISK). Signal read at each
              month end, applied from the next session.
  Assets    : (a) oil CL=F alone; (b) equal-weight basket of the store's 8
              commodity futures (gold, silver, oil, copper, natgas, corn,
              wheat, soy), each leg with its own signal.
  Costs     : Yahoo continuous futures IGNORE the roll, so a flat annual drag
              is charged while long, reported at 0% / 3% / 6%. The verdict
              uses 3%. Plus 0.5% per round trip.
  Control   : EXPOSURE-MATCHED buy-and-hold (B&H scaled to the rule's average
              exposure, same drag on the exposed part).
  Eras      : 2001-07, 2008-13, 2014-19, 2020-now.
  Pass      : at 3% drag, beats the control on Calmar in >= 3 of 4 eras AND
              full-sample CAGR > 0. Judged separately for (a) and (b).
Delete after logging.
"""
from __future__ import annotations
import io, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)
sys.path.insert(0, str(Path(__file__).parent / "src"))
import numpy as np, pandas as pd
from asset_universe import config
from asset_universe.store import reader

TICKERS = ["GC=F", "SI=F", "CL=F", "HG=F", "NG=F", "ZC=F", "ZW=F", "ZS=F"]
ERAS = {"2001-07": ("2001-01-01", "2007-12-31"), "2008-13": ("2008-01-01", "2013-12-31"),
        "2014-19": ("2014-01-01", "2019-12-31"), "2020-now": ("2020-01-01", None)}
LOOKBACK, RT_COST = 252, 0.005

px = pd.DataFrame({t: reader.load(reader.ticker_path(config.raw_data_dir(), "commodities", t))["close"]
                   for t in TICKERS}).sort_index().loc["1999-01-01":].ffill(limit=5)
# Negative/zero prints (CL=F in April 2020) break returns; clip to a floor.
px = px.where(px > 0.5)
rets = px.pct_change().clip(-0.5, 1.0)


def signal(p: pd.Series) -> pd.Series:
    """Read at each month's LAST session, held for the whole NEXT month. The
    first version broadcast a month's end value back over that same month --
    lookahead, caught by a random-walk smoke test that showed +18%/yr."""
    mom = p / p.shift(LOOKBACK) - 1
    per = mom.index.to_period("M")
    last = mom.groupby(per).last()
    sig_m = (last > 0).astype(float).where(last.notna()).shift(1)  # this month's read -> next month
    return pd.Series(sig_m.reindex(per).to_numpy(), index=mom.index)


def leg(t: str, drag: float) -> tuple[pd.Series, pd.Series, pd.Series]:
    r, s = rets[t], signal(px[t]).reindex(rets.index)
    d = drag / 252
    trade = s.diff().abs().fillna(0) * RT_COST / 2
    rule = (s * (r - d) - trade).dropna()
    bh = (r - d).reindex(rule.index)
    return rule, bh, s.reindex(rule.index)


def stats(x: pd.Series) -> tuple[float, float, float]:
    eq = (1 + x.fillna(0)).cumprod()
    yrs = len(x) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else np.nan
    mdd = (eq / eq.cummax() - 1).min()
    return cagr, mdd, cagr / abs(mdd) if mdd < 0 else np.nan


def evaluate(name, rule, bh, expo):
    print(f"\n{name}")
    wins = 0
    for era, (a, b) in ERAS.items():
        r, h, e = rule.loc[a:b], bh.loc[a:b], expo.loc[a:b]
        ctrl = h * e.mean()
        rc, rm, rcal = stats(r); cc, cm, ccal = stats(ctrl)
        win = rcal > ccal
        wins += win
        print(f"  {era:<9} rule CAGR {rc:+6.1%} MDD {rm:+6.1%} Cal {rcal:5.2f} | "
              f"ctrl CAGR {cc:+6.1%} MDD {cm:+6.1%} Cal {ccal:5.2f} | expo {e.mean():4.0%} {'WIN' if win else '   '}")
    fc, fm, fcal = stats(rule)
    print(f"  full      rule CAGR {fc:+6.1%} MDD {fm:+6.1%} Cal {fcal:5.2f}   eras won {wins}/4")
    return wins, fc


for drag in (0.0, 0.03, 0.06):
    print(f"\n========== drag {drag:.0%}/yr while long ==========")
    o = leg("CL=F", drag)
    ow, oc = evaluate("(a) OIL  CL=F", *o)
    legs = [leg(t, drag) for t in TICKERS]
    idx = legs[0][0].index
    for l in legs[1:]:
        idx = idx.intersection(l[0].index)
    basket_rule = sum(l[0].reindex(idx) for l in legs) / len(legs)
    basket_bh = sum(l[1].reindex(idx) for l in legs) / len(legs)
    basket_expo = sum(l[2].reindex(idx) for l in legs) / len(legs)
    bw, bc = evaluate("(b) BASKET (8 commodities, equal weight)", basket_rule, basket_bh, basket_expo)
    if drag == 0.03:
        verdict = {n: ("PASS" if w >= 3 and c > 0 else "FAIL") for n, w, c in (("oil", ow, oc), ("basket", bw, bc))}

print(f"\nVERDICT (pre-registered, 3% drag): oil {verdict['oil']}, basket {verdict['basket']}")
