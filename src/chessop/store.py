"""The one mutable store (spec §7, public spec §3): `<data-dir>/chessop.sqlite`.

One file holds every learner: `Store` is the file, `LearnerStore` one learner's position records,
round log, daily scores and settings in it. Local mode has one implicit learner (`Store.implicit`);
hosted mode's learners are reached through sessions, each the hash of a browser cookie's token.
A learner who signed in has an account; a pending sign-in is an emailed link and code not yet
used, or an emailed link to change an account's address (public spec §5). The daily usage
aggregate keeps counts only, one row per UTC day, never a learner id (public spec §12, G4).
The file runs in WAL mode with `synchronous=NORMAL` (ADR 0002): copy it through SQLite's backup
API only.

A learner's position records live in memory, loaded with the learner and written through at
every round end: the round's passes and miss applied, its `round_log` row appended and the day's
`daily_score` row upserted in one transaction, under one process-wide lock. A forced round is
logged but left out of the day's counts of rounds and successes. A round that never reaches
`commit` writes nothing. Records are keyed by learner and EPD and belong to no repertoire. The
schema grows by forward-only migrations counted in `schema_version`.
"""

import json
import sqlite3
import threading
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from chessop.clock import day, utc_day, utc_midnight
from chessop.memory import DAY, Record, Verdict
from chessop.repertoire import Side
from chessop.score import Scores

FILENAME = "chessop.sqlite"

IMPLICIT = 1  # the id of local mode's one learner

# The setting holding the band a learner was moved off, until they are told of it.
MOVED_FROM_BAND = "moved_from_band"
# The setting holding the learner's IANA time zone, which their days follow (public spec §3).
TIMEZONE = "timezone"

# What the migration to many learners makes of a v1 file's settings. Part of that migration:
# never edit. A declared rating fell in the first of these bands whose upper bound is above it.
_V1_CLOSED_BANDS = ((1200, "0-1200"), (1500, "1200-1500"), (1800, "1500-1800"), (2100, "1800-2100"))
_V1_TOP_BAND = "2100+"
_V1_DEFAULT_BAND = "1500-1800"  # what a v1 file with no declared rating drilled
_OPEN_DEFAULT_BAND = "1500+"

_HISTORY = ("position_record", "round_log", "daily_score")  # a learner's rows but settings
_PER_LEARNER = ("settings", *_HISTORY)
_MANY_LEARNERS_SCHEMA = (
    """CREATE TABLE learner (
        id INTEGER PRIMARY KEY,
        created REAL NOT NULL,
        last_seen REAL NOT NULL,
        snapshot_version TEXT
    )""",
    *(f"ALTER TABLE {table} RENAME TO {table}_v1" for table in _PER_LEARNER),
    """CREATE TABLE settings (
        learner_id INTEGER NOT NULL REFERENCES learner (id) ON DELETE CASCADE,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        PRIMARY KEY (learner_id, key)
    )""",
    """CREATE TABLE position_record (
        learner_id INTEGER NOT NULL REFERENCES learner (id) ON DELETE CASCADE,
        epd TEXT NOT NULL,
        passes INTEGER NOT NULL,
        misses INTEGER NOT NULL,
        last_pass REAL,
        relearn INTEGER NOT NULL,
        PRIMARY KEY (learner_id, epd)
    )""",
    """CREATE TABLE round_log (
        id INTEGER PRIMARY KEY,
        learner_id INTEGER NOT NULL REFERENCES learner (id) ON DELETE CASCADE,
        started_at REAL NOT NULL,
        ended_at REAL NOT NULL,
        side TEXT NOT NULL,
        path TEXT NOT NULL,
        outcome TEXT NOT NULL,
        end_epd TEXT NOT NULL,
        plies INTEGER NOT NULL,
        before TEXT NOT NULL,
        snapshot_version TEXT NOT NULL
    )""",
    "CREATE INDEX round_log_learner ON round_log (learner_id, id)",
    # `day` is the learner's local date (`LearnerStore.day`); the scores are the ones after the
    # day's last round.
    """CREATE TABLE daily_score (
        learner_id INTEGER NOT NULL REFERENCES learner (id) ON DELETE CASCADE,
        day TEXT NOT NULL,
        score REAL NOT NULL,
        white_score REAL NOT NULL,
        black_score REAL NOT NULL,
        rounds INTEGER NOT NULL,
        successes INTEGER NOT NULL,
        updated_at REAL NOT NULL,
        PRIMARY KEY (learner_id, day)
    )""",
)
_ROUND_COLUMNS = (
    "started_at, ended_at, side, path, outcome, end_epd, plies, before, snapshot_version"
)
_DAY_COLUMNS = "day, score, white_score, black_score, rounds, successes, updated_at"


