"""The hosted site's limits (public spec §6): counters in memory, lost on restart.

A `Limit` allows so many events per key in any window of so many seconds; a key's counter is
dropped once its window has passed. A client is its IPv4 address or its IPv6 /64 prefix, as the
forwarded header gives it (the server trusts that header from the proxy only). No address is
ever logged.

`Limits` holds every limit of the hosted site but the sign-in emails' (`chessop.signin`); local
mode has `Unlimited`, which never refuses anything. Past an HTTP limit the answer is a 429 that
says how long to wait (`slow_down`).

Two limits refuse no one outright. At `LIVE_SESSIONS` learner sessions the site is full: a new
session is refused with `Full`, answered by `full` (a 503) or a socket closed with `FULL_CLOSE`,
and the running sessions go on; the count is `chessop.hosted.CookieLearners`'s. Past
`NEW_LEARNERS_PER_HOUR` from one client, the next visitor plays as a throwaway learner
(`chessop.hosted`).
"""

import ipaddress
import math
from collections import Counter, OrderedDict, deque
from collections.abc import Callable

from starlette.requests import HTTPConnection
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from chessop.clock import Clock

MINUTE = 60.0
REQUESTS_PER_MINUTE = 120  # per client, on every route but `/healthz` and the static files
HOUR = 3600.0
SAVES_PER_MINUTE = 10  # settings saves, per learner
DOWNLOADS_PER_HOUR = 5  # downloads of everything stored, per learner
# A socket may send a burst of so many messages, then so many a second, each so many bytes at
# most: past that it is closed with code 1008.
MESSAGE_BURST = 20
MESSAGES_PER_SECOND = 5
MESSAGE_BYTES = 1024
# The server reads no socket message past this many bytes: it closes the socket with code 1009
# first, so that one huge message is not taken in whole before `MESSAGE_BYTES` refuses it.
FRAME_BYTES = 64 * 1024
# Past so many open sockets, a new one is refused.
SOCKETS_PER_LEARNER = 10
SOCKETS_PER_CLIENT = 40
LIVE_SESSIONS = 300  # learner sessions in the process, server-wide: past it the site is full
FULL = "chessop is full right now, try again in a few minutes"
FULL_CLOSE = 1013  # the code a socket refused by a full site is closed with (public spec G5)
NEW_LEARNERS_PER_HOUR = 30  # anonymous learners created, per client


class Limit:
    """At most `count` events per key in any `window` seconds, by `clock`."""

    def __init__(self, count: int, window: float, clock: Clock) -> None:
        self._count = count
        self._window = window
        self._clock = clock
        # Each key's events, oldest first; the keys in the order of their latest event.
        self._events: OrderedDict[str, deque[float]] = OrderedDict()

    def reached(self, key: str) -> bool:
        """Whether `key` has had all the events its window allows."""
        return self._wait(key) is not None

    def add(self, key: str) -> None:
        """Count one event for `key`, now."""
        self._events.setdefault(key, deque()).append(self._clock())
        self._events.move_to_end(key)

    def take(self, key: str) -> float | None:
        """Count one event for `key` now, unless its window is full: None when counted, the
        seconds until the next is allowed when not."""
        wait = self._wait(key)
        if wait is None:
            self.add(key)
        return wait

    def _wait(self, key: str) -> float | None:
        """The seconds until `key` may have another event, None when it may now."""
        now = self._clock()
        horizon = now - self._window
        events = self._events
        # The keys whose latest event left the window come first: dropped whole.
        while events:
            oldest_key, oldest = next(iter(events.items()))
            if oldest[-1] > horizon:
                break
            del events[oldest_key]
        mine = events.get(key)
        if mine is None:
            return None
        while mine[0] <= horizon:
            mine.popleft()
        return mine[0] + self._window - now if len(mine) >= self._count else None


