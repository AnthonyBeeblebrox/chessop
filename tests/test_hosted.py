"""Hosted mode (public spec §1, §3, §4): many learners on one server, each an anonymous learner
behind one cookie. Driven through the app factory with a hosted-settings object, as a browser
would; the store is looked at only to count the learners it holds."""

import base64
import hashlib
import random
import re
import sqlite3
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.graph import Graph
from chessop.hosted import Hosted
from chessop.lichess import LichessIdentity
from chessop.mail import Message
from chessop.repertoire import START
from chessop.store import FILENAME, Store
from test_settings import valid_form
from test_timezone import AFTER, BEFORE, ZONE, ManualClock, machine_in_utc
from test_wire import E4_E5, play

__all__ = ["machine_in_utc"]  # the fixture, used by name

NOW = 1_800_000_000.0
MINUTE, DAY = 60.0, 86400.0
HOSTED = Hosted(
    base_url="https://chessop.example",
    mail_from="login@chessop.example",
    owner_email="owner@chessop.example",
)
PAGES = ("/", "/play", "/progress", "/settings", "/help", "/progress?never=1")


class Outbox:
    """A mailer that sends nothing: the messages handed to it, oldest first."""

    def __init__(self) -> None:
        self.sent: list[Message] = []

    def send(self, message: Message) -> None:
        self.sent.append(message)


class FakeLichess:
    """Lichess as the site reaches it, with nothing sent anywhere: `calls` is every call made
    to it, oldest first, and `live` the tokens it gave that were not revoked."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.live: dict[str, LichessIdentity] = {}
        self.issued: list[str] = []  # every token it ever gave
        self._codes: dict[str, tuple[str, LichessIdentity]] = {}

    def authorise(self, username: str, challenge: str) -> str:
        """The person called `username` agrees to the request carrying `challenge`: the code
        Lichess sends them back with."""
        code = f"code-{len(self._codes)}-{len(self.calls)}"
        self._codes[code] = (challenge, LichessIdentity(username.lower(), username))
        return code

    def token(self, code: str, verifier: str, redirect_uri: str, client_id: str) -> str | None:
        self.calls.append(("token", code, redirect_uri, client_id))
        challenge, account = self._codes.pop(code, ("", None))
        digest = hashlib.sha256(verifier.encode()).digest()
        s256 = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        if account is None or len(verifier) < 43 or s256 != challenge:
            return None
        token = f"lio_secret{len(self.issued)}"
        self.issued.append(token)
        self.live[token] = account
        return token

    def account(self, token: str) -> LichessIdentity | None:
        self.calls.append(("account", token))
        return self.live.get(token)

    def revoke(self, token: str) -> None:
        self.calls.append(("revoke", token))
        self.live.pop(token, None)


class Site:
    """A hosted chessop over `graph` (the 1.e4 e5 one unless given) on a store in `data_dir`,
    its clock, the mail it sent and the Lichess it reaches. `load_band` loads its other bands."""

    def __init__(
        self,
        data_dir: Path,
        hosted: Hosted = HOSTED,
        graph: Graph = E4_E5,
        load_band: Callable[[str], Graph] | None = None,
    ) -> None:
        self.data_dir = data_dir
        self.clock = ManualClock(NOW)
        self.outbox = Outbox()
        self.lichess = FakeLichess()
        self.url = hosted.base_url
        self.app = create_app(
            graph,
            rng=random.Random(1),
            store=Store.open(data_dir),
            load_band=load_band,
            clock=self.clock,
            hosted=hosted,
            mailer=self.outbox,
            lichess=self.lichess,
        )

    def browser(self, ip: str = "203.0.113.7") -> TestClient:
        """A browser with no cookie yet, at the address `ip`."""
        return TestClient(self.app, base_url=self.url, client=(ip, 50000))

    def learners(self) -> int:
        """How many learners the store holds."""
        db = sqlite3.connect(self.data_dir / FILENAME)
        try:
            return db.execute("SELECT COUNT(*) FROM learner").fetchone()[0]
        finally:
            db.close()


def set_cookies(ws) -> list[str]:
    """The cookies the socket's acceptance set."""
    return [v.decode() for k, v in ws.extra_headers or [] if k.lower() == b"set-cookie"]


