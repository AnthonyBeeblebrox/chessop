# Repertoire: as deep as the book names, as wide as popularity keeps

Status: accepted (ticket 13, 2026-09-12)

Ticket 05 cut the repertoire by an absolute popularity cut-off (a line stays only if 0.2 % of the band's games follow it exactly), which ends the Sicilian at ply 4 because its traffic splits across many variations. Reacting to the play-loop prototype the learner asked for *all named variations in the book*. We decided that the **book** (the Lichess `chess-openings` list, 3,810 named lines, CC0, already baked into the snapshot) sets a line's **depth** and popularity sets its **width**: a line runs exactly as deep as the book names it, and at every position only the top-`k` most popular replies are kept.

## Decision

- **Build at load, per band**: take the snapshot's sequence trie, keep at every node the **main moves** whose game count clears the **floor**, then **prune every node with no exactly-named book position at or below it**. A leaf is therefore always a named position, and a **Branch** ends at the deepest name on its path, never continuing by popularity beyond it.
- **Main moves at a position are the top-`k` replies plus every further reply holding at least a share `s` of the games reaching that position.** `k = max(width_player, width_opponent)` stays 3 (ticket 05) and `s` defaults to **5 %**. The share clause is what "main" means: a move a twentieth of the learner's opponents play is main whatever its rank. On the first day of August 2026 at 1800–2100 it widens exactly where a fourth move is common (after `1.e4 c5` it adds the Alapin 2.c3 at 7.9 %, the Bowdler 2.Bc4 and the McDonnell 2.f4; after `2.Nf3` it adds nothing, `2...g6` being 4.6 %); the widest position in the tree holds 7 replies. Share moves are main for both sides: the learner may play them, the opponent may draw them.
- **The floor** is a share of the band's games, so a current month behaves like the sample month. Default **0.02 %**, a setting, bounded below by the snapshot's storage cut-off of the same value (ADR 0003 amended). A named line that fewer games reach at the learner's band is not in their repertoire: the opponent could not weight it (ADR 0001) and it does not prepare them for games they will play.
- **Stubs.** A kept reply with nothing named below it is pruned from the tree but stays an accepted **main move** for the learner: playing it ends the round as a success with a pass on the position it was played from; the opponent never draws it (ADR 0001 amended). A move real players make at the band is never scored as a miss.
- **Scope default: the whole book.** Every opening family is in unless the learner opts it out; ticket 05's family scoping stays as the lever, its default flips from opt-in to opt-out.
- **Widths stay (3,3)** with (1,3) as strict recall; the share applies in both. A named line that needs a move outside the main moves at some position is dropped.
- **No minimum rate of appearance** for rare named lines: ADR 0001's exploration bonus and the full need of never-passed positions are relied on.
- **No "variation" term**: a book entry names a position; **Opening** stays the family used for scoping.

## Amendment (ticket 11, 2026-09-13)

ADR 0006 runs this rule on a graph of positions with counts pooled over move orders (ADR 0003 amended). Nothing in the rule changes: "node" reads "position", a reply's count is the pooled count of its (position, move) edge, and the share is over the pooled games reaching the position. Two consequences: the 195 book lines that only transposition-pooled traffic reaches at the floor enter the repertoire (size to be measured by ticket 17), and **opting an opening out** removes the positions whose exact book name is in that family, after which the prune and the reachability step re-run, so scope is "the book minus these names".

## Amendment (ticket 18, 2026-09-22): share on pooled counts, sizes in positions

- **The share clause is measured on pooled counts**: a reply is main when it holds at least 5 % of the pooled games reaching its position, over every move order. Measuring it on the reply's own order would make a move main for being 5 % of some rare order while 1 % of the position, which is order dependence of the kind ADR 0006 removed. The larger base prunes a knife-edge line at one band: at 1500-1800 the French Tarrasch `3.Nd2` (223 games, kept by the book's own order alone, just under 5 % of the pooled `1.e4 e6 2.d4 d5`) and the Rousseau Gambit (rank 6, 5.1 % in its best order) fall out; this is the 5 % threshold at its boundary, accepted. Lowering the share to 3 % or 4 % was not measured on the pooled graph and is not chosen blind.
- **The floor is the *popularity floor*** (glossary): it is a different thing from ADR 0001's need floor, which `CONTEXT.md` calls Floor. Where this ADR says "floor" it means the popularity floor.
- **Sizes restated in positions.** The "996 positions" of the Consequences below were 996 nodes of the sequence trie, which are 772 distinct positions; the graph ADR 0006 builds on the same sample holds 1,104 positions, 1,326 edges and 1,985 branches (`docs/research/pooled-repertoire.md`, ticket 17). "Lines" and "branches" are unchanged in meaning.

