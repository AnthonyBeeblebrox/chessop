"""Lichess sign-in (public spec §5, ADR 0008): proving a Lichess identity, and keeping nothing else.

OAuth2 with PKCE, with no client secret and no scope. The browser is sent to Lichess with a
`state` and the challenge of a verifier, both random and held here, in memory, for 10 minutes;
Lichess sends it back with the `state` and a code. The `state` is good once, and only in the
browser that began: the one whose cookie is the same as it was then (asking to sign in sets no
cookie, so a browser with none is told from another only by having none). The code and the
verifier buy a token, the token is asked once whose it is, and it is revoked at once. Nothing of
it is stored.

The `client_id` and the `redirect_uri` come from the site's base URL, never from a request.

Lichess itself is reached through a `LichessClient` the app is given: `HttpLichess` is the real
one.
"""

import base64
import hashlib
import http.client
import json
import secrets
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode, urlsplit

from chessop.clock import Clock
from chessop.memory import MINUTE

LICHESS = "https://lichess.org"
CALLBACK = "/signin/lichess/callback"  # where Lichess sends the browser back
LIFE = 10 * MINUTE  # how long a sign-in begun can take at Lichess
PENDING = 1000  # sign-ins begun and held at once; past it the oldest is forgotten
TIMEOUT = 10  # seconds Lichess is waited for


@dataclass(frozen=True)
class LichessIdentity:
    """Who a token is: `id` never changes, `username` is it as its holder writes it."""

    id: str
    username: str


class LichessClient(Protocol):
    """What reaches Lichess. No call raises when Lichess refuses or cannot be reached."""

    def token(self, code: str, verifier: str, redirect_uri: str, client_id: str) -> str | None:
        """The access token `code` buys with the `verifier` of the challenge it was asked
        with, None when it buys none."""
        ...

    def account(self, token: str) -> LichessIdentity | None:
        """Whose `token` is, None when Lichess does not say."""
        ...

    def revoke(self, token: str) -> None:
        """Have `token` good for nothing more."""
        ...


class HttpLichess:
    """Lichess over HTTP, at `base`."""

    def __init__(self, base: str = LICHESS) -> None:
        self._base = base

    def token(self, code: str, verifier: str, redirect_uri: str, client_id: str) -> str | None:
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
        }
        answer = self._call("POST", "/api/token", data=urlencode(form).encode())
        token = answer.get("access_token") if isinstance(answer, dict) else None
        return token if isinstance(token, str) and token else None

    def account(self, token: str) -> LichessIdentity | None:
        answer = self._call("GET", "/api/account", token=token)
        if not isinstance(answer, dict):
            return None
        id, username = answer.get("id"), answer.get("username")
        if not isinstance(id, str) or not id or not isinstance(username, str) or not username:
            return None
        return LichessIdentity(id, username)

    def revoke(self, token: str) -> None:
        self._call("DELETE", "/api/token", token=token)

    def _call(
        self, method: str, path: str, data: bytes | None = None, token: str | None = None
    ) -> Any:
        """What Lichess answers, read as JSON; None when it refuses, cannot be reached or
        answers nothing that is JSON."""
        headers = {"Accept": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            self._base + path, data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return json.loads(response.read() or b"null")
        except (
            OSError,
            http.client.HTTPException,
            ValueError,
        ):  # refused, unreachable, cut short or not JSON
            return None


@dataclass(frozen=True)
class Pending:
    """A sign-in begun: the verifier of the challenge Lichess was sent, the browser that began
    (the hash of its cookie), where to go back to, and when it stops being good."""

    verifier: str
    browser: str
    back: str
    expires: float


class LichessSignIn:
    """The Lichess sign-ins of the site at `base_url`, Lichess reached through `client`."""

    def __init__(self, base_url: str, client: LichessClient, clock: Clock) -> None:
        self._client = client
        self._clock = clock
        self._client_id = urlsplit(base_url).netloc
        self._redirect_uri = base_url + CALLBACK
        self._pending: dict[str, Pending] = {}  # by state, oldest first

    def begin(self, back: str, cookie: str) -> str:
        """Begin a sign-in in the browser holding `cookie`, to lead back to `back`: the address
        at Lichess to send the browser to."""
        now = self._clock()
        for state, pending in list(self._pending.items()):
            if pending.expires <= now or len(self._pending) >= PENDING:
                del self._pending[state]
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        self._pending[state] = Pending(verifier, _hash(cookie), back, now + LIFE)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        query = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "code_challenge_method": "S256",
            "code_challenge": challenge.rstrip(b"=").decode(),
            "state": state,
        }
        return f"{LICHESS}/oauth?{urlencode(query)}"

    def spend(self, state: str, cookie: str) -> Pending | None:
        """The sign-in begun with `state`, spending it; None when none was, when it is too old,
        or when it was begun in another browser than the one holding `cookie`."""
        pending = self._pending.pop(state, None)
        if pending is None or pending.expires <= self._clock():
            return None
        if not secrets.compare_digest(pending.browser, _hash(cookie)):
            return None
        return pending

    def identity(self, pending: Pending, code: str) -> LichessIdentity | None:
        """Whom the `code` Lichess sent back for `pending` proves, None when it proves no one.
        The token it buys is asked once whose it is, then revoked."""
        client = self._client
        token = client.token(code, pending.verifier, self._redirect_uri, self._client_id)
        if token is None:
            return None
        try:
            return client.account(token)
        finally:
            client.revoke(token)


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()