def token(browser: TestClient) -> str:
    """The value of the browser's cookie."""
    (value,) = {cookie.value for cookie in browser.cookies.jar if cookie.name == "chessop"}
    assert value is not None
    return value


def open_socket(browser: TestClient):
    """The play page's socket, the browser keeping the cookie its acceptance sets."""
    ws = browser.websocket_connect(str(browser.base_url.copy_with(scheme="wss", path="/ws")))
    ws.__enter__()
    for cookie in set_cookies(ws):
        name, _, value = cookie.split(";")[0].partition("=")
        browser.cookies.delete(name)
        browser.cookies.set(name, value, domain=browser.base_url.host)
    return ws


MOVES = {("white", True): "e2e4", ("white", False): "a2a3"} | {
    ("black", True): "e7e5",
    ("black", False): "a7a6",
}


def end_round(ws, start: dict, *, success: bool = False) -> dict:
    """End the round `start` began, with a main move or a miss: its `round_over`."""
    return play(ws, MOVES[start["side"], success])[1]


def play_a_round(browser: TestClient, *, success: bool = False) -> dict:
    """One round on a fresh socket: its `round` message."""
    ws = open_socket(browser)
    try:
        start = ws.receive_json()
        end_round(ws, start, success=success)
    finally:
        ws.__exit__(None, None, None)
    return start


