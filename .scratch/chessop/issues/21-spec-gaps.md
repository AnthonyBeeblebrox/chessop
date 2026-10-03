# Spec gaps: the two contradictions and three undecided details ticket 20 found while writing the spec

Type: grilling
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

Writing [`spec.md`](../spec.md) (ticket 20) exposed two places where sources disagree and three details no ticket decided. The spec lists them in its §15 and §16 and is blocked only on them; everything else is final. Resolve each, then edit the spec in place (and amend the ADR named where one is touched):

- **C1. Does a mid-round `moved` carry the reveal?** ADR 0004 has `moved` carry the revealed main moves after each learner move; ticket 10 shows nothing mid-round and did not say whether the field stays (its prototype kept sending it, the client ignored it). Drop it from mid-round `moved` or keep ADR 0004's wire as written.
- **C2. Which position is revealed on a success?** Ticket 10 draws the main moves of the position the last move was played from; ticket 15 says "the leaf on a success", which has no non-stub main moves to draw. Say which position the arrows and the explanation belong to, and whether they may differ.
- **G1. Empty subtrees in the need aggregation.** Below a stub, below a learner move whose child is a leaf, and below an opponent move onto a learner-to-move leaf with no accepted move there are no learner positions, so ADR 0001's mean need is undefined there; forced exploration compares these means and the opponent weights by them. Also whether a learner-to-move position with no accepted move is a learner position at all (for the Score, the side draw, the never-passed list). The prototype returned the need floor for an empty set and excluded moveless positions.
- **G2. Forced outcomes in the counts.** ADR 0001's success target is "net of forced exploration"; a forced round now ends as neither pass nor miss. Whether it counts in `daily_score.rounds` and in the in-session `successes / rounds`.
- **G3. Persisting the `m` toggle.** Ticket 16 remembers the sound state toggled on the play page; ADR 0004 fixed four socket messages and forms for settings. A fifth message or an HTTP POST from the JS module.

HITL: grill the learner; recommendations may be offered, none of these is worth a prototype. Small decisions, one session.

## Answer

Grilled with the learner on 2026-09-24; every recommendation accepted. Folded into [`spec.md`](../spec.md) §4, §5.2, §7, §8, §9, §10.1, §11, §13 (§15 and §16 now record the decisions), ADR 0001 and ADR 0004 (ticket 21 amendments) and the glossary (Explanation, Position record).

- **C1.** A mid-round `moved` carries no reveal; the main moves leave the server only in `round_over`. The page must hide them, so the server does not send them.
- **C2.** The two may differ. The arrows show the position the round's last move was played from: the learner's position on a miss, a forced round, or a success on their own move; on a success on the opponent's reply, the opponent's position before that reply (its other replies), as ticket 10's prototype did. The explanation is for the position where the round ended, the leaf on a success, the most specific text, which is what ticket 15 meant by "the leaf".
- **G1.** An empty set of learner positions below an edge (a stub, an edge onto a leaf) has mean need equal to the floor: nothing left to learn, so forced exploration sets such a move aside first when it is strictly lowest, and the opponent weights an edge onto a leaf by popularity times the floor. A leaf with the learner to move is not a learner position: the round ends on reaching it, so it would be a never-passed zero forever; it holds no record and is out of the Score, the side draw, the aggregates and the never-passed list. Both as the prototype.
- **G2.** Forced rounds are excluded from both `daily_score.rounds`/`successes` and the in-session `successes / rounds`, the literal reading of ADR 0001's "net of forced exploration"; the round log still records them.
- **G3.** A fifth socket message, client to server, `{"type": "sound", "on": bool}`, no reply; the server writes the `sound` setting. The socket is already open on the play page; the settings page keeps its form.

With this the spec has no open decision: the map's destination is reached.

