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
#     MA50 breach, or HARD_STOP_PCT below entry -- whichever binds first
TIME_EXIT_DAYS       = 30
EARNINGS_BUFFER_DAYS = 3
HARD_STOP_PCT        = 0.02
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
        "#   python run_entry_screen.py --close",
        "#",
        "# Position cap: 1 open position at a time. war-chest capital only.",
        '# See MEMORY.md "Formalize the opportunistic sleeve" for the full rule set.',
        "",
        f"open       = {str(bool(state.get('open', False))).lower()}",
        f'ticker     = "{state.get("ticker", "")}"',
        f'category   = "{state.get("category", "")}"',
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

def binding_stop(entry_price: float, ma50: float) -> tuple[float, str]:
    """The binding stop is whichever level is CLOSER to entry (hit first as
    price falls) -- not the farther one. Below ~entry where hard_stop crosses
    ma50, MA50 binds; above that crossover, the 2% hard stop takes over and
    caps risk at ~2% of capital regardless of how extended the entry was."""
    hard_stop = entry_price * (1 - HARD_STOP_PCT)
    if ma50 >= hard_stop:
        return ma50, "MA50"
    return hard_stop, "HARD"


def compute_exit_triggers(
    entry_price: float,
    entry_date: str,
    ticker: str,
    category: str,
    data_dir: Path,
) -> dict:
    entry_dt = _datetime.strptime(entry_date, "%Y-%m-%d").date()
    ma = _ma50_stats(data_dir, category, ticker)
    ma50 = ma["ma50"] if ma else None

    earn_date = _next_earnings(ticker)
    earn_time_exit = (earn_date - _timedelta(days=EARNINGS_BUFFER_DAYS)) if earn_date else None
    flat_time_exit = entry_dt + _timedelta(days=TIME_EXIT_DAYS)
    time_exit = min(flat_time_exit, earn_time_exit) if earn_time_exit else flat_time_exit
    time_exit_days = (time_exit - entry_dt).days
    time_exit_binding = "earnings-3d" if (earn_time_exit and earn_time_exit < flat_time_exit) else "flat 30d"

    stop_price, stop_label = (binding_stop(entry_price, ma50) if ma50 else (None, "n/a"))

    return {
        "ma50":              ma50,
        "hard_stop":         round(entry_price * (1 - HARD_STOP_PCT), 2),
        "binding_stop":      round(stop_price, 2) if stop_price else None,
        "binding_label":     stop_label,
        "time_exit_date":    time_exit,
        "time_exit_days":    time_exit_days,
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


# ── Selection rule (no open position): least MA50-extension -> ROBUST
#    diversity preferred -> win rate. Effect sized on med_21d/win_21d (the
#    horizon that actually matches a ~30d hold) -- med_252d is kept only as
#    a diversity/robustness cross-check, not the headline return number. ──

def select_best_candidate(out: pd.DataFrame, held: set[str]) -> dict | None:
    pool = out[(out["verdict"] == "ENTER") & (~out["ticker"].isin(held)) & out["dist_num"].notna()]
    if pool.empty:
        return None
    pool = pool.copy()
    pool["diversity_rank"] = pool["diversity"].map(DIVERSITY_RANK).fillna(3)
    pool = pool.sort_values(
        by=["dist_num", "diversity_rank", "win_21d"],
        ascending=[True, True, False],
    )
    return pool.iloc[0].to_dict()


# ── Sleeve status display (position already open) ──────────────────────────

def print_sleeve_status(state: dict, data_dir: Path, benchmark: str = "SPY") -> None:
    ticker, category = state["ticker"], state["category"]
    trig = compute_exit_triggers(state["entry_price"], state["entry_date"], ticker, category, data_dir)
    tw = compute_tripwires(state, data_dir, benchmark)

    held = "Yes" if ticker in already_held_tickers() else "No"
    print("=" * 100)
    print("OPPORTUNISTIC SLEEVE")
    print("=" * 100)
    print(f"  Status          : OPEN (1/1 position -- new entries blocked)")
    print(f"  Ticker          : {ticker}")
    print(f"  Already held?   : {held} ({state['shares']} shares from this entry)")
    print(f"  Entered         : {state['entry_date']}")
    print(f"  Entry price     : ${state['entry_price']:.2f}  "
          f"({state['shares']} shares, {state['capital_sek']:,.0f} kr allocated)")
    print(f"  FX at entry     : {state['fx_at_entry']}")
    print()
    print(f"  Exit triggers")
    print(f"    Time exit       : {trig['time_exit_date']}  "
          f"({trig['time_exit_days']}d; bound by {trig['time_exit_binding']})")
    print(f"    MA50 stop       : ${trig['ma50']:.2f}" if trig["ma50"] else "    MA50 stop       : n/a")
    print(f"    Hard stop       : ${trig['hard_stop']:.2f}")
    print(f"    Binding stop    : ${trig['binding_stop']:.2f}  ({trig['binding_label']})"
          if trig["binding_stop"] else "    Binding stop    : n/a")
    print(f"    Next earnings   : {trig['next_earnings'] if trig['next_earnings'] else 'n/a'}")
    if trig["current_price"] and trig["binding_stop"]:
        risk_sh = trig["current_price"] - trig["binding_stop"]
        risk_kr = risk_sh * state["shares"] * state["fx_at_entry"]
        print(f"    Current price   : ${trig['current_price']:.2f}  "
              f"(risk to binding stop: {risk_kr:,.0f} kr, {risk_kr/state['capital_sek']:.2%} of sleeve capital)")
    print()
    print(f"  Post-entry tripwires")
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
        cluster_flag = "WATCH -- BREAKDOWN" if tw["cluster_breakdown"] else "OK"
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
    print("  Selection (least MA50-extension -> ROBUST diversity preferred -> 21d win rate)")
    print("  Effect sized on med_21d/win_21d (matches a ~30d hold); med_252d is a robustness check only.")
    print("-" * 100)
    pick = select_best_candidate(out, held)
    ranked_pool = out[(out["verdict"] == "ENTER") & (~out["ticker"].isin(held)) & out["dist_num"].notna()].copy()
    if not ranked_pool.empty:
        ranked_pool["diversity_rank"] = ranked_pool["diversity"].map(DIVERSITY_RANK).fillna(3)
        ranked_pool = ranked_pool.sort_values(by=["dist_num", "diversity_rank", "win_21d"], ascending=[True, True, False])
        for _, r in ranked_pool.iterrows():
            med21 = f"{r['med_21d']:+.1%}" if pd.notna(r["med_21d"]) else "n/a"
            win21 = f"{r['win_21d']:.1%}" if pd.notna(r["win_21d"]) else "n/a"
            med252 = f"{r['med_252d']:+.1%}" if "med_252d" in r and pd.notna(r["med_252d"]) else "n/a"
            div = r["diversity"] if pd.notna(r["diversity"]) else "n/a"
            marker = " <- selected" if pick is not None and r["ticker"] == pick["ticker"] else ""
            print(f"    {r['ticker']:<8} ext={r['dist_from_ma50']:>7}  div={div:<9}  "
                  f"21d_med={med21:>7}  21d_win={win21:>7}  (252d robustness: {med252:>8}){marker}")
    if pick is None:
        print("  No eligible new candidate (either no ENTER survivors, all already held, or fresh-fallback "
              "path lacks 21d data for ranking).")
    else:
        print(f"\n  Best candidate: {pick['ticker']}  "
              f"(entry ${pick['price']:.2f}, MA50 ${pick['ma50']:.2f}, ext {pick['dist_from_ma50']}, "
              f"21d med {pick['med_21d']:+.1%}, 21d win {pick['win_21d']:.1%}, diversity {pick['diversity']})")
        print("  Not an auto-buy. Confirm capital (war chest only) before executing manually, then run:")
        print(f"    python run_entry_screen.py --open {pick['ticker']} <fill_price> <shares> <capital_sek>")
    print("=" * 100)

    return out


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
        trig = compute_exit_triggers(state["entry_price"], state["entry_date"],
                                      state["ticker"], state["category"], data_dir)
        tw = compute_tripwires(state, data_dir, benchmark)
        any_watch = (not tw["rs_ok"]) or tw["regime_changed"] or tw["cluster_breakdown"] or not tw["ma50_rising"]
        print(f"    Status         : OPEN -- {state['ticker']} @ ${state['entry_price']:.2f} "
              f"({state['entry_date']}), {state['shares']} sh")
        print(f"    Time exit      : {trig['time_exit_date']}  ({trig['time_exit_days']}d left)")
        print(f"    Binding stop   : ${trig['binding_stop']:.2f} ({trig['binding_label']})"
              if trig["binding_stop"] else "    Binding stop   : n/a")
        print(f"    Tripwires      : {'CLEAN' if not any_watch else 'FLAGGED -- run run_entry_screen.py for detail'}")
        return

    regime = current_regime(data_dir)
    conditions = {
        "ry_regime": regime["regimes"]["ry_regime"],
        "baa10y_regime": regime["regimes"]["baa10y_regime"],
    }
    candidates, cat_of, _, extra_info = get_regime_candidates(conditions, top_n, data_dir)
    held = already_held_tickers()

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
        rows.append({
            "ticker": t, "verdict": verdict,
            "dist_num": ma["dist_pct"] if ma else None,
            "dist_from_ma50": f"{ma['dist_pct']:+.1%}" if ma else "n/a",
            "price": ma["price"] if ma else None, "ma50": ma["ma50"] if ma else None,
            "diversity": info.get("diversity"), "med_21d": info.get("med_21d"), "win_21d": info.get("win_21d"),
        })
    out = pd.DataFrame(rows)
    pick = select_best_candidate(out, held) if not out.empty else None

    print(f"    Status         : CLOSED (0/1 position)")
    if pick is not None:
        print(f"    Best candidate : {pick['ticker']}  (ext {pick['dist_from_ma50']}, "
              f"21d med {pick['med_21d']:+.1%}, div {pick['diversity']}) -- run run_entry_screen.py for full detail")
    else:
        print(f"    Best candidate : none eligible today")


# ── Position lifecycle (records a manually-executed trade -- no brokerage
#    integration, this is decision-support/record-keeping only) ────────────

def open_position(ticker: str, entry_price: float, shares: int, capital_sek: float,
                   data_dir: Path | None = None) -> None:
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
        "open": True, "ticker": ticker, "category": category,
        "entry_date": str(_date.today()), "entry_price": entry_price,
        "shares": shares, "capital_sek": capital_sek, "fx_at_entry": fx,
        "entry_ry_regime": conditions["ry_regime"], "entry_baa10y_regime": conditions["baa10y_regime"],
        "cluster_peers": peers,
    }
    _write_sleeve_state(state)
    print(f"Sleeve opened: {ticker} @ ${entry_price:.2f}, {shares} shares, {capital_sek:,.0f} kr, "
          f"regime {conditions['ry_regime']}/{conditions['baa10y_regime']}, peers {peers}")


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
    parser.add_argument("--close", action="store_true", help="Record a manual exit and close the sleeve")
    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else None

    if args.close:
        close_position()
    elif args.open:
        tkr, price, shares, capital = args.open
        open_position(tkr, float(price), int(shares), float(capital), data_dir=data_dir)
    else:
        run_entry_screen(
            top_n=args.top_n,
            hold_days=args.hold_days,
            benchmark=args.benchmark,
            data_dir=data_dir,
            as_of=args.as_of,
        )
