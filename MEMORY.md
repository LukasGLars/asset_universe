# MEMORY.md — Asset Universe handoff doc

Personal quant-finance infra for a Swedish investor's FI@50 plan. Read this
before starting work; update it when you finish a meaningful chunk.

## Current strategy ("Strategy D", validated 2026-06-30)

3-asset scarcity base (static, no dynamic adjustments unless a tactical rule
below fires):
- Gold (GC_F / PPFB.DE): 25%
- AVGO: 55%
- LLY: 20%

On top of the base, two tactical rules (both live in `fi_tracker.py`,
"TACTICAL RULES" section):
- **AVGO 200d guard** — if AVGO closes below its 200d SMA, rotate AVGO's
  weight into Gold+LLY (Gold 52.5%, LLY 47.5%). Re-enter base when AVGO
  closes back above 200d SMA. OOS-validated (Calmar 2.658 vs base 1.434,
  2020-2026), dominant lever of the combined system.
- **Silver GSR tactical** — T1 (GSR>=83.36, fallen >=5% from 60d peak) adds
  +12% silver funded from AVGO; T2 (GSR>=86.45) adds +17%; exit at
  GSR<62.56. Currently INACTIVE.
- **AVGO earnings checkpoint** (`fi_tracker.py`, after the guard block) —
  prints fwd/trail EPS ratio (baseline 3.23x, vs 1.1-1.5x for quality peers)
  and next earnings date. Manual judgment call after each print, not an
  automated rule.

Real portfolio (as of 2026-06-24, `config/portfolio.toml`) does **not** yet
match the target weights — still WMT/CCJ/VRT-heavy, AVGO ~7%. Plus one
tactical position: **HWM, 11 shares, opened 2026-06-24**, time exit by
2026-07-25 (or MA50 breach / $271 hard stop). Rebalancing toward the target
is an open decision (see Next steps).

## Key scripts

- `fi_tracker.py` — daily dashboard: snapshot, FI@50 pace, regime table,
  portfolio signals, AVGO guard + earnings checkpoint. Runs via
  `.github/workflows/sync.yml`.
- `src/asset_universe/analysis/engine.py` — conditional return engine.
  `current_regime()`, `query()`, `screen_tactical()` (4-gate tactical entry
  screen — see below), `_next_earnings()`.
- `run_universe_screen.py` — regime-conditional ranking of the full asset
  universe (no history cutoff, uncapped forward returns). Writes
  `universe_screen_results.csv`. Re-run when the regime label changes, or
  when the cached CSV is more than a few days stale.
- `run_entry_screen.py` — **new (2026-07-01)**, see below.
- `run_regime_alert.py` — daily regime-flip monitor, appends to `status.md`.
- `run_optimizer_all_regimes.py` — per-regime portfolio optimizer (writes
  `optimizer_results/{RY}_{BAA}.csv`; not currently on disk — re-run if
  needed, ~10-15min for all 9 regimes).

## Opportunistic entry screen — built 2026-07-01

`run_entry_screen.py` is a thin CLI wrapper around `screen_tactical()` in
`engine.py`, which already existed and already implemented 3 of the 4 gates
(macro regime, MA50-extension/RS, earnings). It was the basis for the HWM
entry via the older `run_screen.py` (hand-curated candidate list). This new
script generalizes gate 1 (automated regime-ranking source instead of a
hand-picked list) and adds gate 2 (explicit above-MA50 check — screen_
tactical's own extension gate allows negative extension, so a ticker below
its MA50 could otherwise slip through).

