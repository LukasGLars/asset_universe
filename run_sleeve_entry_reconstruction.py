"""
run_sleeve_entry_reconstruction.py

Point-in-time reconstruction of the opportunistic sleeve's entry logic
(run_entry_screen.py / screen_tactical() in engine.py), so the exit-duration
question logged in MEMORY.md's research backlog can finally be tested against
the sleeve's REAL historical entry population instead of a proxy one.

Why this exists (see MEMORY.md "Opportunistic sleeve's 30-day time exit..."
and PR #40): the live screen's 4 gates -- regime top-N, above-MA50,
extension<=p67 + RS20d>0, earnings-clear -- are all built around
`_date.today()` / `prices.iloc[-1]`. PR #40 tried to test TIME_EXIT_DAYS=30
by sweeping duration_matched_return() over all regime-matched dates for
top-ranked momentum names -- NOT the same population as the sleeve's actual
gated entries (dip/extension-filtered, RS-checked). That PR's own report
explicitly disclaims its numbers for this reason.

This script rebuilds all 4 gates so they can be evaluated at ANY historical
date, using only data available up to that date:

  Gate 1 (regime top-N)   -- same walk-forward, no-lookahead ranking as
                              run_sleeve_backtest.py: at each confirmed
                              regime transition, rank candidates by their
                              PRE-transition median 252d regime-conditional
                              return, freeze the top TOP_N list for the
                              whole subsequent regime period (matches that
                              script's already-accepted methodology).
  Gate 2 (above MA50)      -- price > rolling 50d MA, as of the date.
  Gate 3 (extension+RS)    -- MA50 extension <= the p67 threshold computed
                              from ONLY pre-transition matched dates (frozen
                              per period, same reasoning as gate 1), AND
                              trailing-20d return > the benchmark's.
  Gate 4 (earnings-clear)  -- next earnings date (from yfinance's FULL
                              earnings_dates history, not the >=today-
                              filtered _next_earnings()) more than HOLD_DAYS
                              away. Confirmed 2026-07-07: yfinance's
                              get_earnings_dates(limit=60) returns AVGO's
                              complete history back to 2009-12-03 (its IPO
                              era) -- the "yfinance only exposes the current
                              earnings calendar" limitation logged against
                              PR #40 was a property of _next_earnings()'s own
                              >=today filter, not of the underlying data.
                              Missing earnings data defaults to PASS, same as
                              the live screen (screen_tactical: earn_days is
                              None -> gate does not exclude).

Consecutive qualifying days for the same ticker are decluttered (minimum
TIME_EXIT_DAYS gap) so the output is a population of realistic, roughly
independent trade instances, not an autocorrelated run of near-identical
daily observations.

Deliberately NOT built here (bigger, separate task): a full compound-exit
simulation (MA50 breach / hard stop / earnings-buffer all racing against the
time exit). This script measures raw forward-return-by-duration for the REAL
gated-entry population -- an upgrade over PR #40's population, but still a
population-level statistic, not a trade-by-trade P&L simulator. See
MEMORY.md research backlog for that follow-on scope.

Self-check: truncating all data to <=2026-06-24 and re-running must surface
HWM as a top-TOP_N, all-gates-clear candidate on that date -- the same
ground-truth case PR #5 validated the live screen against.

Output: comparison_results/sleeve_entry_duration_grid.csv + console summary.
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.store import reader

DATA_DIR = config.raw_data_dir()
OUT_CSV  = PROJECT_ROOT / "comparison_results" / "sleeve_entry_duration_grid.csv"

# Mirrors run_sleeve_backtest.py's candidate universe (not imported -- that
# script has side-effecting top-level code, including its own sys.stdout
# rewrap, which double-wraps and closes the shared buffer if imported).
EXCLUDE = {
    "GC_F", "AVGO", "LLY",    # in base
    "PPFB_DE", "PHAG_L",       # ETC tickers with TV data / limited history
    "SI_F",                    # silver — covered by T1/T2 tactical rule separately
}
MIN_HISTORY_DAYS = 756   # 3 years before selecting an asset

TOP_N            = 30    # matches run_entry_screen.py's --top-n default
HOLD_DAYS        = 21    # matches screen_tactical()'s default hold_days (earnings gate)
CONFIRM_DAYS     = 5     # matches run_sleeve_backtest.py
MIN_REGIME_DATES = 15    # matches run_sleeve_backtest.py
MIN_N_OBS        = 10    # minimum entries per duration cell to report a stat
DECLUSTER_DAYS   = 30    # minimum gap between counted entries for the same ticker
FWD_DAYS_RANK    = 252   # ranking horizon, matches run_sleeve_backtest.py

DURATION_GRID = [15, 21, 30, 45, 60, 90]   # calendar days

BENCHMARK = "SPY"


# ── Candidate universe ───────────────────────────────────────────────────────

def load_candidates(data_dir: Path, cutoff: pd.Timestamp | None = None) -> dict[str, tuple[str, pd.Series]]:
    """Same universe as run_sleeve_backtest.py: all equities + commodities,
    minus the base assets and known-bad tickers. `cutoff` truncates history
    (used by the HWM self-check to reproduce a past as-of state)."""
    out: dict[str, tuple[str, pd.Series]] = {}
    for cat_dir in ("equities", "commodities"):
        d = data_dir / cat_dir
        if not d.exists():
            continue
        for path in sorted(d.glob("*.parquet")):
            t = path.stem
            if t in EXCLUDE:
                continue
            prices = reader.load(path)["close"].dropna().sort_index()
            if cutoff is not None:
                prices = prices[prices.index <= cutoff]
            if len(prices) >= 50:
                out[t] = (cat_dir, prices)
    return out


# ── Gate 1: no-lookahead regime-transition ranking (mirrors run_sleeve_backtest.py) ──

def detect_transitions(labeled_df: pd.DataFrame) -> list[tuple[pd.Timestamp, str, str]]:
    combo = (labeled_df["ry_regime"].astype(str) + "_" + labeled_df["baa10y_regime"].astype(str)).dropna()
    transitions: list[tuple[pd.Timestamp, str, str]] = []
    i = 0
    while i < len(combo):
        if i == 0:
            ry, baa = combo.iloc[i].split("_", 1)
            transitions.append((combo.index[i], ry, baa))
            i += 1
            continue
        if combo.iloc[i] != combo.iloc[i - 1]:
            new_label = combo.iloc[i]
            end = min(i + CONFIRM_DAYS, len(combo))
            if all(combo.iloc[j] == new_label for j in range(i, end)):
                ry, baa = new_label.split("_", 1)
                transitions.append((combo.index[i], ry, baa))
        i += 1
    return transitions


def regime_median_return(prices: pd.Series, matched_dates: pd.DatetimeIndex, fwd_days: int = FWD_DAYS_RANK) -> float | None:
    rets = []
    for d in matched_dates:
        idx = prices.index.searchsorted(d)
        if idx >= len(prices) or abs((prices.index[idx] - d).days) > 5:
            continue
        end = idx + fwd_days
        if end >= len(prices):
            continue
        p0, p1 = prices.iloc[idx], prices.iloc[end]
        if p0 > 0:
            rets.append((p1 - p0) / p0)
    return float(np.median(rets)) if len(rets) >= MIN_REGIME_DATES else None


def rank_at_transitions(
    transitions: list[tuple[pd.Timestamp, str, str]],
    labeled_df: pd.DataFrame,
    candidates: dict[str, tuple[str, pd.Series]],
) -> list[dict]:
    """Walk-forward: at each transition, rank candidates using ONLY
    pre-transition price history and ONLY pre-transition matched regime
    dates. Also freezes the extension-percentile thresholds (p33/p67) each
    ticker will use for the whole subsequent period, from the same
    pre-transition matched dates -- same no-lookahead reasoning as the rank
    itself."""
    selections: list[dict] = []
    for t_date, ry_new, baa_new in transitions:
        hist = labeled_df[labeled_df.index < t_date]
        mask = (hist["ry_regime"] == ry_new) & (hist["baa10y_regime"] == baa_new)
        matched = hist.index[mask]

        if len(matched) < MIN_REGIME_DATES:
            if selections:
                prev = selections[-1].copy()
                prev["t_date"] = t_date
                selections.append(prev)
            continue

        ranked: list[tuple[str, float]] = []
        for ticker, (_cat, prices) in candidates.items():
            pre_prices = prices[prices.index < t_date]
            if len(pre_prices) < MIN_HISTORY_DAYS:
                continue
            med = regime_median_return(pre_prices, matched)
            if med is not None:
                ranked.append((ticker, med))
        ranked.sort(key=lambda x: x[1], reverse=True)
        top = [r[0] for r in ranked[:TOP_N]]

        # Freeze extension-percentile thresholds per top-N ticker for this period.
        ext_thresholds: dict[str, float] = {}
        for ticker in top:
            _cat, prices = candidates[ticker]
            pre_prices = prices[prices.index < t_date]
            ma50 = pre_prices.rolling(50, min_periods=25).mean()
            ext = pre_prices / ma50 - 1
            ext_on_matched = ext.reindex(matched).dropna()
            if len(ext_on_matched) >= MIN_N_OBS:
                ext_thresholds[ticker] = float(ext_on_matched.quantile(0.6667))

        selections.append({
            "t_date": t_date, "ry": ry_new, "baa": baa_new,
            "top": top, "p67": ext_thresholds,
        })
    return selections


def current_selection(selections: list[dict], date: pd.Timestamp) -> dict | None:
    for sel in reversed(selections):
        if sel["t_date"] <= date:
            return sel
    return None


# ── Gate 4: point-in-time earnings-clear, from yfinance's FULL history ──────

_earnings_cache: dict[str, np.ndarray] = {}


def _earnings_dates(ticker: str) -> np.ndarray:
    """Full historical + upcoming earnings dates for `ticker`, sorted.
    Cached per-ticker (one network call each, not one per date checked).
    Confirmed 2026-07-07: unlike _next_earnings() in engine.py (which
    filters to >=today), the raw get_earnings_dates() dataframe already
    contains the complete point-in-time record -- e.g. AVGO back to
    2009-12-03. Returns empty array on any fetch failure (gate then passes
    by default, matching screen_tactical's own missing-data behavior)."""
    if ticker in _earnings_cache:
        return _earnings_cache[ticker]
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).get_earnings_dates(limit=60)
        dates = np.array(sorted(d.replace(tzinfo=None) if d.tzinfo else d for d in df.index.to_pydatetime()),
                          dtype="datetime64[ns]") if df is not None and not df.empty else np.array([], dtype="datetime64[ns]")
    except Exception:
        dates = np.array([], dtype="datetime64[ns]")
    _earnings_cache[ticker] = dates
    return dates


