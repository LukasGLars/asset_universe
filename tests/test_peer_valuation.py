from run_peer_valuation import build_row, compute_ranks


def test_derivation_math_on_known_inputs():
    # TTM = 4.0, forward = 6.0 -> ratio 1.5, growth 50%, fwd P/E 15x, PEG(1y) 0.3
    row = build_row("TEST", price=90.0, ttm_quarters=[1.0, 1.0, 1.0, 1.0], forward_1y_eps=6.0)
    assert row["ttm_eps"] == 4.0
    assert round(row["ratio"], 2) == 1.5
    assert round(row["growth_pct"], 2) == 50.0
    assert round(row["fwd_pe"], 2) == 15.0
    assert round(row["peg_1y"], 2) == 0.3


def test_negative_growth_returns_na_peg_not_a_negative_number():
    # TTM = 8.0, forward = 6.0 -> ratio 0.75, growth -25% -- PEG is meaningless here
    row = build_row("TEST", price=60.0, ttm_quarters=[2.0, 2.0, 2.0, 2.0], forward_1y_eps=6.0)
    assert row["ratio"] is not None
    assert row["growth_pct"] < 0
    assert row["fwd_pe"] is not None  # still computable, independent of growth sign
    assert row["peg_1y"] is None


def test_zero_or_negative_ttm_eps_returns_na_across_derived_columns():
    row = build_row("TEST", price=50.0, ttm_quarters=[1.0, -1.0, 0.0, 0.0], forward_1y_eps=5.0)
    assert row["ratio"] is None
    assert row["growth_pct"] is None
    assert row["fwd_pe"] is None
    assert row["peg_1y"] is None


def test_partial_earnings_history_returns_na_not_a_partial_ttm():
    # Only 3 quarters -- must not silently sum a partial TTM
    row = build_row("TEST", price=90.0, ttm_quarters=[1.0, 1.0, 1.0], forward_1y_eps=6.0)
    assert row["ttm_eps"] is None
    assert row["ratio"] is None
    assert row["growth_pct"] is None
    assert row["fwd_pe"] is None
    assert row["peg_1y"] is None


def test_missing_forward_estimate_returns_na():
    row = build_row("TEST", price=90.0, ttm_quarters=[1.0, 1.0, 1.0, 1.0], forward_1y_eps=None)
    assert row["ratio"] is None
    assert row["fwd_pe"] is None
    assert row["peg_1y"] is None


def test_missing_price_still_computes_ratio_and_growth_but_not_pe_or_peg():
    row = build_row("TEST", price=None, ttm_quarters=[1.0, 1.0, 1.0, 1.0], forward_1y_eps=6.0)
    assert round(row["ratio"], 2) == 1.5
    assert round(row["growth_pct"], 2) == 50.0
    assert row["fwd_pe"] is None
    assert row["peg_1y"] is None


def test_compute_ranks_handles_ties_and_none():
    rows = [
        {"ticker": "A", "ratio": 2.0},
        {"ticker": "B", "ratio": 2.0},
        {"ticker": "C", "ratio": 1.5},
        {"ticker": "D", "ratio": None},
    ]
    ranks = compute_ranks(rows, "ratio", ascending=False)
    assert ranks["A"] == 1
    assert ranks["B"] == 1
    assert ranks["C"] == 3  # skips rank 2 -- two tied at rank 1
    assert ranks["D"] is None


def test_compute_ranks_ascending_lower_value_is_rank_one():
    rows = [
        {"ticker": "A", "fwd_pe": 30.0},
        {"ticker": "B", "fwd_pe": 10.0},
        {"ticker": "C", "fwd_pe": 20.0},
    ]
    ranks = compute_ranks(rows, "fwd_pe", ascending=True)
    assert ranks["B"] == 1
    assert ranks["C"] == 2
    assert ranks["A"] == 3


def test_compute_ranks_all_none_gives_all_none():
    rows = [{"ticker": "A", "peg_1y": None}, {"ticker": "B", "peg_1y": None}]
    ranks = compute_ranks(rows, "peg_1y", ascending=True)
    assert ranks["A"] is None
    assert ranks["B"] is None
