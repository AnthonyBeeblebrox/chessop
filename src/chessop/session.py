"""A learner session: what the running process holds of one learner (public spec §4).

Their own steering state (the needs of their records, the times they faced each move), the tabs
they have open and the notices owed to them, over the repertoire, ledger and steering caches
they share with every learner of the same settings (`chessop.shared`). Local mode has one, for
its one learner, for the life of the process; hosted mode loads one per learner and drops it
when idle (`chessop.hosted`).

A change of choices or a reset regenerates that learner's repertoire only (spec §4, §7): what
the new settings share is built off the event loop when no learner has it yet, the steering
starts over on it keeping the times faced, and each of their open tabs abandons its round
unrecorded and receives a fresh `round`. Records are never touched by a change of choices; a
reset deletes only position records.
"""

import asyncio
import random
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field, replace
from typing import Any, Literal, Protocol

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.requests import HTTPConnection

from chessop.choices import Choices
from chessop.clock import Clock
from chessop.explanations import Explanations
from chessop.graph import DEFAULT_BAND
from chessop.play import Round
from chessop.progress import Ledger
from chessop.shared import Shared, SharedCache
from chessop.steering import Steering, faced_from_log
from chessop.store import MOVED_FROM_BAND, TIMEZONE, LearnerStore

# The setting noting that the learner was given the notice owed after their first round.
TOLD_AFTER_FIRST_ROUND = "told_after_first_round"


@dataclass(eq=False)
class Tab:
    """One open play page: its socket and its round, changed under its lock."""

    sock: WebSocket
    round: Round | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


@dataclass(frozen=True)
class Drill:
    """What every learner session of the process drills with."""

    rng: random.Random
    explanations: Explanations | None
    shared: SharedCache  # what learners with the same settings share
    clock: Clock


class Session:
    """One learner's session, drilling by `choices` over `shared`, what their settings share.

    `sets_params` says whether the memory model's parameters are this learner's to set; when
    not, `choices.params` are the server's. `after_first_round` is a notice to give them once,
    ever, when they have ended a round. `unsaved` is the notice a learner whose history is kept
    nowhere is given with every round (a throwaway learner, `chessop.hosted`), None for every
    other. "This session" counts from `start`; `active` is the last
    moment the learner made a request or closed a socket."""

    def __init__(
        self,
        drill: Drill,
        learner: LearnerStore,
        shared: Shared,
        choices: Choices,
        *,
        sets_params: bool = True,
        after_first_round: str | None = None,
        unsaved: str | None = None,
    ) -> None:
        self.drill = drill
        self.learner = learner
        self.choices = choices
        self.sets_params = sets_params
        self.unsaved = unsaved
        self.start = self.active = drill.clock()
        self._shared = shared
        self.graph, self.repertoire = shared.repertoire.graph, shared.repertoire
        log = learner.round_log()
        self.steering = Steering(
            self.repertoire, learner.record, choices.params, faced_from_log(log), shared.reach
        )
        self.tabs: set[Tab] = set()
        # Told once on each surface, then never again (spec §3.3).
        notice = " ".join(
            filter(
                None,
                (
                    band_notice(learner, self.graph.band),
                    snapshot_notice(learner, self.graph.version),
                ),
            )
        )
        self._notices = {"play": notice, "progress": notice} if notice else {}
        self.played = bool(log)  # whether the learner has ever ended a round
        self._after_first_round = (
            None if learner.setting(TOLD_AFTER_FIRST_ROUND, False) else after_first_round
        )

    def touch(self, now: float) -> None:
        """Note that the learner was here at `now`."""
        self.active = now
        self.learner.seen(now)

    def new_round(self) -> Round:
        drill = self.drill
        return Round(
            self.repertoire,
            drill.rng,
            self.learner,
            self.choices.params,
            self.steering,
            drill.explanations,
            drill.clock,
        )

    async def open_tab(self, sock: WebSocket) -> Tab:
        """A tab on `sock`, its first round begun and sent."""
        tab = Tab(sock)
        async with tab.lock:
            tab.round = self.new_round()
            self.tabs.add(tab)
            await sock.send_json(self.start_message(tab, first=True))
        return tab

    def close_tab(self, tab: Tab) -> None:
        """The tab's socket closed: its round is abandoned."""
        self.tabs.discard(tab)
        self.active = self.drill.clock()

    async def retire(self) -> None:
        """The learner's history changed hands: every tab's round is abandoned unrecorded and
        its socket closed, so the play page reconnects to the session that replaces this one."""
        tabs, self.tabs = self.tabs, set()
        for tab in tabs:  # before anything is awaited: no round of this session commits after
            tab.round = None
        for tab in tabs:
            with suppress(RuntimeError, WebSocketDisconnect):
                await tab.sock.close(code=1012)

    def move(self, round: Round, frm: str, to: str) -> list[dict[str, Any]]:
        """Judge the learner's move in `round`: the messages to send back, in order."""
        replies = round.move(frm, to)
        self.played = self.played or not round.in_flight
        return replies

    def tell(self, surface: Literal["play", "progress"]) -> str | None:
        """The pending notice for `surface`, once: every later call has none."""
        notices = [self._notices.pop(surface, None)]
        if self._after_first_round is not None and self.played:
            notices.append(self._after_first_round)
            self._after_first_round = None
            self.learner.set_setting(TOLD_AFTER_FIRST_ROUND, True)
        return " ".join(filter(None, notices)) or None

    def start_message(self, tab: Tab, *, first: bool) -> dict[str, Any]:
        """The tab's `round` message, carrying the play page's notice if it is still pending."""
        assert tab.round is not None
        notice = " ".join(filter(None, (self.unsaved, self.tell("play")))) or None
        return {**tab.round.start_message(first=first), "notice": notice}

    def current_choices(self) -> Choices:
        """The choices as stored now: the `m` key writes the sound too, and the play page's
        `hello` the time zone."""
        return replace(
            self.choices,
            sound=bool(self.learner.setting("sound", True)),
            timezone=self.learner.setting(TIMEZONE, None),
        )

    def ledger(self) -> Ledger:
        """The ledger over the repertoire with nothing opted out: opted-out openings stay listed."""
        return self._shared.ledger

    async def regenerate(self, new: Choices, forget: Callable[[], None] | None = None) -> None:
        """Drill by `new` from now on, the steering started over, then give every tab a fresh
        round. `EmptyRepertoire`, before anything changes, when `new` leaves nothing to drill.

        `forget`, a reset's delete, runs once every round in flight is dropped, with nothing
        awaited in between: no round begun on the records it deletes can commit after it."""
        shared = self._shared  # a reset keeps the settings: nothing is awaited at all
        if new.settings != self.choices.settings:
            shared = await self.drill.shared.get(new.settings)  # off the event loop when built
        for tab in self.tabs:
            tab.round = None  # abandoned: it never commits
        if forget is not None:
            forget()
        self._shared = shared
        self.graph, self.repertoire = shared.repertoire.graph, shared.repertoire
        self.steering = Steering(
            self.repertoire, self.learner.record, new.params, self.steering.faced, shared.reach
        )
        self.choices = new
        for tab in list(self.tabs):
            async with tab.lock:
                tab.round = self.new_round()
                try:
                    await tab.sock.send_json(self.start_message(tab, first=False))
                except (WebSocketDisconnect, RuntimeError):
                    self.tabs.discard(tab)


