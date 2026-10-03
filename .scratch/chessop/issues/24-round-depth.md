# Round depth: rounds end too early, where the book stops naming the line

Type: grilling
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

After v1 was built the learner played it and found the rounds too shallow: "games are not enough plies, they are not enough deep". Their round log at 1500-1800 (P = 2, O = 3) had successful rounds averaging 7.7 plies, 11 at most. Measured on the packaged 2026-08 snapshot at 1500-1800, a learner who never misses facing the popularity-weighted opponent averages 9.2 plies as White and 8.7 as Black, 13 at most. Two things end a branch:

1. **ADR 0005's prune**: every position with no exactly-named book position at or below it is removed, so a branch ends at its deepest name. All 704 stubs of the 1500-1800 repertoire are stored positions removed this way.
2. **The storage cut-off**: 0.02 % of the band's 150,000 games (ticket 22), 30 games, below which nothing is stored; popularity thins with every ply, so almost every line falls under it by ply 12-15.

Options put to the learner on 2026-09-24:

- **A. Build deeper snapshots**: lift the 150,000-game cap, lower the cut-off, or keep positions by their share of the parent's games: a rebuild, a larger snapshot, and ADR 0003 and ticket 22 reopened.
- **B. Drop the named-position prune**: a branch runs until popularity at the band ends it, not where the book stops naming it; no rebuild.

## Answer

Decided by the learner on 2026-09-24: **B**, keeping the Explanation of the last position on the path that has a text. Folded into ADR 0005 (ticket 24 amendment), ADR 0001 and ADR 0006 (pointers), [`spec.md`](../spec.md) §4, §13, the glossary (Repertoire, Branch, Main move) and build ticket [`chessop-v1` 16](../../chessop-v1/issues/16-no-named-position-prune.md).

- **No prune**: at load, keep the main moves that clear the popularity floor, apply the opt-out, then keep what the start position reaches over main moves, repeated until stable. A leaf is a position none of whose moves are main; it need not be named.
- **Measured on the packaged snapshot at the defaults (3, 3)**: 1500-1800 goes from 794 positions / 976 edges / 250 leaves / 15 plies deep / 65 % exactly named to 2,695 / 3,030 / 1,043 / 17 / 19 %; 1800-2100 from 1,104 / 1,326 / 310 / 17 / 60 % to 3,074 / 3,432 / 1,052 / 21 / 22 %. A perfect learner's round at 1500-1800 lengthens from about 9 plies to about 11 (White) and 10 (Black). The storage cut-off is now what ends a branch; going deeper still is option A, not taken.
- **Stubs stay in the rule but vanish in practice**: an edge that clears the floor leads to a child at least as popular, which is stored, so the only stubs left are edges the build dropped (cycles, the ply cap). 0 at both bands measured.
- **The Explanation is unchanged**: at round end the text shown is the ended position's own page, else the nearest position on the path walked that has one, labelled as borrowed (spec §8, ticket 15). Deep unnamed leaves mostly borrow.
- **Opt-out** removes the positions whose exact name is in the family, then reachability re-runs; nothing below a removed position survives unless another kept order reaches it.
- The banner keeps showing the last exact name seen on the path walked; the progress view keeps inheriting names along the canonical order.
