"""The learner's day ends at their own midnight (public spec §3, G6): the browser reports its
time zone with `hello {tz}` when the socket opens, the server stores it when the learner has
none, and the daily Score's day follows it. Local mode's one learner keeps the machine's day
whatever is stored (ADR 0002).

Tested at the store seam with a learner of the hosted kind (not the implicit one) and rounds
ended at chosen moments; through the wire once hosted mode exists (ticket 28)."""

import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.choices import BAND_NAMES, Choices, form_values, hello, load, parse, save
from chessop.store import IMPLICIT, TIMEZONE, LearnerStore, Store
from test_settings import valid_form
from test_store import a_round, passes_at_start
from test_wire import E4_E5, play, seeded_for_rounds


def at(local: str, zone: str) -> float:
    """The instant of the ISO local time `local` in `zone`."""
    return datetime.fromisoformat(local).replace(tzinfo=ZoneInfo(zone)).timestamp()


@pytest.fixture
def machine_in_utc(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The machine's clock set to UTC, whatever zone the tests run in."""
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


# Either side of Auckland's midnight, both 10:59 UTC on 2026-03-10: one day on a UTC machine.
ZONE = "Pacific/Auckland"
BEFORE = at("2026-03-10T23:59:30", ZONE)
AFTER = at("2026-03-11T00:00:30", ZONE)


def days_of_rounds_ended(learner: LearnerStore, *ends: float) -> list[str]:
    """Commit a round ended at each of `ends`; the days of the learner's daily Score."""
    for end in ends:
        learner.commit(a_round(started_at=end - 5, ended_at=end), passes_at_start)
    return [row["day"] for row in learner.daily_scores()]


@pytest.mark.usefixtures("machine_in_utc")
def test_rounds_either_side_of_the_learners_midnight_land_on_two_days() -> None:
    learner = Store.in_memory().create_learner(BEFORE)
    learner.set_setting(TIMEZONE, ZONE)
    assert days_of_rounds_ended(learner, BEFORE, AFTER) == ["2026-03-10", "2026-03-11"]


@pytest.mark.usefixtures("machine_in_utc")
def test_with_no_timezone_the_learners_day_is_the_machines() -> None:
    learner = Store.in_memory().create_learner(BEFORE)
    assert days_of_rounds_ended(learner, BEFORE, AFTER) == ["2026-03-10"]


@pytest.mark.usefixtures("machine_in_utc")
def test_local_modes_learner_keeps_the_machines_day_whatever_timezone_is_stored() -> None:
    learner = Store.in_memory().implicit()
    learner.set_setting(TIMEZONE, ZONE)
    assert days_of_rounds_ended(learner, BEFORE, AFTER) == ["2026-03-10"]


@pytest.mark.usefixtures("machine_in_utc")
def test_local_modes_learner_keeps_the_machines_day_though_first_asked_for_by_id(
    tmp_path: Path,
) -> None:
    Store.open(tmp_path).implicit().set_setting(TIMEZONE, ZONE)
    file = Store.open(tmp_path)
    file.learner(IMPLICIT)
    assert days_of_rounds_ended(file.implicit(), BEFORE, AFTER) == ["2026-03-10"]


@pytest.mark.usefixtures("machine_in_utc")
def test_the_change_since_your_last_day_follows_the_learners_day() -> None:
    """Two rounds 20 minutes apart on one machine day but either side of the learner's
    midnight: seen just after, the first was played on the last day before this one."""
    learner = Store.in_memory().create_learner(BEFORE)
    learner.set_setting(TIMEZONE, ZONE)
    first, second = at("2026-03-10T23:50:00", ZONE), at("2026-03-11T00:10:00", ZONE)
    days_of_rounds_ended(learner, first, second)
    now = second + 60
    assert learner.day(now) == "2026-03-11"
    assert learner.last_day_before(learner.day(now)) == ("2026-03-10", 0.1)


@pytest.fixture
def learner() -> LearnerStore:
    """A learner of the hosted kind, with no time zone yet."""
    return Store.in_memory().create_learner(BEFORE)


def test_hello_sets_the_timezone_when_the_learner_has_none(learner: LearnerStore) -> None:
    hello(learner, "Europe/Paris")
    assert load(learner).timezone == "Europe/Paris"


def test_hello_does_not_overwrite_a_stored_timezone(learner: LearnerStore) -> None:
    hello(learner, "Europe/Paris")
    hello(learner, "America/New_York")
    assert load(learner).timezone == "Europe/Paris"


@pytest.mark.parametrize("tz", ["Mars/Olympus_Mons", "../../etc/passwd", "", "x" * 300, 3, None])
def test_an_invalid_timezone_is_ignored(learner: LearnerStore, tz: object) -> None:
    hello(learner, tz)
    assert load(learner).timezone is None
    hello(learner, "Asia/Tokyo")  # a valid one is still taken afterwards
    assert load(learner).timezone == "Asia/Tokyo"


def submitted(learner: LearnerStore, **overrides: str) -> Choices | dict[str, str]:
    """The settings form submitted at the defaults, some fields changed, and saved when it
    parses: what was saved, or the refusals."""
    parsed = parse(valid_form(**overrides), load(learner), 0.0, BAND_NAMES)
    if not isinstance(parsed, dict):
        save(learner, parsed)
    return parsed


def test_the_timezone_is_shown_and_edited_in_settings(learner: LearnerStore) -> None:
    hello(learner, "Europe/Paris")
    assert form_values(load(learner))["timezone"] == "Europe/Paris"
    submitted(learner, timezone="America/Sao_Paulo")
    assert form_values(load(learner))["timezone"] == "America/Sao_Paulo"
    hello(learner, "Europe/Paris")  # the browser's zone no longer applies
    assert load(learner).timezone == "America/Sao_Paulo"


def test_a_timezone_that_names_none_is_refused_in_settings(learner: LearnerStore) -> None:
    submitted(learner, timezone="America/Sao_Paulo")
    refused = submitted(learner, timezone="Atlantis/Capital")
    assert isinstance(refused, dict)
    assert refused["timezone"].startswith("Time zone:")
    assert load(learner).timezone == "America/Sao_Paulo"


def test_a_blank_timezone_gives_the_learner_the_machines_day_until_the_next_hello(
    learner: LearnerStore,
) -> None:
    submitted(learner, timezone="America/Sao_Paulo")
    submitted(learner, timezone="")
    assert load(learner).timezone is None
    hello(learner, "Asia/Tokyo")
    assert load(learner).timezone == "Asia/Tokyo"


def test_a_form_without_the_timezone_field_keeps_the_stored_one(learner: LearnerStore) -> None:
    """Local mode's settings page has no time zone field: saving it leaves the setting be."""
    hello(learner, "Europe/Paris")
    form = valid_form()
    form.pop("timezone", None)
    parsed = parse(form, load(learner), 0.0, BAND_NAMES)
    assert not isinstance(parsed, dict)
    save(learner, parsed)
    assert load(learner).timezone == "Europe/Paris"


class ManualClock:
    """A clock the test moves by hand."""

    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.mark.usefixtures("machine_in_utc")
def test_local_mode_takes_hello_but_keeps_the_machines_day_and_shows_no_timezone() -> None:
    """The browser in Auckland says hello; rounds either side of Auckland's midnight still land
    on the machine's one day, and the settings page offers no time zone to edit."""
    store, clock = Store.in_memory(), ManualClock(BEFORE - 60)
    app = create_app(E4_E5, rng=seeded_for_rounds("white", "white"), store=store, clock=clock)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "hello", "tz": ZONE})
            assert ws.receive_json()["type"] == "round"  # the hello is answered with nothing
            clock.now = BEFORE
            play(ws, "a2a3")
            ws.send_json({"type": "next"})
            assert ws.receive_json()["type"] == "round"
            clock.now = AFTER
            play(ws, "a2a3")
        assert 'name="timezone"' not in client.get("/settings").text
    assert [row["day"] for row in store.implicit().daily_scores()] == ["2026-03-10"]
