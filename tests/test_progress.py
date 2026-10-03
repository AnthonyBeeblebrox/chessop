import re
import time
from datetime import date

import pytest
from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.memory import DAY, Params, Record
from chessop.progress import FIRST_MOVES, Ledger, Line, Naming, Tally, tally
from chessop.repertoire import START, Repertoire, Settings
from chessop.score import Scores
from chessop.store import Outcome, RoundEnd, Store
from graphs import epd_after, graph_of

# 1.e4 c5 2.Nf3 d6 3.d4 is named at 1.e4 c5, 2...d6 and 3.d4 but not at 2.Nf3; 1.d4 d5 2.c4 at
# 1...d5 and 2.c4. 1.e4 is named too, yet sits in the first moves with the start and 1.d4.
SICILIAN = {
    "e4": 6000,
    "d4": 3100,
    "e4 c5": 4000,
    "e4 c5 Nf3": 3000,
    "e4 c5 Nf3 d6": 2000,
    "e4 c5 Nf3 d6 d4": 1500,
    "e4 c5 Nc3": 800,
    "e4 c5 Nc3 Nc6": 600,
    "d4 d5": 2000,
    "d4 d5 c4": 1500,
}
NAMES = {
    "e4": "King's Pawn Game",
    "e4 c5": "Sicilian Defense",
    "e4 c5 Nf3 d6": "Sicilian Defense: Modern Variations",
    "e4 c5 Nf3 d6 d4": "Sicilian Defense: Open",
    "e4 c5 Nc3 Nc6": "Sicilian Defense: Closed",
    "d4 d5": "Queen's Pawn Game",
    "d4 d5 c4": "Queen's Gambit",
}


def ledger() -> Ledger:
    return Ledger(Repertoire(graph_of(SICILIAN, NAMES), Settings()))


def test_a_name_is_inherited_from_the_nearest_named_position_along_the_canonical_order() -> None:
    names = ledger()
    assert names.naming(epd_after("e4", "c5", "Nf3")) == Naming(
        "Sicilian Defense", None, exact=False, family="Sicilian Defense"
    )
    assert names.naming(epd_after("e4", "c5", "Nf3", "d6")) == Naming(
        "Sicilian Defense: Modern Variations", None, exact=True, family="Sicilian Defense"
    )
    assert names.naming(epd_after("e4", "c5", "Nf3", "d6", "d4")).family == "Sicilian Defense"


def test_the_first_two_plies_are_the_first_moves_whatever_their_name() -> None:
    names = ledger()
    assert names.naming(START) == Naming(None, None, exact=False, family=FIRST_MOVES)
    assert names.naming(epd_after("e4")) == Naming(
        "King's Pawn Game", None, exact=True, family=FIRST_MOVES
    )


def test_a_transposed_position_inherits_along_its_canonical_order_only() -> None:
    # 1.d4 Nf6 2.c4 e6 is reached first (the canonical order), then by 1.c4 e6 2.d4 Nf6.
    graph = graph_of(
        {
            "d4": 5000,
            "c4": 2000,
            "d4 Nf6": 4000,
            "c4 e6": 1000,
            "d4 Nf6 c4": 3000,
            "c4 e6 d4": 500,
            "d4 Nf6 c4 e6": 2500,
            "c4 e6 d4 Nf6": 400,
        },
        {"d4 Nf6": "Indian Defense", "c4 e6": "English Opening: Agincourt Defense"},
    )
    names = Ledger(Repertoire(graph, Settings()))
    assert names.naming(epd_after("d4", "Nf6", "c4", "e6")).name == "Indian Defense"


