"""
run_comparison_backtest.py

Head-to-head: current Reactor Core portfolio vs regime rotation strategies.
Period: 2004–present. TC: 10bps on turnover. Benchmark: SPY.

Strategy A — Current portfolio static
    Actual weights from portfolio.toml (HWM excluded, 7 core positions).
    ±5pp drift rebalance trigger, 10bps TC on turnover.

Strategy B — Full universe EW rotation
    Top 8 assets per regime, walk-forward conditional return selection,
    3-day confirmation, 10bps TC at each transition.

Strategy C — Current portfolio regime-tilted
    Same 7 assets, softmax weights per regime (walk-forward), 10bps TC.
    Weight cap 40%, floor 5%.

Strategy D — Hybrid
    50% anchor (Gold + LLY + WMT, fixed proportions), 50% universe EW
    rotation (5 assets, walk-forward), 10bps TC on rotation half.

Weights for Strategy A (actual, HWM excluded, normalized):
    Gold 23.9%  LLY 19.2%  WMT 18.4%  CCJ 12.2%  VRT 12.0%  AVGO 9.9%  Silver 4.3%
"""
from __future__ import annotations

import io, sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.analysis import regimes as regime_module
from asset_universe.analysis.engine import _regime_end_dates
from asset_universe.store import reader

# ── Constants ─────────────────────────────────────────────────────────────────
TC_BPS        = 10       # basis points per one-way turnover
REBAL_TRIGGER = 0.05     # ±5pp drift before rebalancing (Strategy A only)
N_ROT         = 8        # rotation assets per period (Strategy B)
N_ROT_D       = 5        # rotation assets for Strategy D (+ 3 anchor = 8 total)
MIN_DATES     = 5        # min matched dates for walk-forward selection
CONFIRM_DAYS  = 3        # calendar days for regime confirmation
START_DATE    = "2004-01-01"

# Actual portfolio weights (HWM excluded, computed from portfolio.toml × prices 2026-06-30)
_RAW = {
    "GC=F":  0.239,   # Gold  (GC_F in parquet)
    "SI=F":  0.043,   # Silver (SI_F in parquet)
    "LLY":   0.192,
    "WMT":   0.184,
    "CCJ":   0.122,
    "VRT":   0.120,
    "AVGO":  0.099,
}
_s = sum(_RAW.values())
PORT_WEIGHTS = {k: v / _s for k, v in _RAW.items()}

# Strategy D anchor: Gold + LLY + WMT scaled to 50% of portfolio
_ANC = {k: PORT_WEIGHTS[k] for k in ("GC=F", "LLY", "WMT")}
_as  = sum(_ANC.values())
ANCHOR_W = {k: v / _as * 0.50 for k, v in _ANC.items()}

# Pre-IPO: asset earns 0%, weight redistributed to available assets
PRE_IPO = {
    "VRT":  pd.Timestamp("2020-02-07"),
    "AVGO": pd.Timestamp("2009-08-06"),
}

# Parquet location for each portfolio ticker
TICKER_CATS: dict[str, tuple[str, str]] = {
    "GC=F":  ("commodities", "GC_F"),
    "SI=F":  ("commodities", "SI_F"),
    "LLY":   ("equities",    "LLY"),
    "WMT":   ("equities",    "WMT"),
    "CCJ":   ("equities",    "CCJ"),
    "VRT":   ("equities",    "VRT"),
    "AVGO":  ("equities",    "AVGO"),
    "SPY":   ("equities",    "SPY"),
}


# ── Data loading ───────────────────────────────────────────────────────────────

def load_close(data_dir: Path, cat: str, safe: str) -> pd.Series | None:
    path = reader.ticker_path(data_dir, cat, safe)
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index()


def load_portfolio_prices(data_dir: Path) -> pd.DataFrame:
    print("Loading portfolio prices from parquet...")
    series: dict[str, pd.Series] = {}
    for tkr, (cat, safe) in TICKER_CATS.items():
        s = load_close(data_dir, cat, safe)
        if s is not None:
            series[tkr] = s
            print(f"  {tkr:<8} {s.index[0].date()} → {s.index[-1].date()}  ({len(s):,}d)")
        else:
            print(f"  {tkr:<8} NOT FOUND")
    return pd.DataFrame(series).sort_index().loc[START_DATE:]


