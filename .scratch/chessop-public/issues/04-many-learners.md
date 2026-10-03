# From one learner to many

Type: grilling
Status: resolved
Blocked by: 03
Map: [chessop in public](../map.md)

## Question

The glossary's **Learner** is "exactly one learner, never asked who they are" and ADR 0002 keeps all history in one SQLite file with no identity. In hosted mode, decide: what identifies an **anonymous learner** (a server-side record keyed by a cookie token, or history held in the browser); how their position records, round log, daily score and settings are stored (one database with a learner key, or a file per learner); how an account **adopts** anonymous history (and what happens when the account already has history); whether settings such as the rating band and widths become per-learner; and how ADR 0004's single round-end lock and in-process state scale to many learners, including how many of the eight bands' graphs the server holds in memory at once (learners now pick their band, see "Open-ended rating bands"). Amends ADR 0002 and the glossary.

## Answer

Grilled 2026-09-29. Recorded in amendments to [ADR 0002](../../../docs/adr/0002-persistence.md) and [ADR 0004](../../../docs/adr/0004-web-stack.md); glossary: **Learner** reworded, **Account** and **Adopt** added. Code facts measured on the packaged snapshot (5 closed bands): graph 4–8 MB per band, repertoire ~10 ms / ~2 MB, ledger 200–400 ms, per-learner state ~3 MB, round-end commit ~12 ms.

- **Anonymous learner**: server-side record created at the first round, keyed by a random token in an HttpOnly/Secure/SameSite=Lax cookie. No history in the browser.
- **Storage**: one SQLite file (WAL), learner id on records, round log, daily score, settings. Local mode = one implicit learner; a migration moves v1 files onto it. No local-to-hosted import.
- **Adopt**: merge; per position the later last pass wins; both round logs kept; daily score keeps the account's Score, adds anonymous rounds/successes; account settings win if any; anonymous learner deleted. No prompt.
- **Settings**: per learner (band, widths, openings, sound, animation, new timezone from the browser); model parameters server-wide.
- **Memory**: band graphs loaded on first use and kept (≤ 8); repertoire + ledger shared per settings key, LRU 16; learner session dropped after 30 min idle, which is also the progress view's "session".
- **Concurrency**: devices = tabs; the one round-end lock stays on the event loop, per-learner locks + worker thread only if the latency work demands it.
- **Deletion**: a learner's round log goes with the learner; no anonymised copy.
- **Handed on**: what sign-out leaves on the device → "Sign-in with Lichess and email"; cookie lifetime and unclaimed-anonymous retention → "Legal pages and data rights" and the abuse fog.
