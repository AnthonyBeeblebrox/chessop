# Repertoire rule: every named variation in the book, or only lines that survive a popularity cut-off?

Type: grilling
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

The repertoire decision (ticket 05) cut the repertoire by an **absolute** popularity cut-off: a line stays only if ≥ 0.2 % of all games in the rating band follow it exactly, capped at the top-3 replies per position. Reacting to the play-loop prototype the learner asked why the Sicilian is only four plies long and said: *"I want all named variations in the book."* That is a different repertoire rule. Decide:

- What is "the book": the chess-openings TSV (3,810 named lines, CC0, already the naming source in ADR 0003), or something else?
- **All** named lines, including the ones nobody at the learner's band plays (in the 2013-01 month at 1800+, 2,922 of the 3,810 named lines were reached by no game at all, and 266 of the 391 named Sicilian lines), or named lines with some traffic? If traffic, how much: any game, or a cut-off **relative to the games reaching the position** (which is what makes deep Sicilian lines survive) rather than to all games?
- Do the unnamed moves *between* named positions stay in the repertoire (a named line at ply 12 passes through unnamed positions at plies 5-11 whose replies the opponent must also sample)?
- Does the top-3 width cap survive, and what does it mean at a position whose named continuations number more than three?
- Popularity still drives the opponent's sampling weight and the side of the tree the learner sees most (ADR 0001). A named line with zero games has no popularity: does the opponent ever choose it, and with what weight?
- Size: the current rule gives 235 positions / 86 lines at 1800+; the TSV holds 3,810 named positions, 888 of them with any traffic in the month. What repertoire size does the learner actually want to drill, and does the scoping by ECO family (ticket 05) become the lever that keeps it finite?

Resolve the consequences in `CONTEXT.md` (**Repertoire**, **Main move**, **Branch**), in ADR 0003 (the snapshot is stored at a 0.02 % cut-off, which no-traffic named lines never reach), and note whether ADR 0001's popularity-weighted sampling needs a floor for zero-count moves.

HITL: grill the learner; do not answer for them.

Facts from the prototype tree and the openings list (1800+ band, 2013-01 month, bullet excluded, 5,017 games, so the 0.2 % threshold is 10 games):

- Sicilian named lines: 391, of which 355 are deeper than 4 plies and 205 deeper than 10; ply distribution peaks at plies 10-14 (Najdorf, Dragon, Scheveningen, Sveshnikov families). The prototype's Sicilian subtree ends at plies 4-12 (15 leaf paths).
- Reached by ≥ 10 games: 253 of the 3,810 named lines overall, 36 of the 391 Sicilian ones. Reached by ≥ 1 game: 888 overall, 125 Sicilian.
- Examples of named Sicilian lines with zero games in the month: Amazon Attack, Big Clamp Formation, Brick Variation, Gloria Variation.
- A current whole month (ADR 0003) has roughly a thousand times more games, so the *relative* picture holds but the "zero games" set shrinks; how much is measurable with `refs/lichess/tree-width-analysis.py` on a recent dump. A research ticket may be worth it once the learner has said what "all" means.

## Comments

**2026-09-12, round 1 settled** (interim record; the answer is written on resolution, below):

- **The book** is the Lichess `chess-openings` list (3,810 named lines, CC0, already baked into the snapshot).
- **Rule**: book-terminated, popularity-widened. A line runs exactly as deep as the book names it; at each position only the top-`k` most popular replies are kept, as before.
- **Named lines nobody at the band plays are out**, under a floor expressed as a share of the band's games (value from the measurements).
- **Widths stay (3,3)**; a named line that needs a move outside the top 3 is dropped.
- **Target scope: the whole book** (sharpened in round 2).
- **A line ends at its last named position**, never continuing by popularity beyond it.

**2026-09-12, round 2 settled**:

- "The whole book" is a **scope default**, not an override: every family is in unless the learner opts it out; family scoping stays as the lever.
- A popular move with nothing named below it is a **stub**: accepted for the learner, ends the round as a success, never played by the opponent (ADR 0001 amended).
- The **floor is bounded below by the snapshot's 0.02 % storage cut-off** (ADR 0003 amended); the value is chosen from `docs/research/repertoire-rule-candidates.md`.
- Rare named lines get **no minimum rate of appearance**; ADR 0001's exploration bonus and the need of never-passed positions are relied on.
- **No "variation" term**: Book entries name positions, Opening stays the scoping family.

**Raised by the learner while closing, out of this ticket**: gamification (rewarding sounds, an absolute knowledge score shown as a percentage). Ticketed separately.

**2026-09-12, round 3 settled** (after the learner refused to decide on 2013 data and the measurement was rerun on the first day of August 2026, 150,000 games at 1800–2100, `docs/research/repertoire-rule-candidates-recent.md`): width = **top-3 plus every reply holding ≥ 5 % of the games reaching its position**; floor = **0.02 %** of the band's games, the snapshot's storage cut-off.

## Answer

**The book sets depth, popularity sets width.** ADR 0005, `docs/adr/0005-repertoire-rule.md`.

- **The book** is the Lichess `chess-openings` list (3,810 named lines, CC0, already in the snapshot). New glossary term **Book**; "variation" gets no term (a book entry names a position, **Opening** stays the scoping family).
- **Rule**: at load, keep at every node the **main moves** (the top-3 replies plus any reply with ≥ 5 % of the games reaching the position) whose count clears the **floor** (default 0.02 % of the band's games, a setting bounded below by the snapshot's storage cut-off), then prune every node with no exactly-named book position at or below it. A **Branch** ends at the deepest name on its path.
- **Scope default is the whole book**: every family in unless opted out; ticket 05's family scoping stays as the lever.
- **Stubs**: a main move with nothing named below it stays accepted for the learner and ends the round as a success; the opponent never draws it (ADR 0001 amended).
- **No-traffic named lines are out** (2,631 of 3,810 had no game at 1800+ in the 2013 month; 1,054 on the recent day); no minimum rate of appearance for rare lines, ADR 0001's exploration bonus is relied on.
- **Snapshot** (ADR 0003 amended): floor bounded below by the 0.02 % storage cut-off, per-node name flagged exact-or-inherited, ply cap raised from 30 to 36 (the deepest book line).
- **Size** on the recent sample at 1800–2100: 389 lines / 996 positions / 17 plies deep, covering 535 of the 996 book lines real traffic reaches (old rule: 69 / 173 / 10 plies). After `1.e4 c5` the main moves are Nf3, Nc3, d4, c3 (Alapin), Bc4, f4; the widest position holds 7.
- **Rejected**: the book as the repertoire regardless of traffic; a relative cut-off with no book; uncapped widths (650 lines, 18 replies at a position); top-4 or top-5 (rank, not share); 8–10 % shares (miss the Alapin at 7.9 %); floor 0.01 % (doubles the snapshot for 80 tail lines).

**Handed on**: ticket 11 (unblocked now) inherits the transposition finding: 195 of the 996 reachable book lines are missed only because their traffic arrives by move orders other than the book's own (Semi-Slav main line: 215 games pooled, 10 by the book's order). Ticket 16 (new) holds the learner's gamification request. Ticket 05's answer is superseded on the cut-off only.

**Evidence**: `docs/research/repertoire-rule-candidates.md` (2013-01, `refs/lichess/repertoire-rule-analysis.py`) and `docs/research/repertoire-rule-candidates-recent.md` (2026-08 prefix, streamed, `refs/lichess/repertoire-rule-analysis-recent.py`).
