"""`chessop maintain` (public spec §10, §13): the nightly command that writes yesterday's usage
aggregate, warns the email accounts about to be deleted and purges the learners unseen for too
long. The site is driven as a browser would, then the command is run on its data directory with
a recording mailer and a chosen time, and the site and the mail handed over are looked at."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chessop.cli import main, maintain
from chessop.mail import MailError, Message
from chessop.store import Store, UsageDay
from test_cli import HOSTED_ENV
from test_hosted import DAY, HOSTED, NOW, Site, play_a_round
from test_lichess import sign_in as lichess_sign_in
from test_signin import ANN, sign_in


class Post:
    """A mailer that delivers nothing: the messages handed to it, oldest first. One that is
    `down` delivers none and says so."""

    def __init__(self) -> None:
        self.delivered: list[Message] = []
        self.down = False

    def deliver(self, message: Message) -> None:
        if self.down:
            raise MailError("Scaleway answered 503")
        self.delivered.append(message)


def run(site: Site, post: Post | None = None) -> None:
    """Run `chessop maintain` on the site's data directory at the site's time."""
    maintain(site.data_dir, HOSTED, Post() if post is None else post, site.clock.now)


def failed(site: Site, post: Post) -> bool:
    """Run `chessop maintain`: whether it exited non-zero."""
    try:
        run(site, post)
    except SystemExit as stopped:
        assert stopped.code not in (0, None)
        return True
    return False


def usage(site: Site) -> list[UsageDay]:
    store = Store.open(site.data_dir)
    try:
        return store.usage_days()
    finally:
        store.close()


def play_rounds(browser: TestClient, rounds: int) -> None:
    for _ in range(rounds):
        play_a_round(browser)


def test_an_anonymous_learner_is_deleted_after_12_months_with_no_request(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        play_rounds(browser, 5)
    site.clock.now = NOW + 364 * DAY
    run(site)
    assert site.learners() == 1  # one day short
    site.clock.now = NOW + 365 * DAY
    run(site)
    assert site.learners() == 0


def test_an_anonymous_learner_with_fewer_than_5_rounds_is_deleted_after_30_days(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)
    with site.browser() as few, site.browser() as five:
        play_rounds(few, 4)
        play_rounds(five, 5)
    site.clock.now = NOW + 29 * DAY
    run(site)
    assert site.learners() == 2  # one day short
    site.clock.now = NOW + 30 * DAY
    run(site)
    assert site.learners() == 1  # the learner with 5 rounds stays


def test_an_anonymous_learners_request_restarts_the_wait(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        play_rounds(browser, 1)
        site.clock.now = NOW + 29 * DAY
        assert browser.get("/progress").status_code == 200
        site.clock.now = NOW + 58 * DAY
        run(site)
        assert site.learners() == 1
        site.clock.now = NOW + 59 * DAY
        run(site)
        assert site.learners() == 0


def test_an_email_account_is_warned_once_at_23_months_and_deleted_30_days_later(
    tmp_path: Path,
) -> None:
    site, post = Site(tmp_path), Post()
    with site.browser() as browser:
        sign_in(site, browser)
    site.clock.now = NOW + 699 * DAY
    run(site, post)
    assert post.delivered == []  # one day short of 23 months
    site.clock.now = NOW + 700 * DAY
    run(site, post)
    (warning,) = post.delivered
    assert warning.to == ANN
    assert "30 days" in warning.body and "https://chessop.example/signin" in warning.body
    site.clock.now = NOW + 729 * DAY
    run(site, post)
    assert site.learners() == 1 and len(post.delivered) == 1  # warned once, 29 days ago
    site.clock.now = NOW + 730 * DAY
    run(site, post)
    assert site.learners() == 0 and len(post.delivered) == 1


def test_a_visit_after_the_warning_clears_it_and_keeps_the_account(tmp_path: Path) -> None:
    site, post = Site(tmp_path), Post()
    with site.browser() as browser:
        sign_in(site, browser)
    site.clock.now = NOW + 700 * DAY
    run(site, post)
    assert len(post.delivered) == 1
    site.clock.now = back = NOW + 710 * DAY
    with site.browser() as browser:
        sign_in(site, browser)  # the request the warning asks for, and no other
    site.clock.now = NOW + 735 * DAY  # past 24 months from the first visit
    run(site, post)
    assert site.learners() == 1 and len(post.delivered) == 1
    # The wait began again at the visit: a new warning 23 months after it, then 30 days.
    site.clock.now = back + 700 * DAY
    run(site, post)
    assert site.learners() == 1 and len(post.delivered) == 2
    site.clock.now = back + 729 * DAY
    run(site, post)
    assert site.learners() == 1
    site.clock.now = back + 730 * DAY
    run(site, post)
    assert site.learners() == 0


def test_a_warning_that_could_not_be_sent_delays_the_deletion(tmp_path: Path) -> None:
    site, post = Site(tmp_path), Post()
    with site.browser() as browser:
        sign_in(site, browser)
    post.down = True
    site.clock.now = NOW + 700 * DAY
    assert failed(site, post)
    site.clock.now = NOW + 730 * DAY
    assert failed(site, post)
    assert site.learners() == 1  # 24 months unseen, but never warned
    post.down = False
    site.clock.now = NOW + 731 * DAY
    run(site, post)
    assert site.learners() == 1 and len(post.delivered) == 1
    site.clock.now = NOW + 760 * DAY
    run(site, post)
    assert site.learners() == 1  # the warning is 29 days old
    site.clock.now = NOW + 761 * DAY
    run(site, post)
    assert site.learners() == 0 and len(post.delivered) == 1


def test_a_lichess_account_is_deleted_at_24_months_with_no_email(tmp_path: Path) -> None:
    site, post = Site(tmp_path), Post()
    with site.browser() as browser:
        lichess_sign_in(site, browser, "Ben")
    site.clock.now = NOW + 729 * DAY
    run(site, post)
    assert site.learners() == 1  # one day short
    site.clock.now = NOW + 730 * DAY
    run(site, post)
    assert site.learners() == 0 and post.delivered == []


def test_an_account_outlives_the_anonymous_purges(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        play_rounds(browser, 1)
        lichess_sign_in(site, browser, "Ben")
    site.clock.now = NOW + 365 * DAY
    run(site)
    assert site.learners() == 1


def test_running_maintain_twice_in_a_day_changes_nothing_the_second_time(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    site, post = Site(tmp_path), Post()
    with site.browser() as ann, site.browser() as idle:
        sign_in(site, ann)
        play_rounds(idle, 5)
    site.clock.now = NOW + 700 * DAY  # the account is warned, the anonymous learner deleted
    run(site, post)
    first = capsys.readouterr().out
    assert "wrote 2028-12-14" in first
    assert "1 warned" in first and "1 deleted" in first
    after, mailed = usage(site), list(post.delivered)
    assert site.learners() == 1 and len(mailed) == 1
    site.clock.now += 3600
    run(site, post)
    second = capsys.readouterr().out
    assert "2028-12-14 already written" in second
    assert "0 warned" in second and "1 deleted" not in second
    assert usage(site) == after and post.delivered == mailed and site.learners() == 1


def test_a_failing_step_exits_non_zero_while_the_later_steps_still_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    site, post = Site(tmp_path), Post()
    with site.browser() as ann, site.browser() as ben, site.browser() as idle:
        sign_in(site, ann)
        lichess_sign_in(site, ben, "Ben")
        play_rounds(idle, 5)
    post.down = True
    site.clock.now = NOW + 730 * DAY
    assert failed(site, post)  # the warning did not go
    assert site.learners() == 1  # yet the anonymous learner and the Lichess account were purged
    yesterday = usage(site)[-2]
    assert (yesterday.day, yesterday.rounds) == ("2029-01-13", 0)  # and its aggregate row written
    captured = capsys.readouterr()
    assert "warnings" in captured.err and "503" in captured.err
    assert ANN not in captured.out + captured.err  # no address in the log


def test_purge_deletions_are_counted_in_the_aggregate(tmp_path: Path) -> None:
    site = Site(tmp_path)
    with site.browser() as few, site.browser() as five, site.browser() as ben:
        play_rounds(few, 1)
        play_rounds(five, 5)
        lichess_sign_in(site, ben, "Ben")
    site.clock.now = NOW + 730 * DAY  # 2029-01-14, 08:00 UTC
    run(site)
    assert site.learners() == 0
    yesterday, today = usage(site)[-2:]
    assert (yesterday.day, yesterday.rounds, yesterday.deletions) == ("2029-01-13", 0, 0)
    assert (today.day, today.deletions) == ("2029-01-14", 3)


def test_chessop_maintain_reads_the_environment_and_the_data_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    site = Site(tmp_path)
    with site.browser() as browser:
        play_rounds(browser, 5)
    main(["maintain", "--data-dir", str(tmp_path)], HOSTED_ENV)  # at the real time: 2026
    assert site.learners() == 1
    assert "chessop maintain: aggregate" in capsys.readouterr().out
    main(["maintain"], {**HOSTED_ENV, "CHESSOP_DATA_DIR": str(tmp_path)})
    with pytest.raises(SystemExit) as stopped:
        main(["maintain", "--data-dir", str(tmp_path)], {})
    assert "CHESSOP_BASE_URL" in str(stopped.value.code)


def test_chessop_maintain_with_no_database_says_so_and_creates_none(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="no database"):
        main(["maintain", "--data-dir", str(tmp_path / "nowhere")], HOSTED_ENV)
    assert not (tmp_path / "nowhere").exists()