def test_viewing_pages_sets_no_cookie_and_creates_no_learner(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        for page in PAGES:
            response = browser.get(page)
            assert response.status_code == 200, page
            assert "set-cookie" not in response.headers, page
        assert not browser.cookies
    assert site.learners() == 0


def test_the_first_round_creates_the_learner_and_sets_the_cookie(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        ws = browser.websocket_connect("/ws")
        with ws:
            assert ws.receive_json()["type"] == "round"
            (cookie,) = set_cookies(ws)
        assert site.learners() == 1
    name_value, *attributes = cookie.split("; ")
    assert name_value.startswith("chessop=") and len(name_value) > len("chessop=") + 20
    assert sorted(attributes) == [
        "HttpOnly",
        "Max-Age=31536000",
        "Path=/",
        "SameSite=Lax",
        "Secure",
    ]


def hosted_form(**overrides: str) -> dict[str, str]:
    """The settings form as a hosted page submits it: no memory-model field."""
    form = {k: v for k, v in valid_form().items() if k not in PARAMS}
    return {**form, "timezone": "", **overrides}


PARAMS = ("h0", "h_min", "h_max", "sure", "floor", "C", "alpha", "forced_rate", "side_floor")


def test_saving_settings_creates_the_learner_and_sets_the_cookie(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        refused = browser.post("/settings", data=hosted_form(width_player="0"))
        assert refused.status_code == 400 and "set-cookie" not in refused.headers
        assert site.learners() == 0  # nothing was saved
        saved = browser.post(
            "/settings", data=hosted_form(width_player="1"), follow_redirects=False
        )
        assert saved.status_code == 303
        assert saved.headers["set-cookie"].startswith("chessop=")
        assert site.learners() == 1
        assert 'name="width_player" value="1"' in browser.get("/settings").text
        assert site.learners() == 1  # the cookie is theirs from now on


def test_toggling_an_opening_creates_the_learner_and_sets_the_cookie(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        unknown = browser.post("/progress/opening/No%20Such%20Opening/toggle")
        assert unknown.status_code == 404 and site.learners() == 0
        toggled = browser.post(
            "/progress/opening/King%27s%20Pawn%20Game/toggle", follow_redirects=False
        )
        assert toggled.status_code in (303, 400)  # refused when it would empty the repertoire
        assert toggled.headers["set-cookie"].startswith("chessop=")
        assert site.learners() == 1


def session_line(page: str) -> str:
    """What the progress page says of this session's rounds."""
    found = re.search(r"this session</a></span>\s*<b[^>]*>([^<]*)</b>", page)
    assert found is not None
    return found.group(1)


def test_two_browsers_are_two_learners_with_their_own_history_and_settings(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as ann, site.browser() as bob:
        play_a_round(ann, success=True)
        play_a_round(bob)
        play_a_round(bob)
        assert site.learners() == 2
        assert session_line(ann.get("/progress").text).startswith("1/1 rounds")
        assert session_line(bob.get("/progress").text).startswith("0/2 rounds")
        ann.post("/settings", data=hosted_form(width_player="1", sound=""))
        assert 'name="width_player" value="1"' in ann.get("/settings").text
        assert 'data-sound="false"' in ann.get("/play").text
        assert 'name="width_player" value="2"' in bob.get("/settings").text
        assert 'data-sound="true"' in bob.get("/play").text
        assert site.learners() == 2


def test_a_settings_change_restarts_that_learners_tabs_only(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as ann, site.browser() as bob:
        tab1, tab2, bobs = open_socket(ann), open_socket(ann), open_socket(bob)
        try:
            for tab in (tab1, tab2):
                assert tab.receive_json()["type"] == "round"
            bob_start = bobs.receive_json()
            assert site.learners() == 2  # ann's two tabs are one learner's
            assert ann.post("/settings", data=hosted_form(width_player="1")).status_code == 200
            for tab in (tab1, tab2):
                assert tab.receive_json()["type"] == "round"  # a fresh round
            # Bob's round goes on: the next thing his tab hears is the answer to his move.
            assert end_round(bobs, bob_start)["type"] == "round_over"
        finally:
            for tab in (tab1, tab2, bobs):
                tab.__exit__(None, None, None)


def test_the_cookie_drops_secure_on_an_http_base_url(tmp_path: Path) -> None:
    site = Site(tmp_path, replace(HOSTED, base_url="http://localhost:8000"))
    with site.browser() as browser, browser.websocket_connect("/ws") as ws:
        (cookie,) = set_cookies(ws)
    assert sorted(cookie.split("; ")[1:]) == [
        "HttpOnly",
        "Max-Age=31536000",
        "Path=/",
        "SameSite=Lax",
    ]


def test_the_cookie_lasts_twelve_months_from_the_last_visit(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        play_a_round(browser, success=True)
        first = token(browser)
        assert "set-cookie" not in browser.get("/progress").headers  # the same day
        site.clock.now += 200 * DAY
        again = browser.get("/progress")
        assert again.headers["set-cookie"].startswith(f"chessop={first}; ")
        assert "Max-Age=31536000" in again.headers["set-cookie"]
        site.clock.now += 300 * DAY  # 500 days after the first round, 300 after the last visit
        assert "1 day" in browser.get("/progress").text  # their daily Score is still theirs
        site.clock.now += 366 * DAY
        gone = browser.get("/progress")
        assert "set-cookie" not in gone.headers and "1 day" not in gone.text
        assert site.learners() == 1
        play_a_round(browser)  # a fresh anonymous learner
        assert site.learners() == 2 and token(browser) != first


def test_progress_lives_in_this_browser_is_told_once_after_the_first_round(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        ws = open_socket(browser)
        try:
            start = ws.receive_json()
            assert start["notice"] is None  # not before a round is played
            assert "on this browser only" not in browser.get("/progress").text
            end_round(ws, start)
            ws.send_json({"type": "next"})
            second = ws.receive_json()
            assert "progress is kept on this browser only" in second["notice"]
            end_round(ws, second)
            ws.send_json({"type": "next"})
            assert ws.receive_json()["notice"] is None
        finally:
            ws.__exit__(None, None, None)
        assert "on this browser only" not in browser.get("/progress").text
        site.clock.now += 31 * MINUTE  # the session is dropped: still told once only
        assert play_a_round(browser)["notice"] is None
        assert "on this browser only" not in browser.get("/progress").text


def test_the_notice_shows_on_progress_when_that_is_visited_first(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        play_a_round(browser)
        assert "progress is kept on this browser only" in browser.get("/progress").text
        assert "on this browser only" not in browser.get("/progress").text
        assert play_a_round(browser)["notice"] is None


def counts(page: str) -> str:
    """The known / learning / never passed counts of the progress page."""
    found = re.search(r"<b>(\d+) / (\d+) / <a [^>]*>(\d+)</a></b>", page)
    assert found is not None
    return "/".join(found.groups())


def test_a_session_is_dropped_after_thirty_idle_minutes_and_reloads_from_the_store(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        fresh = counts(browser.get("/progress").text)
        play_a_round(browser, success=True)
        site.clock.now += 29 * MINUTE
        page = browser.get("/progress").text
        assert session_line(page).startswith("1/1 rounds")
        assert (played := counts(page)) != fresh
        site.clock.now += 29 * MINUTE  # 29 minutes after the last request: still the session
        assert session_line(browser.get("/progress").text).startswith("1/1 rounds")
        site.clock.now += 31 * MINUTE
        page = browser.get("/progress").text
        assert session_line(page) == "no rounds yet"  # "this session" counts from its start
        assert counts(page) == played  # the history came back from the store


def test_a_session_with_an_open_socket_is_not_dropped(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as other:
        ws = open_socket(browser)
        try:
            end_round(ws, ws.receive_json(), success=True)
            site.clock.now += 45 * MINUTE
            other.get("/progress")  # someone else's request, a moment sessions are swept at
            assert session_line(browser.get("/progress").text).startswith("1/1 rounds")
        finally:
            ws.__exit__(None, None, None)


def test_hosted_settings_show_no_model_parameters_and_take_none(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        page = browser.get("/settings").text
        assert "Memory model" not in page
        for name in PARAMS:
            assert f'name="{name}"' not in page
        assert 'name="width_player"' in page and 'name="timezone"' in page
        assert "recall estimate is 90 % or more" in browser.get("/help").text
        saved = browser.post("/settings", data={**hosted_form(), "sure": "0.5", "h0": "1"})
        assert saved.status_code == 200 and "Saved." in saved.text
        # The server's threshold stands.
        assert "recall estimate is 90 % or more" in browser.get("/help").text


FOOTER = (
    '<footer class="site"><a href="/legal">Legal notice</a> · <a href="/privacy">Privacy</a>'
    ' · <a href="/data">Your data</a>'
    ' · <a href="https://github.com/AnthonyBeeblebrox/chessop">Source</a>'
    '<a class="kofi" href="https://ko-fi.com/chessop">'
)


def test_every_hosted_page_carries_the_footer(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        pages = (*PAGES, "/settings/reset", "/progress/position/" + quote(START, safe=""))
        for page in pages:
            response = browser.get(page)
            assert response.status_code == 200, page
            assert FOOTER in response.text, page


def test_local_mode_has_no_footer_no_cookie_and_no_hosted_route() -> None:
    with TestClient(create_app(E4_E5)) as browser:
        for page in PAGES:
            response = browser.get(page)
            assert "<footer" not in response.text and "Legal notice" not in response.text, page
            assert "set-cookie" not in response.headers, page
        with browser.websocket_connect("/ws") as ws:
            start = ws.receive_json()
            assert not set_cookies(ws)
            end_round(ws, start)
            ws.send_json({"type": "next"})
            assert ws.receive_json()["notice"] is None  # no "this browser" notice either
        assert "set-cookie" not in browser.post("/settings", data=valid_form()).headers
        assert 'name="h0"' in browser.get("/settings").text
        for path in ("/legal", "/privacy", "/data", "/signin", "/account", "/robots.txt"):
            assert browser.get(path).status_code == 404, path
        assert browser.get("/signin/confirm?token=t").status_code == 404
        for path in ("/signin", "/signin/code", "/signin/confirm", "/signout"):
            assert browser.post(path, data={"email": "ann@example.org"}).status_code == 404
        assert "Sign in" not in browser.get("/progress").text


@pytest.mark.usefixtures("machine_in_utc")
def test_a_hosted_learners_day_follows_the_time_zone_their_browser_reports(
    tmp_path: Path,
) -> None:
    """Rounds either side of Auckland's midnight, one day on the UTC server, land on two days."""
    site = Site(tmp_path)
    with site.browser() as browser:
        site.clock.now = BEFORE
        ws = open_socket(browser)
        try:
            ws.send_json({"type": "hello", "tz": ZONE})
            end_round(ws, ws.receive_json())
            site.clock.now = AFTER
            ws.send_json({"type": "next"})
            end_round(ws, ws.receive_json())
        finally:
            ws.__exit__(None, None, None)
        assert 'aria-label="daily Score, 2 days"' in browser.get("/progress").text
        assert f'name="timezone" value="{ZONE}"' in browser.get("/settings").text
