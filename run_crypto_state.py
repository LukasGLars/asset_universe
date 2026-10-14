"""TEMPORARY (2026-10-14). Live BTC/ETH state against the trend sleeve's own
rule. Every number is read from asset_universe.analysis.crypto_trend --
nothing about the bands is restated here. Delete after use."""
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

print("=" * 72)
print(f"CRYPTO TREND SLEEVE -- windows {ct.MA_WINDOWS}, hysteresis {ct.BAND:.0%}")
print("=" * 72)
for tick in ("BTC-USD", "ETH-USD"):
    df = reader.load(reader.ticker_path(config.raw_data_dir(), "crypto", tick))
    closes = ct.weekday_closes(df)          # takes the DataFrame, not a Series
    sig = ct.asset_signal(closes)
    px = sig["close"]
    print(f"\n{tick}   {px:>12,.2f}   as of {sig['as_of']}")
    print(f"  target exposure : {sig['exposure']:.0%}")
    for st in sig["states"]:
        if st["ma"] is None:
            print(f"  MA{st['window']:<4} (insufficient history)")
            continue
        room = px / st["lower"] - 1
        print(f"  MA{st['window']:<4} {st['ma']:>11,.2f}   "
              f"{'LONG' if st['long'] else 'FLAT':<5} "
              f"flat below {st['lower']:>11,.2f}   room {room:>+7.1%}")
    lc = sig["last_change"]
    print(f"  last change     : {lc[0]} -> {lc[1]:.0%}" if lc else "  last change     : none")
    full = df["close"].dropna()
    dd = full / full.cummax() - 1
    print(f"  drawdown now    : {float(dd.iloc[-1]):+.1%}   "
          f"median {float(dd.median()):+.1%}   "
          f"deeper on {float((dd < dd.iloc[-1]).mean()):.0%} of sessions")
print("=" * 72)
