"""recession_mode.py

Recession mode (operator decision 2026-11-15, MEMORY.md "Recession de-risk
rule") and the Market Watch early-warning gauges. Pure functions; the store
is read by fi_tracker, which prints the blocks check_signal_changes parses.

Recession mode -- the Growth-Trend signal, evaluated once per month:
  ON  when, at the last COMPLETED month end,
        S&P (SPY) close < its 10-month average of month-end closes, AND
        unemployment (the previous month's print, as published) > its
        12-month average.
  While ON the targets shift [recession_mode].shift (0.20) from
  [recession_mode].source (LF Global Index, 30% -> 10%) to
  [recession_mode].sink (Reactor Core Cash, 10% -> 30%). The crash plan keeps
  its normal budget (sized off the BASE cash target), so the extra cash is a
  separate recession buffer it cannot spend.
  Tested 2000-2026 (stylised 70/20/10): MaxDD -38.2% -> -28.3%, Calmar
  0.23 -> 0.32, CAGR +0.2pp at 30% cash; missed the pre-registered Calmar bar
  by 0.01 -- adopted as an operator call, not a passed test.

Market Watch -- awareness only, NO trade (every exit rule tested lost
return). Each row is "<name> status: ON|OFF  (detail)"; check_signal_changes
alerts on OFF -> ON and ON -> OFF. HY OAS > 400 bp already has its own alert
and is not repeated here.

The "<name> status: <STATE>" rows are what check_signal_changes parses --
keep them stable.
"""
from __future__ import annotations

import pandas as pd

ON, OFF, NO_DATA = "ON", "OFF", "NO_DATA"

TREND_MONTHS = 10
UNRATE_MONTHS = 12
UNRATE_MIN_PERIODS = 10        # UNRATE 2025-10 is missing (shutdown)


# ── recession mode ───────────────────────────────────────────────────────────

def completed_month_ends(daily_close: pd.Series, today: pd.Timestamp) -> pd.Series:
    """Month-end closes of months that ENDED before `today`'s month began.
    The current month is never used: its 'month end' would be today's close."""
    m = daily_close.dropna().resample("ME").last()
    return m[m.index < pd.Timestamp(today).to_period("M").to_timestamp()]


def recession_state(spx_daily: pd.Series, unrate: pd.Series, today: pd.Timestamp) -> dict:
    """Growth-Trend state at the last completed month end.

    unrate: monthly observations as FRED stamps them (first of the month).
    The value used at month end M is the print FOR month M-1 -- the same
    one-month publication lag as the backtest (MEMORY.md 2026-11-15)."""
    spx_m = completed_month_ends(spx_daily, today)
    if len(spx_m) < TREND_MONTHS or unrate is None or unrate.dropna().empty:
        return {"state": NO_DATA}
    un_m = unrate.dropna().resample("ME").last().shift(1).reindex(spx_m.index).ffill()
    sma = spx_m.rolling(TREND_MONTHS).mean()
    un_avg = un_m.rolling(UNRATE_MONTHS, min_periods=UNRATE_MIN_PERIODS).mean()
    t = spx_m.index[-1]
    if any(pd.isna(x) for x in (sma[t], un_m[t], un_avg[t])):
        return {"state": NO_DATA}
    trend_neg = bool(spx_m[t] < sma[t])
    labour_neg = bool(un_m[t] > un_avg[t])
    return {
        "state": ON if (trend_neg and labour_neg) else OFF,
        "as_of": t,
        "spx": float(spx_m[t]), "spx_avg": float(sma[t]), "trend_neg": trend_neg,
        "unrate": float(un_m[t]), "unrate_avg": float(un_avg[t]), "labour_neg": labour_neg,
    }


def apply_targets(targets: dict[str, float], cfg: dict, state: str) -> dict[str, float]:
    """Targets with the recession shift applied when ON; unchanged otherwise.
    Never lets the source go negative."""
    if state != ON or not cfg.get("enabled", False):
        return dict(targets)
    src, snk, shift = cfg["source"], cfg["sink"], float(cfg["shift"])
    out = dict(targets)
    moved = min(shift, out.get(src, 0.0))
    out[src] = out.get(src, 0.0) - moved
    out[snk] = out.get(snk, 0.0) + moved
    return out