def _to_many_learners(conn: sqlite3.Connection) -> None:
    """Key every table by learner. A v1 file holding anything gives its rows to the implicit
    learner; its declared rating becomes the closed band it mapped to, and with none declared
    it moves to 1500+ and the learner is owed a notice (public spec §3)."""
    for statement in _MANY_LEARNERS_SCHEMA:
        conn.execute(statement)
    if any(conn.execute(f"SELECT 1 FROM {t}_v1 LIMIT 1").fetchone() for t in _PER_LEARNER):
        settings = {
            key: json.loads(value)
            for key, value in conn.execute("SELECT key, value FROM settings_v1")
        }
        now = time.time()
        first, last = conn.execute(
            "SELECT MIN(started_at), MAX(ended_at) FROM round_log_v1"
        ).fetchone()
        conn.execute(
            "INSERT INTO learner (id, created, last_seen, snapshot_version) VALUES (?, ?, ?, ?)",
            (
                IMPLICIT,
                now if first is None else first,
                now if last is None else last,
                settings.pop("snapshot_version", None),
            ),
        )
        rating = settings.pop("rating", None)
        if "band" not in settings:  # a file that already chose its band directly keeps it
            if rating is None:
                settings["band"] = _OPEN_DEFAULT_BAND
                settings[MOVED_FROM_BAND] = _V1_DEFAULT_BAND
            else:
                settings["band"] = next(
                    (name for high, name in _V1_CLOSED_BANDS if rating < high), _V1_TOP_BAND
                )
        conn.executemany(
            "INSERT INTO settings (learner_id, key, value) VALUES (?, ?, ?)",
            [(IMPLICIT, key, json.dumps(value)) for key, value in settings.items()],
        )
        conn.execute(
            "INSERT INTO position_record (learner_id, epd, passes, misses, last_pass, relearn)"
            " SELECT ?, epd, passes, misses, last_pass, relearn FROM position_record_v1",
            (IMPLICIT,),
        )
        conn.execute(
            f"INSERT INTO round_log (id, learner_id, {_ROUND_COLUMNS})"
            f" SELECT id, ?, {_ROUND_COLUMNS} FROM round_log_v1",
            (IMPLICIT,),
        )
        conn.execute(
            f"INSERT INTO daily_score (learner_id, {_DAY_COLUMNS})"
            f" SELECT ?, {_DAY_COLUMNS} FROM daily_score_v1",
            (IMPLICIT,),
        )
    for table in _PER_LEARNER:
        conn.execute(f"DROP TABLE {table}_v1")


# Migration i (1-based) takes the file from version i - 1 to version i. Never edit one: append.
MIGRATIONS: tuple[tuple[str, ...] | Callable[[sqlite3.Connection], None], ...] = (
    (
        "CREATE TABLE schema_version (version INTEGER NOT NULL)",
        "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
        """CREATE TABLE position_record (
            epd TEXT PRIMARY KEY,
            passes INTEGER NOT NULL,
            misses INTEGER NOT NULL,
            last_pass REAL,
            relearn INTEGER NOT NULL
        )""",
        """CREATE TABLE round_log (
            id INTEGER PRIMARY KEY,
            started_at REAL NOT NULL,
            ended_at REAL NOT NULL,
            side TEXT NOT NULL,
            path TEXT NOT NULL,
            outcome TEXT NOT NULL,
            end_epd TEXT NOT NULL,
            plies INTEGER NOT NULL,
            before TEXT NOT NULL,
            snapshot_version TEXT NOT NULL
        )""",
    ),
    (
        # `day` is the machine's local date; the scores are the ones after the day's last round.
        """CREATE TABLE daily_score (
            day TEXT PRIMARY KEY,
            score REAL NOT NULL,
            white_score REAL NOT NULL,
            black_score REAL NOT NULL,
            rounds INTEGER NOT NULL,
            successes INTEGER NOT NULL,
            updated_at REAL NOT NULL
        )""",
    ),
    _to_many_learners,
    (
        # What a browser's cookie points to (public spec §3, §5): the hash of its token, never
        # the token. Unusable from `expires` on.
        """CREATE TABLE session (
            token_hash TEXT PRIMARY KEY,
            learner_id INTEGER NOT NULL REFERENCES learner (id) ON DELETE CASCADE,
            created REAL NOT NULL,
            last_used REAL NOT NULL,
            expires REAL NOT NULL
        )""",
    ),
    (
        # A sign-in identity attached to one learner (public spec §5): `kind` is `lichess` or
        # `email`, `identity` the Lichess id or the address.
        """CREATE TABLE account (
            learner_id INTEGER PRIMARY KEY REFERENCES learner (id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            identity TEXT NOT NULL,
            display_name TEXT NOT NULL,
            created REAL NOT NULL,
            warned_at REAL,
            UNIQUE (kind, identity)
        )""",
        # An emailed link and code not yet used: hashes only. `binding` is the hash of what the
        # requesting browser holds, which the code is good with; `purpose` is `sign-in` or
        # `email-change` (a link only: its `binding` is its token hash, its `code_hash` empty).
        """CREATE TABLE pending_sign_in (
            token_hash TEXT PRIMARY KEY,
            code_hash TEXT NOT NULL,
            email TEXT NOT NULL,
            binding TEXT NOT NULL UNIQUE,
            expires REAL NOT NULL,
            tries INTEGER NOT NULL DEFAULT 0,
            purpose TEXT NOT NULL
        )""",
    ),
    (
        # The learner whose account an `email-change` is for; None for a `sign-in`. Deleting
        # the learner deletes their pending change.
        "ALTER TABLE pending_sign_in"
        " ADD COLUMN learner_id INTEGER REFERENCES learner (id) ON DELETE CASCADE",
    ),
    (
        # The daily usage aggregate (public spec §12, G4): one row per UTC day, counts only,
        # never a learner id, kept forever. The events are counted as they happen; the derived
        # counts stay NULL until `written_at`, when the finished day's are written once.
        """CREATE TABLE daily_usage (
            day TEXT PRIMARY KEY,
            sign_ins INTEGER NOT NULL DEFAULT 0,
            adoptions INTEGER NOT NULL DEFAULT 0,
            deletions INTEGER NOT NULL DEFAULT 0,
            active_anonymous INTEGER,
            active_signed_in INTEGER,
            new_learners INTEGER,
            rounds INTEGER,
            successes INTEGER,
            written_at REAL
        )""",
    ),
)
SCHEMA_VERSION = len(MIGRATIONS)

