# Asset Universe

Personal quantitative-finance infrastructure for a Swedish investor's FI@50 plan:
a regime-conditional data pipeline, a live portfolio strategy with mechanical
guard/tactical rules, and an opportunistic tactical entry screen — all driven
by a daily GitHub Actions job.

For day-to-day continuation (current strategy state, decisions, gotchas,
priority backlog), see [`MEMORY.md`](MEMORY.md) — that file is the shared
handoff doc, kept current every session. This README is orientation only.

## Quick start

```bash
pip install -e .
python -m asset_universe.update      # fetch/refresh the parquet price store
python fi_tracker.py                 # full daily dashboard
```

`python -m pytest tests -q` runs the test suite.

## What runs daily (`.github/workflows/sync.yml`)

Weekdays ~08:00 and ~22:30 CEST, unattended:

1. Sync share counts from the Google Sheet → `config/portfolio.toml`
2. Refresh all prices/macro series → `data/` (parquet, gitignored)
3. Refresh the regime-conditional universe ranking → `universe_screen_results.csv`
4. `fi_tracker.py` → `status.md` (portfolio snapshot, FI@50 pace, macro regime,
   AVGO 200d guard, Silver GSR tactical, AVGO earnings checkpoint, Opportunistic
   Sleeve)
5. Regime-flip alert, portfolio optimizer
6. Commit + push, then a health check that fails the run (and triggers a
   GitHub notification) if `status.md` is stale or contains a failure signature

## Live strategy

3-asset scarcity base — Gold 25% / AVGO 55% / LLY 20% — with two always-on
tactical rules and one opportunistic sleeve, all computed live in
`fi_tracker.py`:

- **AVGO 200d guard**: rotates AVGO's weight into Gold+LLY if AVGO closes
  below its 200-day SMA. Parameter-sensitivity tested (`run_parameter_sensitivity.py`)
  — robust, not curve-fit.
- **Silver GSR tactical**: adds silver (funded from AVGO) when the gold/silver
  ratio spikes and has fallen from its 60-day peak; exits at a cycle-complete
  threshold.
- **AVGO earnings checkpoint**: tracks the forward/trailing EPS ratio against
  a peer baseline — a forward-looking check that price alone won't catch.
- **Opportunistic sleeve** (`run_entry_screen.py`): a separate, capped
  tactical layer for war-chest capital only (1 open position at a time).
  Screens the current macro regime's top-ranked assets through momentum,
  earnings-avoidance, and diversity gates, sizes the recommendation's exit
  triggers to its own runway, and vets the pick against live tripwires
  (relative strength, sector-cluster health, trend slope) before it's ever
  shown as a recommendation — not just after opening it.

## Key scripts

| Script | Purpose |
|---|---|
| `fi_tracker.py` | Daily dashboard — the main entry point |
| `run_entry_screen.py` | Opportunistic sleeve — screen, `--open`/`--close` a position |
| `check_sync_health.py` | Fails the daily job if `status.md` is stale or broken |
| `run_universe_screen.py` | Regime-conditional ranking of the full asset universe |
| `run_combined_system.py` | Backtest of the base + guard + silver system |
| `run_parameter_sensitivity.py` | Robustness grid for the guard/silver thresholds |
| `sync_sheet.py` | Pulls share counts from the Google Sheet into `portfolio.toml` |
| `src/asset_universe/analysis/engine.py` | Core conditional-return engine (`query()`, `current_regime()`, `screen_tactical()`) |

Everything else at the repo root is a one-off research/backtest script from
earlier iterations of the strategy — see `MEMORY.md` for which ones matter
and why.

## Configuration

- `config/portfolio.toml` — live positions and manual cash buckets (war
  chest, home base). Synced from the Google Sheet; manual buckets need
  `value_sek` updated after each trade.
- `config/sleeve_state.toml` — opportunistic sleeve's open/closed position
  state. Managed via `run_entry_screen.py --open`/`--close`, not edited by
  hand.
- `config/fred_series.csv` — FRED macro series fetched daily.
- `.env` / `fred_api.env` — local secrets (gitignored). See `.env.example`
  if present, or `src/asset_universe/config.py` for what's expected.

## No brokerage integration

Nothing in this repo places trades. `run_entry_screen.py --open`/`--close`
record a trade that was executed manually elsewhere (Avanza); every
recommendation is decision-support, not automation of the trade itself.
