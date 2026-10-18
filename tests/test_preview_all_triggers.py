from unittest.mock import patch

import preview_all_triggers as pat


def test_every_scenario_fires_an_actionable_message():
    # Locks in the manual dry-run done before wiring this into a real
    # Telegram-sending workflow -- every known trigger type must produce an
    # actionable message from the real production code, none silently falling
    # through as a no-op. Asserted against len(SCENARIOS) rather than a
    # literal: the literal was left at 8 when PR #122 added the crypto and HY
    # scenarios, so the count is now derived and adding a scenario cannot
    # leave this stale again.
    with patch.object(pat, "send_telegram") as mock_send, patch.object(pat.time, "sleep"):
        code = pat.main()

    assert code == 0
    assert mock_send.call_count == len(pat.SCENARIOS)
    assert len(pat.SCENARIOS) >= 11, "scenarios should not silently disappear"


def test_reports_failure_if_a_scenario_stops_firing():
    # If a future change to the fixture/regex breaks one scenario's
    # trigger condition, this must be caught (non-zero exit), not silently
    # skipped.
    broken_scenarios = pat.SCENARIOS[:-1] + [("broken", pat.BASE)]  # last one: no change at all
    with patch.object(pat, "SCENARIOS", broken_scenarios), \
         patch.object(pat, "send_telegram") as mock_send, \
         patch.object(pat.time, "sleep"):
        code = pat.main()

    assert code == 1
    assert mock_send.call_count == len(broken_scenarios) - 1