def load_universe_prices(data_dir: Path) -> dict[str, pd.Series]:
    screen = PROJECT_ROOT / "universe_screen_results.csv"
    if not screen.exists():
        print("  WARNING: universe_screen_results.csv not found — rotation disabled")
        return {}
    df = pd.read_csv(screen).head(50)
    prices: dict[str, pd.Series] = {}
    for _, row in df.iterrows():
        tkr = row["ticker"]
        cat_raw = str(row.get("category", "")).lower()
        if "commodity" in cat_raw:
            cat = "commodities"
        elif "etf" in cat_raw or "ucits" in cat_raw:
            cat = "intl_etfs"
        else:
            cat = "equities"
        s = load_close(data_dir, cat, reader.safe_name(tkr))
        if s is not None:
            prices[tkr] = s
    # Add portfolio instruments not already in universe
    for tkr, (cat, safe) in TICKER_CATS.items():
        if tkr not in prices and tkr != "SPY":
            s = load_close(data_dir, cat, safe)
            if s is not None:
                prices[tkr] = s
    print(f"  Universe: {len(prices)} assets")
    return prices


# ── Regime transitions ─────────────────────────────────────────────────────────

def get_transitions(labeled_df: pd.DataFrame) -> list[tuple]:
    """
    Confirmed regime transitions with CONFIRM_DAYS hold.
    Prepends a virtual transition at the first valid date so rotation
    strategies cover the full period from the start.
    Returns list of (date, ry_label, baa_label).
    """
    out: list[tuple] = []
    prev_ry = prev_baa = None

    for date, row in labeled_df[["ry_regime", "baa10y_regime"]].iterrows():
        ry, baa = row["ry_regime"], row["baa10y_regime"]
        if pd.isna(ry) or pd.isna(baa):
            continue
        if prev_ry is None:
            out.append((date, ry, baa))       # virtual start
            prev_ry, prev_baa = ry, baa
            continue
        if ry != prev_ry or baa != prev_baa:
            end = date + pd.Timedelta(days=CONFIRM_DAYS)
            fut = labeled_df.loc[date:end, ["ry_regime", "baa10y_regime"]]
            if (len(fut) >= 2
                    and (fut["ry_regime"] == ry).all()
                    and (fut["baa10y_regime"] == baa).all()):
                out.append((date, ry, baa))
                prev_ry, prev_baa = ry, baa

    return out


# ── Walk-forward asset selection ───────────────────────────────────────────────

def select_wf(
    labeled_df: pd.DataFrame,
    universe_prices: dict[str, pd.Series],
    before: pd.Timestamp,
    ry: str,
    baa: str,
    n: int,
    fallback: list[str],
) -> list[str]:
    """
    Select top N assets by capped 252d median conditional return,
    using only dates before `before` (no lookahead).
    """
    cond = {"ry_regime": ry, "baa10y_regime": baa}
    hist = labeled_df[labeled_df.index < before]
    mask = pd.Series(True, index=hist.index)
    for k, v in cond.items():
        mask &= hist[k] == v
    matched = hist.index[mask]

    if len(matched) < MIN_DATES:
        return fallback[:n]

    ends = _regime_end_dates(hist, cond, matched)
    rows: list[tuple[str, float]] = []

    for tkr, prices in universe_prices.items():
        rets: list[float] = []
        for dt in matched:
            idx = prices.index.searchsorted(dt)
            if idx >= len(prices) or abs((prices.index[idx] - dt).days) > 5:
                continue
            fwd = idx + 252
            end_dt = ends.get(dt)
            if end_dt is not None:
                fwd = min(fwd, prices.index.searchsorted(end_dt))
            if fwd >= len(prices) or fwd <= idx:
                continue
            p0, p1 = prices.iloc[idx], prices.iloc[fwd]
            if p0 > 0:
                rets.append((p1 - p0) / p0)
        if len(rets) >= MIN_DATES:
            rows.append((tkr, float(np.median(rets))))

    if not rows:
        return fallback[:n]

    rows.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in rows[:n]]


# ── Weight helpers ─────────────────────────────────────────────────────────────

def eff_w(base: dict[str, float], date: pd.Timestamp) -> dict[str, float]:
    """Redistribute pre-IPO asset weight proportionally to available assets."""
    w = dict(base)
    dropped = 0.0
    for tkr, ipo in PRE_IPO.items():
        if tkr in w and date < ipo:
            dropped += w.pop(tkr)
    s = sum(w.values())
    return {k: v / s for k, v in w.items()} if s > 0 else w


