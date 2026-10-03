# Latency over the internet

Type: grilling
Status: resolved
Blocked by: 
Map: [chessop in public](../map.md)

## Question

ADR 0004's budget (a move's server time under 10 ms p95) was measured on localhost with one learner. Hosted, decide: whether it holds with tens of learners sharing the one round-end lock (~12 ms on the event loop, From one learner to many), measured by a load test against the real server, and whether per-learner locks plus a worker thread are then needed; what the play page does on a dropped or slow socket from a phone on 4G (reconnect and resume the round, or restart it; what the learner sees meanwhile); and whether the 300 live-session ceiling (Abuse and limits on the hosted site) fits the VPS's memory.

## Answer

Grilled 2026-10-02. Recorded in amendments to [ADR 0002](../../../docs/adr/0002-persistence.md) (WAL) and [ADR 0004](../../../docs/adr/0004-web-stack.md) (budget, reconnect, builds off the loop, shared caches); no glossary change.

Measured facts (dev box, faster than the VPS, so times are lower bounds; scripted clients all shared the one learner, so this reflects loop contention and commit cost, not sessions, TLS or the internet):

- A round-ending move costs 12–22 ms on disk for one learner, about 10 ms of it SQLite's fsync (rollback journal, `synchronous=FULL`); about 30% of moves end a round, so all-moves p95 was about 25 ms against the 10 ms budget. A continuing move is under 1 ms. `tests/test_latency.py` passed only because it uses an in-memory store.
- With WAL + `synchronous=NORMAL`: all-moves server p95 4.8 ms at 100 clients, 5.3 ms at 300 (1–3 s think time).
- The round-end lock is never contended (everything is on the event loop); the cost is other learners' moves queueing behind a commit.
- A ledger build is about 208 ms and a band-graph load 66–74 ms (`load_graph` parses the whole file each call), both on the loop.
- A warm learner session is 4.6 MB on 1500-1800 (3.3 MB on 0-1200, 8.6 MB on 2100+), not about 3 MB; about 3.6 of the 4.6 MB (`_count`, `_parents`, `_below`, `_weight` in `Steering`) depends only on the repertoire. 300 sessions measured 1.03–2.6 GB RSS by band; about 0.4–0.5 GB estimated with those caches shared. Open bands 1200+ and 1500+ not measured. An open socket costs about 70 KB.
- `play.js` has no `onclose` or reconnect: a dropped socket leaves the page dead with no sign.

Decisions:

- **Budget**: server handling of a move under 10 ms p95 over all moves, round-ending included, on an on-disk store, held with **30 learners playing at once**; plus drop to reply under 250 ms p95 from a French 4G phone. Past 30 the site may degrade up to the session ceiling.
- **SQLite**: WAL with `synchronous=NORMAL`, both modes. A power loss may lose the last few rounds; never corruption. Database copies go through SQLite's backup API, not a file copy.
- **Round-end lock**: stays, commit on the event loop. No per-learner locks, no worker thread for commits; revisit only if the load test misses the budget on the VPS at 30 learners.
- **Builds off the loop**: the default settings key (band 1500+, default settings) is warmed at startup; any other band graph, repertoire or ledger is built in a worker thread.
- **Session ceiling**: stays 300. The repertoire-only steering caches move into the shared repertoire, so a session holds about 1 MB.
- **Dropped socket**: the round is abandoned as in ADR 0004 (nothing written, no miss charged); no resume. The page **auto-reconnects** with backoff (1 s, 2 s, 5 s, then every 10 s), and at once when the tab becomes visible or the browser reports it is online; the new socket gets a fresh round. No retry after a close with code 1008 (rate limit) or a "chessop is full" refusal: those keep the manual "connection lost, reload" state.
- **While disconnected**: the board locks and a "Reconnecting…" banner sits over the verdict area. After reconnecting, a one-line note: "Connection was lost; that round wasn't counted".
- **Slow socket**: after 1 s with no reply to a move, a "waiting for the server…" hint; after about 10 s of silence the page closes the socket and reconnects. No application heartbeat; uvicorn's WebSocket ping stays as is.
- **Tests**: `tests/test_latency.py` uses an on-disk store. A kept `scripts/loadtest.py` (N scripted WebSocket learners playing rounds, reporting p50/p95 and RSS) is run by hand against the VPS before launch and after any change to the round-end path, not in CI. Pre-launch gate: the budget at 30 learners, and RSS under 1 GB at 300 sessions.
- **Handed on**: the pre-deploy backup in Deploying chessop to the VPS, and any backup in Operating the hosted site, must use the SQLite backup command.
