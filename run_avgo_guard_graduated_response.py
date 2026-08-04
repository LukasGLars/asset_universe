"""
run_avgo_guard_graduated_response.py -- diagnostic, delete after use.

Follow-up to "AVGO crash-ROC guard: basket crashes bounce HARDER than
solo" (MEMORY.md, 2026-08-04): that finding supported modeling a
graduated response before touching the live guard. This is that model.

Change under test: the crash-ROC trigger (5d ROC <=-10%) currently flips
AVGO's weight straight to 0% (full rotation) regardless of whether the
crash is solo or basket-confirmed (>=2 same-sector semiconductor peers
also crashing). This tests a GRADUATED response: basket-confirmed crash-
ROC triggers get a partial rotation (AVGO weight reduced by a fraction of
the full flip, not to zero); solo crash-ROC triggers and the slower 200d
MA guard are left exactly as validated (full flip, unchanged) -- this
targets ONLY the specific scenario the finding was about.

Method: extends run_crash_guard_validation.py's Strategy D (base + guard
+ silver GSR) with a third guard state, BASKET, whose weights are a
linear interpolation between NONE and FULL by ROTATION_FRACTION (0.0 =
ignore the crash-ROC trigger entirely on a basket day, 1.0 = identical to
today's full flip). Grid over ROTATION_FRACTION, same Sharpe/MaxDD/Calmar
comparison the original guard was validated on.

Report-only. No gate, display flag, or live guard change made or implied
by running this script.
"""
from __future__ import annotations
import sys, io, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import pandas as pd

from asset_universe import config

DATA_DIR = config.raw_data_dir()

GSR_T1, GSR_T2, GSR_EXIT = 83.36, 86.45, 62.56
GSR_PEAK_WINDOW, GSR_PEAK_FALL = 60, 0.05
TC = 0.0010
AVGO_MA = 200
CRASH_ROC_WINDOW, CRASH_ROC_THRESHOLD = 5, -0.10
MIN_PEERS_CRASHING = 2
PEERS = ["NVDA", "AMD", "INTC", "TXN", "QCOM", "MU", "AMAT", "LRCX", "KLAC", "ADI", "MRVL", "ON"]

ROTATION_FRACTIONS = [0.0, 0.25, 0.5, 0.75, 1.0]

NONE_WEIGHTS: dict[str, dict[str, float]] = {
    "INACTIVE": {"G": 0.250, "X": 0.550, "L": 0.200, "S": 0.000},
    "T1":       {"G": 0.250, "X": 0.430, "L": 0.200, "S": 0.120},
    "T2":       {"G": 0.250, "X": 0.380, "L": 0.200, "S": 0.170},
}
FULL_WEIGHTS: dict[str, dict[str, float]] = {
    "INACTIVE": {"G": 0.525, "X": 0.000, "L": 0.475, "S": 0.000},
    "T1":       {"G": 0.405, "X": 0.000, "L": 0.475, "S": 0.120},
    "T2":       {"G": 0.355, "X": 0.000, "L": 0.475, "S": 0.170},
}


def _interp_weights(state: str, fraction: float) -> dict[str, float]:
    n, f = NONE_WEIGHTS[state], FULL_WEIGHTS[state]
    return {k: n[k] + fraction * (f[k] - n[k]) for k in n}


def load(category: str, stem: str) -> pd.Series:
    df = pd.read_parquet(DATA_DIR / category / f"{stem}.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index().dropna()


def _fetch_peer_prices(ticker: str) -> pd.Series | None:
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).history(period="max", auto_adjust=True)
        if df.empty:
            return None
        s = df["Close"].dropna()
        s.index = pd.to_datetime(s.index.date)
        return s.sort_index()
    except Exception:
        return None


def basket_confirmed_series(avgo: pd.Series, peer_prices: dict[str, pd.Series]) -> pd.Series:
    """Daily boolean: True where >=MIN_PEERS_CRASHING peers are ALSO in a
    5d/-10% crash on that date, aligned to avgo's index."""
    peer_rocs = {p: (s / s.shift(CRASH_ROC_WINDOW) - 1) for p, s in peer_prices.items()}
    out = pd.Series(False, index=avgo.index)
    for d in avgo.index:
        count = 0
        for proc in peer_rocs.values():
            idx = proc.index.searchsorted(d)
            if idx < len(proc.index) and abs((proc.index[idx] - d).days) <= 2:
                val = proc.iloc[idx]
                if pd.notna(val) and val <= CRASH_ROC_THRESHOLD:
                    count += 1
        out.loc[d] = count >= MIN_PEERS_CRASHING
    return out


