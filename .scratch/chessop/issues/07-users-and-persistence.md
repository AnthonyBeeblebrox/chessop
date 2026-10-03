# Users and persistence: single local learner or accounts, and where do branch stats live?

Type: grilling
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

Is this a personal tool (one learner, local SQLite, no login) or a hosted app with accounts (possibly Lichess OAuth)? Where do per-branch success counts persist, and must they survive repertoire changes (e.g. when the 'main openings' list is regenerated from fresh Lichess data)? This fixes deployment shape and whether the data source can be an offline snapshot.

HITL: grill the user.

## Answer

Recorded as **ADR 0002**, `docs/adr/0002-persistence.md`; glossary updated in `CONTEXT.md` (Learner, Position record, new term Round log).

The first half of the question was already answered by ticket 05 (single learner, local-first). What this ticket settled, all eight points agreed as recommended:

1. **No learner identity.** No accounts, login, profiles or learner id. A second person on the same machine uses a different data directory (flag / env var). Records are keyed by position and learner colour only.
2. **One SQLite file** in the XDG data dir (`~/.local/share/chessop/`, overridable) holds position records, the round log and settings. No config file. Forward-only migrations with a schema-version table.
3. **History survives every repertoire change.** Regeneration (dump month, band, openings, widths) never touches a record; positions that drop out go dormant and return with their records. Only "reset all history" deletes.
4. **History is global, not per repertoire.** Changing band from 1500-1800 to 1800+ keeps the records of the positions common to both. The repertoire is a lens over one memory.
5. **No Lichess token in v1.** The tree ships from an offline snapshot; the app is fully offline. Token / Login-with-Lichess rides with the "seed from own games" fog.
6. **Deployment = local server.** One command starts the server on localhost and opens the browser; a flag binds another interface for a LAN device. No server auth, no Docker, no hosting.
7. **Server authoritative.** Tree, aggregates and records live in the server process, written through to SQLite at every round end and every miss. Tabs are thin; concurrent tabs are serialised. A round cut off by a crash is not recorded.
8. **Backup = copy the file.** No export/import in v1. One confirmed "reset all history" action; finer resets go to the progress view.

Routine calls made without asking: round log append-only and never pruned in v1; schema versioning as above.

### Handed to other tickets

- **Ticket 08** (data source, now unblocked): offline snapshot, no Explorer at runtime; whether the snapshot is a separate immutable file or a table in the same SQLite file is its decision.
- **Ticket 09** (stack, now unblocked): server-authoritative thin client, localhost server started by one command that opens the browser, LAN bind flag; move round trip is client to server to client.
- **Ticket 11**: any position key stable across regeneration is acceptable.
- **Fog**: deployment settled and removed; Lichess token folded into seeding; progress view gains per-opening / per-position reset. **Out of scope**: hosting, multi-device sync, accounts and login.
