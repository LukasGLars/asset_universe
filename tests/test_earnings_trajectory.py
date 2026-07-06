from earnings_trajectory import beat_streak, guidance_direction


def test_beat_streak_all_beats():
    pairs = [(1.69, 1.66), (1.95, 1.87), (2.05, 2.02), (2.44, 2.40)]  # oldest first
    assert beat_streak(pairs) == 4


def test_beat_streak_broken_by_most_recent_miss():
    pairs = [(1.69, 1.66), (1.95, 1.87), (2.05, 2.02), (2.00, 2.40)]  # most recent is a miss
    assert beat_streak(pairs) == 0


def test_beat_streak_counts_back_from_most_recent_only():
    # Miss in the middle, beats after it -- streak only counts the recent run.
    pairs = [(1.69, 1.66), (1.80, 1.95), (2.05, 2.02), (2.44, 2.40)]
    assert beat_streak(pairs) == 2


def test_beat_streak_empty_is_zero():
    assert beat_streak([]) == 0


def test_beat_streak_exact_tie_is_not_a_beat():
    pairs = [(2.00, 2.00)]
    assert beat_streak(pairs) == 0


def test_guidance_direction_up():
    assert guidance_direction(19.40, 17.81) == "revising up"


def test_guidance_direction_down():
    assert guidance_direction(15.00, 19.40) == "revising down"


def test_guidance_direction_flat_within_tolerance():
    assert guidance_direction(19.40, 19.30) == "flat"


def test_guidance_direction_zero_baseline_is_unknown():
    assert guidance_direction(19.40, 0.0) == "unknown"
