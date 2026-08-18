# asset_universe — repo notes

Read `MEMORY.md` first. It carries the current state, decisions and gotchas.

## Git workflow (overrides the global branch+PR rule)

Solo repo with standing merge authorization — PRs get merged as soon as
they're clean, no separate "merge it" needed. The branch+PR step mostly adds
a round-trip here, not real review.

- Small/safe changes (bug fixes, docs, config, data/output files) — push
  straight to `master`.
- Riskier changes (anything touching live trading/alerting logic, credentials,
  or that mutates portfolio state destructively) — still branch + PR, so
  there's a reviewable diff before it's live.

## This repository is PUBLIC

`github.com/LukasGLars/asset_universe` is public. Position sizes, TPV and
contribution rates are already in here by long-standing choice, but personal
details are not to be added:

- **No income, salary, or expense figures.**
- **No date of birth** — including by inference. "Age 50 on 2038-10-10"
  gives it away; the bare horizon date does not.
- Keep those in the operator's personal memory instead, and record only the
  derived result here (thresholds, weights, required returns).

This was violated on 2026-08-18 and redacted in `355d802`. Redaction does
not purge git history — check before committing, not after.

## Two rules earned the hard way

- **Alerts must read their numbers from the source, never restate them in
  prose.** `fi_tracker.py`'s silver action strings drifted 15pp from
  `run_combined_system.WEIGHTS` and would have been sent verbatim to
  Telegram (PR #100). If a message quotes a weight, it must compute it.
- **Sub-period any full-sample statistic before believing it.** SAAB
  screened at 0.11 beta to the AI-semi basket and looked like the first real
  hedge this project had found; by sub-period it was 0.23 / 0.27 / -0.02,
  entirely post-Ukraine (PR #97). One regime can carry a whole number.
