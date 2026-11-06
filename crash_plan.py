"""crash_plan.py

The operator's crash plan for the cash reserve (revised 2026-11-05, MEMORY.md
"Crash plan"), computed so the alert states the trade instead of restating
the rule:

  - Trigger  : a holding's close is >= 10% below its close 5 sessions earlier.
  - Tranches : the reserve is THREE tranches, sized off the cash actually
               AVAILABLE (operator, 2026-11-06; was the cash target): each
               tranche = available cash / tranches not yet used, where
               available = the Reactor Core Cash balance on the sheet minus
               any second half already reserved. The operator updates the
               sheet after every buy, so each alert is sized off real cash.
               With no new money that is a third of the cash at the first
               trigger, every time. First come, first served across
               Broadcom, Lilly and the index.
  - Split    : each tranche is bought in two halves -- half at the trigger,
               the other half 21 sessions later, or at a further -10% from
               the trigger close if that comes first. The first month after a
               trigger is where the risk sits (worst -21.7%, MEMORY.md
               2026-11-05), so only half is exposed to it.
  - Limit    : at most 2 tranches per holding, so one name can never take the
               whole reserve.
  - Cap      : never above 28% of the account for a stock, 38% for the index.
  - Several firing on one run split what is left equally.

Tranches used and open second halves are the state prices cannot show; they
live in config/crash_plan.toml and are recorded after each buy:
    python crash_plan.py bought "Broadcom"          # first half, opens a tranche
    python crash_plan.py bought-second "Broadcom"   # second half, closes it
    python crash_plan.py reset                      # cash back at target

The block's "<name> status: <STATE>" rows are what check_signal_changes
parses -- keep them stable.
"""
from __future__ import annotations

import datetime as dt
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
SECOND_AFTER_SESSIONS = 21
SECOND_DROP = 0.10

# Holding -> (store category, ticker, cap as a fraction of the account).
HOLDINGS = {
    "Broadcom": ("equities", "AVGO", 0.28),
    "Eli Lilly": ("equities", "LLY", 0.28),
    "LF Global Index": ("avanza", "417655", 0.38),
}

ARMED, FIRED, WAITING, SECOND_HALF, NO_DATA = "ARMED", "FIRED", "WAITING", "SECOND_HALF", "NO_DATA"


def roc(closes: list[float], window: int = WINDOW) -> float | None:
    """Return over the last `window` sessions, or None with too little data."""
    if len(closes) < window + 1 or not closes[-(window + 1)]:
        return None
    return closes[-1] / closes[-(window + 1)] - 1.0


# ── state ────────────────────────────────────────────────────────────────────

def load_state(path: Path | None = None) -> dict:
    """{"used": {holding: n}, "pending": {holding: {date, close, half_kr}}}."""
    # Resolved at call time, not as a default: a default binds at import and
    # a test that repoints STATE_PATH would write the live file.
    path = path or STATE_PATH
    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError:
        raw = {}
    used = {n: int(raw.get("used", {}).get(n, 0)) for n in HOLDINGS}
    pending = {n: dict(p) for n, p in raw.get("pending", {}).items() if n in HOLDINGS}
    return {"used": used, "pending": pending}


def load_used(path: Path | None = None) -> dict[str, int]:
    return load_state(path)["used"]


def save_state(state: dict, path: Path | None = None) -> None:
    path = path or STATE_PATH
    lines = ["# Crash-plan state: tranches opened since the cash reserve was last",
             "# full, and second halves still to buy. Written by crash_plan.py.",
             "", "[used]"]
    lines += [f'"{n}" = {int(state["used"].get(n, 0))}' for n in HOLDINGS]
    for n, p in state.get("pending", {}).items():
        lines += ["", f'[pending."{n}"]', f'date    = "{p["date"]}"',
                  f'close   = {float(p["close"]):g}', f'half_kr = {float(p["half_kr"]):.0f}']
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_used(used: dict[str, int], path: Path | None = None) -> None:
    save_state({"used": used, "pending": load_state(path)["pending"]}, path)


# ── plan (pure) ──────────────────────────────────────────────────────────────

def sizing(cash: float, used: dict[str, int] | None = None, pending: dict | None = None) -> dict:
    """Available cash (balance minus reserved second halves), tranches left,
    and the tranche that available cash supports right now."""
    used = used or {}
    pending = pending or {}
    reserved = sum(float(p["half_kr"]) for p in pending.values())
    available = max(0.0, cash - reserved)
    left = max(0, TRANCHES - sum(used.values()))
    return {"reserved": reserved, "available": available, "left": left,
            "tranche": available / left if left else 0.0}


