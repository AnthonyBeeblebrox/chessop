"""The daily usage aggregate and `chessop stats` (public spec §12, G4): one counts-only row per
UTC day, its sign-ins, adoptions and deletions counted as they happen and its derived counts
written once for a finished day; and the tables the owner reads. Events are driven through the
hosted app as a browser would; the aggregate is read back through the store."""

import sqlite3
from pathlib import Path

import pytest

from chessop.cli import main, print_stats
from chessop.stats import report
from chessop.store import FILENAME, Store, UsageDay
from test_account import delete_account
from test_data import forget
from test_hosted import DAY, NOW, Site, play_a_round
from test_lichess import sign_in as lichess_sign_in
from test_signin import ANN, sign_in
from test_store import a_round, passes_at_start


def events(data_dir: Path) -> list[tuple[str, int, int, int]]:
    """Each aggregate row's day, sign-ins, adoptions and deletions, oldest first."""
    store = Store.open(data_dir)
    try:
        return [(u.day, u.sign_ins, u.adoptions, u.deletions) for u in store.usage_days()]
    finally:
        store.close()


def test_a_sign_in_an_adoption_and_each_kind_of_deletion_increment_that_days_row(
    tmp_path: Path,
) -> None:
    site = Site(tmp_path)  # its clock stands at 08:00 UTC on 2027-01-15
    with site.browser() as ann, site.browser() as ben, site.browser() as cat:
        play_a_round(ann, success=True)
        sign_in(site, ann)  # a sign-in that adopts the anonymous learner
        lichess_sign_in(site, ben, "Ben")  # a sign-in with nothing to adopt
        play_a_round(cat, success=True)
        assert forget(cat).status_code == 303  # an anonymous learner forgotten
        assert delete_account(ann).status_code == 303  # an account deleted
        assert events(tmp_path) == [("2027-01-15", 2, 1, 2)]
        site.clock.now += DAY
        sign_in(site, cat)
        assert events(tmp_path) == [("2027-01-15", 2, 1, 2), ("2027-01-16", 1, 0, 0)]


TODAY, YESTERDAY = "2027-01-15", "2027-01-14"  # NOW, 08:00 UTC, and the day before


def seeded(store: Store | None = None) -> Store:
    """The store (an empty one in memory unless given) in which, on 2027-01-15: an anonymous
    learner from the day before played a success and a forced round; a new anonymous learner
    missed; a new learner who signed in succeeded; another new learner never played. One
    sign-in was counted that day."""
    store = Store.in_memory() if store is None else store
    older, newer = store.create_learner(NOW - DAY), store.create_learner(NOW)
    signed = store.create_learner(NOW + 60)
    store.create_learner(NOW + 120)  # never plays
    store.create_account(signed.id, "email", ANN, ANN, NOW + 60)
    store.count_sign_in(NOW + 60)
    older.commit(a_round(outcome="success", ended_at=NOW), passes_at_start)
    older.commit(a_round(outcome="forced", ended_at=NOW + 10), passes_at_start)
    newer.commit(a_round(outcome="miss", ended_at=NOW + 20), passes_at_start)
    signed.commit(a_round(outcome="success", ended_at=NOW + 90), passes_at_start)
    return store


def test_a_finished_days_derived_counts_are_written_beside_its_events() -> None:
    store = seeded()
    assert store.write_usage_day(TODAY, NOW + DAY)
    assert store.usage_days() == [
        UsageDay(
            day=TODAY,
            sign_ins=1,
            adoptions=0,
            deletions=0,
            active_anonymous=2,
            active_signed_in=1,
            new_learners=3,
            rounds=3,
            successes=2,
        )
    ]


def test_writing_a_finished_days_derived_counts_twice_changes_nothing() -> None:
    store = seeded()
    assert store.write_usage_day(TODAY, NOW + DAY)
    written = store.usage_days()
    late = store.create_learner(NOW + 30)
    late.commit(a_round(outcome="success", ended_at=NOW + 40), passes_at_start)
    assert not store.write_usage_day(TODAY, NOW + 2 * DAY)
    assert store.usage_days() == written


def test_a_day_with_nothing_on_it_is_written_as_zeros() -> None:
    store = seeded()
    assert store.write_usage_day(YESTERDAY, NOW)
    assert store.usage_days()[0] == UsageDay(YESTERDAY, 0, 0, 0, 0, 0, 1, 0, 0)


def test_a_day_not_yet_finished_is_not_written() -> None:
    store = seeded()
    with pytest.raises(ValueError, match="not finished"):
        store.write_usage_day(TODAY, NOW + 3600)
    assert [u.active_anonymous for u in store.usage_days()] == [None]


