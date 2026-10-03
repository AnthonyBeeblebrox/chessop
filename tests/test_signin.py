"""Email sign-in, sessions and adopting the anonymous learner (public spec §5, ADR 0008), driven
as a browser would through the hosted app, with a recording mailer and a clock moved by hand."""

import random
import re
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from chessop.app import create_app
from chessop.mail import Message
from chessop.store import Store
from test_hosted import (
    DAY,
    HOSTED,
    MINUTE,
    Site,
    counts,
    end_round,
    hosted_form,
    open_socket,
    play_a_round,
    token,
)
from test_wire import E4_E5

ANN = "ann@example.org"
HOUR = 60 * MINUTE


def who(browser: TestClient, page: str = "/progress") -> str:
    """What the header of `page` shows: the link's address and its text."""
    found = re.search(r'<p class="who"><a href="([^"]*)">([^<]*)</a></p>', browser.get(page).text)
    assert found is not None
    return f"{unescape(found.group(1))} {found.group(2)}"


def field(page: str, name: str) -> str:
    """The value of the page's hidden field `name`."""
    found = re.search(rf'<input type="hidden" name="{name}" value="([^"]*)">', page)
    assert found is not None, name
    return unescape(found.group(1))


def ask(browser: TestClient, email: str = ANN, back: str = "/progress") -> str:
    """Ask for a sign-in message from the sign-in page: the page that answers."""
    response = browser.post("/signin", data={"email": email, "next": back})
    assert response.status_code == 200
    return response.text


def link_in(message: Message) -> str:
    """The path and query of the link the message carries."""
    (link,) = re.findall(r"https://chessop\.example(/\S+)", message.body)
    return link


def code_in(message: Message) -> str:
    (code,) = re.findall(r"(?<![\w-])\d{6}(?![\w-])", message.body)
    return code


def type_code(browser: TestClient, inbox: str, code: str):
    """Type `code` into the "check your inbox" page `inbox`."""
    form = {name: field(inbox, name) for name in ("next", "binding", "email")}
    return browser.post("/signin/code", data={**form, "code": code}, follow_redirects=False)


def press_confirm(browser: TestClient, link: str):
    """Open the mailed link and press its button."""
    page = browser.get(link).text
    form = {name: field(page, name) for name in ("token", "next")}
    return browser.post(urlsplit(link).path, data=form, follow_redirects=False)


def sign_in(site: Site, browser: TestClient, email: str = ANN) -> None:
    inbox = ask(browser, email)
    assert type_code(browser, inbox, code_in(site.outbox.sent[-1])).status_code == 303


def a_wrong_code(right: str) -> str:
    return f"{(int(right) + 1) % 10**6:06d}"


