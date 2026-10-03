# 11: Progress ledger

**What to build:** the learner opens `/progress` and sees where they stand: the Score with its change since the last day played, White and Black scores, known / learning / never-passed counts, the in-session success rate against the 80–90 % target, a sparkline; then a table of openings that unfolds into exactly-named lines and into branches whose learner moves are coloured by recall. `?never=1` lists the never-passed positions. Server-rendered, no JavaScript.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §10.1, §4 step 9 (name inheritance, "First moves"), §6 (per-opening scores). The progress-view prototype (`prototype/progress-view/`, variant A).

**Blocked by:** 05 (The Score).

**Status:** done

- [x] Head: Score and change since the latest `daily_score` row before today; White and Black scores; known/learning/never-passed counts; in-session `successes / rounds` since process start, forced excluded, coloured outside 80–90 %; inline SVG sparkline of `daily_score.score`; never-passed count linking to `?never=1`
- [x] Openings = families inherited along the canonical order; "First moves" (ply 0 and 1) first, then by sum of pooled counts of each opening's learner positions
- [x] Row: name, ECO range, position count, known/learning/never-passed bar, Score, White and Black scores; opted-out openings still listed
- [x] `<details>` into exactly-named lines, then branches in canonical order with each learner move coloured: green ≥ 0.9, yellow 0.5–0.9, orange < 0.5, red relearning owed, grey never passed; a position appears once; each learner move links to its position page
- [x] `?never=1`: never-passed learner positions by pooled count
- [x] Link from the play page outside the board area
- [x] Tests: grouping and inheritance, per-opening scores, forced rounds excluded from the success rate
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
