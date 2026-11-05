"""TEMPORARY (2026-11-05). Rerun of the 2026-08-14 gap-down event study
against TODAY's mix.

Events: AVGO 5-session return <= -10%, declustered (>= 21 sessions apart),
2009-2026. Buy at the NEXT session's close (no lookahead). Compare forward
returns of:
  A  new money into AVGO
  M  the same money into today's mix: AVGO 20 / LLY 20 / Gold 20 /
     Index 30 (SPY proxy) / Cash 10 (2%/yr), bought at the same close
     and held (no rebalance inside the horizon)
All in SEK. Horizons 21/63/126/252 sessions. Report-only: the crash plan is
already decided; this updates the evidence quoted for it. Delete after logging.
"""
from __future__ import annotations
import io, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)
sys.path.insert(0, str(Path(__file__).parent / "src"))
import numpy as np, pandas as pd
from asset_universe import config
from asset_universe.store import reader

MIX = {"AVGO": 0.20, "LLY": 0.20, "Gold": 0.20, "Index": 0.30, "Cash": 0.10}
H = (21, 63, 126, 252)


def _c(cat, t):
    return reader.load(reader.ticker_path(config.raw_data_dir(), cat, t))["close"]


def prices():
    fx = _c("fx", "USDSEK=X")
    df = pd.DataFrame({"AVGO": _c("equities", "AVGO"), "LLY": _c("equities", "LLY"),
                       "Gold": _c("commodities", "GC=F"), "Index": _c("equities", "SPY")}).loc["2009-08-06":]
    df = df.ffill(limit=3).mul(fx.reindex(df.index).ffill(), axis=0).dropna()
    df["Cash"] = 1.02 ** (np.arange(len(df)) / 252)
    return df


def events(avgo: pd.Series) -> list[int]:
    roc = avgo / avgo.shift(5) - 1
    out, last = [], -10**9
    for i, r in enumerate(roc.to_numpy()):
        if r <= -0.10 and i - last >= 21:
            out.append(i)
            last = i
    return out


def main():
    px = prices()
    ev = events(px["AVGO"])
    print(f"{len(ev)} declustered triggers, {px.index[ev[0]].date()}..{px.index[ev[-1]].date()} (SEK)\n")
    p = px.to_numpy()
    cols = list(px.columns)
    w = np.array([MIX[c] for c in cols])
    print(f"{'horizon':<9}{'n':>4}{'AVGO med':>10}{'mix med':>9}{'AVGO>mix':>10}{'AVGO worst':>12}{'mix worst':>11}")
    for h in H:
        a, m = [], []
        for i in ev:
            b = i + 1  # buy next session's close
            if b + h >= len(p):
                continue
            a.append(p[b + h, cols.index("AVGO")] / p[b, cols.index("AVGO")] - 1)
            m.append(float((w * p[b + h] / p[b]).sum() - 1))
        a, m = np.array(a), np.array(m)
        print(f"{h:>4}d    {len(a):>4}{np.median(a):>+10.1%}{np.median(m):>+9.1%}{(a > m).mean():>10.0%}"
              f"{a.min():>+12.1%}{m.min():>+11.1%}")


if __name__ == "__main__":
    main()
