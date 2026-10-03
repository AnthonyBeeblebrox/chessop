"""The progress view's actions (spec §10.3): opting an opening in or out, and the resets."""

import random
import time
from urllib.parse import quote

from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.memory import Record
from chessop.repertoire import START, Settings
from chessop.score import Scores
from chessop.store import RoundEnd, Store
from graphs import epd_after, graph_of
from test_progress import NAMES, SICILIAN


def toggle(family: str) -> str:
    return f"/progress/opening/{quote(family, safe='')}/toggle"


def test_toggling_an_opening_opts_it_out_with_what_only_it_reaches_and_back_in() -> None:
    store = Store.in_memory()
    app = create_app(graph_of(SICILIAN, NAMES), store=store)
    with TestClient(app) as client:
        done = client.post(toggle("Sicilian Defense"), follow_redirects=False)
        assert done.status_code == 303
        assert done.headers["location"] == "/progress"
        kept = app.state.session.steering.repertoire.positions
        # The Sicilian's named positions go, and 2.Nf3 and 2.Nc3 with them: only they reach them.
        for line in ("e4 c5", "e4 c5 Nf3", "e4 c5 Nc3", "e4 c5 Nf3 d6"):
            assert epd_after(*line.split()) not in kept
        assert epd_after("e4") in kept  # the King's Pawn Game, named itself
        assert store.implicit().setting("opted_out", None) == ["Sicilian Defense"]
        text = client.get("/progress").text
        row = text[text.index("<span>Sicilian Defense") :]
        assert "(out)" in row[:200]  # still listed

        client.post(toggle("Sicilian Defense"))
        assert epd_after("e4", "c5", "Nf3") in app.state.session.steering.repertoire.positions
        assert store.implicit().setting("opted_out", None) == []


def test_a_shared_position_named_in_a_kept_opening_survives_an_opt_out() -> None:
    # 1.d4 Nf6 2.c4 e6 is reached first through the Indian Defense, and by 1.c4 e6 2.d4 Nf6
    # through the English; it is named in the English, so opting the Indian out keeps it.
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
        {"d4 Nf6": "Indian Defense", "d4 Nf6 c4 e6": "English Opening: Anglo-Indian"},
    )
    app = create_app(graph)
    with TestClient(app) as client:
        client.post(toggle("Indian Defense"))
    kept = app.state.session.steering.repertoire.positions
    assert epd_after("d4", "Nf6") not in kept
    assert epd_after("d4", "Nf6", "c4") not in kept  # reached only through the Indian
    assert epd_after("c4", "e6", "d4", "Nf6") in kept
    assert epd_after("c4", "e6", "d4") in kept


def test_the_first_moves_and_unknown_openings_cannot_be_toggled() -> None:
    with TestClient(create_app(graph_of(SICILIAN, NAMES))) as client:
        assert client.post(toggle("First moves")).status_code == 404
        assert client.post(toggle("Nowhere Gambit")).status_code == 404


def test_opting_everything_out_is_refused_and_nothing_saved() -> None:
    store = Store.in_memory()
    graph = graph_of({"e4": 6000, "e4 e5": 3000}, {"e4": "King's Pawn Game"})
    app = create_app(graph, rng=random.Random(1), store=store)
    with TestClient(app) as client:
        refused = client.post(toggle("King's Pawn Game"))
    assert refused.status_code == 400
    assert "empty" in refused.text
    assert store.implicit().setting("opted_out", None) is None


def remember(store: Store, *epds: str) -> None:
    """One round passing once at each of `epds`, committed."""
    now = time.time()
    store.implicit().commit(
        RoundEnd(
            started_at=now - 5,
            ended_at=now,
            side="white",
            path=[],
            outcome="success",
            end_epd=epds[-1],
            verdicts={epd: ("counted", now) for epd in epds},
            before={},
            snapshot_version="test",
        ),
        lambda record: Scores(0.5, 0.5, 0.5),
    )


SICILIAN_LEARNER = [
    epd_after(*line.split()) for line in ("e4 c5", "e4 c5 Nf3", "e4 c5 Nc3", "e4 c5 Nf3 d6")
]
OTHERS = [START, epd_after("e4"), epd_after("d4", "d5")]


