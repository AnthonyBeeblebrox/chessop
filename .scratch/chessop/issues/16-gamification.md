# Gamification: what rewards the learner, and what single score says how well they know their openings?

Type: grilling
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

Closing ticket 13 the learner asked to investigate gamification: *"rewarding sounds, player's absolute score as a measure of its opening knowledge as a % displayed, ..."*. The play loop is "go fast" (ticket 10: nothing sits between the learner and the next round) and the memory model already yields per-position recall estimates and a realised success rate (ADR 0001). Decide:

- **The score.** One number, shown as a percentage, that means "how much of my repertoire I know". Candidates: the popularity-weighted mean recall estimate over the repertoire's learner positions (what the opponent already computes at the root, per colour); the share of positions with a recall estimate above the sure threshold; the share of lines the learner can play end to end. Which one, is it per colour or combined, does it cover the whole repertoire or only the scoped openings, and how does it move (a pass on a never-seen position vs a pass on a known one)?
- **Where it shows.** On the play page permanently (the banner?), only at round end (the verdict strip), or only in the progress view. It must not slow the loop.
- **Sounds.** Which events get one (pass, miss, round success, forced exploration, a score milestone), whether they are on by default, and where the assets come from (licence). ADR 0004 vendors chessground; Lichess's own sounds are a candidate but their licence must be checked.
- **Anything else** in the learner's "...": streaks, daily goals, milestones per opening, a history graph. Decide what is in v1 and what is out.

Resolve the glossary consequences in `CONTEXT.md` (a **Score** term if one is adopted) and hand the display decisions to the progress-view fog or a prototype ticket if "how should it look" turns out to be the real question.

HITL: grill the learner; do not answer for them.

## Answer

Grilled with the learner on 2026-09-15 (two rounds, every recommendation taken). Sound licences were checked first: lila's `COPYING.md` lists its default `standard` sound set (and `robot`, `woodland`, `instrument`, `other`) under "Exceptions (non-free)" with no licence, `lisp` as CC BY-NC-SA 4.0, and four sets by Enigmahack (`sfx`, `nes`, `piano`, `futuristic`) as AGPLv3+, which a GPL-3.0-or-later app may ship with the notice and credit kept.

- **The score** is the popularity-weighted mean recall estimate over the learner positions of the scoped repertoire: `Score = sum(count(p) * R(p)) / sum(count(p))` over every position `p` where the learner is to move, `count` the pooled game count from the snapshot, `R` ADR 0001's recall estimate (0 for a never-passed position, the raw estimate, not one minus the floored need). Because each game contributes one unit per learner turn it passes through, the score is the model's probability that, at a learner turn drawn at random from the band's games within the repertoire, the learner produces a main move. It is a per-turn probability: not the chance of getting through a whole round (the product along a branch, rejected), and not the success rate seen while drilling, which sits below it because the opponent steers toward weak positions. Calibrated only as well as the half-life parameters, priors until refitted from the round log.
- **It falls while the learner is away.** A live estimate, decaying with the same clocks the opponent uses; a score that ignored forgetting would contradict the drilling the learner watches. No high-water mark, no coverage variant.
- **One combined number** over both colours' learner positions; the White / Black split is shown only in the progress view.
- **Over the scoped repertoire**, so opting an opening out is not a penalty. The progress view shows the same computation per opening, opted-out ones included.
- **Where it shows.** In the banner permanently, one decimal, recomputed at every round-end commit (it is the memoised root aggregate ADR 0001 already maintains); the per-round change on the verdict strip (`✓ 9 plies · Najdorf · 71.2 % (+0.4)`), no delta after a `forced` outcome since the record is untouched. When a tab opens, the banner shows the change since the last round played once (`81.3 % (−6.1 since Tue)`) until the first round of the session ends, so the overnight drop comes with its explanation. Nothing slows the loop; nothing mid-round changes.
- **Sounds**, from Lichess's `sfx` set (AGPLv3+, Enigmahack), vendored like chessground: Move on every move (Capture on a capture, Check when it gives check, as Lichess does), Victory on round success, Error on a miss (not Defeat: a miss is the event the app exists to produce), nothing extra for the forced outcome, no per-position sound mid-round (ticket 10's "no reveal while playing" applies to the ears). On by default; one toggle in settings and `m` on the play page, both remembered. Attribution in the README's Licences section, the AGPL notice and credit in `LICENSES/`, the way ticket 15 set up for the Wikibooks text.
- **Rejected**: the unweighted mean (a book-coverage figure, near 0 % on a 1,100-position graph for months), the share of sure positions (steps, and a night's decay tips many positions over the 0.9 line at once), the share of branches playable end to end (punishes one weak position across every branch through it), a second number on the play page, the non-free `standard` set, synthesised tones.
- **Out of v1**: streaks and daily goals (they schedule by calendar where the app's premise is that the model schedules), per-opening milestones, session summary. The **score history graph** is not ruled out: it needs a daily snapshot of the score, which the round log does not hold, and it is the evaluation fog's best view of "is this working"; left in the progress-view fog.
- **Glossary**: `Score` added to `CONTEXT.md`; the "avoid: score" notes on Position record and Sampling weight stay, so a position's number or a move's weight is never called a score. Definition recorded as an amendment to ADR 0001, since it is derived from that model and a later change to it would change what every displayed number meant.

Assets: `CONTEXT.md` (Score), `docs/adr/0001-sampling-rule.md` (amendment, ticket 16). Facts: lila `COPYING.md` at master, read 2026-09-15.