def test_the_first_moves_come_first_then_openings_by_the_pooled_count_of_their_positions() -> None:
    openings = ledger().openings
    assert [o.name for o in openings] == [
        FIRST_MOVES,
        "Sicilian Defense",  # 4000 + 3000 + 800 + 2000 (below 2...d6 and 2...Nc6, leaves)
        "Queen's Pawn Game",  # 2000
        "Queen's Gambit",  # a leaf only: listed, nothing to drill
    ]
    sicilian = openings[1]
    assert {epd for epd, _, _ in sicilian.positions} == {
        epd_after("e4", "c5"),
        epd_after("e4", "c5", "Nf3"),
        epd_after("e4", "c5", "Nc3"),
        epd_after("e4", "c5", "Nf3", "d6"),
    }
    assert [line.name for line in sicilian.lines] == [
        "Sicilian Defense",
        "Sicilian Defense: Modern Variations",
        "Sicilian Defense: Closed",  # a leaf only, like the Open
        "Sicilian Defense: Open",
    ]


def strings(line: Line) -> list[str]:
    """A line's branches with the learner's moves starred."""
    return [" ".join(c.text + ("*" if c.epd else "") for c in b) for b in line.branches]


def test_a_line_unfolds_into_branches_where_each_learner_move_is_shown_once() -> None:
    first, sicilian, _, _ = ledger().openings
    # The start and 1.d4 are unnamed, 1.e4 the King's Pawn Game: two lines of the first moves.
    # Every branch runs on to a leaf along the most popular main moves.
    assert [strings(line) for line in first.lines] == [
        ["1.d4* d5* 2.c4"],
        ["1.e4 c5* 2.Nf3 d6 3.d4"],
    ]
    assert [strings(line) for line in sicilian.lines] == [
        # 1.e4 c5 is shown once, on its first branch; the moves of the next line are plain.
        ["1.e4 c5 2.Nf3* d6* 3.d4", "1.e4 c5 2.Nc3 Nc6*"],
        ["1.e4 c5 2.Nf3 d6 3.d4*"],
        ["1.e4 c5 2.Nc3 Nc6"],  # a leaf: nothing to recall
        ["1.e4 c5 2.Nf3 d6 3.d4"],
    ]


def test_every_learner_position_is_shown_once_across_the_ledger() -> None:
    names = ledger()
    shown = [
        chip.epd
        for opening in names.openings
        for line in opening.lines
        for branch in line.branches
        for chip in branch
        if chip.epd
    ]
    assert sorted(shown) == sorted(names.repertoire.learner_positions)


NOW = 1_800_000_000.0


def test_an_opening_scores_its_own_learner_positions_by_pooled_count() -> None:
    sicilian = ledger().openings[1]
    records = {
        epd_after("e4", "c5"): Record(passes=1, last_pass=NOW),  # White, 4000: R = 1
        epd_after("e4", "c5", "Nf3"): Record(passes=1, last_pass=NOW - 2 * DAY),  # Black, 3000: 0.5
        # White, 2000: missed, a relearning pass owed; h = half a day, so R = 0.5
        epd_after("e4", "c5", "Nf3", "d6"): Record(misses=1, last_pass=NOW - DAY / 2, relearn=True),
        # Black, 800: never passed
        epd_after("e4"): Record(passes=5, last_pass=NOW),  # the first moves', not the Sicilian's
    }
    got = tally(sicilian.positions, lambda epd: records.get(epd, Record()), NOW, Params())
    assert got.score == pytest.approx((4000 + 1500 + 1000) / 9800)
    assert got.white == pytest.approx((4000 + 1000) / 6000)
    assert got.black == pytest.approx(1500 / 3800)
    # The relearning position is learning, not known, whatever its estimate.
    assert (got.known, got.learning, got.never) == (1, 2, 1)


def test_an_opening_with_nothing_to_drill_has_no_score() -> None:
    gambit = ledger().openings[3]
    assert tally(gambit.positions, lambda epd: Record(), NOW, Params()) == Tally(
        None, None, None, 0, 0, 0
    )