def test_the_header_offers_sign_in_and_the_page_returns_where_it_came_from(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        assert who(browser, "/progress?never=1") == "/signin?next=%2Fprogress%3Fnever%3D1 Sign in"
        page = browser.get("/signin?next=%2Fprogress%3Fnever%3D1")
        assert page.status_code == 200 and "set-cookie" not in page.headers
        assert '<input type="email" name="email"' in page.text
        assert field(page.text, "next") == "/progress?never=1"
        assert '<a href="/privacy">' in page.text
        inbox = ask(browser, back="/progress?never=1")
        signed = type_code(browser, inbox, code_in(site.outbox.sent[0]))
        assert signed.headers["location"] == "/progress?never=1"
        assert who(browser) == f"/account {ANN}"


def test_sign_in_never_leads_off_the_site(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        for target in ("https://evil.example/", "//evil.example/", "progress", "/\t/evil.example"):
            assert field(browser.get("/signin", params={"next": target}).text, "next") == "/"
            inbox = ask(browser, f"{len(site.outbox.sent)}@example.org", back=target)
            assert link_in(site.outbox.sent[-1]).endswith("&next=%2F")
            signed = type_code(browser, inbox, code_in(site.outbox.sent[-1]))
            assert signed.headers["location"] == "/"


def test_the_link_opens_a_button_and_only_its_post_signs_in_once(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as other:
        assert "Check your inbox" in ask(browser)
        (message,) = site.outbox.sent
        assert message.to == ANN
        link = link_in(message)
        assert link.startswith("/signin/confirm?token=") and len(link) > 22 + 22  # 128 bits
        for _ in range(2):  # a mail scanner fetching the link spends nothing
            landing = browser.get(link)
            assert landing.status_code == 200 and "<button" in landing.text
            assert landing.headers["referrer-policy"] == "no-referrer"
            assert "set-cookie" not in landing.headers
        assert who(browser).endswith("Sign in") and site.learners() == 0
        confirmed = press_confirm(browser, link)
        assert confirmed.status_code == 303 and confirmed.headers["location"] == "/progress"
        assert who(browser) == f"/account {ANN}"
        # A second use fails, here and anywhere.
        assert "no longer works" in other.get(link).text
        again = other.post("/signin/confirm", data={"token": link.split("=")[1].split("&")[0]})
        assert "no longer works" in again.text and "set-cookie" not in again.headers
        assert who(other).endswith("Sign in")
        assert site.learners() == 1


def test_the_link_signs_in_a_browser_other_than_the_one_that_asked(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as laptop, site.browser() as phone:
        ask(laptop)
        assert press_confirm(phone, link_in(site.outbox.sent[0])).status_code == 303
        assert who(phone) == f"/account {ANN}" and who(laptop).endswith("Sign in")


def test_the_code_works_once_and_only_in_the_browser_that_asked(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as other:
        inbox = ask(browser)
        others_inbox = ask(other, "bob@example.org")
        ann_message, _ = site.outbox.sent
        code = code_in(ann_message)
        refused = type_code(other, others_inbox, code)  # the right code, the wrong browser
        assert refused.status_code == 400 and "set-cookie" not in refused.headers
        assert who(other).endswith("Sign in")
        signed = type_code(browser, inbox, code)
        assert signed.status_code == 303 and signed.headers["location"] == "/progress"
        assert who(browser) == f"/account {ANN}"
        # Used: neither the code nor the link of that message works again.
        assert type_code(browser, inbox, code).status_code == 400
        assert "no longer works" in other.get(link_in(ann_message)).text


def test_five_wrong_codes_exhaust_the_code_and_a_resend_does_not_reset_the_count(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        inbox = ask(browser)
        first = code_in(site.outbox.sent[0])
        for _ in range(3):
            assert type_code(browser, inbox, a_wrong_code(first)).status_code == 400
        resend = {name: field(inbox, name) for name in ("next", "binding", "email")}
        resent = browser.post("/signin", data=resend).text
        assert "Check your inbox" in resent and len(site.outbox.sent) == 2
        second = code_in(site.outbox.sent[1])
        assert type_code(browser, resent, first).status_code == 400  # replaced, and a 4th try
        assert type_code(browser, resent, a_wrong_code(second)).status_code == 400
        assert type_code(browser, resent, second).status_code == 400  # the right one, too late
        assert who(browser).endswith("Sign in")
        # A browser left with four tries used still signs in with the right code.
    site = Site(tmp_path / "other")
    with site.browser() as browser:
        inbox = ask(browser)
        code = code_in(site.outbox.sent[0])
        for _ in range(4):
            assert type_code(browser, inbox, a_wrong_code(code)).status_code == 400
        assert type_code(browser, inbox, code).status_code == 303


def test_the_link_and_the_code_expire_after_fifteen_minutes(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as other:
        inbox = ask(browser)
        others_inbox = ask(other, "bob@example.org")
        ann_message, bob_message = site.outbox.sent
        site.clock.now += 15 * MINUTE - 1
        assert type_code(other, others_inbox, code_in(bob_message)).status_code == 303
        site.clock.now += 1
        assert type_code(browser, inbox, code_in(ann_message)).status_code == 400
        assert "no longer works" in browser.get(link_in(ann_message)).text
        late = browser.post("/signin/confirm", data={"token": link_in(ann_message)[22:65]})
        assert "no longer works" in late.text
        assert who(browser).endswith("Sign in")
    site = Site(tmp_path / "other")
    with site.browser() as browser:
        ask(browser)
        site.clock.now += 15 * MINUTE - 1
        assert press_confirm(browser, link_in(site.outbox.sent[0])).status_code == 303


def test_an_unknown_address_gets_its_account_at_the_first_sign_in(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as other:
        ask(browser, " Ann@Example.org ")
        assert site.learners() == 0  # asking creates nothing
        assert site.outbox.sent[0].to == ANN
        press_confirm(browser, link_in(site.outbox.sent[0]))
        assert site.learners() == 1
        sign_in(site, other, ANN)  # the same account from then on
        assert site.learners() == 1 and who(other) == f"/account {ANN}"


def test_something_that_is_no_address_is_refused_and_mailed_nothing(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        for typed in ("", "ann", "ann@nowhere", "a b@example.org"):
            refused = browser.post("/signin", data={"email": typed, "next": "/"})
            assert refused.status_code == 400 and "not an email address" in refused.text
    assert not site.outbox.sent


def answer(page: str) -> str:
    """The "check your inbox" page with its random binding blanked."""
    return re.sub(r'name="binding" value="[^"]*"', "", page)


def test_the_answer_is_the_same_past_three_emails_per_address_in_fifteen_minutes(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        answers = [answer(ask(browser)) for _ in range(3)]
        assert len(site.outbox.sent) == 3
        site.clock.now += 14 * MINUTE
        answers.append(answer(ask(browser)))
        assert len(site.outbox.sent) == 3  # the fourth is not sent
        assert len(set(answers)) == 1 and "Check your inbox" in answers[0]
        assert "Check your inbox" in ask(browser, "bob@example.org")  # another address
        assert len(site.outbox.sent) == 4
        site.clock.now += 1 * MINUTE
        ask(browser)
        assert len(site.outbox.sent) == 5


def test_the_answer_is_the_same_past_ten_emails_per_ip_per_hour(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser(ip="198.51.100.1") as browser, site.browser(ip="198.51.100.2") as other:
        for n in range(10):
            ask(browser, f"learner{n}@example.org")
        assert len(site.outbox.sent) == 10
        assert "Check your inbox" in ask(browser, "learner10@example.org")
        assert len(site.outbox.sent) == 10
        ask(other, "learner10@example.org")  # another client
        assert len(site.outbox.sent) == 11
        site.clock.now += HOUR
        ask(browser, "learner10@example.org")
        assert len(site.outbox.sent) == 12


def test_two_ipv6_addresses_in_one_64_are_one_client(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser(ip="2001:db8:0:1::1") as one, site.browser(ip="2001:db8:0:1:ffff::2") as two:
        for n in range(6):
            ask(one, f"a{n}@example.org")
            ask(two, f"b{n}@example.org")
    assert len(site.outbox.sent) == 10


def test_the_answer_is_the_same_past_250_emails_a_day_site_wide(tmp_path: Path) -> None:
    site = Site(tmp_path)
    for n in range(251):
        with site.browser(ip=f"198.51.{n // 200}.{n % 200}") as browser:
            assert "Check your inbox" in ask(browser, f"learner{n}@example.org")
    assert len(site.outbox.sent) == 250
    site.clock.now += DAY
    with site.browser() as browser:
        ask(browser)
    assert len(site.outbox.sent) == 251


def test_the_cookie_token_rotates_at_sign_in_and_at_sign_out(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as thief:
        play_a_round(browser, success=True)
        anonymous = token(browser)
        played = counts(browser.get("/progress").text)
        fresh = counts(thief.get("/progress").text)
        assert played != fresh
        sign_in(site, browser)
        signed = token(browser)
        assert signed != anonymous
        thief.cookies.set("chessop", anonymous)  # the token from before sign-in is dead
        assert counts(thief.get("/progress").text) == fresh and who(thief).endswith("Sign in")
        out = browser.post("/signout", follow_redirects=False)
        assert out.status_code == 303
        assert out.headers["set-cookie"].startswith("chessop=; ")
        assert "Max-Age=0" in out.headers["set-cookie"]
        assert not browser.cookies
        thief.cookies.set("chessop", signed)  # and so is the signed-in one after sign-out
        assert counts(thief.get("/progress").text) == fresh and who(thief).endswith("Sign in")


def test_the_session_lasts_a_year_from_the_last_visit(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        sign_in(site, browser)
        cookie = token(browser)
        site.clock.now += 200 * DAY
        again = browser.get("/progress")
        assert again.headers["set-cookie"].startswith(f"chessop={cookie}; ")
        assert "Max-Age=31536000" in again.headers["set-cookie"]
        site.clock.now += 300 * DAY  # 500 days after signing in, 300 after the last visit
        assert who(browser) == f"/account {ANN}"
        site.clock.now += 366 * DAY
        assert who(browser).endswith("Sign in")


def test_any_number_of_browsers_stay_signed_in_at_once(tmp_path: Path) -> None:
    site = Site(tmp_path)
    browsers = [site.browser() for _ in range(4)]
    for browser in browsers:
        sign_in(site, browser, ANN)
        site.clock.now += 16 * MINUTE
    assert all(who(browser) == f"/account {ANN}" for browser in browsers)
    assert len({token(browser) for browser in browsers}) == 4


def test_the_first_sign_in_keeps_the_anonymous_history_under_the_account(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as elsewhere:
        fresh = counts(browser.get("/progress").text)
        play_a_round(browser, success=True)
        browser.post("/settings", data={**hosted_form(), "width_player": "1"})
        played = counts(browser.get("/progress").text)
        assert played != fresh and site.learners() == 1
        sign_in(site, browser)
        assert site.learners() == 1  # the account's learner: the anonymous one is gone
        page = browser.get("/progress").text
        assert counts(page) == played and 'aria-label="daily Score, 1 day"' in page
        # The account has it wherever it signs in.
        sign_in(site, elsewhere)
        assert counts(elsewhere.get("/progress").text) == played
        assert 'name="width_player" value="1"' in elsewhere.get("/settings").text
        assert site.learners() == 1


def test_an_account_with_no_history_takes_a_second_browsers_anonymous_history(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as first, site.browser() as second:
        sign_in(site, first)
        fresh = counts(first.get("/progress").text)
        play_a_round(second, success=True)
        played = counts(second.get("/progress").text)
        assert played != fresh and site.learners() == 2
        sign_in(site, second)
        assert site.learners() == 1
        assert counts(second.get("/progress").text) == played
        assert counts(first.get("/progress").text) == played


def test_signing_in_on_a_second_device_with_history_keeps_both_histories(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as first, site.browser() as second:
        sign_in(site, first)
        play_a_round(first, success=True)
        play_a_round(first)
        first.post("/settings", data={**hosted_form(), "width_player": "1"})
        site.clock.now += MINUTE
        play_a_round(second, success=True)
        second.post("/settings", data={**hosted_form(), "width_player": "3"})
        anonymous = token(second)
        assert site.learners() == 2
        sign_in(site, second)
        assert site.learners() == 1  # the anonymous learner is gone
        assert token(second) != anonymous
        # Both browsers are now the account, with its settings.
        for browser in (first, second):
            assert 'name="width_player" value="1"' in browser.get("/settings").text
        store = Store.open(tmp_path)
        account = store.account("email", ANN)
        assert account is not None
        learner = store.learner(account.learner_id)
        log = learner.round_log()
        assert len(log) == 3  # the account's two rounds and the anonymous one
        [today] = learner.daily_scores()
        counted = [r["outcome"] for r in log if r["outcome"] != "forced"]
        assert today["rounds"] == len(counted)
        assert today["successes"] == counted.count("success")
        store.close()


def test_a_tab_open_at_sign_in_is_closed_and_comes_back_as_the_accounts(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        ws = open_socket(browser)
        try:
            start = ws.receive_json()
            sign_in(site, browser)
            with pytest.raises(WebSocketDisconnect):
                end_round(ws, start, success=True)
        finally:
            ws.__exit__(None, None, None)
        play_a_round(browser, success=True)  # the play page reconnects
        assert site.learners() == 1
        assert 'aria-label="daily Score, 1 day"' in browser.get("/progress").text


def test_a_signed_in_learner_is_not_told_their_progress_lives_in_this_browser(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        sign_in(site, browser)
        play_a_round(browser)
        assert play_a_round(browser)["notice"] is None
        assert "on this browser only" not in browser.get("/progress").text


def test_after_sign_out_the_browser_has_no_learner_and_none_of_the_history(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as elsewhere:
        fresh = counts(browser.get("/progress").text)
        play_a_round(browser, success=True)
        sign_in(site, browser)
        sign_in(site, elsewhere)
        played = counts(browser.get("/progress").text)
        browser.post("/signout")
        assert not browser.cookies
        page = browser.get("/progress")
        assert counts(page.text) == fresh and "set-cookie" not in page.headers
        assert who(browser).endswith("Sign in") and site.learners() == 1
        assert browser.get("/account", follow_redirects=False).headers["location"] == (
            "/signin?next=%2Faccount"
        )
        # The account lives on where it is still signed in.
        assert counts(elsewhere.get("/progress").text) == played
        # The next round is a fresh anonymous learner's.
        assert "progress is kept on this browser only" not in page.text
        play_a_round(browser)
        assert site.learners() == 2 and who(browser, "/help").endswith("Sign in")
        assert "progress is kept on this browser only" in browser.get("/progress").text


def test_a_tab_open_at_sign_out_is_closed_and_records_nothing_more(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser, site.browser() as elsewhere:
        sign_in(site, browser)
        sign_in(site, elsewhere)
        fresh = counts(elsewhere.get("/progress").text)
        ws = open_socket(browser)
        try:
            start = ws.receive_json()
            browser.post("/signout")
            with pytest.raises(WebSocketDisconnect):
                end_round(ws, start, success=True)
        finally:
            ws.__exit__(None, None, None)
        assert counts(elsewhere.get("/progress").text) == fresh


def test_signing_out_does_nothing_to_an_anonymous_learner(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        play_a_round(browser, success=True)
        played = counts(browser.get("/progress").text)
        browser.post("/signout")
        assert counts(browser.get("/progress").text) == played


def test_the_account_page_names_the_account_and_signs_out(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        sign_in(site, browser)
        page = browser.get("/account")
        assert page.status_code == 200 and f"<b>{ANN}</b>" in page.text
        assert '<form method="post" action="/signout">' in page.text


def test_with_no_mailer_the_message_is_printed_to_the_console(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    app = create_app(E4_E5, rng=random.Random(1), store=Store.open(tmp_path), hosted=HOSTED)
    with TestClient(app, base_url=HOSTED.base_url) as browser:
        inbox = ask(browser)
        printed = capsys.readouterr().out
        assert f"mail to {ANN}" in printed
        message = Message(to=ANN, subject="", body=printed)
        assert link_in(message).startswith("/signin/confirm?token=")
        assert type_code(browser, inbox, code_in(message)).status_code == 303
