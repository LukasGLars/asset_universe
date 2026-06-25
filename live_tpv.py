import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from asset_universe import config
from asset_universe.store import reader
from asset_universe.download.tv import fetch_price
import pandas as pd

DATA_DIR = config.raw_data_dir()

def latest(category, ticker):
    path = reader.ticker_path(DATA_DIR, category, ticker)
    df = pd.read_parquet(path)
    col = "close" if "close" in df.columns else "value"
    return float(df[col].dropna().iloc[-1])

usdsek = latest("fx", "USDSEK=X")
eursek = latest("fx", "EURSEK=X")

positions = [
    ("PPFB.DE", "EUR",  250, "tv"),
    ("VZLC.DE", "EUR",   66, "tv"),
    ("LLY",     "USD",   14, "equities"),
    ("WMT",     "USD",  126, "equities"),
    ("CCJ",     "USD",   93, "equities"),
    ("VRT",     "USD",   31, "equities"),
    ("AVGO",    "USD",   21, "equities"),
]

manual = [("Spiltan", 279453), ("War Chest", 34205)]

print(f"USDSEK: {usdsek:.3f}   EURSEK: {eursek:.3f}")
print()
print(f"{'Position':<16} {'Shr':>5} {'Price':>9} {'SEK/sh':>9} {'Value SEK':>12}  src")
print("-" * 60)

total = 0.0
for ticker, ccy, shares, src in positions:
    price = fetch_price(ticker) if src == "tv" else latest(src, ticker)
    fx    = eursek if ccy == "EUR" else usdsek
    sek   = price * fx
    val   = sek * shares
    total += val
    lbl = src if src == "tv" else "parquet"
    print(f"  {ticker:<14} {shares:>5} {price:>9.3f} {sek:>9.0f} kr {val:>10,.0f} kr  {lbl}")

print()
for name, val in manual:
    total += val
    print(f"  {name:<14} {'—':>5}  {'manual':>9} {'':>9}    {val:>10,.0f} kr")

print("-" * 60)
print(f"  MY TPV         :  {total:>12,.0f} kr")
print(f"  YOUR TPV       :   1,110,427 kr")
print(f"  Diff           :  {1110427 - total:>+12,.0f} kr")
