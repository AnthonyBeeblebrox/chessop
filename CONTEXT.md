# Chess opening trainer

A drill app that shows a learner as many opening games as possible, sampling the opponent's replies so branches the learner keeps getting right come up less often but never vanish.

_The repertoire vocabulary (Rating band, Repertoire, Opening, Branch, Main move, Round) was confirmed with the user in ticket 05, "Destination and repertoire"; Book was added and Repertoire, Branch and Main move reworded by ticket 13, "Repertoire rule", see ADR 0005. The memory vocabulary (Pass, Miss, Position record, Recall estimate, Half-life, Need, Floor, Forced exploration, Sampling weight, Relearning pass) was settled in ticket 06, "Success rule and sampling"; see ADR 0001. Round log and the global scope of history were settled in ticket 07, "Users and persistence"; see ADR 0002. Snapshot was settled in ticket 08, "Data source"; see ADR 0003. Forced exploration was amended by ticket 10, "Play loop"; see ADR 0001. Position was added and Branch, Position record and Snapshot reworded by ticket 11, "Transpositions"; see ADR 0006. Explanation was added by ticket 15, "Opening explanations in the drill"; see the ticket 15 amendment to ADR 0003. Score was added by ticket 16, "Gamification"; see the ticket 16 amendment to ADR 0001. Explanation and Position record were reworded by ticket 21, "Spec gaps". Popularity floor was added by ticket 18, "Pooled-only main moves"; see the ticket 18 amendments to ADR 0005 and 0006. Progress view and Known were added by ticket 19, "Progress view"; see the ticket 19 amendments to ADR 0002 and 0004. Rating band gained open and closed bands in "Open-ended rating bands" (chessop-public); see its amendment to ADR 0003. Learner was reworded and Account and Adopt added by "From one learner to many" (chessop-public); see its amendment to ADR 0002. Drill was added by "Letting people find chessop" (chessop-public). Throwaway learner was added by "Full site and throwaway learner" (chessop-public); see its spec §6._

## Language

**Learner**:
The person being drilled; plays one side of each round, and owns the history. Run locally, the app knows exactly one learner and never asks who they are; hosted, it knows many, each **anonymous** (known only to the browser that played) until they sign in to an account.
_Avoid_: user, player, student, profile, account (that is the sign-in identity)

**Account**:
A sign-in identity (Lichess or email) attached to one learner, so their history follows them to other browsers and devices. Hosted only, always optional; a learner has at most one.
_Avoid_: user, profile, login, learner (the learner is the person and their history; the account is how they prove it)

**Adopt**:
What signing in does to the anonymous learner's history on that browser: it joins the account's. If the account already has history, the two merge: a position on one side only carries over, a position on both keeps the record with the later last pass.
_Avoid_: import, sync, claim, link

**Throwaway learner**:
What a visitor is when their network has made too many new anonymous learners in the hour: a learner held in memory for one socket, with every default, never stored and given no cookie. They play, told that nothing is saved; signing in still gives them an account.
_Avoid_: guest, temporary account, rate-limited user

**Opponent**:
The app-controlled side, whose moves are sampled from the repertoire weighted by the learner's history.
_Avoid_: engine, computer, bot

**Round**:
One drilled game, from the start position until the branch ends or the learner leaves the repertoire. Which side the learner plays is chosen by the app at the start of each round.
_Avoid_: game, session, attempt, iteration

**Drill**:
What the learner does with a repertoire: play rounds over it, again and again, until its positions are known. The public pitch (page title, link preview, README lead) says **grind** for the same thing; nowhere else does.
_Avoid_: train, practise, study, grind (outside the pitch)

**Rating band**:
The range of player ratings whose games decide which lines count as main; a game counts only when both players are inside it. A **closed band** has a lower and an upper bound (1500–1800); an **open band** has a lower bound only (1500+), so it also holds every stronger player. The learner chooses the band; a repertoire is built for one band.
_Avoid_: level, Elo range, pool, floor band (Floor is a memory term)

**Repertoire**:
The lines in scope for drilling: every line that main moves reach from the start position at the learner's rating band, as deep as its moves stay popular enough at that band to weight. Everything is in by default; the learner may narrow it by opening. The app derives it from the book and measured popularity rather than the learner authoring it.
_Avoid_: book (that is the named list the repertoire is cut from), curriculum, opening set

**Opening**:
A named, ECO-labelled family of lines, such as the Sicilian Defence. The unit by which the learner scopes a repertoire.
_Avoid_: system, variation

**Book**:
The list of named opening lines the app knows: every line with an ECO code and a name in the Lichess `chess-openings` list. The book names positions and scopes openings; popularity decides which moves at each position are main and how deep a line is drilled.
_Avoid_: encyclopaedia, theory, openings list, TSV (that is the file it comes from)

**Snapshot**:
The opening graph the app ships with: every position reached often enough in one month of Lichess games, counted over every move order that reaches it, with the moves played from it, its popularity and its book name, kept separately for each rating band. Frozen at the month it was built from; the repertoire is cut from it, and a new snapshot only ever arrives with a new release.
_Avoid_: database, explorer, dump (that is the raw Lichess file it is built from), book (that is the named list), tree (positions are shared between move orders)

