import sqlite3
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from chessop.memory import DAY, Record
from chessop.score import Scores
from chessop.store import (
    FILENAME,
    MIGRATIONS,
    MOVED_FROM_BAND,
    SCHEMA_VERSION,
    LearnerStore,
    RoundEnd,
    Store,
)
from graphs import epd_after

NOW = 1_800_000_000.0
START, E4 = epd_after(), epd_after("e4")


def a_round(**changes: Any) -> RoundEnd:
    fields: dict[str, Any] = {
        "started_at": NOW - 5,
        "ended_at": NOW,
        "side": "white",
        "path": ["e2e4", "e7e5", "g1f3"],
        "outcome": "miss",
        "end_epd": epd_after("e4", "e5", "Nf3"),
        "verdicts": {START: ("counted", NOW - 4), epd_after("e4", "e5"): ("miss", NOW)},
        "before": {START: {"passes": 0, "misses": 0, "relearn": False, "last_pass": None, "R": 0}},
        "snapshot_version": "2026-08/test",
    }
    return RoundEnd(**{**fields, **changes})


def statements(migration: int) -> tuple[str, ...]:
    """The SQL of one of the first migrations, which are plain statements."""
    found = MIGRATIONS[migration]
    assert isinstance(found, tuple)
    return found


def passes_at_start(record: Callable[[str], Record]) -> Scores:
    """A stand-in for the Score: the counted passes at the start position, as the Score."""
    return Scores(record(START).passes / 10, 0.5, 0.25)


def test_the_first_run_creates_the_file_and_migrates_it_from_empty(tmp_path: Path) -> None:
    data_dir = tmp_path / "nested" / "chessop"
    Store.open(data_dir).close()
    db = sqlite3.connect(data_dir / FILENAME)
    assert db.execute("SELECT version FROM schema_version").fetchall() == [(SCHEMA_VERSION,)]
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert tables == {
        "schema_version",
        "learner",
        "settings",
        "position_record",
        "round_log",
        "daily_score",
        "session",
        "account",
        "pending_sign_in",
        "daily_usage",
    }


def test_reopening_a_migrated_file_keeps_its_history(tmp_path: Path) -> None:
    file = Store.open(tmp_path)
    store = file.implicit()
    store.commit(a_round(), passes_at_start)
    file.close()
    again = Store.open(tmp_path).implicit()
    assert again.record(START) == Record(passes=1, last_pass=NOW - 4)
    assert len(again.round_log()) == 1


def test_a_position_never_seen_has_an_empty_record() -> None:
    assert Store.in_memory().implicit().record(E4) == Record()


def test_a_round_end_applies_its_passes_and_its_miss_and_appends_to_the_log() -> None:
    store = Store.in_memory().implicit()
    store.commit(a_round(), passes_at_start)
    assert store.record(START) == Record(passes=1, last_pass=NOW - 4)
    assert store.record(epd_after("e4", "e5")) == Record(misses=1, relearn=True)
    [row] = store.round_log()
    assert row == {
        "id": 1,
        "started_at": NOW - 5,
        "ended_at": NOW,
        "side": "white",
        "path": ["e2e4", "e7e5", "g1f3"],
        "outcome": "miss",
        "end_epd": epd_after("e4", "e5", "Nf3"),
        "plies": 3,
        "before": {START: {"passes": 0, "misses": 0, "relearn": False, "last_pass": None, "R": 0}},
        "snapshot_version": "2026-08/test",
    }


def test_rounds_apply_on_top_of_each_other() -> None:
    store = Store.in_memory().implicit()
    store.commit(a_round(), passes_at_start)
    store.commit(
        a_round(verdicts={epd_after("e4", "e5"): ("relearning", NOW + 10)}), passes_at_start
    )
    assert store.record(epd_after("e4", "e5")) == Record(misses=1, last_pass=NOW + 10)
    assert [r["id"] for r in store.round_log()] == [1, 2]


