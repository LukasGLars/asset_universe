# MEMORY.md — Asset Universe handoff doc

Personal quant-finance infra for a Swedish investor's FI@50 plan. Read this
before starting work; update it when you finish a meaningful chunk. Deeper
history (full derivation of the base weights, walk-forward backtests, rotation
sleeve tests that were tried and closed, correlation analysis, etc.) lives in
the operator's personal memory file, not in this repo — ask if you need it;
this file is meant to be self-contained for day-to-day continuation.

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
