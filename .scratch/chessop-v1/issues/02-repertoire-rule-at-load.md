# 02: Repertoire rule at load

**What to build:** the rounds are drilled over the repertoire the spec defines, not over every stored edge: main moves by top-k, share and popularity floor on pooled counts; opted-out families removed and the graph pruned to a fixed point; stubs accepted for the learner and never drawn by the opponent; leaves end the round as a success; the learner's accepted set and the opponent's drawable set follow the two widths. The revealed position follows spec §8: the position the round's last move was played from (the opponent's position before its reply when the reply lands on a leaf).

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §4, §5.3 steps 4–5, §8 (`round_over.reveal`). ADR 0005, ADR 0006.

**Blocked by:** 01 (Walking skeleton).

**Status:** done

- [x] Main moves at every position: edges clearing the floor f, top-`max(P, O)` by count (ties: count descending, then SAN descending) plus every edge holding at least share s of the position's pooled count
- [x] Opt-out removes positions whose exact name's family is opted out; prune removes positions with no exactly-named position at or below over main moves, then keeps only what the start reaches; the two repeat until stable
- [x] Stubs stay main moves for the learner (a pass on the position played from, round ends as success) and are never drawn by the opponent
- [x] Learner accepted set = top-P main moves plus share moves (stubs included); opponent drawable set = top-O plus share moves minus stubs
- [x] Leaves identified; a learner-to-move leaf is not a learner position; the round ends as a success on reaching a leaf by either side
- [x] `round_over.reveal` names the right position for success on the learner's move, success on the opponent's reply, and miss
- [x] Defaults P = 3, O = 3, f = 0.0002, s = 0.05, band 1500–1800 held as in-memory defaults for now (settings persistence comes later)
- [x] Fixture tests: top-k, share, floor, tie order, opt-out + prune fixed point, stubs, leaves, reachability; wire tests for both success kinds
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
