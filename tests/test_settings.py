import random
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.graph import FIXTURE_SNAPSHOT, Graph, load_graph
from chessop.memory import Record
from chessop.repertoire import START
from chessop.score import Scores
from chessop.store import RoundEnd, Store
from graphs import graph_of

FIELDS = (
    "band",
    "width_player",
    "width_opponent",
    "popularity_floor",
    "share",
    "h0",
    "h_min",
    "h_max",
    "sure",
    "floor",
    "C",
    "alpha",
    "forced_rate",
    "side_floor",
    "sound",
    "animation_ms",
)


E4_E5 = graph_of({"e4": 6000, "e4 e5": 3000}, {"e4 e5": "King's Pawn Game"})
# 1.e4 e5 2.Nf3 Nc6: a round the learner can pass in without it ending.
DEEP = graph_of(
    {"e4": 6000, "e4 e5": 3000, "e4 e5 Nf3": 2000, "e4 e5 Nf3 Nc6": 1500},
    {"e4 e5": "King's Pawn Game", "e4 e5 Nf3 Nc6": "King's Knight Opening: Normal Variation"},
)

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
AFTER_E4_FEN = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
E4_E5_AFTER_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq -"


def valid_form(**overrides: str) -> dict[str, str]:
    """The form as the page submits it at the defaults (spec §11, §5.4), some fields changed."""
    form = {
        "band": "1500+",
        "width_player": "3",
        "width_opponent": "3",
        "popularity_floor": "0.0002",
        "share": "0.05",
        "h0": "24",  # hours
        "h_min": "15",  # minutes
        "h_max": "270",  # days
        "sure": "0.9",
        "floor": "0.1",
        "C": "1",
        "alpha": "1",
        "forced_rate": "0.1",
        "side_floor": "0.2",
        "sound": "on",
        "animation_ms": "100",
    }
    return {**form, **overrides}


def test_the_settings_page_has_every_key_the_band_and_the_snapshot_version(graph: Graph) -> None:
    with TestClient(create_app(graph)) as client:
        page = client.get("/settings")
    assert page.status_code == 200
    for name in FIELDS:
        assert f'name="{name}"' in page.text
    assert "<b>1500+</b>" in page.text
    assert graph.version in page.text


def band_options(page: str) -> list[str]:
    """The band list of the settings page, in order."""
    return re.findall(r'<option value="([^"]*)"', page)


def test_the_band_is_chosen_from_a_list_of_eight_and_no_rating_is_asked(graph: Graph) -> None:
    with TestClient(create_app(graph)) as client:
        page = client.get("/settings").text
    assert band_options(page) == [
        "0-1200",
        "1200-1500",
        "1500-1800",
        "1800-2100",
        "2100+",
        "1200+",
        "1500+",
        "1800+",
    ]
    assert '<option value="1500+" selected>' in page
    assert 'name="rating"' not in page


def test_a_new_learner_drills_1500_plus_without_being_asked(graph: Graph) -> None:
    with TestClient(create_app(graph, store=Store.in_memory())) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "round"
        page = client.get("/settings").text
    assert "Drilling band <b>1500+</b>" in page
    assert '<option value="1500+" selected>' in page


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("popularity_floor", "0.0001"),  # below the snapshot's storage cut-off
        ("share", "1.5"),
        ("share", "-0.1"),
        ("width_player", "0"),
        ("width_opponent", "2.5"),
        ("animation_ms", "101"),
        ("animation_ms", "-1"),
        ("h0", "0"),
        ("sure", "1"),
        ("forced_rate", "nan"),
    ],
)
def test_invalid_input_is_refused_with_a_message_and_nothing_saved(
    graph: Graph, field: str, value: str
) -> None:
    store = Store.in_memory()
    with TestClient(create_app(graph, store=store)) as client:
        page = client.post("/settings", data=valid_form(**{field: value}))
        assert page.status_code == 400
        assert 'class="error"' in page.text
        assert f'value="{value}"' in page.text  # the refused input is shown back
        assert store.implicit().setting(field, "unset") == "unset"