def earnings_clear(ticker: str, as_of: pd.Timestamp, hold_days: int = HOLD_DAYS) -> bool:
    dates = _earnings_dates(ticker)
    if len(dates) == 0:
        return True  # missing data -> gate does not exclude, matches live screen
    as_of64 = np.datetime64(as_of)
    future = dates[dates >= as_of64]
    if len(future) == 0:
        return True
    days_to_next = (future[0] - as_of64) / np.timedelta64(1, "D")
    return bool(days_to_next > hold_days)


# ── Full gate check + declustered entry-event extraction ───────────────────

def find_gated_entries(
    selections: list[dict],
    candidates: dict[str, tuple[str, pd.Series]],
    bm_prices: pd.Series,
) -> list[dict]:
    """For every date in every regime period, check gates 2-4 for that
    period's frozen top-N list (gate 1). Returns raw (pre-decluster)
    passing (ticker, date) events."""
    bm_ret_20d = bm_prices.pct_change(20)

    # Precompute rolling MA50 + trailing-20d-return series once per ticker
    # that ever appears in a top-N list (not the full 500+ universe).
    all_top_tickers = {t for sel in selections for t in sel["top"]}
    ma50_by_ticker: dict[str, pd.Series] = {}
    ret20_by_ticker: dict[str, pd.Series] = {}
    for ticker in all_top_tickers:
        _cat, prices = candidates[ticker]
        ma50_by_ticker[ticker] = prices.rolling(50, min_periods=25).mean()
        ret20_by_ticker[ticker] = prices.pct_change(20)

    events: list[dict] = []
    for sel_idx, sel in enumerate(selections):
        start = sel["t_date"]
        end = selections[sel_idx + 1]["t_date"] if sel_idx + 1 < len(selections) else None
        for ticker in sel["top"]:
            if ticker not in sel["p67"]:
                continue
            p67 = sel["p67"][ticker]
            _cat, prices = candidates[ticker]
            ma50 = ma50_by_ticker[ticker]
            ret20 = ret20_by_ticker[ticker]

            period_dates = prices.index[(prices.index >= start) & (prices.index < end if end is not None else True)]
            for d in period_dates:
                price, ma = prices.loc[d], ma50.loc[d]
                if pd.isna(ma) or price <= ma:
                    continue  # gate 2: above MA50
                ext = price / ma - 1
                if ext > p67:
                    continue  # gate 3a: extension
                r20 = ret20.loc[d] if d in ret20.index else None
                b20 = bm_ret_20d.loc[d] if d in bm_ret_20d.index else None
                if r20 is None or b20 is None or pd.isna(r20) or pd.isna(b20) or (r20 - b20) <= 0:
                    continue  # gate 3b: RS vs benchmark
                if not earnings_clear(ticker, d):
                    continue  # gate 4: earnings
                events.append({"ticker": ticker, "date": d})
    return events


