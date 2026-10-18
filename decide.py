"""decide.py

One screen: for every position, OWN or CUT, and how much to buy/sell.

    python decide.py

Composes rules that already exist -- adds none:
  - own/cut : Sightline state (config/sightline.toml), plus a collections
              BREAK (collections_monitor.py) -> REVIEW: no trade, no new
              contributions, read the 10-Q (unvalidated signal, never a sell);
              exemptions name the
              rule that governs instead. A targeted position with neither is
              printed as NO RULE -- a gap, not a hold.
  - size    : per-asset target_weight (config/portfolio.toml) against the
              same denominator fi_tracker uses (positions carrying a target),
              traded only outside vol_target.REBAL_BAND. CUT overrides: sell
              all.
  - crypto  : the trend rule's exposure x crypto_sleeve capital_sek.
  - new kr  : next_contribution_target, same gates as fi_tracker.

Every figure is read from its source; nothing is restated (CLAUDE.md rule 1).
The decision core is `decide()`, a pure function, so it is testable without
the store.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from next_contribution import next_contribution_target
from sightline import CUT, REQUALIFIED, derive_state
from vol_target import REBAL_BAND, rebalance_instructions

# Trend-rule ticker -> the ETP row that holds it. Checked against
# portfolio.toml by the tests, so a rename fails loudly.
SLEEVE_ROWS = {"BTC-USD": "Virtune Bitcoin", "ETH-USD": "Virtune Staked ETH"}

# Same exclusions as fi_tracker's NEXT CONTRIBUTION block.
NO_CONTRIB = {"Silver", *SLEEVE_ROWS.values()}


def _governing_rule(pos: dict, sightline_cfg: dict,
                    collections: dict[str, tuple[str, str]] | None = None) -> tuple[str, str, str]:
    """(verdict, rule text, sightline state or '') for one position."""
    entry = sightline_cfg.get(pos["ticker"]) if pos["ticker"] != "exemptions" else None
    if entry:
        state, detail = derive_state(entry.get("readings", []))
        if state == CUT:
            return "CUT", f"Sightline CUT -- {detail}", state
        if state == REQUALIFIED:
            # Re-opens the entry test only -- never a re-buy.
            return "ENTRY", f"Sightline REQUALIFIED -- {detail}", state
        # Below a Sightline CUT on purpose: a validated cut outranks an
        # unvalidated review.
        coll = (collections or {}).get(pos["ticker"])
        if coll and coll[0] == "BREAK":
            return "REVIEW", f"Collections BREAK -- {coll[1]}", state
        return "OWN", f"Sightline HOLD -- {detail}", state
    for key in sightline_cfg.get("exemptions", {}):
        if key in (pos["name"].lower(), pos["bucket"]):
            return "OWN", f"exempt ({key})", ""
    if pos["ticker"] == "":
        return "OWN", "cash", ""
    return "OWN?", "NO RULE -- add a Sightline entry or exemption", ""


def decide(
    positions: list[dict],
    sightline_cfg: dict,
    crypto_signals: dict[str, dict],
    crypto_capital: dict[str, float],
    band: float = REBAL_BAND,
    collections: dict[str, tuple[str, str]] | None = None,
) -> dict:
    """positions: [{name, ticker, bucket, value_sek, price_sek, target}].

    Returns {rows, denom, next, outside}. Each row: name, verdict, rule,
    value, target_kr, action, trade_kr (signed: + buy, - sell)."""
    targeted = [p for p in positions if p["target"] > 0]
    denom = sum(p["value_sek"] or 0.0 for p in targeted)
    if denom <= 0:
        raise ValueError("no valued positions carry a target_weight")

    cur = {p["name"]: (p["value_sek"] or 0.0) / denom for p in targeted}
    tgt = {p["name"]: p["target"] for p in targeted}
    px = {p["name"]: p["price_sek"] or 0.0 for p in targeted}
    rebal = rebalance_instructions(cur, tgt, px, denom, band)

    sleeve_sig = {SLEEVE_ROWS[t]: (t, s) for t, s in crypto_signals.items() if t in SLEEVE_ROWS}

    rows = []
    cut_names = set()
    for p in targeted:
        name, value = p["name"], p["value_sek"] or 0.0
        verdict, rule, _ = _governing_rule(p, sightline_cfg, collections)
        r = rebal[name]
        target_kr = r["target"] * denom

        if verdict == "CUT":
            cut_names.add(name)
            target_kr, trade = 0.0, -value
            action = f"SELL ALL {value:,.0f} kr" if value > 0 else "do not own"
        elif verdict == "ENTRY":
            # Re-opens the entry test only -- never an automatic re-buy.
            trade, action = 0.0, "entry test open -- not a buy"
        elif verdict == "REVIEW":
            # Collections BREAK has never fired and is unvalidated, so it
            # stops new money and asks for a read of the 10-Q -- a trim is
            # the operator's call, not a size this computes.
            trade, action = 0.0, "REVIEW -- no new kr; trim is an option, not a rule"
        elif name in sleeve_sig:
            t, s = sleeve_sig[name]
            cap = crypto_capital.get(t)
            rule = f"trend {s['exposure']:.0%} (as of {s['as_of']})"
            if cap:
                target_kr = s["exposure"] * cap
                rule += f" x {cap:,.0f} kr capital"
            trade = 0.0
            action = f"HOLD at rule {s['exposure']:.0%}"
        else:
            trade = r["gap_kr"] if r["out_of_band"] else 0.0
            if r["out_of_band"]:
                sh = f" (~{r['shares']} sh)" if r["shares"] else ""
                action = f"{r['action']} {abs(trade):,.0f} kr{sh}"
            else:
                action = f"HOLD ({r['gap']*100:+.1f}pp, band {band*100:.0f}pp)"

        rows.append({"name": name, "verdict": verdict, "rule": rule,
                     "value": value, "weight": r["current"], "target": r["target"],
                     "target_kr": target_kr, "action": action, "trade_kr": trade})

    blocked = cut_names | {r["name"] for r in rows if r["verdict"] in ("ENTRY", "REVIEW")}
    allowed = {n: n not in NO_CONTRIB and n not in blocked for n in tgt}
    nxt, _ = next_contribution_target(cur, tgt, allowed)

    outside = [(p["name"], p["value_sek"] or 0.0) for p in positions
               if p["target"] <= 0 and (p["value_sek"] or 0.0) > 0]
    # A held name with no target can still be a Sightline CUT -- surface it.
    for p in positions:
        if p["target"] <= 0 and (p["value_sek"] or 0.0) > 0:
            v, rule, _ = _governing_rule(p, sightline_cfg, collections)
            if v == "CUT":
                rows.append({"name": p["name"], "verdict": v, "rule": rule,
                             "value": p["value_sek"], "weight": 0.0, "target": 0.0,
                             "target_kr": 0.0, "action": f"SELL ALL {p['value_sek']:,.0f} kr",
                             "trade_kr": -p["value_sek"]})

    return {"rows": rows, "denom": denom, "next": nxt, "outside": outside}


def format_lines(result: dict, stale: str | None = None) -> list[str]:
    out = []
    if stale:
        out.append(f"!! STALE DATA -- {stale}. Sizes below may be wrong.")
    out.append(f"DECIDE  [base {result['denom']:,.0f} kr = positions with a target]")
    out.append(f"  {'Position':<20} {'Do':<7} {'Now':>10} {'Wt':>6} {'Tgt':>6}  Action")
    for r in result["rows"]:
        out.append(f"  {r['name']:<20} {r['verdict']:<7} {r['value']:>10,.0f} "
                   f"{r['weight']:>6.1%} {r['target']:>6.1%}  {r['action']}")
        out.append(f"  {'':<20} why: {r['rule']}")
    out.append(f"  Next contribution -> {result['next']}")
    if result["outside"]:
        out.append("  Outside target base: " +
                   ", ".join(f"{n} {v:,.0f} kr" for n, v in result["outside"]))
    return out


def main() -> None:
    import collections_monitor
    import run_crypto_trend
    from asset_universe import config, portfolio
    from check_local_data_freshness import check_freshness
    from sightline import load_config

    data_dir = config.raw_data_dir()
    fresh, latest, since = check_freshness(data_dir)
    snap = portfolio.snapshot(data_dir)
    targets = {p["name"]: float(p.get("target_weight") or 0.0)
               for p in portfolio._load_portfolio_config()["positions"]}

    def _f(v):
        return None if v is None or v != v else float(v)  # NaN -> None

    positions = [{"name": r["name"], "ticker": r["ticker"], "bucket": r["bucket"],
                  "value_sek": _f(r["value_sek"]), "price_sek": _f(r["price_sek"]),
                  "target": targets.get(r["name"], 0.0)}
                 for _, r in snap.iterrows()]

    result = decide(positions, load_config(), run_crypto_trend.signals(data_dir),
                    run_crypto_trend._sleeve_capital(),
                    collections=collections_monitor.live_states())
    stale = None if fresh else f"latest bar {latest}, expected since {since}"
    print("\n".join(format_lines(result, stale)))


if __name__ == "__main__":
    main()
