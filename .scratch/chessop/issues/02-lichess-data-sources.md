# Lichess data: which API / dataset gives us the main-opening tree with move frequencies?

Type: research
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

Which Lichess resources can supply an opening tree with per-move popularity: the Opening Explorer API (masters, lichess, player endpoints), the `lichess-org/chess-openings` ECO TSV repo, the full database dumps, and the `berserk` Python SDK? For each: endpoint shapes, rate limits, auth needs, licence, offline vs live suitability, and how deep (plies) and how wide the tree is at various popularity cut-offs. Also note how `python-chess` can read/represent these. Write findings to `docs/research/lichess-data.md`; save any downloaded TSVs or API docs into `refs/lichess/`.

AFK. Fired at charting time.

## Answer

- Only the Opening Explorer API (`explorer.lichess.org/{masters,lichess,player}`) returns per-move popularity directly (counts per move, `opening` names, filters by rating band/speed/date), one position per request; since 3 Mar 2026 every request needs an OAuth token (personal token is enough for one user), 25 req/min, 50 plies max — anonymous calls get 401 (verified with curl).
- `lichess-org/chess-openings` is names only: 3,810 CC0 lines (eco, name, pgn; dist/ adds uci+epd), 1–36 plies, mean 9.7, 149 families; it labels nodes, it does not weight them.
- The CC0 database dumps (8.13 B standard rated games, one `.pgn.zst` per month, 17.8 MB in 2013-01 to 30.1 GB in 2026-08; ECO/Opening/Elo headers per game) are what the explorer is built from and are the right source for an offline popularity snapshot: 121 k games parse in 6 s; keeping lines played in ≥1 % of games gives ~60–90 nodes and 6–8 plies, ≥0.2 % gives ~300–450 nodes and 10–18 plies, both depending on the rating band.
- berserk 0.14.0 (GPL-3) wraps the three explorer endpoints thinly (dicts), works with `TokenSession`, still uses the old `.ovh` host and has a broken `/master/pgn/` path; a plain `requests` call is equivalent.
- python-chess 1.11.2 (GPL-3) gives the PGN variation tree (`chess.pgn`), EPD/Zobrist position keys, and `chess.polyglot.weighted_choice` as a ready sampler over a Polyglot book — but no Polyglot writer.
- Implication: sample from a local snapshot keyed by position (transpositions merge), pruned by a popularity cut-off per rating band, named via the TSV; use the explorer (with token) only to refresh or extend nodes and to seed from the learner's own games via `/player`.

Findings: [docs/research/lichess-data.md](../../../docs/research/lichess-data.md). Downloads: `refs/lichess/` (indexed in `refs/README.md`).
