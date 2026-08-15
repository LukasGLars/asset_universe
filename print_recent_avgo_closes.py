"""Temporary one-off: print AVGO's last 10 closes + 5d ROC threshold price for the next close."""
from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from asset_universe import config
import pandas as pd

DATA_DIR = config.raw_data_dir()
df = pd.read_parquet(DATA_DIR / "equities" / "AVGO.parquet")
df["date"] = pd.to_datetime(df["date"])
s = df.set_index("date")["close"].sort_index().dropna()
print(s.tail(10))
ref = s.iloc[-5]
print(f"\n5-trading-days-back reference (for next close's 5d ROC): {s.index[-5].date()} = ${ref:.2f}")
print(f"Next close would need to be <= ${ref * 0.90:.2f} to trigger crash-ROC (-10%)")
