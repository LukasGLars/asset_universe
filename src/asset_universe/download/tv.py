"""
TradingView price fetcher for tickers unavailable on yfinance (e.g. XETR-listed ETCs).
Returns the latest price by scraping the TradingView symbols page.
"""

from __future__ import annotations
import re
import urllib.request
import urllib.error


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

# Map our internal ticker → TradingView symbol URL slug
TV_SYMBOLS: dict[str, str] = {
    "PPFB.DE": "XETR-PPFB",
    "VZLC.DE": "XETR-VZLC",
}


def fetch_price(ticker: str) -> float | None:
    """Return latest price for a TradingView-mapped ticker, or None on failure."""
    slug = TV_SYMBOLS.get(ticker)
    if not slug:
        return None

    url = f"https://www.tradingview.com/symbols/{slug}/"
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError:
        return None

    # TradingView embeds price in meta og:description or structured data
    # Pattern: "price":{"last":68.685 or similar JSON-like fragment
    for pattern in [
        r'"last"\s*:\s*([\d.]+)',
        r'"price"\s*:\s*([\d.]+)',
        r'class="[^"]*last-price[^"]*"[^>]*>\s*([\d,.]+)',
        r'data-last-price="([\d.]+)"',
    ]:
        m = re.search(pattern, html)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except ValueError:
                continue

    return None
