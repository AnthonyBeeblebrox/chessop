"""Your data (public spec §10): the download of everything stored about the learner, and
forgetting an anonymous learner. Driven as a browser would through the hosted app, with a clock
moved by hand."""

import hashlib
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from test_hosted import MINUTE, Site, counts, end_round, open_socket, play_a_round, token
from test_lichess import sign_in as lichess_sign_in
from test_signin import ANN, ask, sign_in

PARIS = "Europe/Paris"
# The positions of the 1.e4 e5 graph, as FEN.
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
E4_FEN = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
E4_E5_FEN = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1"
AT_NOW = "2027-01-15T08:00:00Z"  # NOW in UTC
A_MINUTE_LATER = "2027-01-15T08:01:00Z"


def download(browser: TestClient) -> dict:
    """Press "Download my data" on the Your data page: the file, read."""
    page = browser.get("/data").text
    assert '<a href="/data/download">' in page
    response = browser.get("/data/download")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    return {"disposition": response.headers["content-disposition"], **response.json()}


def play_rounds(browser: TestClient, site: Site, *outcomes: bool) -> list[str]:
    """Rounds on one socket opened in Paris, a minute apart: the side of each."""
    sides = []
    ws = open_socket(browser)
    try:
        ws.send_json({"type": "hello", "tz": PARIS})
        start = ws.receive_json()
        for i, success in enumerate(outcomes):
            if i:
                site.clock.now += MINUTE
                ws.send_json({"type": "next"})
                start = ws.receive_json()
            sides.append(start["side"])
            end_round(ws, start, success=success)
    finally:
        ws.__exit__(None, None, None)
    return sides