def tc_drag(old: dict[str, float], new: dict[str, float]) -> float:
    all_t = set(old) | set(new)
    turnover = sum(abs(new.get(t, 0.0) - old.get(t, 0.0)) for t in all_t) / 2
    return turnover * TC_BPS / 10000


def daily_port_ret(prices: pd.DataFrame, i: int, w: dict[str, float]) -> float:
    ret = 0.0
    for t, wt in w.items():
        if t in prices.columns:
            p0 = prices[t].iloc[i - 1]
            p1 = prices[t].iloc[i]
            if pd.notna(p0) and pd.notna(p1) and p0 > 0:
                ret += wt * (p1 - p0) / p0
    return ret


# ── Strategy A: Static ─────────────────────────────────────────────────────────

def simulate_static(prices: pd.DataFrame) -> pd.Series:
    tickers = [t for t in PORT_WEIGHTS if t in prices.columns]
    nav = 1.0
    nav_out: list[float] = []
    w_cur: dict[str, float] = {}

    for i, date in enumerate(prices.index):
        w_tgt = eff_w({t: PORT_WEIGHTS[t] for t in tickers}, date)

        if not w_cur:
            w_cur = dict(w_tgt)
            nav_out.append(nav)
            continue

        # Daily return using current weights
        port_ret = daily_port_ret(prices, i, w_cur)
        nav *= (1 + port_ret)

        # Drift weights forward
        w_new: dict[str, float] = {}
        for t, wt in w_cur.items():
            if t in prices.columns:
                p0 = prices[t].iloc[i - 1]
                p1 = prices[t].iloc[i]
                if pd.notna(p0) and pd.notna(p1) and p0 > 0:
                    w_new[t] = wt * (1 + (p1 - p0) / p0)
                else:
                    w_new[t] = wt
        s = sum(w_new.values())
        if s > 0:
            w_cur = {k: v / s for k, v in w_new.items()}

        # Rebalance trigger
        drift = max(abs(w_cur.get(t, 0.0) - w_tgt.get(t, 0.0)) for t in w_tgt)
        if drift > REBAL_TRIGGER:
            nav *= (1 - tc_drag(w_cur, w_tgt))
            w_cur = dict(w_tgt)

        nav_out.append(nav)

    return pd.Series(nav_out, index=prices.index)


# ── Strategy B / D: Rotation ───────────────────────────────────────────────────

def simulate_rotation(
    prices: pd.DataFrame,
    universe_prices: dict[str, pd.Series],
    labeled_df: pd.DataFrame,
    transitions: list[tuple],
    anchor_w: dict[str, float] | None = None,
    n_rot: int = N_ROT,
) -> tuple[pd.Series, list[dict]]:
    """
    Rotate holdings at each confirmed transition.
    anchor_w: if set (Strategy D), these weights are fixed; n_rot assets fill the rest.
    Returns (nav_series, selection_log).
    """
    fallback = [t for t in PORT_WEIGHTS if t in prices.columns]
    nav_out: dict[pd.Timestamp, float] = {}
    selection_log: list[dict] = []
    nav = 1.0
    prev_h: dict[str, float] = {}

    # Universe excluding anchor (for D) to keep clean separation
    rot_universe = {t: p for t, p in universe_prices.items()
                    if t not in (anchor_w or {})}

    for idx, (trans_date, ry, baa) in enumerate(transitions):
        next_date = (transitions[idx + 1][0]
                     if idx + 1 < len(transitions)
                     else prices.index[-1])

        selected = select_wf(labeled_df, rot_universe, trans_date,
                              ry, baa, n_rot, fallback)

        if anchor_w:
            rot_w = 0.50 / len(selected) if selected else 0.0
            new_h = {**anchor_w, **{t: rot_w for t in selected}}
        else:
            ew = 1.0 / len(selected) if selected else 0.0
            new_h = {t: ew for t in selected}

        selection_log.append({
            "date": trans_date.date(), "ry": ry, "baa": baa,
            "selected": ", ".join(selected),
        })

        # Apply TC on turnover from previous holdings
        nav *= (1 - tc_drag(prev_h, new_h))

        # Simulate this period
        period = prices.loc[trans_date:next_date]
        for i in range(1, len(period)):
            w_day = eff_w(new_h, period.index[i])
            nav *= (1 + daily_port_ret(period, i, w_day))
            nav_out[period.index[i]] = nav

        prev_h = new_h

    return pd.Series(nav_out).sort_index(), selection_log


# ── Strategy C: Regime-tilted ──────────────────────────────────────────────────

