"""
run_crash_guard_validation.py

Validates the AVGO crash guard (CRASH_ROC_WINDOW/CRASH_ROC_THRESHOLD in
run_combined_system.py) against two datasets:

  1. AVGO's own history (2009-2026) -- confirms the crash guard doesn't
     hurt the already-validated strategy.
  2. A TXN analog: same Strategy D methodology (base + guard + silver),
     with TXN substituted for AVGO, run over TXN's full 2000-2026 history
     -- 25.8yr, including the 2001 dot-com crash and 2008 GFC, neither of
     which AVGO's own history (IPO 2009) was ever tested against. TXN is
     a diversified analog/embedded semicap, not an AI-ASIC company like
     AVGO -- this is sector-cyclicality evidence, not an AVGO-specific
     risk model.

Finding (2026-07-02): the 200d-SMA-only guard produced -35.3% MaxDD on the
TXN analog (worst trough: 2001-04-03, dot-com) despite being active --
a moving average can't react fast enough to a sharp break. The crash
guard (early activation on a fast drop, regardless of MA position) closed
most of that gap: -30.0% MaxDD at the validated parameters, with CAGR
*improved* on both datasets, not just risk reduced.

Output: parameter grid (Calmar) for both datasets, printed only -- no CSV,
this is a validation check to rerun when reconsidering the crash guard's
parameters, not a daily-automation script.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config

DATA_DIR = config.raw_data_dir()

GSR_T1, GSR_T2, GSR_EXIT = 83.36, 86.45, 62.56
GSR_PEAK_WINDOW, GSR_PEAK_FALL = 60, 0.05
TC = 0.0010
AVGO_MA = 200

WEIGHTS: dict[tuple[bool, str], dict[str, float]] = {
    (False, "INACTIVE"): {"G": 0.250, "X": 0.550, "L": 0.200, "S": 0.000},
    (False, "T1"):       {"G": 0.250, "X": 0.430, "L": 0.200, "S": 0.120},
    (False, "T2"):       {"G": 0.250, "X": 0.380, "L": 0.200, "S": 0.170},
    (True,  "INACTIVE"): {"G": 0.525, "X": 0.000, "L": 0.475, "S": 0.000},
    (True,  "T1"):       {"G": 0.405, "X": 0.000, "L": 0.475, "S": 0.120},
    (True,  "T2"):       {"G": 0.355, "X": 0.000, "L": 0.475, "S": 0.170},
}

WINDOWS    = [3, 5, 10, 15]
THRESHOLDS = [-0.10, -0.12, -0.15, -0.18, -0.20]


def load(category: str, stem: str) -> pd.Series:
    df = pd.read_parquet(DATA_DIR / category / f"{stem}.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index().dropna()


def perf(equity: pd.Series) -> dict:
    r = equity.pct_change().dropna()
    yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = float(equity.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 else 0.0
    dd = equity / equity.cummax() - 1
    maxdd = float(dd.min())
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
    calmar = cagr / abs(maxdd) if maxdd != 0 else 0.0
    return {"cagr": cagr, "sharpe": sharpe, "maxdd": maxdd, "calmar": calmar,
            "years": yrs, "worst_date": dd.idxmin()}


def run(x_series: pd.Series, gold: pd.Series, lly: pd.Series, silver: pd.Series,
        start: pd.Timestamp, roc_window: int | None = None,
        roc_threshold: float | None = None) -> pd.Series:
    common = (gold.index.intersection(x_series.index)
              .intersection(lly.index).intersection(silver.index))
    common = common[common >= start].sort_values()

    x_r = x_series.reindex(common)
    sma = x_r.rolling(AVGO_MA).mean()
    ma_guard = (x_r < sma).fillna(False)

    if roc_window and roc_threshold:
        roc = x_r.pct_change(roc_window)
        roc_guard = (roc <= roc_threshold).fillna(False)
        guard = ma_guard | roc_guard
    else:
        guard = ma_guard

    gsr = (gold.reindex(common) / silver.reindex(common)).dropna().reindex(common)
    peak = gsr.rolling(GSR_PEAK_WINDOW).max()
    fall = (peak - gsr) / peak.replace(0, np.nan)

    states, state = [], "INACTIVE"
    for i in range(len(common)):
        gv = gsr.iloc[i]
        fv = fall.iloc[i] if not pd.isna(fall.iloc[i]) else 0.0
        if pd.isna(gv):
            states.append(state)
            continue
        if state in ("T1", "T2") and gv < GSR_EXIT:
            state = "INACTIVE"
        if state == "INACTIVE":
            fallen = fv >= GSR_PEAK_FALL
            if gv >= GSR_T2 and fallen:
                state = "T2"
            elif gv >= GSR_T1 and fallen:
                state = "T1"
        states.append(state)

    prices = {"G": gold, "X": x_r, "L": lly, "S": silver}
    rets = {k: v.reindex(common).pct_change() for k, v in prices.items()}
    port = pd.Series(0.0, index=common)
    prev = None
    for i, _date in enumerate(common):
        g, s = bool(guard.iloc[i]), states[i]
        w = WEIGHTS[(g, s)]
        if prev is not None and w != prev:
            cost = sum(TC for a in set(list(w) + list(prev))
                       if abs(w.get(a, 0) - prev.get(a, 0)) > 0.005)
            port.iloc[i] -= cost
        r = sum(wt * (rets[a].iloc[i] if not pd.isna(rets[a].iloc[i]) else 0.0)
                for a, wt in w.items())
        port.iloc[i] += r
        prev = w
    return (1 + port).cumprod()


def main() -> None:
    gold = load("commodities", "GC_F")
    silver = load("commodities", "SI_F")
    lly = load("equities", "LLY")
    avgo = load("equities", "AVGO")
    txn = load("equities", "TXN")

    datasets = [
        ("AVGO actual", avgo, pd.Timestamp("2009-08-06")),
        ("TXN analog (includes 2001, 2008)", txn, pd.Timestamp("2000-08-30")),
    ]

    for label, series, start in datasets:
        print("=" * 90)
        print(f"{label}")
        print("=" * 90)

        base_eq = run(series, gold, lly, silver, start)
        base = perf(base_eq)
        print(f"Baseline (200d SMA only): CAGR {base['cagr']:+.1%}  "
              f"MaxDD {base['maxdd']:+.1%}  Calmar {base['calmar']:.3f}  "
              f"worst trough: {base['worst_date'].date()}")

        # Validated default (CRASH_ROC_WINDOW=5, CRASH_ROC_THRESHOLD=-0.10)
        crash_eq = run(series, gold, lly, silver, start, 5, -0.10)
        crash = perf(crash_eq)
        print(f"+ Crash guard (5d/-10%):  CAGR {crash['cagr']:+.1%}  "
              f"MaxDD {crash['maxdd']:+.1%}  Calmar {crash['calmar']:.3f}  "
              f"worst trough: {crash['worst_date'].date()}")
        print()

        print("Calmar grid, rows=window(days), cols=threshold:")
        rows = []
        for w in WINDOWS:
            row = {"window": w}
            for t in THRESHOLDS:
                p = perf(run(series, gold, lly, silver, start, w, t))
                row[f"{t:.0%}"] = round(p["calmar"], 3)
            rows.append(row)
        grid = pd.DataFrame(rows).set_index("window")
        print(grid.to_string())
        print()


if __name__ == "__main__":
    main()
