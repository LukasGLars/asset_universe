"""TEMPORARY (2026-11-01). How much gold?

Live targets AVGO 20 / LLY 20 / Gold 20 / Index 30 / Cash 10. Gold swept
0 / 10 / 15 / 20 / 25%; the index absorbs the difference (index = 50 - gold).
SEK, daily, 2009-08..now, SPY as index proxy, cash at 2%/yr, live +-10pp
band (full rebalance on any breach), 10 bps.

PRE-REGISTERED: rank on the WORST of five windows (A 09-13, B 14-18,
C 19-22, D 23-now, E 09-22). Gold moves off 20% only if a weight beats it by
>= 0.10 worst-window Calmar AND >= 1pp worst-window MaxDD. Delete after logging.
"""
from __future__ import annotations
import io, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)
sys.path.insert(0, str(Path(__file__).parent / "src"))
import numpy as np, pandas as pd
from asset_universe import config
from asset_universe.store import reader

START, TC, CASH_YLD = "2009-08-06", 0.0010, 0.02
GOLD = [0.0, 0.10, 0.15, 0.20, 0.25]
BAND = 0.10


def targets(g):
    return {"AVGO": 0.20, "LLY": 0.20, "Gold": g, "Index": 0.50 - g, "Cash": 0.10}
WINDOWS = {"A 09-13": (START, "2013-12-31"), "B 14-18": ("2014-01-01", "2018-12-31"),
           "C 19-22": ("2019-01-01", "2022-12-31"), "D 23-now": ("2023-01-01", None),
           "E 09-22": (START, "2022-12-31")}


def _c(cat, t):
    return reader.load(reader.ticker_path(config.raw_data_dir(), cat, t))["close"]


def prices() -> pd.DataFrame:
    fx = _c("fx", "USDSEK=X")
    df = pd.DataFrame({"AVGO": _c("equities", "AVGO"), "LLY": _c("equities", "LLY"),
                       "Gold": _c("commodities", "GC=F"), "Index": _c("equities", "SPY")}).loc[START:]
    df = df.ffill(limit=3).mul(fx.reindex(df.index).ffill(), axis=0).dropna()
    days = np.arange(len(df))
    df["Cash"] = (1 + CASH_YLD) ** (days / 252)
    return df


def simulate(px, tg):
    names = list(tg)
    tgt = np.array([tg[n] for n in names])
    width = np.full(len(tgt), BAND)
    p = px[names].to_numpy()
    units = tgt / p[0]
    vals, n_reb = np.empty(len(p)), 0
    for i in range(len(p)):
        pos = units * p[i]
        v = pos.sum()
        if np.any(np.abs(pos / v - tgt) > width + 1e-12):
            v -= np.abs(tgt * v - pos).sum() * TC
            units = tgt * v / p[i]
            n_reb += 1
        vals[i] = v
    return pd.Series(vals, index=px.index), n_reb


def stats(eq):
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
    mdd = (eq / eq.cummax() - 1).min()
    return cagr, mdd, cagr / abs(mdd)


def main():
    px = prices()
    yrs = (px.index[-1] - px.index[0]).days / 365.25
    print(f"{px.index[0].date()}..{px.index[-1].date()} SEK, band +-{BAND:.0%}\n")
    rows = []
    for g in GOLD:
        tg = targets(g)
        eq, n = simulate(px, tg)
        fc, fm, _ = stats(eq)
        w = {k: stats(simulate(px.loc[a:b], tg)[0]) for k, (a, b) in WINDOWS.items()}
        rows.append({"g": g, "cagr": fc, "mdd": fm, "reb": n / yrs,
                     "wmdd": min(x[1] for x in w.values()), "wcal": min(x[2] for x in w.values()),
                     "wwin": min(w, key=lambda k: w[k][2]), "w": w})
    print(f"{'gold/index':<12}{'CAGR':>7}{'MaxDD':>8}{'reb/yr':>8}{'worst MDD':>11}{'worst Cal':>11}  window")
    for r in rows:
        tag = " LIVE" if r["g"] == 0.20 else ""
        print(f"{r['g']:.0%}/{0.5 - r['g']:.0%}{tag:<6}{r['cagr']:>+7.1%}{r['mdd']:>+8.1%}{r['reb']:>8.1f}"
              f"{r['wmdd']:>+11.1%}{r['wcal']:>11.2f}  {r['wwin']}")
    print("\nPer window MaxDD:")
    for r in rows:
        print(f"  gold {r['g']:.0%}: " + "  ".join(f"{k} {v[1]:+.1%}" for k, v in r["w"].items()))
    live = next(r for r in rows if r["g"] == 0.20)
    best = max(rows, key=lambda r: r["wcal"])
    beats = best is not live and best["wcal"] - live["wcal"] >= 0.10 and best["wmdd"] - live["wmdd"] >= 0.01
    print(f"\nVERDICT (pre-registered): {f'MOVE gold to {best[chr(103)]:.0%}' if beats else 'gold 20% STAYS -- no weight clears the bar'}")


if __name__ == "__main__":
    main()