def simulate_regime_tilted(
    prices: pd.DataFrame,
    labeled_df: pd.DataFrame,
    transitions: list[tuple],
    universe_prices: dict[str, pd.Series],
) -> pd.Series:
    """Same 7 assets, weights shifted by walk-forward regime medians via softmax."""
    tickers = [t for t in PORT_WEIGHTS if t in prices.columns]
    nav_out: dict[pd.Timestamp, float] = {}
    nav = 1.0
    prev_w = {t: PORT_WEIGHTS[t] for t in tickers}

    for idx, (trans_date, ry, baa) in enumerate(transitions):
        next_date = (transitions[idx + 1][0]
                     if idx + 1 < len(transitions)
                     else prices.index[-1])

        cond = {"ry_regime": ry, "baa10y_regime": baa}
        hist  = labeled_df[labeled_df.index < trans_date]
        mask  = pd.Series(True, index=hist.index)
        for k, v in cond.items():
            mask &= hist[k] == v
        matched = hist.index[mask]

        new_w = prev_w.copy()
        if len(matched) >= MIN_DATES:
            ends    = _regime_end_dates(hist, cond, matched)
            medians: dict[str, float] = {}
            for tkr in tickers:
                p_series = universe_prices.get(tkr)
                if p_series is None and tkr in prices.columns:
                    p_series = prices[tkr].dropna()
                if p_series is None:
                    continue
                rets: list[float] = []
                for dt in matched:
                    idx2 = p_series.index.searchsorted(dt)
                    if idx2 >= len(p_series) or abs((p_series.index[idx2] - dt).days) > 5:
                        continue
                    fwd = idx2 + 252
                    end_dt = ends.get(dt)
                    if end_dt is not None:
                        fwd = min(fwd, p_series.index.searchsorted(end_dt))
                    if fwd >= len(p_series) or fwd <= idx2:
                        continue
                    p0, p1 = p_series.iloc[idx2], p_series.iloc[fwd]
                    if p0 > 0:
                        rets.append((p1 - p0) / p0)
                if len(rets) >= MIN_DATES:
                    medians[tkr] = float(np.median(rets))

            if medians:
                vals = np.array(list(medians.values()))
                exp_v = np.exp(vals * 1.5)
                soft  = exp_v / exp_v.sum()
                new_w = dict(zip(medians.keys(), soft))
                # Cap 40%, floor 5%, renormalize
                new_w = {t: max(0.05, min(0.40, w)) for t, w in new_w.items()}
                s = sum(new_w.values())
                new_w = {t: w / s for t, w in new_w.items()}

        nav *= (1 - tc_drag(prev_w, new_w))

        period = prices.loc[trans_date:next_date]
        for i in range(1, len(period)):
            w_day = eff_w(new_w, period.index[i])
            nav  *= (1 + daily_port_ret(period, i, w_day))
            nav_out[period.index[i]] = nav

        prev_w = new_w

    return pd.Series(nav_out).sort_index()


# ── Metrics ────────────────────────────────────────────────────────────────────

def compute_metrics(nav: pd.Series, label: str) -> dict:
    nav  = nav.dropna()
    rets = nav.pct_change().dropna()
    yrs  = (nav.index[-1] - nav.index[0]).days / 365.25
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else 0.0
    vol  = rets.std() * np.sqrt(252)
    sh   = rets.mean() * 252 / vol if vol > 0 else np.nan
    peak = nav.expanding().max()
    mdd  = ((nav - peak) / peak).min()
    cal  = cagr / abs(mdd) if mdd < 0 else np.nan
    return {"label": label, "start": nav.index[0].date(), "end": nav.index[-1].date(),
            "cagr": cagr, "vol": vol, "sharpe": sh, "max_dd": mdd, "calmar": cal}


# ── Output ─────────────────────────────────────────────────────────────────────

