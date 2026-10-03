"""`chessop maintain` (public spec §10, §13): what the site does every night with nothing to
remember. In order: write yesterday's row of the usage aggregate; warn the email accounts about
to be deleted; purge the learners no request came from for too long; back the database up into
the data directory's backups folder and upload it, encrypted, off the VPS (`chessop.backup`).

An anonymous learner is deleted after 12 months with no request, after 30 days when they logged
fewer than 5 rounds. An account is deleted after 24 months with no request: an email account is
warned by email at 23 months and deleted only once its warning is 30 days old, so a warning that
did not go delays the deletion, and any request clears the warning (`LearnerStore.seen`); a
Lichess account has no address and is deleted with no warning. 12 months are 365 days, as the
cookie's are, 24 months 730, and 23 months 30 days short of that.

Each step is idempotent and prints its counts; no step prints an address itself. A step that
fails is reported on standard error and does not stop the later ones.
"""

import sys
from collections.abc import Callable
from pathlib import Path

from chessop import backup
from chessop.clock import utc_day
from chessop.mail import Courier, MailError, Message
from chessop.memory import DAY
from chessop.store import Store

ANONYMOUS_IDLE = 365 * DAY  # 12 months
FEW_ROUNDS = 5  # an anonymous learner with fewer goes sooner
FEW_ROUNDS_IDLE = 30 * DAY
ACCOUNT_IDLE = 730 * DAY  # 24 months
NOTICE = 30 * DAY  # how old an email account's warning is before it is deleted
WARN_AFTER = ACCOUNT_IDLE - NOTICE  # 23 months


def warning(to: str, base_url: str) -> Message:
    """What an email account unseen for 23 months is told."""
    return Message(
        to=to,
        subject="Your chessop account will be deleted in 30 days",
        body=(
            "You have not visited chessop for 23 months.\n\n"
            "To keep your account and your history, sign in within 30 days:\n\n"
            f"{base_url}/signin\n\n"
            "If you do not, your account and everything stored with it are deleted. "
            "There is nothing to do if that is what you want.\n"
        ),
    )


def run(
    store: Store,
    courier: Courier,
    base_url: str,
    backups: Path,
    off_site: backup.OffSite | None,
    now: float,
) -> bool:
    """Every step at `now`, in order, each printing its counts, the backup taken into the folder
    `backups` and uploaded to `off_site`: whether all of them succeeded."""

    def aggregate() -> str:
        yesterday = utc_day(now - DAY)
        if store.write_usage_day(yesterday, now):
            return f"wrote {yesterday}"
        return f"{yesterday} already written"

    def warnings() -> str:
        unseen_since = now - WARN_AFTER
        sent, unsent = 0, []
        for account in store.accounts_to_warn(unseen_since):
            try:
                courier.deliver(warning(account.identity, base_url))
            except MailError as e:
                unsent.append(e)
                continue
            store.warned(account.learner_id, unseen_since, now)
            sent += 1
        if unsent:
            raise MailError(f"{sent} warned, {len(unsent)} not warned: {unsent[0]}")
        return f"{sent} warned"

    steps: tuple[tuple[str, Callable[[], str]], ...] = (
        ("aggregate", aggregate),
        ("warnings", warnings),
        (
            "anonymous learners unseen for 12 months",
            lambda: f"{store.purge_anonymous(now - ANONYMOUS_IDLE, now)} deleted",
        ),
        (
            f"anonymous learners with fewer than {FEW_ROUNDS} rounds unseen for 30 days",
            lambda: f"{store.purge_anonymous(now - FEW_ROUNDS_IDLE, now, FEW_ROUNDS)} deleted",
        ),
        (
            "accounts unseen for 24 months",
            lambda: f"{store.purge_accounts(now - ACCOUNT_IDLE, now - NOTICE, now)} deleted",
        ),
        ("backup", lambda: backup.take(store, backups, now)),
        ("upload", lambda: backup.upload(backups, now, off_site)),
    )
    succeeded = True
    for name, step in steps:
        try:
            print(f"chessop maintain: {name}: {step()}", flush=True)
        except Exception as e:
            succeeded = False
            print(f"chessop maintain: {name} failed: {e}", file=sys.stderr, flush=True)
    return succeeded
