"""run_peer_valuation.py

Peer valuation snapshot: AVGO's embedded growth expectation (fwd/trail EPS
ratio, same normalized non-GAAP method as `eps_ratio.py`) against real
AI/semi peers, with price included -- forward P/E and a 1-year PEG -- so the
growth read can be judged as cheap or expensive, not just high or low.

Replaces the 2026-07-06 analysis that lives only as prose in MEMORY.md
(~lines 684, 747): that session recorded peer fwd/trail ratios but never the
peer forward P/E / PEG numbers behind conclusions like "only NVDA/QCOM have a
lower forward P/E, only MU has a lower PEG" -- those numbers are gone and six
weeks stale. This script makes the comparison reproducible on demand.

PEG(1y) caveat: this script's PEG is built on the same 1-year forward growth
estimate as the ratio above it -- NOT the conventional 5-year growth estimate
that yfinance's own `pegRatio` field (and PEG ratios generally) use. That is
why it's labeled PEG(1y), not PEG, and why yfinance's `pegRatio` is
deliberately not fetched here -- mixing the two would repeat exactly the
kind of basis mismatch `eps_ratio.py` exists to correct. See the footnote
printed at the end of this script's output.

Do not use `info["trailingEps"]` / `info["forwardEps"]` for the EPS inputs --
those mix GAAP and non-GAAP conventions (see `eps_ratio.py`'s docstring for
the AVGO 3.22x-vs-2.39x bug this caused on 2026-07-06). This script sources
TTM/forward EPS the same way `fi_tracker.py`'s AVGO checkpoint already does:
`earnings_history["epsActual"]` / `eps_trend.loc["+1y", "current"]`, both
non-GAAP on both sides.

Wired into daily sync.yml as of 2026-08-25 (appended to status.md, same
pattern as run_regime_alert.py/run_optimizer.py) -- supersedes the
2026-07-06 "manual only" decision. Still no alert/trigger of any kind.

Usage:
    python run_peer_valuation.py
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from eps_ratio import normalized_eps_ratio

# Same nine tickers, same order, as the 2026-07-06 MEMORY.md analysis --
# order preserved so this output is directly comparable to that entry.
PEER_SET = ["MU", "AMD", "AVGO", "NVDA", "MRVL", "TSM", "ASML", "ANET", "QCOM"]

MARKED_TICKER = "AVGO"

# ── Valuation history (added 2026-10-18) ─────────────────────────────────────
# The snapshot answers "cheap versus peers TODAY". It cannot answer "cheap
# versus its OWN past", which is the question that actually supports a
# decision -- a whole sector can de-rate together and leave every rank
# unchanged. That needs a time series, and a time series cannot be
# backfilled: yfinance serves today's forward estimate, not the forward
# estimate as it stood a year ago. So the only way to have this in a year is
# to start storing it now.
#
# Stores raw metrics only. No rule, no alert, no threshold -- see the module
# docstring's "Still no alert/trigger of any kind", which remains true.
#
# MUST be listed in sync.yml's `git add` path list or the runner's copy is
# discarded and nothing accumulates.
HISTORY_CSV = Path(__file__).parent / "comparison_results" / "peer_valuation_history.csv"
HISTORY_FIELDS = ["date", "ticker", "price", "ttm_eps", "fwd_eps",
                  "ratio", "growth_pct", "fwd_pe", "peg_1y"]

# Below this many stored observations a percentile is noise, so it is not
# shown at all rather than shown with a caveat nobody reads.
MIN_HISTORY_OBS = 60


def read_history() -> list[dict]:
    if not HISTORY_CSV.exists():
        return []
    with HISTORY_CSV.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_history(rows: list[dict]) -> None:
    HISTORY_CSV.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=HISTORY_FIELDS)
        w.writeheader()
        w.writerows(rows)


def append_history(rows: list[dict], snapshot_date: dt.date,
                   existing: list[dict] | None = None) -> list[dict]:
    """One row per ticker per date. Same-date rows are REPLACED, not appended:
    sync.yml fires twice a day (06:07 and 20:37 UTC), and without this the
    file would carry two rows per day and silently double-weight every day in
    any percentile computed from it."""
    today = str(snapshot_date)
    kept = [r for r in (existing if existing is not None else read_history())
            if r.get("date") != today]
    for r in rows:
        kept.append({
            "date": today,
            "ticker": r["ticker"],
            "price": r["price"],
            "ttm_eps": r["ttm_eps"],
            "fwd_eps": r["fwd_eps"],
            "ratio": r["ratio"],
            "growth_pct": r["growth_pct"],
            "fwd_pe": r["fwd_pe"],
            "peg_1y": r["peg_1y"],
        })
    kept.sort(key=lambda r: (r["date"], r["ticker"]))
    return kept


def own_history_percentile(history: list[dict], ticker: str, field: str,
                           current: float | None) -> tuple[float | None, int]:
    """Fraction of this ticker's stored history that was CHEAPER than today.

    Low = cheap. Returns (percentile, n). Today's own row is excluded so the
    reading is "versus its past", not "versus its past including itself".
    """
    if current is None:
        return None, 0
    vals = []
    for r in history:
        if r.get("ticker") != ticker:
            continue
        raw = r.get(field)
        if raw in (None, "", "None"):
            continue
        try:
            vals.append(float(raw))
        except ValueError:
            continue
    if len(vals) < MIN_HISTORY_OBS:
        return None, len(vals)
    cheaper = sum(1 for v in vals if v < current)
    return cheaper / len(vals), len(vals)

# The historical PEG(0.41) MEMORY.md recorded alongside a 19.4x forward P/E
# on 2026-07-06 -- kept only to name the discrepancy in the footnote, not
# used in any computation here.
_HISTORICAL_AVGO_FWD_PE = 19.4
_HISTORICAL_AVGO_PEG_5Y = 0.41


# ── Fetch layer (network) ────────────────────────────────────────────────────

def fetch_ticker_snapshot(ticker: str) -> dict:
    """Best-effort live fetch of the three raw inputs this script needs.
    Each field is fetched independently so one missing/erroring field (or
    one broken ticker entirely) never takes down the rest of the run --
    every field defaults to a value build_row() already treats as n/a."""
    import yfinance as yf

    tk = yf.Ticker(ticker)

    price: float | None = None
    try:
        info = tk.info
        price = (info.get("currentPrice") or info.get("regularMarketPrice")
                  or info.get("previousClose"))
    except Exception:
        pass

    ttm_quarters: list[float] = []
    try:
        hist = tk.earnings_history
        if hist is not None and not hist.empty:
            ttm_quarters = hist["epsActual"].dropna().tolist()
    except Exception:
        pass

    forward_1y: float | None = None
    try:
        trend = tk.eps_trend
        if trend is not None and "+1y" in trend.index:
            forward_1y = trend.loc["+1y", "current"]
    except Exception:
        pass

    return {"ticker": ticker, "price": price, "ttm_quarters": ttm_quarters,
            "forward_1y": forward_1y}


# ── Derive layer (pure, no network -- unit tested directly) ────────────────

def build_row(
    ticker: str,
    price: float | None,
    ttm_quarters: list[float] | None,
    forward_1y_eps: float | None,
) -> dict:
    """All four derived columns (ratio, implied growth, forward P/E, PEG(1y))
    are gated on the ratio itself being computable -- if TTM EPS is invalid
    (missing, <4 quarters, or non-positive) or the forward estimate is
    missing, the whole derived block is n/a for that row, not a partial mix.
    PEG(1y) has its own additional gate: growth must be positive, since a
    negative-growth PEG isn't a meaningful number."""
    valid_ttm = ttm_quarters is not None and len(ttm_quarters) >= 4
    ttm_eps = sum(ttm_quarters) if valid_ttm else None
    ratio = normalized_eps_ratio(ttm_quarters, forward_1y_eps) if valid_ttm else None

    growth_pct: float | None = None
    fwd_pe: float | None = None
    peg_1y: float | None = None

    if ratio is not None:
        growth_pct = (ratio - 1) * 100
        if price is not None and forward_1y_eps:
            fwd_pe = price / forward_1y_eps
        if fwd_pe is not None and growth_pct > 0:
            peg_1y = fwd_pe / growth_pct

    return {
        "ticker": ticker,
        "price": price,
        "ttm_eps": ttm_eps,
        "fwd_eps": forward_1y_eps,
        "ratio": ratio,
        "growth_pct": growth_pct,
        "fwd_pe": fwd_pe,
        "peg_1y": peg_1y,
    }