## Amendment (ticket 24, 2026-09-24): no named-position prune

Playing v1, the learner found rounds too shallow: about 9 plies for a learner who never misses at 1500-1800, because a branch ended at its deepest name. **The prune is dropped**: at load the main moves that clear the popularity floor are kept, the opt-out applies, then what the start position reaches over main moves is kept, repeated until stable. **The book no longer sets depth; the popularity floor does**: a branch runs until no move at its end clears the floor, and a leaf need not be named. Width is unchanged (top-`k` plus the share). A stub is still a main move whose child is not kept, but since a child is at least as popular as the edge into it, the only stubs left are edges the build dropped (cycles, the ply cap). On the packaged 2026-08 snapshot at (3, 3): 1500-1800 grows from 794 positions and 15 plies deep to 2,695 and 17; 1800-2100 from 1,104 and 17 to 3,074 and 21. The "relative cut-off" option below was rejected for growing into unnamed territory with no natural end; the absolute floor gives that end. The Explanation of a deep unnamed position borrows the nearest text on the path walked, as before (ticket 15). Measurements and options in `.scratch/chessop/issues/24-round-depth.md`.

## Amendment (2026-09-24): the learner's width defaults to 2

Playing v1, the learner asked for their own width (`width_player`) to default to 2; the opponent's stays 3, so `k = max(P, O)` and the tree are unchanged, and the share clause still accepts any move holding 5 % of the games. Defaults are now (2, 3); (1, 3) stays strict recall.

## Considered options

- **The book is the repertoire** (every named line regardless of traffic): 2,631 of 3,810 lines had no game at 1800+ in the sample month; unweightable and drills lines the learner never meets.
- **Relative cut-off** (a move stays if it is X % of the games reaching its parent): grows deep into unnamed territory with no natural end, and at the depths that keep the Najdorf it keeps hundreds of unnamed lines too.
- **Named lines with any traffic, widths uncapped**: about 1,000 lines on the sample month with up to 15 replies at a position; removes the width cap ticket 05 chose to bound what the learner must have ready.
- **Keep the absolute cut-off and lower it**: at 0.02 % the tree is over 500 nodes with most leaves unnamed and still stops where traffic thins, not where the book does.
- **Top-4 or top-5 instead of the share**: top-4 is close to the share rule in size (354 lines vs 389 at 1800–2100) and bounds the moves to have ready at four, but it rescues the Alapin by accident of rank and keeps a 1 % fourth move elsewhere; top-5 adds 60 more lines for sidelines nobody needs. A share of 8 % or 10 % misses the Alapin (7.9 %) and adds nothing.
- **Floor 0.01 %**: another 80 lines and 22-ply tails, at the price of doubling the snapshot; left as a setting the snapshot does not yet allow.

## Consequences

- The repertoire is several times larger and deeper than ticket 05's: at 1800–2100 on the recent sample, **389 lines and 996 positions** against the old rule's 69 and 173, covering 535 of the 996 book lines real traffic reaches; the deepest lines run to 17 plies (Sveshnikov, Yugoslav Attack). Numbers per floor and width in `docs/research/repertoire-rule-candidates.md` (2013) and `repertoire-rule-candidates-recent.md` (2026-08).
- The tree-width theorem of ticket 05 (only `max(P, O)` sizes the tree) still holds with the share added to both sets.
- **Ticket 11** (transpositions) inherited a sharpened case: of the 996 book lines real traffic reaches at the floor, **195 are missed only because their traffic arrives by move orders other than the book's own** (the Semi-Slav main line: 215 games pooled, 10 by the book's order). ADR 0006 keys by position and recovers them.
- The snapshot's ply cap rises to the deepest book line (36 plies); the per-node name must say whether it is an exact match (ADR 0003 amended).
- Settings gain the floor and lose nothing; the cut-off setting of ADR 0003 *is* the floor.
- The glossary gains **Book**; **Repertoire**, **Branch** and **Main move** are reworded (`CONTEXT.md`).
