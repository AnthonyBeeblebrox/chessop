import json
import random
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.graph import FIXTURE_SNAPSHOT, Graph, load_graph


@pytest.fixture
def graph() -> Graph:
    return load_graph(FIXTURE_SNAPSHOT)


@pytest.fixture(params=[1, 2, 3, 4, 5, 6])
def client(request: pytest.FixtureRequest, graph: Graph) -> Iterator[TestClient]:
    """A test client over the fixture graph; the seeds give rounds of both sides."""
    with TestClient(create_app(graph, rng=random.Random(request.param))) as c:
        yield c


# Where Scaleway Transactional Email takes the messages to send, in its Paris region.
PATH = "/transactional-email/v1alpha1/regions/fr-par/emails"


@dataclass
class Posted:
    """One request the endpoint received."""

    path: str
    headers: dict[str, str]
    body: dict


@dataclass
class Endpoint:
    """Scaleway's email API, stubbed: what it received, oldest first. It answers `status`, and
    only once `answer` is set; `arrived` is set by a request, `replied` by its answer."""

    url: str
    received: list[Posted] = field(default_factory=list)
    status: int = 200
    answer: threading.Event = field(default_factory=threading.Event)
    arrived: threading.Event = field(default_factory=threading.Event)
    replied: threading.Event = field(default_factory=threading.Event)


@pytest.fixture
def endpoint(monkeypatch: pytest.MonkeyPatch) -> Iterator[Endpoint]:
    """Scaleway's email API, stubbed, where every Scaleway mailer made from now on posts."""
    stub: Endpoint

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
            headers = {name.lower(): value for name, value in self.headers.items()}
            stub.received.append(Posted(self.path, headers, body))
            stub.arrived.set()
            stub.answer.wait(10)
            self.send_response(stub.status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"emails": []}')
            stub.replied.set()

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    stub = Endpoint(f"http://127.0.0.1:{server.server_address[1]}{PATH}")
    monkeypatch.setattr("chessop.mail.TEM_URL", stub.url)
    stub.answer.set()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield stub
    finally:
        stub.answer.set()
        server.shutdown()
        server.server_close()
