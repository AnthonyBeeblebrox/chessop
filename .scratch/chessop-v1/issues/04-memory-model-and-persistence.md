# 04: Memory model and persistence

**What to build:** the learner's history survives: each learner position keeps a record (passes, misses, last pass, relearning mark) in one SQLite file in the data directory, updated at every round end in one transaction, with every round appended to the round log. Pass kinds (counted, sure, relearning) are judged at the moment of each move; a round that does not end writes nothing.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §5.1, §7 (tables `schema_version`, `settings`, `position_record`, `round_log`; round-end commit), §2 (`--data-dir`, `CHESSOP_DATA_DIR`). ADR 0001, ADR 0002.

**Blocked by:** 02 (Repertoire rule at load).

**Status:** done

- [x] Data directory from `--data-dir`, else `CHESSOP_DATA_DIR`, else `~/.local/share/chessop/`; the file `chessop.sqlite` created on first run through forward-only migrations tracked in `schema_version`
- [x] Half-life `clip(h0 * 2^(s - f), h_min, h_max)`, recall `2^(-(now - t_last)/h)`, `R = 0` never passed, Need `max(floor, 1 - R)`, parameters at the §5.4 defaults
- [x] Pass: relearning pass clears the mark and sets the clock, not counted; sure pass (R ≥ 0.9) sets the clock only; otherwise counted. Miss: `f += 1`, relearn set, clock untouched
- [x] Round end (success or miss) commits under one process-wide lock in one transaction: records updated, `round_log` row appended with `before` snapshot, path, outcome, end EPD, plies, snapshot version
- [x] A dropped socket, a `next` mid-round, or a killed process writes nothing
- [x] Records are keyed by EPD and outlive a change of repertoire
- [x] Tests: pass kinds, miss halving without touching the clock, clipping, R = 0, Need floor, transaction atomicity, migrations from an empty file, relearning over the wire
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