def plan(rows: list[dict], cash: float, base: float,
         used: dict[str, int] | None = None, pending: dict | None = None) -> list[dict]:
    """rows: [{name, roc, close, value, since}] where `since` is the number of
    sessions after an open tranche's first-half date (None when none is open).
    Returns the rows with state, buy_kr, why and next_price."""
    used = used or {n: 0 for n in HOLDINGS}
    pending = pending or {}
    sz = sizing(cash, used, pending)
    fired = [r for r in rows if r["name"] not in pending and r["roc"] is not None and r["roc"] <= TRIGGER]
    eligible = [r for r in fired if used.get(r["name"], 0) < MAX_PER_HOLDING]
    # Several firing on one run split what is left: each opens a tranche of
    # available / max(tranches left, holdings firing), so the second halves
    # stay covered even when more fire than there are tranches left.
    share = (sz["available"] / max(sz["left"], len(eligible)) / 2) if (eligible and sz["left"]) else 0.0
    out = []
    for r in rows:
        name, cap = r["name"], HOLDINGS[r["name"]][2]
        room = max(0.0, cap * base - r["value"])
        if name in pending:
            p = pending[name]
            level = float(p["close"]) * (1 - SECOND_DROP)
            due = (r.get("since") or 0) >= SECOND_AFTER_SESSIONS or (
                r["close"] is not None and r["close"] <= level)
            if due:
                buy = min(float(p["half_kr"]), room, cash)
                why = "second half of the open tranche" if buy > 0 else "second half blocked by cap or cash"
                out.append({**r, "state": SECOND_HALF, "buy_kr": buy, "why": why, "next_price": None})
            else:
                left = SECOND_AFTER_SESSIONS - (r.get("since") or 0)
                out.append({**r, "state": WAITING, "buy_kr": 0.0,
                            "why": f"second half in {left} sessions or below the level", "next_price": level})
        elif r["roc"] is None:
            out.append({**r, "state": NO_DATA, "buy_kr": 0.0, "why": "", "next_price": None})
        elif r not in fired:
            out.append({**r, "state": ARMED, "buy_kr": 0.0, "why": "", "next_price": None})
        else:
            n_used = used.get(name, 0)
            if n_used >= MAX_PER_HOLDING:
                buy, why = 0.0, f"no buy -- {MAX_PER_HOLDING} tranches already used on this holding"
            elif share <= 0:
                buy, why = 0.0, "no buy -- the reserve is spent"
            elif room <= 0:
                buy, why = 0.0, "no buy -- already at its cap"
            else:
                buy = min(share, room)
                why = f"first half of tranche {n_used + 1} of max {MAX_PER_HOLDING} for this holding"
            out.append({**r, "state": FIRED, "buy_kr": buy, "why": why,
                        "next_price": r["close"] * (1 - SECOND_DROP)})
    return out


def _px(name: str, v: float) -> str:
    return f"${v:,.2f}" if HOLDINGS[name][0] == "equities" else f"{v:,.2f} kr"


def format_lines(planned: list[dict], cash: float, used: dict[str, int] | None = None,
                 pending: dict | None = None) -> list[str]:
    sz = sizing(cash, used, pending)
    res = f" minus {sz['reserved']:,.0f} reserved" if sz["reserved"] else ""
    out = [f"  Crash Plan  [cash {cash:,.0f} kr{res} = {sz['available']:,.0f} available; "
           f"{sz['left']} of {TRANCHES} tranches left -> {sz['tranche']:,.0f} kr each, bought in halves; "
           f"max {MAX_PER_HOLDING} per holding; trigger {WINDOW}d <= {TRIGGER:.0%}; caps 28% stock / 38% index]"]
    for r in planned:
        n, s = r["name"], r["state"]
        if s == NO_DATA:
            out.append(f"    {n} status: {NO_DATA}  (fewer than {WINDOW + 1} closes)")
        elif s == ARMED:
            out.append(f"    {n} status: {ARMED}  ({WINDOW}d {r['roc']:+.1%}, trigger {TRIGGER:.0%})")
        elif s == WAITING:
            out.append(f"    {n} status: {WAITING}  ({r['why']} {_px(n, r['next_price'])})")
        elif s == SECOND_HALF:
            act = f"BUY {r['buy_kr']:,.0f} kr ({r['why']})" if r["buy_kr"] > 0 else r["why"]
            out.append(f"    {n} status: {SECOND_HALF}  -- {act}; then record: "
                       f"python crash_plan.py bought-second \"{n}\"")
        else:
            act = f"BUY {r['buy_kr']:,.0f} kr ({r['why']})" if r["buy_kr"] > 0 else r["why"]
            out.append(f"    {n} status: {FIRED}  ({WINDOW}d {r['roc']:+.1%}) -- {act}; second half in "
                       f"{SECOND_AFTER_SESSIONS} sessions or below {_px(n, r['next_price'])}; "
                       f"then record: python crash_plan.py bought \"{n}\" --close {r['close']:g} "
                       f"--half {r['buy_kr']:.0f}")
    return out


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None, today: dt.date | None = None,
         close: float | None = None, half_kr: float | None = None) -> None:
    """`bought` needs the trigger close and the half amount; fi_tracker's
    alert prints both, and the session recording the buy passes them as
    --close / --half. Kept explicit rather than re-derived so a late record
    cannot pick up a later price."""
    argv = sys.argv[1:] if argv is None else argv
    state = load_state()
    if argv[:1] == ["bought"] and len(argv) >= 2 and argv[1] in HOLDINGS:
        opts = dict(zip(argv[2::2], argv[3::2]))
        c = close if close is not None else float(opts["--close"])
        h = half_kr if half_kr is not None else float(opts["--half"])
        state["used"][argv[1]] += 1
        state["pending"][argv[1]] = {"date": (today or dt.date.today()).isoformat(), "close": c, "half_kr": h}
        save_state(state)
    elif argv[:1] == ["bought-second"] and len(argv) == 2 and argv[1] in HOLDINGS:
        state["pending"].pop(argv[1], None)
        save_state(state)
    elif argv == ["reset"]:
        save_state({"used": {n: 0 for n in HOLDINGS}, "pending": {}})
        state = load_state()
    elif argv:
        raise SystemExit('usage: crash_plan.py [bought "<holding>" --close X --half KR | '
                         'bought-second "<holding>" | reset]')
    state = load_state()
    print(f"tranches opened: {sum(state['used'].values())} of {TRANCHES}  "
          + ", ".join(f"{n} {k}" for n, k in state["used"].items())
          + (f"  | open second halves: {', '.join(state['pending'])}" if state["pending"] else ""))


if __name__ == "__main__":
    main()
