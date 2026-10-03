# Play loop: what does one fast round look and feel like?

Type: prototype
Status: resolved
Blocked by: 05, 06, 09
Map: [Chess opening trainer by sampling](../map.md)

## Question

Build a throwaway prototype of a single round: the board, the learner's move, the sampled opponent reply, what is shown on a wrong move (book move flash? full line?), and the instant jump to the next round. Use it to settle the 'go fast' feel and what minimal feedback the learner needs mid-drill. Link the prototype from this ticket; the answer records the UX decisions, which feed the spec.

HITL: the learner reacts to the prototype.

Inherited from ticket 05 — the loop to prototype:

- A round opens with the app choosing the learner's side, then the learner must produce a main move at each of their turns, with the acceptable set **hidden**.
- The opponent samples among its own most popular replies, weighted by popularity x recall factor.
- After each learner move the app **reveals** the main moves for the position just left. A move outside the accepted set ends the round: reveal, then hard-restart, with no play-out.
- With probability epsilon the app discards the learner's best-known move (only when `width_player >= 2`) and tells them so.
- Settled sizes at `(3,3)` and a 0.2 % cut-off: 86 iterations / 235 positions in the 1800+ bucket.

Inherited from ticket 06 — the opponent and the feedback to prototype (ADR 0001):

- The opponent draws each reply by popularity × mean need of the learner positions below it, plus an exploration bonus; with no history it is the database opponent restricted to the repertoire. The prototype can stub need but should sample by that shape so the feel is right.
- A miss reveals the main moves at that position and restarts; the position comes back soon (its clock is untouched by the miss) and the next pass on it is an uncounted relearning pass. Whether the learner should be told "relearning" mid-drill is a UX question for this ticket.
- The learner's colour is drawn per round (weighted toward the colour with more need, floor 0.2); the round must make the side obvious instantly.
- Every round is logged (side, path, end, outcome, per-position state before the round); the prototype need not persist it but should not fight it.


Inherited from ticket 09 — the stack to prototype on (ADR 0004):

- **chessground** with Lichess defaults, driven by a server-supplied legal-destinations map; the learner may play any legal move and the server judges it. No chess logic in the browser.
- **One WebSocket per tab**, four messages: `move` and `next` up; `round`, `moved` (verdict, revealed main moves, opponent reply, new FEN and dests) and `round_over` (outcome, reveal, path) down. The client sends `next` when it wants the next round, so **this ticket decides the reveal delay** (zero is allowed) and what a miss looks like on the board.
- Animation capped at 100 ms; no loading indicator anywhere in the loop; drop to reply visible under 100 ms.
- The prototype may stub the server (a fake sampler behind the same four messages) or run FastAPI for real; either is fine as long as the message shapes are the ADR's.

## Comments

**2026-09-12, agent — prototype ready, waiting for the learner's reaction.**

Prototype: [`prototype/play-loop/`](../../../prototype/play-loop/README.md). Run `uv run python server.py` in that directory and open <http://localhost:8010/prototype/play?variant=A>; the pink pill at the bottom (or ← →) flips between the three variants. Screenshots of every state are in `prototype/play-loop/shots/`.

It runs the real wire of ADR 0004 (chessground, the four messages, the client asks for `next`) against a real 1800+ tree cut from the 2013-01 dump at 0.2 % / top-3, and the real sampler of ADR 0001 (half-life records, popularity x mean-need opponent with Gumbel exploration, forced exploration at 0.1, side drawn by need). `drive.py` plays scripted rounds through the socket: pass, miss, leaf on the learner's move, leaf on the opponent's reply, forced exploration, relearning and the side draw all behave, and the server handles a move in 0.13 ms mean / 0.43 ms max, far inside the 10 ms budget.

The three variants disagree on exactly the questions this ticket owns:

| question | A Bare board | B Ledger | C Pure recall |
| --- | --- | --- | --- |
| reveal after each learner move | green arrows on the board, instantly | SAN chips in a side ledger | none until the round ends |
| what a miss looks like | red border, red arrow for the move, green arrows for the main moves | red ledger row, move struck through, chips | overlay on the board with big text, arrows underneath |
| reveal delay / restart | auto after 900 ms (miss), 250 ms (success) | never auto; Space / Enter / click | miss waits for any key; success flashes 400 ms then goes |
| relearning shown | no | as a pass-kind label | no |
| forced exploration | 2 s toast "not e4 this time" | chip with ✕ on the discarded move | not shown |
| side made obvious | badge top-left + orientation | "you are white" badge + orientation | big banner ♔ WHITE / ♚ BLACK + orientation |

What the learner's reaction has to settle (the answer of this ticket):