def test_saving_stores_every_key_and_the_page_shows_it_back(graph: Graph) -> None:
    store = Store.in_memory()
    form = valid_form(
        width_player="1", share="0.1", h0="12", sound="", animation_ms="0", forced_rate="0.3"
    )
    with TestClient(create_app(graph, store=store)) as client:
        saved = client.post("/settings", data=form, follow_redirects=False)
        assert saved.status_code == 303
        page = client.get("/settings")
    assert store.implicit().setting("width_player", None) == 1
    assert store.implicit().setting("share", None) == 0.1
    assert store.implicit().setting("h0", None) == 12 * 3600
    assert store.implicit().setting("sound", None) is False
    assert store.implicit().setting("animation_ms", None) == 0
    assert store.implicit().setting("band", None) == "1500+"
    assert 'name="h0" value="12"' in page.text
    assert "forced exploration rate is ignored" in page.text


def test_the_forced_rate_is_not_noted_as_ignored_at_a_width_above_one(graph: Graph) -> None:
    with TestClient(create_app(graph)) as client:
        assert "forced exploration rate is ignored" not in client.get("/settings").text


def pass_at_the_first_turn(ws, start: dict) -> dict:
    """Play the main move at the learner's first turn (1.e4 or 1...e5); the `moved` reply."""
    uci = "e2e4" if start["side"] == "white" else "e7e5"
    ws.send_json({"type": "move", "from": uci[:2], "to": uci[2:]})
    return ws.receive_json()


