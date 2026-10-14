"""TEMPORARY (2026-10-14). Intraday BTC/ETH quote straight from yfinance on the
Actions runner, with explicit timestamps. Delete after use."""
from __future__ import annotations
import datetime as dt
import yfinance as yf

print(f"fetched at (UTC): {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M:%S}")
print("=" * 64)
for t in ("BTC-USD", "ETH-USD"):
    tk = yf.Ticker(t)
    last = prev = src = bar_ts = None
    try:
        fi = tk.fast_info
        last = float(fi["last_price"])
        prev = float(fi["previous_close"])
        src = "fast_info"
    except Exception as e:
        print(f"  {t}: fast_info failed ({e})")
    try:
        h = tk.history(period="1d", interval="1m")
        if len(h):
            bar_ts = h.index[-1]
            if last is None:
                last = float(h["Close"].iloc[-1]); src = "1m bar"
    except Exception as e:
        print(f"  {t}: 1m history failed ({e})")
    chg = (last / prev - 1) if (last and prev) else None
    print(f"\n{t}")
    print(f"  last            : {last:,.2f}" if last else "  last            : unavailable")
    print(f"  prev close      : {prev:,.2f}" if prev else "")
    print(f"  change vs prev  : {chg:+.2%}" if chg is not None else "")
    print(f"  source          : {src}")
    print(f"  last 1m bar (UTC): {bar_ts}" if bar_ts is not None else "")
print("=" * 64)
