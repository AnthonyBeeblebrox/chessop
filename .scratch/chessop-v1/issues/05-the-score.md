# 05: The Score

**What to build:** the learner sees one number for how well they know their repertoire: the Score, in the banner all the time, its per-round change on the verdict strip, and when a tab opens the change since the last round played. Each round end records the day's scores and counts.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §6, §7 (`daily_score`), §8 (`score`, `score_since`), §9. ADR 0001 ticket 16 amendment.

**Blocked by:** 04 (Memory model and persistence).

**Status:** done

- [x] Score = `sum(count(p) * R(p)) / sum(count(p))` over learner positions of the scoped repertoire, raw R (0 never passed); White and Black scores the same sum per colour; learner-to-move leaves excluded
- [x] Computed at every round-end commit and on demand
- [x] `daily_score` (local date) upserted in the round-end transaction with the scores after the commit and the day's `rounds` and `successes`
- [x] `round.score` and `round_over.score = {value, delta}`; `score_since` on a socket's first `round` only, from the latest `daily_score` row before now
- [x] Banner shows the Score with one decimal and, once per tab until its first round ends, `(−6.1 since Tue)`; verdict strip shows `71.6 % (+0.4)`
- [x] Tests: the Score against a hand computation, decay over time, daily upsert, score fields on the wire
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
