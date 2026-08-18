"""
run_ai_basket_beta.py

Rebuild of the 2026-08-16 hedge screen, extended to Swedish large caps.

Method (unchanged from the original, whose script was deleted per repo
convention -- the published reference table in MEMORY.md is what pins it):
an equal-weighted AI-semi basket (NVDA/AVGO/AMD/MRVL/MU/AMAT/LRCX/KLAC),
and each candidate's beta/correlation to that basket measured ONLY on days
the basket is >=10% below its running peak, 2012-2026. The question is not
"is this asset correlated to AVGO on average" but "does it fall with AVGO
in exactly the drawdown it is supposed to protect against" -- which is why
AMZN's low full-sample correlation (0.60) was misleading and its
drawdown-beta (0.53) was disqualifying.

SELF-CHECK: the USD pass must reproduce MEMORY.md's published values --
SPY 0.42, QQQ 0.54, AMZN 0.53, LLY 0.23, GC_F 0.05. If it does not, the
implementation is wrong and every Swedish number below is meaningless.

CURRENCY. The original table was all-USD, so currency never arose. Swedish
names are SEK-denominated, and a USD asset gains SEK value when USD
strengthens -- which it tends to do in risk-off. Reporting a SEK-return
beta against a USD-return basket would silently mix the two, so both passes
are run: USD (reproduces the reference, validates the code) and SEK
(everything including the basket converted, which is what a Swedish
investor actually experiences).
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
import run_combined_system as rcs

BASKET = ["NVDA", "AVGO", "AMD", "MRVL", "MU", "AMAT", "LRCX", "KLAC"]
DD_THRESHOLD = -0.10
START = "2012-01-01"

# Published in MEMORY.md's 2026-08-16 table -- used to validate this rebuild.
REFERENCE = {"SPY": 0.42, "QQQ": 0.54, "AMZN": 0.53, "MSFT": 0.51,
             "GOOGL": 0.48, "WMT": 0.16, "LLY": 0.23, "GC_F": 0.05}


def load(cat: str, stem: str) -> pd.Series | None:
    return rcs.load_prices(cat, stem)


def se_stem(t: str) -> str:
    return t.replace(".", "_").replace("-", "_")


def build_basket(to_sek: pd.Series | None) -> pd.Series:
    cols = {}
    for t in BASKET:
        s = load("equities", t)
        if s is not None:
            cols[t] = s
    px = pd.DataFrame(cols).dropna()
    if to_sek is not None:
        px = px.mul(to_sek.reindex(px.index).ffill(), axis=0).dropna()
    rets = px.pct_change().dropna()
    ew = rets.mean(axis=1)
    return (1 + ew).cumprod()


def drawdown_mask(idx_series: pd.Series) -> pd.Series:
    dd = idx_series / idx_series.cummax() - 1
    return dd <= DD_THRESHOLD


def beta_corr(cand: pd.Series, basket_idx: pd.Series, mask: pd.Series):
    br = basket_idx.pct_change()
    cr = cand.pct_change()
    df = pd.concat([cr, br], axis=1, keys=["c", "b"]).dropna()
    df = df[mask.reindex(df.index).fillna(False)]
    if len(df) < 60 or df["b"].var() == 0:
        return None, None, len(df)
    beta = df["c"].cov(df["b"]) / df["b"].var()
    return beta, df["c"].corr(df["b"]), len(df)


def run_pass(label: str, to_sek: pd.Series | None, candidates: list[tuple[str, str, str]]):
    basket = build_basket(to_sek)
    basket = basket[basket.index >= START]
    mask = drawdown_mask(basket)
    print(f"\n=== {label} ===")
    print(f"  basket {basket.index[0].date()} -> {basket.index[-1].date()}, "
          f"{int(mask.sum()):,} of {len(mask):,} days in >=10% drawdown "
          f"({mask.mean():.0%})")
    rows = []
    for name, cat, stem in candidates:
        s = load(cat, stem)
        if s is None:
            continue
        if to_sek is not None and cat != "se_equities":
            s = (s * to_sek.reindex(s.index).ffill()).dropna()
        b, c, n = beta_corr(s, basket, mask)
        if b is None:
            continue
        rows.append({"name": name, "beta": b, "corr": c, "n": n})
    return pd.DataFrame(rows).sort_values("beta"), basket


def main():
    usdsek = load("fx", "USDSEK_X")

    us_ref = [(t, "equities", t) for t in
              ["SPY", "QQQ", "AMZN", "MSFT", "GOOGL", "WMT", "LLY"]] + \
             [("GC_F", "commodities", "GC_F")]
    se = [(t, "se_equities", se_stem(t)) for t in
          [l.strip() for l in open("config/universes/se_equities.txt")
           if l.strip() and not l.startswith("#")]]

    # --- pass 1: USD, reference names only -> validates the rebuild ---
    usd, _ = run_pass("USD basis - reproduction check", None, us_ref)
    print(f"  {'name':<8} {'beta':>6} {'corr':>6} {'ref':>6} {'delta':>7}")
    ok = True
    for _, r in usd.iterrows():
        ref = REFERENCE.get(r["name"])
        d = r["beta"] - ref
        if abs(d) > 0.05:
            ok = False
        print(f"  {r['name']:<8} {r['beta']:>6.2f} {r['corr']:>6.2f} "
              f"{ref:>6.2f} {d:>+7.2f}")
    print(f"  SELF-CHECK: {'PASS' if ok else 'FAIL'} "
          f"(all within 0.05 of published values)")
    if not ok:
        print("  -> Swedish results below are NOT trustworthy until this passes.")

    # --- pass 2: SEK, everything ---
    sek, _ = run_pass("SEK basis - all candidates", usdsek, us_ref + se)
    print(f"  {'name':<12} {'beta':>6} {'corr':>6} {'n':>6}")
    for _, r in sek.iterrows():
        print(f"  {r['name']:<12} {r['beta']:>6.2f} {r['corr']:>6.2f} {int(r['n']):>6}")

    out = PROJECT_ROOT / "comparison_results" / "ai_basket_beta_se.csv"
    sek.to_csv(out, index=False)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
