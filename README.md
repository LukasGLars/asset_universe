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
6. Commit + push
7. **Signal-change notification**: compares today's guard/LLY-stress/
   joint-stress/silver/sleeve/regime state against yesterday's committed
   `status.md` — silent if nothing actionable changed, one Telegram message
   if it did (`TELEGRAM_BOT_TOKEN` secret, `TELEGRAM_CHAT_ID` variable).
   Telegram carries urgent/time-sensitive items per the 2026-07-03
   ops-scope decision; the (not yet built) FI@50 pace digest and quarterly
   thesis re-check go via email instead, since they're low-urgency. See
   `check_signal_changes.py` / `notify_signal_changes.py`.
8. Health check that fails the run (and triggers a GitHub notification) if
   `status.md` is stale or contains a failure signature

## Live strategy

3-asset scarcity base — Gold 25% / AVGO 55% / LLY 20% — with two always-on
tactical rules and one opportunistic sleeve, all computed live in
`fi_tracker.py`:

- **AVGO 200d guard**: rotates AVGO's weight into Gold+LLY if AVGO closes
  below its 200-day SMA (or a fast-crash trigger fires first). Parameter-sensitivity
  tested (`run_parameter_sensitivity.py`) — robust, not curve-fit.
- **AVGO/LLY joint-stress escalation**: if LLY independently trips the same
  guard logic while AVGO's guard is also active, escalate to 100% Gold — LLY's
  diversification benefit is regime-dependent and breaks down exactly in
  macro/trade-driven selloffs. Validated (`run_joint_stress_validation.py`).
- **Silver GSR tactical**: adds silver (funded from AVGO) when the gold/silver
  ratio spikes and has fallen from its 60-day peak; exits at a cycle-complete
  threshold.
- **AVGO earnings checkpoint**: tracks the forward/trailing EPS ratio against
  a peer baseline — a forward-looking check that price alone won't catch.
- **Crypto trend sleeve** (`run_crypto_trend.py`): the live tactical layer as
  of 2026-09-04, replacing the opportunistic sleeve below. 5% of TPV in
  Virtune BTC + staked ETH ETPs. Per asset: weekday closes, 50/100/200d SMA,
  long above MA+2%, flat below MA-2%, else hold; target exposure = mean of the
  three. Validated against *exposure-matched* buy-and-hold — 3/3 eras, 12/13
  rule variants — net of the 1.49% ETP fee. 10% hard cap.
- **Opportunistic sleeve** (`run_entry_screen.py`) — **RETIRED 2026-09-04**;
  its four gates never beat random entry from the same universe (see
  MEMORY.md). Still printed to `status.md` for continuity, but the war chest is
  suspended so it cannot act. Was: a separate, capped
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
| `run_crypto_trend.py` | Crypto trend sleeve — daily target exposure for the BTC/ETH ETP legs |
| `check_sync_health.py` | Fails the daily job if `status.md` is stale or broken |
| `run_universe_screen.py` | Regime-conditional ranking of the full asset universe (US + Swedish + commodities + ETFs) |
| `run_clean_sheet_search.py` | Clean-sheet 3-asset search over the ROBUST universe, selected in-sample and judged out-of-sample |
| `run_ai_basket_beta.py` | Hedge screen — beta to the AI-semi basket during its own drawdowns |
| `run_contribution_split_test.py` | Whether holding contributions back to dip-buy beats pure DCA |
| `run_combined_system.py` | Backtest of the base + guard + silver system |
| `run_parameter_sensitivity.py` | Robustness grid for the guard/silver thresholds |
| `run_joint_stress_validation.py` | Validation for the AVGO/LLY joint-stress escalation rule (TXN analog + sensitivity grids) |
| `sync_sheet.py` | Pulls share counts from the Google Sheet into `portfolio.toml` |
| `src/asset_universe/analysis/engine.py` | Core conditional-return engine (`query()`, `current_regime()`, `screen_tactical()`) |

Everything else at the repo root is a one-off research/backtest script from
earlier iterations of the strategy — see `MEMORY.md` for which ones matter
and why.

## Configuration

- `config/portfolio.toml` — live positions and manual cash buckets (war
  chest, home base). Synced from the Google Sheet; manual buckets need
  `value_sek` updated after each trade.
- `config/universes/crypto.txt` — crypto trend sleeve universe (BTC/ETH).
  Sleeve capital per leg lives in `config/portfolio.toml`'s `[crypto_sleeve]`.
- `config/sleeve_state.toml` — opportunistic sleeve's open/closed position
  state. Managed via `run_entry_screen.py --open`/`--close`, not edited by
  hand.
- `config/universes/*.txt` — the asset universe, one file per category.
  `se_equities.txt` (Swedish large caps) was added 2026-08-18; adding a new
  file also requires an entry in `update.py`'s `CATEGORIES`.
- `config/fred_series.csv` — FRED macro series fetched daily.
- `.env` / `fred_api.env` — local secrets (gitignored). See `.env.example`
  if present, or `src/asset_universe/config.py` for what's expected.

## No brokerage integration

Nothing in this repo places trades. `run_entry_screen.py --open`/`--close`
record a trade that was executed manually elsewhere (Avanza); every
recommendation is decision-support, not automation of the trade itself.
