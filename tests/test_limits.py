"""The hosted site's limits (public spec §6): one abusive client cannot exhaust the box. Driven
through the app factory as a browser would, the clock moved by hand; local mode has none."""

import json
from contextlib import ExitStack
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from chessop.app import create_app
from chessop.store import Store
from test_hosted import (
    MINUTE,
    NOW,
    Site,
    end_round,
    hosted_form,
    open_socket,
    play_a_round,
    session_line,
    set_cookies,
)
from test_settings import valid_form
from test_signin import sign_in
from test_timezone import ManualClock
from test_wire import E4_E5

# Opting an opening out of the drill, from the progress view.
TOGGLE = "/progress/opening/King%27s%20Pawn%20Game/toggle"
SLOW_DOWN = "Slow down: try again in {} seconds."


def assert_slowed(response, seconds: int) -> None:
    """`response` is the 429 that asks to wait `seconds`."""
    assert response.status_code == 429
    assert response.headers["retry-after"] == str(seconds)
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == SLOW_DOWN.format(seconds)


def test_past_120_requests_a_minute_an_ip_is_asked_to_slow_down_until_the_minute_passes(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser(ip="198.51.100.1") as browser, site.browser(ip="198.51.100.2") as other:
        for _ in range(60):
            assert browser.get("/help").status_code == 200
        site.clock.now += 20
        for _ in range(60):
            assert browser.get("/progress").status_code == 200
        assert_slowed(browser.get("/settings"), 40)
        assert other.get("/help").status_code == 200  # another client
        site.clock.now += 40  # the first 60 leave the window
        assert browser.get("/help").status_code == 200


def test_the_health_check_and_the_static_files_are_never_limited(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        for _ in range(120):
            assert browser.get("/help").status_code == 200
        assert browser.get("/help").status_code == 429
        for _ in range(130):
            assert browser.get("/healthz").status_code == 200
            assert browser.head("/healthz").status_code == 200
            assert browser.get("/static/play.css").status_code == 200


def test_two_ipv6_addresses_in_one_64_are_one_client(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with (
        site.browser(ip="2001:db8:0:1::1") as one,
        site.browser(ip="2001:db8:0:1:ffff::2") as two,
        site.browser(ip="2001:db8:0:2::1") as next_64,
    ):
        for _ in range(60):
            assert one.get("/help").status_code == 200
            assert two.get("/help").status_code == 200
        assert one.get("/help").status_code == 429
        assert two.get("/help").status_code == 429
        assert next_64.get("/help").status_code == 200


def test_local_mode_limits_no_request(tmp_path: Path) -> None:
    with TestClient(create_app(E4_E5, store=Store.open(tmp_path), clock=ManualClock(NOW))) as c:
        for _ in range(200):
            assert c.get("/help").status_code == 200


def save(browser: TestClient):
    """Save the settings form as it stands: the answer, not followed."""
    return browser.post("/settings", data=hosted_form(), follow_redirects=False)


def test_past_10_settings_saves_a_minute_a_learner_is_asked_to_slow_down(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as other:
        play_a_round(browser)
        play_a_round(other)
        for n in range(10):
            site.clock.now += 1
            assert save(browser).status_code == 303
            if n == 0:
                assert save(other).status_code == 303
        assert_slowed(save(browser), 51)
        # Opting an opening out is a settings save too.
        assert_slowed(browser.post(TOGGLE, follow_redirects=False), 51)
        assert save(other).status_code == 303  # another learner
        site.clock.now += 51
        assert save(browser).status_code == 303


def test_past_5_data_downloads_an_hour_a_learner_is_asked_to_slow_down(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as other:
        play_a_round(browser)
        play_a_round(other)
        for _ in range(5):
            assert browser.get("/data/download").status_code == 200
            site.clock.now += 10 * MINUTE
        assert_slowed(browser.get("/data/download"), 600)
        assert other.get("/data/download").status_code == 200  # another learner
        site.clock.now += 10 * MINUTE
        assert browser.get("/data/download").status_code == 200


def ask_next(ws, size: int | None = None) -> None:
    """Ask for the next round, the message padded to `size` bytes."""
    message = {"type": "next"}
    if size is not None:
        message["pad"] = ""
        message["pad"] = "x" * (size - len(json.dumps(message)))
    ws.send_text(json.dumps(message))


def next_round(ws, size: int | None = None) -> None:
    """Ask for the next round, the message padded to `size` bytes, and take it."""
    ask_next(ws, size)
    assert ws.receive_json()["type"] == "round"


def assert_closed_for_policy(ws, send) -> None:
    """Sending with `send` has the server close the socket with code 1008."""
    with pytest.raises(WebSocketDisconnect) as closed:
        send()
        ws.receive_json()
    assert closed.value.code == 1008


def test_a_socket_sending_more_than_a_burst_of_20_then_5_a_second_is_closed(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, browser.websocket_connect("/ws") as ws:
        ws.receive_json()
        for _ in range(20):
            next_round(ws)
        site.clock.now += 1
        for _ in range(5):
            next_round(ws)
        assert_closed_for_policy(ws, lambda: ask_next(ws))


def test_a_socket_sending_a_message_over_1_kb_is_closed(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, browser.websocket_connect("/ws") as ws:
        ws.receive_json()
        next_round(ws, 1024)
        assert_closed_for_policy(ws, lambda: ask_next(ws, 1025))


def test_local_mode_limits_no_socket_message(tmp_path: Path) -> None:
    app = create_app(E4_E5, store=Store.open(tmp_path), clock=ManualClock(NOW))
    with TestClient(app) as c, c.websocket_connect("/ws") as ws:
        ws.receive_json()
        for _ in range(30):
            next_round(ws, 2000)


def socket_url(browser: TestClient) -> str:
    """The play page's socket address, at which the browser sends its cookie."""
    return str(browser.base_url.copy_with(scheme="wss", path="/ws"))


def open_sockets(stack: ExitStack, browser: TestClient, n: int) -> list:
    """Open `n` of the browser's play-page sockets, each past its first round message."""
    sockets = []
    for _ in range(n):
        ws = stack.enter_context(browser.websocket_connect(socket_url(browser)))
        assert ws.receive_json()["type"] == "round"
        sockets.append(ws)
    return sockets


def assert_refused(browser: TestClient) -> None:
    with (
        pytest.raises(WebSocketDisconnect) as refused,
        browser.websocket_connect(socket_url(browser)),
    ):
        pass
    assert refused.value.code == 1008


def test_a_learners_11th_socket_is_refused_until_one_closes(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as other, ExitStack() as stack:
        play_a_round(browser)
        first, *_ = open_sockets(stack, browser, 10)
        assert_refused(browser)
        open_sockets(stack, other, 1)  # another learner, at the same address
        first.close()
        open_sockets(stack, browser, 1)


def test_an_ips_41st_socket_is_refused(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with ExitStack() as stack:
        browsers = [stack.enter_context(site.browser(ip="198.51.100.1")) for _ in range(5)]
        for browser in browsers[:4]:
            play_a_round(browser)
            open_sockets(stack, browser, 10)
        assert_refused(browsers[4])
        open_sockets(stack, stack.enter_context(site.browser(ip="198.51.100.2")), 1)


def test_local_mode_limits_no_open_socket(tmp_path: Path) -> None:
    app = create_app(E4_E5, store=Store.open(tmp_path), clock=ManualClock(NOW))
    with TestClient(app) as c, ExitStack() as stack:
        open_sockets(stack, c, 45)


def test_local_mode_limits_no_settings_save(tmp_path: Path) -> None:
    with TestClient(create_app(E4_E5, store=Store.open(tmp_path), clock=ManualClock(NOW))) as c:
        for _ in range(15):
            saved = c.post("/settings", data=valid_form(), follow_redirects=False)
            assert saved.status_code == 303


FULL = "chessop is full right now, try again in a few minutes"
THROWAWAY = (
    "Too many new visitors from your network: this round won't be saved. Try again later or"
    " sign in."
)
THROWAWAY_HTML = THROWAWAY.replace("'", "&#39;")


def crowd(site: Site, stack: ExitStack, n: int) -> list[TestClient]:
    """`n` browsers, each at its own address, each with a live learner session."""
    browsers = []
    for i in range(n):
        browser = stack.enter_context(site.browser(ip=f"10.1.{i // 250}.{i % 250 + 1}"))
        play_a_round(browser)
        browsers.append(browser)
    return browsers


def assert_full(browser: TestClient) -> None:
    """A page is answered 503 with the sentence, and the socket is closed with code 1013."""
    for page in ("/", "/progress", "/settings"):
        response = browser.get(page)
        assert response.status_code == 503, page
        assert response.text == FULL
    with (
        pytest.raises(WebSocketDisconnect) as refused,
        browser.websocket_connect(socket_url(browser)),
    ):
        pass
    assert refused.value.code == 1013


def test_at_300_live_sessions_a_new_one_is_refused_and_the_running_ones_go_on(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with ExitStack() as stack, site.browser(ip="10.9.9.9") as late:
        first, *_ = crowd(site, stack, 299)
        assert late.get("/").status_code == 200  # one place left: looking takes none
        returning = stack.enter_context(site.browser(ip="10.9.9.8"))
        play_a_round(returning)  # the 300th
        assert_full(late)
        assert not late.cookies and site.learners() == 300
        assert late.post("/settings", data=hosted_form()).status_code == 503
        assert late.get("/healthz").status_code == 200
        assert late.get("/signin").status_code == 200
        # The sessions already running are unaffected.
        assert play_a_round(first)["type"] == "round"
        assert first.get("/progress").status_code == 200
        # A learner whose session was dropped is a new session too.
        site.clock.now += 20 * MINUTE
        for browser in (first, late):
            browser.get("/healthz")
        play_a_round(first)
        site.clock.now += 20 * MINUTE  # 40 idle minutes for all but the first
        assert late.get("/").status_code == 200
        assert play_a_round(late)["type"] == "round"


def test_a_learner_whose_session_was_dropped_is_refused_while_the_site_is_full(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with ExitStack() as stack, site.browser(ip="10.9.9.9") as old:
        play_a_round(old)
        site.clock.now += 31 * MINUTE  # their session is dropped at the next request
        crowd(site, stack, 300)
        assert_full(old)
        assert old.get("/data").status_code == 503


def test_local_mode_has_no_session_ceiling() -> None:
    with TestClient(create_app(E4_E5, clock=ManualClock(NOW))) as c:
        assert c.get("/").status_code == 200  # one learner, never refused


def spend_the_hour(site: Site, ip: str) -> None:
    """Thirty browsers at `ip` each become an anonymous learner."""
    for _ in range(30):
        with site.browser(ip=ip) as browser:
            play_a_round(browser)


def test_the_31st_new_learner_of_an_ip_in_an_hour_plays_unsaved_with_no_cookie(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    ip = "198.51.100.1"
    spend_the_hour(site, ip)
    assert site.learners() == 30
    with site.browser(ip=ip) as browser, site.browser(ip="198.51.100.2") as elsewhere:
        ws = open_socket(browser)
        try:
            assert not set_cookies(ws)
            start = ws.receive_json()
            assert start["type"] == "round" and start["notice"] == THROWAWAY
            assert end_round(ws, start, success=True)["type"] == "round_over"
            ws.send_json({"type": "next"})
            second = ws.receive_json()
            assert second["type"] == "round" and second["notice"] == THROWAWAY
            end_round(ws, second)
        finally:
            ws.__exit__(None, None, None)
        assert not browser.cookies and site.learners() == 30
        assert session_line(browser.get("/progress").text) == "no rounds yet"  # gone
        play_a_round(elsewhere)  # another client is an anonymous learner as ever
        assert elsewhere.cookies and site.learners() == 31
        site.clock.now += 61 * MINUTE  # the hour passes
        assert play_a_round(browser)["notice"] is None
        assert browser.cookies and site.learners() == 32


def test_a_throwaway_learners_settings_and_progress_show_the_notice_and_save_nothing(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    ip = "198.51.100.1"
    spend_the_hour(site, ip)
    with site.browser(ip=ip) as browser:
        assert THROWAWAY_HTML in browser.get("/progress").text
        assert THROWAWAY_HTML in browser.get("/settings").text
        saved = browser.post(
            "/settings", data=hosted_form(width_player="1"), follow_redirects=False
        )
        assert saved.status_code == 200 and THROWAWAY_HTML in saved.text
        assert "Saved." not in saved.text and "set-cookie" not in saved.headers
        assert 'name="width_player" value="2"' in browser.get("/settings").text
        toggled = browser.post(TOGGLE, follow_redirects=False)
        assert toggled.status_code == 200 and THROWAWAY_HTML in toggled.text
        assert "set-cookie" not in toggled.headers
        assert not browser.cookies and site.learners() == 30
    with site.browser(ip="198.51.100.2") as elsewhere:
        assert THROWAWAY_HTML not in elsewhere.get("/progress").text
        assert THROWAWAY_HTML not in elsewhere.get("/settings").text


def test_learners_created_by_a_settings_save_or_a_toggle_count_in_the_30(tmp_path: Path) -> None:
    site = Site(tmp_path)
    ip = "198.51.100.1"
    for n in range(30):
        with site.browser(ip=ip) as browser:
            made = save(browser) if n % 2 else browser.post(TOGGLE, follow_redirects=False)
            assert "set-cookie" in made.headers
    assert site.learners() == 30
    with site.browser(ip=ip) as browser:
        assert play_a_round(browser)["notice"] == THROWAWAY
        assert THROWAWAY_HTML in save(browser).text
        assert not browser.cookies and site.learners() == 30


def test_a_throwaway_learner_counts_in_the_300_until_its_socket_closes(tmp_path: Path) -> None:
    site = Site(tmp_path)
    ip = "198.51.100.1"
    spend_the_hour(site, ip)
    site.clock.now += 31 * MINUTE  # those thirty sessions are dropped at the next request
    with ExitStack() as stack, site.browser(ip=ip) as browser, site.browser() as late:
        ws = open_socket(browser)
        assert ws.receive_json()["notice"] == THROWAWAY
        crowd(site, stack, 299)
        assert_full(late)
        ws.__exit__(None, None, None)
        assert play_a_round(late)["type"] == "round"


def test_a_throwaway_learner_can_still_sign_in(tmp_path: Path) -> None:
    site = Site(tmp_path)
    ip = "198.51.100.1"
    spend_the_hour(site, ip)
    with site.browser(ip=ip) as browser:
        assert play_a_round(browser)["notice"] == THROWAWAY
        sign_in(site, browser, "ann@example.org")
        assert "ann@example.org" in browser.get("/account").text
        assert play_a_round(browser, success=True)["notice"] is None  # saved from now on
        assert session_line(browser.get("/progress").text).startswith("1/1 rounds")
        assert THROWAWAY_HTML not in browser.get("/settings").text
        assert save(browser).status_code == 303
