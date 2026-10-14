"""TEMPORARY (2026-10-14). Current BTC/ETH price against the live trend-sleeve
rule: the MA50/100/200 ensemble and its 2% hysteresis band. Delete after use."""
from __future__ import annotations
import io, sys
from pathlib import Path
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", write_through=True)
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from asset_universe import config
from asset_universe.store import reader
from asset_universe.analysis import crypto_trend as ct

print("=" * 70)
print("CRYPTO TREND SLEEVE -- live state")
print(f"windows {ct.MA_WINDOWS}   hysteresis band {ct.BAND:.0%}")
print("=" * 70)
for tick in ("BTC-USD", "ETH-USD"):
    s = reader.load(reader.ticker_path(config.raw_data_dir(), "crypto", tick))["close"].dropna()
    wk = ct.weekday_closes(s)
    px = float(wk.iloc[-1])
    print(f"\n{tick}   {px:>12,.2f}   as of {wk.index[-1].date()}")
    print(f"  target exposure : {ct.target_exposure(wk):.0%}")
    for w in ct.MA_WINDOWS:
        ma = float(wk.iloc[-w:].mean())
        flat = ma * (1 - ct.BAND)
        state = "LONG" if px > ma * (1 + ct.BAND) else ("FLAT" if px < flat else "HOLD-BAND")
        room = px / flat - 1
        print(f"  MA{w:<4} {ma:>11,.2f}   {state:<10} flat below {flat:>11,.2f}"
              f"   room {room:>+7.1%}")
    ch = ct.last_change(wk)
    print(f"  last change     : {ch}")
    dd = s / s.cummax() - 1
    print(f"  drawdown now    : {float(dd.iloc[-1]):+.1%}   "
          f"median {float(dd.median()):+.1%}   "
          f"deeper on {float((dd < dd.iloc[-1]).mean()):.0%} of sessions")
print("=" * 70)
