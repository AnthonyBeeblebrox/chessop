# 10: Settings page

**What to build:** the learner opens `/settings`, sets their rating, widths, floor, share and the memory parameters, and saves: the repertoire regenerates in the running process with the right band, other open tabs abandon their round unrecorded and receive a fresh one. A confirmed "reset all history" deletes every position record.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §11, §7 (resets, settings changes), §4 (inputs), §3.3 (band loaded). ADR 0002, ADR 0003, ADR 0005.

**Blocked by:** 03 (`build-snapshot`: the graph file), 04 (Memory model and persistence).

**Status:** done

- [x] Jinja2 form with every key in spec §11 and its constraint (popularity floor ≥ the snapshot's storage cut-off, share 0–1, widths ≥ 1, `animation_ms` 0–100); invalid input is refused with a message
- [x] Rating mapped to one of the five bands (none → 1500–1800); changing it loads that band
- [x] Saving regenerates the repertoire in process; in-flight rounds in other tabs are abandoned unrecorded and those tabs get a fresh `round`
- [x] Records are never touched by a settings change; positions leaving the repertoire return with their records
- [x] "Reset all history" behind a confirmation deletes every `position_record` row; round log and daily scores kept
- [x] The declared band and the snapshot version are displayed; `forced_rate` noted as ignored when `width_player` = 1
- [x] Link to settings from the play page outside the board area
- [x] Tests: validation, regeneration leaving records intact, reset all, a second socket receiving a fresh round
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
