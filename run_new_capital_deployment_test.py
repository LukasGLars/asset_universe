"""
run_new_capital_deployment_test.py

Tests the "combo" strategy explicitly: at each real historical AVGO
crash-ROC trigger (5d ROC <= -10%), where should NEW, previously-
uninvested capital go? Three variants, forward returns from each
trigger's close:

  A) DIP-BUY  -- straight into AVGO (the "gap-down tranche" plan).
  B) DEFENSIVE -- into the guard's own defensive mix (Gold52.5/LLY47.5),
     i.e. new capital mirrors what the EXISTING position is rotating
     into at the same moment.
  C) UNGUARDED BASE -- into the static base mix (Gold25/AVGO55/LLY20),
     as if the guard didn't exist and the crash was ignored entirely.

This is deliberately separate from run_crash_guard_validation.py /
run_avgo_guard_graduated_response.py (both already answered "how should
EXISTING capital respond to the guard" -- full flip wins). This answers
a different question: given a real crash-ROC event just fired, was
buying AVGO itself historically the best place for capital that wasn't
already invested? Neither of the earlier scripts tested that.

Declustered trigger list (min 21 trading days apart) over AVGO's full
2009-2026 history. Horizons: 21d/63d/126d/252d forward return from each
trigger's close, each mix rebalanced daily over the window (10bps cost
on entry only, one-time deployment, not simulating an exit).

Output: printed table only -- no CSV. Diagnostic, not a daily script.
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

CRASH_ROC_WINDOW = 5
CRASH_ROC_THRESHOLD = -0.10
DECLUSTER_MIN_GAP = 21
HORIZONS = [21, 63, 126, 252]

BASE_MIX = {"G": 0.25, "X": 0.55, "L": 0.20}
DEFENSIVE_MIX = {"G": 0.525, "X": 0.0, "L": 0.475}
TC = 0.0010


def load(category: str, stem: str) -> pd.Series:
    df = pd.read_parquet(DATA_DIR / category / f"{stem}.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index().dropna()


def find_triggers(avgo: pd.Series) -> list[pd.Timestamp]:
    roc = avgo.pct_change(CRASH_ROC_WINDOW)
    hits = roc[roc <= CRASH_ROC_THRESHOLD].index.tolist()
    triggers, last = [], None
    for dt in hits:
        if last is None or (dt - last).days >= DECLUSTER_MIN_GAP:
            triggers.append(dt)
        last = dt
    return triggers


def mix_forward_return(mix: dict, prices: dict, common: pd.DatetimeIndex,
                        trigger: pd.Timestamp, horizon: int) -> float | None:
    idx = common.get_indexer([trigger], method="nearest")[0]
    if idx + horizon >= len(common):
        return None
    window = common[idx: idx + horizon + 1]
    rets = {k: prices[k].reindex(window).pct_change().fillna(0.0) for k in mix}
    port = pd.Series(0.0, index=window)
    port.iloc[0] -= TC  # one-time entry cost
    for i in range(len(window)):
        port.iloc[i] += sum(w * rets[a].iloc[i] for a, w in mix.items())
    equity = (1 + port).cumprod()
    return float(equity.iloc[-1] - 1)


def dip_buy_forward_return(avgo: pd.Series, trigger: pd.Timestamp, horizon: int) -> float | None:
    idx = avgo.index.get_indexer([trigger], method="nearest")[0]
    if idx + horizon >= len(avgo):
        return None
    entry = avgo.iloc[idx] * (1 + TC)
    exitp = avgo.iloc[idx + horizon]
    return float(exitp / entry - 1)


def main() -> None:
    gold = load("commodities", "GC_F")
    lly = load("equities", "LLY")
    avgo = load("equities", "AVGO")

    common = (gold.index.intersection(avgo.index).intersection(lly.index))
    common = common[common >= pd.Timestamp("2009-08-06")].sort_values()

    prices = {"G": gold, "X": avgo, "L": lly}
    avgo_c = avgo.reindex(common)

    triggers = find_triggers(avgo_c)
    print("=" * 100)
    print(f"NEW CAPITAL DEPLOYMENT TEST -- {len(triggers)} declustered AVGO crash-ROC "
          f"triggers (5d <= -10%), 2009-2026")
    print("A=dip-buy AVGO  B=defensive mix (Gold52.5/LLY47.5)  C=unguarded base (Gold25/AVGO55/LLY20)")
    print("=" * 100)

    rows = []
    for t in triggers:
        row = {"trigger": t.date()}
        for h in HORIZONS:
            row[f"A_{h}d"] = dip_buy_forward_return(avgo_c, t, h)
            row[f"B_{h}d"] = mix_forward_return(DEFENSIVE_MIX, prices, common, t, h)
            row[f"C_{h}d"] = mix_forward_return(BASE_MIX, prices, common, t, h)
        rows.append(row)

    df = pd.DataFrame(rows).set_index("trigger")
    with pd.option_context("display.width", 200, "display.float_format", "{:+.1%}".format):
        print(df)
    print()

    print("-" * 100)
    print("Summary (median / average / win-rate vs the other two, per horizon):")
    print("-" * 100)
    for h in HORIZONS:
        a, b, c = df[f"A_{h}d"].dropna(), df[f"B_{h}d"].dropna(), df[f"C_{h}d"].dropna()
        n = min(len(a), len(b), len(c))
        joint = df[[f"A_{h}d", f"B_{h}d", f"C_{h}d"]].dropna()
        a_beats_b = float((joint[f"A_{h}d"] > joint[f"B_{h}d"]).mean()) if len(joint) else float("nan")
        a_beats_c = float((joint[f"A_{h}d"] > joint[f"C_{h}d"]).mean()) if len(joint) else float("nan")
        print(f"  {h:>3}d  A: med={a.median():+.1%} ave={a.mean():+.1%}  "
              f"B: med={b.median():+.1%} ave={b.mean():+.1%}  "
              f"C: med={c.median():+.1%} ave={c.mean():+.1%}  "
              f"(n={n})  A>B: {a_beats_b:.0%}  A>C: {a_beats_c:.0%}")

    print()
    print("Verdict: A (dip-buy AVGO) is the right call for new capital at a real crash-ROC")
    print("trigger only if its median/average AND win-rate beat both B and C above across")
    print("horizons -- not just one metric at one horizon.")


if __name__ == "__main__":
    main()
