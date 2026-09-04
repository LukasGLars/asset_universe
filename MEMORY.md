# MEMORY.md — Asset Universe handoff doc

Personal quant-finance infra for a Swedish investor's FI@50 plan. Read this
before starting work; update it when you finish a meaningful chunk. Deeper
history (full derivation of the base weights, walk-forward backtests, rotation
sleeve tests that were tried and closed, correlation analysis, etc.) lives in
the operator's personal memory file, not in this repo — ask if you need it;
this file is meant to be self-contained for day-to-day continuation.

## Crypto trend sleeve LIVE; opportunistic sleeve RETIRED (2026-09-04)

**The opportunistic sleeve's four gates were never better than random entry
from the same universe.** The "+1.28% median/trade, 57.5% win, n=4,300" figure
in `sleeve_entry_duration_grid.csv` was never benchmarked against anything.
Control run: all 504 US equities in the universe, every trading date 2009-2026,
no gates at all -> median +1.07%, win 57.8%. So the gates buy **+0.2 to +0.5pp
of median return and a LOWER win rate at every duration** (-0.3pp at 21d,
-1.8pp at 90d). Bootstrap z oscillates 1.47-2.64 across durations -- noise, not
an effect. Nearly all the apparent edge was just being long US equities in a
bull market: a denominator that was never checked.

Live confirmation, reconstructed from the committed `status.md` history
(every `chore(sync)` commit is a point-in-time record of that morning's
recommendation, computed off the prior close -- no lookahead): 13 closed
trades 2026-07-01 -> 09-03 at **mean -5.24%, win 23%, alpha -5.25%**. The
sequential 1-slot sim returned **-19.5% vs SPY +3.7%**. Saved as
`comparison_results/opp_sleeve_live_recommendations.csv` and
`opp_sleeve_live_sequential.csv`.

Higher median + lower win rate is the signature of selecting higher-VOLATILITY
names -- beta, not skill. Cost settled it regardless: ~1% round trip against a
0.2-0.5pp edge. **This supersedes the 2026-08-04 "real, validated,
positive-expectancy mechanism" note.**

**Dead ends tested the same day -- do not re-test:**
- VIX >90th pct, or VIX +40%/5d -> buy SPY/QQQ: NEGATIVE vs baseline. Fear is priced.
- SPY/QQQ/IWM drawdown-from-60d-high buying: noise, sign flips by duration.
- BTC -25% / ETH -30% dip buying: strongly NEGATIVE (-4.5% to -15%). Crypto is a
  momentum regime, not a reversal regime.
- Trend-following SPY/QQQ/GLD/SLV/USO: loses to exposure-matched B&H, 25/25 cells.

**What replaced it.** `run_crypto_trend.py` + `analysis/crypto_trend.py`, live
from 2026-09-04, 5% of TPV (27,225 kr each in Virtune BTC and Virtune Staked
ETH ETPs), funded from the Home Base overweight (18.3% -> 13.3%), core
untouched. Rule per asset: weekday closes only, 50/100/200d SMA, long above
MA+2%, flat below MA-2%, else hold prior state; target = mean of the three
(0/33/67/100%). Validated vs **exposure-matched** buy-and-hold net of the 1.49%
ETP fee and 0.5% round trip: 3/3 eras, 12/13 rule variants, BTC/ETH/SOL
independently, ~2.2 round trips/yr. The 2% band is load-bearing -- without
hysteresis the rule loses to B&H in 2023-26.

Sizing came from gap risk, not the drawdown budget: measured 85/10/5 MaxDD is
-20.79% (better than core-only -23.45%, because the filter sits at 0-33%
exposure exactly when the core is stressed -- correlation to core 0.048, and it
was fully flat at the 2020-03-18 trough). A daily rule cannot exit ahead of a
weekend collapse or issuer failure, hence 5% start and a **10% hard cap**.
SOL and other alts are deliberately excluded: that backtest is hindsight
selection, and the tier fails in days.

**Kill criterion, agreed up front:** if after 3 completed cycles realized return
trails exposure-matched buy-and-hold, close it.

Known gaps: the retired opportunistic sleeve still prints a daily candidate
into `status.md` (war chest is 27 kr, so it can never act) -- left in place
rather than removed unasked; removing it is a clean follow-up. The staked-ETH
ETP can trade at a discount to NAV in stress exactly when the rule says exit --
take the exit anyway.

## AVGO peer valuation snapshot now wired into daily sync (2026-08-25)

Reverses the 2026-07-06 "manual only" decision (~line 1505 below):
`run_peer_valuation.py` now runs as a `sync.yml` step, output appended to
`status.md` same as `run_regime_alert.py`/`run_optimizer.py`. Still no
alert/trigger — `notify_signal_changes.py`'s fingerprint is regex-scoped to
specific known fields, so this new block can't cause a false signal-change
notification. Reason for the reversal: AVGO dropped -14% between the
2026-08-14 snapshot ($417.82) and 2026-08-24 ($358.76) with `status.md`'s
P/E/PEG still showing the stale price the whole time; daily is cheap enough
to just do given the 2026-09-02 earnings print is close.

**2026-08-25 rerun, for reference:** AVGO $358.76, fwd/trail 2.40x (unchanged
-- EPS inputs didn't move), fwd P/E 18.39x (was 21.39x), PEG(1y) 0.13 (was
0.15). Rank improved to 4/9 cheapest on fwd P/E (was 5/9), 3/9 on PEG(1y)
(was 3/9, unchanged). Mid-pack framing still holds, now cheaper in absolute
and relative terms than two weeks ago.

## Session 2026-08-20 (cont.): ADDT_B_ST holdout-verified and REJECTED; no Swedish candidate survives

Independent verification of the ADDT_B_ST write-up directly below (not
committed as scripts -- audit only, run ad hoc). Two of its three claims
reproduce; the third, most important one does not, and changes the call.

**Reproduced, real:**
- Sub-period Sharpe check: 6/6 under calendar-year-aligned chunks (5/6 under
  an even-date split, one virtual tie) -- holds up, not partition-sensitive
  in any meaningful way.
- Regime-bucket check (ry x baa10y): exactly 7/7, matches.
- FI@50 MC funding-mechanism reversal: reproduced and stress-tested for MC
  noise using paired/common-random-number sampling (same bootstrap day-draws
  across variants, only weights differ) -- deltas are stable to +-0.2pp
  across 6 seeds. AVGO-specific funding: -8pp P(reach target) (write-up:
  -6.1pp). Pro-rata funding: +2.4pp (write-up: +2.6pp). **Real signal, not
  noise -- this part of the write-up is solid.**

