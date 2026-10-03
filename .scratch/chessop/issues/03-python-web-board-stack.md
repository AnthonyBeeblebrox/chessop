# Stack: which Python web stack gives a fast interactive board with the least friction?

Type: research
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

What are the realistic options for a Python web app that renders an interactive chess board and needs a fast play loop: FastAPI/Flask + a JS board (chessground, chessboard.js, cm-chessboard), Python-first UI frameworks (NiceGUI, Reflex, Streamlit, Panel), and HTMX-style server rendering? For each: board-library maturity and licence, move input latency, how state round-trips, deployment simplicity, and single-user vs multi-user fit. Write findings to `docs/research/web-board-stack.md`.

AFK. Fired at charting time.

## Answer

The fast loop (move, instant reply, wrong-move flash, next round) is a client-side loop: every Python-first framework still needs a JS board, and only JS with chess.js (or a server-supplied dests map) can react with zero latency. Least-friction stack: FastAPI + cm-chessboard (MIT, 8.14.0 on 2026-09-01, zero deps, ESM from CDN) + chess.js, one WebSocket per session, python-chess server-side; NiceGUI (FastAPI + socket.io, per-client pages, custom JS components) is the credible Python-first alternative wrapping the same board. chessground (Lichess) is the most polished board but GPL-3.0-or-later requires publishing the site source; chessboard.js is frozen since 2019 and needs jQuery; chessboard2 is unfinished since 2023. Reflex cannot return a value from a drop handler (snapback must be JS); Streamlit reruns per interaction and its only chess component is from 2021; Panel's JSComponent works but adds the Bokeh server for nothing. python-chess chess.svg.board renders in ~0.7 ms (31 KB, 5.4 KB gzipped), so HTMX/SSR is fine as a local prototype, but it has no drag input and pays one RTT per click. Open for the spec: local-only vs hosted, and whether the client holds the sampled branch (zero-latency) or the server decides per move (one RTT). Findings: [web-board-stack.md](../../../docs/research/web-board-stack.md).