def test_a_failed_log_append_rolls_back_the_records(tmp_path: Path) -> None:
    file = Store.open(tmp_path)
    store = file.implicit()
    sqlite3.connect(tmp_path / FILENAME).execute(
        "CREATE TRIGGER no_log BEFORE INSERT ON round_log BEGIN SELECT RAISE(ABORT, 'no'); END"
    ).connection.commit()
    with pytest.raises(sqlite3.IntegrityError):
        store.commit(a_round(), passes_at_start)
    assert store.record(START) == Record()
    file.close()
    again = Store.open(tmp_path).implicit()
    assert again.record(START) == Record()
    assert again.round_log() == []


def test_a_round_end_returns_the_scores_before_and_after_it() -> None:
    store = Store.in_memory().implicit()
    assert store.commit(a_round(), passes_at_start) == (
        Scores(0.0, 0.5, 0.25),
        Scores(0.1, 0.5, 0.25),
    )


def test_each_round_end_upserts_the_days_scores_and_counts() -> None:
    store = Store.in_memory().implicit()
    store.commit(a_round(outcome="miss", ended_at=NOW), passes_at_start)
    store.commit(a_round(outcome="success", ended_at=NOW + 10), passes_at_start)
    store.commit(a_round(outcome="success", ended_at=NOW + DAY), passes_at_start)
    today, tomorrow = date.fromtimestamp(NOW), date.fromtimestamp(NOW + DAY)
    assert store.daily_scores() == [
        {
            "day": today.isoformat(),
            "score": 0.2,
            "white_score": 0.5,
            "black_score": 0.25,
            "rounds": 2,
            "successes": 1,
            "updated_at": NOW + 10,
        },
        {
            "day": tomorrow.isoformat(),
            "score": pytest.approx(0.3),
            "white_score": 0.5,
            "black_score": 0.25,
            "rounds": 1,
            "successes": 1,
            "updated_at": NOW + DAY,
        },
    ]


def test_a_forced_round_is_logged_but_left_out_of_the_days_counts() -> None:
    store = Store.in_memory().implicit()
    forced = a_round(outcome="forced", verdicts={START: ("counted", NOW - 4)}, ended_at=NOW)
    store.commit(forced, passes_at_start)
    store.commit(a_round(outcome="success", ended_at=NOW + 10), passes_at_start)
    store.commit(a_round(outcome="forced", verdicts={}, ended_at=NOW + 20), passes_at_start)
    [today] = store.daily_scores()
    assert (today["rounds"], today["successes"]) == (1, 1)
    assert today["score"] == 0.2 and today["updated_at"] == NOW + 20
    assert [r["outcome"] for r in store.round_log()] == ["forced", "success", "forced"]


def test_the_latest_daily_score_is_the_last_row_written_before_the_moment_asked() -> None:
    store = Store.in_memory().implicit()
    assert store.latest_daily_score(NOW) is None
    store.commit(a_round(ended_at=NOW), passes_at_start)
    store.commit(a_round(ended_at=NOW + DAY), passes_at_start)
    assert store.latest_daily_score(NOW + 1) == (date.fromtimestamp(NOW).isoformat(), 0.1)
    assert store.latest_daily_score(NOW + DAY + 1) == (
        date.fromtimestamp(NOW + DAY).isoformat(),
        0.2,
    )


def test_the_session_counts_rounds_ended_since_it_began_forced_rounds_excluded() -> None:
    store = Store.in_memory().implicit()
    assert store.successes_since(NOW) == (0, 0)
    store.commit(a_round(outcome="success", ended_at=NOW - 1), passes_at_start)  # before it
    store.commit(a_round(outcome="success", ended_at=NOW + 1), passes_at_start)
    store.commit(a_round(outcome="miss", ended_at=NOW + 2), passes_at_start)
    store.commit(a_round(outcome="forced", verdicts={}, ended_at=NOW + 3), passes_at_start)
    assert store.successes_since(NOW) == (1, 2)  # successes, rounds