# The scores as they stand with each position's record looked up by the function given.
Scorer = Callable[[Callable[[str], Record]], Scores]

Outcome = Literal["success", "miss", "forced"]

_COMMIT_LOCK = threading.Lock()  # writes are serialised across every socket of the process


@dataclass(frozen=True)
class RoundEnd:
    """What a round that ended commits.

    `verdicts` maps each learner position judged to its pass kind or miss and the time of the move;
    `before` maps each visited learner position to its record and recall estimate before the round.
    """

    started_at: float
    ended_at: float
    side: Side
    path: list[str]
    outcome: Outcome
    end_epd: str
    verdicts: dict[str, tuple[Verdict, float]]
    before: dict[str, dict[str, Any]]
    snapshot_version: str


@dataclass(frozen=True)
class Account:
    """A learner's sign-in identity: `identity` is the key (a Lichess id or an email address),
    `name` what the site shows for it, `created` when it was first signed in to."""

    learner_id: int
    kind: str
    identity: str
    name: str
    created: float


@dataclass(frozen=True)
class PendingSignIn:
    """An emailed link and code not yet used. `tries` counts the wrong codes typed for it.
    `learner_id` is the learner whose account an email change is for, None for a sign-in."""

    token_hash: str
    code_hash: str
    email: str
    tries: int
    learner_id: int | None = None


# The events the daily usage aggregate counts as they happen, each its column (public spec G4).
UsageEvent = Literal["sign_ins", "adoptions", "deletions"]


@dataclass(frozen=True)
class UsageDay:
    """One UTC day of the daily usage aggregate (public spec §12): counts only. The events are
    counted as they happen; the derived counts are None until the finished day's are written
    (`Store.write_usage_day`). Active learners played at least one round that day; `rounds`
    and `successes` leave forced rounds out."""

    day: str
    sign_ins: int
    adoptions: int
    deletions: int
    active_anonymous: int | None
    active_signed_in: int | None
    new_learners: int | None
    rounds: int | None
    successes: int | None


