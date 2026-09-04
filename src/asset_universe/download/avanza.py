"""
Avanza price source for instruments with no public market-data feed.

Swedish fondbolag funds and the Virtune crypto ETPs are not on Yahoo -- the
ETP ISINs resolve to Stuttgart symbols with no price history, and the funds
have no symbol at all. Avanza's public market-guide endpoint quotes both, in
SEK, keyed by its own orderbook id (the number in the instrument's URL:
.../om-certifikatet.html/1639655/virtune-bitcoin -> 1639655).

Only the current quote is exposed, not a history, so the store accumulates one
close per run. That is enough: everything downstream reads the latest row.

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
from datetime import date

import pandas as pd

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
        px = None
        q = d.get("quote")
        if isinstance(q, dict) and q.get("last") is not None:
            px = q["last"]
        elif d.get("nav") is not None:          # fund-guide shape
            px = d["nav"]
        if px is None:
            continue
        listing = d.get("listing") or {}
        return {"date": pd.Timestamp(date.today()),
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


def fetch(orderbook_id: str, *_args, **_kwargs) -> pd.DataFrame | None:
    """update.py-compatible signature: returns a one-row OHLC-shaped frame.

    Start/end are ignored -- Avanza exposes only the current quote, so a
    backfill is impossible and the store grows one row per run.
    """
    q = fetch_quote(orderbook_id)
    if q is None:
        return None
    return pd.DataFrame([{
        "date": q["date"], "open": q["close"], "high": q["close"],
        "low": q["close"], "close": q["close"], "volume": 0,
    }])