def compute_ranks(rows: list[dict], key: str, ascending: bool) -> dict[str, int | None]:
    """Standard competition ranking (ties share a rank, the next distinct
    value skips accordingly -- 1,1,3 not 1,1,2). Rows whose value is n/a for
    this key are excluded from ranking and get None, not dropped from the
    return dict."""
    valid = [(r["ticker"], r[key]) for r in rows if r.get(key) is not None]
    valid.sort(key=lambda t: t[1], reverse=not ascending)

    ranks: dict[str, int | None] = {r["ticker"]: None for r in rows}
    prev_val = None
    prev_rank = 0
    for i, (ticker, val) in enumerate(valid, start=1):
        rank = prev_rank if val == prev_val else i
        ranks[ticker] = rank
        prev_val, prev_rank = val, rank
    return ranks


# ── Format layer ─────────────────────────────────────────────────────────────

def _fmt(value: float | None, kind: str) -> str:
    if value is None:
        return "n/a"
    if kind == "$":
        return f"${value:,.2f}"
    if kind == "x":
        return f"{value:.2f}x"
    if kind == "%":
        return f"{value:+.0f}%"
    return f"{value:.2f}"


def _fmt_rank(rank: int | None) -> str:
    return str(rank) if rank is not None else "n/a"


def print_table(rows: list[dict], snapshot_date: dt.date) -> None:
    rows_sorted = sorted(
        rows,
        key=lambda r: (r["ratio"] is None, -(r["ratio"] if r["ratio"] is not None else 0)),
    )

    print(f"AVGO peer valuation snapshot -- {snapshot_date}\n")

    header = (f"{'Ticker':<8}{'Price':>11}{'TTM EPS':>10}{'Fwd EPS':>10}"
              f"{'Fwd/Trail':>11}{'Impl.growth':>13}{'Fwd P/E':>10}{'PEG(1y)':>10}")
    print(header)
    print("-" * len(header))
    for r in rows_sorted:
        label = r["ticker"] + ("*" if r["ticker"] == MARKED_TICKER else "")
        print(
            f"{label:<8}"
            f"{_fmt(r['price'], '$'):>11}"
            f"{_fmt(r['ttm_eps'], '$'):>10}"
            f"{_fmt(r['fwd_eps'], '$'):>10}"
            f"{_fmt(r['ratio'], 'x'):>11}"
            f"{_fmt(r['growth_pct'], '%'):>13}"
            f"{_fmt(r['fwd_pe'], 'x'):>10}"
            f"{_fmt(r['peg_1y'], ''):>10}"
        )
    print(f"\n* = {MARKED_TICKER}\n")

    n = len(rows)
    ranks_ratio = compute_ranks(rows, "ratio", ascending=False)
    ranks_pe = compute_ranks(rows, "fwd_pe", ascending=True)
    ranks_peg = compute_ranks(rows, "peg_1y", ascending=True)
    print(f"{MARKED_TICKER} rank -- growth ratio (highest first): "
          f"{_fmt_rank(ranks_ratio.get(MARKED_TICKER))} of {n}")
    print(f"{MARKED_TICKER} rank -- forward P/E (cheapest first): "
          f"{_fmt_rank(ranks_pe.get(MARKED_TICKER))} of {n}")
    print(f"{MARKED_TICKER} rank -- PEG(1y) (cheapest first)    : "
          f"{_fmt_rank(ranks_peg.get(MARKED_TICKER))} of {n}")

    print(
        "\nNote: PEG(1y) is built on a 1-year forward growth estimate, not the "
        "conventional 5-year estimate PEG ratios (including yfinance's own "
        "pegRatio field, deliberately not fetched here) normally use. "
        f"MEMORY.md's 2026-07-06 entry recorded AVGO's PEG as "
        f"{_HISTORICAL_AVGO_PEG_5Y} alongside a {_HISTORICAL_AVGO_FWD_PE}x forward "
        f"P/E -- those two never reconciled on the same basis "
        f"({_HISTORICAL_AVGO_FWD_PE} / 139% implied growth = 0.14, not "
        f"{_HISTORICAL_AVGO_PEG_5Y}). PEG(1y) above is internally consistent but "
        "not comparable to that historical figure or to any 5-year PEG from "
        "elsewhere."
    )


