# Web stack: FastAPI, chessground, one WebSocket per tab, server-supplied legal moves

Status: accepted (ticket 09, 2026-09-11)

ADR 0002 fixed a server-authoritative thin client launched locally from one command, and ADR 0003 a snapshot loaded into memory at start, so nothing but the framework, the board and the wire sits on the move round trip. This ADR picks them, with "go fast" as the ruling preference: nothing in the play loop may add a visible wait.

## Decision

- **FastAPI** with uvicorn, single async worker, all state in the process. **Jinja2** server-rendered pages with plain HTML forms for settings and the reset confirmation; exactly **one hand-written JS module**, on the play page. No client framework, no bundler, no Node at build or run time.
- **chessground** (Lichess's board, GPL-3.0-or-later) is the board. Its dist, base CSS, brown board and cburnett piece set (CC BY-SA 3.0, attributed in the README) are **vendored into the package as static files**, copied by hand on upgrade. Lichess defaults, no theme picker in v1. The project is licensed **GPL-3.0-or-later**; python-chess already required it on the server side.
- **The browser holds no chess logic.** No chess.js. With every position the server sends the FEN, the orientation and the legal-destinations map computed by python-chess; chessground restricts drags to it. The learner may play any legal move, because ticket 05 hides the main moves; the server judges it.
- **One WebSocket per tab** carries the round. Client to server: `move {from, to}` and `next`. Server to client: `round` (side, FEN, dests, orientation, opening name) when a round begins; `moved` (verdict pass or miss, the revealed main moves of the position just left, the opponent's reply, new FEN and dests) after each learner move; `round_over` (outcome, reveal, path) when the branch ends or a miss lands. The client asks for the next round with `next`; how long the reveal stays visible is the play page's decision (ticket 10), not the protocol's.
- **One round per tab.** Each socket has its own round in flight; only the round-end commit (position records, need aggregates, round log) is serialised under one lock. Two tabs sampling from need aggregates a few seconds stale is accepted. A socket that closes mid-round abandons the round: nothing is written, no miss charged, the next connection starts fresh.
- **Promotion is auto-queen** and any promoting move is outside the repertoire in v1; chessground has no promotion dialog and no 18-ply repertoire line reaches one.
- **Latency budget**, held by the spec: server handling of a learner move under 10 ms at p95; drop to reply visible under 100 ms end to end on localhost; the next round on the board within 200 ms of `next`; piece animation capped at 100 ms and settable to zero in settings; no loading indicator anywhere in the loop.
- **Packaging**: a uv-managed project, Python 3.12 minimum, one `chessop` console script. `chessop` alone serves on localhost, port 8000 with a free-port fallback, and opens the browser; `chessop serve --host --port` binds a LAN interface; `chessop build-snapshot --month YYYY-MM` and `--snapshot <path>` are ADR 0003's. Installed with `uv tool install` from the repository, PyPI later if wanted.
- **Tests**: pytest for the sampling, memory model and repertoire; FastAPI's test client drives the WebSocket through whole rounds; no browser automation in v1. The play page is verified by the ticket 10 prototype and by hand.

## Amendment (ticket 19, 2026-09-22)

The app's pages are the play page (the one JS module), settings, the reset confirmation, and the **progress view**: `/progress`, a server-rendered ledger of the repertoire (openings in order of the share of games reaching them, each unfolding into its exactly-named lines and then its branches as `<details>`, with the Score, its White and Black halves, the in-session success rate, a sparkline of the daily score and the never-passed count on the head), and `/progress/position/<epd>`, one position's page (board as an SVG from python-chess's `chess.svg`, the numbers, the main moves, the Explanation, reset). Both are plain Jinja2 with HTML forms for the per-opening and per-position resets and the opt-in/out toggles; **no second JS module**, since nothing on them is latency-sensitive. Decided by prototype in `prototype/progress-view/` (ticket 19).

## Amendment (ticket 21, 2026-09-24)

Two changes to the wire. **`moved` no longer carries the revealed main moves**: ticket 10 reveals nothing while the learner plays, so the server does not send what the page must hide; the main moves travel only in `round_over`, for the position the round's last move was played from. **A fifth message**, client to server, `sound {on}`, sent when the learner toggles sound with `m` on the play page; the server writes the `sound` setting and does not reply. The settings page keeps its plain form for the same setting.

## Amendment (chessop-public ticket 03, 2026-09-29)

A hosted deployment is no longer ruled out: the GPL is honoured by publishing the source (public repository linked from the site), and ADR 0007 runs the same FastAPI process, bound to `127.0.0.1`, behind Caddy on one VPS under systemd. "No Docker image" stands. The latency budget above was set on localhost; whether it holds over the internet is still open.

## Amendment (chessop-public "From one learner to many", 2026-09-29)

In hosted mode the process holds three layers. **Band graphs** load on first use and stay for the process's life (at most eight, 4–8 MB each), so changing band no longer re-parses the snapshot file. **Repertoire and progress ledger** depend only on band, widths, popularity floor, share and opted-out openings, so learners with the same settings share one, cached by those settings and evicted least-recently-used past 16. **A learner session** (records, steering caches, faced counts, notices; about 3 MB) loads when the learner first connects or requests a page and is dropped after **30 minutes** with no socket open and no request; the progress view's "in-session" success rate counts from its start. A settings change regenerates only that learner's repertoire and restarts only that learner's tabs. **The single round-end lock stays**, with the commit on the event loop (about 12 ms, p95 15–17 ms): hobby scale cannot saturate it. Per-learner locks with the commit in a worker thread are the fallback if the internet-latency work finds a move's server time breaking the 10 ms p95.

## Amendment (chessop-public "Latency over the internet", 2026-10-02)

**The budget, restated.** Server handling of a learner move under 10 ms at p95 over *all* moves, round-ending ones included, measured on an on-disk store; in hosted mode it is promised with **30 learners playing at once**, plus drop to reply under 250 ms p95 end to end from a French 4G phone. Past 30 the site may degrade up to the session ceiling. Measured before this amendment, one learner already missed it (round-ending move 12–22 ms, about 30% of moves); ADR 0002's WAL amendment is what restores it.

**The round-end commit stays on the event loop under the one lock.** Per-learner locks and a worker thread are not built; a kept load-test script, run by hand against the VPS, is the trigger to revisit. **Slow builds leave the loop**: the default settings key (band 1500+) is warmed at startup, and any other band graph, repertoire or ledger is built in a worker thread, so a new settings key no longer stalls every learner's moves for 70–200 ms. **Steering's repertoire-only caches** (counts, parents, below, weights) live with the shared repertoire, not in each learner session, which then holds about 1 MB instead of 3–9 MB.

**A closed socket still abandons the round** (nothing written, no miss charged), but the play page now **reconnects by itself** with backoff and starts a fresh round; it does not resume. "No loading indicator anywhere in the loop" stands for a healthy socket; a dead or slow one shows a banner.

## Amendment (chessop-public ticket 23, 2026-10-02)

**A sixth message**, client to server, `hello {tz}`, sent by the play page each time its socket opens with the browser's IANA time zone (public spec G6). The server stores it as the learner's `timezone` setting only while they have none, ignores a name that is no time zone, and does not reply. The settings page edits the same setting; with none stored, the learner's day is the machine's. Local mode's implicit learner's day is always the machine's (ADR 0002): its `hello` is still taken, but neither it nor any stored zone moves that learner's day, and local settings show no time zone.

## Amendment (chessop-public ticket 27, 2026-10-02)

chessop installs as an app (public spec §8), in both modes. Beside the play page's module there is now a **service worker**, `/sw.js` at the root scope, rendered from a template and registered by the play page (the manifest's `start_url`; the other pages still carry no script). It caches **only the static shell** (chessground, the five sounds, `play.css`, `play.js`, the icon and the offline page) under a cache named for the release and the shell's contents, deletes older caches on activate, and never answers a page or the socket from its cache: page loads go to the network, and when one fails it shows a static offline page whose one inline handler is Try again's reload. The server stays authoritative, so there is **no offline play**. Like the play page, the worker is verified by hand, not by browser automation.

## Amendment (chessop-public ticket 34, 2026-10-02)

Two more small scripts, hosted mode only, both plain static files. Every hosted page carries **`audience.js`** when the GoatCounter address is configured (public spec §12, G3): it counts one page view (path without query, title, referrer cut to its host), and counts nothing when the browser sends Do Not Track or Global Privacy Control or holds GoatCounter's `skipgc` flag. The privacy notice carries **`audience-toggle.js`**, whose box sets and clears that flag. Local mode still has no script outside the play page. Both are checked by reading them, not by browser automation.

## Amendment (chessop-public ticket 39, 2026-10-02)

**`moved` carries `handled_ms`**: the server's handling of the learner move, in milliseconds, from the move's receipt on the socket to its replies ready, the round-end commit included. It is what the kept load-test script (`scripts/loadtest.py`, public spec §7) reports as the server's move handling, beside the end-to-end reply time it measures itself; no other message carries it, and the play page ignores it. It reveals nothing of the round, so ticket 21's rule (the server does not send what the page must hide) still holds.

## Considered options

- **NiceGUI** wrapping the same board as a Vue component: the settings and progress pages would be pure Python, but v1 has one settings page and one reset button, not enough to pay for a component layer between the socket and the board.
- **Reflex, Streamlit, Panel, HTMX with server-rendered SVG**: all put a rerun or a request between the drop and the board's reaction, or lack drag input; ruled out by the research (docs/research/web-board-stack.md).
- **cm-chessboard** (MIT): licence-neutral and sufficient, but the learner already knows the Lichess board, and the GPL adds no obligation python-chess had not already imposed for a local, or openly published, tool.
- **chess.js in the browser**: zero-latency legality, but a second chess implementation that could disagree with the server, for a millisecond it does not need on localhost.
- **HTTP fetch per move**: easier to curl, but a round is a stateful multi-exchange conversation and the socket lets the server push.
- **Client holds the sampled branch**: fastest possible loop, ruled out by ADR 0002's server-authoritative thin client.
- **Single active round shared by all tabs**: stricter, makes a stale tab a nuisance for nothing.
- **CDN assets, npm build**: the app must run offline (ADR 0002); one library does not need a bundler.

## Consequences

- Ticket 10 (play-loop prototype) is unblocked and builds on this stack: chessground, the four socket messages, `next` from the client, animation at most 100 ms. It decides the reveal delay and what a miss looks like, not the wire.
- The spec carries the message schemas, the latency numbers and the CLI surface as written here.
- A hosted or closed-source deployment is doubly ruled out, by ADR 0002 and by the GPL on both board and server library.
- Attribution for the cburnett piece set and the chessground licence notice are part of the v1 deliverable (README, LICENSE).
