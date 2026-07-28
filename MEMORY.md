# MEMORY.md — Asset Universe handoff doc

Personal quant-finance infra for a Swedish investor's FI@50 plan. Read this
before starting work; update it when you finish a meaningful chunk. Deeper
history (full derivation of the base weights, walk-forward backtests, rotation
sleeve tests that were tried and closed, correlation analysis, etc.) lives in
the operator's personal memory file, not in this repo — ask if you need it;
this file is meant to be self-contained for day-to-day continuation.

## Reactor Core idle cash now tracked; War Chest stale value fixed (2026-07-24)

Follow-on from the TPV work above: reconciled the pipeline against two
real broker screenshots (total-value view + Reactor Core per-holding
view). Result validated the pipeline's share math was already correct --
AVGO/LLY/Gold each matched the live broker value to within 0.2-0.3%
(normal EOD-close-vs-intraday drift). The ~30k kr gap between the
Reactor Core account's real total and the sum of its share positions was
entirely idle/uninvested cash sitting in the account (broker's "Tillg.
för köp"), never tracked anywhere since `snapshot()` only sums named
ticker positions -- confirmed to the kr: broker's implied idle cash
(30,686) vs. the account's own displayed figure (30,621), 65 kr apart.

Fixed the same way Spiltan/War Chest already are -- a manual no-ticker
position row, not a code change: `Reactor Core Cash`, 30,621 kr,
`bucket = "reactor_core"`. Also corrected War Chest's stale manual value
(1,959 -> 9 kr, confirmed against the same screenshot). Verified
`sync_sheet.py`'s patcher can't silently revert this: it only updates
fields for positions matching a name in its sheet `ASSET_MAP`, and
"Reactor Core Cash" isn't in it -- untouched by automation.

Confirmed live: triggered the real daily sync after the fix. Reactor
Core's bucket total is now 731,555 kr (700,934 shares + 30,621 cash),
within 1,795 kr of the broker's real 729,760 kr -- down from a ~30,621 kr
gap before the fix. This is the figure position-weight targets (LLY/AVGO/
Gold vs. their 20/55/25% targets, next-kr routing) are computed against,
so those were previously understating Reactor Core's true size by ~4%.

## TPV made consistently sheet-derived across the framework (2026-07-24)

Operator's explicit rule after a live TPV figure didn't match the position-
table sum this session: TPV must always come from the config Google Sheet,
nothing else -- no fallback of any kind. Audit of every TPV reference in
the codebase found real inconsistencies beyond the one already suspected:

- `fi_pace()` silently fell back to `snapshot(data_dir)["value_sek"].sum()`
  when the sheet fetch failed -- a materially different, independently-
  computed number, substituted with zero indication in `status.md` that a
  different method was used. This is what caused the confusion.
- `run_terminal_wealth.py` and `analysis/transitions.py` each carried their
  own hardcoded stale fallback (1,106,166 and 1,101,671 respectively --
  two different frozen numbers) wrapped in a blanket `except` that would
  have swallowed the new raise too.
- `live_tpv.py` and `tpv_calc.py` never touched the sheet at all -- one-off
  reconciliation scripts computing TPV independently via live/parquet
  prices with stale hardcoded share counts (WMT 126, CCJ 93, VRT 31,
  AVGO 21 -- none matching current `portfolio.toml`), one with a
  hardcoded manual comparison figure baked in. Neither was imported by
  anything else.

**Fix:** `_fetch_sheet_tpv()` now retries transient network failures
(mirrors `sync_sheet.py`'s `fetch_sheet_rows()`) but fails fast on content
errors (HTML response, unparseable row) and raises on final failure
instead of returning `None` -- no caller can conflate "fetch failed" with
"value is None" anymore. `fi_pace()`'s fallback removed entirely.
`run_terminal_wealth.py`/`transitions.py`'s hardcoded fallbacks removed
(manually-run research scripts -- failing loud on a bad fetch is correct
there). `live_tpv.py`/`tpv_calc.py` deleted.

`fi_tracker.py` wraps the now-raising `fi_pace()` the same way
`current_regime()` is already wrapped, so a sheet outage blanks only the
TPV/FI@50-dependent lines (`"[unavailable — reason]"`, the same
failure-signature `check_sync_health.py` already watches for and fails the
Actions run on) -- the rest of the dashboard (guard, signals, earnings
checkpoints) keeps working regardless.

9 new tests added to `tests/test_fi_pace.py` (previously covered only the
pure-math helpers, zero coverage of the sheet-fetch/fallback logic).
Verified both the success and failure paths render correctly via a
stubbed dry run of `fi_tracker.py` (no live data available locally), then
**confirmed for real** by manually triggering the actual `sync.yml` daily
pipeline end-to-end: all steps succeeded including `check_sync_health.py`
and the healthchecks.io heartbeat, and the resulting `status.md` showed a
clean sheet-derived TPV (1,082,660 kr) with no `[unavailable]` anywhere.

## Opp sleeve stop refinement -- analysis complete, awaiting operator decision (2026-07-24)

Prompted by the HWM trade (false stop 07-10, clean profitable exit 07-23
that never needed the hard stop). Built `run_opp_sleeve_stop_sensitivity.py`
+ 13 unit tests (synthetic data) + a temporary diagnostic workflow
(`opp_sleeve_stop_sensitivity_diagnostic.yml`) to test two refinements
against real data instead of guessed parameters: a fixed-day cutoff N
after which the hard stop turns off regardless of MA50 convergence, and a
separate trailing-peak stop for locking in gains once in profit. The
operator paused here to sleep; this was continued overnight on explicitly
confirmed low-risk work only (bug fixes, read-only analysis) -- no live
trading logic touched, per the operator's own boundary.

**best_n bug fixed (2026-07-24):** `main()`'s `best_n` selection wrongly
excluded n_cutoff=0 from consideration when choosing which N to layer the
Phase 2 trailing-stop grid on top of. Since N=0 (hard stop dropped
entirely) is the actual Phase 1 winner, this meant the trailing-stop
numbers reported first were tested on the wrong baseline (N=5). Fixed:
N=0 now competes on equal footing. Re-run confirms the original Phase 1
numbers were unaffected (same random-seed-free simulation, same result);
only Phase 2 changes.

**Corrected result:** with the bug fixed, the best BLIND-population config
is N=0 (no hard stop) *plus* a trailing-peak stop (5% profit trigger, 5%
trailing): Calmar-like -0.145, beating plain N=0 (-0.202) and every
hard-stop variant. So the fuller answer isn't just "drop the hard stop" --
it's "drop the hard stop, keep MA50, and add a trailing stop once
meaningfully in profit," which also directly addresses the second half of
the HWM trade (the profit-protection gap identified when this thread
started).

**Gated variant added and run (2026-07-24):** filtered entries on the 2 of
4 real entry gates cheaply reconstructable from price data alone (above
MA50, positive 20d RS vs SPY) -- 60,385 samples vs. 502 tickers. The
DIRECTIONAL finding replicates and is even starker: N=0's Calmar-like is
-0.353 vs. N=30's -0.837 -- longer hard-stop duration still monotonically
worsens outcomes. **But the gated population's absolute returns are WORSE
than the blind one** (median -1.32% to -2.16% gated vs. -0.46% to -0.86%
blind), which is the opposite of what "more realistic filtering" should
produce if this proxy were actually closer to the real sleeve population.
Most likely explanation: this 2-gate proxy is missing the real screen's
gate 3 (extension control -- MA50 distance capped at the regime's
empirical p67), so "above MA50 + positive RS" alone likely admits a lot of
already-extended, near-term-pullback-prone names that the real screen
would explicitly exclude. **Net: treat the gated run as confirming the
DIRECTION robustly (replicated across two very differently-biased
samples), not as a trustworthy absolute-return number** -- neither
population's magnitude should be taken as representative of real sleeve
trades; the full 4-gate historical reconstruction (regime-conditional
top-N rank + earnings calendar) remains the only way to get a properly
representative number, and is still not built.

**Explicit next steps, in order:**
1. Operator decision needed: accept the directional finding (drop the
   hard stop, add a trailing-peak stop once in profit) as sufficient given
   how robust the direction is across both samples, or invest in the full
   4-gate historical reconstruction first for a trustworthy magnitude.
2. Implement the validated rule in `run_entry_screen.py`'s `binding_stop()`
   / `compute_exit_triggers()`, with tests. **Not done -- deliberately left
   for the operator, not attempted overnight: this changes live trading
   behavior for an account that could open a new position while
   unreachable, which is the operator's call to make, not an autonomous
   one.**
3. Delete `opp_sleeve_stop_sensitivity_diagnostic.yml` once implemented
   (temporary, per repo convention -- same as `entry_screen_check.yml`'s
   siblings).

**Other backlog items surfaced but not acted on this session:**
- Healthchecks.io dead-man's-switch only covers the evening sync slot --
  morning slot coverage is still an acknowledged, open gap (predates this
  session).
- Growth-disappointment cohort study (see AVGO section) needs the SEC's
  full filer universe including delistings to fix its survivorship-bias
  gap -- flagged as worth doing, not urgent, still not built.
- `base_optimizer_with_guard_diagnostic.yml` (the AVGO base-weight
  diagnostic workflow) was labeled "delete once settled" -- the base-weight
  question was substantively addressed this session (see AVGO sections
  below) but the workflow itself hasn't been deleted yet.

## HWM position closed (2026-07-23)

Sold in full: 11 shares @ $286.63 (executed 19:52 local), proceeds $3,153.
Exit price sits well above both the $271.39 hard stop and the ~$264.99 MA50
in play at the time -- a clean exit, not a stop-triggered one. Confirmed via
broker screenshot, not yet reflected in `config/portfolio.toml` as of this
entry (sheet sync will pick it up on next run).

This is the trade the HWM hard-stop question (see below) was explicitly
deferred until -- now unblocked, not yet revisited.

**Key learnings, full entry-to-exit:**
1. Discipline held under a real false positive, and it was the right call.
   The 2026-07-10 STOPPED trigger fired while RS/regime/MA50-slope/cluster
   all stayed clean; the operator correctly read it as noise and explicitly
   refused to change exit rules mid-position. The trade went on to close
   profitably -- validated, not just principled.
2. The design flaw is now confirmed, not theoretical: the 2% hard stop was
   tighter than MA50's own distance from entry (4.3% at the time). A fixed
   stop set tighter than the trend indicator's natural convergence distance
   will produce false triggers on ordinary volatility, independent of
   whether the trend is intact.
3. The position never needed the hard stop to work -- it closed via a
   deliberate, profitable exit above both entry and the stop level. The
   hard stop's entire realized contribution to this trade was one false
   alarm, zero actual protection used.
4. This trade is the real precedent behind the AVGO Sept 3 pre-registration
   approach (see below), even though the connection wasn't drawn explicitly
   at the time: a real signal event happened, and what worked was checking
   it against pre-set criteria instead of re-litigating the rule live.
5. Alerting infrastructure worked correctly -- delivered, confirmed via job
   logs -- a separate, already-settled question from the trading-logic one.

## AVGO 2026-09-03 earnings: pre-registered pass/fail criteria (2026-07-18)

Set *before* the print, deliberately, so the read isn't reconstructed after
the fact to fit whatever the stock does that day. Context: a 2026-07-18
TradingView piece (Erste Group downgrade, "65x earnings, too expensive")
prompted a full re-walk of AVGO's research trail this session -- selection
legitimacy (unbiased, systematic screen, rank 11/539), valuation (the 65x
figure is almost certainly trailing-GAAP, same distortion class as the
3.23x->2.39x EPS-ratio fix; forward P/E 19.4x / PEG 0.41 is cheap-side of
real AI/semi peers), sell-side consensus ($513-524 targets vs. ~$370,
Strong Buy skew), and the flat-since-November price action (reads as
multiple-compression/rotation, not fundamentals -- no valuation ceiling is
forcing it). None of that is new evidence -- it's confirmation of the
existing thesis, not a reason to resize. The one genuinely unresolved
question underneath all of it is still the growth-disappointment cohort
finding (HIGH->MID/LOW deceleration case, real cautionary skew, N=12 too
thin to be conclusive) -- and Sept 3 is the actual test of it, not the
valuation debate.

**CONSTRUCTIVE (remaining rebalance tranche proceeds as sequenced):**
- AI revenue actual tracks the guided $56B FY26 pace (not just "beats
  consensus" -- consensus estimates aren't the guided path).
- FY27 >$100B guidance reaffirmed or raised.
- Beat streak continues (5-for-5).
- Named-contract itemization (Google/Anthropic/OpenAI/Meta, per the real
  Q2 2026 transcript) deepens or holds -- same names/scope or more.
- No new material MediaTek/competitive-share commentary from management.

**CONCERNING (re-open the sizing question, don't pre-commit the answer):**
- AI revenue guidance lowered or FY27 $100B walked back/hedged.
- Beat streak breaks.
- Contract itemization goes vaguer or thins (fewer named counterparties,
  less specific scope than the Q2 2026 print).
- Management raises competitive-share-loss risk unprompted.
- This is the live analog to the growth-disappointment cohort's
  HIGH->MID/LOW pattern -- treat a CONCERNING read as the trigger to
  actually revisit the base weight, not just note it.

**NEUTRAL (default: hold as sized, no action):** beat/reaffirm on both
revenue and guidance, contract itemization roughly flat, nothing new on
competition. This is the base-rate expectation given everything above --
not a low bar, but not a raise either.

Verdict should be judged against these criteria specifically, not against
whether the stock price moves that day -- price reaction and fundamental
verdict can diverge (a CONSTRUCTIVE print can still see a "sell the news"
reaction if the multiple had already priced it in, and vice versa).

## Portfolio construction principle: drawdown-tolerance-first sizing (documented 2026-07-17)

Both sizing layers in this system optimize the same thing at different
scopes -- return per unit of worst-case drawdown, not raw return -- and
that was never stated as an explicit rule anywhere, just implicit in two
disconnected calculations. Writing it down once here:

**Why drawdown, not return, is the binding constraint:** recovery from a
loss is convex, not linear -- -10% needs +11% to break even, -30% needs
+43%, -50% needs +100%, -80% needs +400%. Past roughly -30/-35%, required
recovery return grows faster than any realistic forward CAGR can deliver
in a reasonable timeframe. A large enough drawdown doesn't just hurt --
it can structurally impair the compounding path for years, independent of
whether the underlying asset's long-run edge was ever intact. That
convexity is why this system sizes off worst-case drawdown ceilings
rather than expected-return maximization.

**Two applications of the same rule:**
1. **Internal base split (Gold 25% / AVGO 55% / LLY 20%):** the
   Calmar-optimal point in the 231-combination static weight grid
   (`comparison_results/base_optimizer_grid.csv`) -- #1/231 by Calmar
   (0.839), only 40th/231 by raw CAGR and 44th/231 by Sharpe. Calmar =
   CAGR / |MaxDD|, so this split is specifically where adding more AVGO
   stops being worth the extra drawdown it drags in, even though pure
   CAGR keeps climbing past it (confirmed by `run_base_optimizer_with_guard.py`:
   Gold5/AVGO80/LLY15 beats 25/55/20 on both CAGR and Calmar once the
   guard overlay is added -- 55% is the no-guard Calmar optimum, not the
   global optimum by any metric once the guard changes the tradeoff).
2. **External TPV sizing (Reactor Core 83.3% of total portfolio value):**
   same logic one level up. -25% total-portfolio drawdown tolerance ÷
   -30.0% conservative worst-case strategy MaxDD (the crash-guard-improved
   TXN-analog figure, not AVGO's own milder observed -16.8% -- deliberately
   the harsher number) = 83.3%. See "Rebalance -- DECIDED 2026-07-02" below
   for the full derivation.

Neither layer asks "what maximizes return"; both ask "what maximizes
return subject to a drawdown ceiling I can actually survive," just applied
at different scopes (within Reactor Core, then Reactor Core within total
net worth).

## HWM hard stop: live false-positive confirms the PR #68 finding -- resolution deferred to post-HWM-trade (2026-07-16)

The `HARD_STOP_PCT` (2%) question flagged as unreconciled in PR #68 (see
below) just played out live, not just in backtest: HWM's sleeve Risk
flipped CLEAN -> STOPPED on 2026-07-10 (price $270.85 vs hard stop
$271.39) while every other signal -- RS +4.2%, regime stable, MA50 slope
+10.81 rising, cluster OK -- stayed clean. HWM recovered within days,
closing back at/above entry ($276.93+). The alert itself worked correctly
(delivered, confirmed via job logs); the operator correctly discounted
the *trigger* as noise, not the alerting mechanism.

**Genuine tradeoff, confirmed on real data -- not "just remove it":** the
hard stop's real purpose is bounding max initial loss-per-trade before
MA50 (a lagging 50d average) has converged toward entry. For HWM
specifically, MA50 ($264.99) still sits 4.3% below entry ($276.93) --
more than double the hard stop's 2% cap. Dropping the hard stop outright
would mean initial risk is bounded only by however far below entry MA50
happens to sit at entry time, not a controlled figure. The cost side is
what just happened: a fixed level sitting near price for weeks produces
false triggers from ordinary volatility, independent of whether the
trend is actually intact.

**Decision: explicitly deferred until HWM's position closes** (operator's
own call, 2026-07-16) -- changing exit rules mid-position was rejected on
principle, not because the analysis is unclear. Candidate resolutions to
evaluate then, building on PR #68's unresolved "should any fixed stop
exist at all" question:
1. Drop the hard stop entirely, MA50 sole binding stop (RS/regime/cluster
   stay as tripwires, as already structured).
2. Time-decay the hard stop -- active only for the first N days
   post-entry (while MA50 is still converging), then MA50 takes over.
3. Require multi-day confirmation (e.g. 2 consecutive closes below)
   rather than any single-day touch, to filter ordinary vol without
   dropping the initial-risk-cap purpose entirely.

**Interim fix shipped meanwhile (2026-07-16):** the tripwire detail line
and the Telegram alert now show MA50's actual price level (`MA50 $264.99
(slope +10.68)`), not just its slope -- previously the alert showed the
noisy hard-stop distance but never the level the operator actually
trusts.

## Cron delay root cause found and fixed (2026-07-08, PR #70)

The 2026-07-07 "cron won't fire" scare (see the concurrency-guard entry
below) turned out to be a symptom of something bigger, found the next
morning when `daily-sync`'s 06:07-slot run was still missing ~2h after
its (old) 06:00 scheduled time. Measured **every** scheduled run since
2026-06-25 (18 runs): the old exact-`:00` morning slot was delayed
**166-286 minutes, every single day, without exception**; the old `:30`
evening slot, 66-90 minutes, also every day. `sync-sheet` -- same repo,
also hits `:00` among its 12 daily fires -- averaged only ~8min delay,
proving this wasn't general GitHub congestion but something specific to
`daily-sync` competing for popular round-minute queue slots (only 2
fires/day, both on round numbers, vs. sync-sheet's 12 fires spreading
the exposure).

**Fix:** offset both crons off round minutes -- `37 20 * * 1-5` and
`7 6 * * 1-5` -- matching GitHub's own documented advice. Also updated
`check_sync_health.py`'s `SCHEDULED_RUN_TIMES_UTC` (reused by the
watchdog) to match, and the operator updated healthchecks.io's Cron
expression to `37 20 * * 1-5` / Grace 2h to stay aligned.

**Honest caveat:** the actual delay reduction can only be confirmed at
the next real scheduled fires (today 20:37 UTC / tomorrow 06:07 UTC) --
not provable before merge, since GitHub doesn't expose a way to test
scheduled-fire timing on demand. Worth checking those first real fires
land close to on-time before considering this fully resolved.

## Root cause found for 2026-07-07's delayed/failed scheduled run -- concurrency guard added (PR #60)

The 20:30 UTC `daily-sync` cron appeared not to fire for ~80 minutes,
prompting a long live-debugging session (heartbeat, cron config, etc.)
before the actual cause was found: **the cron wasn't broken -- it fired
late (~80min, GitHub-side queuing/congestion, cause not fully confirmed)
and collided with a concurrent manual `workflow_dispatch` test run.** Both
tried to commit `status.md` around the same time; the second one's `git
pull --rebase origin master` hit a real merge conflict (auto-merge failed
on `status.md`) and the whole job failed outright -- confirmed directly in
that run's own logs (`CONFLICT (content): Merge conflict in status.md`).
No data corruption, but that run's notify/heartbeat steps never executed
since the job failed before reaching them.

**Fix:** added `concurrency: {group: daily-sync, cancel-in-progress:
false}` to both `sync.yml` and `sync_sheet.yml` -- shared group since both
workflows commit to `config/portfolio.toml` too, so this closes the
cross-workflow collision risk, not just within `daily-sync` itself.
`cancel-in-progress: false` means overlapping runs queue and execute
sequentially rather than racing -- no run's work gets dropped. Live-
verified via a real `workflow_dispatch` on a branch before merging.

**Lesson, stated plainly:** none of the alert-robustness work built
earlier same day (retry/fallback, heartbeat, data-freshness gate) was
wrong -- the actual bug was a genuinely new failure mode (concurrent-run
collision), only surfaced because testing that same evening happened to
overlap with a real delayed cron fire. Worth remembering: manual
verification dispatches during active development carry a real (if rare)
risk of colliding with the schedule itself if there's no concurrency
guard -- now fixed.

**Still open, not resolved:** why the cron was ~80 minutes late in the
first place. No GitHub-wide incident was active at the time (checked
githubstatus.com); an earlier documented Actions API incident that day
had already resolved hours prior. Could be residual congestion, could be
something specific to this repo/workflow -- not confirmed either way. If
it recurs on a day with no manual testing to muddy the signal, that's
worth investigating further; a one-off isn't yet a pattern.

## Heartbeat notification path actually proven end-to-end (2026-07-07)

Following up on the heartbeat build (PR #55): confirming a check exists and
pings successfully proves detection, not that a real down event actually
notifies anyone -- so this was deliberately force-tested for real, not
just trusted.

**First real test (Period/Grace temporarily set to 2min/1min) found a real
gap:** the check correctly flipped to Down (confirmed in its Event Log --
"Status change: up -> down" recorded), but **no notification was ever
attempted** -- the Event Log's "Downtime alert" category was completely
empty, which rules out a delivery/spam problem (a failed send attempt
still logs an entry) and points at the email integration's ON toggle not
having actually been saved/armed. Ruled out a race condition from our own
testing first (checked `gh run list` -- no scheduled or dispatched run
fired in the relevant window, next scheduled run was a full hour out).

**Fix: toggle the email integration off, then on again**, to force it to
actually save. Verified via two independent real (non-test-button) state
transitions afterward: a genuine recovery ping produced a real "asset_
universe is UP" email (downtime correctly measured as 23m36s, matching
the original real down event), and a second forced miss produced a real
"asset_universe is DOWN" Telegram message.

**Also added: Telegram as a second healthchecks.io integration, alongside
email.** This directly satisfies the design point flagged when the
heartbeat was first proposed -- the heartbeat's own alert needs to reach a
channel actually watched while traveling, not email. Email alone had
already demonstrated it can silently fail to arm; Telegram is now the
primary expected channel for this specific alert, with email as a second
independent path.

**Status: Period/Grace need reverting from the 2min/1min test values back
to 3 days/1 hour** (set during the earlier gate-tuning session) -- flagged
to the operator, not yet confirmed done as of this writing.

## Live pipeline gated on actual data freshness, not just exit code (2026-07-07, PR #57)

Closes a gap found while scoping an operations test for the whole alert
chain: the heartbeat (PR #55) only proves the job *ran*, not that it ran
on good data. A silent yfinance/FRED hiccup that returns stale data
without erroring would still ping heartbeat healthy and let every
downstream signal (guard, silver, sleeve) compute off day(s)-old prices.
`check_local_data_freshness.py` already had exactly the right logic
(SPY reference ticker, weekend-aware, auto-refresh-then-fail) but was
scoped to local ad-hoc sessions only -- the "unrelated to the live
pipeline" claim in its own docstring was itself unverified, same failure
class as everything else this project keeps finding. Now also wired into
`sync.yml` as a step right after "Update prices": auto-refreshes once if
stale, fails the job loudly if a refresh doesn't fix it, before any signal
gets computed downstream. Live-verified in real CI before merging (not
just local). 187 tests passing project-wide, no new tests needed (existing
4 already cover the trading-day logic this reuses as-is).

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

- **Telegram "just reported" earnings message is missing the actual EPS
  figure (logged 2026-07-08).** `check_signal_changes.py`'s push message
  (AVGO/LLY EARNINGS JUST REPORTED) includes Revenue actual + next-quarter
  consensus and an "EPS beat streak" *count* (e.g. "4"), but not the
  actual reported EPS dollar value or the estimate it beat/missed by --
  that detail only lives in the full dashboard (`status.md`), not the
  push. Same shape of fix as PR #41's revenue addition: add the actual
  EPS $ + consensus + beat magnitude to the message. Quick, not urgent --
  next prints are LLY 2026-08-05, AVGO 2026-09-03.

- ~~PR #40 (`research/sleeve-duration-sensitivity`), open, not merged~~
  -- **CORRECTED 2026-07-08: superseded, not an open question.** PR #40's
  finding (90d beats 30d) used the wrong population (broad regime-matched
  dates, not the sleeve's actual gated entries) and disclaimed itself as
  not decision-grade for exactly that reason. **PR #45 (already merged)
  redid this properly** against the real ~4,300-entry gated-entry
  population (via `run_sleeve_entry_reconstruction.py`) and found the
  **opposite**: annualized median return *declines* with duration (26.5%
  at 15d down to ~20-22% at 45-90d) -- suggesting `TIME_EXIT_DAYS=30` is
  already on the generous side, not that it should be lengthened. Trust
  PR #45's answer over PR #40's. PR #40 itself can be closed without
  merging (superseded), not left open as unresolved. Still genuinely not
  a full verdict either way -- PR #45's own caveat stands: population-
  level stat, not a compound-exit simulation (MA50 breach/hard stop would
  truncate many real trades before the time exit ever binds).

- ~~healthchecks.io check: switch Simple Period to Cron mode~~ -- **DONE
  2026-07-07/08.** Switched to Cron expression `30 20 * * 1-5` (the
  evening run), Grace ~2h -- same-day detection instead of up-to-3-day,
  same weekend-blind-spot as before (unavoidable in this design, not a
  regression). **Optional follow-on still open:** a second check keyed to
  the morning run (`0 6 * * 1-5`) would close the one remaining blind spot
  (a morning-only failure that doesn't also take down the evening run) --
  needs `sync.yml` to route pings by `github.event.schedule`, real but
  small code change, not started.

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

- **Sleeve's `HARD_STOP_PCT` (2%) -- validated against real data (PR #68,
  2026-07-08), and the finding is more important than a simple "is 2% ok"
  answer.** Grid tested [1%, 1.5%, 2%, 3%, 4%] via compound stop-loss
  simulation against PR #45's real ~4,300-entry gated-entry population
  (`run_sleeve_stop_sensitivity.py`). **Every threshold gets stopped out
  on more than half of trades** (73% at 1%, 63% at the live 2%, still 48%
  even at the loosest tested 4%), and **every threshold shows a negative
  median return** -- in real tension with PR #45's own no-stop duration
  study, which found positive annualized returns (~20%+) on this exact
  same population. **Plausible explanation, not yet confirmed:** a fixed
  stop permanently locks in a loss for any entry that dips past it, even
  ones that would have recovered by the 30-day time exit -- meaning the
  real question this raises isn't "what percentage" but **"should any
  fixed stop exist at all."** Honestly flagged as unreconciled in the
  script's own output -- needs a direct side-by-side no-stop-vs-stop
  comparison on the identical population before treating either result as
  decision-grade. **Report-only, live `HARD_STOP_PCT` unchanged.** This is
  a genuinely bigger finding than the original "is 2% the right number"
  question -- worth the operator's own review, not a quiet parameter
  tweak.

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

- ~~Record the earnings-day manual verdict, not just alert on it~~ --
  **DONE, stale entry.** `record_earnings_verdict.py` shipped via PR #39
  (merged 2026-07-06) -- exactly the CLI described below. Corrected
  2026-07-08 after finding this entry hadn't been marked done.

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

- ~~External dead-man's-switch for daily-sync~~ -- **DONE 2026-07-07**
  (healthchecks.io heartbeat, PR #55, live-verified on two channels). See
  "Heartbeat wired in" and "Alert-robustness hardening" sections above.

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

## Opp sleeve stop refinement -- compound-exit test finds the real culprit is MA50, not the hard stop (2026-07-26)

Closes the loop the 2026-07-24 entry left open (full 4-gate compound-exit
simulation, "still not built"). Three scripts, run in sequence, on the real
declustered 4-gate entry population (4,321 entries, 2009-2026, from
`run_sleeve_entry_reconstruction.py` / PR #45):

1. **`run_opp_sleeve_combined_sensitivity.py`** (new): tests stop config x
   hold duration jointly, stratified by realized-20d-vol tercile at entry
   (prompted by "shouldn't stops be asset-specific?"). Finding: vol
   *magnitude* matters (high-vol entries stop out more, lose more under
   every config) but the *ranking* of configs is identical in every
   bucket -- `trailing_5_5` (hard stop off, 5% trigger/5% trailing) beats
   `no_hardstop` beats `current_hardstop` everywhere, so one global
   trailing-stop rule holds up. **Bigger finding, unprompted:** every single
   config -- including the best one -- had a NEGATIVE median return at
   every duration/bucket (e.g. trailing_5_5 @ 30d: -1.2% median, calmar
   -0.37), directly contradicting PR #45's own raw finding that the
   identical entries return +26.5% annualized at 15d with NO exit rule at
   all. MA50 was the one stop left unconditionally active in every config
   tested (matches live `binding_stop() = max(hard_stop_if_active, ma50)`)
   -- and since gate 3 requires entries to NOT be extended (close to their
   own MA50 by construction), a plausible read is that ordinary MA50-touch
   noise, not real breakdowns, was exiting trades right before the recovery
   the raw hold captures.
2. **`run_opp_sleeve_ma50_stop_sensitivity.py`** (new): isolates that
   variable -- hard stop OFF and trailing 5%/5% ON throughout (both already
   validated), sweeps MA50's grace period (days post-entry before it can
   bind) and buffer (price must close X% below MA50, not just below it) --
   independently and combined. **Confirms the hypothesis directly:**
   `ma50_always_tight` (today's live behavior) reproduces the negative
   baseline everywhere. Loosening MA50 flips it: `ma50_grace_20d` and
   `ma50_buffer_3pct` turn positive at short durations (15-30d) but fade
   back toward zero/negative by 45-90d. **`ma50_buffer_5pct` is positive in
   EVERY duration (15-90d) and EVERY vol bucket** -- e.g. 30d pooled: median
   +1.07%, annualized +13.8%, calmar +0.161, still stopping out 45.9% of
   trades (real protection, not "stop never fires"). `ma50_off` (bracketing
   case, not a live candidate -- no ongoing downside protection at all) is
   even stronger (30d pooled: +19.7% annualized, calmar +0.318), confirming
   MA50-touch was the dominant drag, not a residual one.
3. Both new scripts + a MA50-focused unit-test file (20 tests total) ran
   against real data via temporary diagnostic workflows
   (`opp_sleeve_combined_sensitivity_diagnostic.yml`,
   `opp_sleeve_ma50_stop_sensitivity_diagnostic.yml`), same discipline as
   the 2026-07-24 entry.

**Caveat carried forward, still not modeled:** none of these three scripts
simulate re-entry after a stop-out -- every stop-out is treated as a dead
trade, while the real sleeve re-screens daily and could rotate into the
same or a different candidate. Real drag from a tight MA50 is therefore
probably smaller than shown here; the direction (loosen MA50) is not in
question, only the exact magnitude.

**Updated recommendation (supersedes the 2026-07-24 entry's "drop hard
stop + add trailing stop" as sufficient):** drop the hard stop, add the
validated 5%/5% trailing-peak stop, AND add a 5% buffer to the MA50 stop
(require close <= ma50 * 0.95, not just close <= ma50, before it binds).
All three pieces are now validated together on the real gated-entry
population, not guessed.

**IMPLEMENTED (2026-07-26), operator go-ahead given explicitly, no open
position at the time (confirmed with operator before touching anything --
`config/sleeve_state.toml` was itself found stale here, still showing HWM
`open=true` three days after the real 07-23 close; corrected via
`--close`, same bug class as the PR #46 sleeve-state gap).** Also folded
in the duration finding from earlier the same session: `TIME_EXIT_DAYS`
30 -> 21 (Calmar peaks ~21d then decays for the winning stop config, and
30 traced back to the informal HWM precedent, never a backtest).

Changes in `run_entry_screen.py`:
- `HARD_STOP_PCT` removed. `binding_stop(entry_price, ma50, peak_price)`
  gained a third argument and now returns `max(buffered_MA50, trailing_if_armed)`
  instead of `max(hard_stop, ma50)` -- no fixed percentage-of-entry floor
  at all anymore, matching `ma50_buffer_5pct`'s validated shape (the only
  config that was positive in every duration/bucket tested).
- New constants: `MA50_BUFFER_PCT = 0.05`, `TRAILING_TRIGGER_PCT = 0.05`,
  `TRAILING_PCT = 0.05`.
- New `_peak_since_entry()` -- highest close from entry_date to today,
  floored at entry_price, feeding the trailing stop. `compute_exit_triggers()`
  now returns `ma50_buffered`, `peak_price`, `trailing_stop` (None until
  armed) alongside the existing `binding_stop`/`binding_label`.
- Display: "Hard stop" line removed from both the OPEN-position report and
  the daily `status.md` summary; replaced with "MA50 (buffered)" showing
  both the raw and buffered level, plus a "Trailing stop" line once armed.
  `time_exit_binding` and the candidate-table duration caption were
  hardcoded to "30d"/"3d" text -- fixed to read the actual constants so
  they can't silently drift from the real values again.
- `fi_tracker.py` needed no changes -- it only calls
  `run_entry_screen.sleeve_daily_summary()`, which picks up the new
  behavior automatically.
- Tests: rewrote the 3 old `binding_stop()` tests for the new 3-arg
  signature/shape (MA50-vs-trailing precedence, trailing not armed below
  trigger), added 3 tests for `_peak_since_entry`, updated 3
  `suggested_duration_days` tests for `TIME_EXIT_DAYS=21`. Full suite: 257
  passed (1 pre-existing, unrelated `test_panel.py` volume-field failure,
  not touched by this change).
- Deleted all three temporary diagnostic workflows
  (`opp_sleeve_stop_sensitivity_diagnostic.yml`,
  `opp_sleeve_combined_sensitivity_diagnostic.yml`,
  `opp_sleeve_ma50_stop_sensitivity_diagnostic.yml`) per this repo's own
  stated convention -- their job (get real numbers to decide with) is
  done; the backtest scripts themselves stay in the repo as the record of
  how these numbers were derived.

**Not modeled, unchanged from the analysis phase:** re-entry after a
stop-out. Real drag from the old tight MA50 was probably smaller than the
backtests showed; this doesn't affect the direction of the fix, only its
exact magnitude.

## Opp sleeve entry-filter tightening -- no material improvement found, current 4 gates already do the work (2026-07-26)

Prompted the same day as the stop-logic implementation: the live screen
found two near-misses (STLD failed only on RS margin, -2.2% vs the
existing >=0% bar; GM failed on cluster health + a flattening MA50). Built
`run_opp_sleeve_entry_filter_sensitivity.py` to test whether tightening
entry further -- beyond the existing 4 gates -- raises the win rate, on
the real 4,307-entry gated population (2009-2026) at the live 21d
duration.

**Baseline is already strong**: 57.6% win rate, +1.32% median / +25.6%
annualized at 21d, n=4307. Tested tightenings, individually and combined:

| config | n | win rate | annualized |
|---|---|---|---|
| current baseline | 4307 | 57.6% | +25.6% |
| RS margin >=2% | 2628 | 57.3% | +25.6% |
| RS margin >=3% | 2027 | 57.0% | +24.9% |
| RS margin >=5% | 1238 | 57.9% | +28.5% |
| MA50 slope top-tercile | 1436 | 58.8% | +26.3% |
| VIX-calm gate | 2449 | 58.6% | +27.1% |
| diversity proxy (n_matched) top-tercile | 1441 | 57.0% | +27.2% |
| combined moderate (RS>=2% + VIX-calm) | 1409 | 57.8% | +25.5% |
| combined strict (all 4 tightened) | 118 | 53.4% | +7.5% |

**Finding: no individual filter materially beats the baseline.** RS
margin >=2-3% is flat-to-worse than the existing >=0% bar -- confirms
STLD's rejection was correct but says a bigger margin isn't a better
rule. The two closest things to a real (small) improvement are the
VIX-calm gate (+1pt win rate, +1.5pt annualized, keeps more than half the
sample) and MA50 slope top-tercile (+1.2pt win rate) -- both modest,
neither clearly worth the added complexity and reduced trade frequency.
**Stacking all four tightenings together makes things WORSE, not
better** (win rate drops to 53.4%, annualized craters to 7.5%, on a
sample too thin at n=118 to trust anyway) -- a clean example of
over-filtering/overfitting rather than compounding an edge.

Caveats: diversity is approximated via n_matched (pre-transition
regime-matched date count), not the live screen's exact ROBUST/MODERATE/
THIN label -- directional only. Cluster-health tightening (GM's second
failure reason) was not tested -- point-in-time sector-peer
reconstruction across thousands of historical entries is out of scope
for this pass.

**Recommendation: no change.** The existing 4 gates (regime top-N,
above-MA50, extension+RS, earnings-clear) already capture the real edge;
none of the tested additions clear the bar for adding complexity to a
system that's already working. Not implemented, and this one doesn't
need an operator go-ahead to skip -- there's nothing here worth
implementing.

## Opp sleeve trailing-stop distance -- 3% beats the live 5%, no vol-scaling needed (2026-07-27)

Follow-on to the entry-filter study: tested whether the trailing stop
should be volatility-SCALED (different trigger/pct per vol bucket) rather
than one global rule. Swept a 3x3 grid (trigger x trailing_pct, each in
{3%, 5%, 8%}) on the same real 4,321-entry population, holding the rest of
the now-live exit logic fixed (MA50 buffer 5%, no hard stop, 21d
duration).

**Finding: it's not a vol-scaling question -- it's a single-parameter fix.**
(trigger=5%, trailing_pct=3%) is at or within noise of the best result in
EVERY bucket simultaneously:

| bucket | live (5%/5%) calmar | best found | best config |
|---|---|---|---|
| pooled | 0.193 | 0.243 | 5%/3% |
| low_vol | 0.327 | 0.340 | 8%/5% (5%/3% gives 0.339 -- tied) |
| mid_vol | 0.142 | 0.240 | 5%/3% |
| high_vol | 0.132 | 0.217 | 8%/3% (5%/3% gives 0.211 -- close) |

Keeping the profit trigger at 5% (unchanged) and tightening the trailing
distance from 5% to 3% captures nearly all of the available improvement
everywhere, without any bucket-specific complexity: pooled annualized
27.8% vs the live rule's 19.2%, mid_vol calmar +69% relative, high_vol
calmar +60% relative. A real, meaningful improvement -- not a marginal
one, and simpler than what was being tested for (one number changes, not
a new vol-dependent rule).

**IMPLEMENTED (2026-07-27), operator go-ahead given explicitly.**
`TRAILING_PCT` changed from `0.05` to `0.03` in `run_entry_screen.py`
(`TRAILING_TRIGGER_PCT` unchanged at `0.05`). Updated the 1 unit test that
asserted on the old 5%/5% pullback level
(`test_binding_stop_trailing_binds_once_armed_and_higher_than_ma50`).
Full suite: 281 passed. Temporary diagnostic workflow already removed
after the backtest run.

## AVGO gap-down forward-return analysis (2026-07-28)

Standalone research (not opp-sleeve related): `run_avgo_gap_down_analysis.py`
measures AVGO's forward returns after an overnight gap-down (open >=2/3/5%
below the prior close) vs. an unconditional same-horizon baseline, full
history (2009-2026, 4268 sessions) and split pre/post-2023.

**Full history: gap-downs are a consistent, monotonic buy signal.** At
every horizon (21d/63d/252d) and every threshold, gap-down forward returns
beat the unconditional baseline, and the effect strengthens with gap size:
21d median +3.1% baseline -> +4.0%/+5.5%/+7.9% at 2/3/5% gaps; 63d +9.7%
baseline -> +16.7%/+19.2%/+24.8%; win rates climb from ~64% baseline to
~70-84% depending on threshold/horizon.

**Era split matters.** Pre-2023 shows the same clean monotonic pattern
(smaller magnitudes). Post-2023 (AI era) the picture is muddier at 21d --
a 2% gap-down's forward return (+3.3%) is actually slightly BELOW that
era's baseline (+3.9%), because AVGO's own baseline drift post-2023 is
extraordinary (252d baseline median +90%, an unusually high bar for any
subset to clearly beat). The premium reappears at 63d (+27.9% vs +17.7%
baseline for 2%+ gaps). The 5%+ bucket post-2023 has only 6-8 events --
too thin to trust on its own.

**Bottom line:** gap-downs have historically resolved favorably almost
every time (win rates often near 100% at 252d in both eras) -- but "a
gap-down beats just holding AVGO" is a much cleaner story pre-2023 than in
the current AI-melt-up regime, where simply holding is already a very high
bar. Informational only -- not wired into any live gate. Temporary
diagnostic workflow removed after this run.