def decluster(events: list[dict], min_gap_days: int = DECLUSTER_DAYS) -> list[dict]:
    """Keep only the first qualifying date per ticker per DECLUSTER_DAYS
    window, so a long run of consecutive qualifying days (MA50/extension
    move slowly) doesn't get counted as many independent trades."""
    by_ticker: dict[str, list[dict]] = {}
    for e in events:
        by_ticker.setdefault(e["ticker"], []).append(e)

    kept: list[dict] = []
    for ticker, evs in by_ticker.items():
        evs.sort(key=lambda e: e["date"])
        last_kept = None
        for e in evs:
            if last_kept is None or (e["date"] - last_kept).days >= min_gap_days:
                kept.append(e)
                last_kept = e["date"]
    return kept


# ── Forward returns at each duration, for the real entry population ────────

def forward_return(prices: pd.Series, entry_date: pd.Timestamp, calendar_days: int) -> float | None:
    target = entry_date + pd.Timedelta(days=calendar_days)
    idx = prices.index.searchsorted(target)
    if idx >= len(prices):
        return None
    if abs((prices.index[idx] - target).days) > 5:
        return None
    p0_idx = prices.index.searchsorted(entry_date)
    if p0_idx >= len(prices) or abs((prices.index[p0_idx] - entry_date).days) > 5:
        return None
    p0, p1 = prices.iloc[p0_idx], prices.iloc[idx]
    return (p1 - p0) / p0 if p0 > 0 else None


