# "?" explanations for Score and progress

Type: prototype
Status: resolved
Blocked by: 
Map: [chessop in public](../map.md)

## Question

A new visitor meets Score, Known, the White/Black halves, never-passed counts, the sparkline and the play loop's pass/miss with no one to explain them. What do the "?" explanations say and where do they sit: popovers beside each figure, a help page, or both linked; how they work on touch; and whether a first-visit walkthrough (including asking the learner's rating) is wanted. Decided by a rough prototype.

## Answer

Decided against the prototype (branch `prototype/help`, commit `08cefd5`: three variants on the real play and progress pages, A Popovers / B Help page / C Walkthrough, all using the same wording). The owner picked **B, the help page**.

- **One help page at `/help`**, titled "How chessop works", with one section per figure and a list of sections at the top. The sections are: How a round works, The verdict under the board, "Not X this time" (forced exploration), Score, Change since your last day, As White and as Black, Known/learning/never passed, This session (with the 80–90 % target), The line (sparkline), Openings (the table, out and reset), Move colours, Rating band. Each section has an anchor (`/help#score`, …).
- **The figures link to it.** On progress, each figure's label is a dotted-underline link to its section: Score, the change since, as White/as Black, known/learning/never passed, this session, the sparkline ("daily"), the Opening column header and the colour legend. On play, the corner links gain **help**, and after a round a small line under the verdict reads "what does this mean? · what is the Score?", linking to `#verdict` and `#score`. On touch these are ordinary links, so no special touch handling is needed.
- **No popovers and no first-visit walkthrough.** The first visit asks nothing: the band is the default 1500+ and is changed in settings.
- **Wording**: the prototype's text (`src/chessop/templates/proto_help_copy.html` on the branch) is the starting draft. The section on known/learning/never passed quotes the sure threshold, and the session section quotes the target range, from the running values.
- The page belongs to both modes: it is plain help, not a hosted-only feature.
