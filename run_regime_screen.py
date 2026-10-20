"""TEMPORARY (2026-10-20). Which names did well in today's high-rate regime?

Same method as run_rate_regime_validated.py (each regime spell vs the median
of all same-length windows in the asset's own history), applied to the whole
store: us_equities, fixed_income, commodities.

PRE-REGISTERED pass bar (LLY's): median excess > 0, beat baseline >= 75% of
spells, worst third of spells > 0.

PLACEBO: 8 spells x 500+ names means many pass by luck. The same test is run
on 200 sets of RANDOM spells (same lengths, random start dates). Expected
false passes = mean placebo pass count. Survivors are only interesting if the
real count clearly exceeds that. Delete after logging.
"""
from __future__ import annotations
import io, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)
sys.path.insert(0, str(Path(__file__).parent / "src"))
import numpy as np, pandas as pd
from asset_universe import config
from asset_universe.store import reader
from asset_universe.analysis import regimes as regime_module

BASE = {"ry_regime": "HIGH", "nominal_10y_regime": "HIGH", "baa10y_regime": "TIGHT", "usd_regime": "STRONG"}
U = Path(__file__).parent / "config" / "universes"
CATS = {"equities": "us_equities.txt", "fixed_income": "fixed_income.txt", "commodities": "commodities.txt"}
D = config.raw_data_dir()

lab, _ = regime_module.build(D)
mask = pd.Series(True, index=lab.index)
for k, v in BASE.items():
    mask &= lab[k] == v
spells, start, prev = [], None, None
for ts in lab.index[mask]:
    if start is None:
        start = prev = ts; continue
    if (ts - prev).days > 7:
        spells.append((start, prev)); start = ts
    prev = ts
spells.append((start, prev))

px = {}
for cat, f in CATS.items():
    for t in (l.strip() for l in (U / f).read_text().splitlines()):
        if not t or t.startswith("#"):
            continue
        p = reader.ticker_path(D, cat, t)
        if p.exists():
            s = reader.load(p)["close"].dropna()
            if len(s) > 1500:
                px[t] = s
cal = pd.DatetimeIndex(sorted(set().union(*[s.index for s in px.values()])))
cal = cal[cal >= "2005-01-01"]

def test(s, spl, cache):
    ex = []
    for a, b in spl:
        i, j = s.index.searchsorted(a), s.index.searchsorted(b)
        if i >= len(s) or j >= len(s) or j <= i:
            continue  # same as run_rate_regime_validated: skip, don't fail
        L = j - i
        if L not in cache:
            cache[L] = float((s.shift(-L) / s - 1).dropna().median())
        ex.append(float(s.iloc[j] / s.iloc[i] - 1) - cache[L])
    if len(ex) < 6:
        return None
    e = np.array(ex)
    tm = [np.median(e[t]) for t in np.array_split(np.arange(len(e)), 3)]
    return np.median(e), (e > 0).mean(), min(tm)

def passes(r):
    return r is not None and r[0] > 0 and r[1] >= 0.75 and r[2] > 0

caches = {t: {} for t in px}
real = {t: test(s, spells, caches[t]) for t, s in px.items()}
win = [t for t, r in real.items() if passes(r)]

rng = np.random.default_rng(0)
lens = [(b - a) for a, b in spells]
counts = []
for _ in range(200):
    st = rng.choice(len(cal) - 400, len(spells), replace=False)
    fake = [(cal[k], cal[k] + l) for k, l in zip(sorted(st), lens)]
    counts.append(sum(passes(test(s, fake, caches[t])) for t, s in px.items()))
counts = np.array(counts)

print(f"{len(spells)} spells {spells[0][0].date()}..{spells[-1][1].date()}, {len(px)} names tested")
print(f"PASS real: {len(win)}   placebo mean {counts.mean():.1f}, 95th pct {np.percentile(counts,95):.0f}")
print(f"Estimated share of passes that are luck: {min(1, counts.mean()/max(len(win),1)):.0%}\n")
print(f"{'name':<8}{'median ex':>10}{'beat':>6}{'worst 3rd':>11}")
for t in sorted(win, key=lambda t: -real[t][2])[:30]:
    m, b, w = real[t]
    print(f"{t:<8}{m:>+10.1%}{b:>6.0%}{w:>+11.1%}")
