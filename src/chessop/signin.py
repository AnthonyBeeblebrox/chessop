"""Email sign-in (public spec §5, ADR 0008): proving an address with no password.

One message carries a link and a 6-digit code, both good once and for 15 minutes; the store
keeps their hashes only. The link's token is 256 random bits and works from any browser. The
code is short, so it is good only together with the **binding**: a random value the page that
asked for the message holds in its form, never mailed and in no cookie. Five wrong codes exhaust
a pending sign-in's code, and a resend from that page keeps the count; its link still works.

Whether a message was sent is never told: an address with no account gets the same message, and
past a limit (3 per address per 15 minutes, 10 per client per hour, 250 per day for the whole
site) none is sent.

An email account changes its address the same way, with a link only: mailed to the new address,
good once and for 15 minutes, its hash kept, it opens a page whose button makes the change. The
learner's newest request is the only one whose link works.
"""

import hashlib
import secrets
from urllib.parse import quote

from chessop.clock import Clock
from chessop.limits import Limit
from chessop.mail import Mailer, Message
from chessop.memory import DAY, HOUR, MINUTE
from chessop.store import PendingSignIn, Store

LIFE = 15 * MINUTE  # how long a link and its code are good
TRIES = 5  # wrong codes before a pending sign-in's code is dead
CONFIRM = "/signin/confirm"  # the page the link opens
CHANGE = "/account/email/confirm"  # the page an email change's link opens


def address(typed: str) -> str | None:
    """The email address `typed` is, as accounts are keyed by it; None when it is not one."""
    email = typed.strip().lower()
    name, at, domain = email.rpartition("@")
    if (
        not at
        or not name
        or "." not in domain
        or len(email) > 254
        or any(c.isspace() for c in email)
    ):
        return None
    return email


def local(target: str | None) -> str:
    """Where to go back to after signing in: `target` when it is a path on this site, the play
    page otherwise."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return "/"
    # A browser drops control characters from an address and reads a backslash as a slash.
    if "\\" in target or any(ord(c) < 32 or ord(c) == 127 for c in target):
        return "/"
    return target


class EmailSignIn:
    """The pending sign-ins of the site at `base_url`, mailed through `mailer`."""

    def __init__(self, base_url: str, store: Store, mailer: Mailer, clock: Clock) -> None:
        self._base_url = base_url
        self._store = store
        self._mailer = mailer
        self._clock = clock
        self._per_address = Limit(3, 15 * MINUTE, clock)
        self._per_client = Limit(10, HOUR, clock)
        self._site_wide = Limit(250, DAY, clock)

    def _within_limits(self, email: str, client: str) -> bool:
        """Whether one more message to `email` asked by `client` is within every limit; if so,
        it is counted."""
        limits = ((self._per_address, email), (self._per_client, client), (self._site_wide, ""))
        if any(limit.reached(key) for limit, key in limits):
            return False
        for limit, key in limits:
            limit.add(key)
        return True

    def request(self, email: str, binding: str, client: str, back: str) -> None:
        """Mail `email` a link and a code; the code is good with `binding` only, and the link
        leads back to `back`. Nothing is sent past a limit, and nothing says so."""
        if not self._within_limits(email, client):
            return
        token = secrets.token_urlsafe(32)
        code = f"{secrets.randbelow(10**6):06d}"
        now = self._clock()
        self._store.request_sign_in(
            _hash(token), _hash(f"{binding}:{code}"), email, _hash(binding), now, now + LIFE
        )
        link = f"{self._base_url}{CONFIRM}?token={token}&next={quote(back, safe='')}"
        self._mailer.send(
            Message(
                to=email,
                subject="Sign in to chessop",
                body=(
                    "Open this link, then press Sign in:\n\n"
                    f"{link}\n\n"
                    f"Or type this code into the page that asked for it: {code}\n\n"
                    "Both work once, for 15 minutes. If you did not ask to sign in to chessop,"
                    " ignore this message.\n"
                ),
            )
        )

    def link_is_good(self, token: str) -> bool:
        """Whether the link carrying `token` can still sign in. Asking spends nothing."""
        return self._store.pending_sign_in(self._clock(), token_hash=_hash(token)) is not None

    def by_link(self, token: str) -> str | None:
        """The address the link carrying `token` proves, spending it; None when it proves none."""
        pending = self._store.pending_sign_in(self._clock(), token_hash=_hash(token))
        if pending is None:
            return None
        self._store.spend_sign_in(pending.token_hash)
        return pending.email

    def by_code(self, binding: str, code: str) -> str | None:
        """The address `code` proves in the browser holding `binding`, spending it; None when
        it proves none, which counts as a try."""
        pending = self._store.pending_sign_in(self._clock(), binding=_hash(binding))
        if pending is None or pending.tries >= TRIES:
            return None
        if not secrets.compare_digest(pending.code_hash, _hash(f"{binding}:{code.strip()}")):
            self._store.count_wrong_code(pending.token_hash)
            return None
        self._store.spend_sign_in(pending.token_hash)
        return pending.email

    def request_change(self, learner_id: int, email: str, client: str) -> None:
        """Mail `email` a link that makes it the address of the learner's account, within the
        limits of a sign-in message and as long-lived; it replaces the learner's earlier one.
        Nothing is sent past a limit, and nothing says so."""
        if not self._within_limits(email, client):
            return
        token = secrets.token_urlsafe(32)
        now = self._clock()
        self._store.request_email_change(_hash(token), email, learner_id, now, now + LIFE)
        self._mailer.send(
            Message(
                to=email,
                subject="Confirm your new chessop address",
                body=(
                    "Open this link, then press Confirm, to make this your chessop address:\n\n"
                    f"{self._base_url}{CHANGE}?token={token}\n\n"
                    "It works once, for 15 minutes. If you did not ask for this, ignore this"
                    " message: nothing changes.\n"
                ),
            )
        )

    def change_link_is_good(self, token: str) -> bool:
        """Whether the change link carrying `token` can still change an address. Asking spends
        nothing."""
        return self._pending_change(token) is not None

    def by_change_link(self, token: str) -> tuple[int, str] | None:
        """The learner the change link carrying `token` is for and the address it proves,
        spending it; None when it proves none."""
        pending = self._pending_change(token)
        if pending is None or pending.learner_id is None:
            return None
        self._store.spend_sign_in(pending.token_hash)
        return pending.learner_id, pending.email

    def _pending_change(self, token: str) -> PendingSignIn | None:
        return self._store.pending_sign_in(
            self._clock(), token_hash=_hash(token), purpose="email-change"
        )


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()
