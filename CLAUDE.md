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
