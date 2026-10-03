# Success rule: what does 'successfully played the branch' mean, and how does success shape sampling?

Type: grilling
Status: resolved
Blocked by: 01, 04
Map: [Chess opening trainer by sampling](../map.md)

## Question

Define a Success: playing every book move down to the branch's leaf? Any book move (several acceptable lines)? One failure anywhere = branch failed? Then choose the sampling rule informed by the research: how the success count (and time since last visit) maps to the opponent's probability of steering into that branch, what the floor is so nothing is ever forgotten, and whether failures raise the weight symmetrically. Record the chosen rule as an ADR.

HITL: grill the user with the literature and algorithm findings in hand.

Inherited from ticket 05 — settled, do not re-litigate:

- Success is scored on the learner's moves only, first try, per branch: a round succeeds when the learner produced a main move at every one of their turns. A wrong opponent move never counts against them.
- "Any main move" counts (recognition), not "the one move the repertoire names" (recall) — that was considered and rejected as the default, with `width_player=1` kept as a strict mode.
- The acceptable set is hidden while the learner moves and revealed after the move, so a position met moments ago is cued rather than recalled. The model must not treat a fresh reveal as durable recall.
- Epsilon (discard the learner's best-known move; only meaningful when `width_player >= 2`) sets a floor on the failure rate, so the literature's ~80-90 % in-session success target must be read net of it.
- Only `max(width_player, width_opponent)` sizes the tree; defaults `(3,3)`, strict mode `(1,3)`.
- This ticket owns the sampling-rule ADR the destination calls for.

## Comments

Grilled over two rounds (round 1: attribution, memory model, aggregation, sides, cold start, logging, naming; round 2: miss effect, when a pass counts, parameter block, glossary). The user reframed the model as MCTS-style per-node statistics with backup, which replaced the per-branch record ticket 05 had sketched.

## Answer

Recorded as **ADR 0001**, `docs/adr/0001-sampling-rule.md`; glossary rewritten in `CONTEXT.md` (Memory section).

### Success and its evidence

- **Success** stays the round-level term (main move at every learner turn, first try). Evidence is kept **per position and per learner colour**, not per branch: a round is a playout, every position the learner got right takes a **pass**, the one position where they went off book takes a **miss**. A miss is charged to that position alone; the positions passed on the way keep their passes (not MCTS-style full backup of the loss).
- Under forced exploration, the discarded move's positions are not charged.
- **A pass counts only as new evidence**: if the recall estimate was already >= 0.9 at that moment, only the clock refreshes (this is what stops the starting position doubling its half-life on every White round). **The first pass after a miss is a relearning pass**: clears the mark, refreshes the clock, not counted (this is what stops the post-reveal retry counting as recall). **A miss always counts.**

### Memory model

- **Half-life** (Leitner / Duolingo HLR shape): `h = clip(h0 * 2^(passes - misses))`, recall estimate `R = 2^(-delta/h)` with delta since the **last pass** (a miss never touches the clock, so a failed position keeps a high need and returns soon), `R = 0` if never passed. **Need** `= max(floor, 1 - R)`.
- A miss **halves** the half-life (symmetric with a pass), no collapse, no reset. FSRS is the drop-in replacement if geometric decay proves too aggressive; ACT-R rejected.

### Opponent rule

- At an opponent position, each kept move gets `popularity^alpha x popularity-weighted mean need of the learner positions below it + exploration bonus`, bonus = Boltzmann-Gumbel noise scaled by `C / sqrt(1 + times faced)`; popularity renormalised over the moves kept in the repertoire at that position. Draw proportional to weight. With no history this is exactly the database opponent restricted to the repertoire. Sum and weakest-line aggregation rejected (weakest-line is the fallback).
- **Sides**: two position records per position; the learner's colour is drawn proportional to that colour's total need at the root, floored at 0.2.
- **Forced exploration** discards the learner's main move with the lowest mean need below it (reuses the opponent's number), probability 0.1.
- **No cap** on never-seen material in v1.
- **Round log** is a first-class store: side, path, end, outcome, and per visited learner position its counts, elapsed time and predicted R before the round. Exists so h0 and the doubling factor can be refitted.

### Parameter defaults (all tunable settings)

h0 = 1 day; half-life clipped to [15 min, 9 months]; sure threshold R >= 0.9; floor 0.1; exploration scale C = 1.0; popularity exponent alpha = 1; forced exploration 0.1; side floor 0.2; target in-session success 80-90 % net of forced exploration, **displayed and logged only** in v1.

### Glossary

Two epsilons disambiguated: **Forced exploration** (ticket 05's) and **Floor** (the need floor). New terms Pass, Miss, Position record, Recall estimate, Half-life, Relearning pass, Need, Floor, Sampling weight (rewritten); **Branch** kept as the path walked in a round, no longer the history unit.

### Handed to other tickets

- **Ticket 11** (transpositions): the tree node is now the history unit, so its question narrows to whether tree nodes reaching the same position share one position record, given ticket 12's finding that 14 of 17 transposition groups keep different replies per move order.
- **Ticket 10** (prototype): the opponent in the prototype samples by the rule above; the reveal-then-restart and relearning-pass mechanics are what it should make feel fast.
- **Fog** (progress view / evaluation): "known" threshold (~3 counted passes, ticket 01), realised vs target success rate, whether to cap new material or auto-tune toward the target.
