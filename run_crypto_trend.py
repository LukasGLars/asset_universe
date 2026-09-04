"""
run_crypto_trend.py

Daily signal for the crypto trend sleeve. Thin CLI + dashboard summary around
asset_universe.analysis.crypto_trend, which holds the rule itself.

    python run_crypto_trend.py            # full per-asset detail
    python run_crypto_trend.py --brief    # the two lines fi_tracker prints

The rule is mechanical and state-based: whatever it says today is the target,
regardless of how far the move has already run. There is deliberately no
"wait for a fresh crossover" option -- that discretion is not in the backtest.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import warnings
warnings.filterwarnings("ignore")

try:
    import tomllib
except ImportError:  # py3.10
    import tomli as tomllib  # type: ignore

from asset_universe import config
from asset_universe.analysis import crypto_trend
from asset_universe.store import reader

ROOT = Path(__file__).parent
PORTFOLIO_TOML = ROOT / "config" / "portfolio.toml"


def _sleeve_capital() -> dict[str, float]:
    if not PORTFOLIO_TOML.exists():
        return {}
    with open(PORTFOLIO_TOML, "rb") as f:
        return tomllib.load(f).get("crypto_sleeve", {})


def signals(data_dir: Path | None = None) -> dict[str, dict]:
    """{ticker: signal dict}. A ticker with no data is skipped rather than
    faked -- a missing file must not silently read as FLAT and trigger a sell."""
    data_dir = data_dir or config.raw_data_dir()
    out = {}
    for ticker in crypto_trend.ASSETS:
        path = reader.ticker_path(data_dir, crypto_trend.CATEGORY, ticker)
        if not path.exists():
            continue
        closes = crypto_trend.weekday_closes(reader.load(path))
        if len(closes) < max(crypto_trend.MA_WINDOWS):
            continue
        out[ticker] = crypto_trend.asset_signal(closes)
    return out


def crypto_trend_daily_summary(data_dir: Path | None = None) -> None:
    """Printed into status.md by fi_tracker.py. The Target line is what
    check_signal_changes.py fingerprints -- keep its shape stable."""
    print(f"\n  Crypto Trend Sleeve")
    sig = signals(data_dir)
    if not sig:
        print(f"    Status         : [no crypto data in store -- run python -m asset_universe.update]")
        return

    capital = _sleeve_capital()
    for ticker, s in sig.items():
        name = crypto_trend.ASSETS[ticker]
        held = capital.get(ticker)
        kr = f"  = {held * s['exposure']:,.0f} kr of {held:,.0f} kr".replace(",", " ") if held else ""
        print(f"    {name} ({ticker})  ${s['close']:,.0f}  (as of {s['as_of']})")
        print(f"      Target       : {s['exposure']:.0%}{kr}")
        for st in s["states"]:
            if st["ma"] is None:
                continue
            edge = "long above" if not st["long"] else "flat below"
            lvl = st["upper"] if not st["long"] else st["lower"]
            print(f"      MA{st['window']:<3}        : {'LONG' if st['long'] else 'FLAT':<4} "
                  f"(MA ${st['ma']:,.0f}, {edge} ${lvl:,.0f})")
        if s["last_change"]:
            d, v = s["last_change"]
            print(f"      Last change  : {d} -> {v:.0%}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Crypto trend sleeve daily signal")
    ap.add_argument("--brief", action="store_true", help="one Target line per asset")
    ap.add_argument("--data-dir", type=Path, default=None)
    a = ap.parse_args()

    if a.brief:
        for ticker, s in signals(a.data_dir).items():
            print(f"{ticker}: {s['exposure']:.0%}  (close ${s['close']:,.0f}, as of {s['as_of']})")
        return
    crypto_trend_daily_summary(a.data_dir)
    print("\n  Rule: weekday closes, 50/100/200d SMA, long >MA+2%, flat <MA-2%, "
          "else hold. Target = mean of the three.")
    print("  State-based: act on today's target regardless of how far the move has run.")


if __name__ == "__main__":
    main()
