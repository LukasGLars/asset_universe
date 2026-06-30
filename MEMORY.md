# MEMORY.md — Asset Universe handoff log

Shared handoff doc per repo CLAUDE.md. Read this first each session. Append a
dated entry when you finish a meaningful chunk of work — don't rewrite history.

## 2026-07-01 — Parameter sensitivity grid for AVGO guard + GSR silver system (PR #2)

**What was done:** Added `run_parameter_sensitivity.py`, which extends
`run_combined_system.py`'s Strategy D (Base Gold25/AVGO55/LLY20 + AVGO
200d-SMA guard + silver GSR tactical layer) into a 5x5 grid over `AVGO_MA`
(SMA window: 150/175/200/225/250) and `gsr_scale` (single multiplier on
GSR_T1/T2/EXIT together, preserving relative spacing: 0.80/0.90/1.00/1.10/1.20).
Results saved to `comparison_results/parameter_sensitivity_grid.csv`.

**Self-check:** center cell (AVGO_MA=200, gsr_scale=1.00) reproduces the
known-correct baseline exactly — CAGR +37.07% vs +37.1%, Sharpe 1.688,
MaxDD -16.81% vs -16.8%, Calmar 2.205 vs 2.205. PASS, no tolerance needed
beyond rounding.

**Verdict: ROBUST, not curve-fit.** Calmar across all 25 cells ranges
[1.908, 2.682] — every cell beats Strategy A's static-base baseline
(Calmar 1.063) by a wide margin. The validated center cell (200, 1.00) is
*not* the grid maximum — (150, 1.20) hits 2.682. The surface is smooth and
monotonic (Calmar rises as AVGO_MA shrinks, rises as gsr_scale increases),
no cliffs or isolated spikes. This means the edge comes from the guard +
silver mechanism itself, not from tuning to a knife-edge parameter value.

**Decision/no-action:** did not change the live thresholds in
`run_combined_system.py` (AVGO_MA=200, GSR_T1=83.36, GSR_T2=86.45,
GSR_EXIT=62.56) — this task was a robustness check only, not a re-tune.
Worth revisiting: (150, 1.20) and nearby cells outperform the current
config on Calmar; if a re-tune is ever wanted, that corner is the
candidate, but MaxDD is similar across the grid so the upside is mostly
CAGR, not risk reduction.

**Gotchas:**
- `data/` is gitignored and absent from fresh worktrees — copy it in from
  the main checkout before running any backtest script in a new worktree.
- The grid script duplicates `build_signals`/`run_strategy`/`perf`/`WEIGHTS`
  from `run_combined_system.py` with the two thresholds parametrized
  (`avgo_ma`, `gsr_t1/t2/exit` args instead of module constants) — kept as a
  separate file rather than refactoring the original to avoid touching a
  validated, working script for an exploratory grid.

**Next:** per prior project notes — add a tactical gold signal to the base,
then explore a 5-asset optimizer (add Silver + CCJ) once the AVGO/GSR
system above is considered settled.
