# MEMORY.md — Asset Universe handoff doc

Personal quant-finance infra for a Swedish investor's FI@50 plan. Read this
before starting work; update it when you finish a meaningful chunk. Deeper
history (full derivation of the base weights, walk-forward backtests, rotation
sleeve tests that were tried and closed, correlation analysis, etc.) lives in
the operator's personal memory file, not in this repo — ask if you need it;
this file is meant to be self-contained for day-to-day continuation.

## Google Calendar workflow -- ON HOLD (2026-07-03)

`.github/workflows/google-calendar.yml` exists (triggers on push to `main` +
`workflow_dispatch`), but **currently fails at the Google Cloud OIDC auth
step every time** -- confirmed via a real `workflow_dispatch` test run, not
assumed:

```
failed to generate Google Cloud federated token for
//iam.googleapis.com/projects/456157896331/locations/global/workloadIdentityPools/github-pool/providers/github-provider:
{"error":"invalid_grant","error_description":"Error connecting to the given credential's issuer."}
```

This means the Workload Identity Pool/Provider isn't correctly configured
to trust this repo's OIDC issuer on the Google Cloud side -- **entirely a
GCP Console/`gcloud` configuration issue, not fixable from this repo.**

Repo-side bugs already found and fixed (PR #20): the workflow originally
lived at `.github/.github/workflows/` (invisible to GitHub Actions --
wrong path, would never have triggered) and had a malformed Calendar API
endpoint. A further edit pushed directly to master afterward
(`c7fe72c`) added `scopes: 'https://googleapis.com'` to the auth step,
which also isn't a valid OAuth scope format (real Calendar scopes look
like `https://www.googleapis.com/auth/calendar`) -- not fixed, per the
hold below.

**User decision (2026-07-03): hold this feature. Do not continue
debugging or building without being asked.** If revisited, the GCP-side
Workload Identity Federation setup (issuer trust, attribute condition,
IAM binding) needs to be fixed first -- that work has to happen in Google
Cloud Console, not in this repo.

**Process note, for continuity:** this feature arrived via a request
containing malformed/unverifiable infrastructure values (a syntactically
invalid service account email, then a project ID that read as a truncated
UUID), followed by two direct pushes to `master` bypassing the branch/PR
review used for everything else in this project. Confirmed with the
account owner that the pushes were genuinely theirs. Worth staying alert
to the same pattern if this resurfaces.

## Research backlog (not scheduled, not built -- ideas awaiting validation)