def test_the_last_day_played_is_the_latest_daily_row_before_the_day_asked() -> None:
    store = Store.in_memory().implicit()
    today = date.fromtimestamp(NOW + 2 * DAY).isoformat()
    assert store.last_day_before(today) is None
    store.commit(a_round(ended_at=NOW), passes_at_start)  # Score 0.1
    store.commit(a_round(ended_at=NOW + 10), passes_at_start)  # 0.2, the same day
    store.commit(a_round(ended_at=NOW + 2 * DAY), passes_at_start)  # 0.3, today
    assert store.last_day_before(today) == (date.fromtimestamp(NOW).isoformat(), 0.2)


def test_a_failed_daily_upsert_rolls_back_the_whole_round(tmp_path: Path) -> None:
    file = Store.open(tmp_path)
    store = file.implicit()
    sqlite3.connect(tmp_path / FILENAME).execute(
        "CREATE TRIGGER no_day BEFORE INSERT ON daily_score BEGIN SELECT RAISE(ABORT, 'no'); END"
    ).connection.commit()
    with pytest.raises(sqlite3.IntegrityError):
        store.commit(a_round(), passes_at_start)
    assert store.record(START) == Record()
    assert store.round_log() == []


def test_a_file_at_schema_1_migrates_forward_keeping_its_history(tmp_path: Path) -> None:
    db = sqlite3.connect(tmp_path / FILENAME)
    for statement in statements(0):
        db.execute(statement)
    db.execute("INSERT INTO schema_version VALUES (1)")
    db.execute("INSERT INTO position_record VALUES (?, 1, 0, ?, 0)", (START, NOW))
    db.commit()
    db.close()
    file = Store.open(tmp_path)
    store = file.implicit()
    assert store.record(START) == Record(passes=1, last_pass=NOW)
    store.commit(a_round(), passes_at_start)
    assert len(store.daily_scores()) == 1


def test_a_setting_reads_its_default_until_written_and_outlives_the_process(
    tmp_path: Path,
) -> None:
    file = Store.open(tmp_path)
    store = file.implicit()
    assert store.setting("sound", True) is True
    store.set_setting("sound", False)
    assert store.setting("sound", True) is False
    file.close()
    file = Store.open(tmp_path)
    store = file.implicit()
    assert store.setting("sound", True) is False
    assert store.setting("animation_ms", 100) == 100


def test_the_open_file_runs_in_wal_mode_with_synchronous_normal(tmp_path: Path) -> None:
    store = Store.open(tmp_path)
    assert store.durability() == ("wal", "normal")
    store.close()
    assert Store.open(tmp_path).durability() == ("wal", "normal")


def test_two_learners_in_one_store_are_isolated_from_each_other(tmp_path: Path) -> None:
    file = Store.open(tmp_path)
    ann, bob = file.create_learner(NOW), file.create_learner(NOW)
    ann.commit(a_round(outcome="success"), passes_at_start)
    ann.set_setting("band", "1800+")
    ann.set_snapshot_version("2026-08/test")
    bob.set_setting("sound", False)
    for _ in range(2):  # as committed, then as read back from the file
        assert ann.record(START) == Record(passes=1, last_pass=NOW - 4)
        assert len(ann.round_log()) == len(ann.daily_scores()) == 1
        assert ann.successes_since(0) == (1, 1)
        assert ann.latest_daily_score(NOW + 1) is not None
        assert ann.setting("band", None) == "1800+" and ann.setting("sound", True) is True
        assert ann.snapshot_version == "2026-08/test"
        assert bob.record(START) == Record()
        assert bob.round_log() == bob.daily_scores() == []
        assert bob.successes_since(0) == (0, 0)
        assert bob.latest_daily_score(NOW + 1) is None
        assert bob.last_day_before("9999-01-01") is None
        assert bob.setting("band", None) is None and bob.setting("sound", True) is False
        assert bob.snapshot_version is None
        file.close()
        file = Store.open(tmp_path)
        ann, bob = file.learner(ann.id), file.learner(bob.id)


