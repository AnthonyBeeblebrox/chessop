import random
import sqlite3
import time
from datetime import date
from pathlib import Path

import chess
import pytest
from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.explanations import Explanations, Page
from chessop.memory import DAY, Params, Record
from chessop.repertoire import START, Settings
from chessop.score import Scores
from chessop.store import FILENAME, RoundEnd, Store
from graphs import board_after, epd_after, graph_of


def test_a_socket_starts_a_round_on_connect(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
    assert msg["type"] == "round"
    assert msg["side"] in ("white", "black")
    assert msg["orientation"] == msg["side"]
    board = chess.Board(msg["fen"])
    assert (board.turn == chess.WHITE) == (msg["side"] == "white")
    assert msg["dests"]
    assert msg["forced"] is None and msg["forced_uci"] is None


# The main moves of the fixture graph at the positions a round can start from.
MAIN_AT_START = {
    epd_after(): {"e4", "d4"},  # the learner's width is 2: Nf3 is the opponent's only
    epd_after("e4"): {"c5", "e5", "e6"},
    epd_after("d4"): {"d5", "Nf6"},
}


def a_miss(board: chess.Board) -> chess.Move:
    """A legal move no main move of the fixture graph plays."""
    return next(m for m in board.legal_moves if board.san(m) in ("a3", "a6"))


def test_a_move_outside_the_main_moves_is_a_miss_and_ends_the_round(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        start = ws.receive_json()
        board = chess.Board(start["fen"])
        miss = a_miss(board)
        ws.send_json({"type": "move", "from": miss.uci()[:2], "to": miss.uci()[2:]})
        moved = ws.receive_json()
        over = ws.receive_json()
    assert moved["type"] == "moved"
    assert moved["verdict"] == "miss"
    assert moved["reply"] is None
    assert moved["dests"] == {}
    assert "reveal" not in moved and "revealed" not in moved
    assert over["type"] == "round_over"
    assert over["outcome"] == "miss"
    assert over["reveal"]["epd"] == board.epd()
    assert over["reveal"]["fen"] == board.fen()
    assert over["reveal"]["played"] == {"san": board.san(miss), "uci": miss.uci()}
    assert {m["san"] for m in over["reveal"]["main"]} == MAIN_AT_START[board.epd()]
    assert over["path"][-1] == miss.uci()
    assert over["plies"] == len(over["path"])


def play_main_moves(ws, start: dict) -> list[dict]:
    """Play the first main move of the fixture graph at every learner turn until the round ends."""
    graph_main = {  # a main move at every learner position of the fixture graph, by EPD
        epd_after(): "e2e4",
        epd_after("e4"): "e7e5",
        epd_after("d4"): "d7d5",
        epd_after("e4", "c5", "Nf3"): "d7d6",
        epd_after("e4", "e5", "Nf3"): "b8c6",
        epd_after("e4", "e6"): "d2d4",
        epd_after("d4", "d5"): "c2c4",
        epd_after("d4", "Nf6"): "c2c4",
        epd_after("e4", "c5"): "g1f3",
        epd_after("e4", "e5"): "g1f3",
        epd_after("e4", "e5", "Nf3", "Nc6"): "f1c4",
    }
    msgs, msg = [], start
    while True:
        uci = graph_main[chess.Board(msg["fen"]).epd()]
        ws.send_json({"type": "move", "from": uci[:2], "to": uci[2:]})
        msg = ws.receive_json()
        msgs.append(msg)
        if not msg["dests"]:
            msgs.append(ws.receive_json())
            return msgs


def test_main_moves_pass_until_the_round_ends_as_a_success(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        start = ws.receive_json()
        msgs = play_main_moves(ws, start)
    *moved, over = msgs
    assert all(m["type"] == "moved" and m["verdict"] == "pass" for m in moved)
    assert all(m["dests"] for m in moved[:-1])
    assert all("reveal" not in m and "revealed" not in m for m in moved)
    assert all(m["reply"] is not None for m in moved[:-1])
    assert over["type"] == "round_over"
    assert over["outcome"] == "success"
    assert over["reveal"]["played"] is None
    assert over["reveal"]["main"]
    assert over["opening"] is not None
    assert over["plies"] == len(over["path"]) >= 2


def test_the_opponent_replies_and_the_banner_follows_the_last_exact_name(
    client: TestClient,
) -> None:
    with client.websocket_connect("/ws") as ws:
        start = ws.receive_json()
        if start["side"] == "black":
            assert start["opening"] in ("King's Pawn Game", "Queen's Pawn Game")
        else:
            assert start["opening"] is None
        first = play_main_moves(ws, start)[0]
    if first["reply"] is not None:
        board = chess.Board(start["fen"])
        board.push_uci(first["played"]["uci"])
        board.push_uci(first["reply"]["uci"])
        assert first["fen"] == board.fen()


def test_next_starts_a_new_round_after_the_end(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        start = ws.receive_json()
        play_main_moves(ws, start)
        ws.send_json({"type": "next"})
        again = ws.receive_json()
    assert again["type"] == "round"
    assert again["dests"]


def test_next_abandons_a_round_in_flight(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "next"})
        again = ws.receive_json()
        board = chess.Board(again["fen"])
        miss = a_miss(board)
        ws.send_json({"type": "move", "from": miss.uci()[:2], "to": miss.uci()[2:]})
        moved = ws.receive_json()
    assert again["type"] == "round"
    assert moved["verdict"] == "miss"


def test_every_moved_message_carries_how_long_the_server_took_to_handle_the_move(
    client: TestClient,
) -> None:
    """What the load-test script reads as the server's move handling (public spec §7)."""
    with client.websocket_connect("/ws") as ws:
        msgs = play_main_moves(ws, ws.receive_json())
    moved = [m for m in msgs if m["type"] == "moved"]
    assert moved
    for m in moved:
        assert isinstance(m["handled_ms"], float)
        assert 0.0 <= m["handled_ms"] < 10_000.0
    assert all("handled_ms" not in m for m in msgs if m["type"] != "moved")


def test_an_illegal_move_gets_an_error_and_changes_nothing(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        start = ws.receive_json()
        for bad in (
            {"type": "move", "from": "e2", "to": "e6"},
            {"type": "move", "from": "z9", "to": "e4"},
            {"type": "move", "from": "e2"},
        ):
            ws.send_json(bad)
            assert ws.receive_json() == {"type": "error", "text": "illegal"}
        msgs = play_main_moves(ws, start)
    assert msgs[-1]["type"] == "round_over"


def test_a_move_with_no_round_in_flight_gets_an_error(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        start = ws.receive_json()
        board = chess.Board(start["fen"])
        miss = a_miss(board)
        ws.send_json({"type": "move", "from": miss.uci()[:2], "to": miss.uci()[2:]})
        ws.receive_json()
        ws.receive_json()
        after = chess.Board(start["fen"])
        after.push(miss)
        legal = next(iter(after.legal_moves)).uci()
        ws.send_json({"type": "move", "from": legal[:2], "to": legal[2:]})
        assert ws.receive_json() == {"type": "error", "text": "illegal"}


def test_the_play_page_loads_the_board_and_the_one_module(client: TestClient) -> None:
    for route in ("/", "/play"):
        page = client.get(route)
        assert page.status_code == 200
        assert '<script type="module" src="/static/play.js">' in page.text
        assert "chessground.brown.css" in page.text
        assert "chessground.cburnett.css" in page.text
        assert "From Wikibooks, <a" in page.text
        assert "<i>Chess Opening Theory</i></a> · CC BY-SA 4.0 · trimmed" in page.text
    assert client.get("/static/play.js").status_code == 200
    assert client.get("/static/chessground/chessground.min.js").status_code == 200
    assert client.get("/static/chessground/LICENSE").status_code == 200


def draws_side(rng: random.Random, side: str) -> bool:
    """Whether the rng's next side draw gives `side` whatever the needs: the draw is
    `random() < p_white` and the side floor keeps `p_white` within [0.2, 0.8]."""
    u = rng.random()
    return u < 0.2 if side == "white" else u >= 0.8


def seeded_for(side: str) -> random.Random:
    """An rng whose round starts with the learner on `side` (the side is its first draw)."""
    return seeded_for_rounds(side)


# 1.e4 is the only move the opponent may draw (1.Nf3 is a stub); 1...e5 ends on a leaf.
E4_E5 = graph_of(
    {"e4": 6000, "e4 e5": 3000, "Nf3": 400},
    {"e4": "King's Pawn Game", "e4 e5": "King's Pawn Game"},
    unstored=frozenset({"Nf3"}),
)


def play(ws, uci: str) -> list[dict]:
    ws.send_json({"type": "move", "from": uci[:2], "to": uci[2:]})
    return [ws.receive_json(), ws.receive_json()]


def test_a_success_on_the_opponents_reply_reveals_the_position_before_it() -> None:
    with (
        TestClient(create_app(E4_E5, rng=seeded_for("white"))) as client,
        client.websocket_connect("/ws") as ws,
    ):
        assert ws.receive_json()["side"] == "white"
        moved, over = play(ws, "e2e4")
    assert moved["verdict"] == "pass"
    assert moved["reply"] == {"san": "e5", "uci": "e7e5"}
    assert moved["dests"] == {}
    assert over["outcome"] == "success"
    assert over["reveal"]["epd"] == epd_after("e4")
    assert over["reveal"]["fen"] == board_after("e4").fen()
    assert over["reveal"]["main"] == [{"san": "e5", "uci": "e7e5"}]
    assert over["reveal"]["played"] is None
    assert over["path"] == ["e2e4", "e7e5"]


def test_a_success_on_the_learners_move_reveals_the_position_it_was_played_from() -> None:
    with (
        TestClient(create_app(E4_E5, rng=seeded_for("black"))) as client,
        client.websocket_connect("/ws") as ws,
    ):
        start = ws.receive_json()
        assert start["side"] == "black"
        assert chess.Board(start["fen"]).epd() == epd_after("e4")  # the stub is never drawn
        moved, over = play(ws, "e7e5")
    assert moved["verdict"] == "pass"
    assert moved["reply"] is None
    assert moved["dests"] == {}
    assert over["outcome"] == "success"
    assert over["reveal"]["epd"] == epd_after("e4")
    assert over["reveal"]["main"] == [{"san": "e5", "uci": "e7e5"}]
    assert over["reveal"]["played"] is None


def test_a_stub_is_a_pass_and_ends_the_round_as_a_success() -> None:
    with (
        TestClient(create_app(E4_E5, rng=seeded_for("white"))) as client,
        client.websocket_connect("/ws") as ws,
    ):
        ws.receive_json()
        moved, over = play(ws, "g1f3")
    assert moved["verdict"] == "pass"
    assert moved["reply"] is None
    assert moved["dests"] == {}
    assert over["outcome"] == "success"
    assert over["reveal"]["epd"] == epd_after()
    assert over["reveal"]["main"] == [{"san": "e4", "uci": "e2e4"}, {"san": "Nf3", "uci": "g1f3"}]


def test_a_main_move_outside_the_learners_width_is_a_miss() -> None:
    graph = graph_of(
        {"e4": 6000, "e4 e5": 3000, "d4": 400, "d4 d5": 200},  # d4 is 4 %: main by rank alone
        {"e4 e5": "King's Pawn Game", "d4 d5": "Queen's Pawn Game"},
    )
    settings = Settings(width_player=1, width_opponent=3)
    with (
        TestClient(create_app(graph, rng=seeded_for("white"), settings=settings)) as client,
        client.websocket_connect("/ws") as ws,
    ):
        ws.receive_json()
        moved, over = play(ws, "d2d4")
    assert moved["verdict"] == "miss"
    assert over["outcome"] == "miss"
    assert over["reveal"]["main"] == [{"san": "e4", "uci": "e2e4"}]
    assert over["reveal"]["played"] == {"san": "d4", "uci": "d2d4"}


def test_the_opponents_first_move_never_lands_on_a_leaf() -> None:
    # 1.e4 is a leaf, 1.d4 is not: a Black learner always meets 1.d4.
    graph = graph_of(
        {"e4": 6000, "d4": 3000, "d4 d5": 1500},
        {"e4": "King's Pawn Game", "d4 d5": "Queen's Pawn Game"},
    )
    for _ in range(10):
        with (
            TestClient(create_app(graph, rng=seeded_for("black"))) as client,
            client.websocket_connect("/ws") as ws,
        ):
            start = ws.receive_json()
        assert start["side"] == "black"
        assert chess.Board(start["fen"]).epd() == epd_after("d4")


def test_the_learner_plays_white_when_every_first_move_ends_on_a_leaf() -> None:
    graph = graph_of({"e4": 6000, "d4": 3000}, {"e4": "King's Pawn Game", "d4": "Queen's Pawn"})
    with (
        TestClient(create_app(graph, rng=seeded_for("black"))) as client,
        client.websocket_connect("/ws") as ws,
    ):
        start = ws.receive_json()
    assert start["side"] == "white"
    assert start["fen"] == chess.Board().fen()


def test_an_empty_repertoire_is_refused_at_start() -> None:
    # Opting out the only first move leaves the start a leaf: nothing in scope to drill.
    graph = graph_of({"e4": 6000, "e4 c5": 3000}, {"e4": "King's Pawn Game"})
    with pytest.raises(ValueError, match="empty"):
        create_app(graph, settings=Settings(opted_out=frozenset({"King's Pawn Game"})))


def test_a_pass_onto_a_position_the_opponent_cannot_draw_from_is_a_success() -> None:
    # With O = 1 the opponent's only move after 1.e4 is the stub 1...a6; 1...c5 is main by rank.
    graph = graph_of(
        {"e4": 6000, "e4 a6": 400, "e4 c5": 300, "e4 c5 Nf3": 200},
        {"e4 c5 Nf3": "Sicilian Defense: Open"},
        unstored=frozenset({"e4 a6"}),
        position_counts={"e4": 10_000},  # so neither reply holds the 5 % share
    )
    settings = Settings(width_player=3, width_opponent=1)
    with (
        TestClient(create_app(graph, rng=seeded_for("white"), settings=settings)) as client,
        client.websocket_connect("/ws") as ws,
    ):
        ws.receive_json()
        moved, over = play(ws, "e2e4")
    assert moved["verdict"] == "pass"
    assert moved["reply"] is None
    assert over["outcome"] == "success"
    assert over["reveal"]["epd"] == epd_after()


def seeded_for_rounds(*sides: str) -> random.Random:
    """An rng whose rounds start on `sides`, when each round draws nothing but its side (the
    opponent draws nothing where it has one move)."""

    def starts(seed: int) -> bool:
        rng = random.Random(seed)
        return all(draws_side(rng, side) for side in sides)

    return random.Random(next(s for s in range(10_000) if starts(s)))


def test_a_miss_then_a_pass_is_a_relearning_pass_over_the_wire() -> None:
    store = Store.in_memory()
    with (
        TestClient(create_app(E4_E5, rng=seeded_for_rounds("white", "white"), store=store)) as c,
        c.websocket_connect("/ws") as ws,
    ):
        ws.receive_json()
        before = time.time()
        _, over = play(ws, "a2a3")
        assert over["outcome"] == "miss"
        assert store.implicit().record(START) == Record(misses=1, relearn=True)
        ws.send_json({"type": "next"})
        assert ws.receive_json()["side"] == "white"
        _, over = play(ws, "e2e4")
        assert over["outcome"] == "success"
    record = store.implicit().record(START)
    assert (record.passes, record.misses, record.relearn) == (0, 1, False)
    assert record.last_pass is not None and before <= record.last_pass <= time.time()
    miss, success = store.implicit().round_log()
    assert (miss["outcome"], miss["path"], miss["end_epd"]) == ("miss", ["a2a3"], epd_after("a3"))
    assert miss["before"] == {
        START: {"passes": 0, "misses": 0, "relearn": False, "last_pass": None, "R": 0.0}
    }
    assert success["outcome"] == "success"
    assert success["before"][START] == {
        "passes": 0,
        "misses": 1,
        "relearn": True,
        "last_pass": None,
        "R": 0.0,
    }
    assert (success["path"], success["plies"]) == (["e2e4", "e7e5"], 2)
    assert success["end_epd"] == epd_after("e4", "e5")
    assert success["side"] == "white"
    assert success["snapshot_version"] == E4_E5.version
    assert success["started_at"] <= success["ended_at"]


# The learner as White moves twice: 1.e4 e5, then 2.Nf3 Nc6 ends on a leaf.
TWO_TURNS = graph_of(
    {"e4": 6000, "e4 e5": 3000, "e4 e5 Nf3": 2000, "e4 e5 Nf3 Nc6": 1500},
    {"e4 e5 Nf3 Nc6": "King's Knight Opening: Normal Variation"},
)


def test_every_pass_of_a_success_is_counted_at_its_own_position() -> None:
    store = Store.in_memory()
    with (
        TestClient(create_app(TWO_TURNS, rng=seeded_for("white"), store=store)) as client,
        client.websocket_connect("/ws") as ws,
    ):
        ws.receive_json()
        ws.send_json({"type": "move", "from": "e2", "to": "e4"})
        assert ws.receive_json()["verdict"] == "pass"
        _, over = play(ws, "g1f3")
    assert over["outcome"] == "success"
    for epd in (START, epd_after("e4", "e5")):
        assert (store.implicit().record(epd).passes, store.implicit().record(epd).relearn) == (
            1,
            False,
        )
    assert set(store.implicit().round_log()[0]["before"]) == {START, epd_after("e4", "e5")}


def test_a_round_abandoned_by_next_writes_nothing() -> None:
    store = Store.in_memory()
    with (
        TestClient(create_app(TWO_TURNS, rng=seeded_for("white"), store=store)) as client,
        client.websocket_connect("/ws") as ws,
    ):
        ws.receive_json()
        ws.send_json({"type": "move", "from": "e2", "to": "e4"})
        assert ws.receive_json()["dests"]
        ws.send_json({"type": "next"})
        ws.receive_json()
    assert store.implicit().round_log() == []
    assert store.implicit().record(START) == Record()


def test_a_socket_closed_mid_round_writes_nothing_and_the_next_socket_starts_afresh() -> None:
    """What the play page's reconnect relies on (public spec §7): the cut round is abandoned,
    its pass never applied and no miss charged; a new socket's round starts from the start."""
    store = Store.in_memory()
    rng = seeded_for_rounds("white", "white")
    with TestClient(create_app(TWO_TURNS, rng=rng, store=store)) as client:
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({"type": "move", "from": "e2", "to": "e4"})
            assert ws.receive_json()["verdict"] == "pass"  # the round is cut on its second turn
        assert store.implicit().round_log() == []
        assert store.implicit().daily_scores() == []
        assert store.implicit().record(START) == Record()
        with client.websocket_connect("/ws") as ws:
            fresh = ws.receive_json()
            assert fresh["type"] == "round"
            assert chess.Board(fresh["fen"]).epd() == START
            _, over = play(ws, "a2a3")
    assert over["outcome"] == "miss"
    [miss] = store.implicit().round_log()
    assert miss["path"] == ["a2a3"]
    assert store.implicit().record(START) == Record(misses=1, relearn=True)


def test_records_outlive_a_change_of_repertoire(tmp_path: Path) -> None:
    store = Store.open(tmp_path)
    with (
        TestClient(create_app(E4_E5, rng=seeded_for("white"), store=store)) as client,
        client.websocket_connect("/ws") as ws,
    ):
        ws.receive_json()
        play(ws, "e2e4")
    store.close()
    other = graph_of({"e4": 6000, "e4 c5": 3000}, {"e4 c5": "Sicilian Defense"})
    store = Store.open(tmp_path)
    with TestClient(create_app(other, rng=seeded_for("white"), store=store)):
        assert store.implicit().record(START).passes == 1


def test_two_sockets_with_rounds_in_flight_both_commit() -> None:
    store = Store.in_memory()
    with (
        TestClient(create_app(E4_E5, rng=seeded_for_rounds("white", "white"), store=store)) as c,
        c.websocket_connect("/ws") as first,
        c.websocket_connect("/ws") as second,
    ):
        first.receive_json()
        second.receive_json()
        play(first, "a2a3")
        play(second, "h2h3")
    assert [r["path"] for r in store.implicit().round_log()] == [["a2a3"], ["h2h3"]]
    assert store.implicit().record(START) == Record(misses=2, relearn=True)


# E4_E5's learner positions: the start, White to move (10,000), and 1.e4, Black to move (6,000).


def test_the_score_is_on_every_round_and_its_change_on_every_round_over() -> None:
    store = Store.in_memory()
    with (
        TestClient(create_app(E4_E5, rng=seeded_for_rounds("white", "white"), store=store)) as c,
        c.websocket_connect("/ws") as ws,
    ):
        start = ws.receive_json()
        assert start["score"] == 0.0
        _, over = play(ws, "e2e4")  # a counted pass at the start: R = 1 there
        assert over["score"] == {"value": 62.5, "delta": 62.5}
        ws.send_json({"type": "next"})
        assert ws.receive_json()["score"] == 62.5
        _, over = play(ws, "a2a3")  # a miss leaves the clock: R barely moves
        assert over["score"] == {"value": 62.5, "delta": 0.0}
    [today] = store.implicit().daily_scores()
    assert today["day"] == date.today().isoformat()
    assert (today["rounds"], today["successes"]) == (2, 1)
    assert today["score"] == pytest.approx(0.625)
    assert today["white_score"] == pytest.approx(1.0)
    assert today["black_score"] == 0.0


def test_the_score_since_the_last_round_played_is_on_a_sockets_first_round_only(
    tmp_path: Path,
) -> None:
    store = Store.open(tmp_path)
    three_days_ago = time.time() - 3 * DAY
    store.implicit().commit(  # a round three days ago that left the start known and 1.e4 half known
        RoundEnd(
            started_at=three_days_ago - 5,
            ended_at=three_days_ago,
            side="white",
            path=["e2e4", "e7e5"],
            outcome="success",
            end_epd=epd_after("e4", "e5"),
            verdicts={START: ("counted", three_days_ago)},
            before={},
            snapshot_version=E4_E5.version,
        ),
        lambda record: Scores(0.8, 1.0, 0.5),
    )
    day = date.fromtimestamp(three_days_ago).isoformat()
    # h = 2 days after one counted pass: R = 2^(-3/2) at the start, 0 at 1.e4.
    now_score = round(100 * 10_000 * 2**-1.5 / 16_000, 1)
    since = {"delta": round(now_score - 80.0, 1), "day": day}
    with TestClient(create_app(E4_E5, rng=seeded_for_rounds("white"), store=store)) as client:
        with client.websocket_connect("/ws") as ws:
            first = ws.receive_json()
            assert (first["score"], first["score_since"]) == (now_score, since)
            ws.send_json({"type": "next"})
            assert ws.receive_json()["score_since"] is None
        with client.websocket_connect("/ws") as another_tab:
            assert another_tab.receive_json()["score_since"] == since


def test_a_first_run_has_no_score_since() -> None:
    with (
        TestClient(create_app(E4_E5, rng=seeded_for("white"))) as client,
        client.websocket_connect("/ws") as ws,
    ):
        assert ws.receive_json()["score_since"] is None


def test_the_opponents_moves_are_counted_as_faced_and_rebuilt_from_the_log(
    tmp_path: Path,
) -> None:
    store = Store.open(tmp_path)
    app = create_app(E4_E5, rng=seeded_for_rounds("white", "white"), store=store)
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json()
        play(ws, "e2e4")  # 1...e5 in reply
        ws.send_json({"type": "next"})
        ws.receive_json()
        play(ws, "e2e4")
    faced = app.state.session.steering.faced
    assert faced == {(epd_after("e4"), "e7e5"): 2}
    store.close()
    store = Store.open(tmp_path)
    assert create_app(E4_E5, store=store).state.session.steering.faced == faced


def test_a_round_end_refreshes_the_needs_the_side_is_drawn_by() -> None:
    store = Store.in_memory()
    app = create_app(E4_E5, rng=seeded_for("white"), store=store)
    steering = app.state.session.steering
    assert steering.root_need(time.time()) == {"white": 10_000, "black": 6000}
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json()
        play(ws, "e2e4")  # a counted pass at the start: its need falls to the floor
    assert steering.root_need(time.time()) == {"white": pytest.approx(1000), "black": 6000}


# Forced exploration, always on. As White at the start, 1.d4 lands on a leaf: its mean need is the
# floor. After 1.e4 e5, 2.Bc4 lands on a leaf and 2.Nf3 leads to 2...Nc6, a White position.
FORKS = graph_of(
    {
        "e4": 6000,
        "d4": 3000,
        "e4 e5": 3000,
        "e4 e5 Nf3": 2000,
        "e4 e5 Bc4": 500,
        "e4 e5 Nf3 Nc6": 1500,
        "e4 e5 Nf3 Nc6 Bc4": 1000,
    },
    {"d4": "Queen's Pawn Game", "e4 e5 Bc4": "Bishop's Opening", "e4 e5 Nf3 Nc6 Bc4": "Italian"},
)
ALWAYS = Params(forced_rate=1.0)


def test_a_position_never_seen_sets_nothing_aside() -> None:
    with (
        TestClient(create_app(FORKS, rng=seeded_for("white"), params=ALWAYS)) as client,
        client.websocket_connect("/ws") as ws,
    ):
        start = ws.receive_json()
        assert start["side"] == "white"
        assert (start["forced"], start["forced_uci"]) == (None, None)
        ws.send_json({"type": "move", "from": "e2", "to": "e4"})
        moved = ws.receive_json()
    assert moved["verdict"] == "pass"
    assert (moved["forced"], moved["forced_uci"]) == (None, None)


def test_playing_the_set_aside_move_ends_the_round_as_forced() -> None:
    store = Store.in_memory()
    rng = seeded_for_rounds("white", "white")
    with (
        TestClient(create_app(FORKS, rng=rng, store=store, params=ALWAYS)) as client,
        client.websocket_connect("/ws") as ws,
    ):
        ws.receive_json()
        ws.send_json({"type": "move", "from": "e2", "to": "e4"})
        assert ws.receive_json()["forced"] is None  # 1.e4 e5 never seen
        assert play(ws, "a2a3")[1]["outcome"] == "miss"
        start_record, fork_record = (
            store.implicit().record(START),
            store.implicit().record(epd_after("e4", "e5")),
        )
        ws.send_json({"type": "next"})
        start = ws.receive_json()
        assert start["side"] == "white"
        assert (start["forced"], start["forced_uci"]) == ("d4", "d2d4")
        ws.send_json({"type": "move", "from": "e2", "to": "e4"})
        moved = ws.receive_json()
        assert moved["verdict"] == "pass"
        assert (moved["forced"], moved["forced_uci"]) == ("Bc4", "f1c4")
        moved, over = play(ws, "f1c4")
    assert moved["verdict"] == "forced"
    assert moved["reply"] is None and moved["dests"] == {}
    assert (moved["forced"], moved["forced_uci"]) == (None, None)
    assert over["outcome"] == "forced"
    assert over["reveal"]["epd"] == epd_after("e4", "e5")
    assert over["reveal"]["played"] == {"san": "Bc4", "uci": "f1c4"}
    assert {m["san"] for m in over["reveal"]["main"]} == {"Nf3", "Bc4"}
    assert over["score"]["delta"] is None
    assert over["path"] == ["e2e4", "e7e5", "f1c4"]
    # The set-aside move's position is untouched; the pass before it is applied.
    assert store.implicit().record(epd_after("e4", "e5")) == fork_record
    assert store.implicit().record(START).last_pass != start_record.last_pass
    log = store.implicit().round_log()[-1]
    assert (log["outcome"], log["end_epd"]) == ("forced", epd_after("e4", "e5", "Bc4"))
    assert set(log["before"]) == {START, epd_after("e4", "e5")}
    [today] = store.implicit().daily_scores()
    assert (today["rounds"], today["successes"]) == (1, 0)


def test_a_set_aside_move_is_never_announced_at_a_width_of_one() -> None:
    settings = Settings(width_player=1)  # 1.d4 is 30 % of the games: still accepted by share
    store = Store.in_memory()
    rng = seeded_for_rounds("white", "white")
    with (
        TestClient(create_app(FORKS, rng=rng, store=store, settings=settings, params=ALWAYS)) as c,
        c.websocket_connect("/ws") as ws,
    ):
        ws.receive_json()
        play(ws, "a2a3")
        ws.send_json({"type": "next"})
        start = ws.receive_json()
        assert start["side"] == "white"
        assert start["forced"] is None
        moved, over = play(ws, "d2d4")
    assert (moved["verdict"], over["outcome"]) == ("pass", "success")


# The Explanation on `round_over`.


def page(page_id: int, moves: str) -> Page:
    title = f"Chess Opening Theory/{moves}"
    return Page(page_id, title, f"https://en.wikibooks.org/wiki/{title}", f"lead {page_id}", "text")


def explained(*pages: tuple[str, Page]) -> Explanations:
    """Explanations with `pages` at the positions after their SAN lines."""
    return Explanations(
        "test",
        [p for _, p in pages],
        {epd_after(*line.split()): p.id for line, p in pages},
    )


def round_over_with(explanations: Explanations, side: str, uci: str) -> dict:
    with (
        TestClient(create_app(E4_E5, rng=seeded_for(side), explanations=explanations)) as client,
        client.websocket_connect("/ws") as ws,
    ):
        assert ws.receive_json()["side"] == side
        return play(ws, uci)[1]


def test_a_success_is_explained_at_the_leaf_where_it_ended() -> None:
    e4, e4_e5 = page(1, "1. e4"), page(2, "1. e4/1...e5")
    over = round_over_with(explained(("e4", e4), ("e4 e5", e4_e5)), "white", "e2e4")
    assert over["outcome"] == "success"
    assert over["reveal"]["epd"] == epd_after("e4")  # the arrows are at the position before
    assert over["explanation"] == {
        "lead": "lead 2",
        "text": "text",
        "title": e4_e5.title,
        "url": e4_e5.url,
        "borrowed_from": None,
    }


def test_a_position_without_a_page_borrows_the_nearest_one_on_the_path() -> None:
    over = round_over_with(explained(("e4", page(1, "1. e4"))), "white", "e2e4")
    assert over["explanation"]["lead"] == "lead 1"
    assert over["explanation"]["borrowed_from"] == "1.e4"


def test_a_miss_is_explained_at_the_position_the_move_was_played_from() -> None:
    e4, a6 = page(1, "1. e4"), page(2, "1. e4/1...a6")
    over = round_over_with(explained(("e4", e4), ("e4 a6", a6)), "black", "a7a6")
    assert over["outcome"] == "miss"
    assert over["explanation"]["lead"] == "lead 1"
    assert over["explanation"]["borrowed_from"] is None


def test_a_round_ending_on_an_unnamed_leaf_below_the_last_name_borrows_its_text() -> None:
    # No named-position prune: 2.Nf3 is unnamed and has no page, yet it is drilled to.
    graph = graph_of({"e4": 6000, "e4 c5": 3000, "e4 c5 Nf3": 1500}, {"e4 c5": "Sicilian Defense"})
    sicilian = page(1, "1. e4/1...c5")
    explanations = explained(("e4 c5", sicilian))
    with (
        TestClient(create_app(graph, rng=seeded_for("white"), explanations=explanations)) as c,
        c.websocket_connect("/ws") as ws,
    ):
        assert ws.receive_json()["side"] == "white"
        ws.send_json({"type": "move", "from": "e2", "to": "e4"})
        moved = ws.receive_json()
        assert (moved["verdict"], moved["reply"]["san"]) == ("pass", "c5")
        moved, over = play(ws, "g1f3")
    assert (moved["verdict"], over["outcome"]) == ("pass", "success")
    assert over["path"] == ["e2e4", "c7c5", "g1f3"]
    assert over["opening"] == "Sicilian Defense"
    assert over["explanation"]["title"] == sicilian.title
    assert over["explanation"]["borrowed_from"] == "1.e4 c5"


def test_the_explanation_is_null_when_no_position_on_the_path_has_a_page() -> None:
    over = round_over_with(explained(("d4", page(1, "1. d4"))), "white", "e2e4")
    assert over["outcome"] == "success"
    assert over["explanation"] is None


def test_the_sound_message_persists_the_setting_and_gets_no_reply() -> None:
    store = Store.in_memory()
    with (
        TestClient(create_app(E4_E5, rng=seeded_for_rounds("white", "white"), store=store)) as c,
        c.websocket_connect("/ws") as ws,
    ):
        ws.receive_json()
        ws.send_json({"type": "sound", "on": False})  # a round in flight
        moved, over = play(ws, "a2a3")  # the next message is the move's, not a reply to `sound`
        assert (moved["type"], over["type"]) == ("moved", "round_over")
        assert store.implicit().setting("sound", True) is False
        ws.send_json({"type": "sound", "on": True})  # no round in flight
        ws.send_json({"type": "next"})
        assert ws.receive_json()["type"] == "round"
    assert store.implicit().setting("sound", False) is True


def test_a_sound_message_without_a_boolean_changes_nothing() -> None:
    store = Store.in_memory()
    with (
        TestClient(create_app(E4_E5, rng=seeded_for("white"), store=store)) as c,
        c.websocket_connect("/ws") as ws,
    ):
        ws.receive_json()
        ws.send_json({"type": "sound", "on": "no"})
        ws.send_json({"type": "sound"})
        assert play(ws, "e2e4")[1]["type"] == "round_over"
    assert store.implicit().setting("sound", True) is True


def test_the_play_page_starts_with_the_persisted_sound_and_animation() -> None:
    store = Store.in_memory()
    with TestClient(create_app(E4_E5, rng=seeded_for("white"), store=store)) as client:
        page = client.get("/").text
        assert 'data-sound="true"' in page and 'data-animation-ms="100"' in page
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({"type": "sound", "on": False})
        store.implicit().set_setting("animation_ms", 0)
        page = client.get("/").text
        assert 'data-sound="false"' in page and 'data-animation-ms="0"' in page


def test_the_sfx_sounds_are_served_as_real_audio_with_their_licence(client: TestClient) -> None:
    # The set's Error is a link to the non-free standard set: a miss plays Defeat instead.
    for name in ("Move", "Capture", "Check", "Victory", "Defeat"):
        sound = client.get(f"/static/sound/{name}.mp3")
        assert sound.status_code == 200
        assert sound.content[:3] == b"ID3"  # an MP3, not a symlink stub left by a copy
    assert "AFFERO" in client.get("/static/sound/LICENSE").text.upper()
    assert "Enigmahack" in client.get("/static/sound/NOTICE").text


def test_a_visit_notes_when_the_learner_was_last_seen(tmp_path: Path) -> None:
    Store.open(tmp_path).implicit()
    db = sqlite3.connect(tmp_path / FILENAME)
    db.execute("UPDATE learner SET last_seen = 1000.0")  # long ago
    db.commit()
    db.close()
    store = Store.open(tmp_path)
    started = time.time()
    with TestClient(create_app(E4_E5, store=store)) as client:
        assert store.implicit().last_seen == 1000.0
        client.get("/play")
        seen = store.implicit().last_seen
        assert seen >= started
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
        assert store.implicit().last_seen == seen  # the same day: not written again
    store.close()
    assert Store.open(tmp_path).implicit().last_seen == seen
