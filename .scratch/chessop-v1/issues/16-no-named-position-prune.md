# 16: No named-position prune, rounds as deep as popularity keeps

**What to build:** the repertoire stops pruning positions with nothing named at or below them, so a round runs until no move at its end clears the popularity floor, and a leaf need not be named. At round end the Explanation is still the ended position's own text, else the nearest position with a text on the path walked, labelled as borrowed.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §4 (steps 4, 5, expected size), §8 (`explanation`, `borrowed_from`), §13. ADR 0005 (ticket 24 amendment); decision [`../../chessop/issues/24-round-depth.md`](../../chessop/issues/24-round-depth.md).

**Blocked by:** None

**Status:** done

- [x] At load: main moves clearing the floor, opt-out, then reachability from the start, repeated until stable; no named-position prune
- [x] Unnamed positions below the last name are kept and drilled; a leaf is any kept position with no kept main move
- [x] Opting a family out still removes its exactly-named positions and whatever only they reach; opting back in restores them
- [x] A round ending on an unnamed leaf carries the nearest text on the path walked, with `borrowed_from` set
- [x] The build's diagnostics (§3.1 step 5) and any size bounds in tests follow the new expected sizes of §4
- [x] Tests that asserted the prune are rewritten to the new rule
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
