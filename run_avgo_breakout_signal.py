"""
run_avgo_breakout_signal.py

TEMPORARY diagnostic (2026-10-06). Does a volume-confirmed breakout above
recent resistance mark a point worth OVERWEIGHTING AVGO?

The operator specified the shape: price clears the resistance it has been
capped by, on volume above its own average. This operationalises that with
the minimum number of choices and tests it against the bar that matters.

That bar is NOT "did it go up". AVGO is already held at a 20% target, so a
signal to overweight has to beat simply continuing to hold -- the
unconditional forward return from a random session. The retired
opportunistic sleeve died on exactly this comparison, which is why it is
the primary column here.

Signal, at session i:
  - resistance = highest close over the prior LOOKBACK sessions, EXCLUDING i
  - breakout   = close[i] > that resistance
  - volume     = volume[i] / its own trailing 50-session mean >= VOL_MIN
  - entry at close(i+1); the signal bar is never the fill
  - declustered DECLUSTER sessions apart

VOL_MIN = 0 is the control: it isolates whether the volume filter adds
anything over the breakout alone. If it does not, volume is decoration.

PRE-COMMITTED KILL CRITERIA, written before any output was seen:
  1. majority of date-thirds beat the unconditional AVGO baseline at 63d
  2. the volume filter adds >= +1pp median over VOL_MIN=0 at 63d
  3. date-matched excess vs SPY positive at 63d
Fail any one and there is no signal. No threshold hunting afterwards.

Read-only. Delete script, tests and workflow once logged to MEMORY.md.
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", write_through=True)
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.store import reader

DATA_DIR   = config.raw_data_dir()
LOOKBACKS  = [20, 40, 60]
VOL_MINS   = [0.0, 1.0, 1.25, 1.5, 2.0]
VOL_WINDOW = 50
DECLUSTER  = 21
HORIZONS   = [21, 63, 126, 252]
MIN_N      = 5
PRIMARY_H  = 63


def load(ticker: str, category: str = "equities") -> pd.DataFrame:
    df = reader.load(reader.ticker_path(DATA_DIR, category, ticker))
    keep = [c for c in ("close", "volume") if c in df.columns]
    return df[keep].dropna(subset=["close"])


def vol_ratio(volume: pd.Series) -> pd.Series:
    """volume vs its own trailing mean, the bar itself EXCLUDED from the mean
    (otherwise a huge bar inflates its own benchmark and the ratio is damped)."""
    trailing = volume.shift(1).rolling(VOL_WINDOW).mean()
    return volume / trailing


def signals(df: pd.DataFrame, lookback: int, vol_min: float) -> list[int]:
    close = df["close"]
    # shift(1) so the current bar is excluded from its own resistance level
    resistance = close.shift(1).rolling(lookback).max()
    broke = (close > resistance).fillna(False).to_numpy()
    if vol_min > 0 and "volume" in df.columns:
        vr = vol_ratio(df["volume"])
        ok = (vr >= vol_min).fillna(False).to_numpy()
        broke = broke & ok
    raw = np.flatnonzero(broke)
    kept: list[int] = []
    for i in raw:
        if not kept or (i - kept[-1]) >= DECLUSTER:
            kept.append(int(i))
    return kept


def fwd(close: pd.Series, i: int, h: int) -> float | None:
    a, b = i + 1, i + 1 + h
    if b >= len(close):
        return None
    return float(close.iloc[b] / close.iloc[a] - 1.0)


def baseline(close: pd.Series) -> dict[int, float]:
    out = {}
    for h in HORIZONS:
        r = [v for i in range(len(close)) if (v := fwd(close, i, h)) is not None]
        out[h] = float(pd.Series(r).median())
    return out


def main() -> None:
    avgo = load("AVGO")
    spy = load("SPY")
    common = avgo.index.intersection(spy.index)
    avgo, spy = avgo.loc[common], spy.loc[common]
    ac, sc = avgo["close"], spy["close"]
    base = baseline(ac)

    print("=" * 84)
    print("AVGO volume-confirmed breakout -- is this an OVERWEIGHT signal?")
    print("=" * 84)
    print(f"Window: {ac.index[0].date()} to {ac.index[-1].date()} ({len(ac)} sessions)")
    print(f"Volume column present: {'volume' in avgo.columns}")
    print(f"Decluster: {DECLUSTER} sessions   Entry: close(signal+1)")
    print("\nUnconditional AVGO baseline (median forward return, any session):")
    print("  " + "   ".join(f"{h}d {base[h]:+.1%}" for h in HORIZONS))
    print("\n  This is the bar. AVGO is already held at target, so a breakout")
    print("  must beat HOLDING, not merely be positive.")

    rows = []
    for lb in LOOKBACKS:
        for vm in VOL_MINS:
            sig = signals(avgo, lb, vm)
            rec = {"lookback": lb, "vol_min": vm, "n_signals": len(sig)}
            for h in HORIZONS:
                r, ex = [], []
                for i in sig:
                    a = fwd(ac, i, h)
                    b = fwd(sc, i, h)
                    if a is None or b is None:
                        continue
                    r.append(a); ex.append(a - b)
                if len(r) < MIN_N:
                    rec[f"med_{h}"] = None
                    rec[f"vsbase_{h}"] = None
                    rec[f"vsspy_{h}"] = None
                    continue
                s = pd.Series(r)
                rec[f"n_{h}"] = len(r)
                rec[f"med_{h}"] = float(s.median())
                rec[f"vsbase_{h}"] = float(s.median() - base[h])
                rec[f"vsspy_{h}"] = float(pd.Series(ex).median())
            rows.append(rec)
    res = pd.DataFrame(rows)

    print("\n" + "-" * 84)
    print("EDGE OVER HOLDING (median breakout return minus unconditional baseline)")
    print("-" * 84)
    disp = res[["lookback", "vol_min", "n_signals"] + [f"vsbase_{h}" for h in HORIZONS]].copy()
    for h in HORIZONS:
        disp[f"vsbase_{h}"] = disp[f"vsbase_{h}"].map(
            lambda v: "   n/a" if v is None or pd.isna(v) else f"{v:+.1%}")
    print(disp.to_string(index=False))

    print("\n" + "-" * 84)
    print("DATE-MATCHED EXCESS vs SPY")
    print("-" * 84)
    disp2 = res[["lookback", "vol_min", "n_signals"] + [f"vsspy_{h}" for h in HORIZONS]].copy()
    for h in HORIZONS:
        disp2[f"vsspy_{h}"] = disp2[f"vsspy_{h}"].map(
            lambda v: "   n/a" if v is None or pd.isna(v) else f"{v:+.1%}")
    print(disp2.to_string(index=False))

    # ── criterion 2: does volume add anything? ────────────────────────────
    print("\n" + "-" * 84)
    print(f"CRITERION 2 -- does the volume filter add over no filter, at {PRIMARY_H}d?")
    print("-" * 84)
    vol_adds = {}
    for lb in LOOKBACKS:
        ctrl = res[(res.lookback == lb) & (res.vol_min == 0.0)][f"med_{PRIMARY_H}"]
        c = float(ctrl.iloc[0]) if len(ctrl) and ctrl.iloc[0] is not None else np.nan
        for vm in VOL_MINS:
            if vm == 0.0:
                continue
            cell = res[(res.lookback == lb) & (res.vol_min == vm)][f"med_{PRIMARY_H}"]
            v = float(cell.iloc[0]) if len(cell) and cell.iloc[0] is not None else np.nan
            if not np.isnan(c) and not np.isnan(v):
                vol_adds[(lb, vm)] = v - c
                print(f"  lookback {lb:>3}  vol>={vm:<5} : {v:+.1%} vs no-filter "
                      f"{c:+.1%}   adds {v - c:+.1%}")
    best_add = max(vol_adds.values()) if vol_adds else float("nan")

    # ── pick the cell to sub-period: best edge over holding at 63d ────────
    cand = res.dropna(subset=[f"vsbase_{PRIMARY_H}"])
    cand = cand[cand["vol_min"] > 0]
    if cand.empty:
        print("\nNo cell with enough observations. VERDICT: NO SIGNAL.")
        return
    best = cand.loc[cand[f"vsbase_{PRIMARY_H}"].idxmax()]
    lb, vm = int(best["lookback"]), float(best["vol_min"])
    print(f"\n  best cell on edge-over-holding at {PRIMARY_H}d: "
          f"lookback {lb}, vol >= {vm}")

    print("\n" + "-" * 84)
    print(f"CRITERION 1 -- SUB-PERIODS, lookback {lb} / vol >= {vm}, vs holding")
    print("-" * 84)
    sig = signals(avgo, lb, vm)
    recs = []
    for i in sig:
        a = fwd(ac, i, PRIMARY_H)
        b = fwd(sc, i, PRIMARY_H)
        if a is None or b is None:
            continue
        recs.append((ac.index[i], a, a - b))
    thirds = np.array_split(np.arange(len(recs)), 3)
    beat = 0
    n_thirds = 0
    for t in thirds:
        if not len(t):
            continue
        n_thirds += 1
        sub = [recs[k] for k in t]
        med = float(np.median([a for _, a, _ in sub]))
        exs = float(np.median([e for _, _, e in sub]))
        edge = med - base[PRIMARY_H]
        if edge > 0:
            beat += 1
        print(f"  {sub[0][0].date()} to {sub[-1][0].date()}  n={len(sub):3d}  "
              f"median {med:+7.1%}  vs holding {edge:+7.1%}  vs SPY {exs:+7.1%}")

    spy_ex = float(np.median([e for _, _, e in recs])) if recs else float("nan")

    print("\n" + "=" * 84)
    print("VERDICT against the pre-committed criteria")
    print("=" * 84)
    c1 = n_thirds > 0 and beat > n_thirds / 2
    c2 = (not np.isnan(best_add)) and best_add >= 0.01
    c3 = (not np.isnan(spy_ex)) and spy_ex > 0
    print(f"  1. majority of thirds beat holding at {PRIMARY_H}d : "
          f"{beat}/{n_thirds}  {'PASS' if c1 else 'FAIL'}")
    print(f"  2. volume filter adds >= +1pp over no filter   : "
          f"{best_add:+.1%}  {'PASS' if c2 else 'FAIL'}")
    print(f"  3. date-matched excess vs SPY positive         : "
          f"{spy_ex:+.1%}  {'PASS' if c3 else 'FAIL'}")
    print(f"\n  VERDICT: {'SIGNAL' if (c1 and c2 and c3) else 'NO SIGNAL'}")
    print("\n  Bound: AVGO's history is 2009-2026, one long semiconductor bull")
    print("  market with no 2000-02 analogue, and breakouts cluster in uptrends,")
    print("  so declustered episodes still overlap. A pass here would be")
    print("  suggestive, not settled.")
    print("=" * 84)


if __name__ == "__main__":
    main()
