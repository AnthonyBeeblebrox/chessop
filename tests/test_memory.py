import pytest

from chessop.memory import DAY, HOUR, MINUTE, Params, Record, half_life, judge_pass, need, recall

P = Params()
NOW = 1_800_000_000.0


def test_defaults_are_the_spec_parameters() -> None:
    assert (P.h0, P.h_min, P.h_max) == (DAY, 15 * MINUTE, 270 * DAY)
    assert (P.sure, P.floor) == (0.9, 0.1)


def test_a_fresh_record_has_the_initial_half_life() -> None:
    assert half_life(Record(), P) == DAY


def test_each_counted_pass_doubles_and_each_miss_halves_the_half_life() -> None:
    assert half_life(Record(passes=3), P) == 8 * DAY
    assert half_life(Record(passes=3, misses=1), P) == 4 * DAY
    assert half_life(Record(misses=2), P) == 6 * HOUR


def test_the_half_life_is_clipped_to_its_bounds() -> None:
    assert half_life(Record(misses=10), P) == 15 * MINUTE
    assert half_life(Record(passes=20), P) == 270 * DAY


def test_recall_is_zero_for_a_position_never_passed() -> None:
    assert recall(Record(), NOW, P) == 0.0
    assert recall(Record(misses=3, relearn=True), NOW, P) == 0.0


def test_recall_halves_every_half_life_since_the_last_pass() -> None:
    record = Record(passes=1, last_pass=NOW - 4 * DAY)  # h = 2 days
    assert recall(record, NOW, P) == pytest.approx(0.25)
    assert recall(record, NOW - 4 * DAY, P) == 1.0


def test_need_is_one_minus_recall_never_below_the_floor() -> None:
    assert need(Record(), NOW, P) == 1.0
    assert need(Record(passes=1, last_pass=NOW - 4 * DAY), NOW, P) == pytest.approx(0.75)
    assert need(Record(passes=1, last_pass=NOW), NOW, P) == 0.1


def test_a_pass_on_a_position_not_yet_sure_is_counted() -> None:
    record = Record(passes=1, misses=1, last_pass=NOW - DAY)  # R = 0.5
    assert judge_pass(record, NOW, P) == "counted"
    assert Record().apply("counted", NOW) == Record(passes=1, last_pass=NOW)
    assert record.apply("counted", NOW) == Record(passes=2, misses=1, last_pass=NOW)


def test_a_pass_when_the_model_is_already_sure_sets_the_clock_only() -> None:
    record = Record(passes=2, last_pass=NOW - HOUR)  # h = 4 days, R ~ 0.99
    assert judge_pass(record, NOW, P) == "sure"
    assert record.apply("sure", NOW) == Record(passes=2, last_pass=NOW)


def test_the_first_pass_after_a_miss_is_a_relearning_pass_not_counted() -> None:
    record = Record(passes=2, misses=1, last_pass=NOW - DAY, relearn=True)
    assert judge_pass(record, NOW, P) == "relearning"
    assert record.apply("relearning", NOW) == Record(passes=2, misses=1, last_pass=NOW)


def test_a_relearning_pass_wins_even_when_the_model_is_sure() -> None:
    record = Record(passes=5, misses=1, last_pass=NOW - MINUTE, relearn=True)
    assert judge_pass(record, NOW, P) == "relearning"


def test_a_miss_halves_the_half_life_sets_the_mark_and_leaves_the_clock() -> None:
    record = Record(passes=2, last_pass=NOW - DAY)
    missed = record.apply("miss", NOW)
    assert missed == Record(passes=2, misses=1, last_pass=NOW - DAY, relearn=True)
    assert half_life(missed, P) == half_life(record, P) / 2
