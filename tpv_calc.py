import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from asset_universe import config
from asset_universe.store import reader
import pandas as pd

DATA_DIR = config.raw_data_dir()

def latest(category, ticker):
    path = reader.ticker_path(DATA_DIR, category, ticker)
    if not path.exists():
        return None, None
    df = pd.read_parquet(path)
    col = "close" if "close" in df.columns else "value"
    df["date"] = pd.to_datetime(df["date"])
    return float(df[col].dropna().iloc[-1]), df["date"].iloc[-1].date()

usdsek, _ = latest("fx", "USDSEK=X")
eursek, d = latest("fx", "EURSEK=X")

positions = [
    ("PPFB.DE",  "commodities", 250, "EUR", "PPFB.DE (gold)"),
    ("PHAG.L",   "commodities",  66, "USD", "VZLC.DE proxy"),
    ("LLY",      "equities",     14, "USD", "Eli Lilly"),
    ("WMT",      "equities",    126, "USD", "Walmart"),
    ("CCJ",      "equities",     93, "USD", "Cameco"),
    ("VRT",      "equities",     31, "USD", "Vertiv"),
    ("AVGO",     "equities",     21, "USD", "Broadcom"),
]

manual = [
    ("Spiltan",   279453, "Home Base"),
    ("War Chest",  34205, "Home Base"),
]

print("Prices as of:", d)
print("USDSEK:", round(usdsek, 3), "  EURSEK:", round(eursek, 3))
print()
print(f"{'Position':<18} {'Shr':>5} {'Local':>9} {'SEK/sh':>9} {'Value SEK':>12}")
print("-" * 57)

total = 0.0
for ticker, cat, shares, ccy, label in positions:
    price, _ = latest(cat, ticker)
    if price is None:
        print(f"  {label:<16} {shares:>5}   NO DATA")
        continue
    fx  = eursek if ccy == "EUR" else usdsek
    sek = price * fx
    val = sek * shares
    total += val
    print(f"  {label:<16} {shares:>5} {price:>9.2f} {sek:>9.0f} kr {val:>10,.0f} kr")

print()
for name, val, bucket in manual:
    total += val
    print(f"  {name:<16} {'—':>5} {'manual':>9} {'':>9}    {val:>10,.0f} kr")

print("-" * 57)
print(f"  {'TPV':<16} {'':>5} {'':>9} {'':>9}    {total:>10,.0f} kr")
print()
print(f"  Sheet TPV  (live Avanza) :  1,118,517 kr")
print(f"  Parquet TPV (prev close) :  {total:,.0f} kr")
diff = 1118517 - total
print(f"  Gap                      :  {diff:+,.0f} kr  ({diff/1118517*100:+.1f}%)")
