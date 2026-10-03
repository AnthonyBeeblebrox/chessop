# Opening tree: a shipped per-band snapshot built from one Lichess dump month

Status: accepted (ticket 08, 2026-09-11)

The opponent samples from an opening tree with per-move popularity, the play loop must answer in milliseconds, and ADR 0002 rules out any Lichess token or network call at runtime. We decided that the tree is a **snapshot** built by the developer from one month of the CC0 Lichess database dump and shipped with the app, stored loosely enough that the repertoire's cut-off and any transposition handling are applied when the app loads it, not when it is built.

## Decision

- **Shipped, not learner-built.** A build tool in the repo streams one `.pgn.zst` dump month and writes the snapshot; it runs at release time and the result ships as package data. The learner never downloads a dump. The tool takes a `--max-games` switch for developer test runs only.
- **Source: one recent whole month** of the standard rated dump, chosen at release time and recorded in the snapshot metadata together with the band set, the `chess-openings` TSV commit and the build revision.
- **Game filters, fixed at build**: both players' ratings inside the band; games without a rating header dropped; games with a `BOT` title dropped; ultrabullet and bullet excluded; blitz, rapid, classical and correspondence pooled. The learner cannot choose a time control in v1.
- **Five fixed rating bands**, lower bound inclusive: below 1200, 1200–1500, 1500–1800, 1800–2100, 2100 and above. The learner declares a rating in settings and the app maps it to a band; with no declared rating the band is 1500–1800 (ticket 05).
- **Content per band: the sequence trie**, one node per move sequence, carrying its game count, its EPD, and `eco`, `name` and family looked up in the TSV by exact EPD or taken from the nearest named ancestor. The build **never merges by position**; a merged or pooled-count DAG is derivable from the trie at load, so ticket 11 is free to choose.
- **Stored at a loose absolute cut-off of 0.02 % of the band's games with a ply cap of 30.** The repertoire's cut-off (0.2 % absolute, ticket 05) is applied when the app loads the tree; it is a model parameter kept in settings, not a build parameter. At this cut-off a band's trie is on the order of ten thousand nodes, well under a megabyte.
- **A separate read-only file**, never a table in the learner's SQLite file. ADR 0002's "one file holds everything mutable" stays exactly true; the learner's database records only which snapshot version the current repertoire was generated from. The on-disk format (compressed JSON or a read-only SQLite database) is the implementer's choice; the server loads the band's trie into memory at start.
- **Refresh is release-only.** A new app release is built against a newer month. The build tool is also exposed as `chessop build-snapshot --month YYYY-MM` for a learner with the bandwidth, and the app accepts a `--snapshot <path>` override that wins over the packaged file. When the loaded snapshot differs from the one the repertoire was generated from, the repertoire regenerates and the learner is told; position records are untouched (ADR 0002).
- **The runtime never reads the TSV and never touches the network.** Names, ECO codes and families are baked into the snapshot.

## Amendment (ticket 13, 2026-09-12)

ADR 0005 replaced the 0.2 % absolute repertoire cut-off with a book-terminated rule and a much lower traffic floor. The snapshot is unchanged in shape: the load step now keeps the main moves per node (top-`k` plus the share rule of ADR 0005) whose count clears the floor, then prunes every node with no exactly-named position at or below it. Two consequences: the **floor is bounded below by the 0.02 % storage cut-off**, so the snapshot never has to be rebuilt for a floor change, and the per-node `name` must record whether it is an **exact-EPD match** or inherited from an ancestor, since the pruning needs the former. The **ply cap rises from 30 to the depth of the deepest book line (36 plies today)**, since the book, not the cut-off, now ends a line; measured in `docs/research/repertoire-rule-candidates.md`.

## Amendment (ticket 11, 2026-09-13)

ADR 0006 makes the repertoire a graph of positions. **The snapshot stores the pooled position DAG, not the sequence trie**: per band, every position (keyed by EPD) whose games summed over all move orders clear the 0.02 % storage cut-off, with its pooled count, its **exact** book name or none (the exact-or-inherited flag of the ticket 13 amendment is gone: no inherited name is stored), its most popular move order in the sample and, for named positions, the book's own line; and every (position, move) edge with its pooled count. `build-snapshot` still builds the trie first, since the canonical order and the pooling come from it, then keys it; any edge that would close a cycle is dropped (the shorter path wins) and the count reported. The cut-off, ply cap (36), band, filter and versioning rules are unchanged, and the load step (ADR 0005's rule) runs on positions and edges instead of nodes. The "never merges by position" line above and the three-way choice it left to ticket 11 are superseded.

## Amendment (ticket 15, 2026-09-15)

The snapshot gains a **companion explanation file**: the trimmed plain-text prose of the Wikibooks "Chess Opening Theory" book (CC BY-SA 4.0, `docs/research/opening-explanations.md`) for every position in the snapshot that has a page, across all five bands, pulled by `build-snapshot` from the MediaWiki API (wikitext, 50 titles per request, serial, descriptive `User-Agent`, `maxlag`) at the same release-time build. It is a **separate file** from the CC0 graph so the two licences never mix: each page stored once (lead, full trimmed text, title, URL), an EPD-to-page map, and a licence header naming CC BY-SA 4.0 and the trimming. The lookup per position tries the book's own line, then the canonical most-popular order, each following the book's redirects; positions with no page carry no text and borrow one at runtime along the path walked. The "never touches the network" rule stands: the text is static once built and refreshes with a release like the graph. Redistribution obligations (per-text link, README notice, a copy of CC BY-SA 4.0 in `LICENSES/`) are the app's, recorded in ticket 15.

