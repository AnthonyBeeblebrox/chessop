"""Your data's download (public spec §10): everything stored about one learner, as one JSON file
generated on request and streamed, never stored.

The file holds the format version, the export time and the learner's snapshot version; their
account (kind, email address or Lichess username, created) or null; when the learner was created
and last seen; their settings; every position record; the full round log; and the daily scores.
Positions are written as FEN, times as ISO 8601 in UTC. It holds no session token or hash, and no
recall estimate: none computed for the export, and not the ones the round log noted before each
round.
"""

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from chessop.memory import Record
from chessop.store import Account, LearnerStore

FORMAT_VERSION = 1
BATCH = 500  # round log rows read at a time


def filename(learner: LearnerStore, now: float) -> str:
    """The file's name: the export's day on the learner's calendar."""
    return f"chessop-data-{learner.day(now)}.json"


async def export(learner: LearnerStore, account: Account | None, now: float) -> AsyncIterator[str]:
    """The file, in pieces: everything but the round log first, then the round log a batch of
    rows at a time."""
    head = {
        "format_version": FORMAT_VERSION,
        "exported_at": _time(now),
        "snapshot_version": learner.snapshot_version,
        "account": None if account is None else _account(account),
        "learner": {"created": _time(learner.created), "last_seen": _time(learner.last_seen)},
        "settings": learner.settings(),
        "position_records": [
            {"fen": fen(epd), **_record(record)}
            for epd, record in sorted(learner.records().items())
        ],
        "daily_scores": [
            {**row, "updated_at": _time(row["updated_at"])} for row in learner.daily_scores()
        ],
    }
    yield json.dumps(head)[:-1] + ', "round_log": ['
    after = 0
    while rows := learner.round_log(after, BATCH):
        yield ("" if after == 0 else ", ") + ", ".join(json.dumps(_round(row)) for row in rows)
        after = rows[-1]["id"]
    yield "]}"


def fen(epd: str) -> str:
    """The position `epd` as FEN. Its move counters are nominal, at their start values: a
    position, whatever move order reached it, has no move number of its own."""
    return f"{epd} 0 1"


def _account(account: Account) -> dict[str, Any]:
    if account.kind == "email":
        identity = {"email": account.identity}
    else:  # a Lichess account is shown by its username
        identity = {"lichess_username": account.name}
    return {"kind": account.kind, **identity, "created": _time(account.created)}


def _record(record: Record) -> dict[str, Any]:
    return {
        "passes": record.passes,
        "misses": record.misses,
        "last_pass": _time(record.last_pass),
        "relearning_owed": record.relearn,
    }


def _round(row: dict[str, Any]) -> dict[str, Any]:
    """A round log row as the file has it: its positions as FEN, its times in UTC, and each
    visited position's record before the round without the recall estimate noted with it."""
    return {
        "started_at": _time(row["started_at"]),
        "ended_at": _time(row["ended_at"]),
        "side": row["side"],
        "path": row["path"],
        "outcome": row["outcome"],
        "end_fen": fen(row["end_epd"]),
        "plies": row["plies"],
        "before": {
            fen(epd): _record(Record(r["passes"], r["misses"], r["last_pass"], r["relearn"]))
            for epd, r in row["before"].items()
        },
        "snapshot_version": row["snapshot_version"],
    }


def _time(at: float | None) -> str | None:
    """`at` as ISO 8601 in UTC, None for none."""
    if at is None:
        return None
    return datetime.fromtimestamp(at, UTC).isoformat().replace("+00:00", "Z")
