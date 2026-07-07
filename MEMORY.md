# MEMORY.md — Asset Universe handoff doc

Personal quant-finance infra for a Swedish investor's FI@50 plan. Read this
before starting work; update it when you finish a meaningful chunk. Deeper
history (full derivation of the base weights, walk-forward backtests, rotation
sleeve tests that were tried and closed, correlation analysis, etc.) lives in
the operator's personal memory file, not in this repo — ask if you need it;
this file is meant to be self-contained for day-to-day continuation.

## Heartbeat (healthchecks.io) wired in (2026-07-07, PR #55) -- closes the last alert-robustness gap

The one item deferred from the alert-robustness hardening below (needed
the operator's own signup). Operator created a free healthchecks.io check
("asset_universe") same day. `HEALTHCHECKS_PING_URL` added as a repo
secret (URL confirmed reachable via a direct curl before wiring). `sync.yml`
now curls it as the last step in the job -- only reached if every prior
step succeeded, so a dead/broken pipeline shows up as a missed ping on an
independent third-party service, not just inside GitHub. `|| true` on the
curl so a transient healthchecks.io-side hiccup never fails the sync job
itself. Live-verified via a real `workflow_dispatch` run (suppressed
notify) before merging -- heartbeat step confirmed to fire.

**One thing left for the operator, not urgent:** the check's default
"Period: 1 day" will false-alarm every weekend, since the pipeline only
runs weekdays (same Fri-evening -> Mon-morning gap `check_sync_health.py`
already special-cases). Fix is a single dashboard field -- set Period to
~2.5 days / 60h. Flagged to the operator, not yet confirmed done.

## Alert-robustness hardening (2026-07-07, PR #53) -- prompted by the operator going offline for several days

Live audit of the whole notification chain surfaced three real weaknesses
(not hypothetical -- one of them fired for real during this same session,
see below):

1. **Two silent gaps already happened** (HWM sleeve-state, scipy
   dependency) before being caught by accident, not by any check.
2. **The notifier can't tell a real event from a bookkeeping correction.**
   Confirmed live: re-triggering `daily-sync` to verify the HWM sleeve-
   state fix (see below) caused a genuine Telegram send of "Sleeve CLOSED
   -> OPEN" -- a false positive, since HWM had been open since 2026-06-24
   and nothing about the position actually changed.
3. **Single delivery channel, single point of failure.** Telegram-only,
   no retry, no fallback -- one API hiccup and a real guard flip/stop
   breach silently doesn't reach anyone.

**Built and merged (PR #53):**
- `notify_signal_changes.py`: Telegram send now retries twice (2s backoff)
  before falling back to email (`EMAIL_ADDRESS`/`EMAIL_PASSWORD` -- the
  same Gmail App Password secrets from the pre-Telegram pipeline, still
  provisioned, now reused as a backup channel instead of the primary).
  Only if *both* channels fail does the job fail (GitHub's own failure-run
  email is a third, independent fallback).
- `SUPPRESS_NOTIFY` workflow_dispatch flag -- skips notification entirely,
  checked before the diff even runs. For any future run that's a state
  correction rather than a real event (exactly the gap that caused #2
  above). Should be set to `true` whenever manually re-running `daily-sync`
  to verify a fix that changes tracked state.
- 4 new tests (retry-then-succeed, retry-exhausted-then-email-fallback,
  both-channels-fail, suppress-flag). 187 passing project-wide.
- Live-verified on a branch via real `workflow_dispatch` against actual
  secrets in CI before merging -- not just local mocks.

**Explicitly deferred, not built (needs the operator's own action):**
external heartbeat / dead-man's-switch (e.g. healthchecks.io) -- would
catch a full GitHub Actions outage, which nothing today can (both the
pipeline and its watchdog live inside GitHub). Needs a third-party account
signup, so it's config-only whenever the operator has 2 minutes: add the
ping URL as a repo secret/step, wire once, done. Auto-remediation
(retry/fallback above) was prioritized first since it needed no new
external dependency and covers the more probable failure class (a
transient API/delivery hiccup, not a full platform outage).

**Design principle applied, worth repeating:** auto-remediate every
*mechanical* failure class (transient API errors, a missed cron fire --
already self-healing via the existing watchdog) so a human is only paged
for things that genuinely need one. The one thing that can never
self-heal is total pipeline death -- a dead system can't resurrect
itself, which is exactly why a human-facing heartbeat is still the right
tool for that one specific case, not more automation trying to fix a
dead thing.

## Session 2026-07-07 — sleeve entry reconstruction, HWM state gap, risk alerting

**AVGO guard constructiveness + dip-buy overlay, discussed not built.**
Revisited whether the guard (200d SMA + crash trigger + joint-stress) is
genuinely constructive: yes, per-year OOS record (`avgo_guard_oos.csv`)
shows it matched or improved Calmar in 17 of 18 years, with the real wins
concentrated exactly where you'd want them (2020 COVID Calmar 1.39->3.21,
2022 bear 0.001->0.87, 2018 vol spike 0.77->3.66) -- not curve-fit, since
the crash trigger and joint-stress escalation were both validated on a TXN
analog (a crash type AVGO itself has never lived through) and both showed
monotonic, not spiky, improvement. Separately discussed a "buy the dip"
overlay for AVGO/LLY re-entry -- concluded the ~5pp ceiling (the two years
guard cost raw CAGR: 2009, 2026 YTD) doesn't justify the added whipsaw risk
that would fight the guard's own purpose. **Not built, correctly**: pure
discussion, no code changed.

**Sleeve exit-duration backlog item closed (PR #45).** PR #40 had
disclaimed its own exit-duration sweep because it tested the wrong
population (all regime-matched momentum dates, not the sleeve's actual
gated entries) and believed the earnings gate couldn't be reconstructed
point-in-time ("yfinance only exposes the current earnings calendar").
**That claim was wrong, not just unverified** -- confirmed directly:
`yf.Ticker("AVGO").get_earnings_dates(limit=60)` returns the full
historical record back to 2009-12-03; `_next_earnings()` in `engine.py`
just filters it to `>=today`. With that unblocked, built
`run_sleeve_entry_reconstruction.py`: reconstructs all 4 of
`screen_tactical()`'s gates point-in-time (reusing
`run_sleeve_backtest.py`'s no-lookahead walk-forward ranking for gate 1),
generates the real ~4,300-entry declustered gated-entry population
(2009-2026), and sweeps duration against it. Result: annualized median
return *declines* with duration (26.5% at 15d down to ~20-22% at 45-90d)
-- edge looks front-loaded, if anything suggesting `TIME_EXIT_DAYS=30` is
already on the generous side. **Not a verdict** -- still a population-level
stat, not a compound-exit simulation (MA50 breach / hard stop would
truncate many real trades before the time exit ever binds); that stays a
separate, bigger follow-on. Self-check reproduces PR #5's ground truth
(HWM clears all 4 gates as of 2026-06-24). `forward_return()` hand-verified
against real price data. 171 tests passed pre-merge.

**HWM sleeve-state gap found and fixed (PR #46) -- the actual reason for
"no Telegram messages from the sleeve."** `config/sleeve_state.toml` had
shown `open=false` since its creation (PR #6) -- HWM was genuinely entered
2026-06-24 and MEMORY.md had been tracking it against a real exit rule,
but the state file that `compute_exit_triggers()` needs was never
populated via `--open`, so there was nothing to monitor and therefore
nothing that could ever notify, regardless of price action. Backfilled
with the real entry (2026-06-24, $276.93, 11 shares, HIGH/TIGHT regime, FX
9.7344 SEK/USD and capital ~29,653 kr both derived from that date's actual
data) -- **not** via `--open`, which stamps *today's* date and would have
thrown the 30-day time-exit off by two weeks. Resolved the $258-vs-$271
sheet discrepancy along the way: $258 was the sheet's manually-noted MA50
(informational), $271.39 is the real binding hard stop -- consistent with
MEMORY.md's existing "$271 hard stop" note.

**Local data staleness found and guarded against (same PR #46) --
separate from the above, and separate from the live pipeline.** While
investigating HWM, found the local `data/` parquet cache (gitignored,
never synced anywhere) was a full week stale (2026-06-30) with nothing
checking or warning about it -- nearly produced a wrong "HWM has breached
its stop" conclusion mid-session. **Confirmed the live GitHub Actions
pipeline was never affected** -- it restores/refreshes its own cache every
scheduled run, independent of this machine; `check_sync_health.py` and the
watchdog both reported healthy throughout. Added
`check_local_data_freshness.py`: checks a reference ticker's latest date
against the most recent trading day and auto-refreshes if stale, meant to
be run first in any future local ad-hoc analysis session.

**All non-sleeve triggers directly re-verified live, not assumed (per
explicit request to "be clear").** Ran `extract_fingerprint()` against the
actual live `status.md` (committed by the pipeline that morning) -- every
field (AVGO guard/trigger, joint stress, LLY stress, silver GSR, regime
flip, both earnings reminders + latest-quarter/beat-streak/guidance-trend)
parsed a real value, none degraded to `unknown`. Confirmed genuinely live,
not just re-trusting the 2026-07-06 audit's claim.

**Sleeve risk state wired into the Telegram alert diff (PR #47) -- the
deeper gap even after the state fix.** `check_signal_changes.py` only ever
diffed the bare `OPEN`/`CLOSED` word -- `compute_exit_triggers()` and
`compute_tripwires()` were already computing a stop breach, an approaching
time exit, and tripwire flags, but none of those values were diffed, so a
real hard-stop breach on a held position would sit silently in
`status.md`'s text with nothing pushed to Telegram (closing only happens
via a manual `--close`, run after actually selling -- nothing closes a
position automatically). Added `sleeve_risk_state()` (`CLEAN` / `TRIPWIRE`
/ `TIME-EXIT-DUE` / `STOPPED`, in that priority order) to
`run_entry_screen.py`, printed alongside a new `Current price` line in
`sleeve_daily_summary()`, and wired into the alert diff -- `ACTION`-framed
for a stop breach or arrived time exit, `REVIEW`-framed for a softer
tripwire. **Real display bug fixed along the way**: the `Time exit` line
was labeling a constant (days from *entry* to exit, always ~30) as "Xd
left", which would have shown the same number every day regardless of the
actual date -- added `time_exit_days_remaining`, computed from today, and
switched the display to use it. Verified end-to-end against real live
HWM data, not just the test fixtures. 183 tests passed pre-merge.

**Net effect of this session, in plain terms:** HWM's actual exit
conditions are now genuinely under automated watch for the first time
since the trade was taken, and a real breach would now actually reach
Telegram. The live guard/joint-stress/silver/regime/earnings pipeline was
independently re-confirmed healthy, not just assumed from the prior
audit. **Confirmed by design, not a gap:** new-opportunity candidate
suggestions are fully paused while HWM is open -- `sleeve_daily_summary()`
doesn't even run the screening logic while a position is held (position
cap = 1). That resumes automatically once `--close` is run after HWM is
actually sold.

## Session 2026-07-06 — sync reliability, LLY parity, EPS ratio fix, VRT->AVGO trade

**Sync watchdog (PR #26).** `daily-sync`'s Monday 06:00 UTC cron fire was
silently delayed ~4h with no error surfaced -- caught by chance while
checking a live price. Fix: `sync-sheet` (fires every ~2h, never missed a
slot) now also checks whether `daily-sync` has gone stale and re-triggers
it via `workflow_dispatch` if so. Silent on self-heal, Telegram alert only
if the re-trigger itself fails -- explicit user preference: no notification
for "worked as expected," only for "needs a human." Along the way, fixed a
real bug in `check_sync_health.py`: freshness was checked via filesystem
mtime, which `actions/checkout` resets on every job -- would have made the
watchdog always see "fresh" since it runs in a different workflow than the
one that writes `status.md`. Now uses git commit time instead, with mtime
as a fallback outside a git repo (tests). Not yet tested by a real miss --
this morning's incident turned out to be a GitHub-side delay, not a true
drop (the watchdog PR merged after that run's own late completion).

**"Next kr" routing (PR #28).** Recurring contributions needed a rule for
where new capital goes, distinct from the guard's hold-vs-rotate decision
for capital already invested. `next_contribution_target()` in
`next_contribution.py` routes to whichever of Gold/AVGO/LLY is furthest
below its own current target weight (`WEIGHTS`/`JOINT_WEIGHTS` from
`run_combined_system.py`, already regime/guard-aware) among assets whose
gate is open. Silver excluded -- own trigger, own funding mechanism.
Deliberately pull-only in `status.md`, not pushed -- the one time the
destination actually changes (a gate flipping) is already covered by the
existing guard-change Telegram alert.

**LLY valuation checkpoint + earnings reminders for both tickers (PR #29).**
LLY never had AVGO's fwd/trail EPS-ratio checkpoint (backlog since
2026-06-30) -- built it, same structure as AVGO's. Separately, real gap
found: this file previously claimed earnings reminders already went via
Telegram (cited as why Google Calendar was dropped) -- that was never
actually built. `earnings_reminder.py`'s `earnings_reminder_state()` is a
binary DUE/not_due flag (deliberately not a day-count, which would re-fire
daily inside the window) that flips once when earnings come within 7 days
-- reuses the existing diff-based `check_signal_changes.py` -> Telegram
pipeline as-is, no new send logic.

**EPS ratio GAAP/non-GAAP mismatch fixed (PR #30) -- and a process gotcha
worth remembering.** The original AVGO checkpoint compared `trailingEps`
(GAAP) to `forwardEps` (non-GAAP consensus) -- inflates the ratio for any
company with a large GAAP/non-GAAP gap. AVGO's VMware-acquisition
amortization creates exactly that gap. Normalized (TTM actual EPS from
`earnings_history`, +1yr estimate from `eps_trend`, both non-GAAP): AVGO's
real ratio is **2.39x**, not 3.22x. `eps_ratio.py` does this, validated
against LLY (1.58x naive -> 1.51x normalized, barely moves -- confirms the
effect is AVGO-specific, not a bug in the method). **Process gotcha: this
PR was opened, verified, and reported as done in conversation, but never
actually merged -- sat open for ~2h while later PRs (#28, #29, #31) landed
on top of a master that still had the old, unfixed ratio.** Caught and
merged same session when building on the fix again. Lesson: "PR opened"
and "PR merged" are different states -- confirm merge status before
treating a fix as live, especially across a long session with many PRs in
flight.

**Peer-set correction on the same question (not yet a code change, just an
analysis worth recording):** the original outlier framing (2.39x vs. a
1.1-1.5x "quality peer set" of AAPL/GOOG/MA/TDG/MNST/ANET/COST) compared
AVGO against companies that don't share its AI-capex growth story at all.
Checked against actual AI/semi peers (same normalized method): MU 3.32x,
AMD 2.88x, **AVGO 2.39x**, NVDA 2.19x, MRVL 2.04x, TSM 1.69x, ASML 1.67x,
ANET 1.41x, QCOM 0.92x. AVGO is solidly mid-pack among real comparables --
below MU/AMD, in line with NVDA/MRVL, above TSM/ASML/ANET. The "clear
outlier" framing that drove a lot of this session's back-and-forth was
itself partly a peer-selection artifact, on top of the GAAP/non-GAAP one.

**Realized-growth regime research study (PR #31, `sec_edgar.py` /
`eps_growth_regime.py` / `run_eps_growth_regime_study.py`).** Explores
whether AVGO's growth premium historically precedes good or bad forward
returns, using SEC EDGAR's XBRL API (free, ~10yr depth, validated against
yfinance to within a 1-cent rounding artifact -- real gotcha found: many
10-Ks only tag annual EPS, not a discrete Q4, which has to be derived as
annual minus the other three quarters). Explicitly conditions on REALIZED
past growth, not analyst-estimated forward growth -- historical
point-in-time consensus data isn't available anywhere free (I/B/E/S/
FactSet are paid, institutional-only). **Honest result, not decision-grade:**
a quality-only peer set showed misleadingly reassuring numbers (survivorship
bias -- the peer set was pre-selected for having succeeded). Adding a
deliberate "growth disappointment" cohort (INTC/PYPL/ZM/PTON) and switching
to revenue growth (EPS growth is inflated by AVGO's own GAAP distortion,
same root cause as the ratio fix above) shows a real cautionary skew in the
HIGH->MID/LOW deceleration case -- negative median at 63d, ~coin-flip win
rate at 252d -- but N=12 is too thin to be conclusive even pooled across
10 tickers. Full fix needs SEC's complete filer universe including
delistings (survivorship-bias-free), a separate, bigger piece of work --
delisted-company price history isn't in the parquet store or yfinance.
Not built. Net effect: doesn't override the sizing decision (built on
risk-capacity/guard-coverage, not on an assumption growth never
decelerates), but raises the stakes on actually using the Sept earnings
checkpoint as a real gate, not a formality.

**VRT -> AVGO trade executed and confirmed (2026-07-06).** Sold Vertiv in
full (31 -> 0 shares, unconditional exit regardless of price -- excluded
from the target base on the merits), routed proceeds into AVGO (21 -> 49
shares, +28) rather than splitting with LLY -- consistent with "next kr"
routing (AVGO's RC gap dwarfed LLY's). Confirmed via the Google Sheet
`config` tab (gid=1133887937, the exact tab `sync_sheet.py` reads) and a
manually-triggered `sync_sheet.yml` run, since the edit postdated the last
scheduled sync. **Gotcha for future sessions:** the "FI@50" Google Sheet
has ~19 tabs covering unrelated things (a separate crypto/thematic ETF
portfolio, fee calculators, an LLM prompt template, etc.) -- Drive API
tools (`read_file_content`, CSV export) only reach the default/first tab,
not a specific gid. To reach a specific tab, export the whole workbook as
`.xlsx` (`download_file_content` with the OOXML spreadsheet mimeType) and
read it with openpyxl by sheet *name* -- gid isn't preserved in xlsx, but
tab names are. The live automation itself hits Google's direct CSV export
URL with an explicit `gid` param, which does support tab targeting (see
`sync_sheet.py`'s `SHEET_ID`/`GID` constants) -- only the generic Drive
export tools have this limitation, not the pipeline itself.

**AVGO's remaining rebalance tranche (funded by WMT/CCJ/HWM proceeds, still
sequenced to wait for HWM's exit by 07-25) is now also explicitly gated on
the 2026-09-03 earnings print** clearing against the guided AI-revenue
path (not just guard status) -- new condition added this session given the
deceleration-risk finding above. Watch specifically: AI revenue pace vs.
guided $56B FY26/$100B FY27, whether the 4-for-4 beat streak continues,
forward guidance direction (has been revising up for 90 days), and any
Anthropic/OpenAI contract-timing commentary.

**AVGO's valuation reassessed twice more, same day (peer-set correction).**
The 2.39x normalized ratio, checked against genuine AI/semi peers instead
of the mixed "quality" set (AAPL/GOOG/MA/TDG/MNST/ANET/COST), is mid-pack:
MU 3.32x, AMD 2.88x, **AVGO 2.39x**, NVDA 2.19x, MRVL 2.04x, TSM 1.69x,
ASML 1.67x, ANET 1.41x, QCOM 0.92x. Separately, on absolute valuation
(not growth-embedded ratio): AVGO's forward P/E (19.4x) and PEG (0.41) are
both on the *cheap* side of that same peer group -- only NVDA/QCOM have a
lower forward P/E, only MU has a lower PEG. Net: the "priced for
perfection" framing that drove a lot of this session's back-and-forth was
substantially a peer-selection and accounting-mismatch artifact, not a
reflection of AVGO actually being expensive vs. real comparables. Decided
**not** to add PEG/forward-P/E tracking to the daily checkpoint -- these
barely move day-to-day except through price (which the guard already
tracks), and without peer context or a validated trigger it'd be a number
nobody looks at, not real signal. Stays a periodic, triggered exercise.

**Operational reliability push, prompted by the user's actual long-term
goal ("urgent actionable info must reach me immediately, and I must be
able to act on it from anywhere").** Three concrete pieces:

1. **Telegram delivery failures now escalate for real actionable events**
   (`notify_signal_changes.py`). Previously any send failure was silently
   logged and swallowed -- fine for the manual test diagnostic, but meant
   a genuine guard flip / silver trigger / earnings-due event could fail
   to deliver with nothing surfacing it. Now a failed send for an actual
   actionable change exits non-zero, failing the Actions run so GitHub's
   own failure-run email is the fallback channel -- same escalation
   pattern as the sync watchdog. The diagnostic path stays non-fatal.
2. **Full pipeline audit for the same silent-failure class.** Found one
   real, concrete gap: if `current_regime()` raised (caught internally in
   `fi_tracker.py`, not crashing), the Macro Regime and Portfolio Signals
   sections printed `[regime unavailable]` / `[signals unavailable --
   ...]` -- neither matched `check_sync_health.py`'s `"[unavailable"`
   signature, and since the script didn't crash (exit 0), **nothing would
   have caught it** -- no exit-code signal, no content signal, and the
   actual exception message was being discarded entirely. Fixed:
   standardized both messages to the same `"{Section} : [unavailable --
   {reason}]"` format every other section already uses. Rest of the
   pipeline audited and found sound: `run_regime_alert.py`/
   `run_optimizer.py` have no swallow pattern (crash -> Traceback,
   already caught, or explicit `sys.exit(1)`); `sync_sheet.py` already
   escalates correctly. A few minor, non-gating swallows in
   `run_entry_screen.py` (VIX review, company-name lookups) left as-is --
   informational only, not part of any actionable decision path.
3. **Mobile trigger path live-verified, from two independent vantage
   points** -- not just the mobile app's self-report. Dispatched
   `sync-sheet` via `gh workflow run` from Claude Code mobile, confirmed
   completed/success both from the mobile session's own check and
   independently from this session via `gh run view`. Confirms the full
   loop: alert reaches phone -> can trigger a fix from phone -> verified
   it actually ran against the real repo.

**Net effect: the notification/escalation chain covering guard flips,
silver triggers, joint-stress, earnings-due reminders, sync staleness,
and now regime-computation failures has no known silent-failure gaps left
in the parts that actually drive decisions.** Cadence is twice-daily
(06:00/20:30 UTC), not instant -- worth remembering that's a deliberate
match to the guard's own 5-day-ROC/200d-SMA design, not a latency gap to
close further.

**Process note for future sessions, worth repeating from earlier:** PR #30
sat merged-but-not-actually-merged for ~2 hours earlier this same session
before being caught. Today's later PRs (#32, #33) were pushed to their own
branches and merged properly each time -- but the very first memory update
of this session (the section above this one) was mistakenly pushed
**directly to master**, skipping the branch/PR step every other change
this session went through. Caught and named at the time, not hidden.
Two reminders in one day: "PR opened" isn't "PR merged," and "docs-only"
isn't an exemption from the branch/PR discipline either.

## Signal-change notifications migrated Gmail -> Telegram (2026-07-03)

Per the finalized ops-notification scope (see below): urgent items go via
Telegram now, not email. `notify_signal_changes.py` rewritten --
`send_email()` replaced with `send_telegram()` (plain `urllib.request` POST
to the Bot API, no new dependency). Requires `TELEGRAM_BOT_TOKEN` (secret)
and `TELEGRAM_CHAT_ID` (variable -- `8990937151`, not sensitive, just an
identifier). `sync.yml`'s `workflow_dispatch` input renamed `test_email` ->
`test_telegram`. `preview_email.yml` renamed to `preview_notification.yml`
and updated to the same Telegram creds -- also fixed a latent bug found
during the migration: its diff-preview step still referenced `LABELS`,
which `check_signal_changes.py` stopped exporting back in the PR #17
actionable-message redesign (silently broken since 2026-07-02, never
actually re-run until now). Bot: **@A_Sheetsbot** ("FiBot"). Live-verified
via a real Telegram send before trusting it, same standard as everything
else in this project.

Email is not going away entirely -- it's still the intended channel for
the FI@50 pace digest and quarterly thesis re-check (not built yet, see
"Operations notification scope" below). `send_email`/Gmail App Password
setup docs from 2026-07-02 are historical record for that future work, not
currently wired to anything.

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

## Overnight session 2026-07-06 -- three items built; #39 and #43 (docs) now merged, #40/#41 still open

Requested explicitly: build all three, leave every PR unmerged for
morning review, don't touch live money-routing or change any live
constant automatically. All three respected that boundary.

**PR #39 -- record earnings verdict. MERGED 2026-07-06 (commit 4f19b55).**
`earnings_verdict.py` / `record_earnings_verdict.py` -- CLI records the
judgment call (AI revenue vs. guided pace, contract-timing commentary)
formed after actually reading the release/call, shows on
`fi_tracker.py`'s dashboard from then on ("Last verdict: ..."). Intended
workflow, documented in both modules: Claude reads the release, drafts
the verdict, user confirms, THEN it's recorded -- not something to fill
in independently. Not wired to gate money-routing yet (deliberate --
that's a bigger decision for later). Live-smoke-tested end to end
(recorded a real test verdict, confirmed display, removed the test
artifact before committing). 11 tests. Merged after rebasing onto
master and a clean full-suite run (161 passed, no conflicts).

**PR #40 -- sleeve exit-duration sensitivity.** Tests whether
`TIME_EXIT_DAYS=30` (`run_entry_screen.py`) is validated or just
inherited from the HWM precedent. **Real methodological bug caught and
fixed mid-build**: raw per-trade return trivially increases with holding
period for any generally-appreciating stock -- comparing 15d/30d/60d/90d
windows on raw return would always favor the longest one regardless of
whether it's actually better. Added proper (compounding) annualization.
**Deeper population-mismatch bug caught after that (by the user, not by
me) and tightened per explicit instruction ("yes, tighten it")**: this
measures ALL regime-matched dates for top-ranked momentum names, which is
NOT the same population as the sleeve's actual gated entries (MA50 not
extended, momentum conditioning, RS-vs-benchmark, earnings clear) --
those are a materially narrower set, and a dip-entry vs. a random date in
an ongoing uptrend are not the same setup. The original "90d beats 30d"
framing (even hedged as "directional only") implied this test says
something about whether 30d is right for the sleeve's real trades -- it
doesn't, one way or the other. Report output rewritten to drop the
"winner" framing entirely: leads with the population-mismatch caveat,
states the numbers are for pipeline verification only, and explicitly
says not to use them to justify changing `TIME_EXIT_DAYS`. Properly
answering the real question needs `screen_tactical()`'s 4-gate entry
logic (`engine.py`) reconstructed at each historical as-of date (it's
currently built around today-only values, `_date.today()` /
`prices.iloc[-1]`) -- bigger, separate task, logged as a NEXT STEP in the
script's own output, not started. Report-only, doesn't touch the live
constant. 10 tests (unchanged by the tightening -- it only touched report
framing/docstrings, not the underlying calculation).

**Correction (2026-07-07): the "yfinance only exposes CURRENT earnings
calendar" claim above was wrong, not just unverified.** Re-checked
directly against the raw API: `yf.Ticker("AVGO").get_earnings_dates(limit=60)`
returns the complete historical earnings-date record back to 2009-12-03
(AVGO's IPO era) -- 69 rows, not just the next upcoming one. The
limitation was actually in `_next_earnings()` (`engine.py`), which fetches
this same data but discards everything before `_date.today()`. Point-in-time
earnings-gate reconstruction is fully possible with data already available
via the existing yfinance dependency -- no new data source needed (SEC
EDGAR filing dates were checked as a fallback and would only have given a
rough +6-8 day lagged proxy; not needed once this was found). See
`run_sleeve_entry_reconstruction.py` (PR pending), which reconstructs all 4
gates point-in-time and generates the real historical gated-entry
population this PR's own report said was still missing.

**PR #41 -- richer earnings message.** Adds total-company revenue
(actual via SEC EDGAR + TTM YoY growth, next-quarter consensus + implied
growth) alongside the existing EPS beat streak/guidance trend. **Real bug
caught before shipping**: initially used yfinance's "+1q" revenue_estimate
period for "next quarter" -- verified against the actual next-earnings
date and found "+1q" is the quarter AFTER the upcoming one; corrected to
"0q". Per explicit feedback: dropped "MANUAL REVIEW STILL NEEDED" and the
hardcoded "$56B FY26/$100B FY27" figure from both the earnings-due
reminder and the just-reported message -- a hardcoded guidance number in
a recurring alert would silently go stale if guidance changes before the
print actually happens. No "revising up/down" trend shown for revenue
(unlike EPS) -- confirmed `revenue_estimate` has no historical revision
snapshot to compare against.

**Conflict to expect when #41 merges**: PR #39 (merged) and PR #41 (still
open) both touch the AVGO/LLY Earnings Checkpoint blocks in
`fi_tracker.py` (verdict line vs. revenue lines, inserted at nearby
points). Merging master into the #41 branch will need a small manual
resolution -- combine both additions, don't just pick one side.

## Research backlog (not scheduled, not built -- ideas awaiting validation)

- **healthchecks.io check's Period needs a 1-field dashboard fix (logged
  2026-07-07, see "Heartbeat wired in" above -- heartbeat itself is
  DONE/merged, PR #55).** Default "Period: 1 day" will false-alarm every
  weekend since the pipeline only runs weekdays. Fix: set Period to ~2.5
  days / 60h on the healthchecks.io dashboard -- single field, not code.
  Not yet confirmed done. Also worth checking whenever the operator is on
  that dashboard: the check's own missed-ping alert should route somewhere
  actually watched (Telegram/SMS), not just email.

- **HIGHEST PRIORITY: broker-side (Avanza) protective stop on AVGO, once
  the rebalance deploys (logged 2026-07-07).** Everything in this system --
  guard, crash trigger, joint-stress escalation -- is alert-only. It has no
  execution capability: a real breach still requires the operator to see a
  Telegram message and manually trade at Avanza. HWM is the sole exception
  -- its $271.39 hard stop is a real resting sell order at the broker,
  which executes with zero software or human involvement, including through
  a total outage of this entire pipeline or the operator being fully
  unreachable. Once the rebalance executes and AVGO reaches its 55% target
  (currently only 16.1%, so this is explicitly deferred until then, per the
  operator's own call), the same mechanism should be considered for at
  least part of the AVGO position -- it is the only protection that
  survives total human/system unavailability, and AVGO/LLY/Gold currently
  have none.

  **Key design difference from HWM, flagged before building:** HWM's stop
  is a fixed price for a single one-shot 30-day tactical trade -- set once,
  done. AVGO's guard is dynamic (200d SMA + 5-day/-10% crash ROC, both
  move with price), so a broker-side stop mirroring it would need periodic
  re-pricing on some cadence, not a set-and-forget order. That update
  mechanism (who/what re-prices it, how often, what happens if a
  re-pricing is missed) needs to be designed before this is built, not
  assumed away.

  **Explicitly deferred, not built** -- revisit once the rebalance
  (remaining legs, sequenced post-HWM-exit) actually deploys and AVGO is
  at or near target weight.

- **Sleeve's `HARD_STOP_PCT` (2%) is a flat, unvalidated constant, not
  derived from asset volatility (logged 2026-07-07).** `run_entry_screen.py`
  computes the hard stop as a fixed `entry_price * (1 - 0.02)` for every
  sleeve candidate regardless of the asset's own normal vol -- HWM and a
  much choppier candidate would get the identical 2% cap. Set once at the
  sleeve's original design (PR #6) and never revisited. Unlike the AVGO
  guard's SMA window/crash threshold (validated via a 20-cell parameter
  grid, PR #2) or the 30-day time exit (duration sweep done, PR #45), this
  parameter has had **no sensitivity test and no vol-scaling alternative
  considered**. If tested: (a) grid 2% against neighboring flat values
  (1%/1.5%/3%) the same way the guard grid worked, and/or (b) replace the
  flat percentage with a per-candidate vol-scaled stop (e.g. a multiple of
  the asset's own ATR/historical daily move) so a calmer name and a choppier
  one aren't held to the identical risk-cap distance. **Explicitly
  deferred, not built** -- logged as a real gap, not just a style question.

- **Two-message earnings design: structured-data verdict + transcript-read
  qualitative follow-up (logged 2026-07-07, design only, no code written).**
  Goal (operator's own framing): the earnings message needs to say what's
  actually important and how forward guidance moved, not just restate the
  print -- and it needs to judge whether the new information is
  *constructive relative to the previous quarter's own guidance and
  commentary*, not just report the current numbers in isolation. Current
  automation (`earnings_reminder.py`/PR #35, PR #41's richer message)
  reports the print itself plus a generic "beat streak / guidance revising
  up" signal, but never actually diffs today's numbers against what was
  specifically guided last quarter, and has no path to the qualitative
  color (named customer contracts, competitive/regulatory commentary,
  management tone) that only shows up in the earnings call, not the
  press release.

  **Design agreed in conversation:**
  1. **Message 1 -- structured data only, same-day, zero transcript
     dependency.** EPS actual vs. consensus vs. prior guide, revenue
     actual vs. prior guide, next-quarter/FY guidance -- all from
     yfinance/SEC EDGAR, the same source `eps_ratio.py` already uses.
     **Verified directly (2026-07-07): the earnings call transcript does
     NOT contain the EPS figure at all** -- fetched the real AVGO Q2 2026
     Motley Fool transcript and confirmed EPS is absent from both prepared
     remarks and Q&A; it only exists in the press release's financial
     tables. This is why Message 1 must be structured-data-sourced, not
     transcript-sourced -- the transcript has no role here.
  2. **Message 2 -- transcript-dependent, arrives whenever available (lag
     is real and two-stage: call happens same day as the release, but
     Motley Fool's transcript publishes anywhere from a few hours to the
     next day after that -- confirmed by design, not assumed).** Covers
     only what genuinely doesn't exist anywhere else: named
     customer/contract commentary, competitive or regulatory color,
     management tone, analyst Q&A concerns.
  3. **Verdict (CONSTRUCTIVE / NEUTRAL / CONCERNING) derived from three
     comparison dimensions, not a snapshot:** (a) actual vs. the company's
     own prior-quarter guidance (beat/meet/miss, not vs. consensus), (b)
     new guidance vs. prior guidance (raised/maintained/lowered, by how
     much), (c) qualitative color this quarter vs. last quarter's
     equivalent commentary (e.g. more/fewer named contracts, new
     competitive concerns raised). Dimension (c) is the one only a
     transcript read can catch -- confirmed via the real AVGO transcript,
     where FY27 >$100B guidance was reaffirmed but now backed by named
     multi-year deals (Google, Anthropic, OpenAI, Meta) that weren't
     itemized the same way before -- a real trajectory signal, not visible
     in the numbers alone.

  **Requires new persistent state that doesn't exist yet:** a small store
  of the prior quarter's guidance figures and key qualitative highlights,
  to diff against -- nothing today remembers what was guided last time.

  **Two worked examples produced from real transcripts** (AVGO Q2 2026,
  LLY Q1 2026 -- both fetched from Motley Fool call-transcript pages) exist
  in the operator's Claude Code conversation history as a proof of concept
  for the message format; not copied here since they're illustrative, not
  final copy.

  **Explicitly unresolved, needs a decision before building:** trigger
  model -- on-demand via Claude Code (operator pings after a print, no new
  infra/cost, can course-correct a bad transcript match live) vs. fully
  automated in `sync.yml` via a direct Claude API call with web
  search/fetch tool use (needs `ANTHROPIC_API_KEY` secret, real per-call
  cost every quarter, no human catch of a bad transcript match before it
  posts to Telegram). **Do not build either path without that decision
  first.**

- **Opportunistic sleeve's 30-day time exit was never validated against
  alternative durations (logged 2026-07-06).** `TIME_EXIT_DAYS = 30` in
  `run_entry_screen.py` traces back to the informal HWM precedent (a
  judgment call made before this mechanism existed, PR #6), then got
  formalized as a fixed constant -- never backtested against 15d/45d/60d/
  90d to check 30 is actually near-optimal rather than just inherited.
  **This is directly testable with infrastructure that already exists**:
  same parameter-grid methodology already used to validate the AVGO
  guard's SMA window/crash threshold (20-cell grid, PR #2), applied to
  exit-duration instead, reusing `duration_matched_return()` /
  `_uncapped_forward_return()` (already built for the duration-matched
  win-rate work, second commit of PR #6). **Also worth checking whether a
  single fixed cap is even the right shape of rule** -- the optimal
  duration might vary by candidate (how extended the entry was, which
  regime it's in) the same way the entry ranking itself already varies
  per candidate rather than one rule for everyone. **Explicitly deferred,
  not built** -- logged as a real gap, not just a style question, since
  the current number was never actually tested against the alternative.
  **Update (2026-07-07): the blocker is resolved.** PR #40's naive sweep
  used the wrong population (all regime-matched dates, not the sleeve's
  actual gated entries) and its own report said so. `run_sleeve_entry_
  reconstruction.py` (PR pending) reconstructs all 4 gates -- including
  the earnings-clear gate, previously believed unbuildable (see the PR #40
  correction above) -- point-in-time, producing the real historical
  gated-entry population and a duration sweep against it. Still NOT a full
  compound-exit simulation (MA50 breach / hard stop / earnings buffer
  racing the time exit) -- that remains a separate, bigger follow-on if
  this sweep's results warrant it.

- **Record the earnings-day manual verdict, not just alert on it (logged
  2026-07-06).** The earnings-day checklist (`earnings_trajectory.py`,
  PR #35) automates beat streak and guidance direction, but the two
  checklist items that actually matter (AI revenue vs. the $56B FY26/$100B
  FY27 guided pace, Anthropic/OpenAI contract-timing commentary) require a
  human reading the real release/call -- confirmed not automatable, AVGO's
  full SEC XBRL fact list has no segment-revenue breakdown, only a segment
  *count*. Right now that manual judgment, once formed, has nowhere to go
  -- it lives in the operator's memory across the gap until the remaining
  AVGO tranche actually executes (which could be weeks after Sept 3, since
  HWM's own deadline is 07-25 but the earnings gate is 09-03 -- the tranche
  waits for whichever is later). Idea: a small CLI (mirrors
  `run_entry_screen.py --open/--close`) -- `record_earnings_verdict.py AVGO
  --cleared "..."` / `--not-cleared "..."` -- writing a persistent record
  (ticker, date, verdict, free-text reasoning) that (a) shows on the daily
  dashboard going forward instead of disappearing after one Telegram
  message, and (b) could gate the remaining-tranche decision and "next kr"
  routing mechanically, the same way the price guard already does, instead
  of relying on memory to enforce "wait for a cleared verdict."
  **Explicitly deferred, not built** -- logged for later.

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

- **Standalone LLY guard, independent of AVGO's state (logged
  2026-07-03).** LLY already has the identical detection logic as AVGO's
  guard (same 200d SMA / 5d-(-10%) ROC combo, reused as-is) -- but only as
  a *confirmation* input to the joint-stress escalation. A standalone rule
  (LLY rotates its own weight into Gold when *it alone* is stressed,
  regardless of whether AVGO's guard is active) has never been built or
  backtested as its own strategy variant. **This is an untested hypothesis,
  not a confirmed non-finding** -- don't assume it adds zero value just
  because LLY is a smaller slice (20% vs. AVGO's 55%) than the mechanism
  it'd be modeled on. If tested, same TXN-analog + AVGO-actual methodology
  already validated (see `run_joint_stress_validation.py` as the template).

- **External dead-man's-switch for daily-sync, independent of GitHub's own
  scheduler (logged 2026-07-06).** The sync watchdog (`check_daily_sync_watchdog.py`,
  added same day) catches a missed `daily-sync` cron fire by piggybacking
  on `sync-sheet`'s ~2h cadence -- but that's still one GitHub-internal
  cron checking another. If GitHub's scheduler has a broader hiccup that
  also skips `sync-sheet`, nothing checks anything. A third-party
  dead-man's-switch (e.g. healthchecks.io free tier) would close that gap
  fully: `daily-sync` pings it on every successful run, and the external
  service -- running outside GitHub entirely -- alerts if no ping arrives
  in time. **Explicitly deferred, not rejected**: the in-repo watchdog is
  judged sufficient for now (this is the first missed fire in ~2 weeks of
  continuous operation), and an external service adds a signup + secret +
  dependency for a failure mode that's still rare. Revisit if the
  in-repo watchdog itself is ever observed to miss a fire.

- **War-Chest-funded Silver, hybrid with AVGO/Gold-sale for any shortfall
  (logged 2026-07-06).** Silver's GSR tactical trigger currently funds
  itself by *selling* AVGO (base mode) or Gold (guard mode) -- the
  mechanism behind the validated Calmar 2.957 number. Idea: fund from
  already-idle War Chest cash instead, which would resolve an already-
  flagged tension (selling AVGO to buy Silver cuts against the guard/
  sleeve's own momentum-following philosophy -- "don't trim strength").
  **Explicitly deferred, not built**: War Chest's target size (~50k kr,
  4.5% of TPV) is likely too small to fully fund a T2 fire (~17% of
  Reactor Core, could be 150k+ kr), so it'd need to be War-Chest-first-
  then-AVGO/Gold-sale-for-the-remainder, not a full replacement -- and
  that hybrid has never been backtested (the 2.957 number assumes 100%
  AVGO/Gold-funded Silver). Do not silently swap the funding source without
  re-running `run_combined_system.py`/`run_joint_stress_validation.py`
  under the hybrid rule first.

- ~~Self-updating Google Calendar integration for dated reminders~~ --
  **DROPPED 2026-07-03.** Superseded by the finalized ops-notification
  scope below: AVGO + LLY earnings reminders go via Telegram directly
  (data-driven, reusing `fi_tracker.py`'s existing yfinance lookup), which
  covers the actual need ("don't miss the print") without the GCP
  Workload Identity Federation complexity that stalled the Calendar
  workflow (see "ON HOLD" section above). No remaining need for a
  calendar-visible entry was identified, so this is closed, not just
  paused.

## Operations notification scope -- FINALIZED 2026-07-03, partially built

Channel split, by urgency (per the operator's own stated principle:
Telegram for urgency, email for everything else):

| Item | Channel | Status |
|---|---|---|
| Guard / joint-stress / silver-GSR / opportunistic-sleeve events | Telegram | **Built, live-verified (2026-07-03)** |
| GSR watch-zone leading-indicator gauge | Telegram | Not built -- needs its own state machine, see ops-conversation notes |
| AVGO + LLY earnings reminders (data-driven, days-to-event) | Telegram | Not built -- LLY needs the same yfinance lookup AVGO already has |
| FI@50 CAGR/AWAR pace digest (monthly cadence) | Email | Not built |
| Quarterly thesis re-check reminder | Email | Not built |

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
  prints fwd/trail EPS ratio and next earnings date. Manual judgment call
  after each print, not an automated rule. Next earnings: 2026-09-03.
  **Ratio corrected 2026-07-06** (`eps_ratio.py`): the original 3.23x
  baseline compared GAAP trailing EPS to non-GAAP forward EPS -- a
  mismatch that inflates the ratio for any company with large GAAP/non-GAAP
  charges (AVGO's VMware-acquisition amortization, specifically). Properly
  normalized (non-GAAP TTM actual vs non-GAAP +1yr estimate), the real
  ratio is **2.39x** -- still the highest vs. the quality-peer set (AAPL
  1.17x, TDG 1.22x, ANET 1.41x), just a smaller outlier than the mismatched
  number implied. LLY's equivalent (added same day) is 1.51x, in line with
  peers. If you see "3.23x" or "3.22x" cited anywhere else, it's the stale
  pre-fix number.

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
- **FX hedging: closed, no instrument change.** Gold=EUR-listed (PPFB.DE,
  Xetra), AVGO/LLY/WMT=USD, FI@50 tracked in SEK. Reconciled 2026-07-02:
  SEK value = gold(USD) × EURUSD × EURSEK, a genuine two-hop chain (not a
  data bug) — one hop more than the rest of the book. **IGLN** (LSE,
  USD-denominated) shares the exact same ISIN as PPFB.DE (IE00B4ND3602) —
  same fund, same bullion, same custodian — would have collapsed the chain
  to one hop, but **confirmed 2026-07-07: not tradeable on Avanza.** No
  further action — stay on PPFB.DE, two-hop chain accepted as-is. Backtest
  evidence (15y, 2011-2026) already said don't overreact to this either
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