1. Reveal mid-round at all (A, B), or only on a miss (C)?
2. If mid-round: on the board (A) or as text beside it (B)? Note from building A: arrows for the position *just left* are drawn on the board *after* the reply has landed, so an arrow can point through a piece that has since moved (see `shots/A_demo_pass.png`, the e7-e5 arrow under the e6 pawn). If arrows win, they probably need to be drawn at the drop and cleared when the reply lands.
3. After a miss: auto-restart on a timer (A), or wait for a key (B, C)? And after a success: any pause at all?
4. Does the learner want to know a pass was `sure`, `counted` or `relearning` (B), or is that noise?
5. Is the forced-exploration notice needed mid-drill, and where?
6. Animation: 100 ms or 0 (`&anim=0`)?
7. Anything from one variant wanted in another ("the banner from C on A").

Two things noticed while building, for the spec rather than for this decision: the 2013-01 dump is small (5,017 games at 1800+ without bullet), so the top-3 replies include oddities like 2.b4 against the Sicilian; a current month will not have this. And a `moved` message that ends the round carries an empty `dests` map, which is a cleaner "round over" signal for the client than a separate flag; the spec's schema should say so.

The ticket stays **claimed**, not resolved: a prototype ticket resolves through the learner's reaction, which the agent cannot supply.

**2026-09-12, learner's reaction.** "Reveal only on a miss, next round on space, I don't like green arrows while playing. I like seeing the solutions with arrows when the game is over." Reported a bug in C: as Black after 1.e4 they played e5, a main move, and the round ended. The log confirms it: e5 had a counted pass, so forced exploration set it aside and C showed nothing, then charged a miss for it. The learner also asked why the Sicilian is only 4 plies long (see the answer).

## Answer

Variant **C, Pure recall** wins, amended by the reaction. The prototype now runs the winning shape by default (`prototype/play-loop/`, variants A and B kept as the primary source).

- **No reveal while playing.** After a learner move the opponent's reply simply appears; no arrows, no chips, no verdict. The only text on screen mid-round is the banner: the learner's colour (badge plus board orientation) and the opening name of the current position.
- **The solution is shown when the round is over, on the board.** Main moves of the position where the round ended are drawn as green arrows; the move the learner played is drawn red (yellow when it was the set-aside move). A verdict strip under the board says what happened in one line (`✗ e5 · main: c5 · e6`, or `✓ 9 plies · Sicilian Defense: Najdorf`). Nothing covers the board.
- **Next round on Space** (Enter or a click on the strip also work), after every outcome. No timer restart. *Assumption*: the learner said "next round on space" without qualifying it, so success also waits; if a success should run straight on, that is one line in the spec.
- **Forced exploration must be announced** at the turn it applies: the set-aside move is drawn as a **yellow arrow on the board before the learner moves** (learner's request, 2026-09-12) and named in the banner ("not e5 this time"). This is the one thing drawn on the board mid-round. Its silent form is indistinguishable from a bug. Two rule changes follow from the report, recorded in ADR 0001 and `CONTEXT.md`:
  - it fires only when one main move is *strictly* better known than the others (a tie, in particular a position never seen, forces nothing);
  - playing the set-aside move ends the round but is **neither a pass nor a miss**: the learner produced a main move they know, so the record is untouched. The round's remaining plies are the whole cost.
- **Not shown mid-drill**: whether a pass was counted, sure or relearning, and the recall numbers. They belong to the progress view.
- **Animation** stays at chessground's 100 ms default (unchallenged), settable to zero per ADR 0004.
- **Wire consequences for the spec**: `moved` carries a third verdict `forced` and `round_over` a third outcome `forced`, both with the reveal and the played move; a `moved` that ends the round carries an empty `dests` map. The `round` and `moved` messages carry `forced: <san> | null` and `forced_uci` for the position now to move at, so the client can draw it.

**Why the Sicilian is only 4 plies long** (learner's question). The round ends where no continuation survives the repertoire cut-off, and the cut-off from the repertoire decision is *absolute*: a line stays only if at least 0.2 % of all games in the band follow it exactly. The Sicilian is the most-played reply to 1.e4 but splits into many variations, so each branch falls under 0.2 % within a few moves: 1.e4 c5 2.Nc3 d6 and 1.e4 c5 2.Nf3 e6 end at ply 4, the Najdorf at ply 10 (0.76 % of games) with no single continuation above 0.2 %. The prototype's sample makes it worse (January 2013, 5,017 games at 1800+ without bullet, so the threshold is 10 games and 2.b4 shows up as a main reply), but a whole current month keeps the same shape: the relative shares are the same, only the noise goes. Deeper Sicilian lines would need a cut-off relative to the games reaching the position rather than to all games, which is a change to the repertoire decision, not to this ticket; not ticketed unless the learner wants that decision reopened.

Assets: `prototype/play-loop/README.md` (run instructions, variant table), `prototype/play-loop/shots/` (every state of every variant), `prototype/play-loop/drive.py` (scripted rounds through the socket).
