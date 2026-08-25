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

import datetime as dt

from eps_ratio import normalized_eps_ratio

# Same nine tickers, same order, as the 2026-07-06 MEMORY.md analysis --
# order preserved so this output is directly comparable to that entry.
PEER_SET = ["MU", "AMD", "AVGO", "NVDA", "MRVL", "TSM", "ASML", "ANET", "QCOM"]

MARKED_TICKER = "AVGO"

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


def main() -> None:
    snapshot_date = dt.datetime.now(dt.timezone.utc).date()
    rows = []
    for ticker in PEER_SET:
        snap = fetch_ticker_snapshot(ticker)
        rows.append(build_row(ticker, snap["price"], snap["ttm_quarters"], snap["forward_1y"]))
    print_table(rows, snapshot_date)


if __name__ == "__main__":
    main()
