"""TEMPORARY (2026-10-27). What tends to precede oil gains?

PRE-REGISTERED, before the run. Four hypotheses, each with an economic
reason, read at month ends; outcome = oil (CL=F) return over the next 126
sessions (~6 months):
  H1 deep drawdown   : oil <= 60% of its trailing 252d high (supply cuts follow)
  H2 dollar falling  : broad dollar (DTWEXBGS) down over the prior 126d
  H3 real yld falling: 10Y real yield (DFII10) down over the prior 126d
  H4 copper rising   : copper (HG=F) up over the prior 126d (global demand)
Pass, per hypothesis: median 6m oil return when ON beats OFF by >= 5pp, ON
beats OFF in all three sub-periods (2003-09, 2010-16, 2017-now), and a
CIRCULAR-SHIFT placebo (preserves the signal's autocorrelation) gives
p < 0.0125 (0.05 / 4 hypotheses).
Not testable here: the futures-curve shape (backwardation), the predictor
the literature rates best -- the store has no term-structure data.
Also prints the big rallies (6m forward > +40%) with each signal's state.
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

D = config.raw_data_dir()
H, PERIODS = 126, {"2003-09": (2003, 2009), "2010-16": (2010, 2016), "2017-now": (2017, 2100)}

def px(cat, t, col="close"):
    df = reader.load(reader.ticker_path(D, cat, t))
    return df[col].dropna().sort_index()

oil = px("commodities", "CL=F")
oil = oil[oil > 1]
cu = px("commodities", "HG=F")
usd = px("macro", "DTWEXBGS", "value")
ry = px("macro", "DFII10", "value")

me = oil.groupby(oil.index.to_period("M")).tail(1).index
me = me[me >= "2003-01-01"]
pos = oil.index.get_indexer(me)
fwd = pd.Series([oil.iloc[i + H] / oil.iloc[i] - 1 if i + H < len(oil) else np.nan for i in pos], index=me)

def at(s, d):
    s = s.loc[:d]
    return s.iloc[-1] if len(s) else np.nan

def chg(s, d, lag_days=182, pct=True):
    a, b = at(s, d), at(s, d - pd.Timedelta(days=lag_days))
    return (a / b - 1) if pct else (a - b)

sig = pd.DataFrame(index=me)
sig["H1 drawdown"] = [at(oil, d) <= 0.6 * oil.loc[d - pd.Timedelta(days=365):d].max() for d in me]
sig["H2 dollar down"] = [chg(usd, d) < 0 for d in me]
sig["H3 real yld down"] = [chg(ry, d, pct=False) < 0 for d in me]
sig["H4 copper up"] = [chg(cu, d) > 0 for d in me]
df = sig.assign(fwd=fwd).dropna(subset=["fwd"])
print(f"{len(df)} month-ends {df.index[0].date()}..{df.index[-1].date()}, "
      f"unconditional median 6m oil {df.fwd.median():+.1%}\n")

rng = np.random.default_rng(0)
for h in sig.columns:
    on, off = df.loc[df[h], "fwd"], df.loc[~df[h], "fwd"]
    edge = on.median() - off.median()
    s = df[h].to_numpy()
    null = []
    for _ in range(2000):
        k = rng.integers(12, len(s) - 12)
        sh = np.roll(s, k)
        null.append(np.median(df.fwd[sh]) - np.median(df.fwd[~sh]) if sh.any() and (~sh).any() else 0)
    p = float((np.array(null) >= edge).mean())
    subs = []
    for name, (a, b) in PERIODS.items():
        x = df[(df.index.year >= a) & (df.index.year <= b)]
        o, f = x.loc[x[h], "fwd"], x.loc[~x[h], "fwd"]
        subs.append((name, len(o), o.median() - f.median() if len(o) and len(f) else np.nan))
    sub_ok = all(e > 0 for _, n, e in subs if not np.isnan(e))
    ok = edge >= 0.05 and sub_ok and p < 0.0125
    print(f"{h:<17} ON n={len(on):3d} {on.median():+6.1%}  OFF {off.median():+6.1%}  edge {edge:+6.1%}  "
          f"p={p:.3f}  {'PASS' if ok else 'fail'}")
    print("                  " + "  ".join(f"{n} n={k} {e:+.1%}" for n, k, e in subs))

print("\nBig rallies (6m forward > +40%), start month and signal state:")
big = df[df.fwd > 0.40]
for d, r in big.iterrows():
    print(f"  {d:%Y-%m}  {r.fwd:+5.0%}  " + "  ".join(f"{h.split()[0]}={'Y' if r[h] else '.'}" for h in sig.columns))
