"""
Tactical entry screen — four gates.

  1. Macro regime     — live from current_regime(), Core 3 + USD
  2. Entry quality    — MA50 extension empirical p33/p67; HIGH excluded
  3. Relative strength — rs_20d > 0 vs benchmark (default SPY)
  4. Catalyst calendar — no earnings within hold_days (default 30)

Forward returns conditioned on gates 1 + 2 simultaneously.
Temporal diversity mandatory on every row.

Usage:
    python run_screen.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import warnings
warnings.filterwarnings("ignore")

from asset_universe import config
from asset_universe.analysis.engine import current_regime, screen_tactical

DATA_DIR   = config.raw_data_dir()
CANDIDATES = ["APH", "GE", "HWM", "GS", "IBKR", "CFG", "RTX", "BNY", "NEM"]
BENCHMARK  = "SPY"
HOLD_DAYS  = 30

# -- Live regime --------------------------------------------------------------

reg = current_regime(DATA_DIR)
BASE_KEYS  = ["ry_regime", "nominal_10y_regime", "baa10y_regime", "usd_regime"]
conditions = {k: reg["regimes"][k] for k in BASE_KEYS if k in reg["regimes"]}

print(f"Regime as of {reg['date']}  (benchmark: {BENCHMARK}, hold: {HOLD_DAYS}d):")
for k, v in conditions.items():
    print(f"  {k.replace('_regime', ''):<18} {v}")
print(f"  Confidence          {reg['confidence']}")
print("  Fetching earnings dates via yfinance...")

# -- Four-gate tactical screen ------------------------------------------------

df = screen_tactical(
    conditions,
    CANDIDATES,
    forward_days=[21, 63, 252],
    benchmark=BENCHMARK,
    hold_days=HOLD_DAYS,
    data_dir=DATA_DIR,
)

all_passed  = df["ticker"].tolist() if not df.empty else []
excluded    = [t for t in CANDIDATES if t not in all_passed]

print(f"\nFour-gate screen  (N>=30, sorted by RS_20d desc):\n")
if df.empty:
    print("  No candidates passed all four gates.")
else:
    print(f"  {'Ticker':<7} {'MA50ext':>8} {'Bkt':>4}  "
          f"{'RS_20d':>7} {'RS_pct':>6}  {'RS_63d':>7} {'RS_pct':>6}  "
          f"{'N21':>5} {'med21':>7} {'W21':>5}  "
          f"{'N63':>5} {'med63':>7} {'W63':>5}  "
          f"{'Div':>8}  {'Earn':<12}")
    print("  " + "-" * 115)

    for _, r in df.iterrows():
        # Flag 252d as unvalidated if THIN
        med252_s = f"{r['med_252d']*100:>+7.1f}%" if r['diversity'] != "THIN" else "  ~unval"
        print(f"  {r['ticker']:<7} {r['ma50_ext']*100:>+7.1f}%  {r['ma50_bucket']:>4}  "
              f"{r['rs_20d']*100:>+6.1f}%  p{r['rs_20d_pct']*100:>2.0f}  "
              f"{r['rs_63d']*100:>+6.1f}%  p{r['rs_63d_pct']*100:>2.0f}  "
              f"{int(r['n_21d']):>5} {r['med_21d']*100:>+6.1f}% {r['win_21d']*100:>4.0f}%  "
              f"{int(r['n_63d']):>5} {r['med_63d']*100:>+6.1f}% {r['win_63d']*100:>4.0f}%  "
              f"[{r['diversity']:>8}]  {r['earn_flag']}")

print(f"\n  Excluded: {excluded}")
print(f"\n  Gates: (1) regime  (2) MA50 not HIGH  (3) rs_20d>0 vs {BENCHMARK}  (4) no earnings <={HOLD_DAYS}d")
print(f"  Diversity: [ROBUST] >10yr, <50% last 3yr  |  [MODERATE] 5-10yr  |  [THIN] <5yr or >80% last 3yr")
print(f"  252d marked ~unval for THIN signals -- temporal sample too short to validate that horizon")