def duration_stats(entries: list[dict], candidates: dict[str, tuple[str, pd.Series]]) -> pd.DataFrame:
    rows = []
    for calendar_days in DURATION_GRID:
        rets = []
        for e in entries:
            _cat, prices = candidates[e["ticker"]]
            r = forward_return(prices, e["date"], calendar_days)
            if r is not None:
                rets.append(r)
        n = len(rets)
        if n < MIN_N_OBS:
            rows.append({"calendar_days": calendar_days, "n": n, "median_return": float("nan"),
                         "win_rate": float("nan"), "annualized_median": float("nan")})
            continue
        s = pd.Series(rets)
        med = float(s.median())
        annualized = (1 + med) ** (365.25 / calendar_days) - 1
        rows.append({
            "calendar_days": calendar_days, "n": n,
            "median_return": round(med, 4),
            "win_rate": round(float((s > 0).mean()), 4),
            "annualized_median": round(annualized, 4),
        })
    return pd.DataFrame(rows)


# ── Self-check: HWM must surface as of 2026-06-24, same as PR #5's validation ──

def hwm_self_check(labeled_df: pd.DataFrame, data_dir: Path) -> None:
    cutoff = pd.Timestamp("2026-06-24")
    candidates = load_candidates(data_dir, cutoff=cutoff)
    labeled_cut = labeled_df[labeled_df.index <= cutoff]
    transitions = detect_transitions(labeled_cut)
    selections = rank_at_transitions(transitions, labeled_cut, candidates)
    sel = current_selection(selections, cutoff)
    if sel is None:
        print("SELF-CHECK FAILED: no regime selection found as of 2026-06-24")
        return
    if "HWM" not in sel["top"]:
        print(f"SELF-CHECK FAILED: HWM not in top-{TOP_N} as of 2026-06-24 "
              f"(got {sel['top'][:10]}...)")
        return
    rank = sel["top"].index("HWM") + 1
    print(f"SELF-CHECK: HWM rank {rank} of {TOP_N} as of 2026-06-24 "
          f"(PR #5 found rank 9 — some drift expected, different candidate "
          f"universe snapshot / regime rebuild since then; not-present would be the real failure)")
    if "HWM" not in sel["p67"]:
        print("SELF-CHECK: not enough matched dates to freeze an extension threshold for HWM")
        return

    _cat, prices = candidates["HWM"]
    ma50 = prices.rolling(50, min_periods=25).mean()
    price, ma = prices.iloc[-1], ma50.iloc[-1]
    ext = price / ma - 1
    clears_ext = ext <= sel["p67"]["HWM"]
    print(f"SELF-CHECK: HWM above MA50: {price > ma}, extension {ext:.3f} "
          f"<= p67 {sel['p67']['HWM']:.3f}: {clears_ext}")

    bm_path = reader.ticker_path(data_dir, "equities", BENCHMARK)
    bm_prices = reader.load(bm_path)["close"].dropna().sort_index()
    bm_prices = bm_prices[bm_prices.index <= cutoff]
    r20 = float(prices.pct_change(20).iloc[-1])
    b20 = float(bm_prices.pct_change(20).iloc[-1])
    print(f"SELF-CHECK: HWM RS 20d: {r20:.3f} vs benchmark {b20:.3f}: {r20 > b20}")
    print(f"SELF-CHECK: HWM earnings-clear as of 2026-06-24 (hold {HOLD_DAYS}d): "
          f"{earnings_clear('HWM', cutoff)}")