def client(host: str) -> str:
    """The client a request from `host` counts as: an IPv4 address, or an IPv6 /64 prefix."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host
    if address.version == 6:
        return str(ipaddress.ip_network((address, 64), strict=False).network_address)
    return str(address)


def client_of(conn: HTTPConnection) -> str:
    """The client a request or a socket comes from (`client`)."""
    return client(conn.client.host if conn.client else "")


def slow_down(wait: float) -> Response:
    """The answer past an HTTP limit: a 429 asking to wait `wait` seconds, rounded up."""
    seconds = max(1, math.ceil(wait))
    return PlainTextResponse(
        f"Slow down: try again in {seconds} second{'' if seconds == 1 else 's'}.",
        status_code=429,
        headers={"Retry-After": str(seconds)},
    )


class Full(Exception):
    """The site has all the live learner sessions it may: this one is not begun."""


def full() -> Response:
    """The answer to a page request a full site refuses: a 503 with the one sentence."""
    return PlainTextResponse(FULL, status_code=503)


class Limits:
    """The hosted site's limits, counted by `clock`."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._requests = Limit(REQUESTS_PER_MINUTE, MINUTE, clock)
        self._saves = Limit(SAVES_PER_MINUTE, MINUTE, clock)
        self._downloads = Limit(DOWNLOADS_PER_HOUR, HOUR, clock)
        self._new_learners = Limit(NEW_LEARNERS_PER_HOUR, HOUR, clock)
        self._by_client: Counter[str] = Counter()  # open sockets
        self._by_learner: Counter[int] = Counter()

    def request(self, client: str) -> float | None:
        """Count a request from `client`: None when allowed, else the seconds to wait."""
        return self._requests.take(client)

    def save(self, learner_id: int) -> float | None:
        """Count a settings save by the learner: None when allowed, else the seconds to wait."""
        return self._saves.take(str(learner_id))

    def download(self, learner_id: int) -> float | None:
        """Count a download of the learner's data: None when allowed, else the seconds to
        wait."""
        return self._downloads.take(str(learner_id))

    def new_learner(self, client: str) -> bool:
        """Count an anonymous learner created for `client`, unless it has had all its hour
        allows: whether it was counted."""
        return self._new_learners.take(client) is None

    def spent(self, client: str) -> bool:
        """Whether `client` has had all the new anonymous learners its hour allows."""
        return self._new_learners.reached(client)

    def admits(self, client: str) -> bool:
        """Whether `client` may open another socket, as far as its own count goes."""
        return self._by_client[client] < SOCKETS_PER_CLIENT

    def socket(self, client: str, learner_id: int | None) -> "Allowance | None":
        """The allowance of a socket `client` opens now for the learner, None when it is
        refused: either already has all the open sockets it may. `Allowance.close` lets it go.
        A throwaway learner has no id: its one socket counts for the client only."""
        if not self.admits(client):
            return None
        if learner_id is not None and self._by_learner[learner_id] >= SOCKETS_PER_LEARNER:
            return None
        self._by_client[client] += 1
        if learner_id is not None:
            self._by_learner[learner_id] += 1

        def release() -> None:
            _let_go(self._by_client, client)
            if learner_id is not None:
                _let_go(self._by_learner, learner_id)

        return Allowance(self._clock, release)


class Allowance:
    """What one socket may send, by `clock`: `MESSAGE_BURST` messages at once, then
    `MESSAGES_PER_SECOND` a second, none over `MESSAGE_BYTES`."""

    def __init__(self, clock: Clock, release: Callable[[], None]) -> None:
        self._clock = clock
        self._release: Callable[[], None] | None = release
        self._tokens = float(MESSAGE_BURST)  # the messages it may send at once now
        self._at = clock()  # when `_tokens` was last brought up to date

    def message(self, size: int) -> bool:
        """Count a message of `size` bytes: whether the socket may send it."""
        now = self._clock()
        self._tokens = min(MESSAGE_BURST, self._tokens + (now - self._at) * MESSAGES_PER_SECOND)
        self._at = now
        if size > MESSAGE_BYTES or self._tokens < 1:
            return False
        self._tokens -= 1
        return True

    def close(self) -> None:
        """The socket closed: it no longer counts as open. Closing again does nothing."""
        if self._release is not None:
            self._release()
            self._release = None


class Unlimited:
    """Local mode's limits: none. Its one learner is the machine's owner."""

    def save(self, learner_id: int) -> float | None:
        return None

    def admits(self, client: str) -> bool:
        return True

    def socket(self, client: str, learner_id: int | None) -> "Unmetered":
        return Unmetered()


class Unmetered:
    """A local socket's allowance: anything."""

    def message(self, size: int) -> bool:
        return True

    def close(self) -> None:
        pass


class PerClient:
    """Middleware: past `REQUESTS_PER_MINUTE` from one client, a request is answered with
    `slow_down` instead of being handled. `/healthz` and the static files are exempt."""

    def __init__(self, app: ASGIApp, limits: Limits) -> None:
        self.app = app
        self.limits = limits

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and not _exempt(scope["path"]):
            wait = self.limits.request(client_of(HTTPConnection(scope)))
            if wait is not None:
                await slow_down(wait)(scope, receive, send)
                return
        await self.app(scope, receive, send)


def _let_go[K](counter: Counter[K], key: K) -> None:
    """One fewer for `key`, dropped at none."""
    counter[key] -= 1
    if counter[key] <= 0:
        del counter[key]


def _exempt(path: str) -> bool:
    """Whether a request for `path` is never limited: the health check, a static file."""
    return path == "/healthz" or path.startswith("/static/")
