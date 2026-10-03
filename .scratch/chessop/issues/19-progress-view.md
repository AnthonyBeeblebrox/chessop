# Progress view: what does the learner see about their repertoire, and how is a position shown?

Type: prototype
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

The v1 spec needs a progress view: three decisions already put content on it (ticket 07: per-opening and per-position reset of history; ticket 15: the position's explanation with its lead, "more" toggle and attribution footer; ticket 16: the Score split by colour and per opening, opted-out openings included). Nothing says what the page is. Decide, by prototyping and reacting:

- **Shape**: how the repertoire is laid out (a graph of positions, a list of openings that drills down, a board heatmap, some mix), given that ADR 0006 gives every position a canonical move order to show it by and a position reached by several orders appears once.
- **Numbers per position**: which of ticket 06's numbers are shown (recall estimate, half-life, counted passes and misses, "known" at ~3 counted passes per ticket 01, never-passed) and which stay in the store.
- **Aggregates**: the Score per colour and per opening (ticket 16), the realised in-session success rate against the 80-90 % target (ticket 06), and the never-passed positions as ticket 05's neglect answer (exploration is the learner's choice, so untouched branches accumulate no history).
- **Score history graph**: ticket 16 left it optional; it needs a daily snapshot of the score that no store holds (ADR 0002 would gain a table). In or out of v1.
- **Actions**: per-opening and per-position reset (ticket 07), opening opt-out (ADR 0005), and whether a position can be launched as a round from here.
- **Route**: where the view lives relative to the play page (ADR 0004 has Jinja2 pages, one JS module on the play page only) and whether it is one page or several.

Resolve as ADR 0007 if the shape is hard to reverse, otherwise as an amendment to ADR 0004 (pages) and ADR 0002 (any new table). HITL: prototype in `prototype/progress-view/` on `main`, marked throwaway, per the map's Notes; grill the learner on the result; do not answer for them.

## Answer

Prototyped and grilled with the learner on 2026-09-22 (three variants, two rounds of questions, every recommendation taken except the shape, where the learner chose the ledger). Prototype in `prototype/progress-view/` (throwaway, README and `shots/` inside): variant **A Ledger** won over B Explorer (board-first walk of the graph) and C Wall (heatmap of every position).

- **Shape: a ledger.** One page, a **table of openings** in order of the share of games at the band that reach them (the score's own weighting, no sort control): name, ECO range, positions, a known / learning / never-passed bar, the opening's Score and its White and Black scores, an in/out toggle and a reset. A row unfolds into a **second level, one row per exactly-named line** in that family (Najdorf, Dragon, ...) in the same format with its own score; a named line unfolds into its **branches**, each a move string in canonical order with every learner move coloured by that position's recall estimate. Positions above any family (the start position, 1.e4, 1.d4) sit in a "First moves" row at the top. A position reached by several orders appears once, under its canonical order (ADR 0006). Clicking a learner move opens the position.
- **Position page.** A board (the learner's colour at the bottom), the name (marked inherited when the book does not name the position exactly), ECO and canonical line, the numbers, the main moves as chips coloured by the child's recall, the Explanation (lead, "more", the borrowed-text label when the position has no page, the CC BY-SA footer with the page link, ticket 15), and the actions.
- **Numbers per position**: the recall estimate, the half-life, counted passes and misses (with "relearning pass owed" when set), the time since the last pass, the share of games reaching the position and the number of move orders. Plus one **state word** derived from the recall estimate: **known** at or above the sure threshold (0.9, ADR 0001), learning from 0.5, fading below, relearning while a relearning pass is owed, never passed with no pass at all. Ticket 01's "three counted passes" is not the definition of known: the model's own threshold is, so the word and the colour agree. Pass counts are shown but decide nothing.
- **Aggregates** on the page head: the Score with its change since the last day played, the White and Black scores, the known / learning / never counts, the **in-session success rate** as `successes/rounds` against the 80–90 % target (coloured when outside it; rounds since this server process started, which is what "session" means with no login), and a **sparkline of the daily score**. The never-passed count is a link to the list of never-passed positions sorted by popularity: exploration is the learner's choice (ticket 05), and this is where they make it.
- **Score history: in v1.** ADR 0002 gains a **daily score table**, one row per local day (date, score, white score, black score, rounds, successes), upserted at every round-end commit. The sparkline shows the score only; the colour scores and the rate are recorded so a fuller chart needs no migration later.
- **Actions**: reset one position and reset one opening (each behind a confirmation; they delete the position records, which ADR 0002 had reserved to "reset all history"), and opt an opening out or in. Opt-in/out **lives on the progress view**, not in settings; settings keeps the band, the widths and the model knobs, and the one "reset all history". **"Drill from here" is out of v1**: a Round starts from the start position (glossary), and the sampler already steers toward weak positions.
- **Route and JS: server-rendered, no JS.** Two Jinja2 pages, `/progress` (the ledger, the unfolding as `<details>`) and `/progress/position/<epd>` (the position page, its board an SVG from python-chess's `chess.svg`, browser back returns). ADR 0004's one JS module on the play page stands; the never-passed list is `/progress?never=1` or equivalent, the spec's call. Nothing here is latency-sensitive.
- **Recorded as amendments**, not an ADR 0007: the page's shape is easy to change; only the daily score table is a schema commitment.
- **Rejected**: the heatmap wall (reads at a glance but says nothing about *which* move, and its cells are unlabeled), the board-first explorer (one position at a time, no overview; its weakest / never-passed lists survive as the never-passed link), the fuller history chart, a client-side modal for the position, a sort control, a pass-count definition of known.
- **Scale caveat**: the prototype ran on 272 positions (2013-01, 1800+, 0.2 % top-3 pooled by EPD); the real graph is ~1,100 positions and ~2,000 branches (ticket 17), which is why the second level exists.

Assets: `prototype/progress-view/` (server, three variants, README with the verdict, `shots/A.png` `B.png` `C.png` `C_wall.png`). Amendments: `docs/adr/0004-web-stack.md` (pages), `docs/adr/0002-persistence.md` (daily score table, finer resets). Glossary: `CONTEXT.md` gains Progress view and Known.
