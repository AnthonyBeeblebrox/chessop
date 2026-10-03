"""Lichess sign-in (public spec §5, ADR 0008), driven as a browser would through the hosted app,
with a fake Lichess in place of the real one."""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest
from fastapi.testclient import TestClient

from chessop.lichess import HttpLichess, LichessIdentity
from test_hosted import MINUTE, Site, counts, play_a_round, token
from test_signin import HOUR, field, who
from test_signin import sign_in as email_sign_in

CALLBACK = "/signin/lichess/callback"


def start(browser: TestClient, back: str = "/progress", **kwargs) -> tuple[str, dict[str, str]]:
    """Press "Sign in with Lichess": the address at Lichess the browser is sent to, and the
    parameters of its query."""
    response = browser.post(
        "/signin/lichess", data={"next": back}, follow_redirects=False, **kwargs
    )
    assert response.status_code == 303
    url = urlsplit(response.headers["location"])
    return f"{url.scheme}://{url.netloc}{url.path}", dict(parse_qsl(url.query))


def come_back(site: Site, browser: TestClient, asked: dict[str, str], username: str = "Ann"):
    """`username` agrees at Lichess, which sends the browser back to the site."""
    code = site.lichess.authorise(username, asked["code_challenge"])
    return browser.get(
        CALLBACK, params={"code": code, "state": asked["state"]}, follow_redirects=False
    )


def sign_in(site: Site, browser: TestClient, username: str = "Ann", back: str = "/progress"):
    return come_back(site, browser, start(browser, back)[1], username)