def test_resetting_an_opening_asks_first_then_deletes_its_positions_records_only() -> None:
    store = Store.in_memory()
    remember(store, *SICILIAN_LEARNER, *OTHERS)
    reset = f"/progress/opening/{quote('Sicilian Defense', safe='')}/reset"
    with TestClient(create_app(graph_of(SICILIAN, NAMES), store=store)) as client:
        confirm = client.post(reset)
        assert confirm.status_code == 200
        assert f'action="{reset}"' in confirm.text
        assert "<script" not in confirm.text
        assert all(
            store.implicit().record(epd).passes == 1 for epd in SICILIAN_LEARNER
        )  # nothing yet

        done = client.post(reset, data={"confirm": "yes"}, follow_redirects=False)
        assert done.status_code == 303
        assert done.headers["location"] == "/progress"
    assert all(store.implicit().record(epd) == Record() for epd in SICILIAN_LEARNER)
    assert all(store.implicit().record(epd).passes == 1 for epd in OTHERS)
    assert len(store.implicit().round_log()) == 1
    assert len(store.implicit().daily_scores()) == 1


def test_an_opted_out_opening_can_be_reset_and_an_unknown_one_cannot() -> None:
    store = Store.in_memory()
    remember(store, *SICILIAN_LEARNER)
    app = create_app(
        graph_of(SICILIAN, NAMES),
        store=store,
        settings=Settings(opted_out=frozenset({"Sicilian Defense"})),
    )
    with TestClient(app) as client:
        client.post(
            f"/progress/opening/{quote('Sicilian Defense', safe='')}/reset",
            data={"confirm": "yes"},
        )
        assert client.post("/progress/opening/Nowhere/reset").status_code == 404
    assert all(store.implicit().record(epd) == Record() for epd in SICILIAN_LEARNER)


def test_resetting_a_position_asks_first_then_deletes_its_record_only() -> None:
    store = Store.in_memory()
    remember(store, *SICILIAN_LEARNER, *OTHERS)
    epd = epd_after("e4", "c5", "Nf3")
    page = f"/progress/position/{quote(epd, safe='')}"
    with TestClient(create_app(graph_of(SICILIAN, NAMES), store=store)) as client:
        assert f'action="{page}/reset"' in client.get(page).text  # the page offers it
        confirm = client.post(f"{page}/reset")
        assert confirm.status_code == 200
        assert f'action="{page}/reset"' in confirm.text
        assert store.implicit().record(epd).passes == 1

        done = client.post(f"{page}/reset", data={"confirm": "yes"}, follow_redirects=False)
        assert done.status_code == 303
        assert done.headers["location"] == page
    assert store.implicit().record(epd) == Record()
    assert all(
        store.implicit().record(e).passes == 1 for e in [*OTHERS, *SICILIAN_LEARNER] if e != epd
    )
    assert len(store.implicit().round_log()) == 1
    assert len(store.implicit().daily_scores()) == 1


def test_a_position_outside_the_ledger_cannot_be_reset() -> None:
    with TestClient(create_app(graph_of(SICILIAN, NAMES))) as client:
        epd = epd_after("h4")
        assert client.post(f"/progress/position/{quote(epd, safe='')}/reset").status_code == 404


def test_a_reset_gives_every_open_tab_a_fresh_round() -> None:
    store = Store.in_memory()
    remember(store, *SICILIAN_LEARNER)
    epd = quote(epd_after("e4", "c5"), safe="")
    with (
        TestClient(create_app(graph_of(SICILIAN, NAMES), rng=random.Random(2), store=store)) as c,
        c.websocket_connect("/ws") as ws,
    ):
        assert ws.receive_json()["type"] == "round"
        c.post(f"/progress/position/{epd}/reset", data={"confirm": "yes"})
        assert ws.receive_json()["type"] == "round"


def test_every_opening_row_offers_its_reset_and_every_opening_its_toggle_as_plain_forms() -> None:
    with TestClient(create_app(graph_of(SICILIAN, NAMES))) as client:
        text = client.get("/progress").text
    assert "<script" not in text
    sicilian = quote("Sicilian Defense", safe="")
    assert f'<form method="post" action="/progress/opening/{sicilian}/toggle"' in text
    assert f'<form method="post" action="/progress/opening/{sicilian}/reset"' in text
    first = quote("First moves", safe="")
    assert f'action="/progress/opening/{first}/reset"' in text
    assert f'action="/progress/opening/{first}/toggle"' not in text
    assert "Drill from here" not in text