def snapshot_notice(learner: LearnerStore, version: str) -> str | None:
    """Record `version` as the snapshot the learner's repertoire comes from; the notice to give
    them when it differs from the one recorded before (spec §3.3), None on a first start or no
    change.

    The repertoire is generated from the loaded snapshot at every start, so a change needs no more
    than recording it: no record is touched."""
    before = learner.snapshot_version
    if before == version:
        return None
    learner.set_snapshot_version(version)
    if before is None:
        return None
    return (
        f"The opening snapshot changed from {before} to {version}: your repertoire was"
        " regenerated from it. Your history is kept."
    )


def band_notice(learner: LearnerStore, band: str) -> str | None:
    """The notice owed to a learner whom the move to direct band choice took off the old default
    band (public spec §3), None when none is owed. Given once: asking settles it. It waits while
    `band`, the one drilled, is not yet the new default (a snapshot built before the open bands)."""
    before = learner.setting(MOVED_FROM_BAND, None)
    if before is None or band != DEFAULT_BAND:
        return None
    learner.unset_setting(MOVED_FROM_BAND)
    return (
        f"The default rating band is now {DEFAULT_BAND}, not {before}: your repertoire was"
        " regenerated for it. Your history is kept. You can choose another band in settings."
    )


class Learners(Protocol):
    """The current-learner seam (public spec §1): whose session a page request or a socket is
    for. Local mode has `ImplicitLearner`; hosted mode, `chessop.hosted.CookieLearners`."""

    async def visiting(self, conn: HTTPConnection) -> Session:
        """The session of the learner looking at a page. Looking creates no learner."""
        ...

    async def playing(self, conn: HTTPConnection) -> Session:
        """The session of the learner starting a round or saving a choice, the learner created
        when the browser has none."""
        ...

    def handshake(self, sock: WebSocket) -> list[tuple[bytes, bytes]]:
        """The headers the acceptance of `sock` must carry."""
        ...

    def leaving(self, session: Session) -> None:
        """A socket `playing` gave `session` to is closed, or was never accepted."""
        ...


class ImplicitLearner:
    """Local mode's learners: one, never asked who they are (ADR 0002)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    async def visiting(self, conn: HTTPConnection) -> Session:
        self.session.touch(self.session.drill.clock())
        return self.session

    playing = visiting

    def handshake(self, sock: WebSocket) -> list[tuple[bytes, bytes]]:
        return []

    def leaving(self, session: Session) -> None:
        pass
