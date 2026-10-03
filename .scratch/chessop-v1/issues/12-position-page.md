# 12: Position page

**What to build:** from the ledger the learner opens one position and sees the board, its name, the numbers of its record, a state word, its main moves coloured by the child's recall, and its explanation.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §10.2. Ticket 19.

**Blocked by:** 08 (Explanations), 11 (Progress ledger).

**Status:** done

- [x] `/progress/position/<epd>` (URL-encoded) renders server-side, no JavaScript
- [x] Board as SVG from `chess.svg`, learner's colour at the bottom; name (marked *inherited* when not exactly named), ECO, canonical line
- [x] Recall estimate, half-life, counted passes and misses, "relearning pass owed", time since last pass, share of band games reaching it, number of move orders
- [x] State word: known (R ≥ 0.9), learning (0.5–0.9), fading (< 0.5), relearning, never passed
- [x] Main moves as chips coloured by the child's recall, stubs marked
- [x] Explanation with lead, "more", borrowed label and CC BY-SA footer; fallback along the canonical order
- [x] Tests: state words, inherited name marking, explanation fallback
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
