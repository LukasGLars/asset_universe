"""TEMPORARY (2026-10-16). Are the engine's 63d and 252d columns actually
different horizons, or does the regime-end cap collapse them? Delete after."""
from __future__ import annotations
import io, sys
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", write_through=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
import numpy as np, pandas as pd
from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.analysis.engine import query as engine_query

BASE = {"ry_regime": "HIGH", "nominal_10y_regime": "HIGH",
        "baa10y_regime": "TIGHT", "usd_regime": "STRONG"}

lab, _ = regime_module.build(config.raw_data_dir())
mask = pd.Series(True, index=lab.index)
for k, v in BASE.items():
    mask &= lab[k] == v
d = lab.index[mask]
print(f"matched dates under {BASE}: {len(d)}")

# Contiguous spells
spells, start, prev = [], None, None
for ts in d:
    if start is None:
        start = prev = ts; continue
    if (ts - prev).days > 7:
        spells.append((start, prev)); start = ts
    prev = ts
if start is not None:
    spells.append((start, prev))
lens = [(b - a).days for a, b in spells]
print(f"contiguous spells: {len(spells)}")
print(f"  spell length (calendar days): median {np.median(lens):.0f}  "
      f"p25 {np.percentile(lens,25):.0f}  p75 {np.percentile(lens,75):.0f}  max {max(lens)}")
print(f"  spells longer than 63 trading days (~91 cal): "
      f"{sum(1 for l in lens if l > 91)}/{len(lens)}")
print(f"  longer than 252 trading days (~365 cal): {sum(1 for l in lens if l > 365)}/{len(lens)}")

print("\nengine output, 63d vs 252d:")
r = engine_query(BASE, ["GC_F", "LLY", "AVGO"], forward_days=[21, 63, 252])
for t, out in r["results"].items():
    row = []
    for h in ("21d", "63d", "252d"):
        s = out.get(h, {})
        row.append("--" if not s or s.get("insufficient") else f"{s['median']:+.2%} (n={s['n']})")
    same = out.get("63d", {}).get("median") == out.get("252d", {}).get("median")
    print(f"  {t:<6} 21d {row[0]:<18} 63d {row[1]:<18} 252d {row[2]:<18} identical: {same}")
