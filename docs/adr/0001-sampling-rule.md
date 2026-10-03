# Opponent sampling: per-position half-life need, backed up the tree

Status: accepted (ticket 06, 2026-09-11)

The opponent must steer rounds toward what the learner knows least while never letting anything be forgotten, and the play loop must stay fast. We decided to keep the learner's history **per position and per learner colour**, not per branch, and to turn it into a **need** through a half-life recall model that the opponent aggregates up the tree at each of its turns.

## Decision

- **History lives on positions.** Every position where the learner is to move carries two position records, one per learner colour. A round is a playout: each position the learner got right takes a pass, the one position where they went off book takes a miss. A miss is charged to that position only; the positions passed on the way to it keep their passes.
- **Recall is a half-life model** (Leitner / Duolingo HLR shape). A record holds counted passes `s`, misses `f`, the time of the last pass, and a relearning mark. Half-life `h = clip(h0 * 2^(s - f), h_min, h_max)`, recall estimate `R = 2^(-delta / h)` with `delta` the time since the last pass, `R = 0` if never passed. Need `u = max(floor, 1 - R)`.
- **A pass counts only as new evidence.** If `R >= 0.9` at the moment of the pass, only the clock is refreshed. The first pass after a miss is a relearning pass: it clears the mark and refreshes the clock but is not counted. A miss always counts (`f + 1`, `h` halves, mark set) and never touches the clock, so a failed position keeps a high need and comes back soon.
- **The opponent aggregates by popularity-weighted average.** At an opponent position, each candidate move `m` gets `weight(m) = pop(m)^alpha * mean_need(subtree below m) + exploration bonus`, where `pop` is the Lichess move frequency renormalised over the moves kept in the repertoire at that position, `mean_need` is the popularity-weighted average need of the learner positions below `m`, and the bonus is Boltzmann-Gumbel noise scaled by `C / sqrt(1 + times the learner has faced m)`. The opponent plays `m` with probability proportional to its weight. With no history, this is exactly the database opponent restricted to the repertoire.
- **The learner's side** is drawn per round with probability proportional to that colour's total need at the root, floored at 0.2 per colour.
- **Forced exploration** (ticket 05) discards, with probability 0.1, the learner's main move whose subtree has the lowest mean need. It reuses the opponent's aggregate rather than a second notion of "known".
- **Every round is logged**: side, path, where it ended, outcome, and for each learner position visited its counts, elapsed time and predicted `R` before the round. The log is a first-class store so `h0` and the doubling factor can be refitted HLR-style.
- **Defaults** (priors from vocabulary and flashcard data, all tunable): `h0` = 1 day; `h` clipped to [15 min, 9 months]; sure threshold 0.9; floor 0.1; `C` = 1.0; `alpha` = 1; forced exploration 0.1; side floor 0.2; target in-session success 80 to 90 % net of forced exploration, displayed and logged only, nothing self-adjusts in v1. No cap on never-seen material in v1.

## Amendment (ticket 10, 2026-09-12)

The play-loop prototype showed that silent forced exploration is indistinguishable from a bug: the learner played their best-known main move, the round ended, and a miss was charged. Three changes:

- Forced exploration is **announced** at the turn it applies (the play page names the set-aside move).
- It fires only when the lowest subtree mean need is **strictly** lower than the next one; a tie, and in particular a position with no history, forces nothing.
- Playing the set-aside move **ends the round without a pass or a miss**: the record is untouched, because a main move was produced. The wire carries it as a third verdict and outcome, `forced`.

## Amendment (ticket 13, 2026-09-12)

ADR 0005 ends a line at the deepest position the book names. A main move that is popular enough to keep but has no named position below it is a **stub**: it stays in the learner's accepted set (a move real players make at the band is never scored as a miss) and playing it ends the round as a success, with a pass on the position it was played from; the **opponent never draws a stub**, so it adds no line to drill and carries no subtree need. Nothing else in the rule changes; the popularity floor that keeps rare named lines out of the repertoire is ADR 0005's, not a sampling floor.

## Amendment (ticket 11, 2026-09-13)

ADR 0006 keys the repertoire and the learner's history by **position** (EPD). Two corrections and no change to the rule:

- **One record per position, not two.** Side to move is part of the EPD and a learner position is one where the learner is to move, so the record's colour is the side to move in its key; the "two records per position, one per learner colour" above was vacuous. The per-colour split lives only in the aggregates: the root's need per colour, used to draw the learner's side, is the sum over White-to-move and Black-to-move learner positions.
- **Popularity and the bonus are per edge.** `pop(m)` is the pooled count of the (position, move) edge over the pooled count of the position, renormalised over the kept edges; "times the learner has faced `m`" counts the edge. A pass or miss counts in full whatever move order reached the position.
- **The aggregate is memoised per position** in the graph rather than cached per tree node; a round's update touches the visited positions and invalidates the memo above them.

