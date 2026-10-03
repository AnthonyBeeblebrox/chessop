"""The site's mail through Scaleway Transactional Email (public spec §1, §5, G2), asserted
against a stubbed HTTP endpoint standing in for Scaleway's API."""

import logging
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.mail import MailError, Message, TemMailer
from chessop.store import Store
from conftest import PATH, Endpoint
from test_hosted import HOSTED
from test_wire import E4_E5

SECRET, PROJECT = "tem-secret-key", "tem-project-id"


def tem(endpoint: Endpoint) -> TemMailer:
    return TemMailer(SECRET, PROJECT, "login@chessop.example")


MESSAGE = Message(to="ann@example.org", subject="Sign in to chessop", body="Open this link.\n")


def test_a_delivered_message_is_posted_to_scaleway_from_the_sites_sender(
    endpoint: Endpoint,
) -> None:
    tem(endpoint).deliver(MESSAGE)
    (posted,) = endpoint.received
    assert posted.path == PATH
    assert posted.headers["x-auth-token"] == SECRET
    assert posted.headers["content-type"] == "application/json"
    assert posted.body == {
        "from": {"email": "login@chessop.example", "name": "chessop"},
        "to": [{"email": "ann@example.org"}],
        "subject": "Sign in to chessop",
        "text": "Open this link.\n",
        "project_id": PROJECT,
    }


def test_a_refused_delivery_raises(endpoint: Endpoint) -> None:
    endpoint.status = 401
    with pytest.raises(MailError, match="401"):
        tem(endpoint).deliver(MESSAGE)


def test_an_unreachable_scaleway_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("chessop.mail.TEM_URL", "http://127.0.0.1:9/nowhere")
    with pytest.raises(MailError):
        TemMailer(SECRET, PROJECT, "login@chessop.example").deliver(MESSAGE)


def site(tmp_path: Path, endpoint: Endpoint) -> TestClient:
    """A browser on the hosted site at `https://chessop.example`, mailing through `endpoint`."""
    app = create_app(E4_E5, store=Store.open(tmp_path), hosted=HOSTED, mailer=tem(endpoint))
    return TestClient(app, base_url=HOSTED.base_url)


def test_sign_in_answers_without_waiting_on_scaleway(tmp_path: Path, endpoint: Endpoint) -> None:
    endpoint.answer.clear()  # Scaleway takes the request and does not answer yet
    with site(tmp_path, endpoint) as browser:
        answered = browser.post("/signin", data={"email": "ann@example.org", "next": "/"})
        assert answered.status_code == 200 and "check your inbox" in answered.text.lower()
        assert not endpoint.replied.is_set()  # answered before Scaleway did
        assert endpoint.arrived.wait(5)
        (posted,) = endpoint.received
        assert posted.body["to"] == [{"email": "ann@example.org"}]
        assert posted.body["subject"] == "Sign in to chessop"
        assert "/signin/confirm?token=" in posted.body["text"]
        endpoint.answer.set()


def test_a_message_scaleway_refuses_is_logged_and_sign_in_still_answers(
    tmp_path: Path, endpoint: Endpoint, caplog: pytest.LogCaptureFixture
) -> None:
    endpoint.status = 500
    with site(tmp_path, endpoint) as browser, caplog.at_level(logging.ERROR):
        answered = browser.post("/signin", data={"email": "ann@example.org", "next": "/"})
        assert answered.status_code == 200 and "check your inbox" in answered.text.lower()
        assert endpoint.arrived.wait(5)
        deadline = time.monotonic() + 5
        while not caplog.records and time.monotonic() < deadline:
            time.sleep(0.01)
    (record,) = caplog.records
    assert record.levelno == logging.ERROR
    assert "Sign in to chessop" in record.getMessage() and "500" in record.getMessage()
    assert "ann@example.org" not in record.getMessage()
