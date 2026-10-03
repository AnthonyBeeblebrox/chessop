# 22: Many learners in one WAL store

**What to build:** The one SQLite file becomes learner-keyed while local mode keeps behaving as one implicit learner. A learner table (id, created, last seen, snapshot version) is added; position records, round log, daily score and settings each gain the learner id. A forward-only migration attaches a real v1 file's rows to the implicit learner, turns a stored declared rating into the closed band it mapped to, and moves a file with no declared rating to 1500+, telling the learner once that the repertoire was regenerated (records untouched). The snapshot version becomes a per-learner setting, so the regeneration notice shows once per learner after a new snapshot. Deleting a learner removes everything of theirs. The store runs in WAL mode with `synchronous=NORMAL`, and last seen is written at most once a day. (Spec §3, ADR 0002.)

**Blocked by:** 18

**Status:** done

- [x] Opening a real v1 database file migrates it: all rows belong to the implicit learner and nothing is lost
- [x] A v1 declared rating becomes its closed band; no declared rating becomes 1500+ with the once-only notice and position records untouched
- [x] WAL and `synchronous=NORMAL` are in effect on the open store
- [x] Two learners in one store have isolated records, round logs, daily scores and settings (store tests)
- [x] Deleting a learner removes their rows from every table and no one else's
- [x] The snapshot-change notice is shown once per learner; dormant records return if a later snapshot restores their positions
- [x] The latency test runs on an on-disk store and still meets the 10 ms p95 budget
- [x] Local mode behaves as before through the existing wire, settings and progress tests
