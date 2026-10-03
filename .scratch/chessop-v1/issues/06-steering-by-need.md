# 06: Steering by need

**What to build:** rounds steer toward what the learner knows least: the side is drawn by per-colour need, and the opponent weights each reply by popularity times the sum of the mean need below it and a fading exploration bonus (ticket 23). With no history the opponent plays like the band restricted to the repertoire.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §5.2, §5.3 steps 1–2, §5.4. ADR 0001; `prototype/play-loop/server.py` for feel (it works on a tree, not a DAG).

**Blocked by:** 04 (Memory model and persistence).

**Status:** done

- [x] Mean need below an edge over the learner positions reachable from its child over kept main moves, weighted by pooled count, each descendant once (a shared descendant is not counted twice); an empty set (stub, edge onto a leaf) has mean need = floor
- [x] Memoised aggregates invalidated along every ancestor of a position whose record changed at commit
- [x] Per-colour root need; `p_white = clip(need_white / (need_white + need_black), side_floor, 1 - side_floor)`, 0.5 when both are 0
- [x] `faced(m)` rebuilt from the round log at start and counted as the opponent plays
- [x] Opponent weight `pop^alpha * (mean_need + C / sqrt(1 + faced))`, proportional draw, no Gumbel noise and no clamp ([ticket 23](../../chessop/issues/23-exploration-bonus-inside-the-product.md), ADR 0001 amended)
- [x] `move` handling stays under 10 ms p95 on a ~10k-position band
- [x] Tests: mean need on a small DAG with a shared descendant, memo invalidation, root need, empty-set mean need = floor, no-history frequencies match renormalised popularity within tolerance at `C = 1`, a rarely faced move favoured once the others are faced, stubs never drawn, side floor honoured
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