def perf(equity: pd.Series) -> dict:
    r = equity.pct_change().dropna()
    yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = float(equity.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 else 0.0
    dd = equity / equity.cummax() - 1
    maxdd = float(dd.min())
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
    calmar = cagr / abs(maxdd) if maxdd != 0 else 0.0
    return {"cagr": cagr, "sharpe": sharpe, "maxdd": maxdd, "calmar": calmar, "years": yrs}


def run(avgo: pd.Series, gold: pd.Series, lly: pd.Series, silver: pd.Series,
        basket: pd.Series, start: pd.Timestamp, rotation_fraction: float) -> pd.Series:
    common = (gold.index.intersection(avgo.index).intersection(lly.index)
              .intersection(silver.index).intersection(basket.index))
    common = common[common >= start].sort_values()

    x_r = avgo.reindex(common)
    sma = x_r.rolling(AVGO_MA).mean()
    ma_guard = (x_r < sma).fillna(False)
    roc = x_r.pct_change(CRASH_ROC_WINDOW)
    roc_guard = (roc <= CRASH_ROC_THRESHOLD).fillna(False)
    is_basket = basket.reindex(common).fillna(False)

    # NONE unless a guard condition fires. MA breach or a SOLO crash-ROC
    # (not basket-confirmed) keep the full, already-validated flip.
    # A BASKET-confirmed crash-ROC (and no MA breach already active) gets
    # the graduated response under test.
    guard_state = pd.Series("NONE", index=common)
    guard_state[roc_guard & is_basket & ~ma_guard] = "BASKET"
    guard_state[ma_guard | (roc_guard & ~is_basket)] = "FULL"

    gsr = (gold.reindex(common) / silver.reindex(common)).dropna().reindex(common)
    peak = gsr.rolling(GSR_PEAK_WINDOW).max()
    fall = (peak - gsr) / peak.replace(0, np.nan)

    silver_states, state = [], "INACTIVE"
    for i in range(len(common)):
        gv = gsr.iloc[i]
        fv = fall.iloc[i] if not pd.isna(fall.iloc[i]) else 0.0
        if pd.isna(gv):
            silver_states.append(state)
            continue
        if state in ("T1", "T2") and gv < GSR_EXIT:
            state = "INACTIVE"
        if state == "INACTIVE":
            fallen = fv >= GSR_PEAK_FALL
            if gv >= GSR_T2 and fallen:
                state = "T2"
            elif gv >= GSR_T1 and fallen:
                state = "T1"
        silver_states.append(state)

    prices = {"G": gold, "X": x_r, "L": lly, "S": silver}
    rets = {k: v.reindex(common).pct_change() for k, v in prices.items()}
    port = pd.Series(0.0, index=common)
    prev = None
    for i, _date in enumerate(common):
        s = silver_states[i]
        gstate = guard_state.iloc[i]
        w = FULL_WEIGHTS[s] if gstate == "FULL" else (
            _interp_weights(s, rotation_fraction) if gstate == "BASKET" else NONE_WEIGHTS[s])
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
    start = pd.Timestamp("2009-08-06")

    peer_prices = {p: s for p in PEERS if (s := _fetch_peer_prices(p)) is not None}
    print(f"Peers with usable data: {sorted(peer_prices)}")
    basket = basket_confirmed_series(avgo, peer_prices)
    print(f"Basket-confirmed days in AVGO history: {int(basket.sum())} of {len(basket)}")

    print("\n" + "=" * 90)
    print("AVGO guard: graduated response for basket-confirmed crash-ROC triggers")
    print("=" * 90)
    for f in ROTATION_FRACTIONS:
        eq = run(avgo, gold, lly, silver, basket, start, f)
        p = perf(eq)
        label = "current (full flip)" if f == 1.0 else ("ignore basket trigger" if f == 0.0 else f"{f:.0%} rotation")
        print(f"  rotation_fraction={f:.2f} [{label:<22}]  CAGR {p['cagr']:+.1%}  "
              f"MaxDD {p['maxdd']:+.1%}  Sharpe {p['sharpe']:.3f}  Calmar {p['calmar']:.3f}")

    print("\nInformational only -- not wired into any live gate.")


if __name__ == "__main__":
    main()
