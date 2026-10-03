"""A snapshot version change (spec §3.3): regenerate, record the version, keep every record, tell
the learner once on the play page and once on the progress view."""

import random
from dataclasses import replace
from urllib.parse import quote

from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.memory import Record
from chessop.repertoire import START
from chessop.score import Scores
from chessop.session import snapshot_notice
from chessop.store import MOVED_FROM_BAND, RoundEnd, Store
from graphs import epd_after, graph_of

E4_E5 = graph_of({"e4": 6000, "e4 e5": 3000}, {"e4 e5": "King's Pawn Game"})
NEW = replace(E4_E5, version="2026-10/1500-1800/abc/2")


def played_before(version: str) -> Store:
    """A store holding one missed round at the start, drilled from snapshot `version`."""
    store = Store.in_memory()
    store.implicit().set_snapshot_version(version)
    store.implicit().commit(
        RoundEnd(
            started_at=1.0,
            ended_at=2.0,
            side="white",
            path=["d2d4"],
            outcome="miss",
            end_epd=START,
            verdicts={START: ("miss", 2.0)},
            before={},
            snapshot_version=version,
        ),
        lambda record: Scores(0.0, 0.0, 0.0),
    )
    return store


def test_the_loaded_version_is_recorded_and_shown_read_only_in_settings() -> None:
    store = Store.in_memory()
    with TestClient(create_app(NEW, store=store)) as client:
        page = client.get("/settings").text
    assert store.implicit().snapshot_version == "2026-10/1500-1800/abc/2"
    assert "2026-10/1500-1800/abc/2" in page
    assert 'name="snapshot_version"' not in page


def test_a_first_start_records_the_version_and_tells_nothing() -> None:
    with TestClient(create_app(NEW, store=Store.in_memory())) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["notice"] is None
        assert "snapshot" not in client.get("/progress").text.lower()


def test_a_version_change_keeps_every_record_and_the_round_log() -> None:
    store = played_before("old")
    record = store.implicit().record(START)
    create_app(NEW, store=store)
    assert store.implicit().snapshot_version == NEW.version
    assert store.implicit().record(START) == record != Record()
    assert [row["snapshot_version"] for row in store.implicit().round_log()] == ["old"]


def test_a_version_change_is_told_once_on_the_play_page() -> None:
    store = played_before("old")
    with TestClient(create_app(NEW, rng=random.Random(1), store=store)) as client:
        with client.websocket_connect("/ws") as first:
            notice = first.receive_json()["notice"]
            first.send_json({"type": "next"})
            assert first.receive_json()["notice"] is None
        with client.websocket_connect("/ws") as second:
            assert second.receive_json()["notice"] is None
    assert "old" in notice and NEW.version in notice


def test_a_version_change_is_told_once_on_the_progress_view() -> None:
    store = played_before("old")
    with TestClient(create_app(NEW, store=store)) as client:
        first = client.get("/progress").text
        second = client.get("/progress").text
    assert NEW.version in first and "old" in first
    assert NEW.version not in second


def test_each_surface_tells_it_once_whichever_is_visited_first() -> None:
    store = played_before("old")
    with TestClient(create_app(NEW, store=store)) as client:
        client.get("/progress")
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["notice"] is not None


def test_the_next_start_on_the_same_version_tells_nothing() -> None:
    store = played_before("old")
    create_app(NEW, store=store)
    with TestClient(create_app(NEW, store=store)) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["notice"] is None
        assert NEW.version not in client.get("/progress").text


def test_the_change_is_told_once_to_each_learner_of_one_store() -> None:
    store = Store.in_memory()
    ann, bob, new = store.create_learner(1.0), store.create_learner(1.0), store.create_learner(1.0)
    ann.set_snapshot_version("old")
    bob.set_snapshot_version("old")
    assert "old" in (snapshot_notice(ann, NEW.version) or "")
    assert snapshot_notice(ann, NEW.version) is None  # told: bob still is not
    assert "old" in (snapshot_notice(bob, NEW.version) or "")
    assert snapshot_notice(bob, NEW.version) is None
    assert snapshot_notice(new, NEW.version) is None  # a first visit: nothing changed for them
    assert (ann.snapshot_version, bob.snapshot_version, new.snapshot_version) == (NEW.version,) * 3


def test_a_dormant_record_returns_when_a_later_snapshot_restores_its_position() -> None:
    after_e4_e5 = epd_after("e4", "e5")
    with_it = graph_of({"e4": 6000, "e4 e5": 3000, "e4 e5 Nf3": 2000})
    without_it = replace(graph_of({"e4": 6000}), version="2026-10/dropped")
    store = Store.in_memory()
    with (
        TestClient(create_app(with_it, rng=random.Random(1), store=store)) as client,
        client.websocket_connect("/ws") as ws,
    ):
        while ws.receive_json()["side"] != "white":
            ws.send_json({"type": "next"})
        ws.send_json({"type": "move", "from": "e2", "to": "e4"})
        ws.receive_json()
        ws.send_json({"type": "move", "from": "a2", "to": "a3"})  # a miss after 1.e4 e5
        ws.receive_json()
    record = store.implicit().record(after_e4_e5)
    assert record.misses == 1
    href = f"/progress/position/{quote(after_e4_e5, safe='')}"
    with TestClient(create_app(without_it, store=store)) as client:
        assert client.get(href).status_code == 404  # dormant: out of the repertoire
        assert store.implicit().record(after_e4_e5) == record
    restored = replace(with_it, version="2026-11/restored")
    with TestClient(create_app(restored, store=store)) as client:
        page = client.get(href)
    assert page.status_code == 200 and "(relearning pass owed)" in page.text
    assert store.implicit().record(after_e4_e5) == record


def moved_off_the_old_default() -> Store:
    """A store whose local learner the migration moved from 1500-1800 to 1500+."""
    store = played_before(NEW.version)
    store.implicit().set_setting(MOVED_FROM_BAND, "1500-1800")
    return store


def test_a_learner_moved_to_1500_plus_is_told_once_and_keeps_every_record() -> None:
    store = moved_off_the_old_default()
    record = store.implicit().record(START)
    with TestClient(create_app(NEW, store=store)) as client:
        with client.websocket_connect("/ws") as ws:
            notice = ws.receive_json()["notice"]
        first = client.get("/progress").text
        assert "1500-1800" not in client.get("/progress").text
    assert "1500+" in notice and "1500-1800" in notice and "regenerated" in notice
    assert "1500-1800" in first
    assert store.implicit().record(START) == record != Record()
    with TestClient(create_app(NEW, store=store)) as client:  # the next start: nothing
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["notice"] is None
        assert "1500-1800" not in client.get("/progress").text


def test_the_move_is_told_with_a_snapshot_change_in_one_notice() -> None:
    store = played_before("old")
    store.implicit().set_setting(MOVED_FROM_BAND, "1500-1800")
    with TestClient(create_app(NEW, store=store)) as client, client.websocket_connect("/ws") as ws:
        notice = ws.receive_json()["notice"]
    assert "1500-1800" in notice and "old" in notice and NEW.version in notice


def test_the_move_is_not_told_while_another_band_is_drilled() -> None:
    store = moved_off_the_old_default()
    closed = replace(NEW, band="1500-1800")  # a snapshot built before the open bands
    with TestClient(create_app(closed, store=store)) as c, c.websocket_connect("/ws") as ws:
        assert ws.receive_json()["notice"] is None
    with TestClient(create_app(NEW, store=store)) as c, c.websocket_connect("/ws") as ws:
        assert "1500-1800" in ws.receive_json()["notice"]
