# Play-loop prototype (ticket 10) — THROWAWAY

Three variants of one fast round, on the real wire of ADR 0004 (chessground, one WebSocket, `move`/`next` up, `round`/`moved`/`round_over` down) with the sampler of ADR 0001 (half-life records per position and colour, popularity x mean-need opponent with Boltzmann-Gumbel exploration, forced exploration, side drawn by need). Nothing persists: the memory lives in the server process.

## Run

```
cd prototype/play-loop
uv run python build_tree.py /tmp/lichessdump/lichess_db_standard_rated_2013-01.pgn.zst tree.json   # only if tree.json is missing
uv run python server.py
```

Then open <http://localhost:8010/prototype/play> (variant C, the winner, is the default). The pink pill at the bottom (and the ← → keys) switch variants; the URL is shareable. `state` in the pill opens the raw memory (records, needs, half-lives, round log).

| variant | what it tests |
| --- | --- |
| `A` Bare board | Board only. Reveal = green arrows drawn the instant the reply lands. Miss = red border + red arrow for the played move + green arrows for the main moves, then **auto-restart after 900 ms**. Success auto-restarts after 250 ms. Forced exploration is a two-second toast. Relearning is not shown. |
| `B` Ledger | Board + a running move ledger. After every learner move the accepted set appears as chips (the played move green, a forced-out move marked ✕) with the pass kind (`counted` / `sure` / `relearning`). Miss = red row, played move struck through, and the round **waits** for Space / Enter / click. Nothing auto-advances. |
| `C` Pure recall (**winner**, amended by the learner's reaction) | **No reveal mid-round**: the reply just appears. A big banner names the side, the opening and any forced exploration ("not e5 this time"). When the round ends the main moves are drawn as green arrows with the played move red (yellow when it was the set-aside move) and a verdict strip under the board names them; **Space** (Enter, click) starts the next round after every outcome. |

Forced exploration: fires only when one main move is strictly better known; playing the set-aside move ends the round as `forced`, neither pass nor miss.

Knobs: `GET /forced/1` makes forced exploration fire at every eligible turn (default 0.1), to see the yellow set-aside arrow quickly. `&anim=0` sets piece animation to zero (default 100 ms). `GET /speed/3600` makes the memory clock run 3600x so forgetting shows within a session (default 1). `&demo=pass|miss` and `&hold=1` exist only for the screenshots in `shots/`.

Tree: `tree.json` is the 1800+ band of the 2013-01 dump (5,017 games after excluding bullet), 0.2 % cut-off, top-3 replies per position: 289 nodes, 94 leaf paths, 195 learner positions. `drive.py` plays twelve scripted rounds through the socket and prints the message flow and the server's per-move time (0.13 ms mean, 0.43 ms max on this machine).
