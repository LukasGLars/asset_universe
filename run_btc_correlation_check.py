"""Temporary one-off: BTC-USD daily-return correlation vs AVGO/LLY/Gold.
Fetches BTC-USD fresh via yfinance (not in the tracked universe); reads
AVGO/LLY/Gold from the existing parquet cache. Full-period + last-90d.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from asset_universe import config

DATA_DIR = config.raw_data_dir()


def load(category: str, stem: str) -> pd.Series:
    df = pd.read_parquet(DATA_DIR / category / f"{stem}.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index().dropna()


def main() -> None:
    avgo = load("equities", "AVGO")
    lly = load("equities", "LLY")
    gold = load("commodities", "GC_F")

    btc_df = yf.Ticker("BTC-USD").history(period="3y")
    btc = btc_df["Close"]
    btc.index = pd.to_datetime(btc.index.date)
    btc = btc.sort_index()

    rets = pd.DataFrame({
        "BTC": btc.pct_change(),
        "AVGO": avgo.pct_change(),
        "LLY": lly.pct_change(),
        "Gold": gold.pct_change(),
    }).dropna()

    print(f"BTC-USD history: {btc.index[0].date()} to {btc.index[-1].date()}")
    print(f"Overlapping trading days used: {len(rets)}\n")

    print("Full overlap correlation (daily returns):")
    print(rets.corr().round(3).to_string())

    last90 = rets.tail(90)
    print(f"\nLast 90 trading days ({last90.index[0].date()} to {last90.index[-1].date()}):")
    print(last90.corr().round(3).to_string())

    last252 = rets.tail(252)
    print(f"\nLast 252 trading days ({last252.index[0].date()} to {last252.index[-1].date()}):")
    print(last252.corr().round(3).to_string())


if __name__ == "__main__":
    main()
