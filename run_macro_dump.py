"""TEMPORARY (2026-10-20). Dumps two years of weekly macro/market series as
JSON for a one-off reading page. Read-only. Delete after use."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
import pandas as pd
from asset_universe import config
from asset_universe.store import reader

D = config.raw_data_dir()
SERIES = {
    "S&P 500 (SPY)": ("equities", "SPY", "close"), "Nasdaq 100 (QQQ)": ("equities", "QQQ", "close"),
    "VIX": ("volatility", "^VIX", "close"), "Gold": ("commodities", "GC=F", "close"),
    "Oil (WTI)": ("commodities", "CL=F", "close"), "Copper": ("commodities", "HG=F", "close"),
    "Bitcoin": ("crypto", "BTC-USD", "close"), "USD/SEK": ("fx", "USDSEK=X", "close"),
    "Long Treasuries (TLT)": ("fixed_income", "TLT", "close"),
    "10Y yield": ("macro", "DGS10", "value"), "10Y real yield": ("macro", "DFII10", "value"),
    "10Y breakeven": ("macro", "T10YIE", "value"), "10Y-2Y curve": ("macro", "T10Y2Y", "value"),
    "10Y-3M curve": ("macro", "T10Y3M", "value"), "HY credit spread": ("macro", "BAMLH0A0HYM2", "value"),
    "IG spread (Baa-10Y)": ("macro", "BAA10Y", "value"), "Dollar index (broad)": ("macro", "DTWEXBGS", "value"),
    "Unemployment": ("macro", "UNRATE", "value"), "Initial claims": ("macro", "ICSA", "value"),
    "Core PCE index": ("macro", "PCEPILFE", "value"),
    "Broadcom": ("equities", "AVGO", "close"), "Eli Lilly": ("equities", "LLY", "close"),
}
out = {"series": {}, "latest": {}}
for name, (cat, tkr, col) in SERIES.items():
    try:
        df = pd.read_parquet(reader.ticker_path(D, cat, tkr))
    except Exception as e:
        print(f"skip {name}: {e}", file=sys.stderr); continue
    s = df.assign(date=pd.to_datetime(df["date"])).set_index("date")[col].dropna().sort_index()
    s = s.loc[s.index[-1] - pd.Timedelta(days=760):]
    w = s.resample("W-FRI").last().dropna()
    out["series"][name] = [[d.strftime("%Y-%m-%d"), round(float(v), 4)] for d, v in w.items()]
    def at(days):
        sub = s.loc[: s.index[-1] - pd.Timedelta(days=days)]
        return float(sub.iloc[-1]) if len(sub) else None
    ytd = s.loc[: f"{s.index[-1].year - 1}-12-31"]
    out["latest"][name] = {"date": s.index[-1].strftime("%Y-%m-%d"), "last": round(float(s.iloc[-1]), 4),
                           "w1": at(7), "m1": at(30), "y1": at(365),
                           "ytd0": float(ytd.iloc[-1]) if len(ytd) else None}
print("JSON_BEGIN"); print(json.dumps(out, separators=(",", ":"))); print("JSON_END")