## Considered options

- **Per-branch records** (ticket 05's sketch, tabia / neuralpgn style): a miss has no single branch to charge, and a well-known prefix is re-tested on every visit. Rejected once the user framed the tree as MCTS-style per-node statistics with backup.
- **FSRS** as the recall model: better fitted, spacing-aware, but 21 opaque parameters fitted on Anki logs, none chess. Kept as the drop-in replacement if geometric decay proves too aggressive; nothing else changes.
- **ACT-R**: needs every visit timestamp and has no native notion of a miss.
- **Sum or weakest-line aggregation** over the subtree: the sum rewards moves for having many sub-lines; the weakest-line rule keeps a whole move alive for one unknown position. Weakest-line is the fallback if the average lets weak sub-lines hide.
- **Every pass counts** (plain Leitner): the starting position would double its half-life on every White round, and a pass minutes after a reveal would be credited as recall.
- **Collapse or reset on a miss**: harsher than halving and no better supported by the literature (ticket 01: never drop a known item; ticket 04: collapse, don't reset).

## Consequences

- The position is the unit of history. Ticket 11 (ADR 0006) settled that tree nodes reaching the same position share one record: the repertoire is a graph of positions.
- Updates touch only the visited positions and their ancestors' cached aggregates, O(depth); sampling is O(depth x branching). Fast enough for the client-side loop without alias tables.
- The progress view can show per-position recall estimates and half-lives directly; the numbers are explainable in one sentence each.
- The realised success rate and the round log are what the later evaluation work consumes; whether to cap new material or auto-tune toward the target rate is deferred there.

Research behind this: `docs/research/learning-openings.md` (ticket 01), `docs/research/sampling-algorithms.md` (ticket 04).

## Amendment (ticket 16, 2026-09-15)

The **score** the play page shows is derived from this model, not a second one: `Score = sum(count(p) * R(p)) / sum(count(p))` over the learner positions `p` of the scoped repertoire, with `count` the pooled snapshot count and `R` the raw recall estimate (never-passed = 0; not `1 - need`, so the floor does not cap it at 90 %). It is the same root aggregate the opponent memoises, so it costs nothing at round end. Weighting by count makes it a per-turn probability: the chance that, at a learner turn drawn from the band's games within the repertoire, the learner produces a main move. It decays between sessions like every estimate under it; the unweighted mean, the share of sure positions and the share of branches playable end to end were considered and rejected (ticket 16). One combined number over both colours; per colour and per opening only in the progress view. The in-session success rate stays a separate, displayed-only figure and is expected to sit below the score, since sampling steers toward weak positions.

## Amendment (ticket 21, 2026-09-24)

Two details the rule left open. **An empty subtree has the floor as its mean need**: below a stub, or an edge onto a leaf, no learner position remains to learn, so the edge counts as fully known; forced exploration sets such a move aside first when it is strictly the lowest, and the opponent weights an edge onto a leaf by popularity times the floor. **A leaf where the learner is to move is not a learner position**: the round ends on reaching it, so it is never drilled, keeps no record and stays out of the aggregates, the Score and the side draw. And **"net of forced exploration" means forced rounds are left out** of both the rounds counted and the successes counted, in the daily score table and the in-session success rate; the round log still records them.

## Amendment (ticket 23, 2026-09-24)

The opponent's weight contradicted its own claim: added Gumbel noise of scale `C = 1` swamps a popularity share in [0, 1], so with no history a 70/30 split played about 58/42 (found by the spec review of build ticket 06). **The exploration bonus moves inside the product and the noise goes**: `weight(m) = pop(m)^alpha * (mean_need(m) + C / sqrt(1 + times the learner has faced m))`, the move drawn with probability proportional to its weight. With no history every weight is `pop * (1 + C)`, so the opponent is exactly the database opponent restricted to the repertoire at any `C`; rarely faced moves are still favoured, in proportion to their popularity, and the favour fades as they are faced. Every weight is at least `pop * floor`, so no clamp is needed. Rejected: the textbook Boltzmann-Gumbel argmax (its shrinking noise drifts the opponent toward always playing the most-needed move) and dropping the bonus.

## Amendment (ticket 24, 2026-09-24)

ADR 0005 no longer prunes positions with nothing named below them, so a branch ends where the popularity floor ends it. The stub rule above is unchanged, but a stub is now only a main move whose child the build did not keep (a dropped cycle, the ply cap); none occur on the packaged snapshot.