def test_two_learners_rounds_on_one_day_are_scored_apart() -> None:
    file = Store.in_memory()
    ann, bob = file.create_learner(NOW), file.create_learner(NOW)
    ann.commit(a_round(outcome="success"), passes_at_start)
    ann.commit(a_round(outcome="success"), passes_at_start)
    bob.commit(a_round(outcome="miss"), passes_at_start)
    [ann_day], [bob_day] = ann.daily_scores(), bob.daily_scores()
    assert (ann_day["score"], ann_day["rounds"], ann_day["successes"]) == (0.2, 2, 2)
    assert (bob_day["score"], bob_day["rounds"], bob_day["successes"]) == (0.1, 1, 0)


def test_a_reset_deletes_only_that_learners_records() -> None:
    file = Store.in_memory()
    ann, bob = file.create_learner(NOW), file.create_learner(NOW)
    for learner in (ann, bob):
        learner.commit(a_round(), passes_at_start)
    ann.reset([START])
    assert ann.record(START) == Record() and ann.record(epd_after("e4", "e5")) != Record()
    ann.reset_all()
    assert ann.record(epd_after("e4", "e5")) == Record()
    assert bob.record(START) == Record(passes=1, last_pass=NOW - 4)
    assert bob.record(epd_after("e4", "e5")) == Record(misses=1, relearn=True)


def test_the_implicit_learner_is_the_same_one_at_every_start(tmp_path: Path) -> None:
    file = Store.open(tmp_path)
    file.implicit().commit(a_round(), passes_at_start)
    assert file.implicit() is file.implicit()
    file.close()
    assert len(Store.open(tmp_path).implicit().round_log()) == 1


def test_a_learner_the_store_does_not_hold_is_a_key_error() -> None:
    with pytest.raises(KeyError):
        Store.in_memory().learner(7)


def rows_per_learner(path: Path) -> dict[str, dict[int, int]]:
    """For every table of the file holding a learner's rows, the rows of each learner in it;
    a row of no learner (a pending sign-in) is left out."""
    db = sqlite3.connect(path)
    counts: dict[str, dict[int, int]] = {}
    for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
        columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
        key = "id" if table == "learner" else "learner_id" if "learner_id" in columns else None
        if key is not None:
            counts[table] = dict(
                db.execute(
                    f"SELECT {key}, COUNT(*) FROM {table} WHERE {key} IS NOT NULL GROUP BY {key}"
                )
            )
    db.close()
    return counts


def test_deleting_a_learner_removes_their_rows_from_every_table_and_no_one_elses(
    tmp_path: Path,
) -> None:
    file = Store.open(tmp_path)
    ann, bob = file.create_learner(NOW), file.create_learner(NOW)
    for learner in (ann, bob):
        learner.commit(a_round(), passes_at_start)
        learner.set_setting("sound", False)
        file.start_session(f"hash of {learner.id}", learner.id, NOW, NOW + DAY)
        email = f"{learner.id}@example.org"
        file.create_account(learner.id, "email", email, email, NOW)
        file.request_sign_in(f"token {learner.id}", "code", email, f"b{learner.id}", NOW, NOW + 9)
        new = f"new {learner.id}@example.org"
        file.request_email_change(f"change {learner.id}", new, learner.id, NOW, NOW + 9)
    before = rows_per_learner(tmp_path / FILENAME)
    assert set(before) == {
        "learner",
        "settings",
        "position_record",
        "round_log",
        "daily_score",
        "session",
        "account",
        "pending_sign_in",
    }
    assert all(set(rows) == {ann.id, bob.id} for rows in before.values())
    file.delete_learner(ann.id, NOW)
    assert rows_per_learner(tmp_path / FILENAME) == {
        table: {bob.id: rows[bob.id]} for table, rows in before.items()
    }
    with pytest.raises(KeyError):
        file.learner(ann.id)
    assert bob.record(START) == Record(passes=1, last_pass=NOW - 4)
    assert len(bob.round_log()) == 1 and bob.setting("sound", True) is False
    assert file.session(f"hash of {ann.id}", NOW) is None
    assert file.session(f"hash of {bob.id}", NOW) == (bob.id, NOW)
    assert file.account("email", f"{ann.id}@example.org") is None
    assert file.pending_sign_in(NOW, token_hash=f"token {ann.id}") is None
    assert file.pending_sign_in(NOW, token_hash=f"token {bob.id}") is not None
    for learner, left in ((ann, False), (bob, True)):
        change = file.pending_sign_in(
            NOW, token_hash=f"change {learner.id}", purpose="email-change"
        )
        assert (change is not None) == left