- **BAA10Y credit-spread confirmation for the AVGO/LLY joint-stress rule
  (logged 2026-07-03).** Hypothesis: the 2022 episode where AVGO/LLY
  correlation spiked to +0.32 was a rate/credit-driven macro event, not an
  idiosyncratic one -- a credit-spread confirmation might make the joint-
  stress escalation more precise (confirm it's genuinely macro-driven) or
  fire earlier (credit often leads equity price action). **Use BAA10Y
  (26yr history, already a Core-3 regime input), not HY OAS** (only 3yr of
  API history -- not enough to backtest rigorously, per `INTEGRITY.md`'s
  no-assumptions standard). If tested, use the same TXN-analog +
  parameter-grid methodology already validated for the guard/crash-trigger/
  joint-stress work (see `run_joint_stress_validation.py` as the template).
  Separately: plain yield-curve inversion (T10Y3M/T10Y2Y) was considered
  and rejected as a standalone signal -- already tested, found to add zero
  discriminating power beyond Core 3 for this asset set.

- ~~Self-updating Google Calendar integration for dated reminders~~ --
  **DROPPED 2026-07-03.** Superseded by the finalized ops-notification
  scope below: AVGO + LLY earnings reminders go via Telegram directly
  (data-driven, reusing `fi_tracker.py`'s existing yfinance lookup), which
  covers the actual need ("don't miss the print") without the GCP
  Workload Identity Federation complexity that stalled the Calendar
  workflow (see "ON HOLD" section above). No remaining need for a
  calendar-visible entry was identified, so this is closed, not just
  paused.

## Operations notification scope -- FINALIZED 2026-07-03, not yet built

Channel split, by urgency (per the operator's own stated principle:
Telegram for urgency, email for everything else):

| Item | Channel |
|---|---|
| Guard / joint-stress / silver-GSR / opportunistic-sleeve events | Telegram |
| GSR watch-zone leading-indicator gauge (not yet designed in detail) | Telegram |
| AVGO + LLY earnings reminders (data-driven, days-to-event) | Telegram |
| FI@50 CAGR/AWAR pace digest (monthly cadence) | Email |
| Quarterly thesis re-check reminder | Email |

Known small gap when this gets built: `fi_tracker.py`'s AVGO Earnings
Checkpoint already computes days-to-next-earnings live via yfinance; LLY
needs the same lookup added (same pattern, not yet written).

Not started -- this is the scope to build against next, not a completed
feature.

## Signal-change email redesigned to lead with the action (2026-07-02, PR #17)

First version (PR #14) emailed the raw state transition only, e.g. "AVGO
guard: BASE -> DEFENSIVE" — user feedback: that doesn't tell you what to
*do*, just what changed, and it must. Fixed: `check_signal_changes.py` now
also extracts the exact `Action` line text `fi_tracker.py` already computes
and prints live (e.g. "Rotate AVGO -> Gold+LLY (Gold 52.5%, AVGO 0%, LLY
47.5%)"), and `build_actionable_message()` builds `(subject, body)` where
the body always pairs a state change with its instruction:

```
AVGO GUARD: BASE -> DEFENSIVE (trigger: CRASH, joint stress: inactive)
ACTION: Rotate AVGO -> Gold+LLY (Gold 52.5%, AVGO 0%, LLY 47.5%)
```

Subject line is also dynamic now (e.g. "Asset Universe: AVGO guard ->
DEFENSIVE") instead of a fixed generic "signal change" — the phone
lock-screen preview should already say what happened, not require opening
the email. Silver GSR gets the same ACTION treatment. Sleeve/regime-flip
changes are labeled REVIEW (no forced trade, just something to check) to
distinguish "must act" from "worth a look." LLY-stress flipping on its own
(without the AVGO guard also firing) is explicitly labeled informational --
no action follows from it alone.

Wording can never drift from the live dashboard's own instructions, since
it's extracted from the same text, not independently authored.

Live-verified via the manual `preview_email.yml` workflow (see below) with
a real simulated AVGO guard flip -- confirmed both the log output and the
actual received email matched exactly.

## Signal-change email notification added (2026-07-02, PR #14)

Turning the daily sync from "runs unattended" into "runs unattended and
tells you when something needs a decision." `sync.yml` now snapshots
`status.md` before `fi_tracker.py` overwrites it, and after commit, diffs a
curated fingerprint (AVGO guard signal + trigger, LLY-stress, joint-stress,
silver GSR signal, opportunistic sleeve status, confirmed regime flip)
between yesterday's and today's committed dashboard.

**Silent when nothing actionable changed** (the common case — no email
noise). **One-line email via Gmail SMTP when something did** (e.g. "AVGO
guard: BASE -> DEFENSIVE; AVGO guard trigger: none -> CRASH"). Deliberately
excludes price/valuation numbers, which change every day and would make
this useless as a signal — only state transitions trigger it.

Requires repo secrets `EMAIL_ADDRESS` and `EMAIL_PASSWORD` (a Gmail **App
Password**, not the real account password — Gmail SMTP rejects real
passwords outright). Both added 2026-07-02. Failure to send is non-fatal
(logged, doesn't fail the sync job) — `check_sync_health.py` is still the
thing responsible for failing loudly on genuinely broken syncs.

New: `check_signal_changes.py` (fingerprint extraction + diff, also
CLI-usable standalone), `notify_signal_changes.py` (email send, wraps the
above). 16 new tests. 81 passing project-wide.

**Deliberately out of scope**: the one-off Sept 3 AVGO earnings-checkpoint
reminder is not part of this pipeline — it's a single dated event, not a
recurring signal, better served by a calendar entry than folded into daily
diffing logic.

## FI@50 pace tracker bug fixed (2026-07-02, PR #13)

`fi_pace()` in `src/asset_universe/portfolio.py` was computing "Required
CAGR" and "Projected @ AWAR" via pure compounding of current TPV only —
**silently ignoring the confirmed 6,000 kr/month ongoing contributions**,
even though that adjustment was already derived once (off-system, during
the 2026-07-02 rebalance sizing exercise: required CAGR 24.88% → 22.06%,
"the single largest lever found in that analysis") and never wired back
into the live daily dashboard. Every run was reporting a harsher "BEHIND
pace" figure than reality.

Fixed: `config/portfolio.toml`'s `[fi]` section now has
`monthly_contribution_sek = 6000`; `fi_pace()` solves for required CAGR and
projects future value via a proper annuity-due formula (`brentq`, `scipy`
already a dependency) instead of ignoring the contribution term entirely.
Falls back to the exact old pure-compounding formula if
`monthly_contribution_sek` is 0 or absent — not a behavior change for
zero-contribution scenarios. Also fixed the same omission in the
Bear/Conservative/Base/Bull scenario table in `fi_tracker.py` (was using
`math.log` pure-compounding for "years to FI", now uses
`portfolio.years_to_reach_target()`, contribution-aware).

**Effect (2026-07-02 snapshot):** Required CAGR +25.1% → +22.2%, margin
-6.6% → -3.0%, Projected @ AWAR 7.1M → 10.1M kr. Still behind pace, but
meaningfully less behind than the tracker was reporting.

6 new tests (`tests/test_fi_pace.py`): zero-contribution regression
(reproduces the old formula exactly), contributions lower the required-CAGR
bar (not just "differ"), magnitude sanity check against the known
24.9%→22.1% figure, FV/years-to-target round-trip. 70 tests passing
project-wide.

## Current strategy ("Strategy D" + crash guard, validated 2026-07-01)

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
- **AVGO fast-crash trigger (PR #9, merged 2026-07-01)** — the 200d SMA is a
  lagging indicator that can't react to a sharp, fast break. Tested via a
  TXN analog (AVGO IPO'd 2009, never saw a dot-com-style crash; TXN's full
  2000-2026 history includes one) — SMA-only guard took -35.3% MaxDD on the
  analog. Fix: if AVGO drops >10% over 5 trading days, the guard fires
  immediately regardless of the SMA. Validated on a 20-cell grid (window ×
  threshold) — every cell matched or beat SMA-only on both AVGO's own data
  and the TXN analog. Result: AVGO CAGR +37.1%→+40.5% (MaxDD unchanged
  -16.8%), TXN-analog MaxDD -35.3%→-30.0%. This -30.0% conservative MaxDD is
  what the final rebalance sizing (below) is built on.
- **Silver GSR tactical** — T1 (GSR>=83.36, fallen >=5% from 60d peak) adds
  +12% silver funded from AVGO; T2 (GSR>=86.45) adds +17%; exit at
  GSR<62.56. Currently INACTIVE.
- **AVGO/LLY joint-stress escalation (PR #12, merged 2026-07-02)** — LLY's
  diversification vs AVGO is regime-dependent, not stable (tested
  2026-07-02): real in liquidity crashes (COVID, correlation near 0), absent
  in macro/trade-driven selloffs (2022 rate hikes +0.32 correlation, 2025
  tariff shock — LLY fell alongside or worse than AVGO). When LLY
  independently trips the *same* validated guard logic (200d SMA / 5d-(-10%)
  ROC — no new parameters, just checking if LLY trips the already-proven
  AVGO trigger too) while AVGO's guard is also active, that's the
  diversification actually breaking down — escalate to **100% Gold** (AVGO
  0%, LLY 0%; silver still funds from Gold if T1/T2 active). Validated via
  the same TXN-analog methodology as the crash trigger: monotonic
  improvement with more Gold on both AVGO's own history and the TXN analog
  (not a curve-fit interior spike) — AVGO actual Calmar 2.407→2.957, TXN
  analog Calmar 0.824→1.028. Rare (2.6% of days on AVGO's history, 15.9% on
  the harder analog) but meaningfully improves CAGR/MaxDD/Calmar on both
  when it fires. See `run_joint_stress_validation.py`.
- **AVGO earnings checkpoint** (`fi_tracker.py`, after the guard block) —
  prints fwd/trail EPS ratio (baseline 3.23x, vs 1.1-1.5x for quality peers)
  and next earnings date. Manual judgment call after each print, not an
  automated rule. Next earnings: 2026-09-03.

Combined backtest (2009-2026, 10bps TC): CAGR +37.1%→+44.0% (with crash
trigger + joint-stress escalation), Sharpe 1.967, MaxDD -14.9%, Calmar
2.957 (strategy "E" in `run_combined_system.py`; SMA-only-guard baseline
was Calmar 2.205, see above for the layered progression).

## Rebalance — DECIDED 2026-07-02, execution in progress

Target: **Reactor Core 83.3% / War Chest 4.5% / Home Base 12.2%** (of total
TPV, not just Reactor Core). Method: drawdown-ceiling sizing —
confirmed **-25% max drawdown tolerance** ÷ **-30.0% conservative MaxDD**
(crash-guard-improved TXN-analog figure above) = 83.3%. Also confirmed:
**6,000 kr/month contributions**, account is **all ISK** (flat annual tax,
not per-trade capital gains — banded/frequent rebalancing is tax-free).

Execution status:
- **Gold leg: DONE (2026-07-02).** Bought 54 shares PPFB.DE, funded from
  Home Base (Spiltan Räntefond). Live in `config/portfolio.toml` (304
  shares).
- **Remaining legs (sell Silver/WMT/CCJ/VRT, buy AVGO/LLY, top up War
  Chest): NOT yet executed.** Deliberately sequenced to happen *after* the
  HWM tactical position exits (time exit 2026-07-25, or earlier on MA50
  breach / $271 hard stop) — let HWM's own exit rule run its course first,
  then fold proceeds into the rest of the rebalance.
- **The one open sub-decision: lump-sum vs. staged/tranched entry for the
  ~430k kr AVGO buy** (roughly 5-6x the current position). Not resolved as
  of this writing. Matters more than it looks — the 2026-07-01 valuation
  review flagged AVGO at 63x trailing P/E, "priced for near-perfection."
  Resolve deliberately before executing, don't let it happen by default
  when HWM closes.

Full kr-denominated trade list and the annuity-adjusted required-CAGR math
(22.06% with contributions vs 24.88% without) are in the operator's personal
memory — ask if you need the exact numbers re-derived at execution-time
prices.

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
4. **Rebalancing decision** — DECIDED 2026-07-02 (see "Rebalance" section
   above): target 83.3/4.5/12.2, Gold leg executed, remaining legs sequenced
   post-HWM. **Only open sub-question: lump-sum vs. staged AVGO entry** —
   still unresolved, resolve before executing.
5. **HWM tactical exit** — time exit by 2026-07-25 (or MA50 breach / $271
   hard stop, whichever first). Blocks the remaining rebalance legs. Check
   `run_entry_screen.py` output / Avanza MA50 daily.
6. **AVGO conviction tests** — deferred until the 200d guard fires and stays
   active (tripwire). Not yet triggered.
7. **Valuation screen** — generalize the trailing/forward EPS-ratio check
   (used for AVGO) into a reusable script across the ~70-asset
   quality-filtered universe. Monitoring tool, not an AVGO-replacement
   search — doesn't override item 6's tripwire. Not yet built.

**Other gaps flagged 2026-07-01, updated 2026-07-02:**
- Account type **resolved**: all positions are ISK (flat annual tax, not
  per-trade capital gains).
- **FX hedging still open.** Gold=EUR-listed (PPFB.DE, Xetra), AVGO/LLY/WMT=
  USD, FI@50 tracked in SEK. Reconciled 2026-07-02: SEK value = gold(USD) ×
  EURUSD × EURSEK, a genuine two-hop chain (not a data bug) — one hop more
  than the rest of the book. Fix identified: **IGLN** (LSE, USD-denominated)
  shares the exact same ISIN as PPFB.DE (IE00B4ND3602) — same fund, same
  bullion, same custodian, would collapse the chain to one hop. Not yet
  confirmed tradeable on Avanza — check before the next Gold touch-point.
  Backtest evidence (15y, 2011-2026) says don't overreact to this either
  way: unhedged gold(SEK) beat a fully-hedged gold(USD)-only proxy on CAGR
  (+10.0% vs +6.85%), Sharpe (0.56 vs 0.44), *and* MaxDD (-36.9% vs -44.4%)
  over the full period — hedging would have been strictly worse, not a
  wash. A tested USD/SEK 200d-MA tactical overlay also underperformed
  buy-and-hold on Sharpe — rejected, same fate as the retired RY signal.
- **AVGO/LLY correlation in a broad drawdown — tested, still not fully
  resolved.** Full-period daily-return correlation is +0.21 (real but
  modest). It's regime-dependent, not stable: rose to +0.32 during the 2022
  rate-hike growth selloff (correlation increasing exactly during macro
  stress), fell to ~0 in 2025-26 when each stock ran on its own idiosyncratic
  narrative. On AVGO's 10 worst days, LLY decoupled during the COVID crash
  (real ballast) but fell alongside or worse than AVGO during the April 2025
  tariff shock (no ballast). Conclusion: LLY hedges liquidity/structural
  crashes, not macro/trade-driven risk-off — diversification is real but
  narrower than the "different sector" framing suggests.
