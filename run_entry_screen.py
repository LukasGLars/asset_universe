"""
Opportunistic entry screen — thin CLI wrapper around screen_tactical()
in src/asset_universe/analysis/engine.py.

Tactical layer, separate from the 3-asset scarcity base (Gold/AVGO/LLY).
Deploys war-chest / home-base capital opportunistically when a candidate
clears four gates:

  1. Regime top-N  — ticker ranks in the top N of the CURRENT macro regime's
                      (ry_regime + baa10y_regime) conditional-return ranking.
                      Sourced from universe_screen_results.csv when it
                      matches the live regime (validated with a one-ticker
                      GC_F spot-check, not just by trusting the label),
                      otherwise computed fresh for the live regime only
                      (see _rank_universe_fresh).
  2. Above MA50     — price > 50d SMA (momentum confirmed). Checked
                      directly here. screen_tactical's own extension gate
                      (#3) allows negative extension too — a ticker below
                      its MA50 can still land in the "LOW" bucket — so this
                      explicit check is the one piece of gate logic this
                      script adds rather than reuses.
  3. Not extended   — delegated entirely to screen_tactical(): MA50
                      extension below the regime's own empirical p67,
                      combined with its relative-strength-vs-benchmark gate.
  4. No earnings    — delegated entirely to screen_tactical()'s earnings
                      gate (hold_days window, default 21 = 3 weeks).

Gates 3 and 4 are NOT reimplemented. screen_tactical() already existed in
engine.py and was the basis for the HWM entry (2026-06-24) via run_screen.py.
This script adds gate 1 (regime-ranking source) and gate 2 (explicit
above-MA50 check), runs screen_tactical() for gates 3-4, and formats the
combined result as one table.

Usage:
    python run_entry_screen.py
    python run_entry_screen.py --top-n 30 --hold-days 21 --benchmark SPY
    python run_entry_screen.py --as-of 2026-06-24 --data-dir <snapshot dir>
"""
from __future__ import annotations

import argparse
import sys
from datetime import date as _date
from datetime import datetime as _datetime
from datetime import timedelta as _timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import warnings
warnings.filterwarnings("ignore")

import pandas as pd

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.analysis.engine import (
    _next_earnings,
    current_regime,
    screen_tactical,
)
from asset_universe.store import reader

ROOT = Path(__file__).parent
UNIVERSE_CSV = ROOT / "universe_screen_results.csv"
SLEEVE_STATE_PATH = ROOT / "config" / "sleeve_state.toml"
PORTFOLIO_TOML = ROOT / "config" / "portfolio.toml"

# Opportunistic sleeve rules (see MEMORY.md "Formalize the opportunistic sleeve"):
#   - 1 open position at a time
#   - exit at min(TIME_EXIT_DAYS, days-to-earnings - EARNINGS_BUFFER_DAYS), or
#     a buffered MA50 breach, or a trailing-peak stop once meaningfully in
#     profit -- whichever binds first (see binding_stop() below)
#
# Revised 2026-07-26 (see MEMORY.md "Opp sleeve stop refinement -- compound-
# exit test finds the real culprit is MA50, not the hard stop"): the prior
# fixed 2% hard stop and unbuffered MA50 stop are both retired. Validated on
# the real 4,321-entry gated population (2009-2026, run_sleeve_entry_
# reconstruction.py): every stop config with an unbuffered MA50 had a
# NEGATIVE median return at every hold duration, despite the same entries
# returning +26.5% annualized at 15d held with no exit rule at all -- these
# entries qualify by NOT being extended (close to their own MA50 by
# construction), so an unbuffered MA50 gets touched by ordinary noise well
# before any real breakdown. A 5% MA50 buffer was positive in every
# duration (15-90d) and every volatility bucket tested. TIME_EXIT_DAYS
# shortened from 30 to 21: PR #45's raw duration sweep and this same
# compound-exit study both show the edge is front-loaded (Calmar peaks
# ~21d, then decays), and 30d traced back to the informal HWM precedent
# (PR #6), never to a backtest.
#
# Revised 2026-07-27 (see MEMORY.md "Opp sleeve trailing-stop distance --
# 3% beats the live 5%, no vol-scaling needed"): TRAILING_PCT tightened
# from 5% to 3%, keeping TRAILING_TRIGGER_PCT at 5%. A 3x3 trigger x
# trailing_pct grid on the same real 4,321-entry population found (5%
# trigger, 3% trailing) at or within noise of the best result in EVERY
# volatility bucket simultaneously -- not a vol-scaled rule, a single
# global parameter fix. Pooled annualized 27.8% vs the old 5%/5% rule's
# 19.2%; mid/high-vol Calmar +60-69% relative. Because the trailing stop
# only arms after a real profit cushion (unchanged trigger), a
# noise-triggered exit locks in a smaller gain, never a loss -- a
# different, safer failure mode than the retired unbuffered-MA50 problem.
TIME_EXIT_DAYS       = 21
EARNINGS_BUFFER_DAYS = 3
MA50_BUFFER_PCT      = 0.05  # MA50 must be cleared by this margin before it binds
TRAILING_TRIGGER_PCT = 0.05  # unrealized gain since entry before the trailing stop arms
TRAILING_PCT         = 0.03  # trailing distance below the peak close, once armed

# Basket-crash: secondary entry pathway (see MEMORY.md "Sector-capitulation
# reconstruction" + "Capitulation stop-sensitivity", 2026-07-29). A gate-1
# candidate that is itself in a 5d/-10% crash (same convention as the
# AVGO/LLY guard -- not a new threshold) AND has >= MIN_PEERS_CRASHING other
# same-sector gate-1 peers ALSO crashing beat solo idiosyncratic crashes on
# raw return/win-rate at every duration tested (21d: ~4x return, +12pp win
# rate; 90d: ~2x return, +12pp win rate). Priority vs. the primary
# extension-gate pathway: extension-gate wins whenever it has an eligible
# ENTER candidate (it's live-validated, tuned on a 4,321-entry real
# population, and enters ABOVE MA50 with momentum confirmed); basket_crash
# only fills the sleeve's single slot when extension-gate has none -- it is
# newer, thinner-N (299 entries), never live-fired, and enters BELOW MA50
# mid-crash, a structurally higher-stress moment to be deploying capital.
CRASH_ROC_WINDOW    = 5
CRASH_ROC_THRESHOLD = -0.10
MIN_PEERS_CRASHING  = 2

# Basket-crash entries start BELOW their own MA50 by construction, so the
# extension-gate's MA50-floor stop cannot apply to them. Validated on the
# real reconstruction population (comparison_results/opp_sleeve_
# capitulation_stop_sensitivity.csv): ANY fixed floor (MA50-based or a flat
# entry-price percentage) destroyed the edge -- e.g. solo_crash with a 5%
# floor swings to a MEDIAN LOSS despite being +1.13% unstoppped. Trailing-
# only, at this entry type's own validated params (deliberately NOT the
# extension-gate's 5%/3% -- different population, different fit): Calmar-
# like return improved over a raw unstoppped hold for basket_crash
# (0.443 -> 0.481) at these exact values.
BASKET_TRAILING_TRIGGER_PCT = 0.08
BASKET_TRAILING_PCT         = 0.08

# Neither the earnings-avoidance gate nor the execution-drift filter (both
# used by the primary extension-gate pathway) has been validated for this
# entry type -- the reconstruction studies never tested either interaction.
# Deliberately NOT applied here rather than silently reused on an untested
# population; see the "not yet validated" note printed alongside any
# basket-crash candidate.

# Added 2026-07-29 (see MEMORY.md "Opp sleeve execution-drift analysis --
# chasing raises stop-out risk, not return"): a candidate that has already
# moved meaningfully between qualifying (the screen's signal close) and
# when you can actually execute (a live price fetched at decision time) is
# riskier to enter, in EITHER direction -- the real 3,644-entry gated
# population showed early-stop-out rate roughly 2-3x higher at both
# extremes (51.5% gapped down, 35.6% chased up) than near-zero drift
# (14.1%), with no compensating gain in expected return. Bucket edges
# closest to that "sweet spot" sat right around +/-0.9%, hence the
# threshold below. Filters out (not just flags) an ENTER candidate whose
# live/current price has drifted beyond this from its signal close --
# the next-ranked candidate is tried instead, same pattern as the
# pre-entry tripwire gate. Missing live-price data fails OPEN (doesn't
# exclude), matching the repo's existing missing-data convention.
EXECUTION_DRIFT_THRESHOLD = 0.009
DIVERSITY_RANK        = {"ROBUST": 0, "MODERATE": 1, "THIN": 2}

CATEGORY_DIR = {
    "US Equity":  "equities",
    "Commodity":  "commodities",
    "UCITS ETF":  "intl_etfs",
    "Swedish":    "intl_etfs",
}

# Matches universe_screen_results.csv's own methodology (run_universe_screen.py):
# no history-length cutoff (DFII10's 2003 start is the binding data constraint —
# excluding shorter-history names like HWM at 9.6yr would defeat the purpose of
# this fallback), MIN_N=10 matched dates as the only quality bar.
MIN_N_OBS = 10
FWD_DAYS  = 252


# ── Gate 1: regime-appropriate candidate list ───────────────────────────────