def commit_rounds(learner: LearnerStore, *rounds: dict[str, tuple[str, float]]) -> None:
    """Commit one round per verdicts map given, in order, for the learner."""
    for verdicts in rounds:
        learner.commit(a_round(verdicts=verdicts), passes_at_start)


def test_adopting_into_an_account_with_history_keeps_the_later_last_pass_per_position(
    tmp_path: Path,
) -> None:
    file = Store.open(tmp_path)
    account, anonymous = file.create_learner(NOW), file.create_learner(NOW)
    e4e5, d4, c4, d4d5 = (epd_after(*m) for m in (["e4", "e5"], ["d4"], ["c4"], ["d4", "d5"]))
    commit_rounds(
        account,
        {START: ("counted", NOW - 300), E4: ("counted", NOW - 100), e4e5: ("miss", NOW)},
        {START: ("counted", NOW - 200), d4: ("counted", NOW - 50)},
        {d4d5: ("miss", NOW)},
    )
    commit_rounds(
        anonymous,
        {START: ("counted", NOW - 10), E4: ("miss", NOW), d4d5: ("miss", NOW)},
        {E4: ("counted", NOW - 150), e4e5: ("counted", NOW - 400), c4: ("miss", NOW)},
        {d4d5: ("miss", NOW), c4: ("miss", NOW)},
    )
    file.adopt(anonymous.id, account.id, NOW)
    for _ in range(2):  # as adopted, then as read back from the file
        merged = file.learner(account.id)
        # On both sides: the later last pass wins whole, a record never passed losing.
        assert merged.record(START) == Record(passes=1, last_pass=NOW - 10)
        assert merged.record(E4) == Record(passes=1, last_pass=NOW - 100)
        assert merged.record(e4e5) == Record(passes=1, last_pass=NOW - 400)
        assert merged.record(d4d5) == Record(misses=1, relearn=True)  # neither: the account's
        # On one side only: carried over.
        assert merged.record(d4) == Record(passes=1, last_pass=NOW - 50)
        assert merged.record(c4) == Record(misses=2, relearn=True)
        file.close()
        file = Store.open(tmp_path)


def test_adopting_keeps_both_round_logs_and_the_accounts_score_on_a_shared_day() -> None:
    file = Store.in_memory()
    account, anonymous = file.create_learner(NOW), file.create_learner(NOW)
    for outcome, at in (("miss", NOW), ("success", NOW + 10)):  # the account's Score: 0.2
        account.commit(a_round(outcome=outcome, ended_at=at), passes_at_start)
    for outcome, at in (("success", NOW + 5), ("forced", NOW + 6), ("success", NOW + 7)):
        anonymous.commit(a_round(outcome=outcome, ended_at=at), passes_at_start)
    anonymous.commit(a_round(outcome="miss", ended_at=NOW + DAY), passes_at_start)
    file.adopt(anonymous.id, account.id, NOW)
    merged = file.learner(account.id)
    assert sorted((r["ended_at"], r["outcome"]) for r in merged.round_log()) == [
        (NOW, "miss"),
        (NOW + 5, "success"),
        (NOW + 6, "forced"),
        (NOW + 7, "success"),
        (NOW + 10, "success"),
        (NOW + DAY, "miss"),
    ]
    today, tomorrow = date.fromtimestamp(NOW), date.fromtimestamp(NOW + DAY)
    assert merged.daily_scores() == [
        {  # on both sides: the account's Score, the rounds and successes of both
            "day": today.isoformat(),
            "score": 0.2,
            "white_score": 0.5,
            "black_score": 0.25,
            "rounds": 2 + 2,
            "successes": 1 + 2,
            "updated_at": NOW + 10,
        },
        {  # on the anonymous side only: carried over
            "day": tomorrow.isoformat(),
            "score": pytest.approx(0.4),
            "white_score": 0.5,
            "black_score": 0.25,
            "rounds": 1,
            "successes": 0,
            "updated_at": NOW + DAY,
        },
    ]


