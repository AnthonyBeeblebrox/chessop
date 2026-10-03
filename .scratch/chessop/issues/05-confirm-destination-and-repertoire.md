# Destination and repertoire: what counts as a 'main opening', how deep, and for which side?

Type: grilling
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

First confirm the map's Destination (build-ready spec) or redraw it, since it was charted unattended. Then define the repertoire: is 'main openings' the top-N most popular lines from the Lichess explorer at some rating band, a curated list (ECO families), or something the learner picks? How deep does a branch go (fixed ply count, popularity threshold, or until the position leaves 'theory')? Does the learner train as White, Black, or both, and is a branch the learner's moves, the opponent's moves, or the full line? Resolve the glossary terms Opening, Branch, Line, Repertoire in `CONTEXT.md`.

HITL: grill the user; do not answer for them.

## Comments

**Round 1 settled** (interim record; the answer is written on resolution, below):

- **Destination**: confirmed as written, with one addition — *single learner, local-first*. The unattended charting caveat in the map is therefore discharged.
- **What "main openings" means**: hybrid agreed. Derive the candidate set from the CC0 dump by popularity cut-off, group it by ECO family via the `chess-openings` TSV, and let the learner opt families in. Cut-off and rating band deferred to round 2.
- **Which side the learner plays**: the user overrode the recommendation of two separate repertoires. **Both colours, mixed into one** — one repertoire the learner drills, with both sides in it. The consequence (the same position carrying a different meaning depending on the learner's side) is put to the user as round 2 Q8.

**Round 1 still open**: what a Branch is, whether the repertoire fixes one learner move per position, where a branch ends, the width parameter, the rating band.

**Round 2 in flight**: destination, repertoire source and learner side above; plus branch unit, learner move set, depth, width (opponent candidate cap), rating band, and the mixed-colour consequences.

**Iteration model (stated by the user in round 2, reshaping the ticket):**

1. The app samples which side the learner plays (e.g. it comes up White).
2. At each learner turn the app accepts any of the top-`width` moves (at width 3 as White: `1.e4`, `1.d4`, `1.Nf3`). Playing anything else is a failure and a fresh iteration starts.
3. The learner picks one of them (e.g. `1.e4`), and that choice selects the branch to traverse.
4. At each opponent turn the opponent samples among its own top-`width` replies with probability proportional to popularity x factor, the factor falling as the learner's knowledge of that branch rises (matches ticket 04's `w = popularity(path) * (eps + 1 - R)`).

Consequences for this ticket: **width applies to both sides**, not the opponent only (round 2 Q7 assumed opponent-only); the learner's move is **a set of acceptable main moves**, not one specified move (round 2 Q5 recommendation overridden); and the thing being drilled is app-defined main moves rather than a set of lines the learner commits to, which puts the glossary term **Repertoire** in question.

## Answer

**Destination: confirmed, with one addition** — *single learner, local-first*. The map's unattended-charting caveat is discharged.

### What "main" means

- Candidate lines are built offline from a CC0 dump month, filtered to the learner's **rating band** (both players inside it), defaulting to the learner's own declared rating and falling back to 1500-1800 when unknown.
- A line is in the tree iff it was played in **>= 0.2% of all games in that band**. The threshold is **absolute, not relative**: measured against every game in the band, not against the games reaching the parent position. That is what terminates the tree — no depth cap is needed, because no cut-off tree reaches ply 20 (the deepest is ply 18).
- At 1800+ (9,525 games of the 2013-01 dump) 0.2% gives 450 positions and a deepest ply of 18 (nine moves each); with the widths below, **86 iterations and 235 positions**. A 1% cut-off was rejected: 23 iterations / 61 positions is attractive, but it stops at ply 8 — four moves each — short of the 14-18 ply at which real players leave the book (ticket 01).
- Candidate lines are grouped into **ECO families** via the CC0 `chess-openings` TSV, and the learner opts families in. "Main" is therefore measured while the repertoire is theirs to scope.

