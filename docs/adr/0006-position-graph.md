# Repertoire: a graph of positions, not a tree of move sequences

Status: accepted (ticket 11, 2026-09-13)

Two move orders often reach one position (`1.d4 d5 2.c4 e6 3.Nc3 Nf6` and `1.d4 Nf6 2.c4 e6 3.Nc3 d5`), and whole systems converge this way. Ticket 05 made the tree a sequence trie, which drills the same position to different depths depending on how it was reached (14 of the 17 shared positions at 1800+ keep different replies per move order, ticket 12) and, once ADR 0005 ended lines at the book's names, left **195 of the 996 book lines real traffic reaches** out of the repertoire only because their games arrive by move orders other than the book's own (the Semi-Slav main line: 215 games pooled, 10 by the book's order; ticket 13). We decided that the repertoire is a **directed acyclic graph of positions keyed by EPD**, with game counts pooled over every move order, and that the learner's history is keyed the same way.

## Decision

- **The snapshot stores positions, not move sequences** (ADR 0003 amended). `build-snapshot` keys every game position by EPD (`python-chess` `Board.epd()`: placement, side to move, castling, en passant only when a capture is legal; the same call the book uses), sums counts over move orders, and stores per band the positions and the (position, move) edges whose pooled count clears the 0.02 % storage cut-off.
- **ADR 0005's rule runs on the graph unchanged**: at load, keep at every position the main moves (top-3 edges plus any edge with at least 5 % of the games reaching the position) whose pooled count clears the floor, then prune every position with no exactly-named book position at or below it, then keep what is reachable from the start position. Popularity in ADR 0001's sampling weight is the pooled edge count renormalised over the kept edges; the exploration bonus counts how often the learner has faced a (position, move) edge.
- **One position record per position.** Side to move is part of the EPD, and a learner position is by definition one where the learner is to move, so a record's colour is the side to move in its key: there is no second record "per colour" and history cannot bleed between colours (ADR 0001 corrected). A pass or miss on a position counts in full whatever move order reached it; the order walked is kept in the round log's path and nowhere else. The per-colour aggregates (the root's need per colour that draws the learner's side) are sums over White-to-move and Black-to-move learner positions.
- **A DAG by construction.** A position reached at two plies (a knight shuffle) would close a cycle; `build-snapshot` drops any edge that would, keeps the edge on the shorter path, and reports the count. No position is keyed by ply, so the book lookup and the record stay one-to-one with the position. Ticket 12 found no such case inside any cut-off tree of the 2013 sample.
- **Names**: the snapshot stores per position its **exact** book name or none. During a round the banner shows the last exact name seen on the path walked in that round; no inherited name is stored, since a position below two named orders would have to pick one.
- **A canonical move order per position**: the most popular order in the sample, computed from the trie before pooling; for named positions the book's own line as well. For consumers that need a line for a position outside any round (the progress view, the wikibook lookup of ticket 15).
- **Opting an opening out** removes the positions whose exact book name is in that family, then the prune and the reachability step re-run: "the book minus these names", nothing else special-cased. A shared position named in a kept opening survives by whatever orders still lead to it.
- **The round-end reveal** draws the position's main moves whatever order was walked: one position, one reply set, one reveal.
- **Need aggregation** (ADR 0001) becomes a memoised value per position rather than per tree node; updates after a round touch the visited positions and invalidate the memo above them.

## Amendment (ticket 18, 2026-09-22): pooled counts are the counts

Ticket 17 measured 234 of the 1,326 kept edges at 1800-2100 as **main under no single move order**: the edge's pooled count clears the popularity floor, but no one order into its position does (`1.d4 Nf6 2.Nf3 d6 3.c4`: 64 games over 4 orders, the largest 25, floor 30). 165 positions are entered only by such edges. Ticket 18 decided they are **theory, not junk**:

- **A position's traffic is its pooled traffic, whatever the orders.** The popularity floor, the top-3 rank and the 5 % share of ADR 0005 all apply to pooled counts and nothing else. No per-order floor, per-order share or per-order rank is added.
- Why: the edges main under no order are largely the lines this ADR exists to recover. The Semi-Slav Main Line (215 games over 102 orders, none above 13) has every in-edge main under no order, as do the QGD Orthodox and Tartakower, the Slav Exchange and the KID Smyslov; requiring one order to clear the floor would drop them again. ADR 0005 promises that a move real players make at the band is never scored as a miss, and `3.c4` above is played by one opponent in five at that position. And the London and Colle systems (17-73 orders into one position, the largest holding 4-24 %) are the same phenomenon, not a separate case there is a principled cut from.
- **"Junk admitted by pooling" is renamed *diffuse traffic***: positions and edges whose largest single order is below the floor. It is a diagnostic, not a defect. `build-snapshot` reports it per band (counts of diffuse positions and edges) beside the dropped-cycle count, so a future snapshot can be checked against ticket 17's numbers; the runtime never reads it.
- The share clause stays on pooled counts even where the larger base prunes a line at one band (ADR 0005 amended, same ticket).
- ADR 0005's "996 positions" were 996 trie nodes, 772 distinct positions; restated there.

Research: `docs/research/pooled-repertoire.md` (ticket 17) lists every diffuse position and edge at 1800-2100 and 1500-1800.

## Considered options

- **Sequence tree** (ticket 05 as charted): drills one position inconsistently across orders and loses the 195 transposition-only lines; keeping it would make the book's own move order, not the position, the thing the learner is tested on, against ticket 01's finding that experts store openings as positions.
- **Merge by position at load** from a trie snapshot: consistent replies, but the lost lines never enter the snapshot (no single order clears the storage cut-off), so it recovers nothing.
- **Partial credit across orders** (a fraction, or none until traversed): needs a second record keyed by order, for a distinction the learner is not being asked about.
- **Key by (EPD, ply)** to allow repeats: makes the book lookup and the record many-to-one for a case expected to be empty.
- **Store an inherited name per position** along the canonical order: shows the learner a name for a line they did not play.
- **Opt out by cutting the book's own lines**: leaves named positions reachable by other orders in scope while the learner asked for them out.

## Consequences

- The repertoire grows by the recovered transposition-only lines; the exact size, depth, dropped-cycle count and any junk pooling admits at 1800–2100 are measured by ticket 17 (`docs/research/pooled-repertoire.md`): 1,104 positions / 1,985 branches / 17 plies at 1800–2100, 108 of the 195 lines recovered, no cycles; 234 edges are main under no single order, which ticket 18 decided to keep (amendment above).
- The snapshot's shape changes (positions with count, exact name, canonical order; edges with count); it stays a separate read-only versioned file and the storage cut-off, floor and ply cap of ADR 0003 and 0005 are unchanged.
- The tree-width theorem of ticket 05 (only `max(P, O)` sizes the repertoire) still holds: widths bound the edges kept per position.
- The learner drilled as Black may reach the Semi-Slav by any main order; the opponent draws each edge by its real conditional popularity, so a rare order stays a rare path.
- The glossary gains **Position**; **Branch**, **Position record** and **Snapshot** are reworded (`CONTEXT.md`).
- Ticket 15 inherits the canonical order per position for the wikibook lookup and the "name on the path" rule for the banner.

Research behind this: `docs/research/transpositions.md` (ticket 12), `docs/research/repertoire-rule-candidates-recent.md` (ticket 13, "Transposition-only misses"), `docs/research/learning-openings.md` (ticket 01).

## Amendment (ticket 24, 2026-09-24)

ADR 0005 drops the named-position prune: at load the rule keeps the main moves clearing the floor, applies the opt-out, then keeps what the start position reaches. Opting an opening out removes its exactly-named positions and re-runs reachability only; a leaf need not be named.
