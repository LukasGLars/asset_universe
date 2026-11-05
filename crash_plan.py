"""crash_plan.py

The operator's crash plan for the cash reserve (agreed 2026-11-01, MEMORY.md
"Crash plan"), computed so the alert states the trade instead of restating
the rule:

  - Trigger : a holding's close is >= 10% below its close 5 sessions earlier.
  - Stage 1 : buy that holding with 60% of the cash. Several firing on the
              same run split the 60% equally.
  - Cap     : never above 28% of the account for a stock, 38% for the index
              (2 pp under each band line). Cash a cap blocks stays cash.
  - Stage 2 : if it falls a further 15% from the trigger close, the remaining
              40%. Stated as a price in the alert; not tracked here.

Pure functions; fi_tracker supplies prices and values. The block's
"<name> status: ARMED|FIRED|NO_DATA" rows are what check_signal_changes
parses -- keep them stable.
"""
from __future__ import annotations

TRIGGER = -0.10
WINDOW = 5
STAGE1 = 0.60
STAGE2_DROP = 0.15

# Holding -> (store category, ticker, cap as a fraction of the account).
HOLDINGS = {
    "Broadcom": ("equities", "AVGO", 0.28),
    "Eli Lilly": ("equities", "LLY", 0.28),
    "LF Global Index": ("avanza", "417655", 0.38),
}

ARMED, FIRED, NO_DATA = "ARMED", "FIRED", "NO_DATA"


def roc(closes: list[float], window: int = WINDOW) -> float | None:
    """Return over the last `window` sessions, or None with too little data."""
    if len(closes) < window + 1 or not closes[-(window + 1)]:
        return None
    return closes[-1] / closes[-(window + 1)] - 1.0


def plan(rows: list[dict], cash: float, base: float) -> list[dict]:
    """rows: [{name, roc, close, value}] -> the same rows with state, buy_kr
    and stage2_price. base = the account the caps are measured against."""
    fired = [r for r in rows if r["roc"] is not None and r["roc"] <= TRIGGER]
    share = STAGE1 * cash / len(fired) if fired else 0.0
    out = []
    for r in rows:
        cap = HOLDINGS[r["name"]][2]
        if r["roc"] is None:
            out.append({**r, "state": NO_DATA, "buy_kr": 0.0, "stage2_price": None})
        elif r in fired:
            room = max(0.0, cap * base - r["value"])
            out.append({**r, "state": FIRED, "buy_kr": min(share, room),
                        "stage2_price": r["close"] * (1 - STAGE2_DROP)})
        else:
            out.append({**r, "state": ARMED, "buy_kr": 0.0, "stage2_price": None})
    return out


def format_lines(planned: list[dict], cash: float) -> list[str]:
    out = [f"  Crash Plan  [cash {cash:,.0f} kr; trigger {WINDOW}d <= {TRIGGER:.0%}; "
           f"stage 1 = {STAGE1:.0%} of cash, caps 28% stock / 38% index]"]
    for r in planned:
        if r["state"] == NO_DATA:
            out.append(f"    {r['name']} status: {NO_DATA}  (fewer than {WINDOW + 1} closes)")
        elif r["state"] == ARMED:
            out.append(f"    {r['name']} status: {ARMED}  ({WINDOW}d {r['roc']:+.1%}, trigger {TRIGGER:.0%})")
        else:
            buy = (f"BUY {r['buy_kr']:,.0f} kr" if r["buy_kr"] > 0
                   else "no buy -- already at its cap")
            px = (f"${r['stage2_price']:,.2f}" if HOLDINGS[r["name"]][0] == "equities"
                  else f"{r['stage2_price']:,.2f} kr")
            out.append(f"    {r['name']} status: {FIRED}  ({WINDOW}d {r['roc']:+.1%}) -- {buy}; "
                       f"stage 2 below {px}: the remaining {1 - STAGE1:.0%} of cash")
    return out