def format_recession_lines(rs: dict, cfg: dict, source_value: float, sink_value: float,
                           denom: float, base: dict[str, float]) -> list[str]:
    """The Recession Mode block. The trade line is computed from the live
    values and targets -- never restated."""
    src, snk, shift = cfg["source"], cfg["sink"], float(cfg["shift"])
    hdr = (f"  Recession Mode  [Growth-Trend: S&P < {TREND_MONTHS}m avg AND unemployment > "
           f"{UNRATE_MONTHS}m avg, month-end; ON shifts {shift:.0%} {src} -> cash]")
    if rs["state"] == NO_DATA:
        return [hdr, f"    Recession mode status: {NO_DATA}  (not enough S&P or unemployment history)"]
    t = rs["as_of"].strftime("%Y-%m")
    detail = (f"({t}: S&P {rs['spx']:,.0f} vs {TREND_MONTHS}m avg {rs['spx_avg']:,.0f} "
              f"[{'below' if rs['trend_neg'] else 'above'}]; unemployment {rs['unrate']:.1f}% vs "
              f"{UNRATE_MONTHS}m avg {rs['unrate_avg']:.2f}% [{'rising' if rs['labour_neg'] else 'not rising'}])")
    lines = [hdr, f"    Recession mode status: {rs['state']}  {detail}"]
    if rs["state"] == ON:
        tgt_src = max(base.get(src, 0.0) - shift, 0.0)
        sell = max(source_value - tgt_src * denom, 0.0)
        lines.append(f"    Action: ON -- sell ~{sell:,.0f} kr of {src} (to {tgt_src:.0%}); "
                     f"cash target {base.get(snk, 0.0) + shift:.0%}. Park the extra cash in a "
                     f"short SEK fund (e.g. Avanza Ränta Kort). Crash plan unchanged.")
    else:
        tgt_src = base.get(src, 0.0)
        buy = max(tgt_src * denom - source_value, 0.0)
        lines.append(f"    Action: OFF -- targets normal ({src} {tgt_src:.0%}, cash "
                     f"{base.get(snk, 0.0):.0%}); {src} is ~{buy:,.0f} kr below its target.")
    return lines


# ── market watch ─────────────────────────────────────────────────────────────

def _last_n_all(series: pd.Series, n: int) -> bool:
    s = series.dropna()
    return len(s) >= n and bool(s.iloc[-n:].all())


def watch_rows(spx: pd.Series | None, sahm: pd.Series | None, claims: pd.Series | None,
               curve: pd.Series | None, vix: pd.Series | None, vix3m: pd.Series | None,
               oil: pd.Series | None) -> list[dict]:
    """[{name, state, detail}] -- each gauge degrades to NO_DATA on its own."""
    rows = []

    def add(name, fn):
        try:
            state, detail = fn()
        except Exception as e:                         # one bad series never hides the rest
            state, detail = NO_DATA, f"unavailable: {e}"
        rows.append({"name": name, "state": state, "detail": detail})

    def trend():
        s = spx.dropna(); sma = s.rolling(200).mean()
        if sma.dropna().empty:
            return NO_DATA, "fewer than 200 closes"
        on = _last_n_all(s < sma, 3)
        return (ON if on else OFF,
                f"S&P {s.iloc[-1]:,.0f} vs 200d avg {sma.iloc[-1]:,.0f} ({s.iloc[-1] / sma.iloc[-1] - 1:+.1%}); "
                f"ON = 3 closes in a row below; risk of a 10% drawdown ~4x normal in that state")

    def labour():
        parts, on = [], False
        if sahm is not None and not sahm.dropna().empty:
            v = float(sahm.dropna().iloc[-1]); on |= v >= 0.5
            parts.append(f"real-time Sahm {v:.2f} (>= 0.50)")
        if claims is not None and len(claims.dropna()) >= 56:
            c4 = claims.dropna().rolling(4).mean()
            low = c4.iloc[-52:].min(); r = c4.iloc[-1] / low - 1; on |= r >= 0.20
            parts.append(f"claims 4wk avg {c4.iloc[-1] / 1e3:,.0f}k, {r:+.0%} vs 52w low (>= +20%)")
        if not parts:
            return NO_DATA, "no Sahm or claims data"
        return ON if on else OFF, "; ".join(parts) + "; the path to deep, recession-type falls"

    def curve_inv():
        c = curve.dropna()
        if c.empty:
            return NO_DATA, "no data"
        v = float(c.iloc[-5:].mean())
        return ON if v < 0 else OFF, f"10y-3m 5d avg {v:+.2f}pp (ON < 0); classic late-cycle warning"

    def vix_stress():
        a = pd.concat([vix, vix3m], axis=1, keys=["v", "v3"]).dropna()
        if len(a) < 3:
            return NO_DATA, "VIX3M not in the store yet"
        on = _last_n_all(a.v > a.v3, 3)
        return ON if on else OFF, f"VIX {a.v.iloc[-1]:.1f} vs VIX3M {a.v3.iloc[-1]:.1f} (ON = above for 3 closes); panic-level stress"

    def oil_shock():
        o = oil.dropna()
        if len(o) < 300:
            return NO_DATA, "under ~1y of oil data"
        now = o.iloc[-21:].mean(); yr = o[o.index <= o.index[-1] - pd.DateOffset(years=1)].iloc[-21:].mean()
        g = now / yr - 1
        return ON if g >= 0.50 else OFF, f"WTI 1m avg ${now:,.0f}, {g:+.0%} y/y (ON >= +50%); ~2x the base odds of a 15% fall"

    add("Trend break", trend)
    add("Labour cracking", labour)
    add("Curve inverted", curve_inv)
    add("Volatility stress", vix_stress)
    add("Oil shock", oil_shock)
    return rows


def format_watch_lines(rows: list[dict]) -> list[str]:
    out = ["  Market Watch  [early warnings -- awareness only, no trade; crash plan, band and recession mode act]"]
    out += [f"    {r['name']} status: {r['state']}  ({r['detail']})" for r in rows]
    return out
