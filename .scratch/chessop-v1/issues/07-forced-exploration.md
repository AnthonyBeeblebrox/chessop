# 07: Forced exploration

**What to build:** now and then, at a learner position with several accepted moves, the move with strictly the lowest mean need is set aside for that turn: the page draws it as a yellow arrow and the banner says "not e5 this time". Playing it ends the round as forced: no record touched, no score delta, not counted in the day's rounds.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §5.3 steps 3–4, §6 (no delta after forced), §7 (forced excluded from `daily_score` counts), §8 (`forced`, `forced_uci`), §9. ADR 0001, ticket 05's invariant.

**Blocked by:** 05 (The Score), 06 (Steering by need).

**Status:** done

- [x] With probability `forced_rate` at a learner position with `|A| ≥ 2`, set aside the lowest mean-need move only when strictly below the second lowest; ties and never-seen positions force nothing; never when `width_player` = 1
- [x] `round`/`moved` carry `forced`/`forced_uci` for the learner turn now to move
- [x] Playing the set-aside move ends the round as `forced`: `round_over.outcome = "forced"`, `reveal.played` set, `score.delta` null; records untouched; logged in `round_log`; excluded from `daily_score.rounds` and `successes`
- [x] Page: yellow arrow before the learner moves, banner "not e5 this time", at round end the learner's move yellow, verdict strip in the forced form with no delta
- [x] Tests: strict minimum only, never at P = 1, forced round over the wire, absent from daily counts
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