def test_adopting_into_an_account_with_history_keeps_its_settings_if_it_has_any() -> None:
    file = Store.in_memory()
    for account_settings, kept in (
        ({"band": "1800+"}, {"band": "1800+", "sound": True}),
        ({}, {"band": "1200+", "sound": False}),
    ):
        account, anonymous = file.create_learner(NOW), file.create_learner(NOW)
        account.commit(a_round(), passes_at_start)
        account.set_snapshot_version("2026-08/account")
        for key, value in account_settings.items():
            account.set_setting(key, value)
        anonymous.set_setting("band", "1200+")
        anonymous.set_setting("sound", False)
        anonymous.set_snapshot_version("2026-09/anonymous")
        file.adopt(anonymous.id, account.id, NOW)
        merged = file.learner(account.id)
        assert {key: merged.setting(key, True) for key in ("band", "sound")} == kept
        assert merged.snapshot_version == "2026-08/account"
        with pytest.raises(KeyError):
            file.learner(anonymous.id)


def test_last_seen_is_written_at_most_once_a_day(tmp_path: Path) -> None:
    file = Store.open(tmp_path)
    learner = file.create_learner(NOW)
    assert (learner.created, learner.last_seen) == (NOW, NOW)
    learner.seen(NOW + DAY - 1)  # within the day: not written
    file.close()
    file = Store.open(tmp_path)
    learner = file.learner(learner.id)
    assert learner.last_seen == NOW
    learner.seen(NOW + DAY)
    learner.seen(NOW + DAY + 60)
    file.close()
    learner = Store.open(tmp_path).learner(learner.id)
    assert (learner.created, learner.last_seen) == (NOW, NOW + DAY)


def a_v1_file(path: Path, settings: dict[str, str]) -> None:
    """A file as v1 left it (schema 2): `settings` (JSON values), two position records, two
    rounds on two days and their daily scores."""
    db = sqlite3.connect(path)
    for statement in (*statements(0), *statements(1)):
        db.execute(statement)
    db.execute("INSERT INTO schema_version VALUES (2)")
    db.executemany("INSERT INTO settings VALUES (?, ?)", settings.items())
    db.execute("INSERT INTO position_record VALUES (?, 3, 1, ?, 0)", (START, NOW))
    db.execute("INSERT INTO position_record VALUES (?, 0, 2, NULL, 1)", (E4,))
    for round_id, ended_at, outcome in ((1, NOW - DAY, "miss"), (2, NOW, "success")):
        db.execute(
            "INSERT INTO round_log VALUES (?, ?, ?, 'white', ?, ?, ?, 1, ?, '2026-08/v1')",
            (round_id, ended_at - 5, ended_at, '["e2e4"]', outcome, E4, '{"x": {"R": 0.5}}'),
        )
        db.execute(
            "INSERT INTO daily_score VALUES (?, 0.4, 0.5, 0.3, 1, ?, ?)",
            (date.fromtimestamp(ended_at).isoformat(), int(outcome == "success"), ended_at),
        )
    db.commit()
    db.close()


V1_SETTINGS = {"snapshot_version": '"2026-08/v1"', "sound": "false", "width_player": "1"}


