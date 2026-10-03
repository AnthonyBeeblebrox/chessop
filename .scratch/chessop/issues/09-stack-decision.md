# Stack: which web framework and board library, given the speed-first play loop?

Type: grilling
Status: resolved
Blocked by: 03, 07
Map: [Chess opening trainer by sampling](../map.md)

## Question

Given the stack findings and the users decision, pick the Python web framework, the board component, and how a move round-trips (WebSocket, HTMX swap, full JS client with a JSON API). Decide the latency budget for 'go fast'. Record as an ADR.

HITL: grill the user.

Inherited from ticket 07 — settled (ADR 0002):

- **Server authoritative.** The repertoire tree, need aggregates and position records live in the server process; the browser is a thin client that submits moves and renders. A move round-trips client to server to client; no client-side store or sync.
- Every round end and every miss is written through to SQLite before the next round.
- **Deployment**: one command starts the server bound to localhost and opens the browser; a flag binds another interface for a LAN device. No server authentication, no Docker, no hosting. This ticket owns how that launch command and packaging look.
- Several tabs may be open; their rounds are serialised by the server.

Inherited from ticket 08 — settled (ADR 0003):

- The opening tree is a read-only snapshot file shipped as package data; the server loads one band's trie (order of ten thousand nodes) into memory at start. No data access and no network call sits on the move round trip.

## Comments

**Round 1** (eight questions): FastAPI over NiceGUI; board; WebSocket per tab over fetch or HTMX; server-supplied dests over chess.js; the latency budget; vendored assets over CDN or npm; uv project with a `chessop` console script; one round per tab with serialised commits. The user agreed with every recommendation except the board: cm-chessboard was recommended on licence grounds, the user asked for the Lichess board they are used to. Answered that chessground's GPL adds nothing for a local tool and python-chess already binds the server to GPL-3.0+; chessground chosen, project GPL-3.0-or-later.

**Round 2** (six questions): Jinja2 pages plus one JS module; the four-message socket protocol with `next` from the client; auto-queen promotion; a dropped socket abandons the round; pytest plus the FastAPI test client over the socket, no browser automation; vendored Lichess defaults, no theme picker. Agreed in one word. Frontier empty after round 2.

## Answer

Recorded as **ADR 0004**, `docs/adr/0004-web-stack.md`. No glossary change: nothing here is domain language.

- **FastAPI** (uvicorn, one async worker), **Jinja2** pages and plain forms for everything but play, exactly one hand-written JS module on the play page. No client framework, bundler or Node.
- **chessground** is the board, vendored with its base CSS, brown board and cburnett pieces (attributed); Lichess defaults, no theme picker. The project is **GPL-3.0-or-later**, which python-chess already required.
- **No chess logic in the browser**: the server sends FEN, orientation and the legal-destinations map with every position; any legal move may be played, the server judges it.
- **One WebSocket per tab**: `move` and `next` up; `round`, `moved` (verdict, reveal, reply, new position) and `round_over` down. The client asks for the next round, so the reveal delay is ticket 10's call.
- **One round per tab**, round-end commits under one lock; a dropped socket abandons the round unrecorded. Promotion auto-queens and is outside the repertoire.
- **Latency budget**: move handling < 10 ms p95, drop to reply < 100 ms, next round < 200 ms after `next`, animation ≤ 100 ms and settable to zero, no loading indicator in the loop.
- **Packaging**: uv project, Python ≥ 3.12, `chessop` serves on localhost:8000 (free-port fallback) and opens the browser, `chessop serve --host --port` for LAN, installed by `uv tool install` from the repo.
- **Tests**: pytest for model and repertoire, the FastAPI test client through whole rounds over the socket, no browser tests.

### Handed to other tickets

- **Ticket 10**: unblocked; inherits chessground, the message set, `next` from the client and the animation cap. Decides the reveal delay, the miss feedback and whether "relearning" is shown.
- **Spec**: message schemas, latency numbers, CLI surface, LICENSE and attribution are v1 deliverables.
