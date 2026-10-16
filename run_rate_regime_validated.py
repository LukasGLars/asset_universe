"""TEMPORARY (2026-10-16). How do the holdings actually fare in today's
high-rate regime -- measured to this project's standard rather than as a bare
conditional average.

Today's regime: ry=HIGH, nominal_10y=HIGH, baa10y=TIGHT, usd=STRONG.

Two things the bare query was missing:

  CONTROL. "Gold returned +5% in this regime" is meaningless without knowing
  what gold returns over an equivalent window picked at random. Each spell is
  compared against the median of ALL same-length windows in that asset's own
  history, so the reported number is EXCESS over the length-matched baseline.

  SUB-PERIODS. Eleven spells pooled can hide a single regime carrying the
  whole result -- the failure mode that killed the SAAB beta and that this
  repo's CLAUDE.md names explicitly. Ranked on the worst third.

Spells overlap nothing (they are disjoint by construction) but there are only
11 of them, which bounds how much any of this can carry.

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
from asset_universe.analysis import regimes as regime_module

BASE = {"ry_regime": "HIGH", "nominal_10y_regime": "HIGH",
        "baa10y_regime": "TIGHT", "usd_regime": "STRONG"}
ASSETS = [("Gold", "commodities", "GC=F"), ("LLY", "equities", "LLY"),
          ("AVGO", "equities", "AVGO"), ("SPY", "equities", "SPY")]

lab, _ = regime_module.build(config.raw_data_dir())
mask = pd.Series(True, index=lab.index)
for k, v in BASE.items():
    mask &= lab[k] == v
d = lab.index[mask]

spells, start, prev = [], None, None
for ts in d:
    if start is None:
        start = prev = ts; continue
    if (ts - prev).days > 7:
        spells.append((start, prev)); start = ts
    prev = ts
if start is not None:
    spells.append((start, prev))

print("=" * 78)
print("HOLDINGS IN TODAY'S HIGH-RATE REGIME -- excess over a length-matched baseline")
print("=" * 78)
print(f"regime: {BASE}")
print(f"{len(spells)} disjoint spells, {spells[0][0].date()} to {spells[-1][1].date()}\n")

results = {}
for name, cat, tick in ASSETS:
    px = reader.load(reader.ticker_path(config.raw_data_dir(), cat, tick))["close"].dropna()
    rows = []
    for a, b in spells:
        i, j = px.index.searchsorted(a), px.index.searchsorted(b)
        if i >= len(px) or j >= len(px) or j <= i:
            continue
        L = j - i
        actual = float(px.iloc[j] / px.iloc[i] - 1)
        # Every L-length window in this asset's own history.
        win = (px.shift(-L) / px - 1).dropna()
        rows.append({"start": a.date(), "L": L, "actual": actual,
                     "base": float(win.median()),
                     "excess": actual - float(win.median()),
                     "pctile": float((win < actual).mean())})
    results[name] = pd.DataFrame(rows)

for name, df in results.items():
    if df.empty:
        print(f"{name}: no overlapping history\n"); continue
    e = df["excess"]
    thirds = np.array_split(np.arange(len(df)), 3)
    tm = [float(e.iloc[list(t)].median()) for t in thirds if len(t)]
    print(f"{name:<6} spells={len(df):>2}  "
          f"median excess {e.median():>+7.2%}   mean {e.mean():>+7.2%}   "
          f"beat baseline {float((e>0).mean()):>4.0%}")
    print(f"       thirds " + "  ".join(f"{x:+.2%}" for x in tm)
          + f"   WORST THIRD {min(tm):+.2%}")
    print(f"       median spell length {int(df['L'].median())} sessions, "
          f"raw return {df['actual'].median():+.2%} vs baseline {df['base'].median():+.2%}")
    print()

print("-" * 78)
print("PER SPELL (excess over the same-length baseline)")
print("-" * 78)
hdr = f"{'start':<12}{'len':>5}" + "".join(f"{n:>10}" for n in results)
print(hdr)
ref = next(df for df in results.values() if not df.empty)
for i in range(len(ref)):
    line = f"{str(ref['start'].iloc[i]):<12}{ref['L'].iloc[i]:>5}"
    for n, df in results.items():
        line += f"{df['excess'].iloc[i]:>+10.2%}" if i < len(df) else f"{'--':>10}"
    print(line)
print("=" * 78)