**Gate 1 source logic:** prefers `universe_screen_results.csv` when a
GC_F spot-check (median 252d return, same uncapped methodology the CSV
itself uses) confirms it reflects the live regime; falls back to a fresh
single-regime computation otherwise. Important gotcha found while building
this: `universe_screen_results.csv` is **uncapped** (no regime-end cap on
forward returns), while `engine.query()` is **capped** (added 2026-06-29).
Comparing the CSV against `engine.query()` for freshness produces a false
"stale" result every time (GC_F med_252d: 34% uncapped vs 5% capped, same
regime) — purely a methodology gap, not real staleness. Fixed by comparing
like-for-like (uncapped vs uncapped). The fallback ranking also intentionally
has **no history-length cutoff**, matching `run_universe_screen.py`'s own
design choice — an early version of this script used a 10yr floor (borrowed
from `run_regime_survey.py` / `run_optimizer_all_regimes.py`) which silently
excluded HWM (9.6yr history) from the top-30 candidate list. Caught by the
retroactive self-check below, not by code review — worth remembering before
copying constants between these scripts again.

**Retroactive validation (the one ground-truth case available):** built a
truncated parquet snapshot (all rows <= 2026-06-24) and ran the screen
against it. HWM appears at gate-1 rank 9 and passes all 4 gates (price
$276.06 > MA50 $257.66, ABOVE; screen_tactical PASS) → verdict ENTER.
Matches the actual entry decision. Caveat: the earnings gate (`_next_
earnings`) always queries yfinance's *live* calendar — it cannot be
replayed retroactively, so gate 4 in the retroactive run reflects today's
earnings calendar, not what was knowable on 2026-06-24. Flagged in the
script's own output whenever `--as-of` is passed.

**Live run (2026-06-30 close, latest available data as of 2026-07-01):**
ENTER candidates: HOOD, HWM, VRT, VST, NRG, ANET, PWR, BKNG, TRGP, CMI, TPR.
HWM still passes (still held). This is a daily-rerunnable screen, not a
one-time report — re-run before deploying any war-chest/home-base capital.

**Gotcha:** local `data/` (gitignored, not in any worktree by default) was
stale at 2026-06-24 in the main repo checkout — the GitHub Actions daily
sync commits `status.md`/`portfolio.toml` but never the parquet cache itself
(by design, per `.gitignore`). Ran `python -m asset_universe.update` to
refresh before the live run. If working from a fresh worktree, either copy/
junction `data/` from the main checkout or expect a slow first run while
`update.py` re-fetches everything from yfinance.

## Next steps (priority order, set 2026-07-01, time-boxed: max 2 sessions
on robustness + opportunistic entries combined before the rebalance happens
regardless of how "finished" either feels)

1. **Parameter sensitivity** — never tested whether the guard/silver
   thresholds (200d SMA, GSR 83.36/86.45/62.56, 60d peak window, 5%
   fall-from-peak) sit on a smooth Calmar plateau or a sharp spike at the
   exact chosen values. Do this first — it's the test that could most
   change confidence in the 55% AVGO sizing.
2. **Operational fail-safe check** — alert if `status.md` hasn't updated in
   >24h, so a silently-failed daily sync isn't indistinguishable from "guard
   ran and said hold."
3. **Opportunistic entry screen** — DONE this session (`run_entry_screen.py`).
4. **Rebalancing decision** — current portfolio (WMT/CCJ/VRT/HWM-heavy)
   still doesn't match the target (Gold25/AVGO55/LLY20). Open sub-question:
   lump-sum into AVGO now (63x trailing P/E) vs. staging the entry over time.
5. **HWM tactical exit** — time exit by 2026-07-25 (or MA50 breach / $271
   hard stop, whichever first). Check `run_entry_screen.py` output / Avanza
   MA50 daily.
6. **AVGO conviction tests** — deferred until the 200d guard fires and stays
   active (tripwire). Not yet triggered.
7. **Valuation screen** — generalize the trailing/forward EPS-ratio check
   (used for AVGO) into a reusable script across the ~70-asset
   quality-filtered universe. Monitoring tool, not an AVGO-replacement
   search — doesn't override item 6's tripwire.

Deeper history (full derivation of the base weights, walk-forward backtest
results, rotation-sleeve tests that were tried and closed, correlation
analysis, etc.) lives in the operator's personal memory file, not in this
repo — ask if you need it; this file is meant to be self-contained for
day-to-day continuation.