def print_results(nav_dict: dict[str, pd.Series]) -> None:
    mets = [compute_metrics(v, k) for k, v in nav_dict.items()]
    w = max(len(m["label"]) for m in mets) + 1

    print("\n" + "=" * 85)
    print("COMPARISON SUMMARY  (common period, 10bps TC, RF=0% Sharpe)")
    print("=" * 85)
    print(f"  {'Strategy':<{w}}  {'CAGR':>7}  {'Vol':>7}  {'Sharpe':>7}  "
          f"{'MaxDD':>8}  {'Calmar':>7}  {'Period'}")
    print("  " + "-" * 83)
    for m in mets:
        period = f"{m['start']} → {m['end']}"
        print(f"  {m['label']:<{w}}  {m['cagr']:>7.2%}  {m['vol']:>7.2%}  "
              f"{m['sharpe']:>7.3f}  {m['max_dd']:>8.2%}  {m['calmar']:>7.3f}  {period}")

    # Year-by-year
    print("\n" + "=" * 85)
    print("YEAR-BY-YEAR RETURNS")
    print("=" * 85)
    labels = list(nav_dict.keys())
    yr_ret = {k: nav.resample("YE").last().pct_change().dropna() for k, nav in nav_dict.items()}
    all_years = sorted({d.year for s in yr_ret.values() for d in s.index})
    yr_map = {k: {d.year: r for d, r in s.items()} for k, s in yr_ret.items()}

    hdr = f"  {'Year':<5}" + "".join(f"  {l:>13}" for l in labels)
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for yr in all_years:
        row = f"  {yr:<5}"
        for lbl in labels:
            r = yr_map[lbl].get(yr)
            row += f"  {r:>13.2%}" if r is not None else f"  {'n/a':>13}"
        print(row)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    data_dir = config.raw_data_dir()

    print("Building regime labels...")
    labeled_df, _ = regime_module.build(data_dir)
    labeled_df = labeled_df.loc[START_DATE:]
    print(f"  Labels: {labeled_df.index[0].date()} → {labeled_df.index[-1].date()}")

    prices = load_portfolio_prices(data_dir)

    print("Loading universe prices...")
    universe_prices = load_universe_prices(data_dir)

    # Align prices to trading days present in labeled_df
    common = labeled_df.index.intersection(prices.index)
    prices      = prices.reindex(common).ffill(limit=3)
    labeled_df  = labeled_df.reindex(common)

    print("Computing regime transitions...")
    transitions = get_transitions(labeled_df)
    print(f"  {len(transitions)} transitions  "
          f"({transitions[0][0].date()} → {transitions[-1][0].date()})")

    # Build combined price DataFrame so rotation strategies can simulate any selected asset
    univ_df = pd.DataFrame(universe_prices).reindex(common).ffill(limit=3)
    all_prices = pd.concat([prices, univ_df], axis=1)
    all_prices = all_prices.loc[:, ~all_prices.columns.duplicated()]
    print(f"  Combined price matrix: {all_prices.shape[1]} assets")

    print("\nRunning Strategy A (static)...")
    nav_a = simulate_static(prices)

    print("Running Strategy B (universe EW rotation)...")
    nav_b, log_b = simulate_rotation(all_prices, universe_prices, labeled_df, transitions)

    print("Running Strategy C (regime-tilted)...")
    nav_c = simulate_regime_tilted(prices, labeled_df, transitions, universe_prices)

    print("Running Strategy D (50% anchor + 50% rotation)...")
    nav_d, log_d = simulate_rotation(
        all_prices, universe_prices, labeled_df, transitions,
        anchor_w=ANCHOR_W, n_rot=N_ROT_D,
    )

    nav_dict: dict[str, pd.Series] = {
        "A: Static":       nav_a,
        "B: EW Rotation":  nav_b,
        "C: Regime-Tilted": nav_c,
        "D: Hybrid":       nav_d,
    }
    if "SPY" in prices.columns:
        spy = prices["SPY"].dropna()
        nav_dict["SPY"] = spy / spy.iloc[0]

    # Align to common start (latest first date across all strategies)
    common_start = max(v.dropna().index[0] for v in nav_dict.values())
    nav_dict = {
        k: v[v.index >= common_start] / v[v.index >= common_start].iloc[0]
        for k, v in nav_dict.items()
    }

    print_results(nav_dict)

    # Save outputs
    out = PROJECT_ROOT / "comparison_results"
    out.mkdir(exist_ok=True)
    pd.DataFrame(nav_dict).to_csv(out / "comparison_equity_curves.csv")
    pd.DataFrame(log_b).to_csv(out / "rotation_b_selections.csv", index=False)
    pd.DataFrame(log_d).to_csv(out / "rotation_d_selections.csv", index=False)

    print(f"\nSaved to {out}/")
    print("  comparison_equity_curves.csv")
    print("  rotation_b_selections.csv   (which assets Strategy B held per period)")
    print("  rotation_d_selections.csv   (which assets Strategy D rotation held)")
    print("\n" + "=" * 85)


if __name__ == "__main__":
    main()
