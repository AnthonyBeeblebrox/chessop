# Data source: live Lichess explorer calls, an offline snapshot, or the ECO TSV?

Type: grilling
Status: resolved
Blocked by: 02, 05, 07
Map: [Chess opening trainer by sampling](../map.md)

## Question

Given the Lichess findings, the repertoire definition and the persistence decision: build the opening tree live from the Opening Explorer per session, snapshot it into a local file at a chosen popularity cut-off, or derive it from the chess-openings TSV? Decide refresh cadence, rating band, and speed/offline trade-offs. Record as an ADR.

HITL: grill the user.

Inherited from ticket 05 — settled:

- The popularity cut-off is **absolute, not relative**: a line is in the tree iff it was played in >= 0.2 % of *all* games in the band, not of the games reaching the parent position. Chosen for book depth — ply 18, nine moves each, 450 positions uncapped and 235 at the settled widths in the 1800+ bucket.
- Rating band: one band per repertoire, defaulting to the learner's own declared rating, falling back to 1500-1800 when unknown.
- The tree is built offline from a CC0 dump month, and candidate lines are grouped into ECO families via the `chess-openings` TSV; the learner opts openings in.
- The width parameters are separate from the cut-off and do not change the snapshot.
- This ticket owns the opening-tree data-source ADR the destination calls for.

Inherited from ticket 07 — settled (ADR 0002):

- Single learner, local-first, **no Lichess token in v1**: the tree ships from an offline snapshot and the app runs fully offline. Live Explorer calls are not available to this decision.
- All mutable state (position records, round log, settings) is one SQLite file in the XDG data dir. Whether the repertoire snapshot is a separate immutable file (versioned by dump month, band, cut-off) or a table in that same database is this ticket's call.
- Position records are global per position and colour and survive every regeneration, so a snapshot refresh never has to migrate history.

## Comments

**Round 1** (eight questions, all recommendations agreed by the user in one word): shipped snapshot; one recent whole month; five 300-wide bands; bullet excluded; 0.2 % applied at load over a 0.02 % stored trie; sequence trie with EPD, never pre-merged; separate read-only file; release-only refresh with a CLI build command and a `--snapshot` override. Stated assumptions (no Elo dropped, both players in band, names baked in, runtime never reads the TSV) accepted with them. Frontier empty after round 1; the remaining calls (metadata fields, override precedence, regenerate-and-notify on a snapshot change) were made without asking and are in the ADR.

## Answer

Recorded as **ADR 0003**, `docs/adr/0003-opening-tree-snapshot.md`; glossary gains **Snapshot** in `CONTEXT.md`.

- **Shipped snapshot, not live calls and not learner-built.** A build tool in the repo streams one recent whole month of the CC0 standard rated dump at release time; the result ships as package data. The learner never downloads a dump. `--max-games` exists for developer runs only.
- **Filters fixed at build**: both players' ratings inside the band, no-rating and `BOT` games dropped, ultrabullet and bullet excluded, other speeds pooled. No time-control choice in v1.
- **Five fixed bands**, lower bound inclusive: <1200, 1200–1500, 1500–1800, 1800–2100, 2100+. The learner declares a rating; the app maps it; fallback 1500–1800.
- **Per band, the sequence trie** with game count, EPD, and eco / name / family (exact EPD in the TSV or nearest named ancestor) per node, stored at an absolute **0.02 %** cut-off with a ply cap of 30 and **never merged by position**. The repertoire's 0.2 % cut-off is applied at load and lives in settings; ticket 11 can derive a merged or pooled-count DAG from the same file.
- **Separate read-only file**, versioned by dump month, band set, TSV commit and build revision; the learner's SQLite file records only which snapshot version the repertoire came from. Format is the implementer's choice; the server loads one band's trie into memory at start.
- **Refresh is release-only.** `chessop build-snapshot --month YYYY-MM` is exposed for power users and `--snapshot <path>` overrides the packaged file. A changed snapshot regenerates the repertoire with a notice; history is untouched (ADR 0002).
- **The runtime never reads the TSV and never touches the network.**

### Handed to other tickets

- **Ticket 11**: the snapshot is a sequence trie with an EPD per node; sequence, merged and pooled-count trees are all derivable at load, so the choice is purely the drill's.
- **Ticket 09**: the server loads one band's trie into memory at start; no data access sits on the move round trip.
- **Spec**: the build tool (streaming zstd PGN parse, filters, per-band tries, TSV lookup, metadata) is a v1 deliverable; the 2013-01 analysis scripts in `refs/lichess/` are its prototype.