**Did NOT reproduce -- this is the one that matters:** a genuine train/test
holdout (select on 2009-2017, judge purely on untouched 2018-2026 -- same
convention as `run_clean_sheet_search`, PR #99's "0/100" result) was never
run for ADDT_B_ST. Running it: ADDT_B_ST **fails**. OOS CAGR is a wash
(36.7% vs base 36.8%), MaxDD is worse (-24.8% vs -23.5%, same direction as
every other window tested -- MaxDD never once improved, IS, OOS, or full
sample). Only OOS Sharpe holds up (1.604 vs 1.511). Screening the full
local universe (545 tickers) the same way: only 8/138 loose-criterion IS
survivors (6%) also pass OOS -- generalizes PR #99's finding to this
screen type too. **MEMORY.md's own description of the original filter
("improves CAGR, Sharpe AND MaxDD simultaneously") is inconsistent with
its own later admission that MaxDD got slightly worse** -- worth reading
critically next time a "passed the screen" claim shows up here.

**Also checked: does any Swedish name survive the same genuine holdout?**
Screened all 41 `se_equities` tickers IS(2009-17)->OOS(2018-26). Strict
pass (CAGR+Sharpe+MaxDD all improve, both windows): **0/41**. Loosened to
CAGR+Sharpe only: **1/41**, SAAB_B_ST -- but OOS CAGR is rounding-level
(36.9% vs 36.8%), MaxDD worse (-25.6%), MC edge only +0.9pp (vs ADDT's
+2.4pp), and this repo already established (2026-08-18, "SAAB is NOT a
hedge") that SAAB's whole correlation profile is a single post-Ukraine
regime artifact. **No genuine Swedish diversifier exists in the local
universe.**

**Widened to the entire local universe (545 tickers, equities + se_equities),
same strict test: 0/545 pass.** Nothing in the local data simultaneously
improves CAGR, Sharpe AND MaxDD both in-sample (2009-2017) and
out-of-sample (2018-2026) as a 10% pro-rata blend into Gold25/AVGO40/LLY35.
Loosening to CAGR+Sharpe only (MaxDD allowed to get worse) surfaces 8 OOS
survivors -- TPL, SAAB_B_ST, NVDA, DXCM, AXON, FTNT, STX, FIX -- all trading
worse drawdown for the Sharpe gain, same shape as ADDT. **This generalizes
`run_clean_sheet_search`'s 0/100 (PR #99) from full clean-sheet portfolios
down to the single-asset-diversifier level: not a search-coverage gap, a
real null result.** Nothing findable in this repo's local universe
genuinely improves on the live base -- stop looking for a diversifier
here; the next lever (per PR #99 and the FI@50 goal-derivation entry) is
still contribution rate, not asset selection.

**Revised call: REJECT ADDT_B_ST at 10%, or size far smaller than planned
if done at all.** The only edge that survives a real holdout is smoother
day-to-day Sharpe -- no extra return, no extra drawdown protection, tested
honestly. Not enough to justify 10% single-name concentration risk in a
small/mid Swedish industrial. **The rebalance below was never executed and
should now not be, on the terms it was sized.** Reusable lesson, same
species as the split-adjustment/`fi_pace()`/vol-targeting bugs: a
sub-period or regime check that reuses the SAME full-sample data it was
selected on is not an out-of-sample test, no matter how many buckets it's
sliced into -- only a genuine train/test holdout is.

## Session 2026-08-20: stale-weights doc fix (PR #104, MERGED); ADDT_B_ST candidate found, not yet executed

### 1. `run_comparison_backtest.py` / `run_combined_system.py` were modelling a retired portfolio

`run_comparison_backtest.py`'s `PORT_WEIGHTS` hardcoded the old 7-asset mix
(Gold/Silver/LLY/WMT/CCJ/VRT/AVGO), labelled "actual weights from
portfolio.toml" -- stale since the 2026-08-16/17 move to Gold25/AVGO40/LLY35
(Silver/WMT/CCJ/VRT/HWM are all 0 shares, not held). `run_combined_system.py`'s
docstring weight table still showed the old 25/55/20 base. Both corrected to
match live config; Strategy D's anchor drops WMT. Live alerting
(`fi_tracker.py` <- `run_combined_system.WEIGHTS`) was never affected -- only
prose/docs had drifted. **Lesson for next session: don't trust a script's
"actual weights" comment without checking it against `config/portfolio.toml`
directly.**

### 2. Bitcoin explored as both a diversifier and a timing candidate -- rejected on both

- **Diversifier**: full-sample corr to AVGO looks low (0.16) but is
  regime-dependent -- rises to 0.24-0.34 specifically in risk-on/credit-WIDE
  periods, i.e. weakest exactly when a hedge should earn its keep. Naive
  blend (adding 2-10% BTC) improves Sharpe full-sample but Sharpe improved in
  only 4/6 calendar sub-periods, worsening in the two most recent.
- **Timing**: walk-forward momentum/MA200-distance/depth-off-ATH signals for
  BTC's own entries showed "buy strength" beating "buy the dip" -- but this
  was pooled-sample noise. Split by actual halving cycle: HIGH-momentum
  bucket was the WORST place to be in both real bear markets (2018, 2022;
  0% win rate, -55% to -65% median forward 252d return). No timing edge
  survives cycle-conditioning.

### 3. AVGO-diversifier screen: ADDT_B_ST (Addtech) is the one candidate that survives

Scanned the full local universe (555 tickers) for a candidate that
improves CAGR, Sharpe AND MaxDD simultaneously when blended 5-10% into
Gold25/AVGO40/LLY35. ~30 passed a naive full-sample filter (mostly
correlated growth/tech names -- AMZN/NFLX/NVDA/AMD -- likely just adding
return, not real diversification). Applied the SAAB-style sub-period check
(see rule below) to the top candidates:

- **EVO_ST, SAAB_B_ST and everything else tested (ORLY/CASY/PGR/AZO)
  failed** -- only 3-4/6 sub-periods improved Sharpe; full-sample result was
  carried by 1-2 strong early years.
- **ADDT_B_ST (Addtech, Swedish industrial conglomerate) passed both checks**:
  Sharpe improved in 6/6 calendar sub-periods AND 7/7 regime buckets
  (ry_regime x baa10y_regime), 17yr history, corr to AVGO 0.20 full-sample
  (rises to ~0.24-0.29 in WIDE-credit regime -- same directional pattern as
  BTC, just much weaker). Independently re-verified with a second,
  non-pandas implementation (plain-loop NAV/drawdown calc) -- matched to
  within floating-point noise.

**Job it does in the portfolio**: smooths day-to-day vol and adds solid
standalone return (27.5% CAGR) -- it is NOT a crash hedge. In the
portfolio's actual worst historical drawdown it moved with AVGO, not against
it, which is why MaxDD/Calmar get *slightly worse* even as CAGR/Sharpe/vol
all improve. Two different statistics measuring different things (typical
day vs. worst day) -- don't expect this to cushion the next real crash.

### 4. Funding mechanism matters more than the asset itself -- FI@50 outlook check

Ran the block-bootstrap Monte Carlo (`run_outlook_montecarlo.py` methodology,
10k paths to 2038-10-10, target 20.8M kr) for two ways of funding a 10% ADDT
sleeve:

- **Funded specifically from AVGO** (40% -> 30%): best portfolio-level
  Sharpe/MaxDD (1.57 / -22.0%, both better than baseline), but **HURTS the
  actual goal** -- P(reach target) drops 66.8% -> 60.7%, median terminal TPV
  -2.2M kr. Cutting the highest-CAGR leg for a smoother ride costs real odds
  on a hard-date wealth target. **Rejected.**
- **Funded pro-rata** (all three legs trimmed proportionally): worse-looking
  portfolio stats (Sharpe 1.54, MaxDD -24.8%) but **helps the goal** --
  P(reach target) 66.8% -> 69.5% (+2.6pp), median TPV +685k kr, for only
  +0.7pp worse drawdown-tail risk. **This is the version worth doing, if
  either.**

Lesson: portfolio-level Sharpe/MaxDD and goal-level P(reach target) can point
in opposite directions depending on *which* leg funds the new position --
always check both before concluding a change "helps."

### 5. Status: decision leaning yes, NOT YET EXECUTED -- SUPERSEDED, see the "holdout-verified and REJECTED" entry above. Do not execute the rebalance below.

Final call was "reasonable small bet, not a must-do" -- +2.6pp target-hit
probability for real single-stock concentration risk (10% in one Swedish
industrial name) and inherent data-snooping risk (1-of-555 screen survivor,
even though sub-period/regime-robust). Computed the concrete rebalance
(live prices, 2026-08-20): current live holdings had already drifted off the
25/40/35 target (~28/41/30 actual) before this trade. Target: Gold 304->238,
LLY 31->23, AVGO 73->92, ADDT_B_ST 0->261 shares. **`portfolio.toml` was NOT
updated** -- operator has not placed the trade yet. Next session: check
whether the trade was executed; if so, update `config/portfolio.toml`
(new ADDT_B_ST position + adjusted share counts) in a branch+PR.

Also noted in passing: PR #73 (`docs/avgo-staged-entry-decision`) has been
open since 2026-07-15 -- over a month stale. Not touched, flagging for
operator to close or merge.

## Session 2026-08-19: the dashboard was measuring against the wrong goal (PRs #102, #103 -- MERGED, tagged v0.2.0)

Review of portfolio construction + performance vs FI@50 target alignment.
**Construction itself came out clean and is unchanged** -- 25/40/35 with a
10pp band, full sample 2009-2026 CAGR 30.3% USD / 32.5% SEK, Sharpe 1.40,
MaxDD -23.3% / -28.0% SEK, beating SPY and both individual legs on
risk-adjusted terms; PR #99 already established nothing findable beats it
out of sample. **Every finding below is about the wrapper around the
allocation, not the allocation.** Three fixes shipped together.

### 1. `target_sek` was still the retired 12.93M figure -- now real and indexed

The 2026-08-18 derivation concluded `target_sek = 12_934_706` was wrong by
~25% but deliberately left the config alone pending an SWR call. It was
never revisited, so `status.md` printed **"BEHIND -1.7%"** every day against
a threshold nobody endorsed. Against the real bar the gap is **-7.3%**.

`config/portfolio.toml` `[fi]` now carries the 3.5%-gross row (the one
marked "chosen" in the derivation) in real terms plus an indexing rate,
replacing the flat nominal field:

```toml
target_real_sek  = 16150000   # 2026 kr
target_base_year = 2026
target_inflation = 0.02
```

The other two SWR rows are in a comment so switching is a one-line edit.

**Indexing was the missing half, not a nicety.** The trigger is wealth-based
and can fire in any year, so a fixed nominal number is wrong the moment it
is written. `portfolio._fi_target(fi, years_ahead)` returns the bar at any
horizon, and `fi_pace()` now reports three distinct numbers that were
previously collapsed into one and are easy to confuse:

| | value | what it is |
|---|---|---|
| Threshold (2026 kr) | 16,150,000 | the real, indexed bar |
| Trigger now | 16,352,649 | what TPV would have to be TODAY |
| Trigger @ horizon | 20,798,454 | what `required_cagr` is solved against |

Required CAGR moved **19.7% -> 24.8%** on identical TPV and horizon. AWAR is
+17.6%, so the honest margin is -7.3%, not -1.7%.

**Knock-on bug found and fixed in the scenario table.** `years_to_reach_target()`
solved against a frozen bar, so a path that merely beat inflation still
"reached" FI. It now takes `target_inflation` and grows the bar alongside the
portfolio (default 0.0 reproduces the old behaviour exactly; a test asserts a
path growing at exactly the indexing rate returns `inf`). The FI-date column
also had `2026 +` hardcoded as its year base. Combined effect: Bear moved
~2047 -> ~2056, Base ~2038 -> ~2041.

`run_outlook_montecarlo.py`'s own hardcoded `TARGET_SEK = 12_934_706.0` was
the same stale figure and now reads config too.

### 2. Idle cash was sitting in the rebalance band denominator

`fi_tracker.py`'s `_rc_total` included the manual `Reactor Core Cash` row, so
every leg weight was scaled by (1 - cash%) and every reported gap widened by
that factor. Live effect on 2026-08-19: **AVGO read -10.9% against a 10% band
and printed `BUY -- ~27 shares (~98,552 kr)`, when its real drift against the
invested book was -9.7%, i.e. inside the band.** The alert was firing on the
cash balance, not on drift, and would have fired on all three legs at once
had cash grown further.

Denominator is now invested Reactor Core capital only (share positions,
excluding no-ticker manual rows). Weights sum to 1.0 again; all three legs
read HOLD. Cash is not thereby ignored -- it gets its own **Idle Reactor Core
Cash** line reporting the deployable amount and routing it to the most
underweight leg (35,830 kr -> 9 AVGO shares today). **Drift rebalancing and
cash deployment are two different actions; one number could not carry both.**

Same class of bug as PR #100's stale alert strings: a live instruction
computed off the wrong source. Worth checking any other denominator in this
repo that sums a bucket rather than its invested subset.

### 3. Bucket targets had two live values and no single source

MEMORY.md carried **83.3/16.7** (2026-08-04, war-chest suspension) and
**85/15** (2026-08-17) as if both were current, and the only code that
consumed a bucket target was a hardcoded `0.85, 0.0, 0.15` in
`run_outlook_montecarlo.py` -- so the Monte Carlo priced the odds for 85%
while the portfolio actually sat at 81.9%.

Now a `[buckets]` table in `config/portfolio.toml`, read by the Monte Carlo
and printed daily by the tracker as target/drift alongside each bucket's
actual. The 2026-08-04 entry is marked superseded in place (the war-chest
suspension it records still stands; only the split figures were stale).

**Ceiling re-examined and 85% REAFFIRMED as the operating target
(2026-08-19).** 85% sits above the drawdown-ceiling method's honest
post-guard-retirement range of 48%-82%. That was put to the operator
explicitly, twice, with the breach in view, and 85/15 was confirmed as the
target to execute -- not merely to record. An earlier draft of this entry
recommended leaving the split at its drifted 82%; that recommendation is
withdrawn.

The 82-vs-85 comparison, for the record:

| | 82% | 85% |
|---|---|---|
| Terminal wealth | -- | +1.8% to +2.5% |
| MaxDD, AVGO regime | -23.0% | -23.8% |
| MaxDD, TXN stress | -35.9% | -37.2% |

**Neither weight is defensible on the -25% tolerance** -- both blow through
it in a 2000-style regime, so Home Base at this size is not buying the
protection the ceiling method assumes it does. Given that, 1.3pp of
drawdown for ~2% terminal is a rounding error, and the 3pp goes to the
higher-returning asset. Home Base earns ~2.5% nominal, which is **-0.4%
real** after ~0.9% ISK drag and 2% inflation -- certain cost against an
uncertain hedge.

**The live open question this leaves** (worth answering, not urgent): is
-25% still the operator's real deviation threshold? If yes, no weight above
~57% complies and the whole sizing needs redoing. If it was aspirational and
-37% would in fact be held through, the ceiling method should stop being
used to size this bucket at all. Reaffirming 85% twice with the breach
visible points at the second, but it has not been stated outright.

### Left for the operator, not code

- **Deploy the 35,830 kr.** Worth +160k to +557k terminal at 15%-26% core
  returns. Requires an Avanza trade and a share-count sync; the dashboard now
  states the instruction but cannot execute it.
- **Contribution rate is the only remaining lever**, and it dwarfs everything
  above: 6,000 -> 25,000 kr/mo moves required CAGR 24.8% -> 18.5%. Everything
  fixed in this session is worth ~3% terminal; this is worth ~6pp of required
  return. Re-derived against the corrected threshold this session:

  | Contribution | Required CAGR |
  |---|---|
  | 6,000 kr/mo (today) | 24.8% |
  | 10,000 | 23.3% |
  | 15,000 | 21.5% |
  | 18,256 | 20.5% |
  | 25,000 | 18.5% |

- **No actual-contribution ledger exists.** The tracker assumes 6,000 kr/mo
  as an axiom, so AWAR and every projection are wrong by however much the
  real rate differs. Cheapest remaining accuracy win in the repo; not built.
  **This is the agreed next task.**

### 4. Delisted tickers were silently staling the whole local store (PR #103)

Found while checking why a trade instruction had been priced off an old
close. `check_local_data_freshness.py` had been reporting `refresh FAILED`
on every local run: `EA` (taken private, last bar 2026-08-10) and `SATS`
(last bar 2026-07-17) were still in `us_equities.txt`, yfinance returns
nothing for either, `asset_universe.update` exits non-zero, and the freshness
script treats that as the entire refresh having failed. Store sat a day
behind while every script read it without complaint.

**It produced a real wrong number in this very session:** a local
`fi_tracker.py` run priced AVGO off the 08-17 close and reported drift as
+8.6% when the 08-18 figure was +9.66%.

Both removed, with a header comment so a regenerated S&P constituent list
does not re-add them, plus a test asserting they stay out. **Their parquets
are deliberately kept** -- delisted history cannot be refetched, and the
screen's M&A/history gates already exclude them from ranking.

`fi_tracker.py` now reads the same freshness check and prints a stale banner
at the top and again above NEXT CONTRIBUTION (~700 lines down, and the part
that gets acted on). **Warn only, never non-zero** -- `sync.yml` pipes this
script into `status.md`, so aborting would blank the dashboard on a day the
market simply has not closed. The gate that does fail the pipeline already
runs earlier in `sync.yml`.

### PENDING TRADE -- decided, not executed (2026-08-19)

Operator confirmed **85/15** and approved the rebalance. Not executed at
session end; needs an Avanza trade. Sized on the 2026-08-18 close:

| # | Action | Amount |
|---|---|---|
| 1 | SELL Spiltan Räntefond | ~32,911 kr -> Home Base 166,127 (15.0%) |
| 2 | BUY 19 AVGO @ ~3,613 kr | ~68,647 kr (35,830 idle cash + 32,911 from HB) |

Lands the bucket split exactly on 85.0/15.0 and cuts leg drift from 9.8% to
4.7%. Leaves ~94 kr cash. **Re-price before executing** -- share count moves
with the close.

**After executing:** update `Spiltan Räntefond` `value_sek` -> 166,127 and
`Reactor Core Cash` -> 94 in `config/portfolio.toml`, or sync the Sheet.

**Timing note:** AVGO's drift closed the session at **+9.8%, 0.2pp from the
10% band**. If it drifts further the band fires on its own and the rebalance
becomes forced rather than chosen. The dashboard's own cash line says 9
shares, not 19 -- that is correct, not a contradiction: it only sees the
35,830 kr inside Reactor Core. The other 10 shares are funded by the
bucket-level Spiltan sale, which no script models by design.

### OPEN QUESTION worth answering before the next sizing decision

**Is -25% still the operator's real deviation threshold?** It is currently
used to derive the Reactor Core ceiling, but *no weight in live use
satisfies it* -- 82% gives -35.9% and 85% gives -37.2% in the TXN stress
analog. Either:

- -25% is real, in which case nothing above ~57% complies and the whole
  bucket sizing needs redoing; or
- it was aspirational and a -37% path would in fact be held through, in
  which case the ceiling method should stop being used to size this bucket.

Reaffirming 85% twice with the breach explicitly in view points at the
second, but the operator has not stated it outright. **Do not re-derive the
ceiling until this is settled** -- it is the input, and it is unverified.

## Session 2026-08-18: goal derivation, three null results, one live alert bug

Long session. Ordered by what matters.

**1. LIVE BUG FIXED (PR #100).** `fi_tracker.py`'s Silver GSR action strings
were hardcoded prose and had gone stale against the old 25/55/20 base -- T1
said "AVGO -> 43%", T2 "AVGO -> 38%", exit "back to 55%", against a table
saying 28/23/40. **That string is echoed verbatim into the Telegram alert**,
so a fired GSR trigger would have instructed a ~15pp wrong AVGO trade. Not
yet fired (GSR 67.8 vs T1 83.36). Now read from
`run_combined_system.WEIGHTS` so it cannot drift again. **Lesson: any alert
that restates a number in prose will eventually contradict its source. Point
it at the source.** The AVGO guard alert was checked and is CORRECT -- the
"Rotate AVGO" wording that looked alarming lives only in
`preview_all_triggers.py`'s fixture, now refreshed.

**2. Clean-sheet portfolio search: nothing better exists that is findable
(PR #99).** `run_clean_sheet_search.py` -- 433 ROBUST assets, 279,720
weighted 3-asset portfolios, selected on 2009-2017 and judged on 2018-2026.
**0 of the top 100 in-sample portfolios beat the incumbent out of sample.**
In-sample winners score Calmar ~3.0 and collapse to 0.24-0.42 OOS; the
incumbent goes 1.746 -> 1.529. Most in-sample winners were built on
SCA-B.ST. **Caveat that must travel with this result: it does NOT validate
the incumbent, which was itself chosen knowing the post-2018 window.** The
honest claim is only that search-based selection does not transfer -- the
third time this repo has found that.

**3. Swedish large caps added (PRs #97, #98).** 41 Nasdaq Stockholm names,
new `se_equities` category, screen now reads them from the store instead of
a hardcoded 15-name live-fetch list that omitted SAAB and carried a dead
Hexagon ticker. SAAB looked like the first real hedge (0.11 beta to the
AI-semi basket) and isn't -- 0.23/0.27/-0.02 by sub-period, all of it
post-Ukraine. Gold is 0.16/0.13/0.10, stable, which is why it holds its
slot. Best Swedish names rank 38-84 of 566; none displaces anything.

**4. Contribution timing does not work (PR #96).** Both the
withhold-from-DCA version and the operator's better-designed
outside-cash version. -6.2% to +3.0% vs pure DCA, non-monotonic, negative
in the stress regime. **Contribution RATE is the lever, timing is not.**
Deploying capital you already hold at a trigger is still fine; manufacturing
it by not investing is not.

**5. Outlook Monte Carlo refreshed (PR #95)** to the live config and the
real horizon. See the FI@50 entry below for what it produced.

**LLY note:** it screens at rank 389/566 (+5.9% median, 64% win). That flag
was raised and WITHDRAWN -- the screen conditions over 2004-2026 and LLY was
an ordinary pharma for most of it; the GLP-1 franchise only became material
from ~2022. **General limitation worth remembering: the conditional screen
has no concept of a structural break and will score any changed company on
its old self.** LLY is also the best performer since inception (+54% vs AVGO
+35%, gold +28% in SEK). No action.

**Still open:** PR #73 (docs, open since 2026-07-15) and local branch
`research/pead-reconstruction`, both predating this session.

## Swedish large caps added; SAAB is NOT a hedge (2026-08-18, PR #97)

**Gap closed:** Swedish equities were absent from every universe file even
though the 2026-06-26 screen had 13 of them (Investor B 11th of 490 by
Sharpe). No rationale was ever recorded for dropping them. Added 41 Nasdaq
Stockholm large caps (`config/universes/se_equities.txt`, new `se_equities`
category in `update.py`), most with ~26yr history.

**`run_ai_basket_beta.py`** rebuilds the 2026-08-16 hedge screen (original
script deleted per convention). USD pass reproduces every published value
within 0.01 (SPY 0.42, QQQ 0.54, AMZN 0.53, LLY 0.23, GC_F 0.05) -- that is
what validates the rebuild. Adds a SEK pass, since the original table was
all-USD and a USD asset gains SEK value when USD strengthens.

**SAAB screens beautifully and fails on inspection.** Full-sample SEK basis:
beta 0.11 / corr 0.13 -- better than gold (0.12), far below LLY (0.28). But
by sub-period:

| | 2012-2017 | 2018-2021 | 2022-2026 |
|---|---|---|---|
| SAAB-B.ST | 0.23 | 0.27 | **-0.02** |
| AZN.ST | 0.18 | 0.09 | -0.07 |
| TELIA.ST | 0.18 | 0.16 | -0.04 |
| INVE-B.ST | 0.26 | 0.25 | 0.14 |
| **GC_F** | **0.16** | **0.13** | **0.10** |
| LLY | 0.39 | 0.40 | 0.18 |

SAAB was ordinary before 2022 (0.23-0.27, no better than Investor B). Its
entire edge is the post-Ukraine rearmament window -- one regime, one
exogenous event, the same single-path signature already rejected elsewhere
in this project. **Gold's 0.16/0.13/0.10 stability is what a real hedge looks
like, and is why it holds its slot.**

**Verdict: not adopted.** The 2026-08-16 conclusion stands -- AI-thesis
exposure and decorrelation are mutually exclusive. **Reusable lesson: always
sub-period a full-sample beta before believing it.** A single regime can
carry the whole number.

## Contribution-splitting to dip-buy: NO EDGE, do not build it (2026-08-18, PR #96)

**Question:** keep a regular monthly DCA tempo but hold part of it back as cash
and deploy the pile into AVGO at crash-ROC triggers -- better than investing
every contribution immediately?

**Answer: no.** The dip-buying half was already validated (see "Gap-down tranche
validated", 2026-08-14) but the **cost of waiting** never was. Triggers fire
~twice a year, so held-back cash sits idle **~93% of days**, and that drag
exactly cancels the dip edge.

`run_contribution_split_test.py`, terminal wealth vs pure DCA:

| Contribution | AVGO actual (best -> worst) | TXN analog (best -> worst) |
|---|---|---|
| 6,000 kr/mo | +4.4% -> -1.1% | -1.4% -> -3.7% |
| 18,256 kr/mo | +0.8% -> -1.6% | -2.2% -> -3.8% |
| 36,236 kr/mo | +0.9% -> -3.4% | +0.6% -> -6.2% |

**Non-monotonic at every contribution level** (75% holdback best at one, 25% at
another, 100% at a third) -- noise, not signal. **Consistently negative in the
TXN stress regime**, i.e. it hurts most in the regime it was meant to help.

Why the event study and the portfolio sim disagree: the 2026-08-14 test measured
each of 32 triggers independently, which prices the dip edge but never charges
for the idle time between them. Both results are correct; they answer different
questions. **Deploying capital you already have at a trigger is still good;
manufacturing that capital by not investing is not.**

Executes every trigger at the NEXT session's close, so this does not repeat the
lookahead bias that invalidated the 200d guard. Self-check asserts holdback=0%
reproduces pure DCA exactly. Printed CAGR column is a TPV-growth rate including
contributions, NOT an investment return.

**Implication for the FI@50 plan: contribution *rate* is the lever, contribution
*timing* is not.** See the entry below.

## FI@50 goal DERIVED from actual income need -- the 12.93M target was wrong by ~60% (2026-08-18)

**First time the objective has been derived from the operator's real spending
rather than inherited as a number.** Everything below supersedes
`target_sek = 12_934_706` in `config/portfolio.toml`, which is now known to be
optimistic on three counts simultaneously (4% rule, no ISK tax drag, no
inflation indexing). The config value was NOT changed -- see "open" at the end.

**Stated goal:** the *option* to stop working at the FI horizon date. Horizon
end is **2038-10-10** (12.15 yrs from 2026-08-18). The income requirement it is
sized against is deliberately not recorded here -- this repo is PUBLIC. It lives
in the operator's personal memory (`[[user-income-savings-capacity]]`), along
with the expense base and salary figures. Everything below is the derived
result, which is what the repo needs.

**Horizon config fixed (commit 96c983f, master):** `years` 12 -> **13.223**,
so `start_date` 2025-07-21 + 13.223yr lands exactly on 2038-10-10. It had been
reporting 10.9 years remaining; now 12.15. Field is consumed as a float
(`portfolio.py: years_left = years - years_elapsed`), no code change needed.

### "Living off yield" is structurally impossible with this portfolio

Blended dividend yield is **~0.7%** (Gold 0%, AVGO ~0.6%, LLY ~0.5%, Home Base
~2.5%). Funding the target income from actual yield would need roughly **76M
kr** -- about 4.7x the threshold below.
The plan is therefore total-return withdrawal (sell a little each year), not
yield. Worth stating explicitly because the operator's own framing was "living
off yield" and it does not survive contact with a 25/40/35 gold-heavy mix.

### Conversion threshold (the number that matters)

Retiring at 50 implies a **35-45 year** drawdown horizon, not the 30 years the
4% rule was built on. Defensible gross SWR is 3.0-3.5%. **ISK drag** --
schablonintakt = (SLR + 1pp) taxed at 30%, ~**0.9% of capital per year** at
SLR ~2% -- comes straight off it, since it is paid regardless of returns.

| Gross SWR | - ISK drag | Net for living | Capital (2026 kr) |
|---|---|---|---|
| 4.0% | 0.9% | 3.1% | 13,548,000 |
| **3.5% (chosen)** | 0.9% | **2.6%** | **16,154,000** |
| 3.0% | 0.9% | 2.1% | 20,000,000 |

**Trigger is WEALTH-based, not age-based** -- and must be inflation-indexed
since the date it fires is unknown:

```
Convert to income portfolio when TPV >= 16,150,000 x 1.02^(year - 2026)
```

= **~20,550,000 kr nominal if it fires in 2038.** Cross it at 46 and convert at
46; sit at 8M at 50 and do not convert. **The option exists when capital crosses
the threshold, not when the operator turns 50.** A calendar glidepath was
explicitly rejected: it can force selling into exactly the -37% stress path that
removes the option, and it contradicts the same "don't trim strength on a
schedule" logic that killed vol-targeting and the 200d guard.

**Do NOT restructure toward income now.** At 1.1M TPV yield would produce ~8,000
kr/yr -- irrelevant. Accumulation stays max-growth; conversion is a future event
with a defined trigger, not a current allocation question. (Operator pushed back
on an earlier framing that implied otherwise, and was right.)

### Required return, and why "more confidently" is the wrong ask

| Window | 20M | 22M |
|---|---|---|
| **2038-10** (12.15y) | **24.4%** | 25.4% |
| 2035-10 (9.1y) | 34.7% | 36.2% |

Against the portfolio's own blended backtest: **26.1%** (AVGO-actual regime) /
**11.3%** (TXN analog). So:

- **2035 is out.** ~35% sustained for 9 years is not deliverable by anything in
  this repo's tested universe.
- **2038 at 20-22M needs ~25%,** i.e. it only clears in the optimistic regime.
  This is exactly the ~50/50 the refreshed Monte Carlo priced (PR #95).
- **"Build a portfolio that more confidently reaches 20-22M" is self-
  contradictory.** 24.4% for 12 years only comes from concentrated, high-variance
  bets. Every confidence-raising move (diversify, cut AVGO, add a 4th asset)
  lowers expected return and makes 20M LESS likely. Consistent with the
  2026-08-16 hedging finding that AI-thesis exposure and decorrelation are
  mutually exclusive.

**The current portfolio is already close to the max-growth configuration
available from this repo's own validated research. There is no better allocation
waiting to be found.** The gap is not the allocation.

### The one lever that is not the portfolio

Monthly contribution needed for 20M at 2038-10:

| Contribution | Required CAGR |
|---|---|
| 6,000 kr (today) | 24.4% |
| 18,256 kr | 20.0% |
| 36,236 kr | 15.0% |

Tripling contributions moves the required return from "needs the exceptional
regime" to "plausible in a middling one." **It is the only lever that raises
confidence without costing expected return**, and the only one independent of
what the market does.

### Deliberately excluded, and open

- **Pension excluded by operator's explicit choice** ("I will certainly have a
  pension, I don't want to take it into account at this time"). Allmän +
  tjänstepension from ~65-67 would cut the threshold materially -- the portfolio
  currently assumes it funds everything forever, which is the conservative
  anchor, not the likely case. **Largest single reducer available; revisit when
  the operator wants it in.**
- `target_sek` in `portfolio.toml` still reads 12,934,706 and is now known to be
  wrong. Not changed pending the operator's call on which SWR row to adopt.
- 2038 Swedish ISK rules are unknowable; 0.9% drag is a present-rules
  approximation. 2% inflation is an assumption, not a forecast.

## AVGO vol-targeting: shipped edge does NOT reproduce -- live routing is running on an unverified mechanism (2026-08-18)

**Finding: the CAGR/MaxDD improvement that justified shipping vol-targeting
(PR #91, "AVGO volatility-targeting SHIPPED" entry below: normal CAGR
30.15%->30.79%, Calmar 1.288->1.426; stress CAGR 13.43%->13.93%, Calmar
0.267->0.315) does not reproduce.** A faithful, self-checked rebuild
(`run_vol_target_validation.py`, new, committed) shows the shipped
mechanism -- SYMMETRIC realized-vol scaling, exactly as it runs in
production -- LOSING to plain static weights on CAGR, Sharpe, and Calmar in
BOTH the normal and stress windows:

| Dataset | Variant | CAGR | Sharpe | MaxDD | Calmar | Trades/yr |
|---|---|---|---|---|---|---|
| Normal (AVGO, 2009-2026) | STATIC | 30.58% | 1.433 | -23.45% | 1.304 | 0.0 |
| Normal | SYMMETRIC (shipped) | 23.66% | 1.183 | -21.49% | 1.101 | 18.4 |
| Normal | DOWNSIDE (tested, not shipped) | 22.55% | 1.136 | -19.63% | 1.148 | 20.0 |
| Stress (TXN, 2000-2026) | STATIC | 13.56% | 0.743 | -42.59% | 0.318 | 0.0 |
| Stress | SYMMETRIC (shipped) | 10.24% | 0.575 | -50.91% | 0.201 | 8.4 |
| Stress | DOWNSIDE | 8.97% | 0.520 | -54.48% | 0.165 | 10.1 |

**Why this is trusted, not just another disagreeing number:** the original
2026-08-17 research script was never committed -- only its conclusion
reached this file. A first reproduction attempt disagreed sharply, which by
this project's own established rule (see the split-adjustment bug and
`fi_pace()` bug, both caught the same way) means "find the bug before
reporting the new number," not "trust either number." Investigation found:
1. `comparison_results/base_optimizer_grid.csv` (from the older, already-
   committed `run_base_optimizer.py`) has a THIRD, also-disagreeing number
   for the same Gold25/AVGO40/LLY35 static baseline (CAGR 22.45%, Calmar
   0.686) -- proof this repo has never had one canonical, reused backtest
   convention for the live base, not just a one-off gap.
2. `run_vol_target_validation.py`'s vectorized backtest computation was
   checked against actually CALLING the real, live
   `compute_vol_target_weights()` (imported, not hand-copied) at 25 dates
   sampled across the full 2009-2026 history, each truncated to only the
   data that would have been known on that date. **Every sample matched to
   0.00e+00 -- exact.** This rules out transcription drift as the source of
   the disagreement.
3. Its rebalance frequency (18.4 trades/yr) independently matches this
   project's own documented figure for the 5% band ("~19 trades/yr", see
   `REBAL_BAND`'s docstring in `vol_target.py`) -- confirms the
   band/TC/simulation convention matches what was actually parameter-swept
   at the time, not a different mechanic.

**Conclusion: the mechanism itself (self-check-verified against production
code) does not have the edge that was claimed for it. The 2026-08-17 research
script, now unrecoverable, most likely had a real bug** -- most probably in
its rebalance/TC simulation, since the vol FORMULA itself is proven correct
by the self-check. Also tested a downside-only (semi-deviation) variant, on
the hypothesis that the symmetric version wrongly trims AVGO into genuine
rallies (up-moves inflate realized vol same as down-moves) -- it does NOT
fix the underperformance either; worse on CAGR/Sharpe/Calmar than symmetric
in the stress window.

**Follow-up same day, `run_vol_target_robustness.py` (new, committed):
resolved from "doesn't reproduce" to "doesn't work," decisively.** Two real
confounds were flagged and closed before trusting the verdict above as more
than a single disagreeing number:

1. **Sub-period test** (same anti-fitting method as the 2026-08-16 base-mix
   research, `[[project-reactor-core-mix]]` in the operator's personal
   memory -- rank on the WORST sub-period, never full-sample): tested
   whether STATIC's win was an artifact of AVGO's exceptional 2023-2026
   AI-melt-up dominating the full-sample average. **It is not.** STATIC
   beats SYMMETRIC in every sub-period tested: AVGO 2009-2017 (Calmar 1.82
   vs 1.24), AVGO 2017-2026 (1.56 vs 1.33), AVGO with the AI-melt-up
   entirely EXCLUDED, 2009-2022 (1.06 vs 0.86), and even INSIDE the
   AI-melt-up alone, 2023-2026 (2.66 vs 2.64) -- plus both TXN stress
   sub-periods (2000-2013 incl. dot-com/GFC, and 2013-2026).
2. **Parameter grid** (VOL_WINDOW in {10,15,21,30,42} x REBAL_BAND in
   {3%,5%,8%}, clip bounds held at shipped 0.3x-1.3x -- same rigor as the
   AVGO guard's own 20-cell validation grid): SYMMETRIC beats STATIC on
   Calmar in **0 of 15 cells, normal window; 0 of 15 cells, stress window.
   0/30 total.** Not fragile-but-sometimes-works -- never wins, anywhere in
   the swept space, in either regime.

3. **Apples-to-apples rebalance mechanics** (section C, added after a
   validation pass caught a real flaw in 1 and 2 above). The convention
   inherited from `run_combined_system.py` reapplies the locked target fresh
   every day and charges TC only when the TARGET changes -- which for a
   FIXED static target silently means **free daily rebalancing** (confirmed:
   static scores 30.58% with TC forced to zero, i.e. identical to its 30.64%
   headline -- it never paid a cost at all). That flattered static by ~1.6pp
   CAGR against any moving-target strategy. Re-ran with realistic weight
   drift and identical mechanics for both modes (`simulate_real_drift`):

   | Band | NORMAL static | NORMAL sym | STRESS static | STRESS sym |
   |---|---|---|---|---|
   | 3% | 27.49% / 1.138 | 18.28% / 0.824 | 10.65% / 0.207 | 6.41% / 0.104 |
   | 5% | 29.02% / 1.220 | 23.58% / 1.065 | 11.90% / 0.244 | 9.17% / 0.160 |
   | 8% | 29.79% / 1.332 | 26.10% / 1.156 | 12.71% / 0.281 | 10.56% / 0.191 |
   | 15% | 31.05% / 1.375 | 29.42% / 1.280 | 13.71% / 0.302 | 11.34% / 0.213 |

   (CAGR / Calmar.) **Static still wins at every band in both regimes** --
   the correction narrows the gap but does not reverse it anywhere.
   Critically, in the STRESS window vol-targeting makes MaxDD *worse*, not
   better (-57.2% vs -48.7% at the 5% band), so it is not even buying
   drawdown protection in the regime it was meant for.

**Verdict, now well-earned: volatility-scaling AVGO's weight this way does
not add value. Not a bug in one number -- a mechanism that loses to doing
nothing, robustly, across every regime and every reasonable parameter choice
tested.** This is now as thoroughly validated a NEGATIVE result as any
positive one shipped in this project.

**EXECUTED 2026-08-18 (branch `fix/retire-vol-targeting-widen-band`), on
explicit operator instruction:**
- `fi_tracker.py` NEXT CONTRIBUTION routing and the AVGO Rebalance Check
  both now use the STATIC base row (`WEIGHTS[(False, silver_state)]` =
  Gold 25 / AVGO 40 / LLY 35). Both read the same `_target_weights`
  variable, so they can never disagree.
- `compute_vol_target_weights()` kept and still printed, but relabelled
  DIAGNOSTIC ONLY ("RETIRED 2026-08-18", "Would-be weights", "NOT ACTED
  ON") -- same precedent as the retired AVGO 200d guard's trend
  diagnostic. Not deleted: the validation scripts need the live function
  to self-check against.
- `REBAL_BAND` 0.05 -> **0.10** (reasoning and the full band table are in
  `vol_target.py`'s own comment; 10% over the marginally-better-testing
  15% because >20% is known non-monotonic and a wider band lets AVGO drift
  further before trimming, which interacts badly with AVGO's documented
  single-name concentration risk).
- Live-verified by a real `fi_tracker.py` run, not just tests: routing now
  targets AVGO 40.0% (was 33.5% vol-targeted), band displays 10%.
  395 tests pass.

**Immediate consequence worth knowing, surfaced by that live run: the
2026-08-17 trade moved the portfolio AWAY from the static target.** It sold
AVGO 101->73 shares to reach the vol-targeted 33.5%; against the static 40%
target AVGO now sits at 30.2%, i.e. **9.8pp UNDER target**. NEXT
CONTRIBUTION accordingly now routes the next kr to AVGO. Note this gap
(+9.8%) sits just inside the newly-widened 10% band, so the Rebalance Check
reads HOLD rather than BUY -- at the previous 5% band, or at 8%, it would
have fired a BUY instruction. The 10% choice was made and documented before
that live run, on the concentration/stability grounds above, not fitted to
this outcome -- but the coincidence is close enough to be worth stating
plainly. **Net effect: no reversing trade is forced; the gap closes
naturally through ongoing contributions instead.**

**Original recommendation, now superseded by the block above:**
`fi_tracker.py`'s "NEXT CONTRIBUTION" routing and the AVGO Rebalance
Check/Telegram alert are both currently live against vol-targeted weights
(see entries below), and already produced one real executed trade
(2026-08-17: AVGO 101->73 shares, LLY +15 shares, War Chest drawn to ~27
kr -- see "Rebalance executed" entry below). Given the robustness result
above, reverting routing to the static 40% weight and disabling further
vol-target-driven Rebalance Check alerts is the recommended next step --
not yet executed, pending explicit operator confirmation since it's a
live-money-routing change.

**Separate, independently useful result found while validating the above --
the static base's own rebalance band is worth widening.** Static
Gold25/AVGO40/LLY35 under realistic drift, band swept (buy&hold row
cross-validated against a fully independent fixed-share computation --
exact match on CAGR/MaxDD/Sharpe/Calmar in both regimes):

| Band | NORMAL CAGR / MaxDD / Calmar | STRESS CAGR / MaxDD / Calmar |
|---|---|---|
| 0% (daily) | 11.79% / -26.20% / 0.450 | -1.55% / -86.30% / -0.018 |
| 3% | 27.45% / -24.15% / 1.136 | 10.88% / -48.49% / 0.224 |
| **5% (live today)** | 29.03% / -23.79% / 1.220 | 12.02% / -45.74% / 0.263 |
| 8% | 29.72% / -22.36% / 1.329 | 12.43% / -44.24% / 0.281 |
| 15% | 31.01% / -22.42% / 1.383 | 13.46% / -43.99% / 0.306 |
| never (buy&hold) | 34.66% / -38.52% / 0.900 | 11.76% / -35.92% / 0.327 |

Daily rebalancing is actively destructive (TC friction alone turns the
stress window negative). Wider bands beat 5% on BOTH CAGR and Calmar in both
regimes, and the ranking is stable across sub-periods (15% best in 4 of 5
tested, 10% in the other) -- not a single-path artifact. Consistent with the
2026-08-17 finding that >20% goes non-monotonic/unstable, so ~10-15% looks
like the safe upper edge, not "wider is always better." **Not changed
live** -- `REBAL_BAND = 0.05` still stands in `vol_target.py`; flagged as a
real, separately-actionable improvement to decide on alongside the routing
question above. Data: `comparison_results/static_band_sweep.csv`.

**Reusable lesson, now demonstrated a third time in this project (see the
split-adjustment bug and the `fi_pace()` bug for the first two): a backtest
result that isn't checked against a second, independent implementation
before shipping is not actually validated, no matter how confident the
research session was.** `run_vol_target_validation.py` is built to the
`run_crash_guard_validation.py` / `run_joint_stress_validation.py` pattern
specifically so this doesn't happen a fourth time -- rerun it, don't
hand-verify, whenever this mechanism or its parameters are reconsidered.

## Rebalance executed against the vol-targeted mix (2026-08-17)

The AVGO Rebalance Check's opening reading fired for real
(AVGO 46.8% vs 33.5% target, LLY 22.3% vs 38.8% target, Gold in-band) and the
operator executed it, in two tranches, against live Google Sheet share counts
(pulled via `sync_sheet.py`, committed straight to `master` same as the
automated job -- `b17cbd1`, `40dc542`):

- **AVGO 101 -> 73 shares** (sold 28)
- **LLY 16 -> 24 -> 31 shares** (bought 8, then 7, across the two syncs)
- **War Chest 100,565 -> 27 kr** -- drawn to fund the buy, per the
  "War Chest -> 0" funding plan from the 2026-08-16 sizing decision (see the
  operator's personal memory file, `[[project-reactor-core-mix]]`)
- Reactor Core Cash left at **35,830 kr** buffer after the second LLY tranche

**Final state, re-verified via a live `fi_tracker.py` run: all three legs
HOLD.** Gold 27.3% vs 27.7% (gap +0.5%), AVGO 30.2% vs 33.5% (gap +3.3%), LLY
38.6% vs 38.8% (gap +0.2%) -- all inside the 5% band. Nothing left to trade;
next thing that can move these targets is the AVGO earnings print on
2026-09-02 (vol-targeting scalar) or a fresh volatility reading.

**Not touched:** the Reactor Core/Home Base 85%/15% split itself (currently
~82%/18%, per the 2026-08-17 sizing decision below) -- this rebalance only
worked the Gold/AVGO/LLY mix inside Reactor Core, not the bucket-level split.

## AVGO Rebalance Check + Telegram alert SHIPPED (2026-08-17, branch feature/avgo-rebalance-alert)

Closes the gap flagged right after vol-targeting shipped: that build only
routed NEW contributions against the vol-targeted weights. This makes
EXISTING capital actionable too, automated end-to-end.

- **`rebalance_instructions()`** (`vol_target.py`): per-asset (Gold/AVGO/LLY)
  current vs. vol-targeted weight, gap, and -- if the gap exceeds
  `REBAL_BAND` -- a trade size in kr and shares. Sized independently per
  asset (not netted against what a simultaneous sell elsewhere would fund)
  -- simpler and more robust for automation than a "who funds whom"
  allocator. Real float-precision bug caught by its own boundary test:
  0.40-0.35 computes as 0.050000000000000044 in Python, which would have
  fired a spurious trade exactly at a clean 5% band edge -- fixed by
  rounding to 1e-9 before the comparison.
- **`REBAL_BAND = 0.05`**, chosen from a real band-triggered backtest swept
  0%-8% (2009-2026): 5% gives ~19 trades/yr (vs ~252/yr unbanded, daily
  rebalance) and keeps Calmar at 1.420 vs the unbanded 1.483 (~96% of the
  edge retained). Every band tested still clearly beat the non-vol-targeted
  static base (Calmar 1.288).
- **`fi_tracker.py`**: new "AVGO Rebalance Check" section, own try/except
  (a failure here must never be mislabeled as a NEXT CONTRIBUTION failure,
  which already succeeded by the time this runs -- caught and fixed before
  shipping, they originally shared one except block).
- **Telegram/email alert wired into the EXISTING pipeline** (`notify_signal_changes.py`
  -- Telegram, retry, email fallback, CI-failure escalation, all already
  built for the guard/silver/sleeve alerts, zero changes needed there).
  `check_signal_changes.py` gained 6 new fingerprint fields
  (`rebal_{gold,avgo,lly}_status/_detail`) and a new alert block that fires
  ONLY on the HOLD -> SELL/BUY transition per asset (an asset NEWLY
  drifting out of band) -- same "alert on transition, not persisting
  state" convention as every other block in that file. The reverse
  (gap closing back to HOLD) stays silent, same as the earnings-reminder
  DUE -> not_due direction.
- Detail-field regexes scoped to `AVGO Rebalance Check.*?` prefix, not bare
  `"AVGO status:"` -- the PR #89 lesson (unscoped regex risk) applied
  proactively here rather than found the hard way.
- `check_sync_health.py` `REQUIRED_SECTIONS` extended with both new
  sections (Volatility-Targeted Weight, Rebalance Check) -- a silent
  disappearance now fails the health check loudly instead of degrading
  quietly.
- **End-to-end verified for real** (not just fixtures): ran `fi_tracker.py`
  live, simulated a real HOLD->SELL/BUY transition against the actual
  current portfolio (AVGO 46.8% vs 33.5% target, LLY 22.3% vs 38.8%
  target), confirmed `notify_signal_changes.py`'s message builder produces
  the correct Telegram body with real share counts, and confirmed
  unchanged->unchanged produces no message (no false-positive risk).
- 20 new/changed tests (9 in `test_vol_target.py`, 5 new in
  `test_signal_changes.py`, 1 fixture fix in `test_check_sync_health.py`),
  390 passing project-wide.

**Real reading 2026-08-17 that would have fired this alert:** AVGO 46.8%
actual vs. 33.5% target (SELL ~29 shares, ~107,382 kr), LLY 22.3% vs 38.8%
target (BUY ~12 shares, ~133,499 kr), Gold 30.5% vs 27.7% (within band,
HOLD). Not yet executed -- this is the recommendation, not a completed
trade.

## Reactor Core DECIDED at 85% / Home Base 15% (2026-08-17)

Operator's call, closing the open sizing question from the "CRITICAL: the
AVGO 200d guard's entire validated edge is lookahead bias" entry below
(honest unguarded range was 48%-82%; 85% sits just above even that
optimistic bound). Decided, not re-derived from the drawdown-ceiling method
-- explicit trade-off accepted between the ceiling math and Home Base's
role as a behavioural/rainy-day buffer, not a purely risk-capacity-sized
number. Not yet executed against live TPV.

## AVGO volatility-targeting SHIPPED (2026-08-17, branch feature/avgo-vol-targeting)

Builds the one mechanism that survived the split-candidate sweep directly
below -- see that entry for the backtest/stress-test evidence. Live now,
not just a research result:

- **`vol_target.py`** (new): `compute_vol_target_weights()` scales AVGO's
  base 40% weight by `long_run_vol / trailing_21d_vol`, clipped to
  [0.3x, 1.3x] (so AVGO ranges 12%-52%), freed/added weight moving to/from
  Gold+LLY in their 25:35 ratio. Both vol series only ever use data through
  the latest available close (expanding-window long-run average, not the
  backtest's full-sample simplification) -- same "today's reading is
  tomorrow's instruction" convention as every other live signal in this
  repo, so it does not repeat the retired guard's lookahead bug.
  `apply_silver_funding()` funds T1/T2 out of AVGO's vol-targeted slice
  (same rule as the static WEIGHTS table), with a tested edge case: if
  AVGO's floor (12%) is below T2's 17% need, silver caps at what's
  available rather than going negative or reaching into Gold/LLY.
- **`fi_tracker.py`**: new "AVGO Volatility-Targeted Weight" section
  (trailing vol, long-run avg, scalar, resulting weights), printed right
  after the (retired, diagnostic-only) AVGO Trend Diagnostic block.
- **NEXT CONTRIBUTION now routes against the vol-targeted weights**, not
  the static 40% row -- this is a live behaviour change, not informational
  like the guard diagnostic. Falls back to the static `WEIGHTS` table if
  the vol-target computation fails, so routing degrades gracefully instead
  of going dark.
- Live-verified 2026-08-17: `fi_tracker.py` run for real (not just fixture
  tests -- the PR #89 lesson) and re-parsed with `check_signal_changes.py`/
  `check_sync_health.py`; zero parsing breaks, `avgo_trigger` still reads
  `none` not `unknown`. Real reading that day: trailing vol 42.2% vs
  long-run 35.3% (elevated), scalar 0.84x, AVGO target cut to 33.5%,
  Gold/LLY absorbed to 27.7%/38.8%.
- 9 new tests (`tests/test_vol_target.py`), 379 passing project-wide.

**Not done at the time this shipped:** no live rebalance executed against
these new targets, and only NEXT CONTRIBUTION (new money) consulted them --
existing capital had no instruction at all. **Closed same day, see "AVGO
Rebalance Check + Telegram alert SHIPPED" above.** Portfolio.toml/actual
share counts still untouched -- the alert recommends, it doesn't execute.

## AVGO risk management: full split-candidate sweep closed out, vol-targeting is the one real result (2026-08-17)

Follow-on to the two entries directly below (concentration pull, AMD framed
as "live candidate" -- **that framing is now superseded**, see next
paragraph). Extended the same rigor -- real 10-K concentration where
relevant, backtest on the DECIDED Gold25/AVGO40/LLY35 base, then a REAL
2000-2026 stress test (TXN proxies AVGO pre-IPO; the split partner's OWN
real history is used, no proxy, wherever it has one) -- to every remaining
split candidate, plus two mechanical (non-asset) alternatives.

**Split-candidate results, all vs LIVE Gold25/AVGO40/LLY35 (CAGR 30.15%,
MaxDD -23.41% normal / -50.2% stress):**

| Candidate | Concentration | Normal CAGR/MaxDD | Stress MaxDD | Verdict |
|---|---|---|---|---|
| NVDA | fails -- rising sharply (13%->22%+14%) | not tested further | -- | reject |
| MRVL | fails -- top 10 = 82% of revenue | not tested further | -- | reject |
| INTC | no better than AVGO (43% top-3) + weak thesis | not tested | -- | reject |
| TSM | worse aggregate (top-10 78%, rising) + geopolitical tail | not tested | -- | reject |
| IBM | passes (no customer >=10%) | CAGR 23.47%, MaxDD -22.11% | not tested | reject -- huge CAGR cost, ~zero AI thesis fit |
| ADBE | passes cleanly (10-K: literally none >=10%) | CAGR 24.98%, MaxDD -18.30% | -46.3% (better) | real trade-off, doesn't reverse, but costs ~33% of 12yr terminal wealth in the no-crash case |
| AMZN | passes (diversified retail/AWS base; doesn't buy from AVGO -- in-housed via Annapurna Labs 2015) | CAGR 27.76%, MaxDD -17.74% | **-42.0% (best of anything tested)** | best trade-off found -- smaller CAGR cost than ADBE (-18.7% vs -36.3% no-crash terminal wealth) for better stress protection. Still a trade-off, not a dominant win. |
| **AMD** | passes cleanly (no customer >=10%) | **CAGR 31.49%, MaxDD -20.98% (beats LIVE on both, normal-period)** | **-55.5% (WORSE than LIVE's -50.2%)** | **REJECT -- reverses under real stress.** AMD's near-bankruptcy history (dot-com bust, pre-2015) is invisible in the 2009-2026 backtest window; the "dominant win" is a modeling artifact of starting the clock after AMD's worst years. |
| MU | passes reasonably (17%, low) | CAGR 30.65%, MaxDD -22.80% (marginal calm-window win) | **-57.7% (worst of anything tested)** | REJECT -- same AMD trap, sharper. Commodity DRAM/NAND pricing cycle adds real crash risk the calm window hides. |

**Pattern, stated once so it doesn't need re-deriving:** every AI-semi/hyperscaler-adjacent candidate that's genuinely thesis-exposed correlates too much in the scenario that matters (or, for AMD/MU, looks fine until you actually test that scenario). Every candidate that's genuinely diversified (IBM, and to a lesser extent ADBE) costs real terminal wealth with no offsetting edge. **No single stock threaded both needles.** This is expected, not a research gap -- the market prices AI-capex beta into anything that would otherwise "contribute to performance."

**Mechanical alternatives tested instead (position-sizing, not asset selection):**

1. **Volatility-targeting on AVGO -- the one real result of this whole thread.**
   Weight scaled to AVGO's own trailing 21d realized vol vs its long-run
   average (lagged t-1->t, so it does NOT repeat the retired guard's
   lookahead bug), clipped to [0.3x, 1.3x] base weight, freed/added weight
   moves to/from Gold+LLY proportionally (5:7).
   - Normal (2009-2026): CAGR 30.15%->**30.79%**, MaxDD -23.41%->**-21.60%**, Calmar 1.288->1.426.
   - Stress (2000-2026, TXN proxy): CAGR 13.43%->**13.93%**, MaxDD -50.23%->**-44.20%**, Calmar 0.267->0.315.
   **Improves both CAGR and MaxDD, in both regimes, no reversal** -- the only
   candidate in this entire session (asset or mechanism) that clears both
   bars cleanly. Worth an actual build, not just a research note.

2. **Rebalance-band width sweep -- tested, REJECTED as noise.** Every
   backtest already runs a +-5pp drift-trigger rebalance (this IS a
   trim-on-strength mechanism, just not previously named as one). Widening
   it to 15% looked good in both normal and stress windows, but the surface
   is NOT monotonic or well-behaved past that -- 20% is worse than 15% in
   both regimes, 30-50% MaxDD blows out (-38.5% normal at 50%, worse than
   today's 5% band in places). No causal story, just an unstable fit to one
   historical path -- same overfitting signature already flagged elsewhere
   in this project for single-path results. **Left at 5%, not worth
   changing.**

**Options/collar overlay flagged but not analyzed** -- real tail-risk tool
(bounded cost, defined protection, doesn't need a correlated second asset),
but Avanza's actual AVGO-options access was never confirmed (same class of
gap that killed the IGLN gold-instrument idea on 2026-07-07). Check
tradability before spending analysis time on it.

**SHIPPED same day -- see "AVGO volatility-targeting SHIPPED" entry above.**

## AVGO customer diversification candidates: peer 10-Ks pulled, NVDA/MRVL fail, AMD is the one live candidate (2026-08-17)

**NOTE: AMD's candidacy is superseded by the entry directly above --
it reverses under a real stress test (MaxDD -55.5%, worse than LIVE's
-50.2%) and is now a REJECT, not a live candidate.** Left as-is below for
the concentration-pull detail, which still stands.

Follow-on to the concentration finding directly below. Question: does splitting
AVGO's slot with an AI-semi peer that has a genuinely different customer base
reduce idiosyncratic (single-hyperscaler-loss) risk? Pulled real 10-K
customer-concentration disclosures for the full peer set (same method as the
AVGO pull), not reasoned from correlation/beta alone.

| Ticker | Top customer(s), 3yr trend | Broader concentration |
|---|---|---|
| AVGO | 21%->28%->**32%** (one customer, rising) | top 5 ~=40%, flat |
| NVDA | 13%->12%->**22%+14%** (two customers, rising sharply) | top-2 direct 36%, plus unnamed indirect customers >=10% each on top |
| MRVL | 13%->14% direct **+ 24%->34%->37%** distributor (both rising) | **top 10 customers = 82% of revenue** |
| ANET | two customers, 16%/26% (roughly flat, 35-42% combined) | |
| QCOM | three customers, 21%/20%/13% (one declining, one flat, one rising) | ~=54% combined |
| **AMD** | **none >=10%** currently | genuinely the least concentrated |
| MU | 17% one customer, rising off a near-zero base | lowest absolute level |

**NVDA and MRVL -- the two obvious candidates -- fail outright.** NVDA's own
concentration just jumped sharply (FY24 13% -> FY26 22%+14%) and is trending
the same direction as AVGO's. MRVL is far worse: 82% of revenue sits in its
top 10 customers -- swapping into it would concentrate the portfolio *more*,
not less. Confirms the qualitative suspicion from the earlier "MRVL's largest
customer is reportedly Amazon" framing, now with real filed numbers.

**AMD is the one candidate that actually clears the test.** No customer >=10%
of revenue, confirmed. Its revenue mix (client/gaming CPU + datacenter GPU +
embedded) is also structurally different from a pure AI-capex play -- a
genuinely different economic driver, not just a different counterparty inside
the same driver, which is a stronger diversification story than "different
hyperscaler."

**What AMD does not fix:** systemic AI-cycle risk. AMD is itself one of the 8
constituents used to define the "AI-semi basket" in the 2026-08-16 hedging
research -- in a sector-wide AI drawdown it sells off with AVGO regardless of
customer mix. Only addresses the narrow idiosyncratic layer (a single
hyperscaler pulling back from AVGO specifically), not the common case (a
sector-wide selloff). Also weaker thesis fit on this framework's own terms
(AVGO's case rests on contracted multi-year backlog visibility; AMD competes
for GPU share in a more open, less contracted market) and currently more
expensive (fwd P/E ~33x vs AVGO's ~20x, per the peer valuation snapshot
above) -- diversification here has a real, unquantified cost, same shape as
the AMZN dilution finding.

**Not yet quantified -- the natural next step if pursued:** a proper
worst-1-name-shock / Calmar-by-subperiod test for an AVGO/AMD split, same
methodology as the 2026-08-16 4th-asset research. Not built this session --
qualitative case only, flagged as the open follow-up.

## AVGO customer concentration: real 10-K numbers pulled, trend is rising not falling (2026-08-17)

Question was which single number resolves the customer-concentration risk in the
scarcity/AI-ASIC thesis, and its direction. Pulled real figures from Broadcom's
FY2025 10-K (filed 2025-12-18, SEC EDGAR CIK 1730168) rather than reasoning from
the named-customer *count* (5->6, Google/Meta/Anthropic/OpenAI), which says
nothing about weighting.

| | FY2023 | FY2024 | FY2025 |
|---|---|---|---|
| Single largest customer, % of net revenue | 21% | 28% | **32%** |
| Top 5 end customers combined, % of net revenue | -- | ~40% | ~40% (flat) |
| Same single customer, % of accounts receivable | -- | 18% | **44%** |

**Trend is rising, not declining -- the risk-off answer.** Single-customer share
rose 21%->28%->32% over three fiscal years; its share of receivables jumped
18%->44% in one year alone (a sharper near-term signal than the revenue trend).
More named logos (5->6) has not translated into less concentration -- the
dollars are still consolidating in the top one even as the story diversifies
in name only.

**Two caveats on what this number actually measures:**
1. Broadcom does not name the customer in the 10-K -- disclosed only as "a
   distributor... in our semiconductor solutions segment." Very likely tied to
   the Google TPU relationship (the largest, longest-standing hyperscaler
   deal) but that is inference, not a 10-K statement.
2. This is **total company net revenue**, not the AI/XPU segment specifically.
   Semiconductor solutions also includes networking, broadband, wireless,
   storage -- so 32% likely overstates AI-specific concentration on this one
   customer while understating it as a share of AI revenue alone (AI is a
   growing slice of that segment, not all of it).

**Decision-relevant framing (agreed same session):** if this % is flat/rising
*and* the Sept 3 earnings print shows named-contract itemization "thinning"
per the pre-registered CONCERNING criteria above, that combination is the
actual trigger to revisit sizing -- neither signal alone is decisive. Not
wired into any live gate; a periodic manual pull against the next 10-K
(FY2026, expected ~Dec 2026) is the natural refresh point, same cadence as
the P/E/PEG snapshot below.

## CRITICAL: the AVGO 200d guard's entire validated edge is lookahead bias (2026-08-16)

**Nothing has been changed in the repo or in live logic. This is a finding
awaiting an operator decision.** Session was triggered by AVGO's -5.94% drop on
Friday 2026-08-14 (VMware vCenter exploit + a BofA note on ~$370B of AI vehicle
debt + profit-taking into the 09-02 print -- none of it touching the ASIC thesis).

**The bug.** Every guard backtest reads the signal from day *i*'s close and
applies it to day *i*'s return. `run_avgo_guard.py:103` (`state = in_base[date]`,
derived from `close[i]`) feeds `:112` (`AVGO_W * avgo_r.iloc[i]`, the return *of*
day i). There is no `shift(1)` anywhere in any guard script. The position is
chosen using a closing price that cannot be known until after the move happened.

**Evidence it is material, not cosmetic:**
- Mean AVGO return on the 99 guard-exit days: **-3.46%**. On the day *after*:
  **+0.01%**. Re-entry mirror: +3.15% same day, **-0.43%** next day. The signal
  has no predictive content that survives one night.
- Flip-day timing alone hands the backtest ~651 percentage points of raw AVGO
  return across the history.
- Gold25/AVGO55/LLY20, 2009-2026, 10bps: same-day fill gives CAGR 45.0% / MaxDD
  -15.0% / Calmar 2.99 -- which reproduces this file's own published 44.0% /
  -14.9% / 2.957, confirming the method was matched before being changed.
  **Next-day fill gives 19.1% / -39.1% / Calmar 0.49**, versus the unguarded base
  at 32.5% / -30.5% / 1.06. The guard makes the portfolio strictly worse.
- Four execution models tested: same-day close, next-day close, next-day open
  (real OHLC), and intraday resting stops with hysteresis. **All fail.** Best
  stop variant reaches Calmar 0.46 vs 0.86 buy-and-hold, and Calmar improves
  monotonically as turnover falls (0.31 -> 0.46 as trades drop 312 -> 66),
  converging on buy-and-hold. The optimal dose of this guard is zero.

**Scope -- same `signals[...].iloc[i]` -> `rets[...].iloc[i]` pattern:**
`run_avgo_guard.py`, `run_avgo_guard_oos.py` (so the "OOS Calmar 2.658 vs base
1.434" figure is void), `run_combined_system.py` (the headline +44.0% / 2.957),
`run_joint_stress_validation.py`, `run_base_optimizer_with_guard.py` (so the
"Gold5/AVGO80/LLY15 beats 25/55/20" conclusion is void -- and note it pointed
toward *more* concentration).

**NOT affected -- these stand:** `run_base_optimizer.py` (static weights, no
timing signal) so the 25/55/20 derivation is clean; `run_avgo_gap_down_analysis.py`
and the sleeve entry reconstructions, which measure forward returns from an event
date. Useful asymmetry to remember: **the dip-buying research is methodologically
sound, the trend-following exit research is not.**

**The live daily calculation is correct.** `fi_tracker.py` reads the latest close
and tells the operator to act, which they do next day. Nothing is miscomputing.
What is void is the evidence that acting on it helps.

**Closes the backlogged 2026-08-03 crash-ROC false-alarm item.** 30 declustered
crash-ROC fires 2009-2026: **26 rebounded** without falling a further 10%
(87% false-alarm rate). Only four were real breakdowns -- 2011-08, 2020-02
(COVID, -38.7% further), 2025-02, 2025-03. Full guard fires ~6x/year across 104
episodes, **86% lasting <=10 trading days**; median AVGO return while sitting out
is +0.0%.

**Knock-on to sizing.** The Reactor Core 83.3%-of-TPV target was derived as -25%
tolerance / -30.0% MaxDD, where -30.0% was the *guard-improved* TXN-analog figure.
Unguarded, the honest range is **48%** (TXN analog 2000-2026 incl. dot-com+GFC,
-52.3%) to **82%** (AVGO's own gentler -30.5%). Actual weight on 2026-08-16 was
72.9%. 83.3% sits above even the optimistic bound and should not be pursued
without re-deriving it.

## OPEN: PR #90 -- disconnect guard from routing + base to 25/40/35 (2026-08-16)

**Not merged.** Two commits, reviewable separately.

**Commit 1 fixes a real bug PR #89 left behind.** #89 retired the guard's
alerting but left it wired into next-contribution routing: `fi_tracker.py`
still read `WEIGHTS[(_guard_active, _silver_state)]` with a `JOINT_WEIGHTS`
override, and still gated AVGO on `not _guard_active` / LLY on
`not _lly_stress`. A close below the 200d SMA would therefore have silently
retargeted AVGO to 0%, redirected every future contribution to Gold+LLY, and
closed the AVGO gate -- **with no Telegram, because #89 had just removed it.**
Strictly worse than pre-retirement behaviour. Routing now always selects the
base row and applies no gates.

**Commit 2 moves the base to Gold 25 / AVGO 40 / LLY 35** (the 2026-08-16
decision, below). CAGR 32.6% -> 30.6%, MaxDD -30.5% -> -23.5%, Calmar 1.068
-> 1.31. Silver T1/T2 mechanism unchanged (+12%/+17% from AVGO), landing at
AVGO 28%/23%. Guard-active rows re-derived from the new base (0.45/0/0.55) so
backtests still compare like with like.

**Live effect, verified against the real dashboard:** next contribution now
routes to LLY (22.3% vs 35% target) instead of AVGO (which is 6.8pp OVER its
new target). 370 tests pass.

**Caveat to carry forward: PR #88's headline figures were computed at the OLD
25/55/20 base.** Still valid as evidence the guard fails; no longer a
description of the portfolio. Rerun `run_combined_system.py` to get
guarded-vs-unguarded numbers at the current base.

`portfolio.toml` untouched -- share counts and cash flow from the operator's
Google Sheet via `sync_sheet.py`. Once the trades execute and the sheet is
updated, the sync reconciles actual weights against these new targets.

## AVGO GUARD RETIRED -- LIVE (2026-08-16, PR #89, merged 5e217d6)

Operator decision, executed. The guard no longer produces a rotation
instruction or an alert. **AVGO now has NO mechanical downside protection of
any kind.**

**Retired as an instruction, kept as a diagnostic.** The `AVGO 200d Guard`
block in `fi_tracker.py` is renamed `AVGO Trend Diagnostic` and still prints
price vs 200d SMA, 5d ROC, LLY stress and joint stress -- honest context, no
action attached. Kept because the 5d/-10% computation is still load-bearing
for the gap-down tranche, which rests on `run_avgo_gap_down_analysis.py`
(methodologically clean -- forward returns from an event date, no execution
assumption to get wrong).

**The asymmetry is the whole finding: the 5d/-10% trigger is a usable BUY
signal and was never a usable SELL signal.**

| Event | Before | Now |
|---|---|---|
| 200d SMA breach | Telegram "Rotate AVGO -> Gold+LLY" | **silent** |
| MA breach clearing | Telegram "Hold base" | **silent** |
| Joint stress flip | Telegram "full flight to Gold" | **silent** |
| 5d ROC <= -10% | Telegram rotate | **Telegram: deploy gap-down tranche** |

**Silver GSR untouched** -- survives the lag fix, still beats base (Calmar
1.143 vs 1.068). Sleeve, earnings and regime alerts untouched.

**Two parser breaks this change introduced and nearly shipped -- the lesson
matters more than the bug.** The `status.md` section header and its
`Signal :` label are a *parsing contract* between `fi_tracker.py`,
`check_signal_changes.py` and `check_sync_health.py`:
1. Renaming the header silently degraded `avgo_guard`/`avgo_trigger`/
   `avgo_action` to `"unknown"` and would have failed the health check's
   `REQUIRED_SECTIONS` on every run.
2. Rewording the ROC line to "gap-down buy **trigger**: -10%" put a SECOND
   `trigger:` inside the block; the `avgo_trigger` regex is non-greedy from
   the header, matched that first, and parsed the trigger as `"-10%"` --
   which would have made the surviving gap-down alert unreachable.

**All 368 tests passed while both were broken**, because the fixtures still
carried the old wording. Only running the real dashboard caught it. Both now
pinned by tests (`test_avgo_trigger_regex_not_captured_by_an_earlier_trigger_word`,
`test_live_dashboard_labels_are_parseable`) and every fixture realigned with
real output. **Rule going forward: after any change to `status.md` wording,
run `fi_tracker.py` for real and re-parse it -- fixture-only tests cannot
catch format drift.**

First post-merge run verified silent (old committed `status.md` parses as
`unknown`, and the `"unknown" not in (...)` guard suppresses a spurious
alert). 370 tests pass on master.

**NEXT, and now the biggest real gap: the broker-side protective stop at
Avanza** (already logged as HIGHEST PRIORITY below). It is the only
protection that survives the operator being unreachable, and there is now
nothing else.

## Execution-lag fix SHIPPED (2026-08-16, PR #88, merged a657bf2)

The lookahead bug documented below is now fixed in every backtest.
`build_signals()` routes through a new `apply_execution_lag()`
(`EXECUTION_LAG_DAYS = 1`) shifting guard/guard_ma/guard_crash/lly_stress/
joint/silver_state by one bar; `run_avgo_guard.py`, `run_avgo_guard_oos.py`
and `run_joint_stress_validation.py` patched at their own signal-construction
points; `run_base_optimizer_with_guard.py` inherits it via `rcs.build_signals`.

**Gotcha the fix had to handle:** shifting a bool column promotes it to object
with NaN, and `bool(nan)` is **True** -- a missing signal would have become an
ACTIVE guard. Uses `.eq(True)`, not `.fillna(False).astype(bool)`. Pinned by a
test.

**Honest results, Gold25/AVGO55/LLY20, 2009-08-06 to 2026-08-14:**

| Strategy | CAGR | MaxDD | Calmar |
|---|---|---|---|
| A: Static base | **+32.6%** | **-30.5%** | **1.068** |
| B: Base + guard | +18.4% | -42.1% | 0.438 |
| C: Base + silver | +31.3% | -27.4% | **1.143** |
| D: Base + guard + silver | +18.0% | -42.1% | 0.428 |
| E: + joint-stress | +16.6% | -44.8% | 0.371 |

The guard roughly halves CAGR **and deepens MaxDD** (-30.5% -> -42.1%). All 12
cells of the MA-window x defensive-mode grid now lose to the unguarded base;
`run_avgo_guard.py` prints its own `Verdict: NO IMPROVEMENT`. Base wins 16 of
18 years.

**Nuance worth keeping -- the guard is not uniformly bad.** IS 2009-2019 it is
destroyed (Calmar 0.257 vs base 1.545); OOS 2020-2026 it genuinely helps
(1.925 vs 1.440). Classic trend-following: pays for whipsaw in grinding
markets, earns it back in crash regimes. Over the full period it loses
decisively, but "it never works" would be wrong.

**The Silver GSR tactical SURVIVES the fix** and still beats base (Calmar
1.143 vs 1.068). Only the guard fails. Do not retire silver alongside it.

**STILL LIVE AND UNCHANGED:** `fi_tracker.py`'s guard block still computes and
still alerts. That was always correct as a *calculation* (latest close ->
next-day action); what is void is the evidence that acting helps. **Retiring
or replacing the live guard is an open operator decision, deliberately not
made in PR #88.** 367 tests pass.

## DECIDED 2026-08-16: base stays 3-asset, Gold 25 / AVGO 40 / LLY 35

Operator's call at session end. **Not executed -- this is the agreed target, the
trade list is below and nothing has been placed.**

**Change from the old base:** AVGO 55 -> 40, LLY 20 -> 35, Gold 25 unchanged.
Justified by the slot research below (LLY rank 1/4991 for its slot; AVGO 55%
had the worst Calmar in all four sub-periods and the worst single-name shock
exposure).

**A 4th asset was tested extensively and rejected.** AMZN was the best candidate
on risk-adjusted metrics but:
- It is **not a hedge**. Beta to an equal-weighted AI-semi basket *during that
  basket's drawdowns* is **0.53** -- identical to QQQ (0.54) and higher than SPY
  (0.42). It falls with AVGO in exactly the scenario it was meant to protect
  against. Its lower *correlation* (0.60 vs SPY 0.82) means idiosyncratic
  variance, not lower AI sensitivity.
- It costs roughly a third of terminal wealth in the AVGO-works scenario
  (36.4M vs 53.1M on a 1M kr / 14.2yr basis).
- It would require selling ~179k kr of AVGO into the 2026-09-02 print.
- Gold (beta 0.05) and LLY (0.23) already provide the diversification; they beat
  every large-cap tech name tested by a wide margin.

**AMZN's remaining case is as a RETURN thesis** (application layer of the AI
buildout, diversified earnings base), not a risk one -- to be built from
contributions and the post-election tranche if conviction accumulates, never
funded by an AVGO sale.

**Execution sequencing (agreed, not done):** AVGO only ever moves *down* -- never
buy AVGO up toward a weight it is meant to fall below. Deploy Home Base cash into
LLY only. Do not touch AVGO before the 2026-09-02 print. Note LLY and AMZN both
report 2026-10-29, so building both to target before that date concentrates event
risk on one day.

**Still open and blocking the sizing:** which drawdown to size Reactor Core
against, -30.5% (AVGO's own history) or -52.3% (TXN analog incl. dot-com+GFC).

## Hedging research: you cannot buy the AI thesis and decorrelation in the same security (2026-08-16)

Three separate angles were tested for a 4th-asset hedge against AVGO's customer-
concentration risk. All three converged on the same conclusion, which is the
durable finding here:

**Beta / correlation to an equal-weighted AI-semi basket (NVDA/AVGO/AMD/MRVL/MU/
AMAT/LRCX/KLAC), measured only during that basket's >=10% drawdowns, 2012-2026:**

| | beta | corr | | | beta | corr |
|---|---|---|---|---|---|---|
| SPY | 0.42 | 0.82 | | WMT | 0.16 | 0.30 |
| QQQ | 0.54 | 0.88 | | KR | 0.06 | 0.09 |
| AMZN | 0.53 | 0.60 | | LLY | 0.23 | 0.33 |
| MSFT | 0.51 | 0.69 | | GC_F | 0.05 | 0.13 |
| GOOGL | 0.48 | 0.63 | | | | |

1. **Tech-adjacent (AMZN/GOOGL/MSFT):** all ~0.5 beta. No AI-capex protection.
   The GOOGL hypothesis (Broadcom's anchor customer *and* its most advanced
   in-houser, so it should capture what AVGO loses) was **tested and is wrong** --
   GOOGL correlates *more* with AVGO in drawdowns (0.57) than AMZN (0.50).
   Alphabet *is* the AI-capex trade; the in-housing offset is invisible on a
   drawdown view.
2. **Energy/power** (the data-centre-demand thesis): fails at both ends. The
   AI-power names carry AMZN-like betas (PWR 0.54, ETN 0.55, NRG 0.49, TRGP 0.53)
   because the market already re-rated them as AI plays. The genuinely low-beta
   regulated utilities (AEE/XEL/AEP/ATO, beta 0.11-0.16) barely improve portfolio
   drawdown (-19 to -20.5% vs -23.5% unhedged) while giving up 6+pp CAGR, and
   several score *worse than no hedge*. Likely because utilities are bond proxies
   -- decorrelated from AI but correlated to real yields, which the portfolio
   already carries via gold. Factor substitution, not diversification.
3. **Staples** (KR/WMT): the only genuine low-beta option with acceptable return.
   Best portfolio metrics of anything tested (KR worst-sub-period Calmar 1.70 vs
   AMZN 1.54 vs no-hedge 1.12).

**But even staples fail the compounding test, which is why nothing was added.**
1M kr, 2012-2026: no-hedge 53.1M vs WMT20 26.8M (**-50%**). In the real stress case
(TXN proxy 2000-2026, incl. dot-com + GFC) WMT only breaks even on terminal wealth
(+5%) -- what it actually buys is a worst *year* of -13.2% instead of -28.0%, and
11pp less MaxDD. **So the staples hedge is insurance that never makes you richer;
the premium is about half the upside.** Worth paying only if a -28% year would
cause capitulation.

**Generalisable lesson, seen three times in one session** (GOOGL, AMZN, AI-power):
anything that visibly benefits from the AI buildout has already been priced as an
AI asset and moves like one. Thesis purity and drawdown protection are opposites.

**Methodology note worth reusing:** measure correlation/beta *conditional on the
risk asset's own drawdowns*, never unconditionally -- unconditional correlation
hides exactly the co-movement that matters. And benchmark any candidate hedge
against SPY/QQQ: if its beta isn't below the index's, it is not a hedge.

## Portfolio construction research -- 4th asset / AVGO split (2026-08-16)

Follow-on from the above, since with no working guard the risk control is the mix
and the sizing. **Research only, nothing executed, no config changed.**

Method, deliberately anti-fitting (two overfitted answers were produced and caught
earlier the same session): stability filter applied *before* optimisation --
candidates needed >8% CAGR in *both* halves of 2009-2026 and correlation <0.45
with AVGO *during AVGO's own drawdowns* (conditional, not unconditional). 436
assets with continuous history -> 143 survivors. Slot candidates share their slot
**equally**, so weight-fitting is structurally impossible. Ranked on worst
sub-period Calmar, never full-sample. Four sub-periods, not one split.

**LLY at 35% is strongly validated: rank 1 of 4,991.** Tested against every 1-, 2-
and 3-name alternative for its slot; nothing beat it and all top-15 combinations
contained it. This also supersedes any concern from LLY's 375/539 universe-screen
rank -- that screen is a regime-conditional momentum lens with only 154 matched
days for LLY, low information for a holding never selected on momentum.

**AVGO at 40% ranks only 16 of 595 for its slot.** The pairs that beat it mostly
keep AVGO and split the slot. Candidate portfolios, 2009-2026:

| Mix | CAGR | MaxDD | Calmar A / B | worst 1-name -50% shock |
|---|---|---|---|---|
| LIVE Gold25/AVGO55/LLY20 | 32.6% | -30.5% | 1.60 / 1.27 | -27.5% |
| Gold25/AVGO40/LLY35 | 30.6% | -23.5% | 1.72 / 1.65 | -20.0% |
| Gold25/AVGO20/AMZN20/LLY35 | 28.2% | -18.0% | **1.83 / 1.83** | -17.5% |

Ordering identical in all four sub-periods -- not a split artifact. The -50%
single-name shock test is deliberately outside any backtest, since price history
cannot contain an FDA rejection, patent cliff or fraud.

**The AMZN hedge -- and a correction worth keeping.** Structural case: AWS is the
only major hyperscaler *absent* from Broadcom's named custom-silicon customer list,
because it already in-housed via Annapurna Labs (2015, Trainium/Inferentia). AVGO
and AMZN sit on opposite sides of "can hyperscalers do this themselves?".
**However, the hypothesis that GOOGL would be the purer hedge was tested and is
wrong** -- GOOGL correlates *more* with AVGO in AVGO's drawdowns (0.57) than AMZN
does (0.50); MSFT 0.57, META 0.47. Alphabet *is* the AI-capex trade, so its
in-housing offset is invisible on a drawdown view. Amazon's retail half -- which
looks like hedge dilution -- is exactly what decorrelates it. **Thesis purity and
drawdown protection are opposites here.** Durable finding: splitting AVGO helps
regardless of partner (every candidate beats no-hedge on worst-period Calmar,
1.24-1.54 vs 1.12).

**Stress case (TXN substituted for AVGO, 2000-2026):** LIVE 12.5% / -52.3%,
AVGO40 13.6% / -42.6%, SPLIT 17.3% / -42.0%. AMZN barely helps here -- it fell
~95% in the dot-com bust. It hedges AI-capex/in-housing concentration, **not** a
broad tech collapse. Under this belief 10% Home Base is not viable for any mix
(~60% Reactor Core would be required).

**Operator decisions still open at session end:**
1. **Which drawdown to size against** -- -30.5% (AVGO's own) or -52.3% (TXN
   analog originally adopted precisely because AVGO never saw a dot-com bust).
   This single input decides the Home Base question and nothing else can settle it.
2. **Home Base floor.** Operator wants cash held for behavioural reasons
   ("mental health"), was exploring 10-15%. At 10% the live mix breaches the -25%
   tolerance even optimistically.
3. **Whether to retire the guard or attempt re-validation.** No PR opened.
4. **Rotation timing.** Operator correctly rejected an incoherent staging plan
   (building AVGO to 40% when the destination is 20% = paying spread twice).
   Corrected sequencing: **AVGO only ever moves down**; deploy cash into LLY/AMZN
   only, cut AVGO after the 09-02 print. Unmodelled at session end: return profile
   of rotating now vs post-09-02 vs post-11-03, priced against AVGO's earnings gap
   risk (worst historical overnight gaps -14.9% / -14.7% / -12.8%; at ~378k that
   is ~-51k kr) -- and **the existing post-midterm AVGO tranche plan is
   incompatible with cutting AVGO to 20%; one of the two has to go.**

**Unchanged and still valid:** the 2026-09-02 pre-registered earnings criteria
(fundamental, unaffected by any of the above), the AVGO thesis itself ($73B
committed backlog, named customers 5->6 with OpenAI added, $56B FY26 / >$100B FY27),
and valuation (post-drop forward P/E 20.1x, 2nd cheapest of 9 AI/semi peers on
PEG(1y)).

## Peer valuation snapshot script built -- fills the unrecoverable P/E/PEG gap from 2026-07-06 (2026-08-14)

The 2026-07-06 AI/semi peer valuation session (see the two sections below on
`eps_ratio.py`'s history) recorded peer fwd/trail EPS ratios but never the
peer forward P/E or PEG numbers behind its own conclusions ("only NVDA/QCOM
have a lower forward P/E, only MU has a lower PEG") -- those numbers were
never written down and are gone, six weeks stale even if they had been.
`run_peer_valuation.py` replaces the prose with a reproducible, on-demand
snapshot: same 9-ticker AI/semi set (MU, AMD, AVGO, NVDA, MRVL, TSM, ASML,
ANET, QCOM), same normalized non-GAAP EPS sourcing `fi_tracker.py` already
uses (`earnings_history`/`eps_trend`, reuses `normalized_eps_ratio` from
`eps_ratio.py` -- never `info["trailingEps"]`/`forwardEps`, which mix GAAP
conventions and caused the original 3.22x bug), now with price, forward P/E,
and a PEG added.

**PEG basis caveat, worth remembering:** this script's PEG is built on the
same 1-year forward growth estimate as the ratio above it, not the
conventional 5-year estimate real PEG ratios (and yfinance's own `pegRatio`
field, deliberately not fetched here) use. That's exactly why the 0.41 PEG
recorded on 2026-07-06 never reconciled with its own 19.4x forward P/E
(19.4 / 139% = 0.14, not 0.41) -- the two numbers were never on the same
basis. Labeled `PEG(1y)` everywhere in the output specifically so it can't
be silently compared against a 5-year PEG from elsewhere again.

**2026-08-14 snapshot, for reference (will drift -- rerun for anything
current):**

| Ticker | Price | Fwd/Trail | Impl. growth | Fwd P/E | PEG(1y) |
|---|---|---|---|---|---|
| MU | $949.83 | 3.43x | +243% | 6.13x | 0.03 |
| AMD | $483.01 | 2.68x | +168% | 31.24x | 0.19 |
| **AVGO** | **$417.82** | **2.40x** | **+140%** | **21.39x** | **0.15** |
| NVDA | $225.30 | 2.21x | +121% | 17.48x | 0.14 |
| MRVL | $222.18 | 2.06x | +106% | 35.59x | 0.34 |
| ASML | $1,847.90 | 1.87x | +87% | 35.93x | 0.41 |
| TSM | $430.49 | 1.57x | +57% | 19.78x | 0.35 |
| ANET | $203.62 | 1.49x | +49% | 39.46x | 0.80 |
| QCOM | $164.79 | 0.90x | -10% | 16.05x | n/a (negative growth) |

AVGO rank: **3 of 9** on growth ratio, **5 of 9** on forward P/E, **3 of 9**
on PEG(1y) -- confirms the "mid-pack, not an outlier" framing from
2026-07-06 still holds, now with the price dimension actually attached
instead of asserted from memory.

**Also fixed, same commit:** two stale strings still citing the retired
"quality peer set" (AAPL/TDG/ANET, 1.17-1.41x) that 2026-07-06 itself had
already concluded was a peer-selection artifact (those companies share none
of AVGO's AI-capex growth profile) -- `eps_ratio.py`'s module docstring and
`fi_tracker.py`'s AVGO checkpoint line (the one that lands in `status.md`
daily). Both now cite the real AI/semi peer set and AVGO's mid-pack
standing. LLY's checkpoint line carried the same stale range too ("in line
with peer range 1.17-1.41x") -- dropped rather than fixed, since an
LLY-appropriate peer set (pharma, not AI/semi) is out of scope here and
citing the wrong set is worse than citing none.

Standalone research script, no `status.md`/`sync.yml` wiring, no alert --
per the existing 2026-07-06 decision to keep P/E and PEG a periodic manual
exercise, not a daily gate (they barely move day-to-day except through
price, which the AVGO guard already tracks). Derive/format layer is pure
and unit-tested without network (`tests/test_peer_valuation.py`, 9 tests --
derivation math, negative-growth PEG suppression, zero/negative-TTM and
partial-quarter n/a handling, ranking with ties). Live-verified against
real yfinance data (both the standalone script and `fi_tracker.py` end-to-
end) before committing, not just the synthetic tests.

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

## AVGO gap-down x 200d Guard state -- counterintuitive result: guard-active gaps bounce HARDER, not softer (2026-07-28)

Direct follow-on: does the 200d Guard's state (reconstructed point-in-time,
same logic as fi_tracker.py's live guard -- below 200d SMA OR 5d crash ROC
<=-10%) sharpen the gap-down signal? Hypothesis going in was the opposite
of what the data shows: expected guard-active gap-downs to be the "real
breakdown" case and underperform guard-base gap-downs (the "healthy dip"
case).

**Result is the reverse, consistently, across every threshold and
horizon** (guard active on 15.7% of all 4,268 sessions -- a real, non-thin
base rate):

| Gap threshold | Horizon | Guard ACTIVE | Guard base |
|---|---|---|---|
| >=2% | 21d | +8.1% (82% win, n=62) | +1.9% (57% win, n=101) |
| >=2% | 63d | +21.3% (90% win, n=60) | +14.2% (75% win, n=97) |
| >=3% | 21d | +15.1% (92% win, n=26) | +1.8% (56% win, n=34) |
| >=5% | 21d | +20.8% (100% win, n=11) | -5.4% (33% win, n=9) |

Gap-downs occurring WHILE the guard is already active (AVGO already below
its 200d SMA or already in crash-ROC territory) resolved forward *better*
than gap-downs during an otherwise-healthy uptrend, at every threshold and
horizon tested -- opposite of the "guard-active = real breakdown, don't
buy" hypothesis.

**Read carefully -- this does not mean the guard is wrong or should be
ignored.** Most likely explanation: a gap-down that happens after AVGO is
already beaten down reads more like capitulation/panic selling near a
local trough (violent short-term mean reversion), while a gap-down inside
an otherwise-healthy uptrend is a smaller, more ambiguous stumble with a
less extreme bounce. The guard's own job is portfolio-level risk
management across the FULL cycle (validated on Sharpe/MaxDD/Calmar in
run_avgo_guard.py / run_combined_system.py) -- it is not answering "will
this specific dip bounce," it's answering "should the portfolio stay
fully exposed through an extended real drawdown." A high win rate on
individual dip-buys during an active guard period doesn't offset the tail
risk the guard exists to cut -- these two questions are compatible, not
contradictory, and this finding should NOT be read as "turn the guard
off" or "buy every dip regardless of guard state."

Informational only -- not wired into any live gate, no proposal to
implement. Temporary diagnostic workflow removed after this run.

## Gap-down forward returns: Gold (GC_F) and LLY, same lens as AVGO (2026-07-28)

Ran the now-generalized run_avgo_gap_down_analysis.py against Gold and LLY
directly, since the user liked the AVGO "shopping at a discount" framing
and wanted to know if it holds for the other two base holdings. No era
split requested for either (no known single-date narrative shift like
AVGO's 2023 AI re-rating).

**Gold (GC_F), full history 2000-08-30 to 2026-07-27 (6,499 sessions):**

| Gap | Horizon | n | Median return | Win rate | Baseline (same horizon) |
|---|---|---|---|---|---|
| >=2% | 21d | 43 | +1.16% | 63% | +0.79% |
| >=2% | 63d | 42 | +3.01% | 60% | +2.74% |
| >=2% | 252d | 37 | +13.99% | 84% | +11.42% |
| >=3% | 21d | 15 | +0.06% | 53% | +0.79% |
| >=3% | 252d | 13 | +16.63% | 92% | +11.42% |
| >=5% | all | 2 | n too thin, blanked | -- | -- |

Gold's gap-down "discount" is much weaker and noisier than AVGO's. The 2%
bucket shows a small, believable edge at every horizon. The 3% bucket is
basically flat to baseline at 21d/63d (no discernible short/medium-term
edge) and only pulls ahead at 252d, on a thin n=13 -- read that 252d row
as a low-confidence echo of Gold's long-run uptrend, not a real gap-down
premium. 5%+ gap-downs are too rare in Gold to say anything (n=2).
**Bottom line: Gold doesn't reward buying its dips the way AVGO does --
mostly just look like noise around Gold's baseline drift.**

**LLY, full history 2000-01-03 to 2026-07-27 (6,680 sessions):**

| Gap | Horizon | n | Median return | Win rate | Baseline (same horizon) |
|---|---|---|---|---|---|
| >=2% | 5d | 126 | +0.60% | 53% | +0.27% |
| >=2% | 21d | 126 | +1.74% | 60% | +1.08% |
| >=2% | 63d | 126 | +4.94% | 64% | +3.21% |
| >=3% | 5d | 53 | -0.30% | 45% | +0.27% |
| >=3% | 21d | 53 | +2.27% | 62% | +1.08% |
| >=3% | 63d | 53 | +5.56% | 70% | +3.21% |
| >=5% | 5d | 21 | -0.11% | 43% | +0.27% |
| >=5% | 21d | 21 | +2.27% | 62% | +1.08% |
| >=5% | 63d | 21 | +6.55% | 71% | +3.21% |
| >=5% | 252d | 20 | +13.99% | 70% | +12.72% |

LLY shows a distinct **delayed-bounce** pattern, different from both AVGO
(clean monotonic edge at every horizon) and Gold (weak/noisy everywhere).
At the 3%+ and 5%+ gap thresholds, the immediate 5-day forward return is
FLAT TO NEGATIVE and below baseline (win rate drops to 43-45%) -- deeper
LLY gap-downs tend to keep drifting for the first week, i.e. don't
necessarily bounce right away, sometimes still falling further. But by
21d the picture flips to a real, consistent edge over baseline, and by
63d the edge is clear and win rates climb into the high 60s/70s.

**Bottom line across all three base holdings:** AVGO is the one with a
genuinely clean "buy the dip" signal at every horizon. LLY has a real edge
too, but only if you can tolerate the position drifting against you for
the first week or two before it resolves favorably -- treat any LLY
gap-down as a slower-developing opportunity, not an immediate bounce.
Gold's gap-downs carry little to no discernible information beyond its
ordinary baseline drift -- don't read a Gold gap-down as a buying signal.

Informational only -- not wired into any live gate. Temporary diagnostic
workflow (gap_down_analysis_diagnostic.yml) removed after this run.

## Opp sleeve extension-decile analysis: no real dose-response beyond the binary gate (2026-07-29)

Follow-on to the "what's the right question about extension" discussion:
does forward return actually degrade with MA50 extension within the real
gated-entry population, or is extension just a pass/fail gate with no
further information once cleared? Reused the exact same walk-forward,
no-lookahead reconstruction as run_sleeve_entry_reconstruction.py (PR #45)
-- same population (509 candidates, 152 regime transitions, 34,151 raw
gate-clearing events, 4,322 declustered entries) -- with the discarded
`ext` value kept instead of thrown away, bucketed into 10 deciles, at the
live 21d duration (n=4,310 with valid forward returns):

| Decile | ext range | ext median | n | med_return | win_rate |
|---|---|---|---|---|---|
| 1 (least) | 0.0%-0.65% | 0.31% | 431 | +1.29% | 55.5% |
| 2 | 0.65%-1.31% | 0.97% | 431 | +0.99% | 55.7% |
| 3 | 1.31%-2.05% | 1.69% | 431 | +1.96% | 62.9% |
| 4 | 2.05%-2.85% | 2.41% | 431 | +0.83% | 54.5% |
| 5 | 2.85%-3.69% | 3.27% | 431 | +1.39% | 58.7% |
| 6 | 3.69%-4.48% | 4.08% | 431 | +1.50% | 58.0% |
| 7 | 4.48%-5.37% | 4.93% | 431 | +1.32% | 58.9% |
| 8 | 5.37%-6.43% | 5.88% | 431 | +1.92% | 62.9% |
| 9 | 6.43%-8.21% | 7.16% | 431 | +0.59% | 52.0% |
| 10 (most) | 8.21%-24.8% | 9.59% | 431 | +1.35% | 56.8% |

Correlation (decile ext_median vs. decile med_return): **-0.056** --
essentially zero. No monotonic pattern: decile 3 (modest extension) has
the best win rate tied with decile 8 (much more extended); decile 9
(fairly extended) has the worst median return of the whole population;
decile 1 (least extended -- the selection rule's preferred bucket) sits
in the *middle* of the pack, not at the top.

**Conclusion: once a candidate already clears the existing binary
"extension <= regime p67" gate, its exact extension level inside that
gate carries no further predictive information about 21d forward
return.** This is consistent with (and extends) the earlier entry-filter
sensitivity finding this session (tightening the extension/RS thresholds
found no material improvement) -- both point the same direction: the
selection rule's "prefer least-extended ROBUST candidate" tiebreaker is
not wrong, but it is not backed by an actual dose-response curve either.
It's a defensible, harmless tiebreaker among otherwise-equal candidates,
not a real edge. No change proposed to run_entry_screen.py's selection
logic from this finding alone.

Informational only -- not wired into any live gate. Temporary diagnostic
(run_opp_sleeve_extension_decile_analysis.py + its workflow) removed
after this run.

## Opp sleeve execution-drift analysis: chasing raises stop-out risk, not return (2026-07-29)

Follow-on to the extension-decile null result: does the price move
BETWEEN when a candidate qualifies (screen close) and when you can
realistically execute (next session's open) predict trade outcome?
Directly motivated by a live case this session -- STLD qualified off one
day's close, then gapped further (a post-earnings move) before it could
be acted on.

Same reconstruction population as PR #45 / the extension-decile study,
but measuring forward return from the NEXT session's OPEN instead of the
signal close, bucketed by the gap between the two (same convention as
run_avgo_gap_down_analysis.py, applied to entry timing). Also computes,
per bucket, the fraction of entries that would have hit the live
binding_stop() (buffered MA50 / armed trailing stop) within the first 10
trading days -- a "quick failure" rate, not just point-return.

**Bug found and fixed along the way:** the backtest's earnings-clear
gate (gate 4, used by find_gated_entries) was a silent no-op due to TWO
stacked bugs in run_sleeve_entry_reconstruction.py's _earnings_dates():
(1) missing `lxml` dependency (get_earnings_dates() needs it for
pandas.read_html; added to pyproject.toml), and (2) once that was fixed,
an AttributeError -- `d.tz_localize(None)` was called on plain
datetime.datetime objects from `.to_pydatetime()`, which only pandas
Timestamps support (fixed with `.replace(tzinfo=None)`). Both were
silently caught by the same broad except, so bug #2 was completely
masked by bug #1 until #1 was fixed -- gate 4 had likely been a no-op
since PR #45 was written. Added a regression test exercising
_earnings_dates() directly (previously only ever monkeypatched away).
With both fixed, raw gate-clearing events dropped from 34,151 to 25,795
(~25% fewer, consistent with excluding ~21 of every ~91 calendar days
per quarterly cycle) and the declustered population from 4,322 to 3,644.

**Result, properly gated, 21d duration (n=3,641 with valid drift+return),
8 buckets by (next session's open / signal close - 1)**:

| Bucket | drift_median | n | med_return | win_rate | early_stop_rate (10d) |
|---|---|---|---|---|---|
| 1 (gapped down hardest) | -1.45% | 456 | +1.17% | 55.3% | **51.5%** |
| 2 | -0.64% | 455 | +1.33% | 55.4% | 25.9% |
| 3 | -0.29% | 455 | +1.46% | 58.0% | 20.9% |
| 4 (near-zero, sweet spot) | -0.03% | 455 | +0.68% | 56.9% | **14.1%** |
| 5 | +0.13% | 455 | +1.20% | 59.1% | 16.5% |
| 6 | +0.35% | 455 | +1.33% | 57.8% | 20.9% |
| 7 | +0.64% | 455 | +0.81% | 55.2% | 22.4% |
| 8 (chased hardest) | +1.33% | 455 | +1.13% | 54.1% | **35.6%** |

Correlation (drift vs. med_return): -0.25. Correlation (drift vs.
early_stop_rate): -0.39 (linear correlation understates the true shape --
it's U-shaped, not linear).

**Conclusion: point-estimate return is fairly flat/noisy across buckets
(no clean edge from being early or late), but early-stop-out risk is
clearly U-shaped and the pattern is essentially unchanged from the
pre-fix (earnings-contaminated) run** -- both a same-day gap-down before
execution AND chasing a move upward roughly double-to-triple the odds of
a quick stop-out (14-17% at the sweet spot vs. 35-52% at the extremes),
without a comparable gain in expected return to compensate. This
validates the practical read: entering close to when a candidate is
first flagged (neither delayed into a further chase nor arriving after
it's already reversed) minimizes false-start risk without giving up
return. Informational only -- no display flag or gate change implemented
from this finding (explicitly deferred this session). Temporary
diagnostic (run_opp_sleeve_execution_drift_analysis.py + its workflow)
removed after this run.

**Update, same session:** superseded by the very next commit (`0045d42`,
"Add execution-drift filter to opp sleeve candidate selection") -- the
deferral above stood for less than one commit. `EXECUTION_DRIFT_THRESHOLD
= 0.009` now filters (not just flags) candidates in `run_entry_screen.py`:
fetches a live price at selection time, compares to signal close, walks
to the next-ranked candidate if drift exceeds 0.9% (fails open on missing
live-price data). Leaving the "deferred" language above as-is since it's
the accurate record of what was decided at that point in the analysis --
this note exists so the next reader doesn't mistake the deferral for the
final state.

## Opp sleeve edge-type review + PEAD reconstruction: real signal, but binary not magnitude-scaled (2026-07-29)

Follow-on to a broader "what other trade types could this sleeve run"
review (2026-07-29): of five candidates considered (post-earnings-drift,
sector-wide capitulation, index-reconstitution drift, calendar
seasonality, buyback-announcement drift), only the first two are
buildable with zero new data infrastructure -- the other three need a new
ingestion pipeline before validation can even start. `run_sleeve_pead_
reconstruction.py` and `run_sleeve_sector_capitulation_reconstruction.py`
(both permanent, tested scripts, not temporary diagnostics) test the two
buildable candidates.

**PEAD (post-earnings drift), first result:** real EPS surprise history
(yfinance `get_earnings_dates()`) for every ticker that was in the live
gate-1 top-N list at print time (509 candidates, 163 regime transitions,
285 unique tickers with earnings history, 2,340 declustered entries),
bucketed by surprise magnitude, deliberately independent of the existing
MA50/extension gates (PEAD is momentum-continuation, the existing gates
are mean-reversion -- stacking them would muddy which mechanism is doing
the work). Early-stop-rate uses the CURRENT live `binding_stop()`, same
convention as the execution-drift study above.

| Bucket | n | 21d med. return | 21d win rate | 21d early-stop rate |
|---|---|---|---|---|
| miss_or_flat | 493 | -0.16% | 49.4% | **62.8%** |
| beat_0_2 | 232 | +0.17% | 52.2% | 45.3% |
| beat_2_5 | 350 | +1.13% | 58.0% | 46.6% |
| beat_5_10 | 405 | +0.38% | 52.9% | 45.6% |
| beat_10_plus | 860 | +0.85% | 56.0% | 49.2% |

**Same shape as both studies above it in this file: real signal in
early-stop-rate, no clean dose-response in return magnitude.** Every
"beat" bucket clears at a materially lower early-stop-rate (45-49%) than
a miss (62.8%) -- a large, consistent gap. But among the beat buckets,
bigger surprise does NOT mean a better outcome the way the textbook PEAD
story implies: `beat_2_5` (2-5% beat) is as good or better than
`beat_10_plus` at every duration tested, not worse. Median-return
differences across beat buckets are otherwise fairly flat/noisy, same
pattern as the extension-decile and execution-drift findings above.

**Conclusion: if this is ever built, it should be framed as a binary
miss-vs-beat signal (deprioritize/avoid entries right after a miss), not
a magnitude-scaled "chase the biggest beats" signal** -- the data doesn't
support the latter. Report-only: no gate, display flag, or live screen
change implied by this result. Sector-capitulation reconstruction
(solo_crash vs. basket_crash) is the next candidate in this same review,
not yet run as of this entry.

**Side note on running these scripts:** `rank_at_transitions()` (the
walk-forward gate-1 ranking, shared by this study, the sector-
capitulation study, and the original extension reconstruction) is the
actual long pole in a fresh run -- roughly 15-20 minutes on this dataset,
NOT the earnings-fetch loop it was originally suspected to be, and cost
per transition grows substantially in later, denser regime periods (more
candidates have accumulated enough history). It now has an opt-in
`verbose=True` flag for per-transition progress output. Also: the
`sys.stdout = io.TextIOWrapper(...)` rewrap present in every script in
this backlog needs `write_through=True` AND per-call `flush=True` on
anything meant to be visible during a long run -- `write_through` alone
only bypasses the text-encoding buffer, not the underlying binary
buffer's own batching, so a real multi-minute run and a hang were
indistinguishable from the outside until both fixes landed.

## Sector-capitulation reconstruction: basket-crash beats solo-crash, cleanly (2026-07-29)

Second (and last, given only these two of five reviewed candidates need
zero new data infra) study from the same edge-type review. Trigger:
ticker in a 5d/-10% crash (same validated convention as the AVGO/LLY
guard, not a new threshold) AND in that period's frozen gate-1 top-N
list. Split into `solo_crash` (no other same-sector gate-1 peer also
crashing that day) vs. `basket_crash` (>=2 same-sector peers also
crashing) -- 1,252 declustered entries (953 solo, 299 basket) from 151
periods, 4,305 raw crash events.

| Bucket | n | 21d return | 21d win rate | 90d return | 90d win rate |
|---|---|---|---|---|---|
| solo_crash | 953 | +1.13% | 54.7% | +5.51% | 59.8% |
| basket_crash | 299 | **+4.41%** | **66.6%** | **+10.22%** | **72.2%** |

**Real, clean, monotonic signal -- unlike PEAD above.** basket_crash beats
solo_crash at every duration tested, not just one: ~4x the raw return and
+12pp win rate at 21d, still ~2x the return and +12pp win rate at 90d.
This is the strongest single result across all three studies logged in
this backlog today (extension-decile, PEAD, this one) -- the other two
found real signal only in early-stop-rate with flat/noisy returns; this
one shows a real return/win-rate edge directly.

**Important caveat: the early-stop-rate column (94.1% solo, 98.0%
basket) is NOT a meaningful comparison here and should not be read as
"both buckets get stopped out almost immediately, so it doesn't matter."**
These entries are, by construction, already deep in a 5d/-10% crash --
price is already well below its own MA50 at entry. The live
`binding_stop()` (buffered MA50 floor) was calibrated for the EXISTING
extension gate, whose entries start ABOVE MA50; applied to an entry that
starts BELOW MA50, it is close to guaranteed to trip within days
regardless of what happens afterward. The near-saturated 94-98% in both
buckets is a sign the metric doesn't fit this entry type, not a real
finding about either bucket. The raw-return numbers above (no stop
applied) are the trustworthy read for this study; a crash-appropriate
stop definition would need to be designed before early-stop-rate means
anything here -- not attempted in this pass.

Report-only: no gate, display flag, or live screen change implied by this
result.

## Capitulation stop-sensitivity: fixed floors destroy the edge, trailing-only improves it (2026-07-29)

Direct follow-on answering the caveat above: does ANY stop protect
capital on the real solo_crash/basket_crash population (953 / 299
entries) without destroying the edge, or does it repeat the sleeve's own
`HARD_STOP_PCT` history (every threshold tested there got stopped out on
>50% of trades with negative median return)? Two-phase test at 21d, same
methodology as `run_opp_sleeve_stop_sensitivity.py`: Phase 1 grids an
entry-price floor (0.05-0.20, plus `None`/no-floor competing on equal
footing) with no trailing; Phase 2 adds the live trailing-peak grid
(trigger/pct in {0.05,0.08}x{0.03,0.05,0.08}) on top of Phase 1's winner.

**Phase 1 -- the risk was real.** A tight floor doesn't just reduce the
edge, it INVERTS it: solo_crash with a 5% floor swings to median
**-5.05%**, win rate 42.5% (vs. the raw reconstruction's +1.13% at this
duration). Every floor tested underperforms no floor at all; Phase 1's
winner for BOTH buckets was `None` (no floor), converging back to the raw
reconstruction numbers (solo +1.16%, basket +4.31%) -- this is the same
failure mode already documented for the live gate's `HARD_STOP_PCT`,
confirmed here on a different, more extreme (below-MA50) entry
population.

**Phase 2 -- a trailing-ONLY stop (no floor) is the one config that
helps rather than hurts.** Arms only once the trade is already in
profit, so it never clips a live losing/recovering trade the way a floor
does. Calmar-like (median return / |median drawdown among losers|, the
tail-risk-aware metric) roughly doubles for solo_crash (0.177 -> 0.321 at
trigger=0.05/trailing=0.03) and edges past the no-stop baseline for
basket_crash (0.443 -> 0.481 at trigger=0.08/trailing=0.08, also the best
win rate found for that bucket at 66-71% across the trailing grid).

**Conclusion: this trade type survives contact with a real exit rule --
but only the right kind.** A fixed floor (the mechanic the live
`binding_stop()` uses via its MA50 component) actively destroys the edge
here and should NOT be reused as-is for a capitulation-style entry. A
trailing-only stop (no floor, arms only in profit) doesn't just avoid
destroying the edge -- it modestly improves it on both buckets. If a
capitulation gate is ever built, this is the specific constraint: no
entry-price or MA50 floor, trailing stop only. `false_stop_pct_of_stopped`
stays meaningfully non-zero (40-65%) even for the winning configs -- this
is a real, imperfect stop, not a free lunch, but a net tail-risk
improvement over both the floor-based alternative and no stop at all.

Report-only: no gate, display flag, or live screen change implied by this
result. Remaining open items before this could go live: the concentration
cap flagged in conversation (no limit yet on how many same-sector basket
entries could fire simultaneously) and the live-side plumbing to compute
"how many gate-1 peers are crashing today" (currently only exists in the
reconstruction's historical walk, not in `run_entry_screen.py`).

## Basket-crash: live, gated behind extension-gate priority (2026-07-30)

Both remaining gaps from the entry above are now closed and wired into
`run_entry_screen.py` -- basket_crash is a real, live SECONDARY entry
pathway, not just a reconstruction study. Two design decisions were made
explicitly in conversation before any code was written, not assumed:

**1. Priority vs. the primary extension-gate pathway: extension-gate wins.**
basket_crash only fills the sleeve's single slot (position cap is still
1 -- unchanged) when extension-gate's `select_best_candidate` finds no
eligible ENTER candidate that day. Reasoning: extension-gate is
live-validated (real trade, tuned twice on a 4,321-entry population, run
through the pre-entry tripwire + execution-drift gates); basket_crash is a
299-entry backtest that has never been live-fired. Giving a thinner-N,
unproven signal priority over the proven one during exactly the highest-
stress moments (a sector-wide crash) was judged the wrong default until
basket_crash earns its own track record.

**2. Concentration cap bounds SELECTION, not capital.** Since the sleeve
only ever holds one position total, there's no multi-position capital risk
to cap yet. `cap_basket_crash_concentration()` instead caps the CANDIDATE
list to 1-per-sector before ranking (deepest crash wins, peer_count
tie-breaks), so a day where multiple sectors crash together doesn't
silently bias the pick toward whichever sector has the most crashing
gate-1 names. A real capital-exposure cap is explicitly deferred, not
built speculatively for a multi-position design that doesn't exist.

**Shipped in `run_entry_screen.py`:**
- `basket_crash_candidates()` -- live version of the reconstruction's
  historical trigger (5d/-10% crash + >=2 same-sector gate-1 peers also
  crashing), computed on today's data.
- `cap_basket_crash_concentration()` -- the 1-per-sector selection cap above.
- `select_best_basket_crash()` -- picks the deepest crash among capped
  candidates, excluding already-held tickers. Deliberately does NOT reuse
  `select_best_candidate`'s pre-entry tripwire gate (RS>=0 + rising MA50)
  -- those requirements are the OPPOSITE of what qualifies a basket-crash
  candidate.
- `basket_crash_binding_stop()` -- trailing-only, NO MA50-floor branch, at
  this entry type's own validated params (trigger=8%, trailing=8% --
  deliberately different from the extension-gate's 5%/3%, tuned on a
  different population). `compute_exit_triggers()` now takes an
  `entry_type` param and branches: basket_crash gets this stop plus a flat
  21-calendar-day time exit with NO earnings-buffer adjustment (matches
  exactly what `run_opp_sleeve_capitulation_stop_sensitivity.py`
  validated -- `DURATION_DAYS=21`, earnings interaction never tested for
  this entry type).
- `sleeve_state.toml` gained an `entry_type` field (default `"extension"`,
  backward compatible with the existing closed state file).
  `--open TICKER PRICE SHARES CAPITAL --entry-type basket_crash` records
  which pathway a position came from; `print_sleeve_status` and
  `sleeve_daily_summary` both display the pathway and use the matching
  stop/exit rule.
- Both `run_entry_screen()` (full table) and `sleeve_daily_summary()` (the
  compact digest `fi_tracker.py` runs daily) print the basket-crash
  candidates whenever the primary pathway has no pick -- visible every
  day, not just discoverable on demand.

**Deliberately NOT applied to basket_crash candidates** (flagged in the
screen output itself, not just here): the earnings-avoidance gate and the
execution-drift filter. Neither was validated for this entry type by the
reconstruction studies -- silently reusing an extension-gate-tuned
threshold on a structurally different population (below-MA50, mid-crash)
would be exactly the kind of untested assumption this build was trying to
avoid. Left as an explicit, visible gap rather than guessed at.

18 new tests in `tests/test_entry_screen.py` (trailing-stop arming, the
concentration cap's sector-cap + tie-break logic, selection excluding
held tickers, and the live detection function against synthetic same-
sector crash/no-crash parquet data). Full suite: 329 passing.

**Still open:** basket_crash has no live track record yet -- the extension-
gate-first priority rule should be revisited once it does. No urgency;
this is a secondary pathway that only ever activates on days the primary
one is empty.

## Sleeve alert clarity: self-contained Plan/Open lines, basket-crash now wired into Telegram (2026-07-30)

Two follow-on gaps found and closed while reviewing the basket_crash build
above -- both surfaced by walking through what the user actually receives
on their phone, not just what prints to a terminal they may not be at.

**Gap 1: basket_crash candidates never reached Telegram at all.**
`check_signal_changes.py` diffs `status.md` by regex to decide whether to
push a notification. Its only sleeve-candidate watch was
`Best candidate\s*:\s*(\S+)` -- the extension-gate field. The new
`Basket-crash` line added above was invisible to it: a real, live
basket_crash candidate would sit silently in `status.md`, visible only on
a manual check, with no push ever firing. Fixed: added a
`sleeve_basket_candidate` field (same regex pattern, new label) and a
matching alert block in `build_actionable_message()`, guarded the same
way as the existing candidate-appearance check (both sides CLOSED, prev
none/unknown -> curr a real ticker).

**Gap 2: even the alerts that DID fire told the user to go run the
screen instead of saying what to do.** The existing message was
`"...is now ENTER-eligible... REVIEW: run run_entry_screen.py for the
full candidate detail before acting"` -- useless if the user can't get to
a terminal before the signal moves. Fixed by making `sleeve_daily_summary()`
itself (the function that generates `status.md`, which both the screen
output AND the Telegram alert are sourced from) print two new lines
whenever a candidate exists:

```
Plan : buy near $<price>, hold ~<N>d, stop = MA50-5% then trails 3% once +5% gain
Open : run_entry_screen.py --open <TICKER> <fill_price> <shares> <capital_sek>
```

(basket_crash gets its own Plan line reflecting its different mechanics --
flat 21d exit, no floor until +8% gain then trails 8%.) `check_signal_
changes.py` then quotes these two lines VERBATIM into the Telegram body
rather than re-deriving the plan text itself -- single source of truth,
matching the pattern the AVGO-guard/silver alerts already use (pulling
the live Action-line text instead of restating it), so the phone message
can never drift from what the dashboard actually computed.

**Design constraint carried forward:** the alert must be actionable on
its own -- ticker, price, entry logic, exact stop/exit mechanic, and the
literal command to run, with no dependency on being at a keyboard when it
arrives. Apply this same bar to any future sleeve alert type.

Shipped: `basket_crash_candidates()` rows now carry `price` (last close).
`sleeve_daily_summary()`'s CLOSED branch prints `Plan`/`Open` for both
pathways. `check_signal_changes.py` gained the `sleeve_basket_candidate`
watch plus `sleeve_plan`/`sleeve_open_cmd` capture, and a new
"BASKET-CRASH CANDIDATE" alert block. 12 new/updated tests in
`tests/test_signal_changes.py`. Full suite: 334 passing. Verified live
against real data (both the extension "none eligible" and basket-crash
"none eligible" fallback paths render correctly with no exceptions --
no live candidate existed at verification time to see the populated
Plan/Open lines fire for real, so that path is covered by tests only,
not a live confirmation).

**Live send during verification surfaced a real candidate and a real
gap (2026-07-30):** the extension-pathway preview found a genuine live
ENTER candidate -- STLD (Steel Dynamics), $252.34, ext +2.0%, 21d med
+2.7%, div ROBUST -- and delivered the real Telegram message
successfully (`Sleeve candidate -> STLD`, with real Plan/Open lines).
Confirmed via `avgo_guard` preview run too: the pre-existing pipeline
was never broken by this session's changes.

**Gap found while reviewing STLD's own recommendation:** its last
earnings was 2026-07-20 (a small beat, +0.56% surprise), 10 days before
this recommendation -- and nothing in the live screen checks days-since-
last-earnings. Gate 4 only looks FORWARD (next earnings within
hold_days); the execution-drift filter (built 2026-07-29, itself
motivated by an earlier STLD post-earnings-gap incident) only catches a
chase happening the SAME day (today's live price vs. today's signal
close) -- it read -0.1% drift here because STLD's pop had already
happened and settled over a week earlier, nothing same-day left to
catch. Two distinct problems, only one of which is covered: chasing a
live pop (covered by execution-drift) vs. entering into an
already-priced-in pop from days earlier (not covered by anything).
**Not built. Backlog, not urgent** -- discussed live, user has not yet
decided whether to add a days-since-last-earnings gate.

## Basket-crash visibility decoupled from extension-gate priority (2026-07-30)

Follow-on design change, live-discussed the same day: basket_crash was
previously only computed/displayed when the extension pathway had NO
pick (`if pick is None:` gated the whole block in both `run_entry_
screen()` and `sleeve_daily_summary()`). User's objection: the sleeve
being CLOSED (no position, no capital committed) means there's no real
reason to hide basket_crash info just because extension also found
something that day -- suppression only made sense as a stand-in for "no
free slot," but a candidate existing isn't the same as a slot being
used. The two are now decoupled:

- **Priority still applies to which one is labeled the preferred pick**
  if both exist and you can only act on one -- extension is
  live-validated (real trade, tuned on 4,321 entries), basket_crash is
  backtest-only (299 entries, never fired). Rationale unchanged from
  the original priority decision earlier this session.
- **Suppression is gone.** basket_crash is now always computed and
  shown whenever the sleeve is CLOSED, regardless of whether extension
  also has a pick. If both exist, each is shown with its own Plan/Open,
  and a NOTE line cross-references the other ("extension pathway also
  has a candidate today -- that one is preferred").
- Blocking still applies while the sleeve is OPEN (an actual position,
  not just a candidate) -- unchanged, that's the real 1-position-cap
  constraint, not something this decoupling touches.

**Real bug caught while implementing this:** `check_signal_changes.py`'s
`sleeve_plan`/`sleeve_open_cmd` fields used a single generic regex
(first "Plan:" in the section) -- fine when only one candidate could
ever exist, but wrong once both can appear together: the basket-crash
alert would have quoted the EXTENSION's Plan/Open instead of its own.
Fixed by scoping each field to its own candidate label (`Best
candidate` vs `Basket-crash`) via a lookahead-anchored regex, and
splitting into `sleeve_plan`/`sleeve_open_cmd` (extension) vs
`sleeve_basket_plan`/`sleeve_basket_open_cmd` (basket) -- verified with
a new fixture (`FIXTURE_SLEEVE_CLOSED_WITH_BOTH_CANDIDATES`) asserting
neither field leaks the other's ticker.

2 new tests added for the both-real-at-once case (fingerprint scoping +
dual-alert firing with correct content). Full suite: 336 passing.
Verified live via `sleeve_daily_summary()` -- see next session's status
check for whether both a real extension AND real basket-crash candidate
were observed simultaneously (unlikely on any given day, but the code
path is now real and tested either way).

**That prediction resolved same-day: both fired together for real.**
Live check found extension pick STLD alongside a real basket-crash
candidate, **SNDK (Sandisk Corporation)**, $1015.89, Technology, -36.5%
over 5 trading days, 2 peers also crashing -- the decoupled display
worked exactly as designed.

## Execution-drift filter added to basket_crash (2026-07-30)

Same live SNDK case immediately exposed a real gap: by the NEXT session
its price had already reversed **+24.2%** (signal close $1015.89 ->
live $1261.80, intraday high $1272.53) -- a violent one-day bounce off
the crash bottom the signal was built on. basket_crash had deliberately
never run the execution-drift filter (flagged as "not validated for
this population" when the pathway was first built) -- this is live
proof of exactly the risk that filter exists to catch, at a scale (24%)
dwarfing the extension gate's own 0.9% threshold.

**Fix:** `select_best_basket_crash()` now applies the SAME
`_execution_drift_ok()` / `EXECUTION_DRIFT_THRESHOLD` (0.9%) used by
the extension gate -- walks the ranked pool (deepest crash first, same
as before) and skips any candidate that's drifted beyond tolerance
since its signal close, trying the next-ranked one instead. Missing
live-price data still fails OPEN (doesn't exclude), same convention as
the extension gate.

**Explicitly NOT claiming this threshold is right for this population**
-- 0.9% was tuned on the extension gate's near-MA50, momentum-confirmed
entries, not on crash-type entries that are inherently far more
volatile by construction (a stock in a 5d/-10%+ move can easily swing
harder intraday than a calm extension candidate). Reusing it here is a
conservative stopgap, not a validated fit -- it may end up filtering
most or all basket_crash candidates in practice, which would itself be
useful signal (worth a future backtest pass on what threshold actually
suits this population), not evidence of a bug. The alternative -- no
check at all -- is what let SNDK through in the first place.

Shipped: `select_best_basket_crash()` returns `execution_drift` in the
result dict now (mirrors `select_best_candidate`'s pattern). Both
`run_entry_screen()` and `sleeve_daily_summary()` display drift on the
basket-crash pick's summary line, and the "no eligible candidate"
reason text now distinguishes "every candidate already drifted beyond
tolerance" from the other reasons (none crashing, all held). 3 new
tests (skip-and-try-next, none-when-all-fail, missing-price fails
open). Full suite: 339 passing.

## Basket-crash execution-drift: asymmetric band replaces the reused symmetric threshold (2026-07-30)

Follow-on research after shipping the symmetric ±0.9% reuse above --
two studies, in order, both aimed at answering "is the extension gate's
threshold actually the right shape for basket_crash, or just a
convenient stopgap?"

**Study 1 -- basket_crash-specific drift buckets (n=299, the real
declustered population, drift = next-session-open/signal-close - 1,
5 quantile buckets, simulated with the live trailing-only 8%/8% stop):**

| Bucket | drift (median) | med_return | win_rate | early_stop_10d |
|---|---|---|---|---|
| 1 (deep gap-down) | -2.76% | +3.80% | 63.3% | **26.7%** (worst) |
| 2 (slight gap-down) | -0.67% | +4.04% | 66.7% | **11.7%** (best) |
| 3 (near-zero) | +0.22% | +0.55% | 52.5% | 13.6% |
| 4 (slight gap-up) | +1.64% | +1.72% | 58.3% | 15.0% |
| 5 (big gap-up) | +3.17% | **+4.43%** | **70.0%** | 15.0% |

**No U-shape** (unlike the extension gate's own execution-drift study,
which found near-zero drift was the sweet spot). Instead: real
asymmetry. Deep gap-**down** is clearly worse (crash hasn't bottomed --
the reversal thesis isn't confirmed yet). Gap-**up** does NOT get
punished -- the biggest up-drift bucket has the best return and win
rate of all five. Conceptually coherent: basket_crash is a reversal
bet, so a gap up before execution is often the bounce validating
itself in real time, not overextension the way it is for the extension
gate's continuation bet.

**Caveat immediately surfaced: this population had almost no data near
SNDK's actual size.** Max drift observed in all 299 entries: +7.7% up,
-12.5% down. SNDK moved +24.2%. The "gap-up isn't punished" finding is
real within the tested range, but doesn't by itself justify leaving the
upside completely unfiltered at SNDK's magnitude.

**Study 2 -- broader gap-up study, NOT basket_crash-gated (n=670
overnight gap-ups of 15%+, full universe, skips the expensive
walk-forward ranking entirely since it isn't gate-1-conditioned --
runs in under a minute instead of ~20):**

| Gap band | n | med_return | win_rate |
|---|---|---|---|
| 15-20% | 433 | +0.45% | 52.7% |
| 20-30% (SNDK's band) | 179 | +1.59% | 54.2% |
| >=30% | 58 | +0.04% | 50.0% |

Median outcome is a roughly flat coin-flip across all bands -- no clear
degradation as gap size grows. **But the median hides a brutal tail**:
within SNDK's own band, real losses of -64% (MS 2008), -57% (TRGP
2020), -55% (HBAN 2009), -54% (CCL 2020), -46% (BAC 2008) sit alongside
huge winners (+184% AIG 2009, +97% SW 2009). **Most of those worst
losses were "held to 21d exit" -- never stopped** -- the trailing-only
stop only arms after ANOTHER +8% gain, which frequently never comes
after an already-large gap, so the exact protection basket_crash relies
on is close to absent in this specific scenario. Bonus finding: SNDK
itself had an earlier +20.8% gap on 2026-01-30 that resolved essentially
flat (-0.2%) over 21 days -- direct single-ticker precedent, though n=1.

**Conclusion and design:** replaced the symmetric ±0.9% (reused from the
extension gate, shipped as an explicit stopgap) with an asymmetric band
grounded in both studies:
- `BASKET_DRIFT_DOWN_LIMIT = -0.025` (-2.5%) -- matches where Study 1's
  early-stop-rate clearly worsens (roughly the 25th percentile of
  observed negative drifts, close to bucket 1's -2.76% median).
- `BASKET_DRIFT_UP_LIMIT = 0.08` (+8%) -- the actual tested ceiling in
  Study 1 (max observed +7.7%, rounded up slightly for headroom).
  Beyond this is genuinely untested for basket_crash specifically, and
  Study 2 shows real, largely-unprotected tail risk starts well before
  SNDK's own +24.2% -- capping here, not at SNDK's size, is the
  defensible line given what's actually been validated.

**This does NOT solve the SNDK problem on its own** -- SNDK's own drift
was +24.2%, so the NEW cap (+8%) does reject it, unlike the old
symmetric filter reused verbatim would have (it also rejected it, since
0.9% << 24.2%, so both old and new filters happen to reject SNDK
specifically -- the shape difference matters for candidates in the
+1-8% range, which the old filter wrongly rejected and the new one
correctly allows).

Shipped: `_basket_drift_ok()` (new, asymmetric-band-specific, distinct
from `_execution_drift_ok()` which the extension gate keeps using
unchanged). `select_best_basket_crash()` switched from
`_execution_drift_ok` to `_basket_drift_ok`. Print text in
`run_entry_screen()` updated to describe the actual band instead of
"same threshold as the extension gate." 9 tests (band boundaries in
both directions, missing-data fails open, skip-and-try-next). Full
suite: 346 passing.

**Scripts added** (both report-only, no gate/threshold change implied by
running them): `run_opp_sleeve_basket_execution_drift_analysis.py`
(Study 1 -- also saves raw per-entry rows to `comparison_results/
opp_sleeve_basket_execution_drift_entries.csv` for tail drilldowns
without re-running the ~15-20min pipeline) and
`run_gap_up_forward_return_analysis.py` (Study 2 -- general-universe gap
scan, no walk-forward step needed, runs in under a minute).

**Still open:** the -2.5% / +8% band is grounded in real data but not
precision-tuned (bucket medians, not exact breakpoints -- Study 1's
population is thin, ~60 entries/bucket). Revisit if/when basket_crash
accumulates its own live track record.

## Session close: basket_crash is LIVE (2026-07-30, PR #85 merged as ea9118f)

Everything above in this session (live plumbing, concentration cap,
trailing-only stop, Telegram wiring, visibility decoupling,
execution-drift protection, the asymmetric drift band) is merged to
`master` and running for real -- not a proposal, not staged in an open
PR anymore. The next scheduled `sync.yml` run (weekdays ~08:00/22:30
CEST) executes it automatically: no manual trigger needed. Full test
suite passing on master (346).

**Quick orientation for picking this up cold:**
- basket_crash is a *secondary* signal -- fires alongside or instead of
  the existing extension-gate pathway, never replaces it. Extension is
  still labeled preferred when both exist (live-validated vs.
  backtest-only).
- Position cap is still 1 total across both pathways -- nothing here
  changes that. Opening a basket_crash position uses `--open TICKER
  PRICE SHARES CAPITAL --entry-type basket_crash`.
- The edge: 299 real historical basket-crash entries (peer-confirmed
  sector capitulation) beat 953 solo idiosyncratic crashes cleanly at
  every duration tested (21d +4.41% vs +1.13%, 66.6% vs 54.7% win rate).
  Backtest-only -- no live trade has happened on this pathway yet.

**Real open items, not blockers, worth revisiting when there's time or
once basket_crash has its own live track record:**
1. Days-since-last-earnings gate -- still not built (see "STLD ...
   days-since-earnings gap" entry above). Nothing checks whether a
   candidate's setup was caused by a recent earnings print.
2. The -2.5%/+8% drift band is data-grounded but not precision-tuned
   (thin population, bucket medians not exact breakpoints).
3. No live basket_crash trade has fired yet -- first real one is worth
   a close look end-to-end (does the Telegram message read clearly in
   practice, does the trailing-only stop behave as expected) before
   trusting the mechanism blindly.

## LLY earnings-day reaction is noise, not signal (2026-07-31)

One-off diagnostic on LLY's own real historical earnings dates (99
events, 2000-2026, real Surprise(%) from `_earnings_surprises()`):

| | Pre-5d run-up | Earnings reaction | Post-21d drift |
|---|---|---|---|
| All (n=99) | +0.0% (49% win) | +0.1% (51% win) | +0.4% (52% win) |
| Beats (n=74) | +0.3% (57% win) | +0.1% (51% win) | +0.2% (50% win) |
| Misses (n=25) | -1.4% (28% win) | -0.4% (48% win) | +2.1% (56% win) |

Median reaction is ~0% with a coin-flip win rate in both directions --
no exploitable pre-earnings run-up or post-earnings drift for LLY
specifically. The "misses drift up more" line (+2.1%) rests on 25
events and reads as post-dip mean-reversion, not a real edge.
Informational only -- doesn't touch any live gate. Diagnostic script,
test, and workflow deleted after logging this.

## median x win_rate - stop_distance x loss_rate is not a valid expectancy formula (2026-07-31)

Caught mid-conversation: eyeballing an opp-sleeve candidate's expectancy as
`win_rate * median_return - loss_rate * stop_distance` is wrong, because
median_return is the median of the WHOLE distribution (wins and losses
together), not the average size of winning trades, and stop_distance isn't
the average losing trade either. Naive formula for STLD's live candidacy
gave -1.05% (looked like negative expectancy).

Real fix: split the same regime-matched historical return distribution
run_entry_screen.py already builds (duration_matched_return's raw `rets`,
previously discarded after computing median/win-rate) into winners and
losers, and use their actual means. For STLD (n=1390, HIGH/TIGHT regime,
21d duration): win rate 60.5%, mean win +8.2%, mean loss -6.7% ->
**real expectancy +2.27%**. Genuinely positive, just not derivable from
median + win rate alone. Diagnostic script/test/workflow deleted after
logging this; not wired into any live gate (informational check only).

## STLD conditional-median check: mean-based expectancy is not outlier-driven (2026-07-31)

Follow-up to the STLD real-expectancy finding (+2.27% mean-based). Checked
whether that mean was inflated by a few outlier winners by comparing against
medians computed WITHIN the winners/losers groups (same 1390-sample
regime-matched history, HIGH/TIGHT, 21d):

|          | Mean  | Median | Max    |
|----------|-------|--------|--------|
| Win (n=841)  | +8.2% | +6.9%  | +32.1% |
| Loss (n=549) | -6.7% | -5.8%  | -21.8% |

Median-based expectancy: +1.87%, only 0.40% below the mean-based +2.27%.
Small gap -> the edge is a genuinely typical effect across the sample, not
an artifact of a handful of huge winners. Diagnostic script/test/workflow
deleted after logging this; informational only, not wired into any live
gate.

**Backlogged, not built:** a downside-specific outlier check. The mean
vs. median comparison above tests both tails together; the more useful
version would isolate the LOSS side and re-run it against the actual
stop-adjusted loss (the live binding_stop mechanism cuts a trade around
-6.8% from entry, well inside the raw historical max loss of -21.8%),
not the raw fixed-21d-window loss used here. Point being: upside skew is
usually fine (or even the point, for a trailing-stop "let winners run"
design) -- it's specifically hidden downside tail risk that would be
worth flagging, and that requires reconstructing the stop-adjusted loss
distribution rather than reusing the raw one. Worth a proper look when
there's time; not urgent, no live gate depends on it.

## Backlogged: decompose the AVGO crash-ROC trigger's false-alarm rate (2026-08-03)

Operator's skepticism, worth a real answer rather than trend-following
philosophy alone: the crash trigger (5d ROC <=-10%, see fi_tracker.py)
doesn't trim AVGO on a fire -- it flips the target straight to 0%
("Rotate AVGO -> Gold+LLY"), the same severity as a slow 200d SMA
breakdown. If that trigger frequently fires on transient, sector-wide
panics that then rebound, the system could be selling AVGO at close to
the worst possible moment -- the same kind of setup basket_crash exists
to buy *into* on other tickers.

Related, already answered but not the same question: "AVGO gap-down x
200d Guard state" (2026-07-28, above) found guard-active gap-downs
bounce HARDER than guard-base ones, and reasoned this isn't a
contradiction because the guard optimizes full-cycle tail risk
(Sharpe/MaxDD/Calmar), not individual dip-bounce timing. That finding is
about guard STATE broadly; it doesn't decompose the crash-ROC trigger
specifically, and doesn't answer false-alarm rate vs. true-positive
rate -- only that guard-active dips as a whole tend to bounce.

What's still missing: for every historical date the crash-ROC trigger
would have fired, split into "kept falling further" vs. "rebounded
within N days" and report the split, plus the cost of the false alarms
in isolation (not just the net aggregate return the 20-cell parameter
grid already validated). The grid confirms the trigger wins in
aggregate; it doesn't say whether that's from rescuing the portfolio
from a couple of real disasters while eating frequent, costly whipsaws,
or from being right most of the time. Those are very different risk
profiles wearing the same headline number. Not urgent -- the guard is
live and already validated in aggregate -- but worth a proper look
before fully trusting the crash-ROC leg specifically.

## AVGO crash-ROC guard: basket (sector-wide) crashes bounce HARDER than solo ones (2026-08-04)

Direct follow-up to the backlogged crash-ROC false-alarm item (2026-08-03)
and the operator's unease about the guard flipping AVGO to 0% during a
sector-wide crash -- exactly the scenario basket_crash exists to buy into
on other tickers. Reconstructed all 25 historical dates AVGO's own
crash-ROC trigger (5d ROC <=-10%, same threshold as the live guard) would
have fired, declustered, split into solo (AVGO alone) vs. basket (>=2 of
12 real semiconductor peers -- NVDA/AMD/INTC/TXN/QCOM/MU/AMAT/LRCX/KLAC/
ADI/MRVL/ON -- also in a 5d/-10% crash the same date):

**18 of 25 events (72%) were basket, not solo** -- the sector-wide
scenario is the majority case, not an edge case.

| | 21d | 63d |
|---|---|---|
| Solo (n=7)    | +1.1% median, 57% win | +11.2% median, 86% win |
| Basket (n=18) | +4.8% median, 72% win | +12.9% median, 94% win |

Basket crashes bounce harder AND more reliably than solo crashes at both
horizons -- consistent with (and now more specific than) the earlier
"AVGO gap-down x 200d Guard state" finding (2026-07-28, guard-active gaps
bounce harder generally). This is exactly the case the guard's full
"Rotate AVGO -> Gold+LLY (0% AVGO)" response is theoretically most
defensive about, and empirically it's the case with the best, most
reliable rebound.

**Same caveat as the 2026-07-28 finding still applies -- do NOT read
this as "turn the guard off" or "ignore basket crashes":** the guard's
job is capping tail risk across the FULL cycle (validated separately on
Sharpe/MaxDD/Calmar), not predicting individual bounces. A high bounce
rate doesn't offset the value of the rare real-disaster case the guard
exists to cut.

**What this DOES support, worth a real proposal before building:** the
guard currently treats solo and basket crashes identically (same full
0%-target flip). Given basket crashes empirically bounce better, a
softened response specifically for basket-confirmed triggers (e.g.
partial rotation instead of full 0%) is worth modeling properly --
backtest a graduated response against the existing binary one on
Sharpe/MaxDD/Calmar before touching the live guard. Not built --
informational only, diagnostic script/test/workflow deleted after
logging this.

## AVGO guard resolved: graduated response for basket crashes does NOT beat the current full flip (2026-08-04)

Direct resolution of the backlogged item and the basket-crash-bounce
finding above. Built a graduated-response backtest: basket-confirmed
crash-ROC triggers get a partial rotation (AVGO weight interpolated
between full exposure and 0% by a rotation_fraction), MA-breach and solo
crash-ROC triggers unchanged (full flip). Grid over rotation_fraction,
Sharpe/MaxDD/Calmar, AVGO's full history (2009-2026), same rigor as the
original guard validation:

| rotation_fraction | CAGR  | MaxDD | Sharpe | Calmar |
|---|---|---|---|---|
| 0.00 (ignore basket trigger) | +37.3% | -16.8% | 1.697 | 2.219 |
| 0.25 | +37.3% | -16.8% | 1.703 | 2.216 |
| 0.50 | +38.2% | -16.8% | 1.747 | 2.273 |
| 0.75 | +39.2% | -16.8% | 1.788 | 2.329 |
| 1.00 (current, full flip)   | **+40.3%** | -16.8% | **1.835** | **2.399** |

**The current full-flip response wins outright on every metric.** MaxDD is
IDENTICAL across every fraction -- AVGO's worst historical drawdown is
unrelated to these basket-crash-ROC events, so softening the response
buys zero tail-risk benefit while giving up CAGR/Sharpe/Calmar
monotonically as the rotation fraction decreases.

This does not contradict the per-event finding above (basket crashes
bounce harder/more reliably on a 21d/63d point-return basis) -- it
resolves at a different level. The per-event view only looks at where
price ends up after N days; this portfolio simulation captures realized
volatility DURING the crash window itself (compounding, not just
endpoint). Staying partially exposed through a choppy sector-wide crash
costs more in volatility drag than the eventual bounce recovers.

**Resolved -- no change to the live guard.** Diagnostic script/test/
workflow deleted after logging this. If revisited later, the per-event
bounce evidence is real but insufficient on its own; any future guard
change needs to clear this same portfolio-level bar, not just the
event-level one.

## War chest SUSPENDED (not retired) -- target updated to Reactor Core 83.3% / Home Base 16.7% (2026-08-04)

> **SUPERSEDED for the bucket split only (2026-08-19).** The 83.3/16.7
> figures below were replaced by **85/15** on 2026-08-17 ("Reactor Core
> DECIDED at 85% / Home Base 15%" above) and now live in
> `config/portfolio.toml`'s `[buckets]` table, which is the single source of
> truth. This entry was still being read as current alongside that one --
> two live splits in one file. **The war-chest suspension itself stands**,
> as does the ceiling-derivation reasoning, which is why the entry is marked
> rather than deleted. If the war chest is un-suspended, re-derive against
> the 85/15 baseline, not the 83.3/4.5/12.2 one named below.

Operator's call: the war chest / opp sleeve concept stays (it's a real,
validated, positive-expectancy mechanism -- see the STLD expectancy work
above), but the war chest is SUSPENDED for now, not permanently retired.
Its target allocation is reassigned while suspended.

**Updated target (supersedes "Rebalance -- DECIDED 2026-07-02" above
for the bucket split only -- the 83.3% Reactor Core figure and its
derivation are unchanged):**

  Reactor Core 83.3% / Home Base 16.7% / War Chest 0% (suspended)

The freed 4.5% goes ENTIRELY to Home Base, not split with Reactor Core.
Reason: 83.3% is not a preference, it's a hard ceiling --
`-25% max portfolio drawdown tolerance / -30% Reactor Core worst-case
MaxDD (crash-guard-improved TXN analog) = 83.3%`, derived assuming
everything outside Reactor Core has ~0% drawdown risk. Reactor Core is
already at the maximum weight that tolerance allows; raising it further
(via a split) would exceed the -25% portfolio drawdown ceiling the
83.3% figure exists to enforce. Home Base (Spiltan Räntefond, low-vol)
is the bucket the ceiling assumes absorbs everything Reactor Core can't
safely hold, so it's the only correct destination for the freed capital.

Not enforced by any live code (no script reads the bucket-level target
split -- it's a planning reference only, checked manually against
`status.md`'s TPV breakdown). If the war chest is un-suspended later,
revert to Reactor Core 83.3% / War Chest 4.5% / Home Base 12.2%.

## Midterm-election pattern shows up in all 3 core holdings (2026-08-07)

Checked whether the well-known US midterm-election-year pattern (weak
run-up, strong post-election rally) shows up in AVGO/LLY/Gold
specifically, not just the broad index. Real historical US midterm
election dates (2002, 2006, 2010, 2014, 2018, 2022 -- 2026-11-03 is
next, ~3 months out as of this entry). Convention: idx = first trading
day on/after the election.

| | post_21d | post_63d | post_252d | n |
|---|---|---|---|---|
| AVGO | +14.1% med, 100% win | +23.1% med, 100% win | +44.6% med, 100% win | 4 (IPO 2009, only 4 midterms available) |
| LLY  | +4.7% med, 67% win  | +3.8% med, 67% win   | +13.8% med, 83% win  | 6 |
| Gold | +2.5% med, 100% win | +7.7% med, 83% win   | +19.6% med, 83% win  | 6 |

All three show a genuinely positive post-midterm drift. Caveat: n=4-6
per asset -- real pattern, thin sample, not heavily powered (this is
descriptive, not backtest-grade validation like the AVGO gap-down or
opp-sleeve studies). Notable: **Gold's midterm-election signal is
cleaner and stronger than its own gap-down signal** (which was
weak/noisy, 2026-07-28 entry above) -- if Gold needs a tactical timing
signal at all, this looks like a better candidate than gap-down.

Informational only -- not wired into any live gate. Diagnostic script,
test, and workflow deleted after logging this.

## Yield curve uninversion dates confirmed from real FRED data (2026-08-09)

Operator asked when T10Y2Y/T10Y3M uninverted (recession-timing context
-- historically uninversion, not inversion, has preceded recession
onset as the Fed cuts short rates faster than long rates fall). My
from-memory guess was wrong (esp. T10Y3M, off by ~10 months) -- pulled
real dates from the tracked FRED series instead:

- **T10Y2Y**: durably uninverted 2024-09-06 (some noisy flipping right
  at the crossing in late Aug/early Sept 2024 before holding). Current
  +0.46, no re-inversion in 702 days as of 2026-08-07.
- **T10Y3M**: durably uninverted 2025-10-17 (also choppy through most
  of 2025 before holding). Current +0.78, no re-inversion in 296 days.

T10Y3M is the curve the NY Fed's own recession-probability model uses;
~10 months past its uninversion is squarely inside the historical
6-18-month window recessions have tended to start in. T10Y2Y's 23
months since uninversion is longer than typical without a recession
yet. Informational only -- not wired into any live gate. Diagnostic
script/test/workflow deleted after logging this.

## Remaining AVGO tranche (~100k kr): deployment plan decided (2026-08-10)

Last ~100k kr of the AVGO rebalance (funded by prior WMT/CCJ/VRT/HWM
proceeds) split into two tranches instead of one lump-sum entry, each
tied to a signal already validated this session rather than a guess:

- **Half on a real gap-down**, if/when AVGO prints an actual -10%/5d
  crash-ROC move before the midterm window below -- same trigger class
  the crash guard itself watches (`CRASH_ROC_WINDOW=5`,
  `CRASH_ROC_THRESHOLD=-0.10`), not a minor pullback. A 2026-08-07
  1.22% close-to-close pullback (AVGO $427.76, +8.3% above 50MA,
  +16.7% above 200SMA, 5d ROC +9.9%) was explicitly evaluated and
  rejected as this trigger -- noise, nowhere close to -10%/5d, guard
  state BASE throughout.
- **Remainder deployed after 2026-11-03** (the next US midterm
  election), per this session's midterm-election seasonality finding
  (AVGO post-election window showed a positive pattern, n=4-6,
  descriptive not backtest-grade -- see "Midterm-election pattern"
  above).
- If neither the gap-down trigger fires nor the midterm date is
  reached, evaluated opportunity cost vs. the lump-sum-now alternative
  at ~400k current AVGO size and concluded the split plan's
  risk-adjusted expected value still wins -- bottom line reaffirmed
  this session, no new backtest built for this specific comparison
  (reasoned from existing validated pieces, not a fresh script).

Not wired into any code/automation -- this is an operator capital-
deployment decision, tracked here for continuity, not a live gate.

## Gap-down tranche validated: new capital dip-buying AVGO at a real crash-ROC trigger beats the alternatives (2026-08-14)

Operator pushed back on the tranche plan above as counterintuitive --
the guard rotates *held* AVGO out to defensive on a crash-ROC trigger,
while the plan says put *new* capital into AVGO at that same trigger.
Both actions are defensible (different capital, different risk budget)
but the "buy AVGO on the dip" half was never itself backtested, only
argued from adjacent evidence (guard validation + basket-bounce
magnitude). Built `run_new_capital_deployment_test.py` to close that
gap directly: at every declustered AVGO crash-ROC trigger in real
history (32 events, 2009-2026, min 21 trading days apart), compared
forward returns of three uses for previously-uninvested capital --
(A) straight into AVGO, (B) into the guard's own defensive mix
(Gold52.5/LLY47.5, mirroring what the held position rotates into), (C)
into the static unguarded base mix (Gold25/AVGO55/LLY20, as if the
crash were ignored).

**Result: A wins on every horizon, decisively past the first month.**

| Horizon | A (dip-buy) med/ave | B (defensive) med/ave | C (unguarded) med/ave | A>B win-rate | A>C win-rate |
|---|---|---|---|---|---|
| 21d | +4.7% / +6.1% | +2.1% / +2.5% | +4.5% / +4.6% | 56% | 50% |
| 63d | +13.1% / +17.8% | +4.9% / +5.5% | +11.2% / +12.6% | 81% | 68% |
| 126d | +30.7% / +33.0% | +8.9% / +9.2% | +20.5% / +22.7% | 87% | 84% |
| 252d | +64.7% / +61.8% | +22.7% / +25.3% | +45.6% / +46.9% | 83% | 77% |

At 21d, A vs. C (dip-buy vs. just ignoring the crash) is a coin flip --
short-horizon noise, no real edge yet. Past that the edge is
substantial and grows with time, both in magnitude and win-rate. A
beats the defensive mix at every horizon by a wide margin throughout,
confirming new capital sitting in the same defensive assets the guard
rotates *into* is a clear opportunity-cost loser vs. buying the actual
crash.

**Net: proves the combo strategy is coherent, not just individually
plausible halves.** Rotate held AVGO out (already validated,
2026-08-04) *and* deploy new capital into AVGO at the same trigger
(now validated here) are both independently the better choice for
their respective capital pools -- not a contradiction, confirmed with
real numbers rather than just risk-budget reasoning. n=30-32,
descriptive/event-study not a compounding portfolio simulation (each
trigger treated independently, no attempt to net overlapping windows
across the 32 events). Diagnostic script, test, and workflow deleted
after logging this, per repo convention.

## Small speculative Bitcoin position -- held, deliberately untracked (2026-08-21)

Real position, real capital, but **not** in `portfolio.toml` and not part
of any bucket target -- operator briefly added it to the Google Sheet
config, then reverted that same session on the concrete methodological
concerns raised (price data not registered in the download universe
would have broken `fi_pace()`'s "raise on any missing price" behavior;
and Reactor Core's 85/15 bucket-drift math, which drives real rebalance
instructions, shouldn't be distorted by fun money it was never sized
for).

**Position (updated 2026-08-21):** 171 shares, Virtune Bitcoin
(Swedish-listed ETP), @ 118.27 SEK/share = **20,224 kr**, ~1.83% of TPV
(1,102,656 kr) -- added to from the initial 145-share/17,104 kr tranche
logged same day. Still inside the "doesn't matter if it goes to zero"
range discussed (~1-2% of TPV), now near the top of it rather than the
middle -- worth noting if it grows further. Original entry prompted by
Bitcoin's 200-day-SMA reclaim after 270 days below it (2026-08-19/20
news).

**Deliberately off-book.** Logged here for continuity/record-keeping
only -- not in `portfolio.toml`, not in any snapshot/TPV calculation,
not subject to any bucket target or rebalance instruction. If this
changes (position grows, or the operator wants it tracked), it needs
its own bucket outside `reactor_core`/`home_base` so it doesn't
contaminate the drawdown-ceiling-derived bucket math, and its ticker
needs to actually exist in the download universe before it's added to
`portfolio.toml` -- neither was true when the reverted attempt was made.

## BTC trend-following: real signal, but the 200d rule specifically is weak, era-dependent and cost-fragile (2026-08-24)

Operator asked whether it's possible to "bet on BTC when it's about to or
has started rallying." First pass (`run_btc_momentum_check.py`) reported
200d SMA trend beating buy-and-hold on Sharpe/Calmar and I presented that
as a clean positive. Operator asked for verification -- correctly, given
this project has twice shipped an "edge" that did not survive it (AVGO
200d guard = lookahead bias; AVGO vol-targeting = did not reproduce).
Built `run_btc_momentum_validation.py` + 6 unit tests. Six independent
checks; **two passed cleanly, one found a real bug in my own reported
numbers, and three materially qualified the result.**

**BUG FOUND IN THE FIRST REPORT: wrong annualization.** BTC trades 365
days/yr; I annualized Sharpe with sqrt(252). Reported Sharpes (B&H 0.911,
trend 0.958) are wrong. Correct: **B&H 1.096, trend 1.153.** Both arms were
wrong by the same factor so the ranking never changed, and CAGR/MaxDD/
Calmar were unaffected -- but the absolute figures were misstated.

**PASSED -- not lookahead-contaminated.** Ran the identical code path with
shift(1) removed as a deliberate biased twin: Calmar 0.846 (correct) vs
**2.139 (lookahead), +153%.** The reported result is the worse of the two,
which is what a correctly-shifted backtest must be. Unit test asserts the
shift(1) arm provably cannot capture a signal-day spike the twin does.
This is the exact failure mode that voided the AVGO guard.

**PASSED -- survives realistic execution.** Next-day-OPEN fill on real OHLC:
Calmar 0.845 vs 0.846 close-fill -- essentially identical. This is the
check every AVGO guard execution model failed. **Structural reason it
passes here: BTC trades 24/7, so there is no overnight gap between a
signal close and the next open.** The AVGO guard died precisely on that
gap. Do not generalize this pass to any equity signal.

**QUALIFIED -- 200d is the WEAKEST member of the family.** Grid over
{50,100,150,200,250,300}: all 6 beat B&H on Calmar (each vs its own start),
so the effect is a family not a spike -- but 200d's edge (+0.064) is the
smallest of the six. 50d (+0.482), 150d (+0.443), 100d (+0.273) are far
stronger. Reassuring for robustness (the quoted number was not cherry-picked
to the best cell) but it means 200d specifically is a poor choice.

**QUALIFIED -- the edge is concentrated in early history.** Sub-periods
(200d, Calmar, trend vs B&H): 2016-2018 **+0.697** (trend wins big),
2019-2022 -0.018 (wash), 2023-2026 +0.177 (trend wins), full-sample +0.064.
**But dropping to 2020-onward flips it negative: -0.036, B&H wins.** The
full-sample edge is substantially carried by 2016-2018 -- thin, illiquid,
structurally different BTC. Coherent story: long clean trends 2016-2018,
whipsawed by the COVID V-shape and the choppy 2021 double-top, working
again 2023-2026. That is regime-dependent, not a stable edge.

**QUALIFIED -- dies at realistic cost.** TC sweep per flip: 5bp +0.082,
15bp +0.064, **50bp +0.004 (gone), 100bp -0.078 (negative).** And the
operator does not hold spot BTC -- he holds a **Virtune ETP**, whose
bid/ask spread plus annual management fee are **not modelled here at all**.
Realistic all-in round-trip cost for that wrapper plausibly sits at or past
the 50bp point where the edge is already zero.

**Verdict: "yes, this is possible" was too strong.** The trend family shows
a real, non-lookahead, execution-robust signal on spot BTC. The specific
200d rule quoted is the weakest window, its full-sample edge leans on
2015-2018, it loses outright post-2020, and it does not survive Virtune-
realistic costs. **Not actioned, nothing wired.** If revisited, the honest
next steps are: test 50d/150d rather than 200d, get Virtune's real spread
and management fee into the cost model, and treat the post-2020 sub-period
as the decision-relevant window rather than the full sample. Script, tests
and workflow deleted after logging, per repo convention.

## BTC trend on the ACTUAL instrument: the entry above is too pessimistic -- it anchored on 200d, the one window that fails (2026-08-24)

**Supersedes the pessimistic half of the entry directly above.** That entry
passed its execution-realism check on the reasoning "BTC trades 24/7, so
there is no signal-to-fill gap." Operator corrected the premise: he does not
hold spot BTC, he holds **Virtune Bitcoin, a Swedish-listed ETP trading
~252 exchange days/yr.** BTC moves nights and weekends; the ETP cannot be
traded then. A Friday-close signal is not actionable until Monday --
structurally the same gap that voided the AVGO 200d guard, so the prior
PASS did not transfer and had to be re-earned.

Built `run_btc_etp_execution_check.py` + 5 unit tests (one asserts the ETP
position series provably never changes on a weekend bar; a control asserts
the 24/7 model does, so that test is not vacuous).

**PREDICTION MADE BEFORE RUNNING: the weekday-only constraint would degrade
the result. It did the opposite -- it IMPROVED it in every single window.**

Weekend gap is real and large (Fri-close -> Mon-close, n=623): median
|move| 2.27%, mean 3.60%, 90th pct 8.46%, worst -22.68%, and **25.2% of
weekends move >5%, 6.6% move >10%.** Genuine unreactable exposure. But the
inability to trade it turns out to be a *filter*, not a cost -- it blocks
whipsaw round-trips on weekend noise. Calmar gained purely from the
constraint: +0.042 (50d), +0.055 (100d), **+0.078 (150d)**, +0.020 (200d),
+0.046 (250d).

**Tradeable-ETP results, full sample (B&H Calmar 0.782):**

| Window | ETP CAGR | ETP Calmar | vs B&H |
|---|---|---|---|
| 50 | +73.4% | 1.223 | +0.519 |
| 100 | +62.9% | 1.048 | +0.330 |
| **150** | **+77.4%** | **1.304** | **+0.511** |
| 200 | +58.7% | 0.866 | +0.085 |
| 250 | +62.1% | 0.966 | +0.161 |

**Post-2020 -- the window the prior entry called fatal (B&H Calmar 0.560):**
50d **+0.519**, 100d **+0.475**, 150d **+0.539**, 250d +0.059 all beat
buy-and-hold; only **200d loses (-0.089)**. 4/5 windows win. The prior
entry's "post-2020 the edge is gone" was **true only of 200d** and was
wrongly generalized to the family. 200d is not a representative member --
it is the singular failure.

**Cost robustness at 150d is in a different class than 200d's.** 200d died
at 50bp/flip. 150d: 5bp +0.535, 15bp +0.511, 50bp +0.428, 100bp +0.318,
**150bp still +0.213** vs buy-and-hold. It does not die at any plausible
Swedish-ETP round-trip cost.

**Honest remaining gaps -- none of these were modelled:**
1. **FX.** Virtune is SEK-denominated tracking a USD asset. All of the above
   uses BTC-USD; the SEK/USD leg is absent entirely. Real.
2. **Tracking error** between the ETP and spot BTC.
3. **Virtune's annual management fee** -- a drag on the trend arm and on
   buy-and-hold alike, so roughly neutral to the *comparison* but it does
   cut absolute returns.
4. **Selection.** 150d was named best after seeing the grid. Mitigated by
   4 of 5 windows working post-2020 (family, not a point), but not zero.
5. Post-2020 is ~6.6 years, a single regime, n=1.

**Verdict: BTC trend-following is materially stronger than the entry above
concluded, and my pessimism there came from anchoring on the one broken
window.** Still **not actioned, nothing wired, no live code touched** -- the
FX gap alone means this is not decision-ready for the real instrument.
Script, tests and workflow deleted after logging, per repo convention.

## BTC trend CLOSED as not actionable: with the FX leg in, the natural implementation loses to just holding (2026-08-24)

**Closing entry for the BTC trend thread. Supersedes the optimistic verdict
of the entry directly above.** Operator asked to close gap #1 -- add the
SEK/USD leg -- and rerun 150d. Built `run_btc_fx_check.py` + 6 unit tests
(one pins the FX direction to `portfolio.py`'s own `price_sek = price *
usdsek` convention; one asserts weekend FX forward-fill puts the whole gap
on Monday's bar, as a Monday ETP open actually does).

Model: `BTC_SEK = BTC_USD x USDSEK`, so holding the ETP is long BTC **and**
long USD vs SEK; flat is SEK cash with neither exposure. **USDSEK moved
7.118 -> 9.471 (+33.1%) across the sample** -- a large tailwind that was
entirely missing from every prior BTC number in this file.

**Two signal variants, because the choice is not obvious and is the
operator's to make in practice:** USD-signal (trend on BTC-USD) vs
SEK-signal (trend on BTC-SEK -- **the line he actually sees in his
broker**, and therefore the natural implementation).

**Post-2020, scored in SEK (B&H BTC-SEK Calmar 0.607):**

| Variant | CAGR | Calmar | vs B&H | Verdict |
|---|---|---|---|---|
| 150d USD-signal | +44.6% | 1.000 | **+0.393** | trend |
| 150d SEK-signal | +32.2% | 0.573 | **-0.034** | **B&H** |
| 200d SEK-signal (control) | +28.9% | 0.468 | -0.139 | B&H |

**THE KILLER: those two signals agree on 97.2% of days (115 days apart out
of ~4,000).** A 2.8% difference in positioning swings post-2020 Calmar by
**0.427** -- from clearly winning to losing. An effect that fragile to an
essentially arbitrary implementation choice is noise-dominated, not
structural, and **cannot be picked correctly ex ante.** The variant that
loses is also the one the operator would naturally reach for.

Secondary damage: the benchmark got HARDER (B&H BTC-SEK Calmar 0.814 vs
BTC-USD 0.782 -- the weak SEK flattered buy-and-hold too), the full-sample
edge for the natural SEK-signal shrank to +0.166 (from +0.511 USD-only),
and cost tolerance dropped -- **SEK-signal dies at 100bp/flip (-0.031)**
where the USD-only version had survived 150bp.

**Pattern worth naming, because it is the real lesson.** Each added dose of
realism moved the answer, and the moves were not random -- they tracked how
close the model got to the actual instrument: BTC-USD daily (looked strong)
-> weekday-only ETP execution (looked stronger, genuinely) -> **FX leg in
SEK (edge collapses under the natural implementation)**. I revised the
verdict twice in one session, once up and once down. That oscillation is
itself the finding: this is a marginal effect that survives only under
particular modelling choices, which is exactly the profile of the AVGO
guard and vol-targeting before they were retired.

**Verdict: CLOSED, not actionable. Do not trade the 20,224 kr BTC position
on a trend rule.** Hold it as the ~1.8%-of-TPV speculative position already
logged. Nothing wired, no live code touched, `portfolio.toml` untouched.
Still unmodelled and would have to be closed before ANY revisit: Virtune's
tracking error and annual management fee. Script, tests and workflow
deleted after logging, per repo convention.

## BTC trend REOPENED and corrected: the operator's stated thesis defeats the ex-ante objection (2026-08-24)

**Corrects the entry directly above, which was wrong on its central claim.**
That entry closed the thread on the grounds that the two signal variants
(USD-signal vs SEK-signal) agree 97.2% of the time yet diverge sharply in
outcome, therefore the winning variant "cannot be picked correctly ex
ante." Two operator interventions dismantled that.

**1. Judged on the wrong metric.** I scored everything on Calmar and
post-2020 return. The operator's stated purpose is avoiding BTC's
recurring -60% to -80% drawdowns. On THAT metric the result is far more
robust than the entry above implies, and I had the numbers in hand:

| | MaxDD | Recovery needed |
|---|---|---|
| B&H BTC-SEK | -82.2% | +462% |
| 150d SEK-signal | -64.9% | +185% |
| 150d USD-signal | -61.5% | +160% |

**Every window cut drawdown** (50d -59.0%, 100d -61.8%, 150d -61.4%,
200d -70.2%, 250d -65.8%, vs B&H -83.4%), and critically **both signal
variants cut it, including the one I called a loser.** The 97.2%-agreement
fragility argument applies to the RETURN difference between variants. It
does NOT apply to the drawdown effect, which is consistent everywhere.
Caveat that stands: a 150d MA is slow, so it converts -82% into -62%; it
does not exit near the top.

**2. The variant choice was never post-hoc.** Operator's thesis, stated in
his own words: he uses **the Virtune ETP as a vessel and reads signals off
Bitcoin's actual price.** That is a prior, holdable before any backtest,
not hindsight selection -- which was the entire basis of the previous
entry's verdict.

It is also mechanically the better choice independent of any result:
`BTC_SEK = BTC_USD x USDSEK`, so trend-following the SEK line contaminates
a Bitcoin-momentum signal with SEK/USD moves that carry no information
about Bitcoin. You want the trend of the thing being forecast. There is a
*reason* the USD signal is correct, not merely a backtest that prefers it.

**The operator's actual configuration -- USD signal, SEK returns -- is the
best row tested:** full-sample Calmar 1.237 vs B&H-SEK 0.814; post-2020
1.000 vs 0.607; MaxDD -61.5% vs -82.2%.

**What still does NOT survive:** the MAGNITUDE of the return edge. The
+0.393 post-2020 gap rests on 115 differing days out of ~4,000 -- direction
defensible, size a soft estimate. Honest expectation is "materially
shallower drawdowns, return a wash to modestly better," not +0.393.

**Sizing is what makes this academic today.** At 20,224 kr (~1.8% of TPV),
-82% costs ~1.5% of TPV and -62% costs ~1.1% -- the protection is worth
**~0.4% of TPV**, smaller than rebalance bands already tolerated, and not
worth the monitoring overhead. **At 5-10% of TPV the same protection is
worth 1-2% of TPV and the drawdown-ceiling logic governing Reactor Core
would make it required rather than optional.** That is the trigger to
revisit, not a new backtest.

**Status: thesis coherent and accepted, still nothing wired and nothing
actioned.** Fee finding from the same session, separate and more valuable
than any of this: Virtune runs **two** Bitcoin ETPs -- Sustainable
(SE0020845709) at **1.49%/yr** and Bitcoin Prime (SE0025012032) at
**0.25%/yr**, same asset, both SEK on Nasdaq Stockholm. If the position
sits in the 1.49% product, switching is a certain ~1.24%/yr saving needing
no forecast. **Operator has not yet confirmed which product he holds.**
Also corrected: the management fee is NOT neutral between arms as earlier
claimed -- a trend arm is out of the market ~41% of the time and so pays
~41% less fee (~0.6%/yr tailwind at 1.49%), which was never modelled.

## BTC 150d: full economics modelled, RECOMMENDED window is 150d, gated on one checkable number (2026-08-24)

**First run with every leg of the operator's real setup modelled at once.**
All constraints now confirmed by him: instrument is **Virtune Sustainable
Bitcoin ETP (SE0020845709), 1.49%/yr -- the only Virtune BTC ETP on Avanza,
so the 0.25% Prime product is NOT available and 1.49% is a constraint, not
a choice.** SEK-denominated, signal read off BTC-USD (his vessel-vs-signal
thesis), weekday-only execution. `run_btc_full_economics.py` + 7 unit tests
(one proves an always-held trend arm equals buy-and-hold exactly, i.e. the
fee is applied on the same basis to both arms).

**A REAL ERROR IN EVERY PRIOR RUN, and it ran against the strategy.** All
earlier BTC work charged the trend arm its trading costs while giving
buy-and-hold its management fee for free. But a 1.49%/yr ETP fee is paid
only while HOLDING -- buy-and-hold pays it every day; a trend arm out of
the market ~40% of the time pays ~0.90%/yr instead of 1.49%. Correcting
this is worth **+1.02% CAGR** to the trend arm. Not a modelling
preference -- the prior treatment was simply wrong.

**Full sample (2014-2026), 50bp/flip, fee correct on both arms:**

| Window | InMkt | Fee paid | Flips/yr | CAGR | MaxDD | Calmar | vs Hold |
|---|---|---|---|---|---|---|---|
| HOLD | 100% | 1.49% | 0.0 | +66.4% | -82.5% | 0.805 | -- |
| 50 | 58% | 0.86% | 15.4 | +65.1% | -63.1% | 1.032 | +0.227 |
| 100 | 59% | 0.88% | 11.1 | +61.1% | -64.3% | 0.950 | +0.145 |
| **150** | 61% | 0.90% | **6.1** | **+73.3%** | **-62.6%** | **1.170** | **+0.365** |
| 200 | 61% | 0.91% | 6.0 | +52.1% | -69.9% | 0.746 | -0.059 |
| 250 | 65% | 0.97% | 5.1 | +55.5% | -66.7% | 0.833 | +0.028 |

**Post-2020 (50bp/flip) -- the answer to the operator's actual question
about avoiding -60/-80% drawdowns:**

| | CAGR | MaxDD | Calmar | vs Hold |
|---|---|---|---|---|
| HOLD | +41.4% | **-71.5%** | 0.580 | -- |
| 50d | +43.9% | -61.1% | 0.718 | +0.138 |
| 100d | +34.5% | -44.2% | 0.782 | +0.202 |
| **150d** | +39.3% | **-46.1%** | **0.853** | **+0.273** |
| 200d | +22.4% | -69.0% | 0.325 | -0.255 |
| 250d | +27.6% | -60.0% | 0.460 | -0.119 |

**-71.5% -> -46.1% post-2020 at near-identical CAGR.** 150d wins on every
cut; 200d fails again, consistent with every prior run.

**DECISION GATE -- break-even spread, the one input the operator can
verify himself:**
- **150d: 116bp per flip** (6.1 flips/yr)
- 50d: only 45bp per flip (15.4 flips/yr -- 3x the trading kills it)

Below ~1.16% round-trip cost, 150d beats holding. Swedish crypto ETPs
typically quote 30-80bp, which would leave headroom, but **this is
unverified -- check Virtune's actual bid/ask in Avanza's order book before
acting.** That number, not another backtest, decides this.

**Why 150d over 50d beyond the scores:** 6.1 vs 15.4 flips/yr. Lower cost
exposure, a 2.6x higher break-even spread, and far less operational burden
for a manually-executed rule (a missed exit is precisely when the
protection was supposed to fire).

**Caveats that survive:** the 97.2%-signal-agreement fragility means the
MAGNITUDE of the return edge is a soft estimate (direction is defensible,
size is not); post-2020 is a single ~6.6yr regime; Virtune tracking error
still unmodelled; and entry/exit asymmetry (slower exit, faster re-entry)
was never tested and is NOT endorsed.

**Sizing keeps this small regardless.** At 20,224 kr (~1.8% of TPV), the
25-point post-2020 drawdown saving is ~5,000 kr in a crash -- real, but
minor against 1.15M TPV. **Nothing wired, nothing actioned,
`portfolio.toml` untouched.** The revisit trigger remains sizing: at 5-10%
of TPV this stops being optional under the drawdown-ceiling logic that
governs Reactor Core. Script, tests and workflow deleted after logging.

## BTC 150d rule ADOPTED -- spread gate cleared at 0.16% vs 116bp break-even (2026-08-24)

**The decision gate from the entry above is closed.** Operator checked
Virtune's actual bid/ask in Avanza: **0.16%.** Break-even for the 150d rule
was **116bp per flip**, so this clears by roughly **7x**. At 16bp/flip the
150d Calmar lands around **1.25 vs 0.805 for holding** (interpolated
between the run's 0bp -> 1.284 and 25bp -> 1.226 points; not re-run for an
exact figure because a 7x margin makes the precision irrelevant to the
decision).

**Two conservatisms remain in the model, both favouring the rule:**
1. Cost was charged at 16bp per TRANSACTION. If 0.16% is the quoted
   bid/ask, crossing it costs ~8bp per side -- so real cost is likely half
   what was modelled.
2. The flat arm earned **0%** while out of the market. Parking proceeds in
   Home Base (Spiltan Räntefond) earns the short rate on ~40% of the
   calendar. Unmodelled, additive.

**THE RULE, as adopted:**
- Watch **BTC-USD** daily close vs its **150-day SMA** (Bitcoin's own price
  -- the ETP is a vessel; see the vessel-vs-signal entry above for why the
  SEK line is the wrong thing to trend).
- Close **below** the 150d SMA -> sell the Virtune ETP on the **next Swedish
  trading day** (never same-day; the signal day's own move is not capturable).
- Close back **above** -> buy back on the next Swedish trading day.
- Expect **~6 signals/year** (6.1 flips/yr measured).
- Park proceeds in **Home Base** while out, not idle cash.

**Expected outcome, stated honestly:** materially shallower drawdowns
(post-2020 -71.5% -> -46.1% at near-identical CAGR), with return roughly a
wash to modestly better. **Do NOT expect a specific CAGR uplift** -- the
97.2%-signal-agreement fragility means the magnitude is a soft estimate
even though the direction is defensible.

**Scope: manual, off-book, unchanged.** Still not in `portfolio.toml`, still
~1.8% of TPV (20,224 kr), still outside every bucket target and rebalance
instruction. At this size the 25-point drawdown saving is ~5,000 kr in a
crash -- the rule is sound, the sleeve is small. No live code touched.

**Offered and NOT yet actioned:** wiring a BTC-USD 150d signal line into
`fi_tracker.py` as a display-only dashboard entry (same pattern as the
retired AVGO trend diagnostic -- no auto-execution). Would require adding
BTC-USD to the data universe. Awaiting the operator's call, since it
touches live code.

**Still unmodelled:** Virtune tracking error; entry/exit window asymmetry
(slower exit, faster re-entry) which was never tested and is not endorsed.

## AVGO's return is EXTREMELY concentrated: 30 days out of 4,286 carry over half the growth (2026-08-24)

Operator asked whether AVGO's growth came from a few days or was spread
out. Measured on the real 2009-2026 series (`run_avgo_best_days.py` + 6
unit tests, incl. a positive control that a deliberately concentrated
synthetic series is detected and an even one is not).

**Baseline: 4,286 trading days, 17.0 years, 324.5x total, CAGR +40.4%.**

**Miss the best days (they are 1% of the sample):**

| Days removed | % of days | CAGR | Total growth |
|---|---|---|---|
| 0 | 0.00% | +40.4% | 324.5x |
| 1 | 0.02% | +38.6% | 260.7x |
| 5 | 0.12% | +34.0% | 147.3x |
| 10 | 0.23% | +29.8% | 85.4x |
| 20 | 0.47% | +23.0% | 34.0x |
| 30 | 0.70% | +17.3% | 15.3x |
| **50** | **1.17%** | **+8.2%** | **3.8x** |

**Share of total compounded growth:** top 10 days = 23.1%, top 20 = 39.0%,
**top 30 = 52.9%**, top 50 = 76.8%. Missing 1.17% of days destroys 99% of
the wealth (324.5x -> 3.8x).

**THE MIRROR, which must be quoted alongside it.** Missing the 50 WORST
days takes 324.5x -> **22,965x** and CAGR +40.4% -> **+80.3%**. Avoiding
bad days is worth MORE than capturing good ones. So concentration alone
does NOT prove "never sell" -- it proves "never be out at random." A rule
better than random at separating them could still add value; the retired
AVGO guard simply was not one (see the lookahead-bias entry above).

**Clustering is weaker than folk wisdom claims.** Only 20% of the top-10
and top-20 best days fall within 5 trading days of a comparable worst day
(36% at top-50). The extreme tails are somewhat separable, not hopelessly
interleaved.

**Recency warning.** The 20 best days by year: 2011 x2, 2013 x2, 2015 x2,
2020 x3, 2023 x2, 2024 x4, **2025 x5** -- 9 of the top 20 landed in
2024-2025 alone. The concentration is substantially an AI-melt-up
phenomenon, not a stable 17-year property. Treat forward extrapolation
with care.

**The 200d-SMA window, measured directly.** AVGO sits below its 200d SMA
on only **14.7%** of days. That window contains **20%** of the best days
but **36-50%** of the worst days -- roughly a 2:1 ratio in the rule's
favour on tail days alone. **This does NOT rehabilitate the retired
guard:** tail-day counts ignore the ordinary positive drift forfeited
across all other out-of-market days, the ~104 episodes' transaction costs,
and the SMA's lag -- all of which the realistic-execution backtest already
showed to be decisive (next-day fill: CAGR 19.1% vs 32.5% unguarded).
Recorded so the two findings are not mistaken for a contradiction.

**Implication for the live portfolio: supports the CURRENT configuration.**
Guard retired, static weights, AVGO held continuously. With half the
growth in 30 days and no validated way to know which ones, continuous
exposure is the correct posture for this holding -- and that is already
what the portfolio does. **No change recommended, nothing wired.** Script,
tests and workflow deleted after logging, per repo convention.

**Ops note:** `git push` credentials failed mid-session ("could not read
Username for https://github.com") while `git fetch` kept working. Worked
around it with the GitHub MCP API (`push_files`), which writes commits
directly. Local was then `git reset --hard origin/master` to resync after
verifying the content diff was comment-formatting only. Worth remembering
as the fallback if push auth drops again.

---

## De-risking on VIX / credit-spread spikes -- tested 2026-08-31

**Question (user):** "Should I be reducing my positions if e.g. VIX and
credit spreads spike, if so can we operationalize it?"

**Answer: the credit signal is real but the evidence is two crashes. Do
NOT wire it as an automated rule. An alert is defensible; automation is
not.**

**Why this was worth testing at all.** VIX is implied vol and BAA10Y is a
credit-market price -- neither is a function of the Core's own price
history, so this is a different signal class from the two overlays already
retired here (the AVGO 200d guard, a price-trend rule killed by lookahead
bias; vol-targeting, a realized-vol rule that lost 0 of 30 cells).

**Credit series is BAA10Y, not HY OAS.** `BAMLH0A0HYM2` is licence-
restricted to the trailing 3 years via the FRED API and `INTEGRITY.md:145`
already bars it as a conditioning variable. It cannot be backtested.

**Method.** `run_derisk_signal_test.py`, 348-cell grid: 4 modes (credit /
VIX / OR / AND) x credit thresholds {25,50,75,100}bp of 20d widening x VIX
rules {p80,p90,p95 point-in-time, >20,>25,>30} x reduction {25,50,100}% x
cash yield {0,2}%. Benchmark: static Gold25/AVGO40/LLY35, 10bps costs,
+-5pp drift rebalance. Signal from close(i) sets weights held close(i) ->
close(i+1); BAA10Y carries an extra publication-lag day; VIX percentiles
are expanding, never full-sample. 16 tests pin the timing invariants.
Runs: Actions 33438179581 and 33438579479.

**Found and fixed a real bug in the first cut of the script**: turnover
decided at close(i) was charged against day i's NAV while the weights
applied to day i+1 -- letting a signal move the NAV on its own signal day.
Smaller cousin of what killed the guard. Two tests now fail if it returns.

**Pre-committed kill criteria (written before any output was seen):** beat
static on Calmar in a majority of ACTIVE cells (>=5 episodes and >=1% of
days on -- inert cells excluded, "never traded" is not evidence), full
sample AND post-2020.

**Result: PASS.** 199/264 active cells (75%) full sample, 156/264 (59%)
post-2020.

**But the structure of the result is the classic overfit signature, and
that matters more than the verdict.** Static: CAGR 22.28%, MaxDD -32.74%,
Calmar 0.681.

| credit | reduce | episodes | CAGR | MaxDD | Calmar | 2010-19 | 2020+ |
|--------|--------|----------|------|-------|--------|---------|-------|
| >=25bp | 100%   | **39**   | 18.4%| -22.7%| 0.813  | **1.150** | **1.488** |
| >=50bp | 100%   | 10       | 22.0%| -22.6%| 0.977  | 1.643   | 1.973 |
| >=75bp | 100%   | **2**    | 22.9%| -21.8%| **1.050** | 1.679 | 2.010 |
| static | --     | --       | 22.28%| -32.74%| 0.681 | 1.679   | 1.773 |

Calmar rises monotonically as the sample collapses: 39 episodes -> 0.813,
10 -> 0.977, 2 -> 1.050. Performance improves in direct proportion to how
little evidence supports it. The >=25bp threshold -- the only one with a
real sample -- is the one that actively DAMAGES 2010-2019 and post-2020.

**The firing dates are the sample, and they are tiny.** >=75bp and >=100bp
fire exactly twice in 22 years: Oct 2008 and Mar 2020. >=50bp fires 10
times, but 6 are 2007-2009, which is pre-AVGO-IPO -- that leg of the
portfolio is Gold/LLY only, so it is not a test of the real portfolio. In
the AVGO era >=50bp fires four times: 2010-05 (6d), 2011-08 (**1d**),
2011-09 (**1d**), 2020-03 (24d). Two real events and two one-day blips.

**VIX contributes nothing and costs money.** Credit-only: 100% of cells
beat static, +0.128 median Calmar, **0.00% CAGR cost** (out of the market
~1.2% of days). VIX-only: 67% win rate, +0.029 Calmar, **-3.3%/yr**, out
13.1% of days. In the top-10 table `CREDIT >=50bp` alone is numerically
identical to `AND >=50bp + VIX>20` -- same Calmar, same 10 episodes. The
OR mode is dominated by the VIX leg and is the worst of the four.

**It is a crash rule, not a bear-market rule.** 2022: 0% of days on, zero
effect. GFC 2008 +8.8% vs static, COVID 2020 +12.2%.

**Lookahead twin: median Calmar leak +0.591, 52/58 cells.** Large, as
expected -- same-day VIX/credit is loaded with contemporaneous
information. Confirms the shift is doing real work and the honest numbers
are the honest numbers.

**Decision: alert, not automation.** `BAA10Y 20d widening >= 50bp` is the
one defensible cell -- costs 0.3%/yr, cuts MaxDD ~10pp, and is neutral
through 2010-2019 (1.643 vs 1.679) rather than damaging it. Recommended as
a display/alert line in `fi_tracker.py` so the condition surfaces and the
decision stays manual. **Hard-wiring an automatic 100%-to-cash trigger off
2-4 AVGO-era observations is exactly the mistake that produced the 200d
guard and the vol-targeter.** Passing a pre-committed kill test earns a
signal the right to be looked at; it does not earn it the right to trade
the portfolio unattended.

**Nothing wired. No change to live config.** Reading at 2026-08-28:
BAA10Y 20d widening **-4.0bp (tightening)**, VIX 14.4, p95 threshold 33.6.
Nowhere near firing.

**Open, not done:** the alert line in `fi_tracker.py` is recommended but
NOT built -- user has not decided. Script, tests and workflow deleted after
logging, per repo convention; recoverable from commits c636b78 / bb74e70.

---

## Drawdown control: allocation, not timing -- tested 2026-08-31

**Question (user):** "Figure out a confident strategy to avoid drawdowns."

**Answer: the live weights are already right. Do not change them. The only
open lever is the bucket split, and whether to move it is a judgment call
about 2008, not a data question.**

**Timing is closed -- 4 attempts, 0 survivors.** AVGO 200d guard (lookahead
bias), vol-targeting (0 of 30 cells), VIX/credit (passed its criteria but
on two crashes). Allocation needs no forecast and cannot be overfit to a
handful of crash dates, which is why this pass looked there instead.

**Method.** `run_drawdown_control.py`: 231 core weight combos x 9 bucket
splits x 2 Home Base models (SHY real data, flat 2% cash) = 4,158
portfolios. Same conventions as `run_base_optimizer.py` so numbers are
comparable to the committed grid. Two-level rebalancing (Core internally,
then the bucket split against it), matching the live portfolio. 12 tests
on the blend accounting. Runs: Actions 33440203087, 33440402387.

### The robust structural findings

**Core reweighting alone CANNOT reach the -25% tolerance: 0 of 231 combos.
Shallowest achievable by any weight mix is -28.42% (Gold70/AVGO15/LLY15).**
All three assets fall together in 2008 and 2020. The bucket split is the
only lever that reaches -25% -- confirmed, not assumed.

**Cost of drawdown control (full sample, Home Base = SHY):**

| ceiling | best config | core% | CAGR | MaxDD |
|---------|-------------|-------|------|-------|
| -18% | Gold40/AVGO50/LLY10 | 60% | 15.39% | -17.80% |
| -20% | Gold25/AVGO55/LLY20 | 65% | 17.13% | -19.42% |
| -22% | Gold30/AVGO50/LLY20 | 75% | 18.72% | -21.83% |
| -25% | Gold35/AVGO55/LLY10 | 80% | 20.62% | -24.32% |
| -28% | Gold35/AVGO50/LLY15 | 95% | 23.69% | -27.85% |
| none | Gold5/AVGO95/LLY0   | 100% | 33.52% | -48.15% |

Going -28% -> -25% costs ~3pp CAGR; -25% -> -20% costs another 3.5pp.
Every row falls short of the 20.48M nominal FI target (proj. 10.4M-14.4M),
so de-risking below -25% is expensive against an already-short projection.

### MY ERROR, and the correction -- this is the important part

**I first ranked the weight grid on the FULL SAMPLE and reported that the
live mix was dominated on both axes -- that LLY was the drawdown driver and
should be cut, and that the 2026-08-16 change (AVGO 55->40, LLY 20->35) had
cost 2.7pp CAGR and 2.9pp of drawdown. That was wrong.**

`MEMORY.md`'s `[[project-reactor-core-mix]]` method is explicit: base-mix
selection ranks on the WORST sub-period, never full-sample. Re-ranked
properly across five windows (one excluding the 2023-2026 AI melt-up):

| mix | worst-sub-period MaxDD | worst-sub-period Calmar |
|-----|------------------------|-------------------------|
| **LIVE Gold25/AVGO40/LLY35** | **-23.41%** | **1.034** |
| PREV Gold25/AVGO55/LLY20 | -29.82% | 0.867 |

**The live weights WIN, by 6.4pp of worst-case drawdown. The 2026-08-16
change was a good decision and must not be reversed.**

**The LLY conclusion inverts completely.** Best achievable worst-sub-period
MaxDD by LLY weight: 0% -> -22.7%, 10% -> -18.8%, 20% -> -17.2%,
35% -> -15.2%, 50% -> -14.7% (best), 75% -> -19.0%, 100% -> -34.5%.
**LLY is PROTECTIVE up to ~50%, not destructive** -- it diversifies AVGO.
LLY at 0-10% is the worst zone. The full-sample picture said the opposite
only because full-sample MaxDD is dominated by LLY's 2004-2009 stretch,
when AVGO did not yet exist. Textbook "winner that only won once" -- and I
produced it one hour after criticising exactly that failure mode in the
VIX/credit test. Gold 25-35% is the sweet spot on the same ranking; live
sits at 25%, which is fine.

### The one open decision

The -27.90% full-sample figure that breaches tolerance includes a 2008 in
which the portfolio is Gold/LLY only (pre-AVGO-IPO). On the post-AVGO
record the live mix's worst sub-period is **-23.41% at 100% Core** --
already inside -25% before any dilution. So:
- sizing for a 2008-style repeat -> Reactor Core 75-80%
- sizing on the AVGO-era record -> 85% already complies, no change

**That is a risk-appetite judgment, not something the data settles.
Nothing changed, nothing wired.** Also note the backtest cannot see
single-name blowup risk (fraud, patent cliff, obsolescence) -- the
operator's AVGO concentration worry is about a risk these numbers
structurally cannot measure, and should not be overridden by them.

Script, tests and workflow deleted after logging, per repo convention;
recoverable from commits 5c8e252 / 35b58a7.

---

## BTC inside the Reactor Core: it ADDS on the repo's own standard, but on one cycle (2026-09-01)

**Question (user):** "What would happen if I held x% BTC in RC as well?"

**Result: BTC adds at every Core fraction and both arms, ranked on the
WORST sub-period. Direction supported, magnitude not. Recommended ~5% of
Core; the 15-20% the backtest prefers should NOT be acted on.**

**Setup -- the real instrument, not spot BTC.** Virtune Sustainable ETP
SE0020845709, 1.49%/yr (only Virtune BTC product on Avanza -- a constraint,
not a choice), 0.16% measured spread, weekday-only execution,
`BTC_SEK = BTC_USD x USDSEK`, signal read off BTC-USD per the
vessel-vs-signal thesis. Two arms: plain HOLD, and the 150d SMA rule
adopted 2026-08-24. Core weights held at the live Gold25/AVGO40/LLY35
(settled, and correct on worst-sub-period). Everything converted to SEK,
so these numbers are NOT comparable to the 2004-2026 USD grid -- the 0% BTC
row is the baseline. Ranked on worst sub-period FROM THE START, with BTC's
2021-2022 -77% bear isolated as its own window. 12 tests, including the
one MEMORY.md flags as decisive: an always-held trend arm must equal
buy-and-hold exactly, proving the fee is on the same basis for both arms.
Run: Actions 33473529794.

**Core 85% (live split), SEK, 2014-09..2026-08:**

| BTC% | HOLD CAGR | HOLD worstDD | 150d CAGR | 150d worstDD | 150d worstCal |
|------|-----------|--------------|-----------|--------------|---------------|
| 0%   | 30.65%    | -25.16% BREACH | 30.65%  | -25.16% BREACH | 1.110 |
| 5%   | 33.46%    | -24.70%      | 33.47%    | -24.38%      | 1.268 |
| 10%  | 35.52%    | -24.47%      | 35.90%    | -23.85%      | 1.372 |
| 15%  | 37.83%    | -23.79%      | 37.23%    | **-22.15%**  | 1.335 |
| 20%  | 39.41%    | -24.42%      | 39.56%    | -22.18%      | **1.418** |

Worst-sub-period best weight: Core 85% -> HOLD 10%, 150d 20%. Core 80% ->
HOLD 15%, 150d 15%. **Every case says ADDS.**

**BTC made drawdown SHALLOWER, not deeper -- the opposite of the
pre-run prediction.** Coherent mechanism (BTC crashes unsynced from the
Core's, the 150d rule exits during BTC's own crashes, rebalancing an
uncorrelated high-vol asset harvests volatility), but see the caveats.
**5% BTC is also where Core 85% flips from breaching the -25% tolerance to
complying** -- BTC does what cutting the Core to 80% would have done.

**Why the magnitude is not trustworthy:**
1. **ONE cycle.** 11.5yr, one BTC bull and one bear. The core-mix result
   had 22yr and five regimes. Weakest evidence base in this file's recent
   work -- comparable to the VIX/credit result, not to the weights answer.
2. **The drawdown improvement is the fragile claim.** It requires BTC not
   crashing WITH equities. March 2020 it did exactly that (-50% in a day
   alongside the crash). This window happens to have BTC's 2021-22 bear
   LEAD the equity bear; reorder those events and the finding flips.
3. **CAGR levels are not forward-looking.** The 30.65% baseline carries no
   2008, AVGO's AI melt-up, and SEK depreciation (USDSEK ~6.5 -> ~9.5).
   BTC itself compounded ~66%/yr. **The FI@50 projections in the run output
   (35M-76M against a 20.5M target) are arithmetic on a backtested CAGR and
   must NOT be planned on.**
4. **Survivorship.** BTC is the crypto that won; picking it in 2014 was not
   obvious ex ante and the backtest cannot see what went to zero.

**Mild corroboration:** the 150d arm beats HOLD on drawdown in nearly every
row, consistent with the rule already adopted on independent evidence.

**Nothing wired, no config change, position still untracked.** Current
holding ~20,225 kr = ~1.8% of TPV, ~2.1% of Core. Moving to 5% of Core at
the live split would be ~48,900 kr, i.e. ~+28,700 kr. **User asked what
would happen, not to act -- this is a report, not an executed decision.**

Script, tests and workflow deleted after logging, per repo convention;
recoverable from commit 185aa94.
