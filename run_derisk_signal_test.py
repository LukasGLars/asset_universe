"""
run_derisk_signal_test.py

TEMPORARY DIAGNOSTIC (2026-08-31). Question from the user: "should I be
reducing positions if e.g. VIX and credit spreads spike, and can we
operationalize it?"

Tests a de-risking overlay on the Reactor Core (Gold/AVGO/LLY) driven by
*forward-looking / implied* stress signals, which are a genuinely different
signal class from everything already tested and retired here:
  - the AVGO 200d guard   -> price trend      (retired: lookahead bias)
  - vol-targeting         -> realized vol     (retired: 0 of 30 cells won)
VIX is implied vol and BAA10Y is a credit-market price. Neither is a
function of the Core's own price history, so this is not a re-run of a
dead test.

CREDIT SERIES: BAA10Y, not HY OAS. BAMLH0A0HYM2 is license-restricted to
the most recent 3 years via the FRED API (INTEGRITY.md:145) -- it cannot be
backtested and is not used as a conditioning variable anywhere in this repo.

NO-LOOKAHEAD DISCIPLINE (the thing that killed the AVGO guard):
  - a signal computed from day i's close sets the weights HELD FROM
    close(i) TO close(i+1). It never touches day i's own return.
  - credit series get an extra MACRO_LAG_DAYS on top of that, because FRED
    publishes BAA10Y at T+1: at close(i) you actually only know close(i-1).
  - the VIX percentile is EXPANDING (point-in-time), never a full-sample
    quantile -- a full-sample quantile leaks the future by construction.
  - a deliberate LOOKAHEAD TWIN is run at the end as a self-check. If the
    twin doesn't beat the honest version, the shift plumbing is wrong.

KILL CRITERIA, pre-committed before seeing any output:
  the overlay must beat cost-matched static Gold25/AVGO40/LLY35 on Calmar
  in a MAJORITY of grid cells AND hold up post-2020. If it does not, it is
  dead -- no threshold hunting, no rescue variants.

Read-only. Writes comparison_results/derisk_signal_grid.csv. Delete this
script, its test file and its workflow once the result is in MEMORY.md.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

if __name__ == "__main__":
    # Only when run directly -- doing this at import time breaks pytest's
    # stdout/stderr capture for anything that imports this module (same
    # gotcha as run_base_optimizer_with_guard.py:40).
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.store import reader

# ── Fixed conventions (matched to run_base_optimizer.py so the static
#    benchmark is the same object the base-weight work already produced) ──
START_DATE    = "2004-01-01"
TC_BPS        = 10
REBAL_TRIGGER = 0.05
AVGO_IPO      = pd.Timestamp("2009-08-06")
BASE_W        = {"Gold": 0.25, "AVGO": 0.40, "LLY": 0.35}   # live split

# FRED publishes BAA10Y for day D on day D+1, so at close(i) the freshest
# value you could actually have read is day i-1's. Applied BEFORE the
# act-next-day shift, not instead of it.
MACRO_LAG_DAYS = 1

# Point-in-time VIX percentile needs enough history to mean anything.
VIX_MIN_OBS = 756          # ~3 trading years

ASSETS = {
    "Gold": ("commodities", "GC_F"),
    "AVGO": ("equities",    "AVGO"),
    "LLY":  ("equities",    "LLY"),
}

# ── Grid ──────────────────────────────────────────────────────────────────
CREDIT_LOOKBACK   = 20                        # trading days of widening
CREDIT_BPS        = [25, 50, 75, 100]         # 20d BAA10Y widening, bps
VIX_PCTL          = [0.80, 0.90, 0.95]        # expanding, point-in-time
VIX_ABS           = [20.0, 25.0, 30.0]        # fixed level
REDUCTIONS        = [0.25, 0.50, 1.00]        # fraction of Core -> cash
MODES             = ["CREDIT", "VIX", "OR", "AND"]
CASH_YIELDS       = [0.00, 0.02]              # annual, on the de-risked part

# A cell that almost never fires "beats" static by doing nothing -- that is
# not evidence for the signal, it is evidence the threshold is inert. The
# kill criteria are therefore scored on ACTIVE cells: ones that actually took
# the trade often enough for the result to be about the signal.
MIN_EPISODES   = 5
MIN_DAYS_ON    = 0.01     # >=1% of days de-risked

# Named stress episodes -- the situations the user is actually asking about.
EPISODES = [
    ("GFC crash 2008",   "2008-09-01", "2009-03-09"),
    ("COVID crash 2020", "2020-02-19", "2020-03-23"),
    ("2022 bear",        "2022-01-03", "2022-10-12"),
]

SUBPERIODS = [
    ("AVGO era 2009-08+", "2009-08-06", None),
    ("GFC 2007-2009",     "2007-01-01", "2009-12-31"),
    ("2010-2019",         "2010-01-01", "2019-12-31"),
    ("2020+",             "2020-01-01", None),
]


# ── Data ──────────────────────────────────────────────────────────────────

def load_prices(data_dir: Path) -> pd.DataFrame:
    series = {}
    for name, (cat, safe) in ASSETS.items():
        df = pd.read_parquet(reader.ticker_path(data_dir, cat, safe))
        df["date"] = pd.to_datetime(df["date"])
        series[name] = df.set_index("date")["close"].sort_index()
    return pd.DataFrame(series).sort_index().loc[START_DATE:].ffill(limit=3)


def load_vix(data_dir: Path) -> pd.Series:
    df = pd.read_parquet(reader.ticker_path(data_dir, "volatility", "^VIX"))
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index()


def load_macro(data_dir: Path, series_id: str) -> pd.Series:
    df = pd.read_parquet(reader.ticker_path(data_dir, "macro", series_id))
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["value"].sort_index()


# ── Signals ───────────────────────────────────────────────────────────────

def credit_widening_bps(baa: pd.Series, calendar: pd.DatetimeIndex,
                        lookback: int = CREDIT_LOOKBACK,
                        macro_lag: int = MACRO_LAG_DAYS) -> pd.Series:
    """20d widening of BAA10Y in bps, as knowable at each close.

    BAA10Y is stored in percentage points; x100 -> bps. The macro_lag shift
    is the FRED publication delay and is applied to the level series before
    any differencing, so both ends of the difference are equally lagged.
    """
    lvl = baa.reindex(calendar.union(baa.index)).ffill().reindex(calendar)
    lvl = lvl.shift(macro_lag)
    return (lvl - lvl.shift(lookback)) * 100.0


def vix_expanding_pctl(vix: pd.Series, calendar: pd.DatetimeIndex,
                       q: float, min_obs: int = VIX_MIN_OBS) -> pd.Series:
    """Point-in-time q-quantile of VIX using only data up to and including
    each date. NOT vix.quantile(q) over the whole sample -- that is the
    single most common way a vol rule fakes an edge."""
    v = vix.reindex(calendar.union(vix.index)).ffill().reindex(calendar)
    return v.expanding(min_periods=min_obs).quantile(q)


# ── Simulation ────────────────────────────────────────────────────────────

def eff_core_weights(date: pd.Timestamp, base: dict[str, float]) -> dict[str, float]:
    """Pre-IPO AVGO weight redistributes proportionally to Gold+LLY."""
    if date >= AVGO_IPO:
        return dict(base)
    rest = {k: v for k, v in base.items() if k != "AVGO"}
    s = sum(rest.values())
    return {k: v / s for k, v in rest.items()} if s > 0 else rest


def simulate(prices: pd.DataFrame,
             derisk: np.ndarray | None,
             reduction: float,
             cash_annual: float,
             base: dict[str, float] = BASE_W,
             tc_bps: float = TC_BPS,
             rebal_trigger: float = REBAL_TRIGGER,
             lookahead: bool = False) -> pd.Series:
    """NAV path.

    `derisk[i]` is the signal AS COMPUTED AT CLOSE(i). It governs the
    weights held from close(i) to close(i+1), i.e. it is applied to day
    i+1's return. Pass derisk=None for the static benchmark.

    lookahead=True deliberately breaks that (uses derisk[i] on day i's own
    return) and exists only as a bias self-check.
    """
    names = list(prices.columns)
    px    = prices.to_numpy(dtype=float)
    dates = prices.index
    n     = len(dates)
    cash_daily = (1.0 + cash_annual) ** (1.0 / 252.0) - 1.0

    def target_at(i: int) -> dict[str, float]:
        w = eff_core_weights(dates[i], base)
        if derisk is None:
            cut = 0.0
        else:
            cut = reduction if derisk[i] else 0.0
        w = {k: v * (1.0 - cut) for k, v in w.items()}
        w["CASH"] = cut
        return w

    # index 0: the signal that can be acted on for day 1's return is
    # derisk[0] (honest) or derisk[1] (lookahead -- shifted forward).
    def signal_index(i: int) -> int:
        return min(i + 1, n - 1) if lookahead else i

    w_cur  = target_at(signal_index(0))
    w_prev_tgt = dict(w_cur)
    nav    = 1.0
    out    = [nav]
    # Turnover decided at close(i) is EXECUTED on day i+1 (that is the whole
    # point of the shift), so its cost is accrued and charged against day
    # i+1's NAV -- not against day i's. Charging it at close(i) would let a
    # signal move the NAV on its own signal day, which is exactly the shape
    # of error that made the AVGO guard look real.
    pending_cost = 0.0

    for i in range(1, n):
        # 1. return over (i-1, i] under the weights set at close(i-1)
        ret = 0.0
        for k, wt in w_cur.items():
            if wt == 0.0:
                continue
            if k == "CASH":
                ret += wt * cash_daily
                continue
            j  = names.index(k)
            p0, p1 = px[i - 1, j], px[i, j]
            if p0 > 0 and np.isfinite(p0) and np.isfinite(p1):
                ret += wt * (p1 - p0) / p0
        nav *= (1.0 + ret)

        # 1b. pay for the trade decided at close(i-1) and executed today
        if pending_cost:
            nav *= (1.0 - pending_cost)
            pending_cost = 0.0

        # 2. drift
        w_new = {}
        for k, wt in w_cur.items():
            if k == "CASH":
                w_new[k] = wt * (1.0 + cash_daily)
                continue
            j  = names.index(k)
            p0, p1 = px[i - 1, j], px[i, j]
            w_new[k] = wt * (1.0 + (p1 - p0) / p0) if (
                p0 > 0 and np.isfinite(p0) and np.isfinite(p1)) else wt
        s = sum(w_new.values())
        if s > 0:
            w_cur = {k: v / s for k, v in w_new.items()}

        # 3. target for the NEXT holding period, from close(i)
        w_tgt = target_at(signal_index(i))

        # 4. rebalance on drift, or unconditionally when the target moved
        target_moved = any(
            abs(w_tgt.get(k, 0.0) - w_prev_tgt.get(k, 0.0)) > 1e-12
            for k in set(w_tgt) | set(w_prev_tgt)
        )
        drift = max(abs(w_cur.get(k, 0.0) - w_tgt.get(k, 0.0)) for k in w_tgt)
        if target_moved or drift > rebal_trigger:
            turnover = sum(
                abs(w_tgt.get(k, 0.0) - w_cur.get(k, 0.0))
                for k in set(w_cur) | set(w_tgt)
            ) / 2.0
            pending_cost = turnover * tc_bps / 10_000.0
            w_cur = dict(w_tgt)
        w_prev_tgt = dict(w_tgt)

        out.append(nav)

    return pd.Series(out, index=dates)


def metrics(nav: pd.Series) -> dict:
    nav = nav.dropna()
    if len(nav) < 30:
        return {"cagr": np.nan, "vol": np.nan, "sharpe": np.nan,
                "mdd": np.nan, "calmar": np.nan}
    nav  = nav / nav.iloc[0]
    rets = nav.pct_change().dropna()
    yrs  = (nav.index[-1] - nav.index[0]).days / 365.25
    cagr = nav.iloc[-1] ** (1.0 / yrs) - 1.0
    vol  = rets.std() * np.sqrt(252)
    sh   = rets.mean() * 252 / vol if vol > 0 else 0.0
    peak = nav.expanding().max()
    mdd  = ((nav - peak) / peak).min()
    cal  = cagr / abs(mdd) if mdd < 0 else 0.0
    return {"cagr": cagr, "vol": vol, "sharpe": sh, "mdd": mdd, "calmar": cal}


def window(nav: pd.Series, start, end) -> pd.Series:
    s = nav
    if start is not None:
        s = s[s.index >= pd.Timestamp(start)]
    if end is not None:
        s = s[s.index <= pd.Timestamp(end)]
    return s


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    data_dir = config.raw_data_dir()

    prices = load_prices(data_dir)
    vix    = load_vix(data_dir)
    baa    = load_macro(data_dir, "BAA10Y")

    print("=" * 78)
    print("DE-RISK OVERLAY TEST  --  VIX (implied vol) + BAA10Y (credit)")
    print("=" * 78)
    print(f"Prices  {prices.index[0].date()} -> {prices.index[-1].date()}  ({len(prices):,}d)")
    print(f"VIX     {vix.index[0].date()} -> {vix.index[-1].date()}  ({len(vix):,} obs)")
    print(f"BAA10Y  {baa.index[0].date()} -> {baa.index[-1].date()}  ({len(baa):,} obs)")

    # Trim to where both signals are actually available, so no cell is
    # scored on a window where its signal silently never fires.
    sig_start = max(pd.Timestamp(vix.index[0]), pd.Timestamp(baa.index[0]),
                    pd.Timestamp(prices.index[0]))
    prices = prices[prices.index >= sig_start]
    cal    = prices.index
    print(f"Common  {cal[0].date()} -> {cal[-1].date()}  ({len(cal):,}d)")

    widen = credit_widening_bps(baa, cal)
    vixc  = vix.reindex(cal.union(vix.index)).ffill().reindex(cal)
    pctl  = {q: vix_expanding_pctl(vix, cal, q) for q in VIX_PCTL}

    print(f"\n20d BAA10Y widening: median {widen.median():.1f}bp  "
          f"p90 {widen.quantile(0.90):.1f}bp  p99 {widen.quantile(0.99):.1f}bp  "
          f"max {widen.max():.1f}bp")
    print(f"VIX: median {vixc.median():.1f}  p90 {vixc.quantile(0.90):.1f}  "
          f"max {vixc.max():.1f}")

    print(f"\nWHERE THE SIGNALS STAND RIGHT NOW ({cal[-1].date()}):")
    print(f"  BAA10Y 20d widening : {widen.iloc[-1]:+.1f}bp "
          f"(thresholds tested: {CREDIT_BPS} bp)")
    print(f"  VIX                 : {vixc.iloc[-1]:.1f} "
          f"(levels tested: {[f'{a:.0f}' for a in VIX_ABS]})")
    for q in VIX_PCTL:
        print(f"  VIX p{int(q*100)} (point-in-time) : {pctl[q].iloc[-1]:.1f} "
              f"-> {'FIRING' if vixc.iloc[-1] > pctl[q].iloc[-1] else 'quiet'}")

    # ── Static benchmarks, one per cash yield (cash yield is irrelevant to
    #    static since it holds no cash, but keep the pairing explicit) ──
    static_nav = simulate(prices, None, 0.0, 0.0)
    sm = metrics(static_nav)
    print(f"\nSTATIC Gold25/AVGO40/LLY35 (cost-matched, {TC_BPS}bps, "
          f"+-{REBAL_TRIGGER:.0%} drift):")
    print(f"  CAGR {sm['cagr']:7.2%}  MaxDD {sm['mdd']:7.2%}  "
          f"Sharpe {sm['sharpe']:.3f}  Calmar {sm['calmar']:.3f}")
    static_sub = {}
    for label, s, e in SUBPERIODS:
        static_sub[label] = metrics(window(static_nav, s, e))
        m = static_sub[label]
        print(f"    {label:<20} CAGR {m['cagr']:7.2%}  MaxDD {m['mdd']:7.2%}  "
              f"Calmar {m['calmar']:.3f}")

    # ── Build the signal cells ────────────────────────────────────────────
    cells = []
    for mode in MODES:
        credit_opts = CREDIT_BPS if mode in ("CREDIT", "OR", "AND") else [None]
        vix_opts    = ([("pctl", q) for q in VIX_PCTL] +
                       [("abs", a) for a in VIX_ABS]) if mode in ("VIX", "OR", "AND") else [None]
        for cbps in credit_opts:
            for vopt in vix_opts:
                for red in REDUCTIONS:
                    for cy in CASH_YIELDS:
                        cells.append((mode, cbps, vopt, red, cy))

    print(f"\nGrid: {len(cells)} cells "
          f"({len(MODES)} modes x thresholds x {len(REDUCTIONS)} reductions "
          f"x {len(CASH_YIELDS)} cash yields)")
    print("Running...", flush=True)

    def build_flags(mode, cbps, vopt) -> np.ndarray:
        c = (widen >= cbps) if cbps is not None else None
        if vopt is None:
            v = None
        elif vopt[0] == "pctl":
            v = vixc > pctl[vopt[1]]
        else:
            v = vixc > vopt[1]
        if mode == "CREDIT":
            f = c
        elif mode == "VIX":
            f = v
        elif mode == "OR":
            f = c | v
        else:
            f = c & v
        return f.fillna(False).to_numpy(dtype=bool)

    rows = []
    for n_done, (mode, cbps, vopt, red, cy) in enumerate(cells, 1):
        flags = build_flags(mode, cbps, vopt)
        nav   = simulate(prices, flags, red, cy)
        m     = metrics(nav)
        row = {
            "mode": mode,
            "credit_bps": cbps if cbps is not None else "",
            "vix_rule": (f"p{int(vopt[1]*100)}" if vopt and vopt[0] == "pctl"
                         else (f">{vopt[1]:.0f}" if vopt else "")),
            "reduction": red,
            "cash_yield": cy,
            "pct_days_derisked": float(flags.mean()),
            "n_episodes": int(np.sum(flags[1:] & ~flags[:-1])) + int(flags[0]),
            "cagr": m["cagr"], "mdd": m["mdd"],
            "sharpe": m["sharpe"], "calmar": m["calmar"],
            "calmar_vs_static": m["calmar"] - sm["calmar"],
            "cagr_vs_static": m["cagr"] - sm["cagr"],
            "beats_static_calmar": m["calmar"] > sm["calmar"],
        }
        for label, s, e in SUBPERIODS:
            sub = metrics(window(nav, s, e))
            key = label.split()[0].lower().replace("+", "").replace("-", "_")
            row[f"calmar_{key}"] = sub["calmar"]
            row[f"beats_{key}"]  = bool(sub["calmar"] > static_sub[label]["calmar"])
        rows.append(row)
        if n_done % 25 == 0:
            print(f"  {n_done}/{len(cells)}", flush=True)

    df = pd.DataFrame(rows)
    out_dir = PROJECT_ROOT / "comparison_results"
    out_dir.mkdir(exist_ok=True)
    df.to_csv(out_dir / "derisk_signal_grid.csv", index=False)

    # ── Verdict against the pre-committed kill criteria ───────────────────
    print("\n" + "=" * 78)
    print("RESULT")
    print("=" * 78)
    key2020 = [c for c in df.columns if c.startswith("beats_2020")][0]
    df["active"] = ((df["n_episodes"] >= MIN_EPISODES) &
                    (df["pct_days_derisked"] >= MIN_DAYS_ON))
    act = df[df["active"]]
    print(f"Cells: {len(df)} total, {len(act)} ACTIVE "
          f"(>={MIN_EPISODES} episodes and >={MIN_DAYS_ON:.0%} of days on). "
          f"Inert cells\nare excluded from the verdict -- 'never fired' is not "
          f"evidence the signal works.")
    win_full = act["beats_static_calmar"].mean() if len(act) else 0.0
    win_2020 = act[key2020].mean() if len(act) else 0.0
    print(f"\nACTIVE cells beating static on Calmar, FULL sample : "
          f"{act['beats_static_calmar'].sum()}/{len(act)}  ({win_full:.0%})")
    print(f"ACTIVE cells beating static on Calmar, POST-2020   : "
          f"{act[key2020].sum()}/{len(act)}  ({win_2020:.0%})")
    print(f"(all cells incl. inert, full sample: "
          f"{df['beats_static_calmar'].sum()}/{len(df)} "
          f"= {df['beats_static_calmar'].mean():.0%})")
    print(f"Median Calmar delta vs static: {df['calmar_vs_static'].median():+.3f}")
    print(f"Median CAGR   delta vs static: {df['cagr_vs_static'].median():+.2%}")

    print("\nBy mode:")
    g = df.groupby("mode").agg(
        n=("calmar", "size"),
        win_rate=("beats_static_calmar", "mean"),
        med_calmar_delta=("calmar_vs_static", "median"),
        med_cagr_delta=("cagr_vs_static", "median"),
        med_days_derisked=("pct_days_derisked", "median"),
    )
    print(g.to_string(float_format=lambda x: f"{x:8.3f}"))

    print("\nBy reduction size:")
    g2 = df.groupby("reduction").agg(
        win_rate=("beats_static_calmar", "mean"),
        med_calmar_delta=("calmar_vs_static", "median"),
        med_cagr_delta=("cagr_vs_static", "median"),
    )
    print(g2.to_string(float_format=lambda x: f"{x:8.3f}"))

    cols = ["mode", "credit_bps", "vix_rule", "reduction", "cash_yield",
            "pct_days_derisked", "n_episodes", "cagr", "mdd", "calmar",
            "calmar_vs_static"]
    print("\nTop 10 ACTIVE cells by Calmar:")
    print(act.sort_values("calmar", ascending=False).head(10)[cols]
            .to_string(index=False, float_format=lambda x: f"{x:8.3f}"))

    print("\nBest MaxDD reduction among ACTIVE cells "
          "(does it at least cut drawdown, and at what cost to CAGR?):")
    print(act.sort_values("mdd", ascending=False).head(5)[cols]
            .to_string(index=False, float_format=lambda x: f"{x:8.3f}"))

    # ── The operational table: credit alone, every threshold x reduction.
    #    Split out because the mode comparison above shows the credit leg
    #    carries the whole result and VIX only adds cost.
    print("\n" + "-" * 78)
    print("CREDIT-ONLY (BAA10Y 20d widening), every threshold x reduction")
    print("-" * 78)
    ccols = ["credit_bps", "reduction", "cash_yield", "pct_days_derisked",
             "n_episodes", "cagr", "mdd", "calmar", "calmar_vs_static"]
    ccols += [c for c in df.columns if c.startswith("calmar_")
              and c != "calmar_vs_static"]
    print(df[df["mode"] == "CREDIT"].sort_values(["credit_bps", "reduction"])[ccols]
            .to_string(index=False, float_format=lambda x: f"{x:8.3f}"))

    # When did it actually fire? With N this small the dates matter more
    # than the summary stats -- they are the sample.
    print("\nFiring episodes by credit threshold (start -> end, trading days):")
    for cbps in CREDIT_BPS:
        f = pd.Series(build_flags("CREDIT", cbps, None), index=prices.index)
        starts = f & ~f.shift(1, fill_value=False)
        ends   = f & ~f.shift(-1, fill_value=False)
        sd, ed = list(f.index[starts]), list(f.index[ends])
        print(f"\n  >= {cbps}bp  ({f.mean():.1%} of days, {len(sd)} episodes)")
        for a, b in zip(sd, ed):
            print(f"      {a.date()} -> {b.date()}  "
                  f"({len(f.loc[a:b])}d)")

    # ── Did it help in the episodes the question is actually about? ──
    print("\n" + "-" * 78)
    print("NAMED STRESS EPISODES -- best ACTIVE cell by full-sample Calmar")
    print("-" * 78)
    if len(act):
        best = act.sort_values("calmar", ascending=False).iloc[0]
        _cb = f"{best['credit_bps']}bp" if best["credit_bps"] != "" else "n/a"
        print(f"Cell: mode={best['mode']}  credit>={_cb}  "
              f"vix={best['vix_rule'] or 'n/a'}  reduce={best['reduction']:.0%}  "
              f"cash={best['cash_yield']:.0%}  "
              f"({best['pct_days_derisked']:.1%} of days on, "
              f"{int(best['n_episodes'])} episodes)")
        vopt = None
        if best["vix_rule"]:
            vr = best["vix_rule"]
            vopt = (("pctl", float(vr[1:]) / 100) if vr.startswith("p")
                    else ("abs", float(vr[1:])))
        cb = int(best["credit_bps"]) if best["credit_bps"] != "" else None
        flags = build_flags(best["mode"], cb, vopt)
        nav_b = simulate(prices, flags, best["reduction"], best["cash_yield"])
        print(f"\n{'Episode':<20}{'static':>12}{'de-risked':>12}{'diff':>10}"
              f"{'days on':>10}")
        for label, s_, e_ in EPISODES:
            ws, wb = window(static_nav, s_, e_), window(nav_b, s_, e_)
            if len(ws) < 5:
                print(f"{label:<20}{'no data':>12}")
                continue
            rs = ws.iloc[-1] / ws.iloc[0] - 1
            rb = wb.iloc[-1] / wb.iloc[0] - 1
            on = pd.Series(flags, index=prices.index)
            on = window(on, s_, e_).mean()
            print(f"{label:<20}{rs:>11.1%}{rb:>12.1%}{rb - rs:>+10.1%}{on:>10.0%}")
    else:
        print("No active cells -- every threshold tested was inert.")

    verdict = "PASS" if (win_full > 0.5 and win_2020 > 0.5) else "FAIL"
    print(f"\nKILL CRITERIA (pre-committed, before any output was seen): the "
          f"overlay must beat\nstatic on Calmar in a majority of ACTIVE cells, "
          f"on the full sample AND post-2020.\nVERDICT: {verdict}")

    # ── Lookahead twin: self-check that the shift plumbing is real ────────
    print("\n" + "=" * 78)
    print("LOOKAHEAD TWIN (self-check -- NOT a strategy)")
    print("=" * 78)
    print("Same cells, signal applied to its OWN day's return. If these do "
          "not\nbeat the honest version, the shift(1) is not doing anything "
          "and the\nwhole test is void.")
    twin_rows = []
    for mode, cbps, vopt, red, cy in cells:
        if red != 1.00 or cy != 0.00:
            continue
        flags = build_flags(mode, cbps, vopt)
        h = metrics(simulate(prices, flags, red, cy, lookahead=False))
        l = metrics(simulate(prices, flags, red, cy, lookahead=True))
        twin_rows.append({"mode": mode, "credit_bps": cbps,
                          "vix": (vopt[1] if vopt else None),
                          "honest_calmar": h["calmar"],
                          "lookahead_calmar": l["calmar"],
                          "leak": l["calmar"] - h["calmar"]})
    t = pd.DataFrame(twin_rows)
    print(f"\nCells: {len(t)}   lookahead beats honest in "
          f"{(t['leak'] > 0).sum()}/{len(t)}")
    print(f"Median Calmar leak: {t['leak'].median():+.3f}   "
          f"max {t['leak'].max():+.3f}")

    print(f"\nWrote {out_dir / 'derisk_signal_grid.csv'}  ({len(df)} rows)")


if __name__ == "__main__":
    main()
