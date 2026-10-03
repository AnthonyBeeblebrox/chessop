"""The account page (public spec §5, ADR 0008): sign out, change the email address, delete the
account. Driven as a browser would through the hosted app, with a recording mailer, a fake
Lichess and a clock moved by hand."""

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from test_hosted import MINUTE, Site, counts, end_round, open_socket, play_a_round
from test_lichess import sign_in as lichess_sign_in
from test_signin import ANN, ask, field, link_in, sign_in, who


def press_confirm(browser: TestClient, link: str):
    """Open the mailed change link and press its button."""
    token = field(browser.get(link).text, "token")
    return browser.post(urlsplit(link).path, data={"token": token})


def press_confirm_token(browser: TestClient, link: str):
    """Post the link's token as its button would, without opening it first."""
    return browser.post(urlsplit(link).path, data={"token": token_of(link)})


def token_of(link: str) -> str:
    """The token the link carries."""
    return parse_qs(urlsplit(link).query)["token"][0]


def test_the_account_page_is_reached_from_the_header_and_shows_the_identity_and_kind(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as by_email, site.browser() as by_lichess:
        sign_in(site, by_email)
        assert who(by_email) == f"/account {ANN}"
        page = by_email.get("/account").text
        assert f"Signed in by email as <b>{ANN}</b>." in page
        lichess_sign_in(site, by_lichess, "Ann")
        assert who(by_lichess) == "/account Ann"
        page = by_lichess.get("/account").text
        assert "Signed in with Lichess as <b>Ann</b>." in page


BEN = "ben@example.org"


def change_email(browser: TestClient, email: str):
    """Ask, from the account page, to change the account's address to `email`."""
    page = browser.get("/account").text
    assert '<form method="post" action="/account/email">' in page
    return browser.post("/account/email", data={"email": email})


def test_changing_email_takes_effect_only_after_the_link_sent_to_the_new_address(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as elsewhere, site.browser() as later:
        sign_in(site, browser)
        play_a_round(browser, success=True)
        played = counts(browser.get("/progress").text)
        asked = change_email(browser, " Ben@Example.org ")
        assert asked.status_code == 200 and f"<b>{BEN}</b>" in asked.text
        message = site.outbox.sent[-1]
        assert message.to == BEN
        link = link_in(message)
        assert link.startswith("/account/email/confirm?token=")
        assert len(token_of(link)) >= 22  # 128 bits
        # Nothing changes before the link's button is pressed.
        for _ in range(2):
            landing = elsewhere.get(link)
            assert landing.status_code == 200 and "<button" in landing.text
            assert landing.headers["referrer-policy"] == "no-referrer"
        assert who(browser) == f"/account {ANN}"
        confirmed = press_confirm(elsewhere, link)
        assert confirmed.status_code == 200 and f"<b>{BEN}</b>" in confirmed.text
        # The browser signed in stays signed in, under the new address.
        assert who(browser) == f"/account {BEN}"
        assert f"Signed in by email as <b>{BEN}</b>." in browser.get("/account").text
        # The new address signs in to the account; the old one no longer does.
        sign_in(site, elsewhere, BEN)
        assert counts(elsewhere.get("/progress").text) == played
        sign_in(site, later, ANN)
        assert counts(later.get("/progress").text) != played
        assert who(later) == f"/account {ANN}" and site.learners() == 2
        # The link works once.
        assert "no longer works" in later.get(link).text
        again = press_confirm_token(later, link)
        assert "no longer works" in again.text
        assert who(browser) == f"/account {BEN}"


def test_a_change_to_an_address_another_account_holds_is_refused_and_mails_nothing(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as ann, site.browser() as ben:
        sign_in(site, ann)
        sign_in(site, ben, BEN)
        mailed = len(site.outbox.sent)
        refused = change_email(ann, BEN.upper())
        assert refused.status_code == 400
        assert "Another account uses that address." in refused.text
        assert len(site.outbox.sent) == mailed
        same = change_email(ann, ANN)
        assert same.status_code == 400 and len(site.outbox.sent) == mailed
        assert change_email(ann, "no address").status_code == 400
        assert who(ann) == f"/account {ANN}" and who(ben) == f"/account {BEN}"


def test_a_change_link_to_an_address_taken_since_it_was_mailed_changes_nothing(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as ann, site.browser() as ben:
        sign_in(site, ann)
        change_email(ann, BEN)
        link = link_in(site.outbox.sent[-1])
        sign_in(site, ben, BEN)  # the address gets its own account meanwhile
        refused = press_confirm(ann, link)
        assert "Another account now uses" in refused.text
        assert who(ann) == f"/account {ANN}" and who(ben) == f"/account {BEN}"
        assert site.learners() == 2


def test_only_the_newest_change_link_works_and_none_after_fifteen_minutes(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        sign_in(site, browser)
        change_email(browser, BEN)
        first = link_in(site.outbox.sent[-1])
        change_email(browser, "cat@example.org")
        newest = link_in(site.outbox.sent[-1])
        assert "no longer works" in browser.get(first).text
        assert "no longer works" in press_confirm_token(browser, first).text
        site.clock.now += 15 * MINUTE
        assert "no longer works" in browser.get(newest).text
        assert "no longer works" in press_confirm_token(browser, newest).text
        assert who(browser) == f"/account {ANN}"


def test_a_change_link_signs_no_one_in_and_a_sign_in_link_changes_nothing(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as other:
        sign_in(site, browser)
        change_email(browser, BEN)
        change = link_in(site.outbox.sent[-1])
        token = token_of(change)
        other.post("/signin/confirm", data={"token": token, "next": "/"})
        assert who(other).endswith("Sign in")
        ask(other, BEN)
        token = token_of(link_in(site.outbox.sent[-1]))
        assert "no longer works" in browser.get(f"/account/email/confirm?token={token}").text
        posted = browser.post("/account/email/confirm", data={"token": token})
        assert "no longer works" in posted.text
        assert who(browser) == f"/account {ANN}"


def test_a_lichess_account_has_no_address_to_change(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        lichess_sign_in(site, browser, "Ann")
        page = browser.get("/account").text
        assert 'action="/account/email"' not in page and 'name="email"' not in page
        assert browser.post("/account/email", data={"email": BEN}).status_code == 404
        assert not site.outbox.sent
        assert who(browser) == "/account Ann"


def test_only_a_signed_in_browser_can_ask_to_change_an_address(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        play_a_round(browser)
        asked = browser.post("/account/email", data={"email": BEN}, follow_redirects=False)
        assert asked.headers["location"] == "/signin?next=%2Faccount"
        assert not site.outbox.sent


def delete_account(browser: TestClient):
    """Press "Delete my account" on the account page, then confirm."""
    page = browser.get("/account").text
    assert '<a href="/account/delete">' in page
    asked = browser.get("/account/delete")
    assert asked.status_code == 200
    assert '<form method="post" action="/account/delete">' in asked.text
    return browser.post("/account/delete", follow_redirects=False)


def test_deleting_the_account_removes_everything_and_signs_out_every_device(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as other, site.browser() as bystander:
        fresh = counts(browser.get("/progress").text)
        play_a_round(bystander, success=True)
        sign_in(site, browser)
        sign_in(site, other)
        play_a_round(browser, success=True)
        change_email(browser, BEN)  # a pending change goes with the account
        change = link_in(site.outbox.sent[-1])
        ws = open_socket(other)
        try:
            start = ws.receive_json()
            # Asking spends nothing: the account is still there.
            assert browser.get("/account/delete").status_code == 200
            assert who(other) == f"/account {ANN}"
            deleted = delete_account(browser)
            assert deleted.status_code == 303
            assert deleted.headers["set-cookie"].startswith("chessop=; ")
            assert not browser.cookies
            # The other device's open tab is closed, and records nothing more.
            with pytest.raises(WebSocketDisconnect):
                end_round(ws, start, success=True)
        finally:
            ws.__exit__(None, None, None)
        assert site.learners() == 1  # the bystander's only
        # The second device is signed out at its next request, with none of the history.
        page = other.get("/progress")
        assert who(other).endswith("Sign in") and counts(page.text) == fresh
        assert other.get("/account", follow_redirects=False).status_code == 303
        assert who(browser).endswith("Sign in") and counts(browser.get("/progress").text) == fresh
        assert "no longer works" in press_confirm_token(other, change).text
        # The address is free again: it signs in to a new, empty account.
        sign_in(site, browser)
        assert counts(browser.get("/progress").text) == fresh and site.learners() == 2


def test_only_a_signed_in_browser_can_delete_an_account(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        play_a_round(browser, success=True)
        played = counts(browser.get("/progress").text)
        assert browser.get("/account/delete", follow_redirects=False).status_code == 303
        browser.post("/account/delete")
        assert counts(browser.get("/progress").text) == played and site.learners() == 1


def test_a_lichess_account_is_deleted_the_same_way(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        lichess_sign_in(site, browser, "Ann")
        play_a_round(browser, success=True)
        assert delete_account(browser).status_code == 303
        assert site.learners() == 0 and who(browser).endswith("Sign in")
