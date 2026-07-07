from unittest.mock import patch

import pytest

import record_earnings_verdict as rev


def test_cleared_flag_records_cleared_verdict():
    with patch.object(rev, "save_verdict") as mock_save:
        code = rev.main(["AVGO", "--cleared", "on pace"])

    assert code == 0
    mock_save.assert_called_once_with("AVGO", "CLEARED", "on pace")


def test_not_cleared_flag_records_not_cleared_verdict():
    with patch.object(rev, "save_verdict") as mock_save:
        code = rev.main(["avgo", "--not-cleared", "missed pace"])

    assert code == 0
    mock_save.assert_called_once_with("AVGO", "NOT_CLEARED", "missed pace")  # ticker uppercased


def test_requires_exactly_one_of_cleared_or_not_cleared():
    with patch.object(rev, "save_verdict"), pytest.raises(SystemExit):
        rev.main(["AVGO"])
