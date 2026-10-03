# Transpositions: is a branch a move sequence or a position, and how does success credit a position reached another way?

Type: grilling
Status: resolved
Blocked by: 12, 13
Map: [Chess opening trainer by sampling](../map.md)

## Question

Two move orders reach the same position — `1.e4 e5 2.Nf3 Nc6` and `1.Nf3 Nc6 2.e4 e5` are one position, and whole systems converge this way. Ticket 05 made a Branch a *path* (a move sequence) and both the sampling unit and the success unit, while the data-source research recommends keying the tree by *position* so transpositions merge. Those two pull against each other. Decide:

- Is a Branch a move sequence or a position? If a position, what is a leaf, and how is a branch displayed to the learner?
- When the learner succeeds on one path into a position, how much credit does that same position get when reached by another path — all of it, a fraction, or none until traversed?
- The learner is drilled on both colours in one repertoire, so the same position recurs with the learner on **opposite** sides (after `1.e4 e5` the learner may have played `e4` as White or `e5` as Black). Ticket 05 says weights must never bleed across colours — confirm that stays two separate records, and say how a position is keyed to make that true.
- The reveal after each move shows the main moves for the position the learner just left. On a transposition, does it show what they already demonstrated on the other path?

Resolve any glossary consequences in `CONTEXT.md`, where `Branch` is currently defined as a path.

HITL: grill the user; do not answer for them.

Inherited from ticket 06 — settled, do not re-litigate:

- History is kept **per tree node (learner position) and per learner colour**, not per branch: a pass on every position got right, a miss on the one position missed. `Branch` is now only the path walked in a round. So the second bullet above ("how much credit does the same position get when reached another way") becomes: **do tree nodes that reach the same position share one position record, or does each move order keep its own?** Ticket 12 measured that 14 of 17 transposition groups keep different replies under different move orders, so a shared record would also have to say which continuation set applies.
- The colour question is answered structurally: side to move is in the position key and no transposition group spans plies (ticket 12), so a record needs the learner's colour only because both colours are drilled from one tree — two records per position, whichever keying is chosen.
- The opponent aggregates need by popularity-weighted mean over the learner positions below each move (ADR 0001); a shared record changes what "below" means for a merged node, not the rule.


Inherited from ticket 08 — settled (ADR 0003):

- The snapshot is the **sequence trie** with an EPD and game count per node, stored at a loose 0.02 % cut-off and never merged at build. A merged DAG (ticket 12's 216 positions) and a pooled-count DAG (268 positions, 53 of them qualifying only once move orders are summed) are both derivable when the app loads the tree, so this ticket chooses freely between sequence, merged and pooled; nothing in the data file forces a side.

## Comments

**2026-09-12, agent.** Now also blocked by ticket 13 ("Repertoire rule: every named variation in the book?"): if the repertoire becomes the named lines of the openings list, the tree is far larger and deeper than the 235-position one ticket 12 measured, and transpositions between named move orders matter more. Decide the repertoire first, then this.

**2026-09-12, agent.** Ticket 13 is resolved (ADR 0005), so this ticket is unblocked. Inherited: the repertoire is now book-terminated and about four times larger (389 lines / 996 positions at 1800–2100 on the August 2026 sample, 17 plies deep). The recent measurement (`docs/research/repertoire-rule-candidates-recent.md`, "Transposition-only misses") found that **195 of the 996 book lines real traffic reaches are missed only because their games arrive by move orders other than the book's own**: no single order clears the floor although the position does (Semi-Slav main line 215 pooled vs 10 own-order games; QGD Semi-Tarrasch 116 vs 9; London System main line 107 vs 1). Keying by position and pooling counts over move orders would recover them; this is now the strongest argument in the sequence-versus-position decision, alongside ticket 12's 14 of 17 groups with inconsistent replies.

**2026-09-13, round 1 settled**: the repertoire is a pooled position graph built at snapshot time (the merged-at-load option recovers nothing, since the lost sequences never enter the snapshot); the position record is keyed by the EPD alone, colour being the side to move in it; credit across move orders is full; one reveal per position; the pooled repertoire is measured after the decision, by a research ticket.

**2026-09-13, round 2 settled**: `build-snapshot` guarantees a DAG by dropping cycle-closing edges; the snapshot stores exact book names only and the banner inherits along the path walked; a canonical (most popular) move order is stored per position, plus the book's own line for named positions; opting an opening out removes its exactly-named positions and re-runs the prune; recorded as ADR 0006 with amendments to ADR 0001, 0003 and 0005.

## Answer

**The repertoire is a graph of positions keyed by EPD, with counts pooled over move orders.** ADR 0006, `docs/adr/0006-position-graph.md`.

- **A Branch is a path, a position is the node.** `build-snapshot` keys every game position by EPD (python-chess `Board.epd()`, the book's own key), sums counts over move orders, and stores per band the positions and (position, move) edges above the 0.02 % storage cut-off; a leaf is still the deepest book-named position on a path (ADR 0005 runs unchanged on the graph). The 195 book lines lost to transposition come back. Snapshot shape amended in ADR 0003; size measured by ticket 17.
- **Credit is full**: one position record per position, so a pass or miss via one move order is a pass or miss via every other; the order walked lives only in the round log's path.
- **Colour is the side to move.** A learner position is one where the learner is to move and side to move is inside the EPD, so the record key is the EPD alone, ADR 0001's "two records per colour" was vacuous and is corrected; bleed across colours is impossible by construction, and the per-colour need at the root is a sum over White-to-move and Black-to-move positions.
- **The reveal** draws the position's main moves whatever order was walked: one position, one reply set.
- **Also settled**: a DAG by construction (cycle-closing edges dropped at build, count reported); only exact book names stored, the banner inherits along the path walked in the round; a canonical most-popular move order per position (plus the book's line for named positions) for the progress view and ticket 15's wikibook lookup; opting an opening out removes its exactly-named positions and re-runs the prune and reachability.
- **Glossary**: new **Position**; **Branch**, **Position record** and **Snapshot** reworded.
- **Rejected**: the sequence tree; merge at load; partial or no credit across orders; keying by (EPD, ply); a stored inherited name; opting out by cutting the book's own lines.

**Handed on**: ticket 17 (new, research) measures the pooled repertoire at 1800–2100 on the August 2026 sample. Ticket 15 inherits the canonical order and the banner rule.
