"""
run_hood_technicals.py

TEMPORARY diagnostic (2026-10-06). Descriptive technical read on HOOD, with
SPY and the current Core names as reference columns so "strong" means strong
against something rather than in isolation.

Descriptive only. This project has repeatedly tested technical entry gates and
retired all of them -- the opportunistic sleeve's four gates were never better
than random entry, and trend-following SPY/QQQ/GLD/SLV/USO is on the do-not-
retest list. Nothing here is a signal; it is a snapshot.

Delete script, tests and workflow once read.
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

DATA_DIR = config.raw_data_dir()
NAMES = [("HOOD", "equities"), ("SPY", "equities"), ("AVGO", "equities"),
         ("LLY", "equities")]
BENCH = "SPY"


def closes(ticker: str, category: str) -> pd.Series:
    return reader.load(reader.ticker_path(DATA_DIR, category, ticker))["close"].dropna()


def rsi(s: pd.Series, window: int = 14) -> float:
    """Wilder's RSI on closes. Wilder smoothing = EWM with alpha 1/window."""
    d = s.diff().dropna()
    gain = d.clip(lower=0).ewm(alpha=1 / window, adjust=False).mean()
    loss = (-d.clip(upper=0)).ewm(alpha=1 / window, adjust=False).mean()
    last_loss = float(loss.iloc[-1])
    if last_loss == 0:
        return 100.0
    rs = float(gain.iloc[-1]) / last_loss
    return 100.0 - 100.0 / (1.0 + rs)


def roc(s: pd.Series, n: int) -> float | None:
    if len(s) <= n:
        return None
    return float(s.iloc[-1] / s.iloc[-(n + 1)] - 1)


def pct_of_range(s: pd.Series, window: int = 252) -> tuple[float, float, float, float]:
    w = s.iloc[-window:]
    lo, hi, last = float(w.min()), float(w.max()), float(s.iloc[-1])
    pos = (last - lo) / (hi - lo) if hi > lo else float("nan")
    return lo, hi, pos, last / hi - 1.0


def realised_vol(s: pd.Series, window: int = 60) -> float:
    r = s.pct_change().dropna().iloc[-window:]
    return float(r.std() * np.sqrt(252))


def fmt(v, pct=True, width=8):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return f"{'n/a':>{width}}"
    return f"{v:>+{width}.1%}" if pct else f"{v:>{width}.1f}"


def main() -> None:
    series = {t: closes(t, c) for t, c in NAMES}
    bench = series[BENCH]

    print("=" * 74)
    print("HOOD -- technical snapshot (descriptive, not a signal)")
    print("=" * 74)
    for t, s in series.items():
        print(f"  {t:5s} {s.index[0].date()} to {s.index[-1].date()}  "
              f"({len(s)} sessions)  last {s.iloc[-1]:.2f}")

    print("\n" + "-" * 74)
    print("TREND -- close vs moving average (+ = above)")
    print("-" * 74)
    print(f"{'ticker':<8}{'50d':>10}{'100d':>10}{'200d':>10}{'200d slope 21d':>18}")
    for t, s in series.items():
        row = f"{t:<8}"
        for w in (50, 100, 200):
            if len(s) >= w:
                sma = float(s.iloc[-w:].mean())
                row += fmt(float(s.iloc[-1]) / sma - 1, width=10)
            else:
                row += f"{'n/a':>10}"
        if len(s) >= 221:
            sma_now = float(s.iloc[-200:].mean())
            sma_then = float(s.iloc[-221:-21].mean())
            row += fmt(sma_now / sma_then - 1, width=18)
        else:
            row += f"{'n/a':>18}"
        print(row)

    print("\n" + "-" * 74)
    print("MOMENTUM -- trailing returns")
    print("-" * 74)
    print(f"{'ticker':<8}{'5d':>10}{'21d':>10}{'63d':>10}{'252d':>10}")
    for t, s in series.items():
        print(f"{t:<8}" + "".join(fmt(roc(s, n), width=10) for n in (5, 21, 63, 252)))

    print("\n" + "-" * 74)
    print("POSITION & RISK")
    print("-" * 74)
    print(f"{'ticker':<8}{'RSI14':>8}{'52w pos':>10}{'from hi':>10}{'60d vol':>10}")
    for t, s in series.items():
        _, _, pos, from_hi = pct_of_range(s)
        print(f"{t:<8}{rsi(s):>8.0f}{fmt(pos, width=10)}{fmt(from_hi, width=10)}"
              f"{fmt(realised_vol(s), width=10)}")

    print("\n" + "-" * 74)
    print(f"RELATIVE STRENGTH vs {BENCH} (ratio change, + = outperforming)")
    print("-" * 74)
    print(f"{'ticker':<8}{'21d':>10}{'63d':>10}{'252d':>10}")
    for t, s in series.items():
        if t == BENCH:
            continue
        common = s.index.intersection(bench.index)
        ratio = s.reindex(common) / bench.reindex(common)
        print(f"{t:<8}" + "".join(fmt(roc(ratio, n), width=10) for n in (21, 63, 252)))

    h = series["HOOD"]
    print("\n" + "-" * 74)
    print("HOOD drawdown history (peak-to-trough, full listing)")
    print("-" * 74)
    dd = h / h.cummax() - 1
    print(f"  max drawdown     : {float(dd.min()):+.1%}  "
          f"(trough {dd.idxmin().date()})")
    print(f"  current drawdown : {float(dd.iloc[-1]):+.1%}")
    print(f"  listed since     : {h.index[0].date()} "
          f"({(h.index[-1] - h.index[0]).days / 365.25:.1f} yr)")

    print("\n" + "=" * 74)
    print("Read this as description only. Every technical entry gate this")
    print("project has tested was no better than random entry, and HOOD's")
    print("history is short -- it has not traded through a full cycle.")
    print("=" * 74)


if __name__ == "__main__":
    main()
