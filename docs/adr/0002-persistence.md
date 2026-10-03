# Persistence: one global memory per position, server-side, in one SQLite file

Status: accepted (ticket 07, 2026-09-11)

The destination fixes a single learner and a local-first app, and ADR 0001 keeps history on positions rather than branches. This ADR decides where that history lives, what it survives, and who owns it while a round is played.

## Decision

- **No learner identity.** The app has no accounts, login, profiles or learner id. The learner is whoever runs a given data directory; a second person on the same machine uses another data directory (CLI flag or environment variable).
- **One SQLite file** in the XDG data directory (`~/.local/share/chessop/` by default, overridable) holds everything mutable: position records, the round log, and settings (rating band, widths, opted-in openings, model parameters). There is no separate config file. Schema changes are forward-only migrations tracked by a schema-version table.
- **History is global per position and learner colour, independent of any repertoire.** Regenerating the repertoire (new dump month, other rating band, openings opted in or out, widths changed) never touches a record. Positions that leave the repertoire go dormant; if they return, their records return with them. Only an explicit "reset all history" deletes records. Ticket 11 chooses the exact key (EPD or move string); either is stable across regeneration, which is all this ADR requires.
- **The server is authoritative.** The repertoire tree, its cached need aggregates and the position records live in the server process. Every round end (including every miss) is written through to SQLite before the next round starts. Browser tabs are thin: they submit moves and render; the server scores. Several tabs may be open; their rounds are serialised. A round cut off by a crash is simply not recorded.
- **The round log is append-only and never pruned** in v1; it is the input for refitting the memory model later.
- **No Lichess token in v1.** The tree ships from an offline snapshot; the app runs fully offline. A personal token or Login-with-Lichess belongs to the later "seed from own games" work.
- **Deployment is a local server.** One command starts the server bound to localhost and opens the browser; a flag allows binding another interface for a device on the LAN. No authentication on the server, no Docker image, no hosting.
- **Backup is copying the file.** No export/import feature in v1. One "reset all history" action in settings, behind a confirmation; finer resets belong to the progress view.

## Amendment (ticket 19, 2026-09-22)

The SQLite file gains a **daily score table**: one row per local day, holding the Score (ticket 16), its White and Black halves, and the day's rounds and successes, **upserted at every round-end commit** in the same transaction as the position records and the round log. It exists because the round log cannot reproduce a past score (records change under it) and the progress view shows the daily score; it is also the evaluation work's cheapest "is this working" series. The **finer resets** this ADR left to the progress view are decided there: resetting one position or one opening deletes those position records (with a confirmation), and opting an opening in or out is a settings write made from the progress view.

## Amendment (chessop-public ticket 03, 2026-09-29)

"No hosting" is lifted for a **hosted mode**: the same server, still authoritative with its history in SQLite on local disk, runs on one OVH VPS behind Caddy at `chessop.fr` (ADR 0007). The local mode described above is unchanged. Who the learner is and how history is keyed when many learners share one server is left to chessop-public ticket 04.

## Amendment (chessop-public "From one learner to many", 2026-09-29)

"No learner identity" holds for the **local mode** only. The **hosted mode** knows many learners:

- **An anonymous learner is a server-side record**, created at their first round (not their first page view), keyed by a random token in an HttpOnly, Secure, SameSite=Lax cookie that holds nothing but that pointer. History never lives in the browser; clearing cookies or changing device loses an anonymous learner's history unless they signed in, and the site says so once.
- **Still one SQLite file** (WAL mode). A learner table; position records, the round log, the daily score and settings all carry the learner id. Local mode uses the same schema with one implicit learner; a forward-only migration attaches an existing v1 file's rows to it and turns the stored `rating` into the closed band it maps to. No import of local history into the hosted site in this effort.
- **Settings are per learner**: rating band, widths, opted-in openings, sound, animation, and a new **timezone** (reported by the browser on its first socket message when unset, editable in settings; local mode uses the machine clock). The daily score's day is the learner's local day. **Model parameters stay server-wide**, set by the owner. A new learner gets the defaults (1500+, widths 2 and 3).
- **Adopting**: signing in attaches the anonymous learner to the account. If the account has no history it takes everything. Otherwise they merge: a position on one side only carries over; on both, the record with the later last pass wins (half-life states do not add); both round logs are kept; the daily score keeps the account's Score for shared days and adds the anonymous rounds and successes. The account's settings win if it has any. The anonymous learner is then deleted. No prompt.
- **Several devices are several tabs** (ADR 0004): no limit on concurrent sign-ins.
- **The round log is never pruned while its learner exists**; deleting a learner (on request or by the inactivity purge) deletes their round log with them. No anonymised copy is kept.

