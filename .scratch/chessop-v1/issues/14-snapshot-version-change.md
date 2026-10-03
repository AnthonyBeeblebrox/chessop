# 14: Snapshot version change

**What to build:** when the learner starts chessop on a snapshot whose version differs from the one their database recorded (a new release, or `--snapshot`), the repertoire regenerates, no record is touched, and they are told once on the play page and once on the progress view.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §3.3 (refresh), §7 (`snapshot_version` setting), §8 (`round.notice`), §11. ADR 0003.

**Blocked by:** 10 (Settings page), 11 (Progress ledger).

**Status:** done

- [x] The loaded version string is recorded as `snapshot_version` and shown read-only in settings
- [x] On a mismatch at start: regeneration, the new version recorded, records untouched
- [x] The notice goes out once in `round.notice` on the play page and once on the progress view, then never again
- [x] Tests: mismatch triggers the notice once per surface; records intact
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
