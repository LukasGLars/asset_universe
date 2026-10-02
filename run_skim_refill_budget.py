"""
run_skim_refill_budget.py

TEMPORARY diagnostic (2026-10-02). How often would a 10%-relative rebalance
band skim gains into cash, and does that refill the dip-buy sleeve fast enough
to fund the triggers that actually arrived?

Context. 2026-10-02 established that the standing 10% cash sleeve should be
deployed in full at the crash trigger -- every ladder lost (see MEMORY.md
"Cash-tranche laddering"). But that test handed a FULL sleeve to all 31 AVGO
episodes. In reality the sleeve is spent in one go and refills at the
contribution rate, so roughly half the triggers would have been underfunded.
That gap is what this measures, with the skim rule as the variable.

The question is NOT whether skimming beats holding. It is arithmetic:
  1. How often does each position breach target x 1.10?
  2. How much cash does each breach yield?
  3. What fraction of a full sleeve is actually on hand when a trigger fires,
     with contributions alone vs contributions plus skim?

Three arms, same prices and same triggers:
  A  contributions only, no skim
  B  contributions + 10% band skim
  C  skim only, no contributions   (isolates the skim's own contribution)

Mechanics and the discipline they follow:
  - Band checked at close(i); the skim executes at close(i+1). The trigger is
    computed from close(i); the deploy executes at close(i+1). Nothing acts on
    the bar that generated it.
  - Cash is the sink and the sleeve, so it is EXEMPT from the band. Capping
    cash at 11% would make a 10% sleeve unbuildable, which would answer a
    different question.
  - A skim sells the overweight back to exactly target and moves the proceeds
    to cash. Underweights are never topped up -- skim-only, which is the rule
    being priced.
  - A trigger deploys ALL available cash into the triggering name, per the
    laddering verdict. If cash is short, the trigger is underfunded, and that
    shortfall is the output.

Index leg: LF Global Index has no public price feed, so SPY stands in. The
operator describes that fund as broad US large-cap exposure, which SPY is, but
SPY is less diversified -- it will slightly OVERSTATE how often the index leg
breaches its band and how correlated it is to AVGO. Flagged, not corrected.

Crypto starts in 2014/2017, so requiring it would truncate the history past
2008-2015. Two runs: --no-crypto renormalises the other five weights and
reaches back to AVGO's start; the default uses the target as actually stated
over the shorter window. Crypto's volatility is a major driver of band
breaches, so neither run alone answers it.

Read-only. Delete script, tests and workflow once logged to MEMORY.md.
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", write_through=True)
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.store import reader

DATA_DIR = config.raw_data_dir()

# Operator-stated target, 2026-09-27 (MEMORY.md). Fractions of the Reactor
# Core account. Spiltan sits outside and is not modelled.
TARGET_FULL = {
    "AVGO": 0.20, "LLY": 0.20, "GOLD": 0.20,
    "INDEX": 0.25, "BTC": 0.025, "ETH": 0.025,
}
CASH_TARGET = 0.10

SERIES = {
    "AVGO":  ("equities",    "AVGO"),
    "LLY":   ("equities",    "LLY"),
    "GOLD":  ("commodities", "GC=F"),
    "INDEX": ("equities",    "SPY"),
    "BTC":   ("crypto",      "BTC-USD"),
    "ETH":   ("crypto",      "ETH-USD"),
}
FX_PAIR = ("fx", "USDSEK=X")

BAND            = 0.10        # relative, matches vol_target.REBAL_BAND
START_RC_SEK    = 979_428.0   # operator-confirmed Reactor Core account value
ANNUAL_CONTRIB  = 100_000.0   # operator-stated cash build rate
CASH_ANNUAL     = 0.02
CASH_DAILY      = (1 + CASH_ANNUAL) ** (1 / 252) - 1

CRASH_WINDOW    = 5
CRASH_THRESHOLD = -0.10
DECLUSTER_DAYS  = 21
TRIGGER_NAMES   = ("AVGO", "LLY")


def load_prices_sek(with_crypto: bool) -> pd.DataFrame:
    fx = reader.load(reader.ticker_path(DATA_DIR, *FX_PAIR))["close"].dropna()
    cols = {}
    for key, (cat, tick) in SERIES.items():
        if not with_crypto and key in ("BTC", "ETH"):
            continue
        cols[key] = reader.load(reader.ticker_path(DATA_DIR, cat, tick))["close"].dropna()
    px = pd.DataFrame(cols)
    px = px.join(fx.rename("FX"), how="outer").sort_index()
    px = px.ffill().dropna()
    for c in px.columns:
        if c != "FX":
            px[c] = px[c] * px["FX"]          # everything quoted in USD
    return px.drop(columns=["FX"])


def targets_for(cols: list[str]) -> dict[str, float]:
    """Renormalise the risk-asset targets over the assets actually present,
    keeping cash at its stated 10%."""
    sub = {k: v for k, v in TARGET_FULL.items() if k in cols}
    scale = (1.0 - CASH_TARGET) / sum(sub.values())
    return {k: v * scale for k, v in sub.items()}


def trigger_signal_days(px: pd.DataFrame) -> dict[str, set[int]]:
    """Declustered crash-ROC SIGNAL indices per name. Callers execute on i+1."""
    out = {}
    for name in TRIGGER_NAMES:
        if name not in px.columns:
            continue
        s = px[name]
        roc = s.pct_change(CRASH_WINDOW)
        raw = np.flatnonzero((roc <= CRASH_THRESHOLD).to_numpy())
        kept: list[int] = []
        for i in raw:
            if not kept or (i - kept[-1]) >= DECLUSTER_DAYS:
                kept.append(int(i))
        out[name] = set(kept)
    return out


def skim_excess(
    values: dict[str, float],
    cash: float,
    tgt: dict[str, float],
    band: float = BAND,
) -> dict[str, float]:
    """SEK to sell from each position that breaches target x (1+band).

    Selling exactly this amount moves the position to its target weight: the
    proceeds stay inside the account (they become cash), so `total` does not
    change and the new weight is tgt*total/total = tgt. Extracted so the
    arithmetic is testable on its own -- it is what the whole run turns on.
    """
    total = sum(values.values()) + cash
    if total <= 0:
        return {}
    return {
        a: values[a] - tgt[a] * total
        for a in values
        if values[a] / total > tgt[a] * (1 + band)
    }


def simulate(px: pd.DataFrame, skim: bool, contribute: bool) -> dict:
    tgt = targets_for(list(px.columns))
    assets = list(tgt)
    sigs = trigger_signal_days(px)
    dates = px.index

    shares = {a: START_RC_SEK * w / float(px[a].iloc[0]) for a, w in tgt.items()}
    cash = START_RC_SEK * CASH_TARGET
    per_session_contrib = (ANNUAL_CONTRIB / 252.0) if contribute else 0.0

    pending_skim: dict[str, float] = {}
    pending_deploy: str | None = None
    skims: list[dict] = []
    fires: list[dict] = []

    for i, d in enumerate(dates):
        px_row = {a: float(px[a].iloc[i]) for a in assets}
        cash = cash * (1 + CASH_DAILY) + per_session_contrib

        # ── execute what was decided at close(i-1) ────────────────────────
        for a, excess_sek in pending_skim.items():
            sold = min(excess_sek, shares[a] * px_row[a])
            shares[a] -= sold / px_row[a]
            cash += sold
            skims.append({"date": d, "asset": a, "sek": sold})
        pending_skim = {}

        if pending_deploy is not None:
            a = pending_deploy
            total = sum(shares[x] * px_row[x] for x in assets) + cash
            fires.append({
                "date": d, "asset": a, "cash": cash, "total": total,
                "cash_frac": cash / total if total else 0.0,
                "sleeve_frac": (cash / total / CASH_TARGET) if total else 0.0,
            })
            shares[a] += cash / px_row[a]
            cash = 0.0
            pending_deploy = None

        # ── decide at close(i), act next session ──────────────────────────
        values = {a: shares[a] * px_row[a] for a in assets}
        if skim:
            pending_skim = skim_excess(values, cash, tgt)

        for name, idxs in sigs.items():
            if i in idxs:
                pending_deploy = name
                break

    px_last = {a: float(px[a].iloc[-1]) for a in assets}
    final = sum(shares[a] * px_last[a] for a in assets) + cash
    years = (dates[-1] - dates[0]).days / 365.25
    sk = pd.DataFrame(skims)
    fr = pd.DataFrame(fires)
    return {"skims": sk, "fires": fr, "final": final, "years": years,
            "targets": tgt, "n_sessions": len(dates)}


def report(px: pd.DataFrame, label: str) -> None:
    tgt = targets_for(list(px.columns))
    print("=" * 78)
    print(f"{label}")
    print("=" * 78)
    print(f"Window       : {px.index[0].date()} to {px.index[-1].date()} "
          f"({len(px)} sessions)")
    print(f"Target       : " + "  ".join(f"{k} {v:.1%}" for k, v in tgt.items())
          + f"  CASH {CASH_TARGET:.0%}")
    print(f"Band         : target x {1 + BAND:.2f} (10% relative), cash exempt")
    print(f"Start RC     : {START_RC_SEK:,.0f} kr")

    arms = {
        "A  contributions only": simulate(px, skim=False, contribute=True),
        "B  contrib + skim":     simulate(px, skim=True,  contribute=True),
        "C  skim only":          simulate(px, skim=True,  contribute=False),
    }

    b = arms["B  contrib + skim"]
    sk = b["skims"]
    yrs = b["years"]

    print("\n" + "-" * 78)
    print(f"1. SKIM FREQUENCY at a {BAND:.0%} relative band (arm B, {yrs:.1f} yr)")
    print("-" * 78)
    if sk.empty:
        print("  no breaches")
    else:
        print(f"  total skims: {len(sk)}   = {len(sk)/yrs:.1f}/yr   "
              f"= one every {252*yrs/len(sk):.0f} sessions")
        rows = []
        for a in sorted(sk["asset"].unique()):
            s = sk[sk["asset"] == a]
            rows.append({
                "asset": a, "target": f"{tgt[a]:.1%}", "skims": len(s),
                "per_yr": round(len(s)/yrs, 1),
                "median_kr": f"{s['sek'].median():,.0f}",
                "total_kr": f"{s['sek'].sum():,.0f}",
                "kr_per_yr": f"{s['sek'].sum()/yrs:,.0f}",
            })
        print(pd.DataFrame(rows).to_string(index=False))
        print(f"\n  ALL: {sk['sek'].sum()/yrs:,.0f} kr/yr from skims vs "
              f"{ANNUAL_CONTRIB:,.0f} kr/yr contributed "
              f"({sk['sek'].sum()/yrs/ANNUAL_CONTRIB:.2f}x)")
        print(f"  median skim {sk['sek'].median():,.0f} kr = "
              f"{sk['sek'].median()/(START_RC_SEK*CASH_TARGET):.0%} of a full sleeve")

    print("\n" + "-" * 78)
    print("2. CASH ON HAND WHEN A TRIGGER FIRES (sleeve_frac 1.00 = full 10%)")
    print("-" * 78)
    for name, arm in arms.items():
        fr = arm["fires"]
        if fr.empty:
            print(f"  {name:24s} no triggers")
            continue
        sf = fr["sleeve_frac"]
        print(f"  {name:24s} n={len(fr):3d}  median {sf.median():5.2f}  "
              f">=0.8 {(sf >= 0.8).mean():5.1%}  >=0.5 {(sf >= 0.5).mean():5.1%}  "
              f"<0.25 {(sf < 0.25).mean():5.1%}")

    print("\n" + "-" * 78)
    print("3. TERMINAL VALUE (secondary -- see caveat)")
    print("-" * 78)
    for name, arm in arms.items():
        contributed = ANNUAL_CONTRIB * arm["years"] if "only" in name or "contrib +" in name else 0.0
        if name.startswith("C"):
            contributed = 0.0
        print(f"  {name:24s} {arm['final']:>14,.0f} kr   "
              f"(contributed {contributed:,.0f} kr)")
    print("\n  A vs B is NOT a clean read on whether skimming pays: B both skims")
    print("  AND has more cash to deploy, and the 2026-08-18 holdback test showed")
    print("  a portfolio sim can invert an event study. Criterion 1 and 2 above")
    print("  are what this run is for.")


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--no-crypto", action="store_true")
    a = p.parse_args()

    if a.no_crypto:
        report(load_prices_sek(with_crypto=False),
               "SKIM REFILL BUDGET -- 5 assets, no crypto (long history)")
    else:
        report(load_prices_sek(with_crypto=False),
               "SKIM REFILL BUDGET -- 5 assets, no crypto (long history)")
        print()
        report(load_prices_sek(with_crypto=True),
               "SKIM REFILL BUDGET -- full stated target incl. crypto (short history)")

    print("\n" + "=" * 78)
    print("Bounds on all of the above:")
    print("  - SPY stands in for LF Global Index (no public feed). Less")
    print("    diversified, so index-leg breaches are OVERSTATED.")
    print("  - Contributions are a flat 100k/yr against a portfolio that grows")
    print("    through the window, so early years are over-contributed relative")
    print("    to size. Skim rates as a MULTIPLE of contributions are the")
    print("    scale-free number; absolute kr/yr is not.")
    print("  - Skim-only, no top-ups of underweights. A full two-sided rebalance")
    print("    is a different policy and is not priced here.")
    print("  - Gold/index/crypto triggers are not modelled; only AVGO and LLY")
    print("    crash-ROC fires deploy cash.")
    print("=" * 78)


if __name__ == "__main__":
    main()
