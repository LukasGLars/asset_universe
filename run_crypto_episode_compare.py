"""
run_crypto_episode_compare.py

TEMPORARY DIAGNOSTIC (2026-09-24). "How do BTC/ETH look now versus how they
behaved after previous buy triggers?" -- with the current trade still open.

Reuses the LIVE rule (analysis.crypto_trend.exposure_series) rather than
reimplementing it, so the episodes here are exactly the ones the sleeve
would have taken: weekday closes, 50/100/200d MAs, 2% hysteresis band,
target = mean of the three states.

An EPISODE starts when exposure rises from 0 and ends when it returns to 0.
The live episode (entered 2026-08-21 at 100%) is measured the same way and
compared against the closed ones at the SAME age, which is the only honest
comparison while it is still open -- a 23-weekday-old trade cannot be judged
against finished trades' final returns.

Report-only. Delete after logging.
"""
from __future__ import annotations
import io, sys
from pathlib import Path

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", write_through=True)

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from asset_universe import config
from asset_universe.store import reader
from asset_universe.analysis import crypto_trend as ct


def episodes(closes: pd.Series) -> list[dict]:
    """Contiguous stretches with non-zero exposure."""
    exp = ct.exposure_series(closes)
    out, start = [], None
    for i, (d, e) in enumerate(exp.items()):
        if e > 0 and start is None:
            start = i
        elif e == 0 and start is not None:
            out.append({"i0": start, "i1": i - 1})
            start = None
    if start is not None:
        out.append({"i0": start, "i1": len(exp) - 1, "open": True})
    for ep in out:
        seg = closes.iloc[ep["i0"]:ep["i1"] + 1]
        ep.update(entry=closes.index[ep["i0"]], exit=closes.index[ep["i1"]],
                  ep_px=float(seg.iloc[0]), last_px=float(seg.iloc[-1]),
                  bars=len(seg), seg=seg,
                  ret=float(seg.iloc[-1] / seg.iloc[0] - 1),
                  mdd=float((seg / seg.cummax() - 1).min()),
                  peak=float(seg.max() / seg.iloc[0] - 1),
                  open=ep.get("open", False))
    return out


def main() -> None:
    d = config.raw_data_dir()
    for sym, name in ct.ASSETS.items():
        df = pd.read_parquet(reader.ticker_path(d, ct.CATEGORY, sym))
        df["date"] = pd.to_datetime(df["date"])
        closes = ct.weekday_closes(df.set_index("date").sort_index())
        eps = episodes(closes)
        closed = [e for e in eps if not e["open"]]
        live = next((e for e in eps if e["open"]), None)

        print("=" * 76)
        print(f"{name} ({sym})   last {closes.iloc[-1]:,.0f} "
              f"on {closes.index[-1].date()}   history from {closes.index[0].date()}")
        print("=" * 76)

        print(f"\nCLOSED EPISODES ({len(closed)}):")
        print(f"  {'entry':<12}{'exit':<12}{'bars':>6}{'ret':>9}{'peak':>9}{'maxDD':>9}")
        for e in closed:
            print(f"  {str(e['entry'].date()):<12}{str(e['exit'].date()):<12}"
                  f"{e['bars']:>6}{e['ret']:>9.1%}{e['peak']:>9.1%}{e['mdd']:>9.1%}")
        if closed:
            r = pd.Series([e["ret"] for e in closed])
            b = pd.Series([e["bars"] for e in closed])
            print(f"\n  median ret {r.median():+.1%}   mean {r.mean():+.1%}   "
                  f"win {(r > 0).mean():.0%}   median length {b.median():.0f} bars")

        if not live:
            print("\n  No open episode.\n")
            continue

        age = live["bars"]
        print(f"\nLIVE EPISODE  entered {live['entry'].date()} at "
              f"{live['ep_px']:,.0f}  -> {live['last_px']:,.0f}")
        print(f"  age {age} bars   return {live['ret']:+.1%}   "
              f"peak {live['peak']:+.1%}   maxDD since entry {live['mdd']:+.1%}")

        # Apples to apples: where were the closed episodes at this same age?
        same = []
        for e in closed:
            if e["bars"] >= age:
                same.append(float(e["seg"].iloc[age - 1] / e["seg"].iloc[0] - 1))
        print(f"\n  AT THE SAME AGE ({age} bars), closed episodes that lasted "
              f"this long (n={len(same)}):")
        if same:
            s = pd.Series(same)
            pct = float((s < live["ret"]).mean())
            print(f"    median {s.median():+.1%}   range {s.min():+.1%} .. {s.max():+.1%}"
                  f"   win {(s > 0).mean():.0%}")
            print(f"    live at {live['ret']:+.1%}  ->  better than "
                  f"{pct:.0%} of them at this point")
        else:
            print("    none ran this long -- this episode is already older than "
                  "every closed one")

        # How did those that were ahead at this age finish?
        fin = [e["ret"] for e in closed
               if e["bars"] >= age and e["seg"].iloc[age - 1] / e["seg"].iloc[0] - 1 > 0]
        if fin:
            f = pd.Series(fin)
            print(f"\n  Of those UP at {age} bars (n={len(f)}): finished median "
                  f"{f.median():+.1%}, win {(f > 0).mean():.0%}, "
                  f"worst {f.min():+.1%}")
        print()


if __name__ == "__main__":
    main()
