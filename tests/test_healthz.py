"""`/healthz`: what the uptime check and the deploy script poll (public spec §12).

Served in both modes; these run the app factory as local mode runs it.
"""

from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.graph import Graph
from chessop.store import Store


def test_healthz_answers_200_on_a_healthy_app(graph: Graph) -> None:
    with TestClient(create_app(graph)) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.text == "ok"


def test_healthz_answers_a_head_request_as_uptime_checks_send(graph: Graph) -> None:
    with TestClient(create_app(graph)) as client:
        response = client.head("/healthz")
    assert response.status_code == 200


def test_healthz_fails_when_the_database_cannot_be_queried(graph: Graph) -> None:
    store = Store.in_memory()
    with TestClient(create_app(graph, store=store)) as client:
        store.close()
        response = client.get("/healthz")
    assert response.status_code == 503


def test_healthz_fails_when_no_snapshot_is_loaded(graph: Graph) -> None:
    with TestClient(create_app(graph)) as client:
        graph.positions.clear()  # the graph the app drills from no longer holds a position
        response = client.get("/healthz")
    assert response.status_code == 503
