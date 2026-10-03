"""The mail the hosted site sends (public spec §1, §5): through a mailer the app is given.

`TemMailer` sends through Scaleway Transactional Email's HTTP API (Paris), from the site's
sender; the site uses it when it has a mail key, which an `https` base URL requires (public spec
G2). `ConsoleMailer` is the development implementation, used when the site has no mail key: it
prints each message instead of sending it.

Both have `send`, for the site: it hands a message over and goes on, so no request waits on
mail, and a message that could not go is logged as an error with its recipient's address left
out. Both have `deliver`, for `chessop notify-owner`: it sends the message before returning and
raises `MailError` when it did not go. `chessop maintain` warns through it too, so that it knows
which warnings went.
"""

import json
import logging
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

# Scaleway Transactional Email's endpoint for sending, in its Paris region (ADR 0008).
TEM_URL = "https://api.scaleway.com/transactional-email/v1alpha1/regions/fr-par/emails"
SENDER_NAME = "chessop"  # the name the site's mail is from, beside its address
TIMEOUT = 10.0  # seconds one delivery waits on Scaleway

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Message:
    """One plain-text message to one address."""

    to: str
    subject: str
    body: str


class MailError(Exception):
    """A message that did not go."""


class Mailer(Protocol):
    """What sends the site's mail."""

    def send(self, message: Message) -> None:
        """Send `message`. Never raises for a message that could not be delivered."""
        ...


class Courier(Protocol):
    """What delivers a command's mail (`chessop notify-owner`, `chessop maintain`)."""

    def deliver(self, message: Message) -> None:
        """Send `message` before returning; `MailError` when it did not go."""
        ...


class ConsoleMailer:
    """The mailer of a site with no mail key: every message is printed to the console."""

    def send(self, message: Message) -> None:
        print(
            f"chessop: mail to {message.to}\nSubject: {message.subject}\n\n{message.body}",
            flush=True,
        )

    def deliver(self, message: Message) -> None:
        """Print `message`, as `send` does: printing never fails."""
        self.send(message)


class TemMailer:
    """The mailer of a site with a mail key: Scaleway Transactional Email, with `secret_key`
    for the project `project_id`, from `sender`. `send` delivers on a thread of its own, so the
    request that asked for the message never waits on Scaleway."""

    def __init__(self, secret_key: str, project_id: str, sender: str) -> None:
        self._secret_key = secret_key
        self._project_id = project_id
        self._sender = sender
        self._url = TEM_URL
        self._background = ThreadPoolExecutor(max_workers=2, thread_name_prefix="chessop-mail")

    def deliver(self, message: Message) -> None:
        body = {
            "from": {"email": self._sender, "name": SENDER_NAME},
            "to": [{"email": message.to}],
            "subject": message.subject,
            "text": message.body,
            "project_id": self._project_id,
        }
        request = urllib.request.Request(
            self._url,
            data=json.dumps(body).encode(),
            headers={"X-Auth-Token": self._secret_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT):
                pass
        except urllib.error.HTTPError as e:
            raise MailError(f"Scaleway answered {e.code} {e.reason}") from None
        except (urllib.error.URLError, OSError) as e:
            raise MailError(f"Scaleway could not be reached: {e}") from None

    def send(self, message: Message) -> None:
        self._background.submit(self._deliver_or_log, message)

    def _deliver_or_log(self, message: Message) -> None:
        try:
            self.deliver(message)
        except Exception as e:
            log.error("mail %r not sent: %s", message.subject, e)
