"""
Regime change alert + exit priority list.

Runs daily. Checks if RY or BAA10Y has flipped and held for CONFIRM_DAYS.
If confirmed: prints exit priority ranked by 63d degradation, with rotation targets.
If not: prints current regime status and exits cleanly.

Usage:
    python run_regime_alert.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.store import reader

# ── Configuration ─────────────────────────────────────────────────────────────
# Days the new label must hold before the flip is considered confirmed.
# Empirical basis: 47-52% of RY/BAA10Y flips revert within 3 days.
CONFIRM_DAYS = 3

# 63d degradation thresholds for action labels
EXIT_THRESHOLD  = -10.0   # delta_63d below this -> EXIT
WATCH_THRESHOLD =  -3.0   # delta_63d below this -> WATCH
ADD_THRESHOLD   =   3.0   # delta_63d above this -> ADD (all else = HOLD)

# ── Holdings ──────────────────────────────────────────────────────────────────
HOLDINGS = [
    {"name": "Gold",  "ticker": "PPFB.DE", "safe": "PPFB_DE", "cat": "commodities"},
    {"name": "Silver","ticker": "PHAG.L",  "safe": "PHAG_L",  "cat": "commodities"},
    {"name": "LLY",   "ticker": "LLY",     "safe": "LLY",     "cat": "equities"},
    {"name": "WMT",   "ticker": "WMT",     "safe": "WMT",     "cat": "equities"},
    {"name": "CCJ",   "ticker": "CCJ",     "safe": "CCJ",     "cat": "equities"},
    {"name": "VRT",   "ticker": "VRT",     "safe": "VRT",     "cat": "equities"},
    {"name": "AVGO",  "ticker": "AVGO",    "safe": "AVGO",    "cat": "equities"},
    {"name": "HWM",   "ticker": "HWM",     "safe": "HWM",     "cat": "equities"},
]

WATCH_FEATURES = ["ry_regime", "baa10y_regime"]

# Only alert when the new label is an extreme value — MID oscillations are noise.
# Empirical basis: 100% of flips pass through MID; LOW/WIDE are the only
# directional breaks that matter for exit decisions.
TRIGGER_LABELS: dict[str, set[str]] = {
    "ry_regime":     {"LOW"},
    "baa10y_regime": {"WIDE"},
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_prices(data_dir: Path, cat: str, safe: str) -> pd.Series:
    path = reader.ticker_path(data_dir, cat, safe)
    if not path.exists():
        return pd.Series(dtype=float)
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index()


def fwd_return(prices: pd.Series, date: pd.Timestamp, days: int) -> float | None:
    idx = prices.index.searchsorted(date)
    if idx >= len(prices):
        return None
    if abs((prices.index[idx] - date).days) > 5:
        return None
    fwd = idx + days
    if fwd >= len(prices):
        return None
    p0, p1 = prices.iloc[idx], prices.iloc[fwd]
    return (p1 - p0) / p0 if p0 > 0 else None


def compute_stats(labeled_df: pd.DataFrame, conditions: dict,
                  prices: pd.Series, horizon: int) -> tuple[float, float, int]:
    """Returns (median_pct, win_rate_pct, n)."""
    mask = pd.Series(True, index=labeled_df.index)
    for k, v in conditions.items():
        mask &= labeled_df[k] == v
    dates = labeled_df.index[mask]
    rets = [r for dt in dates if (r := fwd_return(prices, dt, horizon)) is not None]
    if len(rets) < 10:
        return float("nan"), float("nan"), len(rets)
    s = pd.Series(rets)
    return round(s.median() * 100, 1), round((s > 0).mean() * 100, 0), len(rets)


def action_label(delta: float) -> str:
    if np.isnan(delta):
        return "N<10"
    if delta < EXIT_THRESHOLD:
        return "EXIT"
    if delta < WATCH_THRESHOLD:
        return "WATCH"
    if delta >= ADD_THRESHOLD:
        return "ADD"
    return "HOLD"


# ── Flip detection ────────────────────────────────────────────────────────────

def check_confirmed_flips(
    labeled_df: pd.DataFrame,
    n_days: int = CONFIRM_DAYS,
) -> dict[str, tuple[str, str]]:
    """
    Returns {col: (old_label, new_label)} for each feature that has flipped
    and held for n_days consecutive days.
    """
    if len(labeled_df) < n_days + 1:
        return {}

    recent = labeled_df[WATCH_FEATURES].tail(n_days + 1).dropna(how="all")
    if len(recent) < n_days + 1:
        return {}

    confirmed: dict[str, tuple[str, str]] = {}
    for col in WATCH_FEATURES:
        if col not in recent.columns:
            continue
        old_label = recent[col].iloc[0]
        window    = recent[col].iloc[1:]
        if pd.isna(old_label) or window.isna().any():
            continue
        new_label = str(window.iloc[0])
        if window.nunique() == 1 and new_label != old_label:
            if col in TRIGGER_LABELS and new_label not in TRIGGER_LABELS[col]:
                continue  # MID oscillation — not an extreme flip, ignore
            confirmed[col] = (str(old_label), new_label)

    return confirmed


def build_new_conditions(
    confirmed_flips: dict[str, tuple[str, str]],
    labeled_df: pd.DataFrame,
) -> dict[str, str]:
    """Current regime labels with confirmed flips applied."""
    last = labeled_df.iloc[-1]
    conditions = {col: str(last[col]) for col in WATCH_FEATURES if col in last.index}
    for col, (_, new_label) in confirmed_flips.items():
        conditions[col] = new_label
    return conditions


def scenario_name(confirmed_flips: dict) -> str:
    parts = []
    for col, (old, new) in confirmed_flips.items():
        feat = col.replace("_regime", "").upper()
        parts.append(f"{feat}: {old}->{new}")
    return " | ".join(parts)


# ── Exit ranking ──────────────────────────────────────────────────────────────

def compute_exit_ranking(
    labeled_df: pd.DataFrame,
    data_dir: Path,
    current_conditions: dict,
    new_conditions: dict,
) -> pd.DataFrame:
    rows = []
    for h in HOLDINGS:
        prices = load_prices(data_dir, h["cat"], h["safe"])
        if prices.empty:
            continue

        cur_63,  cur_win63,  cur_n63  = compute_stats(labeled_df, current_conditions, prices, 63)
        new_63,  new_win63,  new_n63  = compute_stats(labeled_df, new_conditions,     prices, 63)
        cur_252, cur_win252, cur_n252 = compute_stats(labeled_df, current_conditions, prices, 252)
        new_252, new_win252, new_n252 = compute_stats(labeled_df, new_conditions,     prices, 252)

        delta_63  = new_63  - cur_63  if not (np.isnan(new_63)  or np.isnan(cur_63))  else float("nan")
        delta_252 = new_252 - cur_252 if not (np.isnan(new_252) or np.isnan(cur_252)) else float("nan")

        rows.append({
            "name":      h["name"],
            "ticker":    h["ticker"],
            "cur_63":    cur_63,
            "new_63":    new_63,
            "d63":       delta_63,
            "cur_252":   cur_252,
            "new_252":   new_252,
            "d252":      delta_252,
            "action":    action_label(delta_63),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("d63").reset_index(drop=True)


# ── Rotation targets ──────────────────────────────────────────────────────────

def top_rotation_targets(
    labeled_df: pd.DataFrame,
    data_dir: Path,
    new_conditions: dict,
    n: int = 5,
) -> list[dict]:
    screen_path = PROJECT_ROOT / "universe_screen_results.csv"
    if not screen_path.exists():
        return []

    screen_df = pd.read_csv(screen_path)
    current_tickers = {h["ticker"] for h in HOLDINGS}
    top50 = screen_df.head(50)[["ticker", "category"]].to_dict("records")

    rows = []
    for entry in top50:
        tkr = entry["ticker"]
        if tkr in current_tickers:
            continue
        cat_raw = entry.get("category", "")
        if "swedish" in cat_raw.lower() or "equity" in cat_raw.lower():
            cat = "equities"
        elif "commodity" in cat_raw.lower():
            cat = "commodities"
        elif "etf" in cat_raw.lower() or "ucits" in cat_raw.lower():
            cat = "intl_etfs"
        else:
            cat = "equities"

        prices = load_prices(data_dir, cat, reader.safe_name(tkr))
        if prices.empty:
            continue

        med, win, n_obs = compute_stats(labeled_df, new_conditions, prices, 252)
        if np.isnan(med) or n_obs < 10:
            continue
        rows.append({"ticker": tkr, "med252": med, "win252": win, "n": n_obs})

    return sorted(rows, key=lambda x: -x["med252"])[:n]


# ── Output ────────────────────────────────────────────────────────────────────

def print_no_flip(labeled_df: pd.DataFrame) -> None:
    last = labeled_df.iloc[-1]
    ry  = last.get("ry_regime",     "?")
    baa = last.get("baa10y_regime", "?")
    date = str(labeled_df.index[-1].date())
    print(f"  Regime check ({date}): RY={ry}  BAA={baa}  -- no confirmed flip (window={CONFIRM_DAYS}d)")


def print_alert(
    confirmed_flips: dict,
    ranking: pd.DataFrame,
    targets: list[dict],
    labeled_df: pd.DataFrame,
) -> None:
    date = str(labeled_df.index[-1].date())
    scen = scenario_name(confirmed_flips)

    print("=" * 62)
    print(f"  REGIME CHANGE ALERT -- {date}")
    print(f"  {scen}  (confirmed {CONFIRM_DAYS}d)")
    print("=" * 62)

    print(f"\n  EXIT PRIORITY  (63d degradation, ascending = sell first)")
    print(f"  {'Name':<8}  {'Cur 63d':>8}  {'New 63d':>8}  {'d63':>6}  {'252d d':>7}  {'Action':<6}")
    print("  " + "-" * 55)

    for _, row in ranking.iterrows():
        cur = f"{row.cur_63:>+.1f}%" if not np.isnan(row.cur_63) else "  n/a "
        new = f"{row.new_63:>+.1f}%" if not np.isnan(row.new_63) else "  n/a "
        d63 = f"{row.d63:>+.1f}" if not np.isnan(row.d63) else "  n/a"
        d252 = f"{row.d252:>+.1f}" if not np.isnan(row.d252) else "  n/a"
        print(f"  {row['name']:<8}  {cur:>8}  {new:>8}  {d63:>6}  {d252:>7}  {row.action:<6}")

    if targets:
        print(f"\n  ROTATION TARGETS (top {len(targets)} in new regime, 252d median)")
        print(f"  {'Ticker':<10}  {'252d med':>9}  {'Win%':>6}  {'N':>5}")
        print("  " + "-" * 35)
        for t in targets:
            print(f"  {t['ticker']:<10}  {t['med252']:>+8.1f}%  {t['win252']:>5.0f}%  {t['n']:>4}")

    print()


# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    data_dir   = config.raw_data_dir()
    labeled_df, _ = regime_module.build(data_dir)

    confirmed = check_confirmed_flips(labeled_df, CONFIRM_DAYS)

    if not confirmed:
        print_no_flip(labeled_df)
        return

    last = labeled_df.iloc[-1]
    current_conditions = {col: str(last[col]) for col in WATCH_FEATURES if col in last.index}
    new_conditions     = build_new_conditions(confirmed, labeled_df)

    ranking = compute_exit_ranking(labeled_df, data_dir, current_conditions, new_conditions)
    targets = top_rotation_targets(labeled_df, data_dir, new_conditions)

    print_alert(confirmed, ranking, targets, labeled_df)


if __name__ == "__main__":
    main()