Considered: history in the browser until sign-in (the second source of truth this ADR already rejected); a file per learner (easy export and deletion, but usage figures across learners become a scan of every file); asking at each sign-in whether to keep, drop or merge (a memory-model question for the learner); dropping the anonymous side (throws away progress at the moment someone commits to the site); an anonymised round log for refitting (still personal data while paths and timings remain).

## Amendment (chessop-public "Latency over the internet", 2026-10-02)

The SQLite file runs in **WAL mode with `synchronous=NORMAL`**, in both modes. With the defaults (rollback journal, `synchronous=FULL`) the round-end commit's fsync cost about 10 ms of a 12–22 ms round-ending move, which alone broke ADR 0004's 10 ms budget; in WAL/NORMAL the same move is about 2–4 ms. The price: a power loss or kernel crash (not a process crash) may lose the last few committed rounds; the file is never corrupted. Accepted for a drill. Any copy of the database (backups, export tooling) must go through SQLite's backup API, never a plain file copy, because of the `-wal` file.

## Amendment (chessop-public ticket 28, 2026-10-02)

The SQLite file gains a **session table**: the SHA-256 hash of a browser cookie's random token, the learner it points to, when it was created and last used, and when it expires. It is what the anonymous learner's cookie resolves through, and what sign-in will rotate (ADR 0008); deleting a learner deletes their sessions. The anonymous learner's row is created **when the socket of their first round opens** (the cookie is set on that handshake), or when they first save settings or opt an opening in or out; a page view reads a shared, unstored learner with every default. The 12 months slide a day at a time: a session used after more than a day is extended and its cookie re-sent. In local mode nothing reads the table.

## Amendment (chessop-public ticket 33, 2026-10-02)

The hosted site has an **export**, which "No export/import feature in v1" no longer covers there: `/data` downloads one JSON file of everything stored about the browser's learner (account, learner times, settings, position records, the round log, the daily scores), generated and streamed on request from the store, never written anywhere. Positions are written as FEN with nominal move counters (`0 1`: a position has no move number of its own), times as ISO 8601 in UTC. It holds no session token or hash and no recall estimate: the round log's rows keep each visited position's record as it stood, without the estimate noted with it. There is still no import. An anonymous learner can be forgotten from the same page: deleted as an account's learner is, the cookie cleared. Local mode has neither.

## Amendment (chessop-public ticket 41, 2026-10-02)

The SQLite file gains a **daily usage aggregate**: one row per UTC day, counts only, never a learner id, kept forever, so it survives the deletion of every learner. Sign-ins, adoptions and deletions (an account deleted, an anonymous learner forgotten, later a purge) are incremented in the day's row as they happen, in the transaction that does them. The derived counts of a finished day (active learners with and without an account, new learners, rounds and successes with forced rounds left out) are written once, over the learners that remain then, and never rewritten. `chessop stats` reads it for past days and computes weekly and monthly active learners, retention and the choices of active learners live from the learners that remain.

## Amendment (chessop-public ticket 42, 2026-10-02)

Hosted learners are **purged by `chessop maintain`**, nightly, by their last-seen time: an anonymous learner after 12 months with no request (365 days), after 30 days when they logged fewer than 5 rounds (every logged round counts, forced ones included); a learner with an account after 24 months (730 days). An email account is first warned by email at 23 months (700 days) and `warned_at` set only once the message went; it is deleted when unseen for 24 months and the warning is at least 30 days old, so a mail outage delays deletion. Noting a learner as seen clears `warned_at`, and a sign-in notes the account's learner as seen. A Lichess account has no address and is deleted with no warning. Each purge selects and deletes in one transaction, as an account's deletion does, each learner counted in the day's deletions.

## Considered options

- **Accounts with Lichess OAuth** (hosted app): rejected by the destination's single learner / local-first; it would also force live Explorer calls and a hosted database. Superseded for the hosted mode by ADR 0008 (sign-in); still rejected for local mode.
- **Per-repertoire history** (records scoped to band, openings or widths): a known position would be relearned from zero after changing the band; the literature (ticket 01) says knowledge is of positions, not of the curriculum they sit in.
- **Client-side store** (browser storage, server as a sync target): simpler round trip but a second source of truth, a sync protocol, and history that dies with the browser profile.
- **JSON / JSONL files**: readable, but the round log needs querying for refitting and settings plus records plus log want one transaction at round end.
- **Config file for settings**: one more file to locate and version for no gain when the database is already the single mutable store.

## Consequences

- Ticket 08 (data source) can assume an offline snapshot and no Explorer access at runtime; whether the snapshot is a separate immutable file or a table in the same database is its call.
- Ticket 09 (stack) inherits a server-authoritative thin client on localhost, launched from one command; "how a move round-trips" is now client to server to client, never client-only.
- Ticket 11 may pick any position key stable across regeneration.
- Out of scope for this effort: hosting, multi-device sync, accounts and login.
