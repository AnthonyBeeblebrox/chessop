# 13: Opt-out and resets from the progress view

**What to build:** from the ledger the learner takes an opening out of (or back into) the repertoire, and resets an opening or a single position after a confirmation page. Each goes through the same regeneration path as a settings save.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §10.3, §7 (resets), §4 step 3 (opt-out on exact names). ADR 0006; ADR 0002 ticket 19 amendment.

**Blocked by:** 10 (Settings page), 12 (Position page).

**Status:** done

- [x] `POST /progress/opening/<family>/toggle` flips the family in `opted_out` and regenerates; the row stays listed with its scores
- [x] `POST /progress/opening/<family>/reset` and `POST /progress/position/<epd>/reset` show a confirmation page whose form deletes that opening's learner positions' records (grouped by inherited name) or that position's record
- [x] Round log and daily scores never deleted; in-flight rounds abandoned and tabs get a fresh round
- [x] Plain HTML forms, no JavaScript; no "Drill from here"
- [x] Tests: opt-out plus prune on toggle, a shared position named in a kept opening survives, both resets
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