def a_round_passing_at_start(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        pass_at_the_first_turn(ws, ws.receive_json())
        while ws.receive_json()["type"] != "round_over":
            pass


def test_saving_regenerates_the_repertoire_and_leaves_the_records_intact() -> None:
    store = Store.in_memory()
    app = create_app(E4_E5, rng=random.Random(1), store=store)
    with TestClient(app) as client:
        a_round_passing_at_start(client)
        records = {epd: store.implicit().record(epd) for epd in (START, E4_E5_AFTER_E4)}
        before = app.state.session.steering
        client.post("/settings", data=valid_form(width_player="1", width_opponent="1"))
        after = app.state.session.steering
    assert after is not before
    assert after.repertoire.settings.width_player == 1
    assert {epd: store.implicit().record(epd) for epd in (START, E4_E5_AFTER_E4)} == records
    assert any(r != Record() for r in records.values())


def test_a_position_leaving_the_repertoire_returns_with_its_record() -> None:
    store = Store.in_memory()
    after_nf3 = "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq -"
    store.implicit().commit(
        RoundEnd(
            1.0,
            2.0,
            "black",
            ["e2e4", "e7e5", "g1f3"],
            "miss",
            after_nf3,
            {after_nf3: ("miss", 2.0)},
            {},
            "test",
        ),
        lambda record: Scores(0.0, 0.0, 0.0),
    )
    app = create_app(DEEP, store=store)
    with TestClient(app) as client:
        saved = client.post("/settings", data=valid_form(popularity_floor="0.25"))  # Nf3: 20 %
        assert saved.status_code == 200
        assert after_nf3 not in app.state.session.steering.repertoire.positions
        assert store.implicit().record(after_nf3).misses == 1
        client.post("/settings", data=valid_form())
        assert after_nf3 in app.state.session.steering.repertoire.learner_positions
    assert store.implicit().record(after_nf3) == Record(misses=1, relearn=True)


def test_a_setting_that_empties_the_repertoire_is_refused(graph: Graph) -> None:
    store = Store.in_memory()
    with TestClient(create_app(graph, store=store)) as client:
        page = client.post("/settings", data=valid_form(popularity_floor="1"))
    assert page.status_code == 400
    assert "empty" in page.text
    assert store.implicit().setting("popularity_floor", "unset") == "unset"


def test_saving_another_band_loads_it_and_regenerates_the_repertoire() -> None:
    loaded: list[str] = []

    def load_band(band: str) -> Graph:
        loaded.append(band)
        return load_graph(FIXTURE_SNAPSHOT, band)

    store = Store.in_memory()
    app = create_app(load_graph(FIXTURE_SNAPSHOT), store=store, load_band=load_band)
    with TestClient(app) as client:
        before = app.state.session.steering
        saved = client.post("/settings", data=valid_form(band="1500-1800"), follow_redirects=False)
        page = client.get("/settings")
    assert saved.status_code == 303
    assert loaded == ["1500-1800"]
    assert app.state.session.steering is not before
    assert app.state.session.steering.repertoire.graph.band == "1500-1800"
    assert store.implicit().setting("band", None) == "1500-1800"
    assert "<b>1500-1800</b>" in page.text
    assert '<option value="1500-1800" selected>' in page.text


@pytest.mark.parametrize("band", ["2100+", "1800+"])
def test_a_band_the_snapshot_lacks_is_listed_but_refused(graph: Graph, band: str) -> None:
    store = Store.in_memory()
    with TestClient(create_app(graph, store=store, load_band=lambda b: graph)) as client:
        assert f'<option value="{band}" disabled>' in client.get("/settings").text
        page = client.post("/settings", data=valid_form(band=band))
    assert page.status_code == 400
    assert f"the snapshot holds no games for band {band}" in page.text
    assert store.implicit().setting("band", "unset") == "unset"


@pytest.mark.parametrize("band", ["1600", "", "1500+ "])
def test_a_band_not_among_the_eight_is_refused(graph: Graph, band: str) -> None:
    store = Store.in_memory()
    with TestClient(create_app(graph, store=store)) as client:
        page = client.post("/settings", data=valid_form(band=band))
    assert page.status_code == 400
    assert "Rating band: one of the bands listed" in page.text
    assert store.implicit().setting("band", "unset") == "unset"


def a_miss(msg: dict) -> str:
    return "a2a3" if msg["side"] == "white" else "a7a6"


def test_saving_gives_every_open_tab_a_fresh_round_and_abandons_theirs_unrecorded() -> None:
    store = Store.in_memory()
    with (
        TestClient(create_app(DEEP, rng=random.Random(5), store=store)) as client,
        client.websocket_connect("/ws") as first,
        client.websocket_connect("/ws") as second,
    ):
        start = first.receive_json()
        second.receive_json()
        # A pass in the first tab, its round still in flight when the settings are saved.
        assert pass_at_the_first_turn(first, start)["dests"]
        client.post("/settings", data=valid_form(share="0.2"))
        for ws in (first, second):
            fresh = ws.receive_json()
            assert fresh["type"] == "round"
            assert fresh["score_since"] is None
            assert fresh["fen"] in (START_FEN, AFTER_E4_FEN)
        miss = a_miss(fresh)
        second.send_json({"type": "move", "from": miss[:2], "to": miss[2:]})
        assert second.receive_json()["verdict"] == "miss"
        assert second.receive_json()["type"] == "round_over"
    # Only the fresh round that ended committed; the pass of the abandoned one never did.
    assert [len(r["path"]) for r in store.implicit().round_log()] == [
        1 if fresh["side"] == "white" else 2
    ]
    assert store.implicit().record(START).passes == 0
    assert store.implicit().record(E4_E5_AFTER_E4).passes == 0


def test_reset_all_history_asks_for_confirmation_then_deletes_every_record() -> None:
    store = Store.in_memory()
    with TestClient(create_app(E4_E5, rng=random.Random(1), store=store)) as client:
        a_round_passing_at_start(client)
        confirm = client.get("/settings/reset")
        assert confirm.status_code == 200
        assert 'action="/settings/reset"' in confirm.text
        assert any(store.implicit().record(e) != Record() for e in (START, E4_E5_AFTER_E4))
        done = client.post("/settings/reset", follow_redirects=False)
    assert done.status_code == 303
    assert store.implicit().record(START) == Record()
    assert store.implicit().record(E4_E5_AFTER_E4) == Record()
    assert len(store.implicit().round_log()) == 1
    assert len(store.implicit().daily_scores()) == 1


def test_a_reset_survives_the_process(tmp_path: Path) -> None:
    store = Store.open(tmp_path)
    with TestClient(create_app(E4_E5, rng=random.Random(1), store=store)) as client:
        a_round_passing_at_start(client)
        client.post("/settings/reset")
    store.close()
    store = Store.open(tmp_path)
    assert store.implicit().record(START) == Record()
    assert store.implicit().record(E4_E5_AFTER_E4) == Record()


def test_the_stored_settings_build_the_repertoire_at_start() -> None:
    store = Store.in_memory()
    store.implicit().set_setting("width_player", 1)
    store.implicit().set_setting("h0", 3600.0)
    app = create_app(E4_E5, store=store)
    assert app.state.session.steering.repertoire.settings.width_player == 1
    assert app.state.session.steering.params.h0 == 3600.0


def test_the_play_page_links_to_the_settings_outside_the_board(graph: Graph) -> None:
    with TestClient(create_app(graph)) as client:
        page = client.get("/").text
    assert 'href="/settings"' in page
    assert page.index('href="/settings"') < page.index('class="board"')