## Amendment (ticket 22, 2026-09-24)

A whole month does not fit the build: the trie of ~45 M kept games is about 1.2 billion nodes, some 400 GB, found by the spec review of build ticket 03. **The source becomes a capped prefix of one recent month: at most 150,000 kept games per band**, read from the start of the dump; a full band drops its further games and reading stops when every band is full or the month ends (about 5–6 % of 2026-08, ~6 GB peak). 150,000 is the sample ticket 17 measured at 1800–2100, so its sizes stay the build's sanity bounds. The storage cut-off stays 0.02 % of the band's kept games. The metadata adds the cap, the games read and the compressed bytes read. `zstandard` is a build-time dependency in the optional extra `chessop[build]`, never loaded by the server. Filters, bands, ply cap and files are unchanged.

## Considered options

- **Live Opening Explorer calls**: the only direct per-move popularity source, but a token on every request since March 2026, 25 requests per minute and one position per request; 40 minutes to fetch a 1,000-node tree. Ruled out of the play loop by "speed first" and out of v1 altogether by ADR 0002.
- **Learner-built snapshot** (download a dump on first run): a recent month is 30 GB and over an hour of parsing; local-first means running offline, not rebuilding the tree.
- **The `chess-openings` TSV as the tree**: names only, no popularity; it labels nodes, it cannot weight them.
- **Bake the 0.2 % cut-off at build**: ~500 nodes per band, but every change to the cut-off or to how transpositions are counted would need a rebuild.
- **Pre-merge transpositions at build**: closes ticket 11's question inside the data file.
- **A table in the learner's SQLite file**: one place for everything, at the cost of a copy step and a migration on every app update.
- **All speeds, or a learner-chosen speed**: bullet openings are not classical openings; a chosen speed multiplies the snapshot and the repertoire by five for a small gain.
- **The explorer's own rating groups** (1000, 1200, 1400, 1600, 1800, 2000, 2200, 2500): narrower, but the settled fallback 1500–1800 is not one of them, and 300-wide bands leave every band well over 100 k games in a recent month.
- **Several months summed**: buys nothing at 90 M games a month.
- **The whole month in one pass** (ticket 22): about 400 GB of trie. **The Opening Explorer walked at build time**: a token, hours per band, its own rating groups and no move orders. **Two passes over the whole month**: all the data, but over an hour and a new method for no measured gain over ticket 17's sample.

## Consequences

- Ticket 11 chooses between the sequence tree, a merged DAG and a pooled-count DAG from the same file; the snapshot supports all three.
- Ticket 09 (stack) inherits a server that loads one band's trie into memory at start and serves the play loop from it; no data access is on the move round trip.
- The build tool is part of the v1 deliverable: streaming zstd PGN parse, rating and speed filters, per-band tries, TSV lookup, metadata. The 2013-01 measurements (`refs/lichess/tree-width-analysis.py`, `transposition-analysis.py`) are its prototype.
- Settings gain a declared rating (mapped to a band), the cut-off, and the snapshot version the repertoire came from.
- Repertoire size numbers measured on 2013-01 (235 positions at 1800+ / 0.2 % / (3,3)) will shift on a recent month; the shape, not the count, is what was decided.

## Amendment (chessop-public ticket 02, 2026-09-29)

For a hosted chessop the owner wanted to drill against stronger play than the learner's own band. **Eight bands**: the five closed bands stay and the **open bands 1200+, 1500+ and 1800+** are added (2100+ is already open). A game counts toward **every** band both players fall in, so the build keeps one game in several tries; the cap of 150,000 kept games per band, the storage cut-off, filters, ply cap and files are unchanged. **The learner chooses the band** in settings; the declared rating and its mapping to a band are gone. **The default band becomes 1500+.** A stored declared rating migrates to the closed band it mapped to; a learner with none moves to 1500+ under the refresh rule above (repertoire regenerates, learner told, position records untouched). An open band keeps the natural rating mix of its games (1500+ on 2026-08: 54 % 1500–1799, 37 % 1800–2099, 9 % 2100+), not a strength-stratified one. Measured in `docs/research/open-bands.md` (branch `research/open-bands`): the three open bands add about 3 GB and 5 minutes to the build and 588 KB to the snapshot.

Considered: **open bands only** (drops "what my peers play", which closed bands answer); **only 1500+** (a lone odd band); **learner's side only above the bound** (impossible, a game feeds both colours); **a rating plus an "include stronger players" toggle** (two settings for one choice); **stratified sampling across strengths** (invents a population; top moves already match the neighbouring bands at 62 of 65 busy positions); **a larger cap for open bands** (sample noise sits near the floor in every band, a general question).
