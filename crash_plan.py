"""crash_plan.py

The operator's crash plan for the cash reserve (revised 2026-11-05, MEMORY.md
"Crash plan"), computed so the alert states the trade instead of restating
the rule:

  - Trigger  : a holding's close is >= 10% below its close 5 sessions earlier.
  - Tranches : the reserve is THREE equal tranches, each one third of the cash
               TARGET (so the size stays the same as cash is spent). First
               come, first served across Broadcom, Lilly and the index.
  - Limit    : at most 2 tranches per holding, so one name can never take the
               whole reserve.
  - Next     : a further -10% from the trigger close is the next tranche's
               level; the alert states it as a price.
  - Cap      : never above 28% of the account for a stock, 38% for the index.
  - Several firing on one run split what is left equally.

Tranches used are the one piece of state prices cannot show; they live in
config/crash_plan.toml and are recorded after each buy:
    python crash_plan.py bought Broadcom
    python crash_plan.py reset            # cash back at target

The block's "<name> status: ARMED|FIRED|NO_DATA" rows are what
check_signal_changes parses -- keep them stable.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

STATE_PATH = Path(__file__).parent / "config" / "crash_plan.toml"

TRIGGER = -0.10
WINDOW = 5
TRANCHES = 3
MAX_PER_HOLDING = 2
NEXT_DROP = 0.10

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


def load_used(path: Path = STATE_PATH) -> dict[str, int]:
    try:
        with open(path, "rb") as f:
            used = tomllib.load(f).get("used", {})
    except FileNotFoundError:
        used = {}
    return {n: int(used.get(n, 0)) for n in HOLDINGS}


def save_used(used: dict[str, int], path: Path = STATE_PATH) -> None:
    lines = ["# Crash-plan tranches used since the cash reserve was last full.",
             "# Written by `python crash_plan.py bought <holding>` / `reset`.",
             "", "[used]"]
    lines += [f'"{n}" = {int(used.get(n, 0))}' for n in HOLDINGS]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plan(rows: list[dict], cash: float, base: float, cash_target_kr: float,
         used: dict[str, int] | None = None) -> list[dict]:
    """rows: [{name, roc, close, value}] -> the same rows with state, buy_kr,
    why, and next_price. base = the account the caps are measured against."""
    used = used or {n: 0 for n in HOLDINGS}
    tranche = cash_target_kr / TRANCHES
    fired = [r for r in rows if r["roc"] is not None and r["roc"] <= TRIGGER]
    eligible = [r for r in fired if used.get(r["name"], 0) < MAX_PER_HOLDING]
    share = min(tranche, cash / len(eligible)) if eligible else 0.0
    out = []
    for r in rows:
        cap = HOLDINGS[r["name"]][2]
        n_used = used.get(r["name"], 0)
        if r["roc"] is None:
            out.append({**r, "state": NO_DATA, "buy_kr": 0.0, "why": "", "next_price": None})
        elif r not in fired:
            out.append({**r, "state": ARMED, "buy_kr": 0.0, "why": "", "next_price": None})
        else:
            room = max(0.0, cap * base - r["value"])
            if n_used >= MAX_PER_HOLDING:
                buy, why = 0.0, f"no buy -- {MAX_PER_HOLDING} tranches already used on this holding"
            elif share <= 0:
                buy, why = 0.0, "no buy -- the reserve is spent"
            elif room <= 0:
                buy, why = 0.0, "no buy -- already at its cap"
            else:
                buy = min(share, room)
                why = f"tranche {n_used + 1} of max {MAX_PER_HOLDING} for this holding"
            out.append({**r, "state": FIRED, "buy_kr": buy, "why": why,
                        "next_price": r["close"] * (1 - NEXT_DROP)})
    return out


def format_lines(planned: list[dict], cash: float, cash_target_kr: float) -> list[str]:
    out = [f"  Crash Plan  [cash {cash:,.0f} kr; {TRANCHES} tranches of "
           f"{cash_target_kr / TRANCHES:,.0f} kr, max {MAX_PER_HOLDING} per holding; "
           f"trigger {WINDOW}d <= {TRIGGER:.0%}; caps 28% stock / 38% index]"]
    for r in planned:
        if r["state"] == NO_DATA:
            out.append(f"    {r['name']} status: {NO_DATA}  (fewer than {WINDOW + 1} closes)")
        elif r["state"] == ARMED:
            out.append(f"    {r['name']} status: {ARMED}  ({WINDOW}d {r['roc']:+.1%}, trigger {TRIGGER:.0%})")
        else:
            px = (f"${r['next_price']:,.2f}" if HOLDINGS[r["name"]][0] == "equities"
                  else f"{r['next_price']:,.2f} kr")
            act = f"BUY {r['buy_kr']:,.0f} kr ({r['why']})" if r["buy_kr"] > 0 else r["why"]
            out.append(f"    {r['name']} status: {FIRED}  ({WINDOW}d {r['roc']:+.1%}) -- {act}; "
                       f"next tranche level below {px}; then record: python crash_plan.py bought \"{r['name']}\"")
    return out


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    used = load_used()
    if argv[:1] == ["bought"] and len(argv) == 2 and argv[1] in HOLDINGS:
        used[argv[1]] += 1
        save_used(used)
    elif argv == ["reset"]:
        used = {n: 0 for n in HOLDINGS}
        save_used(used)
    elif argv:
        raise SystemExit(f"usage: crash_plan.py [bought <{' | '.join(HOLDINGS)}> | reset]")
    total = sum(used.values())
    print(f"tranches used: {total} of {TRANCHES}  " + ", ".join(f"{n} {k}" for n, k in used.items()))


if __name__ == "__main__":
    main()