def test_signing_in_with_lichess_shows_the_username_in_the_header(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        page = browser.get("/signin?next=%2Fprogress").text
        assert page.index('action="/signin/lichess"') < page.index('name="email"')  # offered first
        signed = sign_in(site, browser, "Ann", back="/progress?never=1")
        assert signed.status_code == 303 and signed.headers["location"] == "/progress?never=1"
        assert who(browser) == "/account Ann"
        assert site.learners() == 1


def test_the_account_is_keyed_by_the_lichess_id_and_shown_by_the_username(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as elsewhere:
        play_a_round(browser, success=True)
        played = counts(browser.get("/progress").text)
        sign_in(site, browser, "ann")
        # The same id, its letters' case changed at Lichess: the same account, shown as it is now.
        sign_in(site, elsewhere, "Ann")
        assert counts(elsewhere.get("/progress").text) == played
        assert who(elsewhere) == "/account Ann" and who(browser) == "/account Ann"
        assert site.learners() == 1
        with site.browser() as bob:
            sign_in(site, bob, "Bob")
            assert who(bob) == "/account Bob" and counts(bob.get("/progress").text) != played


def test_lichess_is_asked_with_a_pkce_challenge_no_scope_and_the_sites_own_addresses(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        forged = {"host": "evil.example"}
        response = browser.post(
            "/signin/lichess", data={"next": "/progress"}, follow_redirects=False, headers=forged
        )
        assert "set-cookie" not in response.headers  # asking to sign in sets no cookie
        url = urlsplit(response.headers["location"])
        asked = dict(parse_qsl(url.query))
        assert f"{url.scheme}://{url.netloc}{url.path}" == "https://lichess.org/oauth"
        assert set(asked) == {
            "response_type",
            "client_id",
            "redirect_uri",
            "code_challenge_method",
            "code_challenge",
            "state",
        }  # no scope
        assert asked["response_type"] == "code" and asked["code_challenge_method"] == "S256"
        assert asked["client_id"] == "chessop.example"
        assert asked["redirect_uri"] == f"https://chessop.example{CALLBACK}"
        assert len(asked["code_challenge"]) == 43  # a SHA-256, base64url with no padding
        code = site.lichess.authorise("Ann", asked["code_challenge"])
        back = browser.get(
            CALLBACK,
            params={"code": code, "state": asked["state"]},
            follow_redirects=False,
            headers=forged,
        )
        # The fake gives a token only for the verifier of that challenge.
        assert back.status_code == 303 and back.headers["location"] == "/progress"
        assert site.lichess.calls[0] == (
            "token",
            code,
            f"https://chessop.example{CALLBACK}",
            "chessop.example",
        )


def test_the_token_is_revoked_after_the_one_account_call_and_stored_nowhere(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        assert sign_in(site, browser).status_code == 303
        (token,) = site.lichess.issued
        assert [call[0] for call in site.lichess.calls] == ["token", "account", "revoke"]
        assert site.lichess.calls[1:] == [("account", token), ("revoke", token)]
        assert not site.lichess.live
        assert who(browser) == "/account Ann"
    stored = b"".join(path.read_bytes() for path in tmp_path.iterdir() if path.is_file())
    assert b"ann" in stored and token.encode() not in stored


def test_a_token_whose_account_lichess_does_not_tell_is_revoked_all_the_same(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = Site(tmp_path)
    monkeypatch.setattr(site.lichess, "live", NoAccounts())
    with site.browser() as browser:
        refused = sign_in(site, browser)
        assert refused.status_code == 400 and "Lichess did not sign you in" in refused.text
        assert [call[0] for call in site.lichess.calls] == ["token", "account", "revoke"]
        assert who(browser).endswith("Sign in") and site.learners() == 0


class NoAccounts(dict):
    """The tokens of a Lichess that never says whose a token is."""

    def get(self, key, default=None):
        return None


def test_a_wrong_or_replayed_state_is_refused(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        _, asked = start(browser)
        wrong = come_back(site, browser, {**asked, "state": "not-the-state"})
        assert wrong.status_code == 400 and "not started here" in wrong.text
        assert site.lichess.calls == [] and who(browser).endswith("Sign in")
        assert come_back(site, browser, asked).status_code == 303
        browser.post("/signout")
        calls = len(site.lichess.calls)
        replayed = come_back(site, browser, asked)
        assert replayed.status_code == 400 and "not started here" in replayed.text
        assert len(site.lichess.calls) == calls and who(browser).endswith("Sign in")
        assert browser.get(CALLBACK).status_code == 400  # and so is none at all


def test_a_state_is_good_for_ten_minutes(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        _, asked = start(browser)
        site.clock.now += 10 * MINUTE
        assert come_back(site, browser, asked).status_code == 400
        _, asked = start(browser)
        site.clock.now += 9 * MINUTE
        assert come_back(site, browser, asked).status_code == 303


def test_a_state_is_good_only_in_the_browser_that_began(tmp_path: Path) -> None:
    """Someone who begins a sign-in and hands its way back to another browser does not get
    that browser's anonymous history into their own account."""
    site = Site(tmp_path)
    with site.browser() as mallory, site.browser() as browser:
        play_a_round(browser, success=True)
        played = counts(browser.get("/progress").text)
        _, asked = start(mallory)
        refused = come_back(site, browser, asked, "Mallory")
        assert refused.status_code == 400 and site.lichess.calls == []
        assert who(browser).endswith("Sign in")
        assert counts(browser.get("/progress").text) == played


def test_lichess_refusing_leads_back_to_the_sign_in_page(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        _, asked = start(browser, back="/progress?never=1")
        denied = browser.get(CALLBACK, params={"error": "access_denied", "state": asked["state"]})
        assert denied.status_code == 400 and "Lichess did not sign you in" in denied.text
        assert field(denied.text, "next") == "/progress?never=1"
        assert site.lichess.calls == [] and who(browser).endswith("Sign in")
        _, asked = start(browser)
        bad_code = browser.get(CALLBACK, params={"code": "made-up", "state": asked["state"]})
        assert bad_code.status_code == 400 and who(browser).endswith("Sign in")


def test_lichess_sign_in_never_leads_off_the_site(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        signed = sign_in(site, browser, back="https://evil.example/")
        assert signed.headers["location"] == "/"


def test_anonymous_history_is_adopted_as_with_email(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as second:
        play_a_round(browser, success=True)
        anonymous = token(browser)
        first = counts(browser.get("/progress").text)
        sign_in(site, browser)
        assert token(browser) != anonymous  # the cookie's token rotates
        assert site.learners() == 1 and counts(browser.get("/progress").text) == first
        # A second device with history of its own: both histories are kept.
        site.clock.now += HOUR
        play_a_round(second, success=True)
        assert site.learners() == 2
        sign_in(site, second)
        assert site.learners() == 1
        merged = second.get("/progress").text
        assert counts(merged) != first and counts(browser.get("/progress").text) == counts(merged)
        # Sign-out is the same too: the browser has no learner.
        out = second.post("/signout", follow_redirects=False)
        assert out.headers["set-cookie"].startswith("chessop=; ") and not second.cookies


def test_signing_in_with_email_afterwards_reaches_a_different_account(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        fresh = counts(browser.get("/progress").text)
        play_a_round(browser, success=True)
        sign_in(site, browser, "Ann")
        played = counts(browser.get("/progress").text)
        browser.post("/signout")
        email_sign_in(site, browser, "ann@example.org")
        assert who(browser) == "/account ann@example.org"
        assert counts(browser.get("/progress").text) == fresh != played
        assert site.learners() == 2
        browser.post("/signout")
        sign_in(site, browser, "Ann")
        assert who(browser) == "/account Ann" and counts(browser.get("/progress").text) == played


def test_the_real_client_buys_a_token_asks_whose_it_is_and_revokes_it() -> None:
    with a_lichess() as (base, seen):
        client = HttpLichess(base)
        token = client.token("the-code", "the-verifier", "https://chessop.example/cb", "chessop")
        assert token == "lio_token"
        assert client.account(token) == LichessIdentity("ann", "Ann")
        client.revoke(token)
        assert client.account("lio_revoked") is None  # refused: no error raised
    assert seen == [
        (
            "POST",
            "/api/token",
            None,
            {
                "grant_type": "authorization_code",
                "code": "the-code",
                "code_verifier": "the-verifier",
                "redirect_uri": "https://chessop.example/cb",
                "client_id": "chessop",
            },
        ),
        ("GET", "/api/account", "Bearer lio_token", {}),
        ("DELETE", "/api/token", "Bearer lio_token", {}),
        ("GET", "/api/account", "Bearer lio_revoked", {}),
    ]
    assert HttpLichess(base).token("c", "v", "r", "i") is None  # no one answers any more


@contextmanager
def a_lichess() -> Iterator[tuple[str, list]]:
    """A local server answering as Lichess does: its address and the requests it saw."""
    seen: list = []

    class Handler(BaseHTTPRequestHandler):
        def answer(self) -> None:
            body = self.rfile.read(int(self.headers.get("content-length", 0))).decode()
            authorization = self.headers.get("authorization")
            seen.append((self.command, self.path, authorization, dict(parse_qsl(body))))
            if self.command == "DELETE":
                status, answer = 204, b""
            elif self.command == "POST":
                status, answer = 200, json.dumps({"access_token": "lio_token"}).encode()
            elif authorization == "Bearer lio_token":
                account = {"id": "ann", "username": "Ann", "perfs": {}}
                status, answer = 200, json.dumps(account).encode()
            else:
                status, answer = 401, b'{"error": "No such token"}'
            self.send_response(status)
            self.send_header("content-length", str(len(answer)))
            self.end_headers()
            self.wfile.write(answer)

        do_GET = do_POST = do_DELETE = answer

        def log_message(self, format: str, *args) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
