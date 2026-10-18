"""TEMPORARY (2026-10-18). How should the 40% concentrated-growth leg split
between AVGO and LLY? Swept 0/40 .. 40/0 in 5pp steps, everything else held
at the live target: Gold 20 / Index 25 / Cash 10 / Crypto 5.

Proxies (stated, not hidden):
  Index  = SPY (no world-index series in the store; MSCI World is ~70% US).
  Crypto = cash at 0%. BTC history starts 2014 and would cut the window in
           half; the 5% is identical across rows, so it shifts levels only.
  Cash   = 0% (ISK cash). Same across rows.
All in SEK (x USDSEK). Daily closes, 10pp absolute band (live REBAL_BAND),
rebalance all legs to target when any leg breaches, 10bps per traded kr.

PRE-REGISTERED, before the run:
  Rank on the WORST sub-period (CLAUDE.md rule 2), never the full sample.
  Windows: A 2009-08..2013, B 2014..2018, C 2019..2022, D 2023..now,
           E 2009-08..2022 (excludes the AI / GLP-1 melt-up).
  Each window restarts at target weights.
  Noise bar: a split replaces 20/20 only if it beats it on worst-window
  MaxDD by >= 2pp AND worst-window Calmar by >= 0.10. Otherwise 20/20 stands.

Delete after logging.
"""
from __future__ import annotations
import io, sys
from pathlib import Path
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", write_through=True)
sys.path.insert(0, str(Path(__file__).parent / "src"))
import numpy as np, pandas as pd
from asset_universe import config
from asset_universe.store import reader

BAND, TC = 0.10, 0.0010
START = "2009-08-06"  # AVGO IPO
WINDOWS = {"A 09-13": (START, "2013-12-31"), "B 14-18": ("2014-01-01", "2018-12-31"),
           "C 19-22": ("2019-01-01", "2022-12-31"), "D 23-now": ("2023-01-01", None),
           "E 09-22": (START, "2022-12-31")}
FIXED = {"Gold": 0.20, "Index": 0.25, "Cash": 0.15}  # cash 10 + crypto 5
SPLITS = [(a / 100, (40 - a) / 100) for a in range(0, 45, 5)]


def _close(cat, tkr):
    df = reader.load(reader.ticker_path(config.raw_data_dir(), cat, tkr))
    return df["close"]


def prices() -> pd.DataFrame:
    fx = _close("fx", "USDSEK=X")
    usd = {"AVGO": _close("equities", "AVGO"), "LLY": _close("equities", "LLY"),
           "Gold": _close("commodities", "GC=F"), "Index": _close("equities", "SPY")}
    df = pd.DataFrame(usd).loc[START:]
    fx = fx.reindex(df.index).ffill()
    df = df.ffill(limit=3).mul(fx, axis=0).dropna()
    df["Cash"] = 1.0
    return df


def simulate(px: pd.DataFrame, w: dict[str, float]) -> pd.Series:
    names = list(w)
    tgt = np.array([w[n] for n in names])
    p = px[names].to_numpy()
    units = tgt / p[0]
    vals = np.empty(len(p))
    for i in range(len(p)):
        pos = units * p[i]
        v = pos.sum()
        cur = pos / v
        if np.any(np.abs(cur - tgt) > BAND + 1e-9):
            v -= np.abs(tgt * v - pos).sum() * TC
            units = tgt * v / p[i]
        vals[i] = v
    return pd.Series(vals, index=px.index)


def stats(eq: pd.Series) -> tuple[float, float, float]:
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
    mdd = (eq / eq.cummax() - 1).min()
    return cagr, mdd, cagr / abs(mdd) if mdd else np.nan


def main() -> None:
    px = prices()
    print(f"Window {px.index[0].date()} .. {px.index[-1].date()}, SEK, n={len(px)}")
    rows = []
    for a, l in SPLITS:
        w = {"AVGO": a, "LLY": l, **FIXED}
        r = {"split": f"{a*100:.0f}/{l*100:.0f}"}
        r["full_cagr"], r["full_mdd"], r["full_cal"] = stats(simulate(px, w))
        for k, (s, e) in WINDOWS.items():
            r[k] = stats(simulate(px.loc[s:e], w))
        r["worst_mdd"] = min(r[k][1] for k in WINDOWS)
        r["worst_cal"] = min(r[k][2] for k in WINDOWS)
        r["worst_win"] = min(WINDOWS, key=lambda k: r[k][2])
        rows.append(r)

    print("\nAVGO/LLY  full CAGR  full MDD | worst-window MDD  worst Calmar (window)")
    for r in rows:
        print(f"  {r['split']:>6}   {r['full_cagr']:+7.1%}  {r['full_mdd']:+7.1%} | "
              f"{r['worst_mdd']:+8.1%}       {r['worst_cal']:5.2f} ({r['worst_win']})")

    print("\nPer window: CAGR / MaxDD / Calmar")
    for k in WINDOWS:
        print(f"  {k}")
        for r in rows:
            c, m, cal = r[k]
            print(f"    {r['split']:>6}  {c:+7.1%}  {m:+7.1%}  {cal:5.2f}")

    base = next(r for r in rows if r["split"] == "20/20")
    best = max(rows, key=lambda r: r["worst_cal"])
    beats = (best["worst_mdd"] - base["worst_mdd"] >= 0.02
             and best["worst_cal"] - base["worst_cal"] >= 0.10)
    print(f"\nBest on worst-window Calmar: {best['split']} "
          f"({best['worst_cal']:.2f}, MDD {best['worst_mdd']:+.1%}) vs 20/20 "
          f"({base['worst_cal']:.2f}, MDD {base['worst_mdd']:+.1%})")
    print(f"Verdict (pre-registered noise bar): "
          f"{'ADOPT ' + best['split'] if beats else '20/20 STANDS -- difference inside noise bar'}")


if __name__ == "__main__":
    main()
