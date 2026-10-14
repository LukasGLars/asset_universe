"""TEMPORARY (2026-10-14). What the semiconductor complex is doing right now.
Descriptive panel, no signals. Delete after reading."""
from __future__ import annotations

import io
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", write_through=True)

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.store import reader

SEMIS = ["NVDA", "AVGO", "AMD", "MU", "TXN", "QCOM", "INTC", "ADI", "AMAT",
         "LRCX", "KLAC", "MRVL", "NXPI", "MCHP", "ON", "SWKS", "TER", "MPWR",
         "SMCI", "WDC", "STX", "LITE"]
REF = ["SPY", "QQQ"]
DD = config.raw_data_dir()


def close(t):
    try:
        return reader.load(reader.ticker_path(DD, "equities", t))["close"].dropna()
    except Exception:
        return None


def roc(s, n):
    return None if len(s) <= n else float(s.iloc[-1] / s.iloc[-(n + 1)] - 1)


def f(v, w=8):
    return f"{'n/a':>{w}}" if v is None else f"{v:>+{w}.1%}"


series = {t: s for t in SEMIS + REF if (s := close(t)) is not None}
asof = max(s.index[-1] for s in series.values())

print("=" * 86)
print(f"SEMICONDUCTOR COMPLEX -- as of {asof.date()}")
print("=" * 86)
print(f"{'ticker':<8}{'last':>10}{'1d':>8}{'5d':>8}{'21d':>8}{'63d':>8}{'252d':>9}"
      f"{'vs200d':>9}{'from 52wk hi':>14}")

rows = []
for t, s in series.items():
    if s.index[-1] != asof:
        continue
    sma200 = float(s.iloc[-200:].mean()) if len(s) >= 200 else None
    hi = float(s.iloc[-252:].max()) if len(s) >= 252 else None
    rows.append({
        "t": t, "last": float(s.iloc[-1]),
        "d1": roc(s, 1), "d5": roc(s, 5), "d21": roc(s, 21),
        "d63": roc(s, 63), "d252": roc(s, 252),
        "vs200": (float(s.iloc[-1]) / sma200 - 1) if sma200 else None,
        "fromhi": (float(s.iloc[-1]) / hi - 1) if hi else None,
        "ref": t in REF,
    })

for r in sorted(rows, key=lambda r: (r["ref"], -(r["d5"] if r["d5"] is not None else -9))):
    mark = "  <-- ref" if r["ref"] else ""
    print(f"{r['t']:<8}{r['last']:>10,.2f}{f(r['d1'])}{f(r['d5'])}{f(r['d21'])}"
          f"{f(r['d63'])}{f(r['d252'],9)}{f(r['vs200'],9)}{f(r['fromhi'],14)}{mark}")

semis = [r for r in rows if not r["ref"]]
for h, k in (("1d", "d1"), ("5d", "d5"), ("21d", "d21"), ("63d", "d63")):
    v = [r[k] for r in semis if r[k] is not None]
    up = sum(1 for x in v if x > 0)
    print(f"\n  {h:>4}: median {np.median(v):+.1%}   {up}/{len(v)} advancing", end="")
print()
above = [r for r in semis if r["vs200"] is not None and r["vs200"] > 0]
print(f"\n  above 200d : {len(above)}/{len([r for r in semis if r['vs200'] is not None])}")
print("=" * 86)
