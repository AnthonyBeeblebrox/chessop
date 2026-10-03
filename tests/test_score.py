from collections.abc import Callable

import pytest

from chessop.memory import DAY, Params, Record
from chessop.repertoire import START, Repertoire, Settings
from chessop.score import Scores, scores
from graphs import epd_after, graph_of

P = Params()
NOW = 1_800_000_000.0

# White to move at the start (10,000) and after 1.e4 e5 (3,000); Black after 1.e4 (6,000) and
# 1.d4 (2,000). 1.e4 e5 Nf3 and 1.d4 d5 are leaves, never drilled whoever is to move.
GRAPH = graph_of(
    {"e4": 6000, "d4": 2000, "e4 e5": 3000, "e4 e5 Nf3": 2500, "d4 d5": 1500},
    {"e4 e5 Nf3": "King's Knight Opening", "d4 d5": "Queen's Pawn Game"},
)
REP = Repertoire(GRAPH, Settings())
E4, D4, E4_E5 = epd_after("e4"), epd_after("d4"), epd_after("e4", "e5")


def lookup(records: dict[str, Record]) -> Callable[[str], Record]:
    return lambda epd: records.get(epd, Record())


def test_the_learner_positions_are_the_kept_positions_that_are_not_leaves() -> None:
    assert REP.learner_positions == {START, E4, D4, E4_E5}


def test_nothing_passed_scores_zero() -> None:
    assert scores(REP, lookup({}), NOW, P) == Scores(0.0, 0.0, 0.0)


def test_the_score_is_the_count_weighted_mean_recall_over_both_colours() -> None:
    records = {
        START: Record(passes=1, last_pass=NOW),  # R = 1
        E4: Record(passes=1, last_pass=NOW - 2 * DAY),  # h = 2 days: R = 0.5
        E4_E5: Record(passes=0, misses=1, last_pass=NOW - DAY / 2, relearn=True),  # R = 0.5
        # D4 never passed: R = 0, and a record on a leaf is never counted.
        epd_after("e4", "e5", "Nf3"): Record(passes=9, last_pass=NOW),
    }
    got = scores(REP, lookup(records), NOW, P)
    assert got.score == pytest.approx((10_000 * 1 + 6000 * 0.5 + 3000 * 0.5 + 2000 * 0) / 21_000)
    assert got.white == pytest.approx((10_000 * 1 + 3000 * 0.5) / 13_000)
    assert got.black == pytest.approx((6000 * 0.5 + 2000 * 0) / 8000)


def test_the_score_is_raw_recall_not_capped_by_the_need_floor() -> None:
    passed = {epd: Record(passes=3, last_pass=NOW) for epd in REP.learner_positions}
    assert scores(REP, lookup(passed), NOW, P) == Scores(1.0, 1.0, 1.0)


def test_the_score_decays_with_time_like_the_estimates_under_it() -> None:
    records = {epd: Record(passes=1, last_pass=NOW) for epd in REP.learner_positions}  # h = 2 days
    assert scores(REP, lookup(records), NOW + 2 * DAY, P).score == pytest.approx(0.5)
    assert scores(REP, lookup(records), NOW + 4 * DAY, P).score == pytest.approx(0.25)


def test_the_score_covers_the_scoped_repertoire_only() -> None:
    scoped = Repertoire(GRAPH, Settings(opted_out=frozenset({"Queen's Pawn Game"})))
    records = {START: Record(passes=1, last_pass=NOW)}
    got = scores(scoped, lookup(records), NOW, P)
    assert got.score == pytest.approx(10_000 / 19_000)
    assert got.black == 0.0


def test_a_colour_with_no_learner_position_scores_zero() -> None:
    only_white = Repertoire(graph_of({"e4": 6000}, {"e4": "King's Pawn Game"}), Settings())
    records = {START: Record(passes=1, last_pass=NOW)}
    assert scores(only_white, lookup(records), NOW, P) == Scores(1.0, 1.0, 0.0)
