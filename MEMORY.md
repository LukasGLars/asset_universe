# MEMORY

Shared handoff doc for whoever (human or agent) picks up work on this repo next.
Read this before starting; update it when you finish a meaningful chunk of work.

## 2026-07-01 — Sync health check (PR #3, branch `chore/sync-health-check`)

**What**: Added `check_sync_health.py` + `tests/test_check_sync_health.py`, wired
as a new step in `.github/workflows/sync.yml` *after* "Commit changes". It checks
`status.md` for (1) freshness against the actual cron schedule (handles the
Fri-evening → Mon-morning gap by walking the weekday schedule backwards rather
than using a flat threshold) and (2) failure signatures (`[unavailable`,
`Traceback`, `Error`) / missing key sections (Silver GSR Tactical, AVGO 200d
Guard, AVGO Earnings Checkpoint). Exits non-zero to fail the Actions run, which
triggers GitHub's default failure-run email.

**Why**: Previously a silent sync failure (network blip, yfinance API change,
runner hiccup) looked identical to "ran fine, said hold" — nothing distinguished
them. The strategy guards depend entirely on this job running and writing a
healthy `status.md` every weekday.

**Decision — step ordering**: placed *after* commit-and-push so a legitimate but
degraded `status.md` still gets committed/recorded (we want history of what
actually happened), but the job still ends in a failed run to trigger
notification. See PR #3 body for full reasoning.

**Gotcha found, not fixed (separate scope)**: `run_optimizer.py` imports
`scipy.optimize` but `scipy` is missing from `pyproject.toml` dependencies — the
"Portfolio optimizer" step has been failing and appending a traceback to
`status.md` (confirmed in the live `status.md` at the time of this PR). Also,
that same live `status.md` predates the AVGO Earnings Checkpoint feature
(`fi_tracker.py` merged in PR #1 / commit `b1e9877`), so the section was missing
too — the health check correctly flagged both as a true negative during
self-testing. **Follow-up needed**: add `scipy` to `pyproject.toml` dependencies,
then let the next scheduled sync run regenerate a clean `status.md`.

**Gotcha — in-job freshness check has limited bite**: when this step runs in the
same job right after `tee` just wrote `status.md`, the file's OS mtime is
"now" regardless of whether upstream data is actually good — so within this job,
the *content* scan is doing the real work of catching silent partial failures.
The freshness check's payoff is mainly for out-of-band runs (manual,
`workflow_dispatch`, or a future separate watchdog workflow checking a repo that
hasn't been touched in days).

## Next todo
- Follow up: add `scipy` to `pyproject.toml` dependencies so `run_optimizer.py`
  stops failing (see gotcha above). Not done in PR #3 — out of scope for that
  change.
- Review/merge PR #3 (not auto-merged per workflow rules — human decides).
