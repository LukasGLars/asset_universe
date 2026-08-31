"""
run_drawdown_control.py

TEMPORARY DIAGNOSTIC (2026-08-31). User: "figure out a confident strategy
to avoid drawdowns."

The honest framing, which this script is built to test rather than assert:
three TIMING overlays have now been tried and none survived --
  AVGO 200d guard  -> retired, lookahead bias
  vol-targeting    -> retired, beat static in 0 of 30 cells
  VIX/credit spike -> passed its kill criteria today, but on 2 crashes
                      (Oct-2008 / Mar-2020); Calmar rose as sample size
                      collapsed, the classic overfit signature
So this asks the STRUCTURAL question instead: how far can drawdown be cut
by allocation alone -- which requires no forecast, no signal, and cannot
be overfit to a handful of crash dates.

Two levers, tested jointly:
  1. Core weight mix (Gold/AVGO/LLY, 5% steps, the same 231-combo grid
     already in comparison_results/base_optimizer_grid.csv)
  2. Reactor Core vs Home Base bucket split (live: 85/15)

Home Base is modelled two ways because the answer should not rest on an
assumption: SHY (1-3yr Treasuries, real data, closest listed proxy to
Spiltan Rantefond's short duration) and a flat 2%/yr cash rate. Spiltan is
short CORPORATE credit, so SHY understates its 2020-style credit shock --
flagged, not hidden.

Conventions match run_base_optimizer.py exactly (2004-01-01, 10bps, +-5pp
drift, AVGO pre-IPO redistribution) so numbers are comparable to the grid
already committed to the repo. Two-level rebalancing: the Core rebalances
internally, and the bucket split rebalances against it -- which is how the
live portfolio actually works.

Read-only. Delete script, tests and workflow once logged to MEMORY.md.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

if __name__ == "__main__":
    # Import-time stdout wrapping breaks pytest capture (same gotcha as
    # run_base_optimizer_with_guard.py:40).
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_universe import config
from asset_universe.store import reader

START_DATE    = "2004-01-01"
TC_BPS        = 10
REBAL_TRIGGER = 0.05
AVGO_IPO      = pd.Timestamp("2009-08-06")

LIVE_CORE_W   = {"Gold": 0.25, "AVGO": 0.40, "LLY": 0.35}
LIVE_CORE_FRAC = 0.85
PREV_CORE_W   = {"Gold": 0.25, "AVGO": 0.55, "LLY": 0.20}   # pre 2026-08-16

DD_TOLERANCE  = -0.25        # the operator's stated total-portfolio ceiling

CORE_FRACTIONS = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]
STEP           = 5           # weight grid step, %

ASSETS = {
    "Gold": ("commodities", "GC_F"),
    "AVGO": ("equities",    "AVGO"),
    "LLY":  ("equities",    "LLY"),
}
HOME_BASE_PROXY = ("fixed_income", "SHY")
CASH_ANNUAL     = 0.02

# FI@50 projection inputs (config/portfolio.toml)
TPV_NOW          = 1_150_000
MONTHLY_CONTRIB  = 6_000
YEARS_LEFT       = 12.11     # 2026-08-31 -> 2038-10-10
TARGET_REAL      = 16_150_000
TARGET_INFLATION = 0.02
TARGET_BASE_YEAR = 2026
HORIZON_YEAR     = 2038


# ── Data ──────────────────────────────────────────────────────────────────

def load_series(data_dir: Path, cat: str, safe: str) -> pd.Series:
    df = pd.read_parquet(reader.ticker_path(data_dir, cat, safe))
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].sort_index()


def load_prices(data_dir: Path) -> pd.DataFrame:
    s = {n: load_series(data_dir, c, t) for n, (c, t) in ASSETS.items()}
    return pd.DataFrame(s).sort_index().loc[START_DATE:].ffill(limit=3)


# ── Core simulation (identical convention to run_base_optimizer.py) ───────

def eff_weights(w: dict[str, float], date: pd.Timestamp) -> dict[str, float]:
    if date >= AVGO_IPO:
        return w
    rest = {k: v for k, v in w.items() if k != "AVGO"}
    s = sum(rest.values())
    return {k: v / s for k, v in rest.items()} if s > 0 else rest


def simulate_core(prices: pd.DataFrame, target_w: dict[str, float]) -> pd.Series:
    names = list(prices.columns)
    px    = prices.to_numpy(dtype=float)
    dates = prices.index
    nav, out, w_cur = 1.0, [1.0], {}

    for i, date in enumerate(dates):
        w_tgt = eff_weights(target_w, date)
        if not w_cur:
            w_cur = dict(w_tgt)
            continue

        ret = 0.0
        for k, wt in w_cur.items():
            j = names.index(k)
            p0, p1 = px[i - 1, j], px[i, j]
            if p0 > 0 and np.isfinite(p0) and np.isfinite(p1):
                ret += wt * (p1 - p0) / p0
        nav *= (1.0 + ret)

        w_new = {}
        for k, wt in w_cur.items():
            j = names.index(k)
            p0, p1 = px[i - 1, j], px[i, j]
            w_new[k] = wt * (1.0 + (p1 - p0) / p0) if (
                p0 > 0 and np.isfinite(p0) and np.isfinite(p1)) else wt
        s = sum(w_new.values())
        if s > 0:
            w_cur = {k: v / s for k, v in w_new.items()}

        drift = max(abs(w_cur.get(t, 0.0) - w_tgt.get(t, 0.0)) for t in w_tgt)
        if drift > REBAL_TRIGGER:
            turn = sum(abs(w_tgt.get(t, 0.0) - w_cur.get(t, 0.0))
                       for t in set(w_cur) | set(w_tgt)) / 2.0
            nav *= (1.0 - turn * TC_BPS / 10_000.0)
            w_cur = dict(w_tgt)
        out.append(nav)

    return pd.Series(out[:len(dates)], index=dates)


def blend(core_nav: pd.Series, hb_nav: pd.Series, core_frac: float,
          tc_bps: float = TC_BPS,
          rebal_trigger: float = REBAL_TRIGGER) -> pd.Series:
    """Two-level: blend two NAV paths at a target bucket split, rebalancing
    the split back on +-5pp drift. core_frac=1.0 returns the core path."""
    if core_frac >= 1.0:
        return core_nav.copy()
    cr = core_nav.pct_change().fillna(0.0).to_numpy()
    hr = hb_nav.pct_change().fillna(0.0).to_numpy()
    nav, wc = 1.0, core_frac
    out = [nav]
    for i in range(1, len(cr)):
        r = wc * cr[i] + (1.0 - wc) * hr[i]
        nav *= (1.0 + r)
        # drift the split
        c_new = wc * (1.0 + cr[i])
        h_new = (1.0 - wc) * (1.0 + hr[i])
        tot = c_new + h_new
        wc = c_new / tot if tot > 0 else wc
        if abs(wc - core_frac) > rebal_trigger:
            nav *= (1.0 - abs(wc - core_frac) * tc_bps / 10_000.0)
            wc = core_frac
        out.append(nav)
    return pd.Series(out, index=core_nav.index)


def metrics(nav: pd.Series) -> dict:
    nav = nav.dropna()
    nav = nav / nav.iloc[0]
    rets = nav.pct_change().dropna()
    yrs = (nav.index[-1] - nav.index[0]).days / 365.25
    cagr = nav.iloc[-1] ** (1.0 / yrs) - 1.0
    vol = rets.std() * np.sqrt(252)
    peak = nav.expanding().max()
    mdd = ((nav - peak) / peak).min()
    return {"cagr": cagr, "vol": vol,
            "sharpe": rets.mean() * 252 / vol if vol > 0 else 0.0,
            "mdd": mdd, "calmar": cagr / abs(mdd) if mdd < 0 else 0.0}


def fv_with_contributions(pv: float, annual_return: float, years: float,
                          monthly: float) -> float:
    """Future value of pv plus a monthly contribution stream."""
    n = int(round(years * 12))
    r = (1.0 + annual_return) ** (1.0 / 12.0) - 1.0
    fv = pv * (1.0 + r) ** n
    fv += monthly * (((1.0 + r) ** n - 1.0) / r) if r != 0 else monthly * n
    return fv


def main() -> None:
    data_dir = config.raw_data_dir()
    prices = load_prices(data_dir)
    shy = load_series(data_dir, *HOME_BASE_PROXY).reindex(prices.index).ffill()

    print("=" * 78)
    print("DRAWDOWN CONTROL BY ALLOCATION  (no signal, no forecast)")
    print("=" * 78)
    print(f"Window {prices.index[0].date()} -> {prices.index[-1].date()} "
          f"({len(prices):,}d)")

    # Home Base, two models
    hb_shy  = shy / shy.iloc[0]
    daily_c = (1 + CASH_ANNUAL) ** (1 / 252) - 1
    hb_cash = pd.Series((1 + daily_c) ** np.arange(len(prices)), index=prices.index)
    m_shy = metrics(hb_shy)
    print(f"\nHome Base proxies:")
    print(f"  SHY (1-3y UST, real)  CAGR {m_shy['cagr']:6.2%}  "
          f"MaxDD {m_shy['mdd']:7.2%}  vol {m_shy['vol']:5.2%}")
    print(f"  Flat cash             CAGR {CASH_ANNUAL:6.2%}  MaxDD   0.00%")
    print("  NOTE: Spiltan Rantefond is short CORPORATE credit. SHY is govvies,")
    print("        so both proxies UNDERSTATE Home Base's own 2020-style shock.")

    # ── Core grid ─────────────────────────────────────────────────────────
    combos = [(g, a, 100 - g - a)
              for g in range(0, 101, STEP)
              for a in range(0, 101 - g, STEP)]
    print(f"\nSimulating {len(combos)} core weight combos "
          f"x {len(CORE_FRACTIONS)} bucket splits "
          f"x 2 Home Base models = {len(combos)*len(CORE_FRACTIONS)*2:,} portfolios")

    core_navs = {}
    for n, (g, a, l) in enumerate(combos, 1):
        w = {"Gold": g / 100, "AVGO": a / 100, "LLY": l / 100}
        core_navs[(g, a, l)] = simulate_core(prices, w)
        if n % 50 == 0:
            print(f"  core {n}/{len(combos)}", flush=True)

    rows = []
    for (g, a, l), cn in core_navs.items():
        cm = metrics(cn)
        for cf in CORE_FRACTIONS:
            for hb_name, hb in (("SHY", hb_shy), ("cash2pct", hb_cash)):
                m = metrics(blend(cn, hb, cf))
                rows.append({
                    "gold": g, "avgo": a, "lly": l,
                    "label": f"Gold{g}/AVGO{a}/LLY{l}",
                    "core_frac": cf, "home_base": hb_name,
                    "core_cagr": cm["cagr"], "core_mdd": cm["mdd"],
                    "cagr": m["cagr"], "mdd": m["mdd"],
                    "calmar": m["calmar"], "sharpe": m["sharpe"],
                    "within_tolerance": bool(m["mdd"] >= DD_TOLERANCE),
                })
    df = pd.DataFrame(rows)
    out = PROJECT_ROOT / "comparison_results"
    out.mkdir(exist_ok=True)
    df.to_csv(out / "drawdown_control_grid.csv", index=False)

    def find(g, a, l, cf, hb="SHY"):
        return df[(df.gold == g) & (df.avgo == a) & (df.lly == l)
                  & (df.core_frac == cf) & (df.home_base == hb)].iloc[0]

    # ── 1. Where the live portfolio actually sits ─────────────────────────
    print("\n" + "=" * 78)
    print("1. WHERE THE LIVE PORTFOLIO SITS")
    print("=" * 78)
    for hb in ("SHY", "cash2pct"):
        r = find(25, 40, 35, LIVE_CORE_FRAC, hb)
        p = find(25, 55, 20, LIVE_CORE_FRAC, hb)
        print(f"\nHome Base = {hb}")
        print(f"  LIVE  Gold25/AVGO40/LLY35 @85% core: "
              f"CAGR {r.cagr:6.2%}  MaxDD {r.mdd:7.2%}  Calmar {r.calmar:.3f}"
              f"   {'WITHIN' if r.within_tolerance else 'BREACHES'} -25%")
        print(f"  PREV  Gold25/AVGO55/LLY20 @85% core: "
              f"CAGR {p.cagr:6.2%}  MaxDD {p.mdd:7.2%}  Calmar {p.calmar:.3f}"
              f"   {'WITHIN' if p.within_tolerance else 'BREACHES'} -25%")

    # ── 2. Can the Core alone reach tolerance? ────────────────────────────
    print("\n" + "=" * 78)
    print("2. CAN CORE REWEIGHTING ALONE REACH -25%?")
    print("=" * 78)
    core_only = df[(df.core_frac == 1.00) & (df.home_base == "SHY")]
    print(f"Core-only combos within -25%: {core_only.within_tolerance.sum()} "
          f"of {len(core_only)}")
    print(f"Shallowest MaxDD achievable by ANY weight mix: "
          f"{core_only.mdd.max():.2%}  "
          f"({core_only.loc[core_only.mdd.idxmax(), 'label']})")
    print("-> If this is > -25%, reweighting alone cannot get there and the")
    print("   bucket split is the only lever that can.")

    # ── 3. The dominating region vs live ──────────────────────────────────
    print("\n" + "=" * 78)
    print("3. CONFIGURATIONS THAT DOMINATE LIVE (higher CAGR *and* shallower DD)")
    print("=" * 78)
    live = find(25, 40, 35, LIVE_CORE_FRAC)
    s = df[(df.home_base == "SHY")]
    dom = s[(s.cagr > live.cagr) & (s.mdd > live.mdd)]
    print(f"{len(dom)} of {len(s)} configurations dominate live on both axes.")
    print("\nOf those, the ones also INSIDE the -25% tolerance:")
    domok = dom[dom.within_tolerance].sort_values("cagr", ascending=False)
    cols = ["label", "core_frac", "cagr", "mdd", "calmar", "sharpe"]
    if len(domok):
        print(domok.head(15)[cols].to_string(index=False,
              float_format=lambda x: f"{x:8.3f}"))
    else:
        print("  none -- dominating live and meeting tolerance are different asks.")

    # ── 4. The actual frontier under the tolerance constraint ─────────────
    print("\n" + "=" * 78)
    print("4. HIGHEST-RETURN PORTFOLIO AT EACH DRAWDOWN CEILING (Home Base=SHY)")
    print("=" * 78)
    print(f"{'ceiling':>9}  {'best config':<22}{'core%':>7}{'CAGR':>9}"
          f"{'MaxDD':>9}{'Calmar':>8}")
    best_at = {}
    for ceil in [-0.15, -0.18, -0.20, -0.22, -0.25, -0.28, -0.30, -0.35, -1.0]:
        sub = s[s.mdd >= ceil]
        if not len(sub):
            print(f"{ceil:>8.0%}   none")
            continue
        b = sub.loc[sub.cagr.idxmax()]
        best_at[ceil] = b
        print(f"{ceil:>8.0%}   {b.label:<22}{b.core_frac:>7.0%}{b.cagr:>9.2%}"
              f"{b.mdd:>9.2%}{b.calmar:>8.3f}")

    # ── 5. What it costs, in FI@50 terms ──────────────────────────────────
    print("\n" + "=" * 78)
    print("5. WHAT DRAWDOWN CONTROL COSTS AT THE FI@50 HORIZON")
    print("=" * 78)
    target_nom = TARGET_REAL * (1 + TARGET_INFLATION) ** (HORIZON_YEAR - TARGET_BASE_YEAR)
    print(f"TPV now {TPV_NOW:,.0f} kr | {MONTHLY_CONTRIB:,.0f} kr/mo | "
          f"{YEARS_LEFT:.2f} yrs to 2038-10-10")
    print(f"Target at horizon: {target_nom:,.0f} kr nominal "
          f"({TARGET_REAL:,.0f} real 2026 kr)\n")
    print(f"{'config':<30}{'core%':>7}{'CAGR':>8}{'MaxDD':>8}"
          f"{'proj TPV 2038':>16}{'vs target':>14}")
    scenarios = [("LIVE Gold25/AVGO40/LLY35", find(25, 40, 35, LIVE_CORE_FRAC))]
    for ceil in (-0.25, -0.22, -0.20):
        if ceil in best_at:
            b = best_at[ceil]
            scenarios.append((f"<={abs(ceil):.0%}DD {b.label}", b))
    for name, r in scenarios:
        fv = fv_with_contributions(TPV_NOW, r.cagr, YEARS_LEFT, MONTHLY_CONTRIB)
        print(f"{name:<30}{r.core_frac:>7.0%}{r.cagr:>8.2%}{r.mdd:>8.2%}"
              f"{fv:>16,.0f}{fv - target_nom:>+14,.0f}")

    print("\nNOTE: projecting a 2004-2026 backtested CAGR forward 12 years is an")
    print("illustration of the TRADE-OFF between rows, not a forecast of any row.")

    print(f"\nWrote {out / 'drawdown_control_grid.csv'} ({len(df):,} rows)")


if __name__ == "__main__":
    main()
