# 01: Walking skeleton: one round from CLI to board

**What to build:** the learner runs `chessop`, the browser opens on the play page, and they play whole rounds against an opponent over a small hand-written graph file: the opponent draws by popularity, each learner move is judged a pass (an edge stored in the graph) or a miss, the round ends with the reveal arrows, and Space/Enter/click on the strip starts the next one. This fixes the on-disk format of the graph file (spec §3.3; compressed JSON or read-only SQLite, implementer's choice) and the WebSocket protocol of spec §8, minus the fields later tickets fill (`forced`, `score`, `explanation` may be null or placeholders). Side is a fair coin for now; no memory, no persistence.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §2, §3.3, §8, §9, §12. The play-loop prototype (`prototype/play-loop/`, variant C) is the reference for feel and holds the chessground copy to vendor.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] Built on the existing uv project (src layout, package `chessop`, console script `chessop`, GPL-3.0-or-later); runtime deps stay FastAPI, uvicorn, Jinja2, python-chess, added with `uv add`
- [x] `chessop` serves on 127.0.0.1:8000, falls back to a free port when 8000 is taken, opens the browser at `/`; `chessop serve --host --port` binds another interface; `--snapshot <path>` chooses the graph file
- [x] A tiny fixture graph file in the chosen format (positions keyed by `Board.epd()`, edges with counts, SAN, child EPD, exact names, canonical order) is loaded into memory at start
- [x] `/` and `/play` render a Jinja2 page plus the app's one hand-written JS module; chessground (brown board, cburnett pieces) vendored with its LICENSE; no Node, no bundler, no CDN
- [x] `/ws` starts a round on connect with `round`; `move` answers `moved` then, at round end, `round_over`; `next` starts a new round (abandoning one in flight); an illegal move or a move with no round in flight gets `{"type": "error", "text": "illegal"}`; promotion auto-queens
- [x] A round-ending `moved` carries empty `dests`; no `moved` carries any reveal; `round_over.reveal` carries the main moves and the learner's move on a miss
- [x] Play page: nothing revealed mid-round; banner with colour badge, board orientation and last exact opening name; at round end green arrows for main moves, red for the learner's miss, the one-line verdict strip under the board; nothing covers the board
- [x] pytest drives whole rounds over `/ws` with the FastAPI test client (pass, miss, `next`, `error`)
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