def main() -> None:
    print("Building regime labels...")
    labeled_df, _ = regime_module.build(DATA_DIR)

    print("Self-check: HWM as of 2026-06-24...")
    hwm_self_check(labeled_df, DATA_DIR)

    print("Loading full candidate universe...")
    candidates = load_candidates(DATA_DIR)
    print(f"Candidates: {len(candidates)}")

    print("Detecting regime transitions...")
    transitions = detect_transitions(labeled_df)
    print(f"Transitions: {len(transitions)}")

    print(f"Walk-forward ranking (top {TOP_N}) at each transition...")
    selections = rank_at_transitions(transitions, labeled_df, candidates)

    print("Loading benchmark (SPY)...")
    bm_path = reader.ticker_path(DATA_DIR, "equities", BENCHMARK)
    bm_prices = reader.load(bm_path)["close"].dropna().sort_index()

    print("Scanning full history for gate-clearing (ticker, date) events...")
    raw_events = find_gated_entries(selections, candidates, bm_prices)
    print(f"Raw gate-clearing events: {len(raw_events)}")

    entries = decluster(raw_events)
    print(f"Declustered entry population (>= {DECLUSTER_DAYS}d apart per ticker): {len(entries)}")

    print("Computing forward returns by duration...")
    out = duration_stats(entries, candidates)

    OUT_CSV.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}\n")
    print(out.to_string(index=False))
    print(
        "\nReading this: annualized_median lets you compare across durations "
        "without PR #40's raw-return-favors-longest-horizon bug. A smoothly "
        "rising or plateauing curve is a healthy signal; a spike at exactly "
        "one duration is not. This still doesn't simulate the compound exit "
        "rule (MA50 breach / hard stop / earnings buffer racing the time "
        "exit) -- see MEMORY.md backlog for that follow-on."
    )


if __name__ == "__main__":
    # Only rewrap stdout/stderr when actually run as a script -- doing this
    # at module level (as run_sleeve_backtest.py does) breaks anything that
    # imports the module instead of executing it (pytest collection, or
    # another script importing these helpers), since the reassignment
    # double-wraps and garbage-collects the original wrapper, closing the
    # shared underlying buffer.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    main()