class LearnerStore:
    """One learner's position records, round log, daily scores and settings; got from `Store`,
    never built directly.

    `snapshot_version` is the snapshot the learner's repertoire was last generated from, None
    until one is recorded. `follows_timezone` says whether the learner's days follow their stored
    time zone; local mode's implicit learner's always follow the machine's (ADR 0002)."""

    def __init__(self, conn: sqlite3.Connection, learner_id: int) -> None:
        row = conn.execute(
            "SELECT created, last_seen, snapshot_version FROM learner WHERE id = ?", (learner_id,)
        ).fetchone()
        if row is None:
            raise KeyError(learner_id)
        self._conn = conn
        self.id = learner_id
        self.follows_timezone = True  # `Store.implicit` turns it off
        self.created: float = row[0]
        self.last_seen: float = row[1]
        self.snapshot_version: str | None = row[2]
        self._records = {
            epd: Record(passes, misses, last_pass, bool(relearn))
            for epd, passes, misses, last_pass, relearn in conn.execute(
                "SELECT epd, passes, misses, last_pass, relearn FROM position_record"
                " WHERE learner_id = ?",
                (learner_id,),
            )
        }

    def seen(self, now: float) -> None:
        """Note that the learner was here at `now`; written at most once a day. A warning that
        their account is about to be deleted is cleared (public spec §10)."""
        if now - self.last_seen < DAY:
            return
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute("UPDATE learner SET last_seen = ? WHERE id = ?", (now, self.id))
            self._conn.execute(
                "UPDATE account SET warned_at = NULL WHERE learner_id = ?", (self.id,)
            )
        self.last_seen = now

    def set_snapshot_version(self, version: str) -> None:
        """Record the snapshot this learner's repertoire was generated from."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute(
                "UPDATE learner SET snapshot_version = ? WHERE id = ?", (version, self.id)
            )
        self.snapshot_version = version

    def record(self, epd: str) -> Record:
        return self._records.get(epd, Record())

    def records(self) -> dict[str, Record]:
        """Every position record the learner has, by EPD."""
        return dict(self._records)

    def commit(self, end: RoundEnd, score: Scorer) -> tuple[Scores, Scores]:
        """Apply the round's verdicts, append its log row and upsert the day's scores, all or
        nothing; the scores just before and just after the round's records changed."""
        with _COMMIT_LOCK:
            updated = {
                epd: self.record(epd).apply(verdict, at)
                for epd, (verdict, at) in end.verdicts.items()
            }
            before = score(self.record)
            after = score(lambda epd: updated.get(epd, self.record(epd)))
            with _transaction(self._conn):
                self._conn.executemany(
                    "INSERT OR REPLACE INTO position_record"
                    " (learner_id, epd, passes, misses, last_pass, relearn)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        (self.id, epd, r.passes, r.misses, r.last_pass, int(r.relearn))
                        for epd, r in updated.items()
                    ],
                )
                self._conn.execute(
                    f"INSERT INTO round_log (learner_id, {_ROUND_COLUMNS})"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        self.id,
                        end.started_at,
                        end.ended_at,
                        end.side,
                        json.dumps(end.path),
                        end.outcome,
                        end.end_epd,
                        len(end.path),
                        json.dumps(end.before),
                        end.snapshot_version,
                    ),
                )
                self._conn.execute(
                    f"INSERT INTO daily_score (learner_id, {_DAY_COLUMNS})"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (learner_id, day) DO"
                    " UPDATE SET score = excluded.score, white_score = excluded.white_score,"
                    " black_score = excluded.black_score, rounds = rounds + excluded.rounds,"
                    " successes = successes + excluded.successes, updated_at = excluded.updated_at",
                    (
                        self.id,
                        self.day(end.ended_at),
                        after.score,
                        after.white,
                        after.black,
                        int(end.outcome != "forced"),
                        int(end.outcome == "success"),
                        end.ended_at,
                    ),
                )
            self._records.update(updated)
            return before, after

    def day(self, at: float) -> str:
        """The ISO date of `at` on the learner's calendar: in their time zone when their days
        follow one and they have one, in the machine's otherwise."""
        return day(at, self.setting(TIMEZONE, None) if self.follows_timezone else None)

    def setting(self, key: str, default: Any) -> Any:
        """The value stored under `key` in `settings`, `default` if none is."""
        row = self._conn.execute(
            "SELECT value FROM settings WHERE learner_id = ? AND key = ?", (self.id, key)
        ).fetchone()
        return default if row is None else json.loads(row[0])

    def set_setting(self, key: str, value: Any) -> None:
        """Store `value` (JSON) under `key` in `settings`, replacing any earlier value."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute(
                "INSERT OR REPLACE INTO settings (learner_id, key, value) VALUES (?, ?, ?)",
                (self.id, key, json.dumps(value)),
            )

    def unset_setting(self, key: str) -> None:
        """Forget what is stored under `key`: it reads its default again."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute(
                "DELETE FROM settings WHERE learner_id = ? AND key = ?", (self.id, key)
            )

    def reset_all(self) -> None:
        """Delete every position record; the round log and the daily scores are kept (§7)."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute("DELETE FROM position_record WHERE learner_id = ?", (self.id,))
            self._records.clear()

    def reset(self, epds: Iterable[str]) -> None:
        """Delete the records of `epds` (an opening's or one position's); the round log and the
        daily scores are kept (§7)."""
        epds = list(epds)
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.executemany(
                "DELETE FROM position_record WHERE learner_id = ? AND epd = ?",
                [(self.id, e) for e in epds],
            )
            for epd in epds:
                self._records.pop(epd, None)

    def round_log(self, after: int = 0, limit: int | None = None) -> list[dict[str, Any]]:
        """Every round the learner played, oldest first: those whose `id` is above `after`, at
        most `limit` of them when there is one."""
        rows = self._rows(
            f"SELECT id, {_ROUND_COLUMNS} FROM round_log WHERE learner_id = ? AND id > ?"
            " ORDER BY id LIMIT ?",
            after,
            -1 if limit is None else limit,  # SQLite reads a negative limit as none
        )
        for row in rows:
            row["path"] = json.loads(row["path"])
            row["before"] = json.loads(row["before"])
        return rows

    def daily_scores(self) -> list[dict[str, Any]]:
        """One row per day a round ended, oldest first."""
        return self._rows(
            f"SELECT {_DAY_COLUMNS} FROM daily_score WHERE learner_id = ? ORDER BY day"
        )

    def settings(self) -> dict[str, Any]:
        """Every value stored in `settings`, by key."""
        return {
            key: json.loads(value)
            for key, value in self._conn.execute(
                "SELECT key, value FROM settings WHERE learner_id = ? ORDER BY key", (self.id,)
            )
        }

    def _rows(self, query: str, *values: Any) -> list[dict[str, Any]]:
        cursor = self._conn.execute(query, (self.id, *values))
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor]

    def latest_daily_score(self, before: float) -> tuple[str, float] | None:
        """The day and Score of the last daily row written before `before`, None if none."""
        return self._conn.execute(
            "SELECT day, score FROM daily_score WHERE learner_id = ? AND updated_at < ?"
            " ORDER BY updated_at DESC LIMIT 1",
            (self.id, before),
        ).fetchone()

    def last_day_before(self, day: str) -> tuple[str, float] | None:
        """The day and Score of the latest daily row before `day` (an ISO date), None if none."""
        return self._conn.execute(
            "SELECT day, score FROM daily_score WHERE learner_id = ? AND day < ?"
            " ORDER BY day DESC LIMIT 1",
            (self.id, day),
        ).fetchone()

    def successes_since(self, since: float) -> tuple[int, int]:
        """The successes and the rounds ended since `since`, forced rounds left out of both."""
        successes, rounds = self._conn.execute(
            "SELECT COALESCE(SUM(outcome = 'success'), 0), COUNT(*) FROM round_log"
            " WHERE learner_id = ? AND ended_at >= ? AND outcome != 'forced'",
            (self.id, since),
        ).fetchone()
        return successes, rounds


class Store:
    """The file. It hands out one `LearnerStore` per learner, the same one at every asking."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        _migrate(conn)
        conn.execute("PRAGMA foreign_keys = ON")  # deleting a learner cascades to their rows
        self._learners: dict[int, LearnerStore] = {}

    @classmethod
    def open(cls, data_dir: Path) -> "Store":
        """The store in `data_dir`, the directory and the file created and migrated as needed."""
        data_dir.mkdir(parents=True, exist_ok=True)
        return cls(_connect(str(data_dir / FILENAME)))

    @classmethod
    def in_memory(cls) -> "Store":
        """A store that forgets everything with the process, for tests and throwaway runs."""
        return cls(_connect(":memory:"))

    def close(self) -> None:
        self._conn.close()

    def back_up(self, target: Path) -> None:
        """Copy the database, as committed now, into the new file `target` through SQLite's
        backup API (ADR 0002): one file, with no write-ahead log beside it."""
        copy = sqlite3.connect(target)
        try:
            self._conn.backup(copy)
            copy.execute("PRAGMA journal_mode = DELETE")
        finally:
            copy.close()

    def answers(self) -> bool:
        """Whether the database can be queried right now."""
        try:
            self._conn.execute("SELECT 1 FROM schema_version").fetchone()
        except sqlite3.Error:
            return False
        return True

    def durability(self) -> tuple[str, str]:
        """The journal mode and the `synchronous` level the open file runs with."""
        levels = {0: "off", 1: "normal", 2: "full", 3: "extra"}
        return (
            self._conn.execute("PRAGMA journal_mode").fetchone()[0],
            levels[self._conn.execute("PRAGMA synchronous").fetchone()[0]],
        )

    def create_learner(self, now: float) -> LearnerStore:
        """A new learner, created and last seen at `now`: nothing recorded, every default."""
        with _COMMIT_LOCK, _transaction(self._conn):
            learner_id = self._conn.execute(
                "INSERT INTO learner (created, last_seen) VALUES (?, ?)", (now, now)
            ).lastrowid
        assert learner_id is not None
        return self.learner(learner_id)

    def learner(self, learner_id: int) -> LearnerStore:
        """The learner of that id; `KeyError` when the store holds none."""
        if learner_id not in self._learners:
            self._learners[learner_id] = LearnerStore(self._conn, learner_id)
        return self._learners[learner_id]

    def implicit(self) -> LearnerStore:
        """Local mode's one learner, created at the first asking in a file that has none. Their
        days follow the machine's time zone, whatever is stored (ADR 0002)."""
        if IMPLICIT not in self._learners:
            now = time.time()
            with _COMMIT_LOCK, _transaction(self._conn):
                self._conn.execute(
                    "INSERT OR IGNORE INTO learner (id, created, last_seen) VALUES (?, ?, ?)",
                    (IMPLICIT, now, now),
                )
        learner = self.learner(IMPLICIT)
        learner.follows_timezone = False  # however it was first asked for
        return learner

    def unload(self, learner_id: int) -> None:
        """Let go of the learner's records held in memory; the next asking reads the file."""
        self._learners.pop(learner_id, None)

    def start_session(self, token_hash: str, learner_id: int, now: float, expires: float) -> None:
        """A session of the learner under `token_hash`, usable until `expires`."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute(
                "INSERT INTO session (token_hash, learner_id, created, last_used, expires)"
                " VALUES (?, ?, ?, ?, ?)",
                (token_hash, learner_id, now, now, expires),
            )

    def session(self, token_hash: str, now: float) -> tuple[int, float] | None:
        """The learner of the session under `token_hash` and when it was last used; None when
        there is none or it has expired by `now`."""
        return self._conn.execute(
            "SELECT learner_id, last_used FROM session WHERE token_hash = ? AND expires > ?",
            (token_hash, now),
        ).fetchone()

    def extend_session(self, token_hash: str, now: float, expires: float) -> None:
        """Note the session as used at `now`, usable until `expires`."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute(
                "UPDATE session SET last_used = ?, expires = ? WHERE token_hash = ?",
                (now, expires, token_hash),
            )

    def end_session(self, token_hash: str) -> None:
        """Forget the session under `token_hash`: its token points to no one."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute("DELETE FROM session WHERE token_hash = ?", (token_hash,))

    def create_account(
        self, learner_id: int, kind: str, identity: str, name: str, now: float
    ) -> None:
        """Attach the sign-in identity to the learner, who has none yet."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute(
                "INSERT INTO account (learner_id, kind, identity, display_name, created)"
                " VALUES (?, ?, ?, ?, ?)",
                (learner_id, kind, identity, name, now),
            )

    def rename_account(self, learner_id: int, name: str) -> None:
        """Have the site show `name` for the learner's account."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute(
                "UPDATE account SET display_name = ? WHERE learner_id = ?", (name, learner_id)
            )

    def account(self, kind: str, identity: str) -> Account | None:
        """The account of that sign-in identity, None when no learner has it."""
        return self._account("kind = ? AND identity = ?", (kind, identity))

    def account_of(self, learner_id: int) -> Account | None:
        """The learner's account, None for an anonymous learner."""
        return self._account("learner_id = ?", (learner_id,))

    def _account(self, where: str, values: tuple[Any, ...]) -> Account | None:
        row = self._conn.execute(
            f"SELECT learner_id, kind, identity, display_name, created FROM account WHERE {where}",
            values,
        ).fetchone()
        return None if row is None else Account(*row)

    def change_email(self, learner_id: int, email: str) -> bool:
        """Key the learner's email account by `email` and show it, unless another account holds
        that address: whether it changed."""
        with _COMMIT_LOCK, _transaction(self._conn):
            changed = self._conn.execute(
                "UPDATE account SET identity = ?, display_name = ?"
                " WHERE learner_id = ? AND kind = 'email' AND NOT EXISTS ("
                " SELECT 1 FROM account WHERE kind = 'email' AND identity = ?"
                " AND learner_id != ?)",
                (email, email, learner_id, email, learner_id),
            ).rowcount
        return changed == 1

    def adopt(self, anonymous: int, account: int, now: float) -> None:
        """Join the history of the learner `anonymous` to the learner `account`'s, then delete
        the anonymous learner (public spec §5, ADR 0002), counting one adoption in `now`'s day of
        the usage aggregate. Both learners are unloaded.

        An account with no history takes everything: records, round log, daily scores, settings
        and snapshot version. Otherwise they merge: a position on one side only carries over; on
        both, the record with the later last pass wins whole (one never passed loses, the
        account's wins a tie, two never passed included); both round logs are kept; a day on
        both sides keeps the account's Score and adds the anonymous rounds and successes. The
        account keeps its settings and snapshot version if it has any."""
        conn = self._conn
        with _COMMIT_LOCK, _transaction(conn):
            has_history = any(
                conn.execute(
                    f"SELECT 1 FROM {table} WHERE learner_id = ? LIMIT 1", (account,)
                ).fetchone()
                for table in _HISTORY
            )
            # The account's records beaten by a later last pass on the anonymous side go; then
            # every anonymous record whose position the account no longer holds moves over.
            conn.execute(
                "DELETE FROM position_record WHERE learner_id = ? AND EXISTS ("
                " SELECT 1 FROM position_record AS theirs"
                " WHERE theirs.learner_id = ? AND theirs.epd = position_record.epd"
                " AND theirs.last_pass IS NOT NULL AND (position_record.last_pass IS NULL"
                " OR theirs.last_pass > position_record.last_pass))",
                (account, anonymous),
            )
            conn.execute(
                "UPDATE OR IGNORE position_record SET learner_id = ? WHERE learner_id = ?",
                (account, anonymous),
            )
            conn.execute(
                "UPDATE round_log SET learner_id = ? WHERE learner_id = ?", (account, anonymous)
            )
            # A day on both sides keeps the account's Score and adds the anonymous rounds and
            # successes; a day on the anonymous side only moves over.
            conn.execute(
                "UPDATE daily_score SET"
                " rounds = daily_score.rounds + theirs.rounds,"
                " successes = daily_score.successes + theirs.successes"
                " FROM (SELECT day, rounds, successes FROM daily_score WHERE learner_id = ?)"
                " AS theirs WHERE daily_score.learner_id = ? AND daily_score.day = theirs.day",
                (anonymous, account),
            )
            conn.execute(
                "UPDATE OR IGNORE daily_score SET learner_id = ? WHERE learner_id = ?",
                (account, anonymous),
            )
            account_has_settings = conn.execute(
                "SELECT 1 FROM settings WHERE learner_id = ? LIMIT 1", (account,)
            ).fetchone()
            if not has_history or not account_has_settings:
                conn.execute(
                    "INSERT OR REPLACE INTO settings (learner_id, key, value)"
                    " SELECT ?, key, value FROM settings WHERE learner_id = ?",
                    (account, anonymous),
                )
            preferred, fallback = (account, anonymous) if has_history else (anonymous, account)
            conn.execute(
                "UPDATE learner SET snapshot_version = COALESCE("
                "(SELECT snapshot_version FROM learner WHERE id = ?),"
                " (SELECT snapshot_version FROM learner WHERE id = ?)) WHERE id = ?",
                (preferred, fallback, account),
            )
            conn.execute("DELETE FROM learner WHERE id = ?", (anonymous,))
            _count(conn, "adoptions", now)
        for learner_id in (anonymous, account):
            self._learners.pop(learner_id, None)

    def request_sign_in(
        self,
        token_hash: str,
        code_hash: str,
        email: str,
        binding: str,
        now: float,
        expires: float,
    ) -> None:
        """A pending sign-in for `email`, good until `expires`. One under `binding` already
        (a resend) takes the new link and code and keeps its count of tries. Those expired by
        `now` are forgotten."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute("DELETE FROM pending_sign_in WHERE expires <= ?", (now,))
            self._conn.execute(
                "INSERT INTO pending_sign_in"
                " (token_hash, code_hash, email, binding, expires, purpose)"
                " VALUES (?, ?, ?, ?, ?, 'sign-in') ON CONFLICT (binding) DO UPDATE SET"
                " token_hash = excluded.token_hash, code_hash = excluded.code_hash,"
                " email = excluded.email, expires = excluded.expires",
                (token_hash, code_hash, email, binding, expires),
            )

    def request_email_change(
        self, token_hash: str, email: str, learner_id: int, now: float, expires: float
    ) -> None:
        """A pending change of the learner's account's address to `email`, good until
        `expires`: a link only, no code. It replaces the learner's earlier one, whose link dies.
        Those expired by `now` are forgotten."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute(
                "DELETE FROM pending_sign_in WHERE expires <= ?"
                " OR (purpose = 'email-change' AND learner_id = ?)",
                (now, learner_id),
            )
            # No browser holds a binding for it, and no code is good with one: the column, which
            # must be unique, takes the token hash again.
            self._conn.execute(
                "INSERT INTO pending_sign_in"
                " (token_hash, code_hash, email, binding, expires, purpose, learner_id)"
                " VALUES (?, '', ?, ?, ?, 'email-change', ?)",
                (token_hash, email, token_hash, expires, learner_id),
            )

    def pending_sign_in(
        self,
        now: float,
        *,
        token_hash: str | None = None,
        binding: str | None = None,
        purpose: Literal["sign-in", "email-change"] = "sign-in",
    ) -> PendingSignIn | None:
        """The pending sign-in, or email change, under that token hash, or under that binding;
        None when there is none or it has expired by `now`."""
        column, value = ("token_hash", token_hash) if binding is None else ("binding", binding)
        row = self._conn.execute(
            "SELECT token_hash, code_hash, email, tries, learner_id FROM pending_sign_in"
            f" WHERE {column} = ? AND purpose = ? AND expires > ?",
            (value, purpose, now),
        ).fetchone()
        return None if row is None else PendingSignIn(*row)

    def count_wrong_code(self, token_hash: str) -> None:
        """One more wrong code was typed for the pending sign-in."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute(
                "UPDATE pending_sign_in SET tries = tries + 1 WHERE token_hash = ?", (token_hash,)
            )

    def spend_sign_in(self, token_hash: str) -> None:
        """The pending sign-in was used: neither its link nor its code works again."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute("DELETE FROM pending_sign_in WHERE token_hash = ?", (token_hash,))

    def delete_learner(self, learner_id: int, now: float) -> None:
        """Delete the learner and everything of theirs: records, round log, daily scores,
        settings, account, sessions, the pending sign-ins of their address and their pending
        change of address, counting one deletion in `now`'s day of the usage aggregate. No one
        else's rows are touched."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._delete((learner_id,), now)

    def _delete(self, learner_ids: Iterable[int], now: float) -> int:
        """`delete_learner` for each of `learner_ids`, inside a transaction: how many."""
        deleted = 0
        for learner_id in learner_ids:
            self._conn.execute(
                "DELETE FROM pending_sign_in WHERE purpose = 'sign-in' AND email IN"
                " (SELECT identity FROM account WHERE learner_id = ? AND kind = 'email')",
                (learner_id,),
            )
            self._conn.execute("DELETE FROM learner WHERE id = ?", (learner_id,))
            _count(self._conn, "deletions", now)
            self._learners.pop(learner_id, None)
            deleted += 1
        return deleted

    def purge_anonymous(
        self, unseen_since: float, now: float, rounds_under: int | None = None
    ) -> int:
        """Delete, as `delete_learner` does, every anonymous learner last seen at `unseen_since`
        or before, only those with fewer than `rounds_under` rounds logged when it is given
        (public spec §10): how many were deleted."""
        few = (
            ""
            if rounds_under is None
            else (" AND (SELECT COUNT(*) FROM round_log AS r WHERE r.learner_id = l.id) < ?")
        )
        values = (unseen_since,) if rounds_under is None else (unseen_since, rounds_under)
        with _COMMIT_LOCK, _transaction(self._conn):
            idle = self._conn.execute(
                "SELECT l.id FROM learner AS l WHERE l.last_seen <= ? AND NOT EXISTS"
                f" (SELECT 1 FROM account AS a WHERE a.learner_id = l.id){few}",
                values,
            ).fetchall()
            return self._delete([learner_id for (learner_id,) in idle], now)

    def purge_accounts(self, unseen_since: float, warned_by: float, now: float) -> int:
        """Delete, as `delete_learner` does, every learner with an account last seen at
        `unseen_since` or before; one with an email account only when they were warned at
        `warned_by` or before (public spec §10): how many were deleted."""
        with _COMMIT_LOCK, _transaction(self._conn):
            idle = self._conn.execute(
                "SELECT l.id FROM learner AS l JOIN account AS a ON a.learner_id = l.id"
                " WHERE l.last_seen <= ? AND (a.kind != 'email' OR a.warned_at <= ?)",
                (unseen_since, warned_by),
            ).fetchall()
            return self._delete([learner_id for (learner_id,) in idle], now)

    def accounts_to_warn(self, unseen_since: float) -> list[Account]:
        """The email accounts of the learners last seen at `unseen_since` or before that no
        warning stands for."""
        return [
            Account(*row)
            for row in self._conn.execute(
                "SELECT a.learner_id, a.kind, a.identity, a.display_name, a.created"
                " FROM account AS a JOIN learner AS l ON l.id = a.learner_id"
                " WHERE a.kind = 'email' AND a.warned_at IS NULL AND l.last_seen <= ?"
                " ORDER BY a.learner_id",
                (unseen_since,),
            )
        ]

    def warned(self, learner_id: int, unseen_since: float, now: float) -> None:
        """Note that the learner's account was warned at `now` that it is about to be deleted,
        unless they were seen after `unseen_since` in the meantime."""
        with _COMMIT_LOCK, _transaction(self._conn):
            self._conn.execute(
                "UPDATE account SET warned_at = ? WHERE learner_id = ? AND EXISTS"
                " (SELECT 1 FROM learner WHERE id = account.learner_id AND last_seen <= ?)",
                (now, learner_id, unseen_since),
            )

    def count_sign_in(self, now: float) -> None:
        """Count one sign-in in `now`'s day of the usage aggregate."""
        with _COMMIT_LOCK, _transaction(self._conn):
            _count(self._conn, "sign_ins", now)

    def write_usage_day(self, iso_date: str, now: float) -> bool:
        """Write the derived counts of the UTC day `iso_date` into the usage aggregate, beside
        the events counted that day, unless they were written already: whether they were now.
        Counted over the learners that remain: those active (a round logged that day) with an
        account and without, those created that day, and their rounds and successes, forced
        rounds left out. `ValueError` when the day has not finished by `now`."""
        start = utc_midnight(iso_date)
        end = start + DAY
        if now < end:
            raise ValueError(f"the UTC day {iso_date} is not finished")
        with _COMMIT_LOCK, _transaction(self._conn):
            anonymous, signed_in = self.active_learners(start, end)
            rounds, successes = self._conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(outcome = 'success'), 0) FROM round_log"
                " WHERE ended_at >= ? AND ended_at < ? AND outcome != 'forced'",
                (start, end),
            ).fetchone()
            (new,) = self._conn.execute(
                "SELECT COUNT(*) FROM learner WHERE created >= ? AND created < ?", (start, end)
            ).fetchone()
            written = self._conn.execute(
                "INSERT INTO daily_usage (day, active_anonymous, active_signed_in, new_learners,"
                " rounds, successes, written_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT (day) DO UPDATE SET active_anonymous = excluded.active_anonymous,"
                " active_signed_in = excluded.active_signed_in,"
                " new_learners = excluded.new_learners, rounds = excluded.rounds,"
                " successes = excluded.successes, written_at = excluded.written_at"
                " WHERE daily_usage.written_at IS NULL",
                (iso_date, anonymous, signed_in, new, rounds, successes, now),
            ).rowcount
        return written == 1

    def active_learners(self, start: float, end: float) -> tuple[int, int]:
        """The anonymous and the signed-in learners, of those that remain, who logged at least
        one round from `start` until `end`."""
        return self._conn.execute(
            "SELECT COUNT(DISTINCT CASE WHEN a.learner_id IS NULL THEN r.learner_id END),"
            " COUNT(DISTINCT CASE WHEN a.learner_id IS NOT NULL THEN r.learner_id END)"
            " FROM round_log AS r LEFT JOIN account AS a ON a.learner_id = r.learner_id"
            " WHERE r.ended_at >= ? AND r.ended_at < ?",
            (start, end),
        ).fetchone()

    def returning_learners(
        self, start: float, end: float, after: Iterable[float]
    ) -> tuple[int, list[int]]:
        """Of the learners that remain created from `start` until `end`: how many there are,
        and for each lapse in `after`, how many logged a round at least that long after they
        were created."""
        (created,) = self._conn.execute(
            "SELECT COUNT(*) FROM learner WHERE created >= ? AND created < ?", (start, end)
        ).fetchone()
        returned = [
            self._conn.execute(
                "SELECT COUNT(*) FROM learner AS l WHERE l.created >= ? AND l.created < ?"
                " AND EXISTS (SELECT 1 FROM round_log AS r"
                " WHERE r.learner_id = l.id AND r.ended_at >= l.created + ?)",
                (start, end, lapse),
            ).fetchone()[0]
            for lapse in after
        ]
        return created, returned

    def choices_since(self, since: float) -> list[tuple[Any, Any, str | None]]:
        """For each learner who logged a round since `since`: their stored band and opted-out
        openings, None for one not stored, and the snapshot version they were last on."""
        return [
            (
                None if band is None else json.loads(band),
                None if opted_out is None else json.loads(opted_out),
                version,
            )
            for band, opted_out, version in self._conn.execute(
                "SELECT (SELECT value FROM settings WHERE learner_id = l.id AND key = 'band'),"
                " (SELECT value FROM settings WHERE learner_id = l.id AND key = 'opted_out'),"
                " l.snapshot_version FROM learner AS l WHERE EXISTS (SELECT 1 FROM round_log"
                " AS r WHERE r.learner_id = l.id AND r.ended_at >= ?)",
                (since,),
            )
        ]

    def usage_days(self) -> list[UsageDay]:
        """Every day of the usage aggregate, oldest first."""
        return [
            UsageDay(*row)
            for row in self._conn.execute(
                "SELECT day, sign_ins, adoptions, deletions, active_anonymous, active_signed_in,"
                " new_learners, rounds, successes FROM daily_usage ORDER BY day"
            )
        ]