### Sides

- **Both colours, one repertoire.** The app samples the side each iteration, weighted toward the colour whose branches carry the highest sampling weight (the one least known), with a floor so neither colour starves.
- The learner never has a move sampled for them.

### Branch and success

- **Branch** = one full path from the start position to a leaf of the repertoire. The sampling unit and the success unit are the same object.
- Where the learner is to move, **any of the top `width_player` moves is acceptable**; anything else leaves the repertoire. Success is scored on the learner's moves only — a wrong opponent move never counts against them.
- `Line` is not a separate term.

### The two widths

- `width_player` (P): how many of the most popular moves are acceptable at the learner's turn.
- `width_opponent` (O): how many the opponent samples among.
- **Only `k = max(P, O)` sizes the tree**, because every position holds the union of both sets; counts repeat along the anti-diagonal. P alone therefore cannot shrink the repertoire — it only raises the pass bar. Both must come down: `(1,1)` collapses the tree to a single 8-position line.
- **Default (3,3)**: at a 0.2% cut-off, 86 iterations / 235 positions, rejecting 9.98% of the move mass real players produce at the learner's decision points. `(5,5)` gives 137 / 343 at 4.38%.
- **(1,3) ships as a "strict recall" mode**: the structurally identical tree, but 38.8% of real move choices rejected (39.5% at a 1% cut-off), because the learner must match the single most popular move.
- Mean acceptable learner moves is only ~1.6 even at P=5, so P bites almost entirely at the first move or two.

### Hidden, revealed, failed

- The acceptable moves are **hidden while the learner is to move**: they must produce a main move from memory.
- **After the learner's move** the app reveals the accepted set for the position they just left, so they learn the variations they did not pick.
- An off-book move ends the iteration: **reveal, then hard-restart**. No play-out, because a post-reveal replay must never count as success (ticket 01). This closes the map's "Leaving the book" fog.

### Forced exploration (epsilon)

- With probability epsilon the app **discards the acceptable move whose subtree the learner knows best** (lowest weight, highest R) and tells them so. It reuses the opponent's weight function rather than adding a second notion of "popular", falling back to the most popular move when there is no history.
- **Invariant: epsilon > 0 requires width_player >= 2** — at P=1 there is nothing left to play.
- Keep epsilon small (0.1-0.2): it sets a floor on the failure rate.
- Rationale: at P>1 a learner who knows one move per position passes every one of their nodes on that single line, so recorded success measures recognition of *a* main move rather than coverage. Epsilon is what makes the wider mode measure coverage.

### Glossary

`CONTEXT.md` updated with `Opening`, `Branch`, `Repertoire` resolved and `Line` explicitly excluded.

### Handed to other tickets

- **Ticket 06** inherits first-try scoring, per-branch success, the reveal's cuing effect (a position seen moments ago is cued, not recalled), epsilon's floor on the failure rate, and ownership of the sampling-rule ADR.
- **Ticket 08** inherits the cut-off (0.2%, absolute) and the rating-band rules; the data-source ADR records them.
- **Ticket 11** (new, on the frontier): transpositions.

**Evidence**: `docs/research/tree-width-measurements.md` — measured across all 150 cells (3 bands x 2 cut-offs x 25 (P, O) combinations), validated by reproducing `refs/lichess/dump-2013-01-tree-stats.txt` exactly.

**2026-09-12, agent.** The cut-off rule decided here is reopened by ticket 13 ("Repertoire rule: every named variation in the book?") after the learner, reacting to the play-loop prototype, asked for all named variations. Nothing else in this ticket is in question.

**2026-09-12, agent.** Ticket 13 resolved: the absolute 0.2 % cut-off is superseded by ADR 0005 (book-terminated depth, top-3 plus 5 % share width, 0.02 % floor). Widths, sides, hidden/revealed/failed and forced exploration stand.
