# Opening explanations: does the drill show the wikibook text, where, and does it ship in the snapshot?

Type: grilling
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

Ticket 14 established the facts: the prose on Lichess's own opening pages is Lichess's user-written wiki and cannot be reused, but the "Chess Opening Theory" wikibook that Lichess falls back to is CC BY-SA 4.0, fetchable from the MediaWiki API without auth (2,563 pages, about 4.6 MB of wikitext, keyed by move order with redirects for transpositions), and covers 61 % of the current 1800+ repertoire's positions with real prose (100 % via a named ancestor) but only 20 % of the 3,810 named lines. See `docs/research/opening-explanations.md`. Decide:

- Does the drill show it at all in v1, and where: with the reveal at the end of a round (ticket 10's verdict strip), in the progress view, on demand per position, or somewhere else? The play loop is "go fast", so nothing may sit between the learner and the next round.
- Which text for a position with no page of its own: the nearest named ancestor's, or nothing?
- Does it ship in the snapshot (ADR 0003, a separate CC BY-SA data file beside the CC0 tree, pulled at `build-snapshot` time) or is it fetched live (ADR 0002 says the app runs offline, which rules live fetching out unless that decision is reopened)?
- Attribution: where the per-page link, the licence notice and the "trimmed" note live in the UI and the README.
- Resolve the consequences in `CONTEXT.md` (a glossary entry for the text) and as an amendment to ADR 0003 if it ships in the snapshot.

HITL: grill the learner; do not answer for them. Blocked by nothing, but the repertoire rule (ticket 13) changes the coverage numbers: at "all named lines" the wikibook covers one line in five.

## Comments

**2026-09-13, agent.** Inherited from ticket 11 (ADR 0006): the repertoire is now a graph of positions, so a position has no single move order. The snapshot stores per position a canonical (most popular) move order and, for named positions, the book's own line; the wikibook is keyed by move order with redirects for transpositions, so this ticket chooses which of the two the lookup uses (and what to do when neither has a page). The banner shows the last exact book name seen along the path walked in the round; an explanation shown "for the position" should say whether it follows the same rule (nearest named position on the path walked) or the canonical order.

## Answer

Grilled with the learner on 2026-09-15; every recommendation was taken as proposed.

- **In v1.** The Wikibooks "Chess Opening Theory" text (CC BY-SA 4.0, ticket 14) ships and shows. The glossary gains **Explanation** for it (`CONTEXT.md`).
- **Where.** Two places: **at round end**, under the verdict strip, for the position where the round ended (the one whose main moves the arrows reveal: the missed position, the leaf on a success, the position where the set-aside move was played on a forced outcome); and **in the progress view**, per position, handed to that fog patch. Never mid-round: no on-demand key (the page's responses list would reveal the main moves against ticket 10's rule) and nothing in the banner. Space goes straight on; the text blocks nothing and there is **no setting** to hide it.
- **Amount and form.** The **lead** (the prose before the first sub-heading, capped at a few hundred characters) shows under the strip, with a "more" toggle that expands the whole trimmed page in place; the board never moves. **Plain-text paragraphs** stripped from the wikitext at build: no links, no markup; the position template, theory table, "All possible replies" / "responses" lists, external links and the conventions line are trimmed as Lichess trims them (`transformWikiHtml`, ticket 14 §1b).
- **Fallback.** A position with no page of its own shows the text of the **nearest position with a page on the path walked in the round**, labelled with that position's moves so the substitution is visible: the same rule the banner uses for names (ADR 0006). Ticket 14 measured that this gives every repertoire position a text. Never the canonical order (it can explain a line the learner did not play) and never nothing.
- **Shipped, not fetched.** `build-snapshot` pulls the text from the MediaWiki API (wikitext, 50 titles per request, serial, descriptive User-Agent, `maxlag`) and writes a **separate CC BY-SA 4.0 data file beside the CC0 graph**, keyed by position. ADR 0002 and 0003 stand: the runtime never touches the network. ADR 0003 amended.
- **Lookup at build.** For every position in the snapshot (**all five bands**, at the 0.02 % storage cut-off, so no repertoire-rule or band change ever needs a text rebuild): try the **book's own line** (named positions), then the **canonical most-popular order**, each with `redirects=1`; store each page once and map EPD to page. Positions with no page carry no text; the fallback is resolved at runtime along the path walked.
- **Attribution.** A one-line footer under every shown text, "From Wikibooks, Chess Opening Theory · CC BY-SA 4.0 · trimmed", the page title linking to the Wikibooks page (opens the browser; offline it simply fails); a Licences section in the README; a copy of CC BY-SA 4.0 in `LICENSES/` beside the GPL; a licence header inside the text data file itself, so the file redistributed alone stays compliant.
- **Assumptions recorded.** English Wikibooks only. Fair-use quotations and any extra attribution notation a page carries are kept as they are (ticket 14 saw none on the pages sampled).
- **Wire consequence for the spec** (ADR 0004 protocol, not amended): `round_over` and a round-ending `moved` carry the explanation for the revealed position: lead, full text, the moves of the position the text belongs to (empty when it is the revealed position's own), page title and URL. No extra round trip.

Assets: `CONTEXT.md` (Explanation), `docs/adr/0003-opening-tree-snapshot.md` (amendment, ticket 15). Facts: `docs/research/opening-explanations.md`.