def print_own_history(rows: list[dict], history: list[dict]) -> None:
    """Where each name sits against its OWN stored past, which the peer ranks
    above cannot say. Prints the accrual state honestly while it is still
    filling rather than implying a reading exists."""
    print(f"\n{MARKED_TICKER} and peers vs their OWN stored history "
          f"(low percentile = cheap for that name)")
    print(f"{'Ticker':<8}{'Fwd P/E':>10}{'pctile':>9}{'obs':>6}")
    for r in sorted(rows, key=lambda x: x["ticker"]):
        pct, n = own_history_percentile(history, r["ticker"], "fwd_pe", r["fwd_pe"])
        pct_s = f"{pct:.0%}" if pct is not None else "--"
        print(f"{r['ticker']:<8}{_fmt(r['fwd_pe'], 'x'):>10}{pct_s:>9}{n:>6}")
    have = max((own_history_percentile(history, r["ticker"], "fwd_pe",
                                        r["fwd_pe"])[1] for r in rows), default=0)
    if have < MIN_HISTORY_OBS:
        print(f"  accruing -- {have}/{MIN_HISTORY_OBS} observations needed before a "
              f"percentile is shown. Started 2026-10-18; cannot be backfilled.")


def main() -> None:
    snapshot_date = dt.datetime.now(dt.timezone.utc).date()
    rows = []
    for ticker in PEER_SET:
        snap = fetch_ticker_snapshot(ticker)
        rows.append(build_row(ticker, snap["price"], snap["ttm_quarters"], snap["forward_1y"]))
    print_table(rows, snapshot_date)

    # Persistence must never break the sync. This block is appended to
    # status.md, and check_sync_health.py fails the whole job on the string
    # "Traceback" appearing there -- so a disk or CSV problem would take the
    # pipeline down over a column nobody acts on yet.
    try:
        history = read_history()
        print_own_history(rows, history)
        write_history(append_history(rows, snapshot_date, history))
    except Exception as exc:
        print(f"\n  valuation history unavailable: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