def _uncapped_forward_return(prices: pd.Series, dt: pd.Timestamp, fwd_days: int) -> float | None:
    """Forward return, NOT capped at regime end — intentionally mirrors
    run_universe_screen.py's own _forward_return (the script that produces
    universe_screen_results.csv) rather than engine.py's regime-capped
    version, so the freshness check and the fallback ranking both stay
    apples-to-apples with the cached CSV. (engine.py's capped helper was a
    later, more conservative fix applied to the conditional-return *engine*;
    the universe screen was never migrated to it — see MEMORY.md. Comparing
    against the capped engine.query() here would make a same-regime CSV look
    "stale" purely from the methodology gap, not from an actual regime
    change — confirmed empirically: GC_F med_252d is 34% uncapped vs 5%
    capped for the same HIGH+TIGHT regime.)"""
    idx = prices.index.searchsorted(dt)
    if idx >= len(prices) or abs((prices.index[idx] - dt).days) > 5:
        return None
    fwd_idx = idx + fwd_days
    if fwd_idx >= len(prices):
        return None
    p0, p1 = prices.iloc[idx], prices.iloc[fwd_idx]
    return (p1 - p0) / p0 if p0 > 0 else None


def _matched_dates(conditions: dict, data_dir: Path) -> pd.DatetimeIndex:
    labeled_df, _ = regime_module.build(data_dir)
    mask = pd.Series(True, index=labeled_df.index)
    for k, v in conditions.items():
        mask &= labeled_df[k] == v
    return labeled_df.index[mask]


def _csv_matches_live_regime(df_full: pd.DataFrame, matched: pd.DatetimeIndex, data_dir: Path) -> bool:
    """Spot-check: does universe_screen_results.csv reflect the regime that's
    live right now? Recomputes GC_F's median 252d return with the SAME
    (uncapped) methodology the CSV was built with, rather than trusting a
    stale file blindly or comparing against a differently-capped method."""
    if "GC_F" not in df_full["ticker"].values:
        return False
    csv_row = df_full.loc[df_full["ticker"] == "GC_F"].iloc[0]
    if pd.isna(csv_row.get("med_252d")):
        return False
    path = reader.ticker_path(data_dir, "commodities", "GC_F")
    if not path.exists():
        return False
    prices = reader.load(path)["close"].dropna().sort_index()
    rets = [r for dt in matched if (r := _uncapped_forward_return(prices, dt, FWD_DAYS)) is not None]
    if len(rets) < MIN_N_OBS:
        return False
    same_n   = abs(len(rets) - csv_row["n_matched"]) <= 5
    same_med = abs(float(pd.Series(rets).median()) - csv_row["med_252d"]) < 0.01
    return same_n and same_med


def _rank_universe_fresh(matched: pd.DatetimeIndex, data_dir: Path, top_n: int) -> tuple[list[str], dict[str, str]]:
    """Fallback gate-1 ranking — same conditional-median-252d-return ranking
    used by run_universe_screen.py, computed only for the live regime (not
    the full universe screen's broader yfinance-fetched Swedish/UCITS set).
    Only runs when no valid cached ranking exists on disk for the current
    regime. No history-length cutoff, by design (see MIN_N_OBS comment above)."""
    rows = []
    cat_of: dict[str, str] = {}
    for cat_dir in ("equities", "commodities", "intl_etfs"):
        d = data_dir / cat_dir
        if not d.exists():
            continue
        for f in sorted(d.glob("*.parquet")):
            prices = reader.load(f)["close"].dropna().sort_index()
            if len(prices) < 50:
                continue
            rets = [
                r for dt in matched
                if (r := _uncapped_forward_return(prices, dt, FWD_DAYS)) is not None
            ]
            if len(rets) < MIN_N_OBS:
                continue
            rows.append({"ticker": f.stem, "median": float(pd.Series(rets).median())})
            cat_of[f.stem] = cat_dir

    rows.sort(key=lambda r: -r["median"])
    top = rows[:top_n]
    return [r["ticker"] for r in top], cat_of


def get_regime_candidates(
    conditions: dict, top_n: int, data_dir: Path,
) -> tuple[list[str], dict[str, str], str, dict[str, dict]]:
    """Returns (tickers, ticker->category_dir map, source description,
    ticker->{med_21d, win_21d, diversity} for the selection rule -- empty
    dict per ticker when using the fresh fallback, which doesn't compute
    21d returns; selection then degrades to extension-only ranking)."""
    matched = _matched_dates(conditions, data_dir)
    if UNIVERSE_CSV.exists():
        df_full = pd.read_csv(UNIVERSE_CSV)
        if _csv_matches_live_regime(df_full, matched, data_dir):
            ranked = df_full.sort_values("rank").head(top_n)
            cat_of = {row.ticker: CATEGORY_DIR.get(row.category, "equities") for row in ranked.itertuples()}
            extra = {
                row.ticker: {
                    "med_21d": row.med_21d, "win_21d": row.win_21d,
                    "diversity": row.diversity, "med_252d": row.med_252d,
                }
                for row in ranked.itertuples()
            }
            return (ranked["ticker"].tolist(), cat_of,
                    f"{UNIVERSE_CSV.name} (validated against live regime)", extra)
    tickers, cat_of = _rank_universe_fresh(matched, data_dir, top_n)
    return tickers, cat_of, "computed fresh (no valid cached ranking found for live regime)", {}


# ── Gate 2: explicit above-MA50 check + display stats ───────────────────────

def _ma50_stats(data_dir: Path, cat_dir: str, ticker: str) -> dict | None:
    path = reader.ticker_path(data_dir, cat_dir, ticker)
    if not path.exists():
        return None
    prices = reader.load(path)["close"].dropna().sort_index()
    if len(prices) < 50:
        return None
    ma50 = prices.rolling(50, min_periods=25).mean()
    price, ma = float(prices.iloc[-1]), float(ma50.iloc[-1])
    if pd.isna(ma):
        return None
    return {
        "price":     price,
        "ma50":      ma,
        "dist_pct":  price / ma - 1,
        "above_ma50": price > ma,
        "as_of":     str(prices.index[-1].date()),
    }


def _peak_since_entry(data_dir: Path, cat_dir: str, ticker: str, entry_date: str, entry_price: float) -> float:
    """Highest close from entry_date to the latest available price, floored
    at entry_price (a position that has never traded above its own entry
    has no unrealized gain, so its peak is the entry itself). Feeds the
    trailing-peak stop in binding_stop()."""
    path = reader.ticker_path(data_dir, cat_dir, ticker)
    if not path.exists():
        return entry_price
    prices = reader.load(path)["close"].dropna().sort_index()
    since_entry = prices[prices.index >= pd.Timestamp(entry_date)]
    if since_entry.empty:
        return entry_price
    return max(entry_price, float(since_entry.max()))


# ── Sleeve state (persisted — the one thing price data alone can't give us:
#    what price/date a position was actually entered at) ────────────────────

def load_sleeve_state(path: Path | None = None) -> dict:
    path = path or SLEEVE_STATE_PATH
    if not path.exists():
        return {"open": False}
    with open(path, "rb") as f:
        return tomllib.load(f)


