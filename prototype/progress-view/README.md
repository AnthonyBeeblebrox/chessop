# Progress-view prototype (ticket 19) — THROWAWAY

**Verdict (2026-09-22): A Ledger won**, amended by the grilling: a second level of exactly-named lines between an opening and its branches, the sparkline as the only history graph, server-rendered with the position as its own page instead of a drawer, "drill from here" dropped. See `.scratch/chessop/issues/19-progress-view.md`.

Three variants of the progress view, the page where the learner looks at their repertoire between rounds. One route, one data payload, three structurally different pages; the floating pink pill (and the ← → keys) switch variants, the URL is shareable.

## Run

```
cd prototype/progress-view
uv run python server.py
```

Then open <http://localhost:8011/prototype/progress?variant=A>. `data` in the pill opens the raw payload.

## What it shows

The play-loop prototype's `tree.json` (2013-01 dump, 1800+, 0.2 %, top-3: 289 trie nodes) pooled by EPD into the position graph of ADR 0006: **272 positions, 188 of them learner positions** (side to move = the learner's colour, ADR 0006), 15 reached by more than one move order. **The real graph is about four times this** (1,104 positions at 1800–2100 on August 2026 data, ticket 17); judge density with that in mind.

The history is **simulated**: three weeks of daily sessions (25–70 rounds a day, three days off) played by a fake learner with a per-opening skill under ADR 0001's memory model (half-life recall, counted / sure / relearning passes, need floor 0.1, popularity × mean-need opponent). Plus a 23-round session "today", so the in-session success rate has something to say. Score history is one snapshot per day at the end of the session. Nothing persists; restart for a fresh history.

Explanations (ticket 15): the Najdorf position has the real Wikibooks text (from `refs/openings-text/`); every other position has a marked placeholder, borrowed from the nearest exactly-named ancestor on the canonical order when the position has no exact name.

| variant | what it tests |
| --- | --- |
| `A` Ledger | The repertoire as a **table of openings** (score, W/B split, known/learning/never bar, opt-in toggle, reset), each unfolding into its **branches as move strings**; every learner move is a chip underlined by recall colour; clicking one opens a **detail drawer** (mini board, numbers, main moves, explanation, drill/reset). Score history is a sparkline in the header. |
| `B` Explorer | **Board-first**, like an analysis board: the shown position, its main moves as rows (popularity, name below, aggregate recall below, the child's own recall), breadcrumbs, ← to go up, plus a **weakest positions** and a **never passed** list as shortcuts. Detail panel on the right. No table, no graph. |
| `C` Wall | A **heatmap**: every learner position is one 16 px cell inside its opening's block, ordered by ply, coloured by recall (grey = never passed, black-bordered = Black to move); a full-width **score history chart** with per-day rounds and success rate; W/B filter; click a cell for a modal detail. |

Colour scale everywhere: green ≥ 90 % recall, yellow 50–90 %, orange < 50 %, red = a relearning pass owed (missed, not yet passed again), grey = never passed.

The actions (reset a position, reset an opening, opt an opening out or in) are **stubs that mutate the in-memory state** so the page shows their consequence. "Drill from here" only toasts.

Screenshots in `shots/` (`?sel=40` selects the Indian Defense position used there).