def _count(conn: sqlite3.Connection, event: UsageEvent, now: float) -> None:
    """One more `event` in `now`'s UTC day of the usage aggregate; inside a transaction."""
    conn.execute(
        f"INSERT INTO daily_usage (day, {event}) VALUES (?, 1)"
        f" ON CONFLICT (day) DO UPDATE SET {event} = {event} + 1",
        (utc_day(now),),
    )


def _connect(database: str) -> sqlite3.Connection:
    # Transactions are explicit; the app's socket handlers may run on another thread than `open`.
    conn = sqlite3.connect(database, isolation_level=None, check_same_thread=False)
    conn.execute("PRAGMA journal_mode = WAL")  # an in-memory database stays in `memory`
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


@contextmanager
def _transaction(conn: sqlite3.Connection) -> Iterator[None]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def _migrate(conn: sqlite3.Connection) -> None:
    with _transaction(conn):
        known = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_version'"
        ).fetchone()
        version = conn.execute("SELECT version FROM schema_version").fetchone()[0] if known else 0
        if version > SCHEMA_VERSION:
            raise RuntimeError(f"the data file is schema {version}, newer than this chessop")
        for migration in MIGRATIONS[version:]:
            if callable(migration):
                migration(conn)
                continue
            for statement in migration:
                conn.execute(statement)
        if not known:
            conn.execute("INSERT INTO schema_version VALUES (?)", (SCHEMA_VERSION,))
        else:
            conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
