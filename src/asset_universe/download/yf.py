import warnings
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")


def fetch(ticker: str, start: str, end: str) -> pd.DataFrame | None:
    """
    Download daily OHLCV for a single ticker via yfinance.
    Returns DataFrame with columns [date, open, high, low, close, volume]
    or None if no data is available.
    """
    raw = yf.download(
        ticker,
        start=start,
        end=end,
        progress=False,
        auto_adjust=True,
        actions=False,
    )

    if raw is None or raw.empty:
        return None

    # yfinance 1.4+ returns MultiIndex (price_type, ticker) — drop ticker level
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.droplevel(1)

    raw.columns = [c.lower() for c in raw.columns]
    raw.index = pd.to_datetime(raw.index).tz_localize(None)
    raw.index.name = "date"

    df = raw[["open", "high", "low", "close", "volume"]].copy()
    df = df.dropna(subset=["close"])
    return df.reset_index()