def page(store: Store, opted_out: frozenset[str] = frozenset()) -> str:
    graph = graph_of(SICILIAN, NAMES)
    with TestClient(
        create_app(graph, store=store, settings=Settings(opted_out=opted_out))
    ) as client:
        response = client.get("/progress")
    assert response.status_code == 200
    return response.text


def commit(store: Store, outcome: Outcome, ended_at: float, score: float = 0.5) -> None:
    store.implicit().commit(
        RoundEnd(
            started_at=ended_at - 5,
            ended_at=ended_at,
            side="white",
            path=["e2e4"],
            outcome=outcome,
            end_epd=epd_after("e4"),
            verdicts={},
            before={},
            snapshot_version="test",
        ),
        lambda record: Scores(score, score, score),
    )


def test_the_ledger_lists_every_opening_in_order_without_script() -> None:
    text = page(Store.in_memory())
    assert "<script" not in text
    order = [text.index(f"<span>{name}") for name in (FIRST_MOVES, "Sicilian Defense", "Queen")]
    assert order == sorted(order)
    assert "B20" not in text  # graph_of names carry no ECO


def test_an_opted_out_opening_stays_listed_with_its_scores_while_the_head_leaves_it_out() -> None:
    store = Store.in_memory()
    epd = epd_after("d4", "d5")  # the Queen's Pawn Game's one learner position, White, 2000
    store.implicit().commit(
        RoundEnd(
            started_at=0.0,
            ended_at=time.time(),
            side="white",
            path=["d2d4", "d7d5"],
            outcome="success",
            end_epd=epd,
            verdicts={epd: ("counted", time.time())},
            before={},
            snapshot_version="test",
        ),
        lambda record: Scores(0.0, 0.0, 0.0),
    )
    text = page(store, opted_out=frozenset({"Queen's Pawn Game"}))
    row = text[text.index("<span>Queen&#39;s Pawn Game") :]
    assert "(out)" in row[:200]
    assert "100.0 %" in row[: row.index("</summary>")]
    head = text[: text.index('class="table"')]
    assert "100.0 %" not in head  # opted out: out of the Score


def test_the_session_rate_counts_this_process_only_and_leaves_forced_rounds_out() -> None:
    store = Store.in_memory()
    commit(store, "success", time.time() - 3600)  # an earlier process
    graph = graph_of(SICILIAN, NAMES)
    with TestClient(create_app(graph, store=store)) as client:
        commit(store, "success", time.time() + 1)
        commit(store, "miss", time.time() + 2)
        commit(store, "forced", time.time() + 3)
        text = client.get("/progress").text
    assert "1/2 rounds (50 %)" in text
    assert re.search(r'class="outside">1/2 rounds', text)  # below the target of 80 to 90 %


def test_the_head_shows_the_change_since_the_last_day_played_and_a_sparkline() -> None:
    store = Store.in_memory()
    yesterday = time.time() - 86_400
    commit(store, "success", yesterday, score=0.25)
    text = page(store)
    assert f"-25.0 since {date.fromtimestamp(yesterday).isoformat()}" in text
    assert "<polyline" in text


def test_never_passed_positions_are_listed_by_pooled_count() -> None:
    graph = graph_of(SICILIAN, NAMES)
    with TestClient(create_app(graph)) as client:
        text = client.get("/progress?never=1").text
    listed = re.findall(r'<li><a href="/progress/position/[^"]+">([^<]+)</a>', text)
    assert listed == [
        "the start",  # 10,000
        "1.e4",  # 6,000
        "1.e4 c5",  # 4,000
        "1.d4",  # 3,100
        "1.e4 c5 2.Nf3",
        "1.e4 c5 2.Nf3 d6",
        "1.d4 d5",  # 2,000 each, in EPD order
        "1.e4 c5 2.Nc3",  # 800
    ]


def test_the_play_page_links_to_the_ledger() -> None:
    graph = graph_of(SICILIAN, NAMES)
    with TestClient(create_app(graph)) as client:
        assert 'href="/progress"' in client.get("/").text
