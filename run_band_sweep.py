"""TEMPORARY (2026-11-01). How wide should the rebalance band be?

Live portfolio targets: AVGO 20 / LLY 20 / Gold 20 / Index 25 / Cash 10
(crypto exited; the five sum to 95%, normalised to 100% here). SEK, daily,
2009-08 (AVGO IPO) to now. Index = SPY (no world-index series in store).
Cash earns 2%/yr (assumption, stated). 10 bps per traded kr.
Rebalance: when ANY leg breaches its band, ALL legs go back to target.

Bands compared:
  absolute +-5 / +-7.5 / +-10 pp (live = 10)
  relative +-25% / +-50% of each leg's target

PRE-REGISTERED: rank on the WORST of five windows (A 09-13, B 14-18,
C 19-22, D 23-now, E 09-22). A band replaces the live +-10pp only if it
beats it by >= 0.10 worst-window Calmar AND >= 1pp worst-window MaxDD.
Rebalances per year reported (turnover is a real cost of tighter bands).
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

START, TC, CASH_YLD = "2009-08-06", 0.0010, 0.02
RAW = {"AVGO": 0.20, "LLY": 0.20, "Gold": 0.20, "Index": 0.25, "Cash": 0.10}
TGT = {k: v / sum(RAW.values()) for k, v in RAW.items()}
BANDS = [("abs 5pp", "abs", 0.05), ("abs 7.5pp", "abs", 0.075), ("abs 10pp LIVE", "abs", 0.10),
         ("rel 25%", "rel", 0.25), ("rel 50%", "rel", 0.50)]
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


def simulate(px, kind, band):
    names = list(TGT)
    tgt = np.array([TGT[n] for n in names])
    width = np.full(len(tgt), band) if kind == "abs" else tgt * band
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
    print(f"{px.index[0].date()}..{px.index[-1].date()} SEK; targets {', '.join(f'{k} {v:.1%}' for k, v in TGT.items())}\n")
    rows = []
    for name, kind, band in BANDS:
        eq, n = simulate(px, kind, band)
        fc, fm, fcal = stats(eq)
        w = {k: stats(simulate(px.loc[a:b], kind, band)[0]) for k, (a, b) in WINDOWS.items()}
        rows.append({"name": name, "cagr": fc, "mdd": fm, "reb_yr": n / yrs,
                     "wmdd": min(x[1] for x in w.values()), "wcal": min(x[2] for x in w.values()),
                     "wwin": min(w, key=lambda k: w[k][2])})
    print(f"{'band':<15}{'CAGR':>7}{'MaxDD':>8}{'reb/yr':>8}{'worst MDD':>11}{'worst Cal':>11}  window")
    for r in rows:
        print(f"{r['name']:<15}{r['cagr']:>+7.1%}{r['mdd']:>+8.1%}{r['reb_yr']:>8.1f}"
              f"{r['wmdd']:>+11.1%}{r['wcal']:>11.2f}  {r['wwin']}")
    live = next(r for r in rows if "LIVE" in r["name"])
    best = max(rows, key=lambda r: r["wcal"])
    beats = best is not live and best["wcal"] - live["wcal"] >= 0.10 and best["wmdd"] - live["wmdd"] >= 0.01
    print(f"\nVERDICT (pre-registered): {'ADOPT ' + best['name'] if beats else 'abs 10pp STAYS -- no band clears the bar'}")


if __name__ == "__main__":
    main()