def _write_sleeve_state(state: dict, path: Path | None = None) -> None:
    path = path or SLEEVE_STATE_PATH
    lines = [
        "# Opportunistic sleeve state — manually maintained, NOT synced from the",
        "# Google Sheet (unlike portfolio.toml's share counts).",
        "#",
        "# Updated via:",
        "#   python run_entry_screen.py --open TICKER ENTRY_PRICE SHARES CAPITAL_SEK",
        "#     [--entry-type extension|basket_crash]  (default: extension)",
        "#   python run_entry_screen.py --close",
        "#",
        "# Position cap: 1 open position at a time. war-chest capital only.",
        '# See MEMORY.md "Formalize the opportunistic sleeve" for the full rule set,',
        '# and "Sector-capitulation reconstruction" / "Capitulation stop-sensitivity"',
        "# for the basket_crash entry_type (different stop, different time exit --",
        "# see compute_exit_triggers()).",
        "",
        f"open       = {str(bool(state.get('open', False))).lower()}",
        f'ticker     = "{state.get("ticker", "")}"',
        f'category   = "{state.get("category", "")}"',
        f'entry_type = "{state.get("entry_type", "extension")}"',
        f'entry_date = "{state.get("entry_date", "")}"',
        f"entry_price = {float(state.get('entry_price', 0.0))}",
        f"shares      = {int(state.get('shares', 0))}",
        f"capital_sek = {float(state.get('capital_sek', 0.0))}",
        f"fx_at_entry = {float(state.get('fx_at_entry', 0.0))}",
        "",
        f'entry_ry_regime     = "{state.get("entry_ry_regime", "")}"',
        f'entry_baa10y_regime = "{state.get("entry_baa10y_regime", "")}"',
        "",
        f"cluster_peers = {list(state.get('cluster_peers', []))}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def already_held_tickers(portfolio_path: Path | None = None) -> set[str]:
    """Tickers with shares > 0 in portfolio.toml — used to flag ENTER
    candidates that are already held (a PASS/ENTER there means "no red flag
    today", NOT "add capital" — those are different claims)."""
    path = portfolio_path or PORTFOLIO_TOML
    if not path.exists():
        return set()
    with open(path, "rb") as f:
        cfg = tomllib.load(f)
    return {
        p["ticker"] for p in cfg.get("positions", [])
        if p.get("ticker") and p.get("shares", 0) > 0
    }


# ── Exit triggers ────────────────────────────────────────────────────────

def binding_stop(entry_price: float, ma50: float, peak_price: float) -> tuple[float, str]:
    """The binding stop is whichever level is HIGHER (hit first as price
    falls): a buffered MA50 floor, or -- once the position has moved
    TRAILING_TRIGGER_PCT into profit -- a trailing stop below the peak
    close since entry. There is no fixed hard stop (dropped 2026-07-26): a
    flat 2% cap was tighter than MA50's own typical distance from entry and
    produced false triggers on ordinary volatility (the HWM 2026-07-10
    false stop) for zero realized protection across its one real use.
    peak_price must be >= entry_price (see _peak_since_entry) so the
    trailing branch only ever activates in genuine profit."""
    levels = [(ma50 * (1 - MA50_BUFFER_PCT), "MA50")]
    if peak_price / entry_price - 1 >= TRAILING_TRIGGER_PCT:
        levels.append((peak_price * (1 - TRAILING_PCT), "TRAILING"))
    return max(levels, key=lambda lv: lv[0])


def basket_crash_binding_stop(entry_price: float, peak_price: float) -> tuple[float | None, str]:
    """Trailing-only stop for basket-crash entries -- deliberately NO MA50
    floor branch (see BASKET_TRAILING_* above: any fixed floor destroyed
    the edge on this below-MA50-by-construction population). Returns
    (None, ...) until the trade is far enough in profit to arm -- there is
    no floor to fall back on before then, unlike binding_stop()."""
    if peak_price / entry_price - 1 >= BASKET_TRAILING_TRIGGER_PCT:
        return peak_price * (1 - BASKET_TRAILING_PCT), "TRAILING"
    return None, "n/a (not yet armed -- no floor for this entry type)"


def compute_exit_triggers(
    entry_price: float,
    entry_date: str,
    ticker: str,
    category: str,
    data_dir: Path,
    entry_type: str = "extension",
) -> dict:
    entry_dt = _datetime.strptime(entry_date, "%Y-%m-%d").date()
    ma = _ma50_stats(data_dir, category, ticker)
    ma50 = ma["ma50"] if ma else None
    peak_price = _peak_since_entry(data_dir, category, ticker, entry_date, entry_price) if ma else None
    earn_date = _next_earnings(ticker)

    if entry_type == "basket_crash":
        # Flat 21-calendar-day exit, NO earnings-buffer adjustment -- matches
        # exactly what run_opp_sleeve_capitulation_stop_sensitivity.py
        # validated (DURATION_DAYS=21, earnings interaction never tested for
        # this entry type). next_earnings is still shown below for context.
        time_exit = entry_dt + _timedelta(days=21)
        time_exit_binding = "flat 21d (basket-crash -- no earnings-buffer validated for this entry type)"
    else:
        earn_time_exit = (earn_date - _timedelta(days=EARNINGS_BUFFER_DAYS)) if earn_date else None
        flat_time_exit = entry_dt + _timedelta(days=TIME_EXIT_DAYS)
        time_exit = min(flat_time_exit, earn_time_exit) if earn_time_exit else flat_time_exit
        time_exit_binding = (f"earnings-{EARNINGS_BUFFER_DAYS}d" if (earn_time_exit and earn_time_exit < flat_time_exit)
                              else f"flat {TIME_EXIT_DAYS}d")
    time_exit_days = (time_exit - entry_dt).days

    if entry_type == "basket_crash":
        stop_price, stop_label = (basket_crash_binding_stop(entry_price, peak_price) if peak_price is not None else (None, "n/a"))
        trailing_armed = bool(peak_price is not None and peak_price / entry_price - 1 >= BASKET_TRAILING_TRIGGER_PCT)
        trailing_stop = round(peak_price * (1 - BASKET_TRAILING_PCT), 2) if trailing_armed else None
        ma50_buffered = None  # no MA50 floor for this entry type -- see basket_crash_binding_stop
    else:
        stop_price, stop_label = (binding_stop(entry_price, ma50, peak_price) if ma50 else (None, "n/a"))
        trailing_armed = bool(ma50 and peak_price is not None and peak_price / entry_price - 1 >= TRAILING_TRIGGER_PCT)
        trailing_stop = round(peak_price * (1 - TRAILING_PCT), 2) if trailing_armed else None
        ma50_buffered = round(ma50 * (1 - MA50_BUFFER_PCT), 2) if ma50 else None

    return {
        "ma50":              ma50,
        "ma50_buffered":     ma50_buffered,
        "peak_price":        round(peak_price, 2) if peak_price is not None else None,
        "trailing_stop":     trailing_stop,
        "binding_stop":      round(stop_price, 2) if stop_price else None,
        "binding_label":     stop_label,
        "time_exit_date":    time_exit,
        "time_exit_days":    time_exit_days,
        # Days remaining FROM TODAY, distinct from time_exit_days above (the
        # fixed entry-to-exit duration, e.g. always 21 -- that field never
        # changes day to day, so a "Xd left" display built from it would
        # silently show the same number every day regardless of how close
        # the real deadline actually is). This is the one that should be
        # used anywhere "days left" is the claim.
        "time_exit_days_remaining": (time_exit - _date.today()).days,
        "time_exit_binding": time_exit_binding,
        "next_earnings":     earn_date,
        "current_price":     ma["price"] if ma else None,
    }


# ── Post-entry tripwires (price-vs-fixed-level alone can't tell a good dip
#    from an early warning -- these five can) ────────────────────────────

def _period_return(prices: pd.Series, n_days: int) -> float | None:
    if len(prices) < n_days + 1:
        return None
    return float(prices.iloc[-1] / prices.iloc[-(n_days + 1)] - 1)


def asset_name(ticker: str) -> str:
    """Full company/asset name via yfinance, for display next to a ticker
    at the points where a human is actually deciding something (the
    recommendation, an open position) -- not fetched for every row of the
    30-candidate table, to avoid ~30 extra API calls on a run where only
    one or two names actually matter for the decision."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        return info.get("longName") or info.get("shortName") or ""
    except Exception:
        return ""


def discover_cluster_peers(
    ticker: str, gate1_candidates: list[str], exclude: set[str],
    data_dir: Path, max_peers: int = 4,
) -> list[str]:
    """Same-sector peers from the current gate-1 candidate list, via
    yfinance's sector field. Computed ONCE at entry (see sleeve_state.toml)
    -- not recomputed daily, since peers should be fixed for the trade's
    life and re-querying yfinance sector data every run would be a needless
    API cost for something that shouldn't change."""
    import yfinance as yf
    try:
        sector = yf.Ticker(ticker).info.get("sector")
    except Exception:
        sector = None
    if not sector:
        return []
    peers = []
    for t in gate1_candidates:
        if t == ticker or t in exclude:
            continue
        try:
            s = yf.Ticker(t).info.get("sector")
        except Exception:
            s = None
        if s == sector:
            peers.append(t)
        if len(peers) >= max_peers:
            break
    return peers


# ── Basket-crash: live detection + concentration cap (secondary pathway,
#    see MIN_PEERS_CRASHING / BASKET_TRAILING_* above) ─────────────────────

_sector_cache: dict[str, str | None] = {}


def _sector_of(ticker: str) -> str | None:
    """Cached sector lookup -- separate cache from discover_cluster_peers
    (which is called once per trade entry, not worth sharing a cache for),
    since this runs across the full gate-1 candidate list every screen run."""
    if ticker in _sector_cache:
        return _sector_cache[ticker]
    try:
        import yfinance as yf
        sector = yf.Ticker(ticker).info.get("sector")
    except Exception:
        sector = None
    _sector_cache[ticker] = sector
    return sector


def basket_crash_candidates(
    gate1_candidates: list[str], cat_of: dict[str, str], data_dir: Path,
    min_peers: int = MIN_PEERS_CRASHING,
) -> list[dict]:
    """Live version of run_sleeve_sector_capitulation_reconstruction.py's
    historical trigger: which of TODAY's gate-1 candidates are themselves in
    a 5d/-10% crash AND have >= min_peers other same-sector gate-1 peers
    ALSO crashing today. Returns one dict per qualifying ticker (ticker,
    sector, roc_5d, peer_count, category, price -- the last close, so a
    candidate can be acted on directly from a message without a live
    lookup) -- uncapped; see cap_basket_crash_concentration for the
    1-per-sector selection cap."""
    rocs: dict[str, float] = {}
    last_price: dict[str, float] = {}
    for t in gate1_candidates:
        path = reader.ticker_path(data_dir, cat_of.get(t, "equities"), t)
        if not path.exists():
            continue
        prices = reader.load(path)["close"].dropna().sort_index()
        if len(prices) <= CRASH_ROC_WINDOW:
            continue
        rocs[t] = float(prices.iloc[-1] / prices.iloc[-1 - CRASH_ROC_WINDOW] - 1)
        last_price[t] = float(prices.iloc[-1])

    crashing = {t: roc for t, roc in rocs.items() if roc <= CRASH_ROC_THRESHOLD}
    if not crashing:
        return []

    sector_of = {t: _sector_of(t) for t in crashing}
    rows = []
    for t, roc in crashing.items():
        sector = sector_of.get(t)
        if sector is None:
            continue
        peer_count = sum(1 for other, s in sector_of.items() if other != t and s == sector)
        if peer_count >= min_peers:
            rows.append({
                "ticker": t, "sector": sector, "roc_5d": roc, "price": last_price[t],
                "peer_count": peer_count, "category": cat_of.get(t, "equities"),
            })
    return rows


def cap_basket_crash_concentration(rows: list[dict]) -> list[dict]:
    """1-per-sector cap on today's basket-crash candidates, applied before
    selection. This is a SELECTION-bias guard, not a capital-exposure cap --
    the sleeve only ever holds one position total (see position cap in
    open_position), so there is no multi-position concentration risk to
    bound yet. Without this, a day where multiple sectors crash together
    could silently steer the pick toward whichever sector happens to have
    the most crashing gate-1 names. Within a sector, keeps the deepest
    crash (most negative roc_5d), tie-broken by peer_count -- the same
    "stronger capitulation signal wins" rationale the reconstruction's
    basket_crash bucket validated against solo_crash."""
    best_by_sector: dict[str, dict] = {}
    for row in rows:
        sector = row["sector"]
        current = best_by_sector.get(sector)
        if current is None or (row["roc_5d"], -row["peer_count"]) < (current["roc_5d"], -current["peer_count"]):
            best_by_sector[sector] = row
    return list(best_by_sector.values())


def select_best_basket_crash(rows: list[dict], held: set[str]) -> dict | None:
    """Pick among post-cap basket-crash candidates -- deepest crash first
    (same criterion the concentration cap uses per-sector), excluding
    already-held tickers. Deliberately does NOT reuse select_best_candidate's
    pre-entry tripwire gate: that gate requires RS >= 0 and a rising MA50,
    both the OPPOSITE of what qualifies a basket-crash candidate in the
    first place."""
    pool = [r for r in rows if r["ticker"] not in held]
    if not pool:
        return None
    return min(pool, key=lambda r: (r["roc_5d"], -r["peer_count"]))


# ── Execution-drift filter (pre-entry, see EXECUTION_DRIFT_THRESHOLD) ──────

def _live_price(ticker: str) -> float | None:
    """Best-effort current quote -- premarket, else regular, else postmarket.
    Returns None on any failure (missing data fails OPEN in the caller,
    same convention as the rest of this module's live-data lookups)."""
    import yfinance as yf
    try:
        info = yf.Ticker(ticker).info
        return info.get("preMarketPrice") or info.get("regularMarketPrice") \
            or info.get("currentPrice") or info.get("postMarketPrice")
    except Exception:
        return None


def _execution_drift_ok(ticker: str, signal_close: float) -> tuple[bool, float | None]:
    """True if a live price fetched right now hasn't drifted beyond
    EXECUTION_DRIFT_THRESHOLD from the close that generated the ENTER
    signal, in EITHER direction. Missing live-price data or a
    non-positive signal_close fails OPEN (doesn't exclude the
    candidate) -- there's nothing to compare against, not evidence of a
    problem. Returns (ok, drift) so callers can display the actual
    drift value even when it's within tolerance."""
    if signal_close is None or signal_close <= 0:
        return True, None
    price = _live_price(ticker)
    if price is None:
        return True, None
    drift = price / signal_close - 1
    return abs(drift) <= EXECUTION_DRIFT_THRESHOLD, drift


# ── VIX review at entry (informational -- for you to weigh, not an
#    automated gate). The post-entry tripwire compares VIX to its own 20d
#    average, which is a LOCAL baseline -- if VIX has been elevated for a
#    month, that comparison would still read "calm relative to recent."
#    This instead ranks today's level against its full ~26yr history, so
#    "elevated" means something absolute, not just relative-to-last-month.
#    No tested evidence a VIX threshold improves outcomes in this
#    framework, so this stays a review line, not a block. ────────────────

def _vix_stats(vix: pd.Series) -> dict:
    now = float(vix.iloc[-1])
    percentile = float((vix < now).mean())
    chg_5d = float(vix.iloc[-1] - vix.iloc[-6]) if len(vix) > 6 else None
    trend = "spiking" if (chg_5d is not None and chg_5d > 1.0) else \
            ("falling" if (chg_5d is not None and chg_5d < -1.0) else "flat")
    return {
        "now": now, "percentile": percentile, "chg_5d": chg_5d, "trend": trend,
        "years": round((vix.index[-1] - vix.index[0]).days / 365.25, 1),
    }


def vix_review(data_dir: Path) -> dict:
    vix = reader.load(reader.ticker_path(data_dir, "volatility", "VIX"))["close"].dropna().sort_index()
    return _vix_stats(vix)


def compute_tripwires(state: dict, data_dir: Path, benchmark: str = "SPY") -> dict:
    ticker, category = state["ticker"], state["category"]

    t_prices = reader.load(reader.ticker_path(data_dir, category, ticker))["close"].dropna().sort_index()
    b_prices = reader.load(reader.ticker_path(data_dir, "equities", benchmark))["close"].dropna().sort_index()
    t_20d, b_20d = _period_return(t_prices, 20), _period_return(b_prices, 20)
    rs_20d = (t_20d - b_20d) if (t_20d is not None and b_20d is not None) else None

    regime = current_regime(data_dir)
    regime_changed = (
        regime["regimes"]["ry_regime"] != state.get("entry_ry_regime")
        or regime["regimes"]["baa10y_regime"] != state.get("entry_baa10y_regime")
    )

    peers = state.get("cluster_peers") or []
    peer_rets = {}
    for p in peers:
        path = reader.ticker_path(data_dir, "equities", p)
        if path.exists():
            s = reader.load(path)["close"].dropna().sort_index()
            r5 = _period_return(s, 5)
            if r5 is not None:
                peer_rets[p] = r5
    cluster_avg = (sum(peer_rets.values()) / len(peer_rets)) if peer_rets else None
    cluster_breakdown = sum(1 for r in peer_rets.values() if r < -0.03) >= max(1, len(peer_rets) // 2 + 1) if peer_rets else False

    vix = reader.load(reader.ticker_path(data_dir, "volatility", "VIX"))["close"].dropna().sort_index()
    vix_now = float(vix.iloc[-1])
    vix_20d_avg = float(vix.iloc[-20:].mean())
    vix_5d_chg = float(vix.iloc[-1] - vix.iloc[-6]) if len(vix) > 6 else None
    vix_calm = vix_now <= vix_20d_avg

    ma50 = t_prices.rolling(50).mean()
    ma50_slope = float(ma50.iloc[-1] - ma50.iloc[-21]) if len(ma50) > 21 and not pd.isna(ma50.iloc[-21]) else None

    return {
        "rs_20d": rs_20d, "rs_ok": (rs_20d is not None and rs_20d >= 0),
        "regime_now": regime["regimes"], "regime_changed": regime_changed,
        "peer_rets": peer_rets, "cluster_avg": cluster_avg, "cluster_breakdown": cluster_breakdown,
        "vix_now": vix_now, "vix_20d_avg": vix_20d_avg, "vix_5d_chg": vix_5d_chg, "vix_calm": vix_calm,
        "ma50_now": float(ma50.iloc[-1]), "ma50_slope": ma50_slope,
        "ma50_rising": (ma50_slope is not None and ma50_slope > 0),
    }


# ── Suggested duration + exact duration-matched return ──────────────────────
# A candidate's actual runway isn't a flat 21d/30d -- it's capped by its own
# earnings date. Rather than reading off the fixed med_21d/win_21d CSV
# columns (a mismatch for anyone whose runway isn't close to 21 trading
# days), reuse _uncapped_forward_return/_matched_dates -- already built for
# the 21d/63d/252d columns -- parametrized to each candidate's own suggested
# duration. No new algorithm, no network calls, cheap: pure price-history
# math on data already loaded for the MA50 check.

def suggested_duration_days(earn_date, today: _date | None = None) -> int:
    today = today or _date.today()
    if earn_date:
        earn_based = (earn_date - today).days - EARNINGS_BUFFER_DAYS
        return max(1, min(TIME_EXIT_DAYS, earn_based))
    return TIME_EXIT_DAYS


def duration_matched_return(
    ticker: str, category: str, matched: pd.DatetimeIndex,
    calendar_days: int, data_dir: Path,
) -> tuple[float | None, float | None, int]:
    """Median return + win rate at calendar_days out, computed fresh from
    the regime-matched historical dates. Returns (median, win_rate, n)."""
    path = reader.ticker_path(data_dir, category, ticker)
    if not path.exists():
        return None, None, 0
    prices = reader.load(path)["close"].dropna().sort_index()
    trading_days = max(1, round(calendar_days * 252 / 365.25))
    rets = [r for dt in matched if (r := _uncapped_forward_return(prices, dt, trading_days)) is not None]
    if len(rets) < MIN_N_OBS:
        return None, None, len(rets)
    s = pd.Series(rets)
    return float(s.median()), float((s > 0).mean()), len(rets)


# ── Pre-entry tripwire gate: the recommendation must earn it, not just the
#    static gates. Of the 5 post-entry tripwires, 3 are meaningful checked
#    "as if entering right now": RS-vs-benchmark, cluster health, MA50
#    slope. Regime-changed is skipped (trivially unchanged pre-entry --
#    there's no elapsed time yet for it to have flipped). VIX regime is
#    contextual framing for interpreting a move, not itself a pass/fail on
#    the candidate, so it's not a gate either. A candidate that fails any
#    of the 3 is disqualified and the next-ranked one is checked instead. ──

def _pretrade_tripwire_check(
    ticker: str, category: str, gate1_candidates: list[str], held: set[str],
    regime_labels: dict, data_dir: Path, benchmark: str = "SPY",
) -> tuple[bool, dict]:
    peers = discover_cluster_peers(ticker, gate1_candidates, exclude=held, data_dir=data_dir)
    synthetic_state = {
        "ticker": ticker, "category": category,
        "entry_ry_regime": regime_labels["ry_regime"],
        "entry_baa10y_regime": regime_labels["baa10y_regime"],
        "cluster_peers": peers,
    }
    tw = compute_tripwires(synthetic_state, data_dir, benchmark)
    passed = tw["rs_ok"] and (not tw["cluster_breakdown"]) and tw["ma50_rising"]
    return passed, tw


# ── Selection rule (no open position): least MA50-extension -> ROBUST
#    diversity preferred -> win rate at the candidate's own suggested-
#    duration horizon (falls back to win_21d if that horizon has too few
#    matched observations). med_252d is kept only as a diversity/robustness
#    cross-check, not the headline return number. Walks the ranked list and
#    returns the first candidate that ALSO clears the pre-entry tripwire
#    gate above -- a static top-rank alone is not enough to be "the"
#    recommendation. ─────────────────────────────────────────────────────

def select_best_candidate(
    out: pd.DataFrame, held: set[str],
    data_dir: Path | None = None,
    gate1_candidates: list[str] | None = None,
    regime_labels: dict | None = None,
    benchmark: str = "SPY",
) -> dict | None:
    pool = out[(out["verdict"] == "ENTER") & (~out["ticker"].isin(held)) & out["dist_num"].notna()]
    if pool.empty:
        return None
    pool = pool.copy()
    pool["diversity_rank"] = pool["diversity"].map(DIVERSITY_RANK).fillna(3)
    dur_win = (pd.to_numeric(pool["duration_win"], errors="coerce") if "duration_win" in pool.columns
               else pd.Series(float("nan"), index=pool.index))
    pool["rank_win"] = dur_win.combine_first(pd.to_numeric(pool["win_21d"], errors="coerce"))
    pool = pool.sort_values(
        by=["dist_num", "diversity_rank", "rank_win"],
        ascending=[True, True, False],
    )

    if data_dir is None or gate1_candidates is None or regime_labels is None:
        # Pre-entry tripwire vetting needs live data (yfinance sector lookup,
        # price history) -- unavailable in unit tests with synthetic data.
        # Falls back to the static ranking alone rather than crashing.
        result = pool.iloc[0].to_dict()
        result["pretrade_tripwires"] = None
        result["execution_drift"] = None
        return result

    for _, row in pool.iterrows():
        passed, tw = _pretrade_tripwire_check(
            row["ticker"], row["category"], gate1_candidates, held, regime_labels, data_dir, benchmark
        )
        if not passed:
            continue  # disqualified despite ranking well statically -- try the next one
        drift_ok, drift = _execution_drift_ok(row["ticker"], row.get("price"))
        if not drift_ok:
            continue  # already moved too far since qualifying -- try the next one
        result = row.to_dict()
        result["pretrade_tripwires"] = tw
        result["execution_drift"] = drift
        return result

    return None  # every ranked ENTER candidate failed the pre-entry tripwire or execution-drift gate


# ── Sleeve status display (position already open) ──────────────────────────

def _risk_to_stop_str(trig: dict, shares: int, fx_at_entry: float, capital_sek: float) -> str | None:
    """kr and % of sleeve capital at risk between current price and the
    binding stop -- shared by the manual report, the daily status.md
    summary, and (via check_signal_changes.py) the Telegram alert, so the
    number can't drift between the three."""
    if trig["current_price"] is None or trig["binding_stop"] is None:
        return None
    risk_sh = trig["current_price"] - trig["binding_stop"]
    risk_kr = risk_sh * shares * fx_at_entry
    return f"{risk_kr:,.0f} kr, {risk_kr / capital_sek:.2%} of sleeve capital"


def _tripwire_detail_line(tw: dict) -> str:
    """One-line, always-present breakdown of all 4 post-entry tripwires --
    not just whichever one happens to have fired -- so a risk-state change
    (and the Telegram alert built from it, see check_signal_changes.py)
    carries the full picture instead of a bare CLEAN/FLAGGED label. Cluster
    health is explicitly flagged as a coarse sector-only match (see
    discover_cluster_peers, which matches on yfinance's ~11-bucket `sector`
    field, not the finer `industry` field) -- confirmed 2026-07-09 to group
    HWM (Aerospace & Defense) with GEV/VRT/PWR/CMI (Electrical Equipment /
    Engineering & Construction / Machinery), which share a GICS sector but
    not an actual demand driver. Read it as informational, not equal-
    confidence with the other three checks."""
    rs_part = (f"RS {tw['rs_20d']:+.1%} [{'OK' if tw['rs_ok'] else 'WATCH'}]"
               if tw["rs_20d"] is not None else "RS n/a")
    regime_part = (f"Regime {'FLIPPED' if tw['regime_changed'] else 'stable'} "
                   f"[{'WATCH' if tw['regime_changed'] else 'OK'}]")
    ma50_part = (f"MA50 ${tw['ma50_now']:.2f} (slope {tw['ma50_slope']:+.2f}) "
                 f"[{'OK' if tw['ma50_rising'] else 'WATCH'}]"
                 if tw["ma50_slope"] is not None else "MA50 n/a")
    if tw["peer_rets"]:
        cluster_flag = ("WATCH, sector-only match -- low-confidence"
                         if tw["cluster_breakdown"] else "OK")
        cluster_part = f"Cluster avg {tw['cluster_avg']:+.1%} [{cluster_flag}]"
    else:
        cluster_part = "Cluster n/a (no peers on record)"
    return f"{rs_part} | {regime_part} | {ma50_part} | {cluster_part}"


def print_sleeve_status(state: dict, data_dir: Path, benchmark: str = "SPY") -> None:
    ticker, category = state["ticker"], state["category"]
    entry_type = state.get("entry_type", "extension")
    trig = compute_exit_triggers(state["entry_price"], state["entry_date"], ticker, category, data_dir, entry_type=entry_type)
    tw = compute_tripwires(state, data_dir, benchmark)

    held = "Yes" if ticker in already_held_tickers() else "No"
    print("=" * 100)
    print("OPPORTUNISTIC SLEEVE")
    print("=" * 100)
    name = asset_name(ticker)
    print(f"  Status          : OPEN (1/1 position -- new entries blocked)")
    print(f"  Ticker          : {ticker}" + (f"  ({name})" if name else ""))
    print(f"  Entry pathway   : {entry_type}" + (
        "  (below-MA50 crash entry -- trailing-only stop, no floor; flat 21d exit)"
        if entry_type == "basket_crash" else "  (MA50 + trailing stop; earnings-aware time exit)"))
    print(f"  Already held?   : {held} ({state['shares']} shares from this entry)")
    print(f"  Entered         : {state['entry_date']}")
    print(f"  Entry price     : ${state['entry_price']:.2f}  "
          f"({state['shares']} shares, {state['capital_sek']:,.0f} kr allocated)")
    print(f"  FX at entry     : {state['fx_at_entry']}")
    print()
    print(f"  Exit triggers")
    print(f"    Time exit       : {trig['time_exit_date']}  "
          f"({trig['time_exit_days']}d; bound by {trig['time_exit_binding']})")
    print(f"    MA50 (buffered) : ${trig['ma50_buffered']:.2f}  (raw MA50 ${trig['ma50']:.2f})"
          if trig["ma50_buffered"] else "    MA50 (buffered) : n/a (no MA50 floor for this entry type)"
          if entry_type == "basket_crash" else "    MA50 (buffered) : n/a")
    if trig["trailing_stop"] is not None:
        print(f"    Trailing stop   : ${trig['trailing_stop']:.2f}  (peak ${trig['peak_price']:.2f} since entry)")
    print(f"    Binding stop    : ${trig['binding_stop']:.2f}  ({trig['binding_label']})"
          if trig["binding_stop"] else f"    Binding stop    : {trig['binding_label']}")
    print(f"    Next earnings   : {trig['next_earnings'] if trig['next_earnings'] else 'n/a'}")
    risk_str = _risk_to_stop_str(trig, state["shares"], state["fx_at_entry"], state["capital_sek"])
    if risk_str:
        print(f"    Current price   : ${trig['current_price']:.2f}  (risk to binding stop: {risk_str})")
    print()
    print(f"  Post-entry tripwires" + (
        "  (RS/MA50-slope WATCH is EXPECTED for a crash entry -- these check for"
        " above-MA50/positive-RS behavior this entry type doesn't have by construction)"
        if entry_type == "basket_crash" else ""))
    rs_flag = "OK" if tw["rs_ok"] else "WATCH"
    if tw["rs_20d"] is not None:
        print(f"    RS vs {benchmark} (20d)   : {tw['rs_20d']:+.1%}  [{rs_flag}]")
    else:
        print(f"    RS vs {benchmark} (20d)   : n/a")
    regime_flag = "WATCH -- FLIPPED" if tw["regime_changed"] else "OK"
    print(f"    Regime (RY/BAA10Y)   : {tw['regime_now']['ry_regime']}/{tw['regime_now']['baa10y_regime']} "
          f"(entry: {state['entry_ry_regime']}/{state['entry_baa10y_regime']})  [{regime_flag}]")
    if tw["peer_rets"]:
        peer_str = " ".join(f"{k} {v:+.1%}" for k, v in tw["peer_rets"].items())
        cluster_flag = ("WATCH -- BREAKDOWN (sector-only match, low-confidence)"
                         if tw["cluster_breakdown"] else "OK")
        print(f"    Cluster health (5d)  : {peer_str}")
        print(f"                           avg {tw['cluster_avg']:+.1%}  [{cluster_flag}]")
    else:
        print(f"    Cluster health (5d)  : no peers on record  [n/a]")
    vix_flag = "calm/falling" if tw["vix_calm"] else "elevated/rising"
    print(f"    Vol regime (VIX)     : {tw['vix_now']:.2f} (20d avg {tw['vix_20d_avg']:.2f}, "
          f"{vix_flag}) -- {'idiosyncratic' if tw['vix_calm'] else 'check if systematic'} moves stand out  [OK]")
    slope_flag = "OK" if tw["ma50_rising"] else "WATCH -- FLATTENING/FALLING"
    print(f"    MA50 slope (20d)     : {tw['ma50_slope']:+.2f}  "
          f"({'rising' if tw['ma50_rising'] else 'not rising'})  [{slope_flag}]")
    print()
    any_watch = (not tw["rs_ok"]) or tw["regime_changed"] or tw["cluster_breakdown"] or not tw["ma50_rising"]
    print(f"  {'One or more tripwires flagged -- review the position.' if any_watch else 'All tripwires clean -- no early-warning flags.'}")
    print("=" * 100)


# ── Main screen ───────────────────────────────────────────────────────────

def run_entry_screen(
    top_n: int = 30,
    hold_days: int = 21,
    benchmark: str = "SPY",
    data_dir: Path | None = None,
    as_of: str | None = None,
) -> pd.DataFrame:
    if data_dir is None:
        data_dir = config.raw_data_dir()

    state = load_sleeve_state()
    if state.get("open"):
        print_sleeve_status(state, data_dir, benchmark)
        return pd.DataFrame()

    regime = current_regime(data_dir)
    conditions = {
        "ry_regime":     regime["regimes"]["ry_regime"],
        "baa10y_regime": regime["regimes"]["baa10y_regime"],
    }

    candidates, cat_of, source, extra_info = get_regime_candidates(conditions, top_n, data_dir)
    held = already_held_tickers()
    matched = _matched_dates(conditions, data_dir)

    print("=" * 100)
    print("OPPORTUNISTIC ENTRY SCREEN")
    print("=" * 100)
    print(f"  Data as of      : {regime['date']}" + (f"  (--as-of {as_of} requested)" if as_of else ""))
    print(f"  Regime          : ry={conditions['ry_regime']}  baa10y={conditions['baa10y_regime']}  "
          f"(confidence: {regime['confidence']})")
    print(f"  Gate 1 source   : {source}")
    print(f"  Gate 1 candidates (top {top_n}): {', '.join(candidates)}")
    if as_of:
        print("  NOTE: --as-of replays MA50/regime from snapshot data, but the earnings-date")
        print("        gate (engine._next_earnings) always queries yfinance's LIVE calendar —")
        print("        it cannot be replayed retroactively. Treat gate 4 here as illustrative only.")
    print()

    # Group candidates by category dir, run screen_tactical (gates 3+4) per group
    survivors_frames = []
    by_cat: dict[str, list[str]] = {}
    for t in candidates:
        by_cat.setdefault(cat_of.get(t, "equities"), []).append(t)

    for cat_dir, tickers in by_cat.items():
        df = screen_tactical(
            conditions, tickers,
            category=cat_dir, benchmark=benchmark, hold_days=hold_days,
            data_dir=data_dir,
        )
        if not df.empty:
            survivors_frames.append(df)

    survivors = pd.concat(survivors_frames, ignore_index=True) if survivors_frames else pd.DataFrame()
    survivor_set = set(survivors["ticker"]) if not survivors.empty else set()

    # Build the combined table for every gate-1 candidate
    rows = []
    today = _date.today()
    for i, t in enumerate(candidates, 1):
        ma = _ma50_stats(data_dir, cat_of.get(t, "equities"), t)
        earn_date = _next_earnings(t)
        earn_days = (earn_date - today).days if earn_date else None
        gate2_pass = bool(ma and ma["above_ma50"])
        gate34_pass = t in survivor_set  # not-extended + RS + earnings, per screen_tactical
        verdict = "ENTER" if (gate2_pass and gate34_pass) else "PASS"

        info = extra_info.get(t, {})

        # Exact duration-matched return -- only worth computing for ENTER
        # survivors (that's the pool select_best_candidate ranks over).
        dur_days = dur_med = dur_win = dur_n = None
        if verdict == "ENTER":
            dur_days = suggested_duration_days(earn_date, today)
            dur_med, dur_win, dur_n = duration_matched_return(
                t, cat_of.get(t, "equities"), matched, dur_days, data_dir
            )

        row = {
            "rank":          i,
            "ticker":        t,
            "already_held":  "YES" if t in held else "",
            "price":         round(ma["price"], 2) if ma else None,
            "ma50":          round(ma["ma50"], 2) if ma else None,
            "dist_from_ma50": f"{ma['dist_pct']:+.1%}" if ma else "n/a",
            "dist_num":      ma["dist_pct"] if ma else None,
            "ma50_status":   ("ABOVE" if gate2_pass else "BELOW") if ma else "no data",
            "next_earnings": str(earn_date) if earn_date else "n/a",
            "earn_in_days":  earn_days if earn_days is not None else "n/a",
            "gate2_ma50":    "PASS" if gate2_pass else "FAIL",
            "gate34_screen_tactical": "PASS" if gate34_pass else "FAIL",
            "verdict":       verdict,
            "category":      cat_of.get(t, "equities"),
            "med_21d":       info.get("med_21d"),
            "win_21d":       info.get("win_21d"),
            "diversity":     info.get("diversity"),
            "duration_days": dur_days,
            "duration_med":  dur_med,
            "duration_win":  dur_win,
            "duration_n":    dur_n,
            "med_252d":      info.get("med_252d"),
        }
        rows.append(row)

    out = pd.DataFrame(rows)

    print(f"{'Rk':>3} {'Ticker':<9} {'Held':<5} {'Price':>9} {'MA50':>9} {'Dist':>8} {'Status':<8} "
          f"{'NextEarn':<12} {'Gate2':<6} {'Gate3+4':<8} {'Verdict':<7}")
    print("-" * 100)
    for _, r in out.iterrows():
        price_s = f"{r['price']:.2f}" if r["price"] is not None else "n/a"
        ma_s    = f"{r['ma50']:.2f}" if r["ma50"] is not None else "n/a"
        print(f"{r['rank']:>3} {r['ticker']:<9} {r['already_held']:<5} {price_s:>9} {ma_s:>9} {r['dist_from_ma50']:>8} "
              f"{r['ma50_status']:<8} {r['next_earnings']:<12} {r['gate2_ma50']:<6} "
              f"{r['gate34_screen_tactical']:<8} {r['verdict']:<7}")

    entries = out[out["verdict"] == "ENTER"]["ticker"].tolist()
    held_entries = out[(out["verdict"] == "ENTER") & (out["already_held"] == "YES")]["ticker"].tolist()
    print()
    print(f"  ENTER candidates (all 4 gates passed): {entries if entries else 'none'}")
    if held_entries:
        print(f"  Of those, already held (no red flag today, NOT a signal to add): {held_entries}")

    print()
    print("-" * 100)
    print("  Selection (least MA50-extension -> ROBUST diversity preferred -> win rate)")
    print(f"  Return/win shown at EACH candidate's own suggested duration "
          f"(min({TIME_EXIT_DAYS}d, earnings-{EARNINGS_BUFFER_DAYS}d)),")
    print("  computed fresh from regime-matched history -- not a flat 21d proxy. med_252d: robustness check only.")
    print("-" * 100)
    pick = select_best_candidate(out, held, data_dir=data_dir, gate1_candidates=candidates, regime_labels=conditions, benchmark=benchmark)
    ranked_pool = out[(out["verdict"] == "ENTER") & (~out["ticker"].isin(held)) & out["dist_num"].notna()].copy()
    if not ranked_pool.empty:
        ranked_pool["diversity_rank"] = ranked_pool["diversity"].map(DIVERSITY_RANK).fillna(3)
        ranked_pool["rank_win"] = ranked_pool["duration_win"].combine_first(ranked_pool["win_21d"])
        ranked_pool = ranked_pool.sort_values(by=["dist_num", "diversity_rank", "rank_win"], ascending=[True, True, False])
        for _, r in ranked_pool.iterrows():
            dur = f"{int(r['duration_days'])}d" if pd.notna(r["duration_days"]) else "n/a"
            if pd.notna(r["duration_med"]):
                dur_med = f"{r['duration_med']:+.1%}"
                dur_win = f"{r['duration_win']:.1%}"
                dur_note = f" (n={int(r['duration_n'])})"
            else:
                dur_med, dur_win = f"{r['med_21d']:+.1%}" if pd.notna(r["med_21d"]) else "n/a", \
                                   f"{r['win_21d']:.1%}" if pd.notna(r["win_21d"]) else "n/a"
                dur_note = " (fallback: 21d fixed, too few obs at exact duration)"
            med252 = f"{r['med_252d']:+.1%}" if pd.notna(r["med_252d"]) else "n/a"
            div = r["diversity"] if pd.notna(r["diversity"]) else "n/a"
            marker = " <- selected" if pick is not None and r["ticker"] == pick["ticker"] else ""
            print(f"    {r['ticker']:<8} ext={r['dist_from_ma50']:>7}  div={div:<9}  duration={dur:<4}  "
                  f"med={dur_med:>7}  win={dur_win:>7}{dur_note}  (252d robustness: {med252:>8}){marker}")
    if pick is None:
        print("  No eligible new candidate (either no ENTER survivors, all already held, fresh-fallback "
              "path lacks 21d data for ranking, or every ranked candidate FAILED the pre-entry tripwire "
              "or execution-drift gate).")
    else:
        pick_med = pick["duration_med"] if pd.notna(pick["duration_med"]) else pick["med_21d"]
        pick_win = pick["duration_win"] if pd.notna(pick["duration_win"]) else pick["win_21d"]
        pick_name = asset_name(pick["ticker"])
        print(f"\n  Best candidate: {pick['ticker']}" + (f"  ({pick_name})" if pick_name else "") + "  "
              f"(entry ${pick['price']:.2f}, MA50 ${pick['ma50']:.2f}, ext {pick['dist_from_ma50']}, "
              f"suggested duration {int(pick['duration_days'])}d, "
              f"med {pick_med:+.1%}, win {pick_win:.1%}, diversity {pick['diversity']})")
        pt = pick.get("pretrade_tripwires")
        if pt is not None:
            print(f"  Pre-entry tripwire gate: PASSED (RS {pt['rs_20d']:+.1%}, "
                  f"cluster {'ok' if not pt['cluster_breakdown'] else 'BREAKDOWN'}, "
                  f"MA50 slope {'rising' if pt['ma50_rising'] else 'FALLING'}) -- "
                  f"vetted as-if-entering-now, not just statically ranked.")
        else:
            print("  Pre-entry tripwire gate: not run (no data_dir -- static ranking only).")
        drift = pick.get("execution_drift")
        if drift is not None:
            print(f"  Execution drift: {drift:+.1%} since signal close (live price vs. ${pick['price']:.2f}) "
                  f"-- within +/-{EXECUTION_DRIFT_THRESHOLD:.1%} tolerance.")
        try:
            vr = vix_review(data_dir)
            print(f"  VIX review (for you to weigh, not a gate): {vr['now']:.2f}  "
                  f"({vr['percentile']:.0%} percentile over {vr['years']:.0f}yr history, "
                  f"5d {vr['chg_5d']:+.2f} -- {vr['trend']})")
        except Exception:
            pass
        print("  Not an auto-buy. Confirm capital (war chest only) before executing manually, then run:")
        print(f"    python run_entry_screen.py --open {pick['ticker']} <fill_price> <shares> <capital_sek>")
    print("=" * 100)

    if pick is None:
        print()
        print("-" * 100)
        print("  BASKET-CRASH CANDIDATES (secondary pathway -- only considered because there is no")
        print("  extension-gate ENTER survivor today; see MEMORY.md 'Sector-capitulation reconstruction'")
        print("  and 'Capitulation stop-sensitivity', 2026-07-29). Below-MA50 by construction -- different")
        print("  stop (trailing-only, no floor, 8%/8%) and different time exit (flat 21d, no earnings")
        print("  buffer) than the extension pathway above. NOT run through the earnings gate or")
        print("  execution-drift filter -- neither is validated for this entry type; left out rather")
        print("  than silently applied. 1-per-sector concentration cap already applied below.")
        print("-" * 100)
        raw_basket = basket_crash_candidates(candidates, cat_of, data_dir)
        capped_basket = cap_basket_crash_concentration(raw_basket)
        if capped_basket:
            for row in sorted(capped_basket, key=lambda r: r["roc_5d"]):
                held_flag = "  [already held]" if row["ticker"] in held else ""
                print(f"    {row['ticker']:<8} sector={row['sector']:<28} 5d_roc={row['roc_5d']:+.1%}  "
                      f"peers_crashing={row['peer_count']}{held_flag}")
        basket_pick = select_best_basket_crash(capped_basket, held) if capped_basket else None
        if basket_pick is None:
            reason = "no candidate in a 5d/-10% crash with >=2 same-sector gate-1 peers also crashing" \
                     if not raw_basket else "all qualifying candidates already held"
            print(f"  No eligible basket-crash candidate today ({reason}).")
        else:
            b_name = asset_name(basket_pick["ticker"])
            print(f"\n  Best candidate: {basket_pick['ticker']}" + (f"  ({b_name})" if b_name else "") + "  "
                  f"(sector={basket_pick['sector']}, 5d_roc={basket_pick['roc_5d']:+.1%}, "
                  f"peers_crashing={basket_pick['peer_count']})")
            print("  Not an auto-buy. Confirm capital (war chest only) before executing manually, then run:")
            print(f"    python run_entry_screen.py --open {basket_pick['ticker']} <fill_price> <shares> "
                  f"<capital_sek> --entry-type basket_crash")
        print("=" * 100)

    return out


# ── Discrete risk state for an open position -- exists so check_signal_
#    changes.py has a single word to diff, the same pattern the guard/
#    silver signals already use, instead of only watching the bare
#    OPEN/CLOSED status word (which never changes while a position is
#    held, no matter what the price actually does). Priority order: an
#    actual stop breach outranks a looming time exit, which outranks a
#    softer tripwire warning. ─────────────────────────────────────────────

def sleeve_risk_state(trig: dict, any_watch: bool) -> str:
    if trig["current_price"] is not None and trig["binding_stop"] is not None \
            and trig["current_price"] <= trig["binding_stop"]:
        return "STOPPED"
    if trig["time_exit_days_remaining"] <= 0:
        return "TIME-EXIT-DUE"
    if any_watch:
        return "TRIPWIRE"
    return "CLEAN"


# ── Compact daily summary for fi_tracker.py's TACTICAL RULES section --
#    the full candidate table (~30 rows) belongs in an on-demand run of this
#    script, not in the daily status.md digest, so this reuses the same
#    underlying functions but prints a short block instead. ────────────────

def sleeve_daily_summary(data_dir: Path | None = None, top_n: int = 30, benchmark: str = "SPY") -> None:
    if data_dir is None:
        data_dir = config.raw_data_dir()

    print(f"\n  Opportunistic Sleeve")
    state = load_sleeve_state()

    if state.get("open"):
        entry_type = state.get("entry_type", "extension")
        trig = compute_exit_triggers(state["entry_price"], state["entry_date"],
                                      state["ticker"], state["category"], data_dir, entry_type=entry_type)
        tw = compute_tripwires(state, data_dir, benchmark)
        any_watch = (not tw["rs_ok"]) or tw["regime_changed"] or tw["cluster_breakdown"] or not tw["ma50_rising"]
        risk = sleeve_risk_state(trig, any_watch)
        print(f"    Status         : OPEN -- {state['ticker']} @ ${state['entry_price']:.2f} "
              f"({state['entry_date']}), {state['shares']} sh, entry_type={entry_type}")
        if trig["current_price"]:
            risk_str = _risk_to_stop_str(trig, state["shares"], state["fx_at_entry"], state["capital_sek"])
            print(f"    Current price  : ${trig['current_price']:.2f}"
                  + (f"  (risk to stop: {risk_str})" if risk_str else ""))
        else:
            print(f"    Current price  : n/a")
        print(f"    Time exit      : {trig['time_exit_date']}  ({trig['time_exit_days_remaining']}d left)")
        if trig["trailing_stop"] is not None:
            print(f"    Trailing stop  : ${trig['trailing_stop']:.2f}  (peak ${trig['peak_price']:.2f} since entry)")
        print(f"    Binding stop   : ${trig['binding_stop']:.2f} ({trig['binding_label']})"
              if trig["binding_stop"] else "    Binding stop   : n/a")
        print(f"    Tripwires      : {'CLEAN' if not any_watch else 'FLAGGED -- run run_entry_screen.py for detail'}")
        print(f"    Tripwire detail : {_tripwire_detail_line(tw)}")
        print(f"    Risk           : {risk}")
        return

    regime = current_regime(data_dir)
    conditions = {
        "ry_regime": regime["regimes"]["ry_regime"],
        "baa10y_regime": regime["regimes"]["baa10y_regime"],
    }
    candidates, cat_of, _, extra_info = get_regime_candidates(conditions, top_n, data_dir)
    held = already_held_tickers()
    matched = _matched_dates(conditions, data_dir)
    today = _date.today()

    survivors_frames = []
    by_cat: dict[str, list[str]] = {}
    for t in candidates:
        by_cat.setdefault(cat_of.get(t, "equities"), []).append(t)
    for cat_dir, tickers in by_cat.items():
        df = screen_tactical(conditions, tickers, category=cat_dir, benchmark=benchmark,
                              hold_days=21, data_dir=data_dir)
        if not df.empty:
            survivors_frames.append(df)
    survivors = pd.concat(survivors_frames, ignore_index=True) if survivors_frames else pd.DataFrame()
    survivor_set = set(survivors["ticker"]) if not survivors.empty else set()

    rows = []
    for t in candidates:
        ma = _ma50_stats(data_dir, cat_of.get(t, "equities"), t)
        info = extra_info.get(t, {})
        gate2_pass = bool(ma and ma["above_ma50"])
        verdict = "ENTER" if (gate2_pass and t in survivor_set) else "PASS"

        dur_days = dur_med = dur_win = None
        if verdict == "ENTER":
            earn_date = _next_earnings(t)
            dur_days = suggested_duration_days(earn_date, today)
            dur_med, dur_win, _ = duration_matched_return(t, cat_of.get(t, "equities"), matched, dur_days, data_dir)

        rows.append({
            "ticker": t, "verdict": verdict, "category": cat_of.get(t, "equities"),
            "dist_num": ma["dist_pct"] if ma else None,
            "dist_from_ma50": f"{ma['dist_pct']:+.1%}" if ma else "n/a",
            "price": ma["price"] if ma else None, "ma50": ma["ma50"] if ma else None,
            "diversity": info.get("diversity"), "med_21d": info.get("med_21d"), "win_21d": info.get("win_21d"),
            "duration_days": dur_days, "duration_med": dur_med, "duration_win": dur_win,
        })
    out = pd.DataFrame(rows)
    pick = (select_best_candidate(out, held, data_dir=data_dir, gate1_candidates=candidates,
                                   regime_labels=conditions, benchmark=benchmark)
            if not out.empty else None)

    print(f"    Status         : CLOSED (0/1 position)")
    if pick is not None:
        pick_med = pick["duration_med"] if pd.notna(pick["duration_med"]) else pick["med_21d"]
        dur = int(pick["duration_days"]) if pd.notna(pick["duration_days"]) else 21
        pick_name = asset_name(pick["ticker"])
        drift = pick.get("execution_drift")
        drift_note = f", drift {drift:+.1%}" if drift is not None else ""
        price_str = f"${pick['price']:.2f}" if pd.notna(pick.get("price")) else "n/a"
        # Kept short and self-contained on purpose (see MEMORY.md "Sleeve
        # alert clarity", 2026-07-30) -- this exact text is what ends up in
        # the Telegram push via check_signal_changes.py, and the user may
        # not be able to run the full screen before needing to act on it.
        print(f"    Best candidate : {pick['ticker']}" + (f" ({pick_name})" if pick_name else "") + f"  {price_str}  "
              f"(ext {pick['dist_from_ma50']}, {dur}d med {pick_med:+.1%}, div {pick['diversity']}{drift_note})")
        print(f"    Plan           : buy near {price_str}, hold ~{dur}d, "
              f"stop = MA50-{MA50_BUFFER_PCT:.0%} then trails {TRAILING_PCT:.0%} once +{TRAILING_TRIGGER_PCT:.0%} gain")
        print(f"    Open           : run_entry_screen.py --open {pick['ticker']} <fill_price> <shares> <capital_sek>")
        try:
            vr = vix_review(data_dir)
            print(f"    VIX review     : {vr['now']:.2f}  ({vr['percentile']:.0%} percentile, "
                  f"{vr['trend']}) -- for review, not a gate")
        except Exception:
            pass
    else:
        print(f"    Best candidate : none eligible today (either no ENTER survivors, or all "
              f"failed the pre-entry tripwire or execution-drift gate)")

    if pick is None:
        raw_basket = basket_crash_candidates(candidates, cat_of, data_dir)
        capped_basket = cap_basket_crash_concentration(raw_basket)
        basket_pick = select_best_basket_crash(capped_basket, held) if capped_basket else None
        if basket_pick is not None:
            b_name = asset_name(basket_pick["ticker"])
            b_price = f"${basket_pick['price']:.2f}" if basket_pick.get("price") is not None else "n/a"
            print(f"    Basket-crash   : {basket_pick['ticker']}" + (f" ({b_name})" if b_name else "") + f"  {b_price}  "
                  f"(sector {basket_pick['sector']}, {basket_pick['roc_5d']:+.1%} 5d, "
                  f"{basket_pick['peer_count']} peers crashing)")
            print(f"    Plan           : buy near {b_price}, flat 21d exit, "
                  f"NO stop until +{BASKET_TRAILING_TRIGGER_PCT:.0%} gain then trails {BASKET_TRAILING_PCT:.0%} "
                  f"(no floor before that -- riskier than the extension pathway above)")
            print(f"    Open           : run_entry_screen.py --open {basket_pick['ticker']} <fill_price> <shares> "
                  f"<capital_sek> --entry-type basket_crash")
        else:
            print(f"    Basket-crash   : none eligible today")


# ── Position lifecycle (records a manually-executed trade -- no brokerage
#    integration, this is decision-support/record-keeping only) ────────────

def open_position(ticker: str, entry_price: float, shares: int, capital_sek: float,
                   data_dir: Path | None = None, entry_type: str = "extension") -> None:
    if entry_type not in ("extension", "basket_crash"):
        raise SystemExit(f"Unknown --entry-type {entry_type!r} -- must be 'extension' or 'basket_crash'.")
    if data_dir is None:
        data_dir = config.raw_data_dir()

    existing = load_sleeve_state()
    if existing.get("open"):
        raise SystemExit(
            f"Sleeve already occupied by {existing['ticker']} (entered {existing['entry_date']}). "
            "Position cap is 1 -- close it first with --close."
        )

    category = "equities"
    regime = current_regime(data_dir)
    conditions = {
        "ry_regime":     regime["regimes"]["ry_regime"],
        "baa10y_regime": regime["regimes"]["baa10y_regime"],
    }
    candidates, _, _, _ = get_regime_candidates(conditions, 30, data_dir)
    peers = discover_cluster_peers(ticker, candidates, exclude=already_held_tickers(), data_dir=data_dir)
    fx = float(reader.load(reader.ticker_path(data_dir, "fx", "USDSEK=X"))["close"].dropna().iloc[-1])

    state = {
        "open": True, "ticker": ticker, "category": category, "entry_type": entry_type,
        "entry_date": str(_date.today()), "entry_price": entry_price,
        "shares": shares, "capital_sek": capital_sek, "fx_at_entry": fx,
        "entry_ry_regime": conditions["ry_regime"], "entry_baa10y_regime": conditions["baa10y_regime"],
        "cluster_peers": peers,
    }
    _write_sleeve_state(state)
    print(f"Sleeve opened: {ticker} @ ${entry_price:.2f}, {shares} shares, {capital_sek:,.0f} kr, "
          f"entry_type={entry_type}, regime {conditions['ry_regime']}/{conditions['baa10y_regime']}, peers {peers}")


def close_position() -> None:
    state = load_sleeve_state()
    if not state.get("open"):
        print("Sleeve already closed -- nothing to do.")
        return
    print(f"Closing sleeve position: {state['ticker']} (entered {state['entry_date']} @ ${state['entry_price']:.2f})")
    _write_sleeve_state({"open": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Opportunistic entry screen (4-gate, war chest / home base capital).")
    parser.add_argument("--top-n", type=int, default=30, help="Gate-1 regime ranking depth (default 30)")
    parser.add_argument("--hold-days", type=int, default=21, help="Earnings avoidance window in days (default 21 = 3 weeks)")
    parser.add_argument("--benchmark", default="SPY", help="Benchmark for screen_tactical's RS gate (default SPY)")
    parser.add_argument("--data-dir", default=None, help="Override parquet data dir (e.g. a point-in-time snapshot)")
    parser.add_argument("--as-of", default=None, help="Label only — for documenting a retroactive replay (see --data-dir)")
    parser.add_argument("--open", nargs=4, metavar=("TICKER", "ENTRY_PRICE", "SHARES", "CAPITAL_SEK"),
                         help="Record a manually-executed entry and open the sleeve (position cap: 1)")
    parser.add_argument("--entry-type", choices=["extension", "basket_crash"], default="extension",
                         help="Which pathway this --open entry came from (default: extension). "
                              "Governs the stop/time-exit rule used for the position -- see compute_exit_triggers().")
    parser.add_argument("--close", action="store_true", help="Record a manual exit and close the sleeve")
    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else None

    if args.close:
        close_position()
    elif args.open:
        tkr, price, shares, capital = args.open
        open_position(tkr, float(price), int(shares), float(capital), data_dir=data_dir, entry_type=args.entry_type)
    else:
        run_entry_screen(
            top_n=args.top_n,
            hold_days=args.hold_days,
            benchmark=args.benchmark,
            data_dir=data_dir,
            as_of=args.as_of,
        )
