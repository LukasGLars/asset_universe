# Data Integrity Policy

Every number, label, threshold, and classification produced by this codebase must be traceable to the data in the parquet store. This document defines the standard of evidence required. It applies to all analytical work: regime classification, conditional return engines, signal triggers, analogues, and any future additions.

---

## 1. No hardcoded thresholds

Breakpoints, cutoffs, and boundaries must be derived from the empirical distribution of the relevant series — not assumed, not rounded to convenient numbers, not borrowed from external commentary.

**Minimum standard:** percentile-based splits (e.g. p33/p67 or p25/p75) computed from the full available history of the series.

**Preferred where data supports it:** principled statistical methods that let the data reveal its own structure:
- Gaussian Mixture Models (GMM) — for series with latent multi-modal distributions
- Hidden Markov Models (HMM) — for series with regime-switching behaviour
- Change-point detection — for structural breaks in the level or volatility of a series

If a simpler method is used, the reason must be stated (e.g. insufficient history for GMM convergence, N < 100).

---

## 2. Labels describe data, not narratives

Regime names and category labels are assigned after examining the statistical properties of each cluster or state. They are not pre-assigned and retrofitted.

If a regime is labelled "high real yield / credit tight", that name must reflect what the data in that state actually shows — not a prior assumption about what should co-occur.

When in doubt, use the data's own language: percentile rank, z-score, or cluster index. Human-readable labels are a convenience layer on top, not the foundation.

---

## 3. Sample size transparency

Every conditional return statistic — mean, median, win rate, percentile — must be accompanied by the number of observations (N) that produced it.

| N | Treatment |
|---|---|
| < 10 | Do not report distributions. State N and flag as insufficient. |
| 10–29 | Report with explicit warning. Treat as directional only. |
| 30+ | Reportable. Standard confidence intervals apply. |

A regime with N=4 must never be presented in the same format as one with N=60. If a regime is historically rare, that rarity is itself a finding worth stating.

---

## 4. No look-ahead bias

Regime classification at date T uses only data available at or before T.

This applies to:
- Rolling windows: window must end at T, not beyond
- Moving averages: computed on data up to T only
- Normalisation: z-scores and percentile ranks computed against the history up to T, not the full future series

Any feature that requires knowing future values — even one day ahead — is prohibited in historical regime labelling.

---

## 5. Full reproducibility

Every output must be reproducible by running the code against the parquet store. No exceptions.

Prohibited:
- Numbers typed directly into output files or documents
- Results cached as committed data (status.md is a display artefact, not a data source)
- Manual overrides of computed values
- Pinned or hardcoded dates in analytical scripts

If a result cannot be reproduced from `data/raw/` + the code in this repository, it should not be reported as a finding.

---

## 6. Staleness policy

Any script that reads from the parquet store must use the latest available row for each series. No pinned dates. If the data is stale (last row > 5 business days old), the output must emit a warning before reporting results.

The parquet store is the single source of truth for all market and macro data. External numbers (broker UI, news, memory) are reference only — they do not override computed outputs.

---

## 7. Uncertainty must be visible

Findings must state what they are uncertain about, not just what they show.

Required disclosures:
- N for any conditional statistic
- Date range of the data used
- Whether the current observation falls within the historical range used to fit the model (in-distribution) or outside it (extrapolation)
- Method used to derive thresholds or regime boundaries

A finding that looks precise but rests on N=6 and a hand-drawn threshold is not a finding — it is a prior dressed up as evidence.

---

## Data source decisions

**Credit spread proxy — BAA10Y not BAMLH0A0HYM2**
The primary credit conditioning variable is `BAA10Y` (Moody's Baa minus 10Y Treasury, 26 years of history). The HY OAS series `BAMLH0A0HYM2` (ICE BofA) is restricted by FRED/ICE license to the most recent 3 years via API — insufficient for regime conditioning. `BAA10Y` is used for all historical conditioning. `BAMLH0A0HYM2` is retained for real-time HY monitoring and HY-IG divergence alerting only — it is not used as a conditioning variable.

**HY-IG divergence signal**
`hy_ig_divergence` = 20d change in HY OAS minus 20d change in BAA10Y (both in bps). When this exceeds 1.5 standard deviations of its own historical distribution, `regime_confidence` is set to UNCERTAIN — signalling that the BAA10Y-based regime label may be stale and a regime transition is possible.

## Scope

This policy applies to:
- `conditional_returns.py` and any regime classification module
- `gold_analogues.py` and any future analogue engine
- `fi_tracker.py` scenario projections
- Any signal or trigger threshold used in portfolio decision logic
- Any document, status file, or output committed to this repository

It does not apply to:
- Raw data ingestion (`update.py`, `yf.py`, `fred.py`) — these are pass-through, no classification
- `portfolio.toml` position data — sourced from broker, not computed
- `status.md` — display artefact, regenerated on every sync