def test_an_anonymous_learner_downloads_exactly_what_they_played(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        (side,) = play_rounds(browser, site, True)
        site.clock.now += MINUTE
        data = download(browser)
    fen = START_FEN if side == "white" else E4_FEN
    path = ["e2e4", "e7e5"]
    [day] = data.pop("daily_scores")
    assert 0 < day.pop("score") <= 1 and 0 <= day.pop("white_score") <= 1
    assert 0 <= day.pop("black_score") <= 1
    assert day == {"day": "2027-01-15", "rounds": 1, "successes": 1, "updated_at": AT_NOW}
    assert data == {
        "disposition": 'attachment; filename="chessop-data-2027-01-15.json"',
        "format_version": 1,
        "exported_at": A_MINUTE_LATER,
        "snapshot_version": "test",
        "account": None,
        "learner": {"created": AT_NOW, "last_seen": AT_NOW},
        "settings": {"timezone": PARIS},
        "position_records": [
            {"fen": fen, "passes": 1, "misses": 0, "last_pass": AT_NOW, "relearning_owed": False}
        ],
        "round_log": [
            {
                "started_at": AT_NOW,
                "ended_at": AT_NOW,
                "side": side,
                "path": path,
                "outcome": "success",
                "end_fen": E4_E5_FEN,
                "plies": 2,
                "before": {
                    fen: {"passes": 0, "misses": 0, "last_pass": None, "relearning_owed": False}
                },
                "snapshot_version": "test",
            }
        ],
    }


def test_a_signed_in_learner_downloads_their_account_and_all_their_rounds(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        sign_in(site, browser)  # at NOW
        site.clock.now += MINUTE
        sides = play_rounds(browser, site, True, False)
        data = download(browser)
    assert data["account"] == {"kind": "email", "email": ANN, "created": AT_NOW}
    assert data["learner"]["created"] == AT_NOW
    log = data["round_log"]
    assert [(r["side"], r["outcome"], r["ended_at"]) for r in log] == [
        (sides[0], "success", A_MINUTE_LATER),
        (sides[1], "miss", "2027-01-15T08:02:00Z"),
    ]
    miss = {"white": "a2a3", "black": "a7a6"}[sides[1]]
    assert log[1]["path"] == (["e2e4", miss] if sides[1] == "black" else [miss])
    [day] = data["daily_scores"]
    assert (day["rounds"], day["successes"]) == (2, 1)
    fens = {"white": START_FEN, "black": E4_FEN}
    records = {r["fen"]: (r["passes"], r["misses"]) for r in data["position_records"]}
    expected: dict[str, tuple[int, int]] = {}
    for side, passed in zip(sides, (True, False), strict=True):
        passes, misses = expected.get(fens[side], (0, 0))
        expected[fens[side]] = (passes + passed, misses + (not passed))
    assert records == expected
    relearning = {r["fen"]: r["relearning_owed"] for r in data["position_records"]}
    assert relearning[fens[sides[1]]] is True  # a miss owes a relearning pass


def test_a_lichess_account_is_downloaded_with_its_username(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        lichess_sign_in(site, browser, "Ann")
        data = download(browser)
    assert data["account"] == {"kind": "lichess", "lichess_username": "Ann", "created": AT_NOW}
    assert data["position_records"] == data["round_log"] == data["daily_scores"] == []


def keys(value: object) -> set[str]:
    """Every key of every object in `value`, however deep."""
    if isinstance(value, dict):
        return {str(k) for k in value}.union(*(keys(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(keys(v) for v in value))
    return set()


def test_the_download_holds_no_token_hash_or_estimate(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        play_rounds(browser, site, True, False, True)
        sign_in(site, browser)
        ask(browser)  # a pending sign-in, with its hashes
        cookie = token(browser)
        response = browser.get("/data/download")
    text = response.text
    assert cookie not in text and hashlib.sha256(cookie.encode()).hexdigest() not in text
    assert not re.search(r"[0-9a-f]{32}", text)
    data = json.loads(text)
    assert not {k for k in keys(data) if re.search(r"token|hash|binding|code|^R$|recall|estim", k)}
    assert len(data["round_log"]) == 3 and all(r["before"] for r in data["round_log"])


NOTHING = "Nothing is stored about this browser"
NOINDEX = '<meta name="robots" content="noindex">'


def test_a_browser_with_no_learner_is_told_nothing_is_stored_and_gets_none(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        page = browser.get("/data")
        assert page.status_code == 200 and NOTHING in page.text
        assert "/data/download" not in page.text and "/data/forget" not in page.text
        for asked in (
            browser.get("/data/download", follow_redirects=False),
            browser.get("/data/forget", follow_redirects=False),
            browser.post("/data/forget", follow_redirects=False),
        ):
            assert asked.status_code == 303 and asked.headers["location"] == "/data"
            assert "set-cookie" not in asked.headers
        assert "set-cookie" not in page.headers and not browser.cookies
    assert site.learners() == 0


def forget(browser: TestClient):
    """Press "Forget this browser's history" on the Your data page, then confirm."""
    assert '<a href="/data/forget">' in browser.get("/data").text
    asked = browser.get("/data/forget")
    assert asked.status_code == 200
    assert '<form method="post" action="/data/forget"' in asked.text
    return browser.post("/data/forget", follow_redirects=False)


def test_forgetting_deletes_the_anonymous_learner_and_clears_the_cookie(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as bystander:
        fresh = counts(browser.get("/progress").text)
        play_a_round(bystander, success=True)
        play_rounds(browser, site, True, True)
        assert counts(browser.get("/progress").text) != fresh
        ws = open_socket(browser)
        try:
            start = ws.receive_json()
            # Asking deletes nothing.
            assert browser.get("/data/forget").status_code == 200 and site.learners() == 2
            forgot = forget(browser)
            assert forgot.status_code == 303 and forgot.headers["location"] == "/data"
            assert forgot.headers["set-cookie"].startswith("chessop=; ")
            assert not browser.cookies
            # The browser's open tab is closed, and records nothing more.
            with pytest.raises(WebSocketDisconnect):
                end_round(ws, start, success=True)
        finally:
            ws.__exit__(None, None, None)
        assert site.learners() == 1  # the bystander's only
        # A later visit has no history.
        assert NOTHING in browser.get("/data").text
        assert counts(browser.get("/progress").text) == fresh
        assert site.learners() == 1


def test_a_signed_in_learner_is_pointed_to_the_deletion_of_their_account(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        sign_in(site, browser)
        play_rounds(browser, site, True)
        played = counts(browser.get("/progress").text)
        page = browser.get("/data").text
        assert '<a href="/account/delete">' in page and "/data/forget" not in page
        assert browser.get("/data/forget", follow_redirects=False).status_code == 303
        browser.post("/data/forget")
        assert counts(browser.get("/progress").text) == played and site.learners() == 1


def test_your_data_is_linked_from_the_footer_and_the_account_page_and_not_indexed(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        assert '<a href="/data">Your data</a>' in browser.get("/").text
        assert NOINDEX in browser.get("/data").text
        play_a_round(browser)
        assert NOINDEX in browser.get("/data").text and NOINDEX in browser.get("/data/forget").text
        assert browser.get("/data/download").headers["x-robots-tag"] == "noindex"
        sign_in(site, browser)
        # Beyond the footer's.
        assert browser.get("/account").text.count('<a href="/data">') == 2