def test_the_aggregate_holds_no_learner_id_and_survives_the_deletion_of_every_learner(
    tmp_path: Path,
) -> None:
    store = seeded(Store.open(tmp_path))
    assert store.write_usage_day(TODAY, NOW + DAY)
    written = store.usage_days()
    for learner_id in range(1, 5):  # the four seeded
        store.delete_learner(learner_id, NOW + DAY)
    assert store.usage_days() == [*written, UsageDay("2027-01-16", 0, 0, 4, *[None] * 5)]
    store.close()
    db = sqlite3.connect(tmp_path / FILENAME)
    try:
        assert db.execute("SELECT COUNT(*) FROM learner").fetchone() == (0,)
        columns = {row[1] for row in db.execute("PRAGMA table_info(daily_usage)")}
    finally:
        db.close()
    assert columns == {
        "day",
        "sign_ins",
        "adoptions",
        "deletions",
        "active_anonymous",
        "active_signed_in",
        "new_learners",
        "rounds",
        "successes",
        "written_at",
    }


AT = NOW + 40 * DAY  # 2027-02-24, a Wednesday, 08:00 UTC: when the owner reads the stats


def a_site_lived(store: Store) -> Store:
    """The seeded store, then: the learner from 2027-01-14 played again a week later, when an
    anonymous learner with nothing played signed in and was adopted; in February the signed-in
    learner (1800+, the Sicilian opted out, snapshot 2027-01/x) and the new anonymous learner
    (every default) played again. The aggregate of 2027-01-14, -15 and -22 was written; the
    learner who never played was deleted on the day the stats are read."""
    seeded(store)
    older, newer, signed = (store.learner(i) for i in (1, 2, 3))
    older.commit(a_round(outcome="miss", ended_at=NOW + 7 * DAY), passes_at_start)
    adopted = store.create_learner(NOW + 7 * DAY + 60)
    store.count_sign_in(NOW + 7 * DAY + 120)
    store.adopt(adopted.id, signed.id, NOW + 7 * DAY + 120)
    signed.set_setting("band", "1800+")
    signed.set_setting("opted_out", ["Sicilian Defense"])
    signed.set_snapshot_version("2027-01/x")
    store.learner(signed.id).commit(
        a_round(outcome="success", ended_at=NOW + 35 * DAY), passes_at_start
    )
    newer.commit(a_round(outcome="success", ended_at=NOW + 36 * DAY), passes_at_start)
    for day in (YESTERDAY, TODAY, "2027-01-22"):
        assert store.write_usage_day(day, AT)
    store.delete_learner(4, AT)
    return store


TABLES = (
    """\
Active learners per day
  day         anonymous  signed in  total
  2027-01-14          0          0      0
  2027-01-15          2          1      3
  2027-01-22          1          0      1
""",
    """\
Active learners per week
  week of     anonymous  signed in  total
  2027-01-11          2          1      3
  2027-01-18          1          0      1
  2027-01-25          0          0      0
  2027-02-01          0          0      0
  2027-02-08          0          0      0
  2027-02-15          1          1      2
  2027-02-22          0          0      0
""",
    """\
Active learners per month
  month    anonymous  signed in  total
  2027-01          2          1      3
  2027-02          1          1      2
""",
    """\
New learners per day
  day         new
  2027-01-14    1
  2027-01-15    3
  2027-01-22    0
""",
    """\
Rounds per day
  day         rounds  per active learner
  2027-01-14       0                   -
  2027-01-15       3                 1.0
  2027-01-22       1                 1.0
""",
    "Success rate: 50.0% (2 successes in 4 rounds, forced exploration left out)\n",
    """\
Sign-ins, adoptions and deletions per day
  day         sign-ins  adoptions  deletions
  2027-01-14         0          0          0
  2027-01-15         1          0          0
  2027-01-22         1          1          0
  2027-02-24         0          0          1
""",
    """\
Retention of each week's new learners
  week of     new  after 1 day  after 7 days  after 30 days
  2027-01-11    3     3 (100%)      3 (100%)        2 (67%)
""",
    """\
Bands of active learners
  band   learners
  1500+         1
  1800+         1
""",
    """\
Openings of active learners
  opted out         learners
  none                     1
  Sicilian Defense         1
""",
    """\
Snapshot versions of active learners
  version    learners
  2027-01/x         1
  none              1
""",
)


def test_stats_prints_each_table_with_the_figures_of_the_seeded_database() -> None:
    printed = report(a_site_lived(Store.in_memory()), AT)
    for table in TABLES:
        assert table in printed
    assert "a round in the last 30 days" in printed  # what "active" means for the mixes


def test_chessop_stats_prints_the_tables_of_the_data_dirs_database(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a_site_lived(Store.open(tmp_path)).close()
    print_stats(tmp_path, AT)
    assert capsys.readouterr().out == report(a_site_lived(Store.in_memory()), AT)
    main(["stats", "--data-dir", str(tmp_path)], environ={})  # at the real time
    printed = capsys.readouterr().out
    assert TABLES[0] in printed and "Snapshot versions of active learners" in printed
    main(["--data-dir", str(tmp_path), "stats"], environ={})
    assert capsys.readouterr().out == printed
    main(["stats"], environ={"CHESSOP_DATA_DIR": str(tmp_path)})
    assert capsys.readouterr().out == printed


def test_chessop_stats_with_no_database_says_so_and_creates_none(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="no database"):
        main(["stats", "--data-dir", str(tmp_path / "nowhere")], environ={})
    with pytest.raises(SystemExit, match="no database"):
        print_stats(tmp_path / "nowhere", AT)
    assert not (tmp_path / "nowhere").exists()
