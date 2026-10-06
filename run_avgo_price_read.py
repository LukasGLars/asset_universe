"""
run_avgo_price_read.py

TEMPORARY (2026-10-06). Raw price structure for AVGO. No thresholds, no
pass/fail, no triggers -- just the data needed to read the chart: weekly bars,
recent dailies, swing highs and lows, where the highs and lows actually sit,
volume, and the drawdown path.

Delete after reading.
"""
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

df = reader.load(reader.ticker_path(config.raw_data_dir(), "equities", "AVGO"))
cols = [c for c in ("open", "high", "low", "close", "volume") for _ in (0,)
        if c in df.columns]
df = df[cols].dropna(subset=["close"])
has_vol = "volume" in df.columns

print("=" * 74)
print(f"AVGO price structure -- through {df.index[-1].date()}")
print("=" * 74)

ath = df["close"].idxmax()
print(f"  all-time closing high : {df['close'].max():.2f}  ({ath.date()})")
y = df.loc[df.index[-1] - pd.Timedelta(days=365):]
print(f"  52w high close        : {y['close'].max():.2f}  ({y['close'].idxmax().date()})")
print(f"  52w low close         : {y['close'].min():.2f}  ({y['close'].idxmin().date()})")
print(f"  now                   : {df['close'].iloc[-1]:.2f}")
print(f"  from ATH              : {df['close'].iloc[-1]/df['close'].max()-1:+.1%}")

# ── weekly bars, last 2 years ────────────────────────────────────────────────
agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
if has_vol:
    agg["volume"] = "sum"
wk = df.resample("W-FRI").agg(agg).dropna(subset=["close"]).tail(78)
print("\n" + "-" * 74)
print("WEEKLY BARS (last 78 weeks)")
print("-" * 74)
hdr = f"  {'week end':<12}{'open':>9}{'high':>9}{'low':>9}{'close':>9}{'chg':>8}"
if has_vol:
    hdr += f"{'vol vs 13w':>12}"
print(hdr)
wk["chg"] = wk["close"].pct_change()
if has_vol:
    wk["volrel"] = wk["volume"] / wk["volume"].rolling(13).mean()
for d, r in wk.iterrows():
    line = (f"  {str(d.date()):<12}{r['open']:>9.2f}{r['high']:>9.2f}"
            f"{r['low']:>9.2f}{r['close']:>9.2f}")
    line += f"{r['chg']:>+8.1%}" if pd.notna(r["chg"]) else f"{'':>8}"
    if has_vol and pd.notna(r.get("volrel")):
        line += f"{r['volrel']:>11.2f}x"
    print(line)

# ── swing points on daily closes ─────────────────────────────────────────────
def swings(s: pd.Series, k: int = 10) -> list[tuple]:
    out = []
    v = s.to_numpy()
    for i in range(k, len(v) - k):
        w = v[i - k:i + k + 1]
        if v[i] == w.max():
            out.append((s.index[i], v[i], "HIGH"))
        elif v[i] == w.min():
            out.append((s.index[i], v[i], "LOW"))
    # collapse runs of the same kind, keeping the extreme
    merged: list[tuple] = []
    for p in out:
        if merged and merged[-1][2] == p[2]:
            better = max if p[2] == "HIGH" else min
            if better(p[1], merged[-1][1]) == p[1]:
                merged[-1] = p
        else:
            merged.append(p)
    return merged

d2 = df["close"].loc[df.index[-1] - pd.Timedelta(days=540):]
print("\n" + "-" * 74)
print("SWING POINTS (daily closes, 10-session pivots, last ~18 months)")
print("-" * 74)
sw = swings(d2, 10)
prev = None
for d, v, kind in sw:
    rel = ""
    if prev and prev[2] == kind:
        rel = f"   {'higher' if v > prev[1] else 'lower'} {kind.lower()}"
    print(f"  {str(d.date()):<12}{kind:<6}{v:>9.2f}{rel}")
    prev = (d, v, kind)

print("\n" + "-" * 74)
print("LAST 30 DAILY CLOSES")
print("-" * 74)
tail = df.tail(30)
print(f"  {'date':<12}{'open':>9}{'high':>9}{'low':>9}{'close':>9}{'chg':>8}"
      + (f"{'vol vs 50d':>12}" if has_vol else ""))
vol50 = df["volume"].rolling(50).mean() if has_vol else None
for d, r in tail.iterrows():
    line = (f"  {str(d.date()):<12}{r['open']:>9.2f}{r['high']:>9.2f}"
            f"{r['low']:>9.2f}{r['close']:>9.2f}"
            f"{df['close'].pct_change().loc[d]:>+8.1%}")
    if has_vol and pd.notna(vol50.loc[d]) and vol50.loc[d] > 0:
        line += f"{r['volume']/vol50.loc[d]:>11.2f}x"
    print(line)

print("\n" + "-" * 74)
print("DRAWDOWN PATH FROM THE ATH")
print("-" * 74)
dd = df["close"] / df["close"].cummax() - 1
post = dd.loc[ath:]
print(f"  ATH {ath.date()} at {df['close'].max():.2f}")
print(f"  deepest since         : {post.min():+.1%}  ({post.idxmin().date()})")
print(f"  current               : {post.iloc[-1]:+.1%}")
print(f"  sessions since ATH    : {len(post) - 1}")
mo = dd.loc[ath:].resample("ME").last()
print("  month-end drawdown since the ATH:")
for d, v in mo.items():
    print(f"    {d.date().strftime('%Y-%m')}  {v:+.1%}")
print("=" * 74)