**Position**:
A board with a side to move, whatever move order reached it. The unit the repertoire, the book and the learner's history are keyed by: two move orders that reach the same board are one position, drilled and remembered once.
_Avoid_: node, FEN or EPD (those are how a position is written down), move sequence

**Branch**:
One path through the repertoire from the start position to a leaf, a position none of whose moves is popular enough to be main: what the learner walks in a round. Several branches may pass through the same position by different move orders. History is not kept on it; it is kept on the positions along it.
_Avoid_: variation, line, move order (a branch is one, a position may have several)

**Main move**:
A move among the few most popular continuations at its position, or one that a real share of the games reaching that position play, and so part of the repertoire. Where the learner is to move, the app accepts any main move and rejects the rest. A main move whose position the snapshot does not keep is still accepted, and ends the round; the opponent never plays one.
_Avoid_: acceptable move, book move, best move

**Explanation**:
The prose the app shows for a position, taken from the Wikibooks "Chess Opening Theory" book: why the moves are played and what each side wants. Shown when a round ends, for the position where the round ended (on a success, the end of the branch, which may lie below the position whose main moves are revealed), and in the progress view; never while the learner is still moving. A position without a text of its own borrows the nearest one on the path walked, and says so.
_Avoid_: theory, commentary, description, wiki text, annotation

**Progress view**:
The page where the learner looks at their repertoire between rounds: every opening with its Score, unfolding into its named lines and their branches, every learner position coloured by its recall estimate, and one page per position with its numbers and Explanation. Also where an opening is opted in or out and where a position's or an opening's history is reset.
_Avoid_: dashboard, stats page, tree view, repertoire editor

## Memory

**Success**:
A round in which the learner produced a main move at every one of their turns, first try. Being shown the moves afterwards does not count as recall.
_Avoid_: win, pass (a pass is per position)

**Pass**:
The learner produced a main move at a position, first try. Counted as evidence only when the model was not already sure of the position and no relearning pass is owed.
_Avoid_: hit, correct move

**Miss**:
The learner produced a move outside the main moves at a position. It ends the round and is charged to that position alone, never to the positions passed on the way.
_Avoid_: failure, error, mistake

**Position record**:
The history the app keeps for one position: counted passes, misses, the time of the last pass, and whether a relearning pass is owed. A position is the learner's only when they hold the side to move in it and it is not the end of a branch (a round ends there, so it is never drilled), so one record is one colour's history, and a pass or miss counts in full whatever move order reached the position. A record belongs to the position, not to any repertoire: it outlives every regeneration and is only ever removed by the learner resetting their history.
_Avoid_: branch stats, node stats, score

**Recall estimate**:
The model's predicted chance that the learner still knows a position. It falls with time since the last pass and rises with each counted pass; zero for a position never passed.
_Avoid_: retention, strength, knowledge

**Known**:
The state of a position whose recall estimate is at or above the model's sure threshold: the app is as confident as it gets that the learner will play a main move there. A word for the learner, derived from the estimate, never from a count of passes.
_Avoid_: mastered, learned, memorised, sure (that is the threshold, this is the state)

**Half-life**:
The time after which a position's recall estimate has fallen to one half. Doubled by a counted pass, halved by a miss, never below a minimum or above a maximum.
_Avoid_: interval, stability, ease

**Relearning pass**:
The first pass on a position after a miss. It restores the position and refreshes its clock but is not counted, because the main moves were just revealed.
_Avoid_: retry, replay

**Need**:
One minus the recall estimate, never below the floor. What the opponent steers toward.
_Avoid_: priority, weakness, due-ness

**Floor**:
The lowest need any position can have, so that no position ever stops being sampled.
_Avoid_: epsilon, minimum weight, popularity floor (that is the traffic cut-off, a different thing)

**Popularity floor**:
The share of the band's games a move must be played in, counted over every move order reaching its position, to be in the repertoire at all. What keeps lines too rare to weight out; a setting.
_Avoid_: floor (bare, that is the need floor), cut-off, threshold, minimum games

**Forced exploration**:
The app setting aside, for one turn, the learner's main move whose continuation they know best, so that the wider mode measures coverage rather than recognition of one move. Always announced to the learner at that turn (a yellow arrow on the board, and by name); only happens when one main move is strictly better known than the others; playing the set-aside move ends the round as neither a pass nor a miss.
_Avoid_: epsilon, randomisation, discard (the move is set aside for one turn, not removed)

**Sampling weight**:
A move's popularity times the sum of the average need of the learner positions below it and an exploration bonus that fades as the learner faces the move (ticket 23). What the opponent draws its move by.
_Avoid_: priority, score, probability

**Round log**:
The append-only account of every round played: the side, the path walked, where and how it ended, and each visited position's record and recall estimate as they stood before the round. Kept so the memory model can be refitted; never pruned while its learner exists.
_Avoid_: history (that is the position records), game log, session log

**Score**:
The one number the app shows for how well the learner knows their repertoire: the average recall estimate over every position where the learner is to move in the scoped repertoire, each position weighted by how often games at the band reach it. Read as the chance that, at a random turn of theirs in a real game, the learner plays a main move. Falls with time like the estimates it is built from; shown as a percentage in the banner and, per opening and per colour, in the progress view.
_Avoid_: knowledge, level, progress, rating; and never for a position's own number (that is its recall estimate) or a move's weight
