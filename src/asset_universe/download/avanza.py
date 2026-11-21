"""
Avanza price source for instruments with no public market-data feed.

Swedish fondbolag funds and the Virtune crypto ETPs are not on Yahoo -- the
ETP ISINs resolve to Stuttgart symbols with no price history, and the funds
have no symbol at all. Avanza's public market-guide endpoint quotes both, in
SEK, keyed by its own orderbook id (the number in the instrument's URL:
.../om-certifikatet.html/1639655/virtune-bitcoin -> 1639655).

DATES (fixed 2026-11-21): rows used to be stamped with the FETCH date
(date.today()). A fund NAV is published a day late, and a 01:59 UTC run reads
the previous session's price, so every row was labelled 1-2 days late, and an
early-Saturday run stored a Saturday row that the crash plan (weekday rows only)
dropped -- the LF index trigger read a NAV one behind. Now:
  - fetch_quote dates a quote by its own `quote.timeOfLast`, in Stockholm time;
  - fetch_history rebuilds the series from Avanza's dated history (funds: the
    fund-guide chart, a % series converted with the current NAV; listed
    instruments: price-chart daily closes), and update.py REPLACES the overlap,
    so the mis-dated rows written before the fix are repaired on the next run.

CURRENCY IS NOT SEK. Avanza quotes each instrument in its listing currency --
Eli Lilly and Broadcom in USD (NYSE/NASDAQ), the iShares gold ETC in EUR
(Xetra), the Virtune ETPs in SEK (Stockholmsborsen). Assuming SEK here would
have valued LLY at 1/9.6 of reality, silently. The parquet store holds no
currency column, so the position's `currency` in portfolio.toml is what
snapshot() converts by -- and verify_currencies() below cross-checks the two
so a mismatch fails loudly instead of quietly scaling a holding by the FX rate.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

STOCKHOLM = ZoneInfo("Europe/Stockholm")
_FUND_CHART = "https://www.avanza.se/_api/fund-guide/chart/{id}/{period}"
_PRICE_CHART = "https://www.avanza.se/_api/price-chart/stock/{id}?timePeriod={period}"


def _local_date(ms) -> pd.Timestamp:
    """Avanza epoch-ms -> the Stockholm calendar date (a CET/CEST midnight
    stamp is 23:00 or 22:00 UTC the day before; a fixed offset gets summer
    dates wrong)."""
    return pd.Timestamp(datetime.fromtimestamp(ms / 1000, STOCKHOLM).date())

# Certificates/ETPs and funds sit behind different paths; try each.
_ENDPOINTS = (
    "https://www.avanza.se/_api/market-guide/certificate/{id}",
    "https://www.avanza.se/_api/market-guide/fund/{id}",
    "https://www.avanza.se/_api/market-guide/stock/{id}",
    "https://www.avanza.se/_api/fund-guide/guide/{id}",
)


def _get(url: str, timeout: int = 20) -> dict | None:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def fetch_quote(orderbook_id: str) -> dict | None:
    """{'date', 'close', 'name'} for one Avanza orderbook id, or None.

    Reads `quote.last` for exchange-traded instruments and `nav` for funds.
    Returns None rather than raising so one dead id cannot take down the
    daily refresh -- update.py already reports per-ticker errors.
    """
    for tmpl in _ENDPOINTS:
        d = _get(tmpl.format(id=orderbook_id))
        if not d:
            continue
        px, when = None, None
        q = d.get("quote")
        if isinstance(q, dict) and q.get("last") is not None:
            px, when = q["last"], q.get("timeOfLast")
        elif d.get("nav") is not None:          # fund-guide shape
            px = d["nav"]
            when = d.get("navDate")
        if px is None:
            continue
        listing = d.get("listing") or {}
        if isinstance(when, (int, float)):
            qdate = _local_date(when)
        elif isinstance(when, str) and when:
            qdate = pd.Timestamp(when[:10])
        else:
            qdate = pd.Timestamp(date.today())     # last resort: no timestamp in the payload
        return {"date": qdate,
                "close": float(px),
                "name": d.get("name", ""),
                "currency": listing.get("currency") or d.get("currency"),
                "market": listing.get("marketPlaceName")}
    return None


def verify_currencies(positions: list[dict]) -> list[str]:
    """Cross-check each avanza-category position's configured `currency`
    against what Avanza actually quotes it in. Returns a list of human-readable
    mismatches (empty when all agree). Positions whose quote cannot be fetched
    are skipped rather than reported -- a network blip is not a config error.
    """
    problems = []
    for pos in positions:
        if pos.get("category") != "avanza" or not pos.get("ticker"):
            continue
        q = fetch_quote(pos["ticker"])
        if not q or not q.get("currency"):
            continue
        if q["currency"] != pos.get("currency"):
            problems.append(
                f"{pos['name']} (id {pos['ticker']}): config says "
                f"{pos.get('currency')}, Avanza quotes {q['currency']}"
            )
    return problems


def _frame(dates, closes) -> pd.DataFrame:
    return pd.DataFrame({"date": dates, "open": closes, "high": closes,
                         "low": closes, "close": closes, "volume": 0})


def fetch_history(orderbook_id: str, period: str = "one_year") -> pd.DataFrame | None:
    """Dated daily closes for the last `period`, or None.

    Funds: the fund-guide chart is a % change series from the window start;
    it is converted to NAVs by anchoring its last point to the current NAV,
    and is only used when that point is dated the same day as the quote.
    Listed instruments: price-chart daily closes as quoted.
    One row per Stockholm date; the latest quote wins for its own date."""
    q = fetch_quote(orderbook_id)
    if q is None:
        return None
    rows: dict = {}
    fund = _get(_FUND_CHART.format(id=orderbook_id, period=period))
    pts = (fund or {}).get("dataSerie") or []
    pts = [p for p in pts if p.get("x") is not None and p.get("y") is not None]
    if pts and _local_date(pts[-1]["x"]) == q["date"]:
        base = 1 + pts[-1]["y"] / 100
        for p in pts:
            rows[_local_date(p["x"])] = q["close"] * (1 + p["y"] / 100) / base
    else:
        chart = _get(_PRICE_CHART.format(id=orderbook_id, period=period))
        for p in (chart or {}).get("ohlc") or []:
            if p.get("timestamp") is not None and p.get("close") is not None:
                rows[_local_date(p["timestamp"])] = float(p["close"])
    rows[q["date"]] = q["close"]
    dates = sorted(rows)
    return _frame(dates, [rows[d] for d in dates])


def fetch(orderbook_id: str, *_args, **_kwargs) -> pd.DataFrame | None:
    """update.py-compatible signature. Dated history (see fetch_history);
    falls back to the single dated quote if no history endpoint answers."""
    h = fetch_history(orderbook_id)
    if h is not None and len(h):
        return h
    q = fetch_quote(orderbook_id)
    if q is None:
        return None
    return _frame([q["date"]], [q["close"]])