def test_a_v1_file_migrates_with_every_row_on_the_implicit_learner(tmp_path: Path) -> None:
    a_v1_file(tmp_path / FILENAME, {**V1_SETTINGS, "rating": "1650"})
    file = Store.open(tmp_path)
    learner = file.implicit()
    assert learner.record(START) == Record(passes=3, misses=1, last_pass=NOW)
    assert learner.record(E4) == Record(misses=2, relearn=True)
    assert learner.round_log() == [
        {
            "id": round_id,
            "started_at": ended_at - 5,
            "ended_at": ended_at,
            "side": "white",
            "path": ["e2e4"],
            "outcome": outcome,
            "end_epd": E4,
            "plies": 1,
            "before": {"x": {"R": 0.5}},
            "snapshot_version": "2026-08/v1",
        }
        for round_id, ended_at, outcome in ((1, NOW - DAY, "miss"), (2, NOW, "success"))
    ]
    assert learner.daily_scores() == [
        {
            "day": date.fromtimestamp(ended_at).isoformat(),
            "score": 0.4,
            "white_score": 0.5,
            "black_score": 0.3,
            "rounds": 1,
            "successes": successes,
            "updated_at": ended_at,
        }
        for ended_at, successes in ((NOW - DAY, 0), (NOW, 1))
    ]
    assert learner.setting("sound", True) is False
    assert learner.setting("width_player", 2) == 1
    assert learner.snapshot_version == "2026-08/v1"
    assert (learner.created, learner.last_seen) == (NOW - DAY - 5, NOW)
    learner.commit(a_round(ended_at=NOW + 10), passes_at_start)  # and it goes on from there
    assert [row["id"] for row in learner.round_log()] == [1, 2, 3]
    assert rows_per_learner(tmp_path / FILENAME) == {
        "session": {},
        "account": {},
        "pending_sign_in": {},
        "learner": {learner.id: 1},
        "settings": {learner.id: 3},  # sound, width_player and the band
        "position_record": {learner.id: 3},
        "round_log": {learner.id: 3},
        "daily_score": {learner.id: 2},
    }


@pytest.mark.parametrize(
    ("rating", "band"),
    [
        (0, "0-1200"),
        (1199, "0-1200"),
        (1200, "1200-1500"),
        (1500, "1500-1800"),
        (1799, "1500-1800"),
        (1800, "1800-2100"),
        (2100, "2100+"),
        (2850, "2100+"),
    ],
)
def test_a_v1_declared_rating_becomes_the_closed_band_it_mapped_to(
    tmp_path: Path, rating: int, band: str
) -> None:
    a_v1_file(tmp_path / FILENAME, {**V1_SETTINGS, "rating": str(rating)})
    learner = Store.open(tmp_path).implicit()
    assert learner.setting("band", None) == band
    assert learner.setting("rating", None) is None
    assert learner.setting(MOVED_FROM_BAND, None) is None  # the same band: nothing to tell


@pytest.mark.parametrize("settings", [V1_SETTINGS, {**V1_SETTINGS, "rating": "null"}])
def test_a_v1_file_with_no_declared_rating_moves_to_1500_plus_and_owes_a_notice(
    tmp_path: Path, settings: dict[str, str]
) -> None:
    a_v1_file(tmp_path / FILENAME, settings)
    learner = Store.open(tmp_path).implicit()
    assert learner.setting("band", None) == "1500+"
    assert learner.setting(MOVED_FROM_BAND, None) == "1500-1800"
    assert learner.record(START) == Record(passes=3, misses=1, last_pass=NOW)
    assert learner.record(E4) == Record(misses=2, relearn=True)


def test_a_file_that_already_chose_its_band_keeps_it(tmp_path: Path) -> None:
    a_v1_file(tmp_path / FILENAME, {**V1_SETTINGS, "band": '"1800+"'})
    learner = Store.open(tmp_path).implicit()
    assert learner.setting("band", None) == "1800+"
    assert learner.setting(MOVED_FROM_BAND, None) is None


def test_a_new_file_owes_its_learner_no_notice(tmp_path: Path) -> None:
    learner = Store.open(tmp_path).implicit()
    assert learner.setting(MOVED_FROM_BAND, None) is None
    assert learner.setting("band", None) is None  # the default, 1500+
