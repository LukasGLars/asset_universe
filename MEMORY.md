# MEMORY.md — Asset Universe handoff doc

Personal quant-finance infra for a Swedish investor's FI@50 plan. Read this
before starting work; update it when you finish a meaningful chunk. Deeper
history (full derivation of the base weights, walk-forward backtests, rotation
sleeve tests that were tried and closed, correlation analysis, etc.) lives in
the operator's personal memory file, not in this repo — ask if you need it;
this file is meant to be self-contained for day-to-day continuation.

## Current strategy ("Strategy D", validated 2026-06-30)

3-asset scarcity base (static, no dynamic adjustments unless a tactical rule
below fires):
- Gold (GC_F / PPFB.DE): 25%
- AVGO: 55%
- LLY: 20%

On top of the base, tactical rules (all live in `fi_tracker.py`, "TACTICAL
RULES" section):
- **AVGO 200d guard** — if AVGO closes below its 200d SMA, rotate AVGO's
  weight into Gold+LLY (Gold 52.5%, LLY 47.5%). Re-enter base when AVGO
  closes back above 200d SMA. OOS-validated (Calmar 2.658 vs base 1.434,
  2020-2026), dominant lever of the combined system. **Parameter-sensitivity
  tested 2026-07-01 (PR #2): ROBUST** — see below.
- **Silver GSR tactical** — T1 (GSR>=83.36, fallen >=5% from 60d peak) adds
  +12% silver funded from AVGO; T2 (GSR>=86.45) adds +17%; exit at
  GSR<62.56. Currently INACTIVE.
- **AVGO earnings checkpoint** (`fi_tracker.py`, after the guard block) —
  prints fwd/trail EPS ratio (baseline 3.23x, vs 1.1-1.5x for quality peers)
  and next earnings date. Manual judgment call after each print, not an
  automated rule.

Combined backtest (2009-2026, 10bps TC): CAGR +37.1%, Sharpe 1.688, MaxDD
-16.8%, Calmar 2.205.

Real portfolio (as of 2026-06-24, `config/portfolio.toml`) does **not** yet
match the target weights — still WMT/CCJ/VRT-heavy, AVGO ~7%. Plus one
tactical position: **HWM, 11 shares, opened 2026-06-24**, time exit by
2026-07-25 (or MA50 breach / $271 hard stop). Rebalancing toward the target
is the next open decision (see below).

## Key scripts

- `fi_tracker.py` — daily dashboard: snapshot, FI@50 pace, regime table,
  portfolio signals, AVGO guard + earnings checkpoint. Runs via
  `.github/workflows/sync.yml`.
- `check_sync_health.py` — validates the daily sync actually ran and produced
  sane `status.md` output; new step in `sync.yml` after commit-and-push. See
  PR #3.
- `src/asset_universe/analysis/engine.py` — conditional return engine.
  `current_regime()`, `query()`, `screen_tactical()` (4-gate tactical entry
  screen), `_next_earnings()`.
- `run_universe_screen.py` — regime-conditional ranking of the full asset
  universe (no history cutoff, uncapped forward returns). Writes
  `universe_screen_results.csv`. Re-run when the regime label changes, or
  when the cached CSV is more than a few days stale.
- `run_entry_screen.py` — daily-rerunnable opportunistic entry screen for
  war-chest/home-base capital (separate from the base strategy). See PR #5.
- `run_combined_system.py` — the validated Strategy D backtest (source of
  the baseline numbers quoted above).
- `run_parameter_sensitivity.py` — robustness grid over the guard/silver
  thresholds. See PR #2.
- `run_regime_alert.py` — daily regime-flip monitor, appends to `status.md`.
- `run_optimizer_all_regimes.py` — per-regime portfolio optimizer (writes
  `optimizer_results/{RY}_{BAA}.csv`).

## 2026-07-01 — Overnight validation session (PRs #2-#5)

Context: the system above (guard + silver + checkpoint) had three open gaps —
nobody had tested whether the thresholds were robust or curve-fit, nobody
would notice if the daily automation silently failed, and the opportunistic
entry logic from the HWM trade had never been generalized into a reusable
tool. All three closed in one overnight session, plus one bug found along the
way.

**1. Parameter sensitivity (PR #2) — DONE, verdict ROBUST.**
`run_parameter_sensitivity.py` grids `AVGO_MA` (150/175/200/225/250) x
`gsr_scale` (0.80/0.90/1.00/1.10/1.20, a single multiplier on GSR_T1/T2/EXIT
together). Self-check: center cell (200, 1.00) reproduces the known baseline
exactly (Calmar 2.205). Across all 25 cells, Calmar ranges [1.908, 2.682] —
every cell beats the static-base benchmark (1.063) by ~2x, and the validated
config is *not* the grid maximum, it sits mid-surface with no cliffs nearby.
Conclusion: the edge comes from the mechanism, not a tuned knife-edge.
Thresholds were **not** changed — this was a robustness check, not a re-tune.
Gotcha: `data/` is gitignored and absent from fresh worktrees — copy it from
the main checkout before running backtests there.

**2. Operational fail-safe check (PR #3) — DONE.**
`check_sync_health.py`, wired into `sync.yml` *after* the commit-and-push
step (so a degraded-but-real `status.md` still gets recorded before the job
fails). Checks (a) freshness against the actual weekday cron schedule
(handles the Fri-evening -> Mon-morning gap by walking the schedule backwards
rather than a flat threshold) and (b) failure signatures (`[unavailable`,
`Traceback`, `Error`, missing key sections). Self-tested against a clean pass
case and two constructed fail cases (staleness, broken content) — both
correctly flagged. Bonus: it also flagged the *real* `status.md` as broken,
which led to finding #3 below.

**3. scipy dependency fix (PR #4) — DONE.**
The health check's true-negative catch led here: `run_optimizer.py`,
`run_optimizer_all_regimes.py`, `run_terminal_wealth.py`, and
`run_walkforward.py` all import `scipy.optimize`, but `scipy` was never
declared in `pyproject.toml`. CI installs via `pip install -e .`, so every
scheduled sync has been crashing on the optimizer step since these scripts
were added (confirmed independently in the live `status.md` traceback — not
just the agent's report). Fixed by adding `scipy>=1.11.0` to dependencies.
Does not affect the guard/silver/checkpoint sections (no scipy dependency
there) — portfolio signals were never corrupted, just the optimizer step was
silently dead.

**4. Opportunistic entry screen (PR #5) — DONE.**
`run_entry_screen.py` wraps the existing `screen_tactical()` in `engine.py`
(which already implemented 3 of 4 gates: regime, MA50-extension/RS,
earnings) rather than reimplementing it. Adds an automated regime-ranking
source (replacing a hand-picked candidate list) and an explicit above-MA50
gate. **Retroactively validated against the one ground-truth case
available**: truncated the data to <=2026-06-24 and re-ran — HWM surfaces at
rank 9 and clears all 4 gates, matching the actual entry decision. Two real
bugs caught and fixed during the build (not silently patched): an early
version wrongly borrowed a 10yr history-length floor from a different
script, which excluded HWM (9.6yr history); and a capped-vs-uncapped
forward-return methodology mismatch between `universe_screen_results.csv`
and `engine.query()` was producing false "stale data" positives. **Live
candidates as of 2026-06-30 close** (HIGH+TIGHT regime): HOOD, HWM, VRT,
VST, NRG, ANET, PWR, BKNG, TRGP, CMI, TPR. Re-run before deploying any
war-chest/home-base capital — this is a daily-rerunnable screen, not a
one-time report. Gotcha: the earnings gate queries yfinance's *live*
calendar and can't be replayed retroactively — flagged in script output
whenever `--as-of` is passed.

**PR-merge note**: all three worktree agents independently created this file
from scratch (none existed before). This version (committed to PR #2,
master's first MEMORY.md) is the consolidated, accurate-after-all-four-merge
version; PRs #3 and #5 had their own draft `MEMORY.md` removed from their
diffs to avoid merge conflicts — their functional code changes are
unaffected. Merge order doesn't matter beyond #2 needing to land before or
alongside the others for this file to exist on master.

## Next steps (priority order, set 2026-07-01, time-boxed: max 2 sessions on
robustness + opportunistic entries before the rebalance happens regardless of
how "finished" either feels — that condition is now satisfied, all three are
done)

1. ~~Parameter sensitivity~~ — DONE, robust (see above).
2. ~~Operational fail-safe check~~ — DONE (see above).
3. ~~Opportunistic entry screen~~ — DONE (see above).
4. **Rebalancing decision** — current portfolio (WMT/CCJ/VRT/HWM-heavy)
   still doesn't match the target (Gold25/AVGO55/LLY20). Open sub-question:
   lump-sum into AVGO now (63x trailing P/E, priced for near-perfection per
   2026-07-01 valuation review) vs. staging the entry over time — the
   backtest assumes the target weight is held from day one and doesn't
   answer this. **This is next up now that 1-3 are closed.**
5. **HWM tactical exit** — time exit by 2026-07-25 (or MA50 breach / $271
   hard stop, whichever first). Check `run_entry_screen.py` output / Avanza
   MA50 daily.
6. **AVGO conviction tests** — deferred until the 200d guard fires and stays
   active (tripwire). Not yet triggered.
7. **Valuation screen** — generalize the trailing/forward EPS-ratio check
   (used for AVGO) into a reusable script across the ~70-asset
   quality-filtered universe. Monitoring tool, not an AVGO-replacement
   search — doesn't override item 6's tripwire. Not yet built.

**Other gaps flagged 2026-07-01, not yet on a numbered item:**
currency/account-type never discussed (Gold=EUR, AVGO/LLY/WMT=USD, FI@50
tracked in SEK — is the AVGO position in an ISK or a regular depå, and is FX
hedging worth considering for a Swedish investor with most net worth in USD
mega-caps?). LLY's correlation to AVGO in a *broad* AI-theme drawdown (not an
AVGO-specific miss) is still unresolved.
