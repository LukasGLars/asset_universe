"""eps_ratio.py

Forward/trailing EPS ratio, computed on a consistent (non-GAAP-to-non-GAAP)
basis. yfinance's raw `trailingEps`/`forwardEps` fields mix conventions for
companies with a large GAAP/non-GAAP gap -- `trailingEps` is GAAP, while
`forwardEps` is a non-GAAP analyst consensus estimate. Comparing them
directly overstates the embedded growth assumption for any company with
heavy non-cash charges (acquisition-intangible amortization, stock-based
comp) between GAAP and non-GAAP earnings.

Found 2026-07-06: AVGO's naive ratio was reported as 3.22x (GAAP trailing
$6.02 vs non-GAAP forward $19.40) -- largely an artifact of VMware-
acquisition amortization depressing the GAAP side. Properly normalized
(non-GAAP TTM actual vs non-GAAP +1yr estimate, both from yfinance's
`earnings_history`/`eps_trend`), the real ratio is 2.39x. The original
"outlier" framing against a 1.17-1.41x range (AAPL/TDG/ANET) was itself a
peer-selection artifact -- those companies don't share AVGO's AI-capex
growth story. Against real AI/semi peers (MU/AMD/NVDA/MRVL/TSM/ASML/ANET/
QCOM), re-checked 2026-08-14, AVGO is mid-pack: below MU/AMD, in line with
NVDA/MRVL, above TSM/ASML/ANET/QCOM -- see `run_peer_valuation.py` for the
reproducible, price-aware version of this comparison (adds forward P/E and
a 1-year PEG, not just the ratio). LLY barely moved (1.58x naive vs 1.51x
normalized) since it doesn't carry a comparable GAAP/non-GAAP gap.
"""
from __future__ import annotations


def normalized_eps_ratio(
    quarterly_actual_eps: list[float],
    forward_1y_estimate: float | None,
) -> float | None:
    """TTM non-GAAP actual EPS (sum of the last reported quarters) vs the
    +1yr non-GAAP consensus estimate. Both inputs already come from the
    same (non-GAAP) convention, unlike yfinance's raw trailingEps/forwardEps."""
    if not quarterly_actual_eps or forward_1y_estimate is None:
        return None
    ttm_actual = sum(quarterly_actual_eps)
    if ttm_actual <= 0:
        return None
    return forward_1y_estimate / ttm_actual
