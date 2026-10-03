# Lichess data sources for the opening tree

Ticket: [.scratch/chessop/issues/02-lichess-data-sources.md](../../.scratch/chessop/issues/02-lichess-data-sources.md).
Downloaded material: [refs/lichess/](../../refs/lichess/) (indexed in [refs/README.md](../../refs/README.md)).
Researched 2026-09-11; every live observation below was made that day with `curl` from this machine.

## Summary

1. **The Opening Explorer API (`explorer.lichess.org/{masters,lichess,player}`) is the only Lichess resource that returns per-move popularity directly**, one position per request, with `opening` names attached — but since 3 Mar 2026 every request needs an OAuth token, is capped at 25 requests/minute and 50 plies, and anonymous calls return HTTP 401 (verified) [B1][S1][C1].
2. **The `chess-openings` TSVs carry names only, no popularity**: 3,810 lines (eco, name, pgn), CC0, 388 KB, plies 1–36 (mean 9.7); they parse cleanly with python-chess and map 1:1 to distinct EPDs [O1][X1].
3. **The database dumps (CC0, 8.13 billion standard rated games, one `.pgn.zst` per month, 17.8 MB in 2013-01 up to 30.1 GB in 2026-08)** are the raw material the explorer itself is built from; every game carries `WhiteElo/BlackElo`, `ECO`, `Opening`, and a speed in `Event` [D1][E1].
4. **Measured on the 2013-01 dump (121,332 games, 6 s to parse)**: keeping only lines played in ≥1 % of games gives a 60-node tree 6 plies deep; ≥0.1 % gives 661 nodes and 10 plies; restricting to games where both players are ≥1800 stretches the same cut-offs to 8 and 19 plies [X2].
5. **berserk 0.14.0** wraps the three explorer endpoints as thin dict-returning calls (`client.opening_explorer.get_lichess_games/get_masters_games/get_player_games`), works with `TokenSession`, still points at the old `explorer.lichess.ovh` host, and its `get_otb_master_game` hits a wrong path (`/master/pgn/`, 404) [K1][C2].
6. **python-chess 1.11.2** reads PGN into a variation tree (`chess.pgn`), reads Polyglot books with `weighted_choice` (exactly "sample a reply by popularity"), keys positions with `Board.epd()`/`zobrist_hash`, but has **no Polyglot writer** [P1][P2][X1].
7. For a "speed first" drill loop the live API cannot be in the hot path (a 1,000-node repertoire is 40 minutes of requests); the fit is **offline snapshot for sampling + TSV for names + explorer (with token) for on-demand refresh and for seeding from the learner's own games**.
8. Licences: data CC0 (dumps, TSV); explorer server AGPL-3; berserk and python-chess GPL-3.0-or-later — relevant to the stack/licence decision.

## 1. Opening Explorer API

### Hosts, auth, limits

- Canonical host is now **`https://explorer.lichess.org`** (spec commit `ac27c30`, 2026-03-03, changed every `explorer.lichess.ovh` URL and turned `security: []` into `security: - OAuth2: []` on all four endpoints) [S1][S2]. The old `.ovh` host still answers (same 401 behaviour observed).
- Thibault's blog post of 3 Mar 2026 [B1]: "Anonymous requests to the opening explorer are no longer allowed." / "If you use the explorer through the API, you now need to add an oauth token to each explorer request." / "you can send 25 requests per minute, which should be plenty enough. The max depth remains 50 plies." / "7.5 Billion games indexed, 3 Million OTB master games". Reason: a residential-IP DDoS ("each explorer request causes reads in a dataset of several terabytes"). The lila commit `cc9d8d9` says the same: "using the opening explorer now requires being logged in because we can't defend anon requests against DDoS" [B2].
- `OAuth2: []` means any token, no scope. Simplest: a personal API token from <https://lichess.org/account/oauth/token>, sent as `Authorization: Bearer <token>`; the Lichess auth guide says "Never use this for an app that will be used by multiple users" — a hosted multi-user app must use "Login with Lichess" (authorization-code / PKCE) instead [A1].
- General rate rule in the API intro: "Only make one request at a time. If you receive an HTTP response with a 429 status, you have exceeded one of the rate limits. In most cases, waiting one minute before retrying will be sufficient" [S3].
- **Observed 2026-09-11** (no token): `GET /masters`, `/lichess`, `/player` on both hosts → `HTTP/2 401`, nginx "Authorization Required" body, with CORS `Access-Control-Allow-Origin: *` (saved: `refs/lichess/explorer-401-no-token.headers`). A bogus bearer token also gets 401. `GET /masters/pgn/aAbqI4ey` returned **200 and a full PGN without a token** (saved: `refs/lichess/masters-pgn-sample.pgn`, Carlsen–Chadaev, Wch Blitz 2012) although the spec marks it OAuth2 too [C1]. I had no token available, so response bodies below come from the spec's own example files, which are real captures [S4].
- The forum thread that reacted to the change adds nothing official beyond the blog and commit [B3]. The February 2026 "all requests return 429" outage reports predate the auth change and were the DDoS itself [B4].

### Endpoints and parameters (from the OpenAPI tag files [S2])

| Endpoint | Purpose | Parameters (default) | Response |
|---|---|---|---|
| `GET /masters` | OTB master games ("OTB games of 2200+ FIDE-rated players from 1952 to …" is the UI string; `since` defaults to 1952) [L1] | `fen` (X-FEN), `play` (comma-separated UCI moves from `fen`), `since` (year, 1952), `until` (year), `moves` (12), `topGames` (15, max 15) | JSON `OpeningExplorerMasters` |
| `GET /lichess` | Aggregated rated Lichess games | `variant` (standard), `fen` (X-FEN or EPD), `play`, `speeds` (ultraBullet…correspondence), `ratings` (groups `0,1000,1200,1400,1600,1800,2000,2200,2500`, each spanning to the next), `since` (month, `1952-01`), `until` (`3000-12`), `moves` (12), `topGames` (4, max 4), `recentGames` (4, max 4 "or 8"), `history` (false) | JSON `OpeningExplorerLichess` |
| `GET /player` | One Lichess player's games, indexed on demand | `player`, `color` (required), `variant`, `fen`, `play`, `speeds`, `modes` (casual,rated), `since`, `until`, `moves`, `recentGames` (8, max 8) | **ND-JSON stream**: "Will start indexing on demand, immediately respond with the current results, and stream more updates until indexing is complete… Will index new games at most once per minute" |
| `GET /masters/pgn/{gameId}` | PGN of one master game | path `gameId` | `application/x-chess-pgn` |

`play` is "Required to find an opening name, if fen is not an exact match for a named position" — i.e. the explorer resolves names by walking the move history against the `chess-openings` data [S2][R1].

### Response shape (schemas [S5], examples [S4])

Common top level: `opening` (`{eco, name}` or null), `white`, `draws`, `black` (game counts from this position), `moves[]`, `topGames[]`; `/lichess` adds `recentGames[]` and optional `history[]` (`{month, white, draws, black}`); `/player` adds `queuePosition`.

Each `moves[]` item: `uci`, `san`, `averageRating`, `white`, `draws`, `black`, `game` (a single game object when the move was played only once, else null), `opening` (name of the position *after* the move, or null). `/player` uses `averageOpponentRating` and adds `performance`. Game objects: `id`, `winner` (`white`/`black`/null), `speed` (lichess/player only), `mode` (player only), `white`/`black` `{name, rating}`, `year`, `month`.

Excerpt from the spec's `/lichess` example (position after `1.d4 d5 2.c4 c6 3.cxd5`), 10 M games at that node:

```json
{"white": 5061745, "draws": 492487, "black": 4458129,
 "moves": [
   {"uci":"c6d5","san":"cxd5","averageRating":1806,"white":4517660,"draws":450366,"black":4016728,"game":null,"opening":null},
   {"uci":"d8d5","san":"Qxd5","averageRating":1662,"white":236785,"draws":17561,"black":170379,"game":null,"opening":null},
   {"uci":"g8f6","san":"Nf6","averageRating":1973,"white":195502,"draws":17425,"black":184987,"game":null,
    "opening":{"eco":"D06","name":"Queen's Gambit Declined: Marshall Defense, Tan Gambit"}}, ...],
 "recentGames": [...], "topGames": [...]}
```

Sizes: the three example bodies are 5.4 KB (`/lichess`, 12 moves + 8 games), 5.3 KB (`/masters`), 2.9 KB (`/player`) [S4]. Per-move popularity = `white+draws+black` of the move divided by the node total; note the doc caveat "more may transpose to resulting position" [R1].

### Depth and width

The explorer is a **per-position** service: it never returns a subtree, so tree depth is whatever you walk (server max 50 plies [B1]) and width is `moves` (default 12, no documented upper bound). Fetching a tree of N nodes costs N requests → **at 25 req/min a 1,000-node repertoire takes 40 min cold**, a 100-node one 4 min. The `ratings`/`speeds` filters let you pick the population the learner will actually face.

### Licence

Server code: AGPL-3 [R1]. The API spec: AGPL-3.0-or-later [S3]. The *data* returned is not licensed explicitly anywhere in the spec; the Lichess games behind `/lichess` are the CC0 dumps [D1]; the OTB masters games' rights are unstated.

## 2. `lichess-org/chess-openings` (ECO TSV)

- Five files `a.tsv`…`e.tsv` (ECO volumes), columns `eco`, `name`, `pgn`; a generated `dist/` adds `uci` and `epd` ("install Python, then `pip3 install chess` and run `make`" or take the CI artifact) [O1]. Also published as Parquet on Hugging Face (`Lichess/chess-openings`, columns eco-volume, eco, name, pgn, uci, epd, img; 3,704 rows as of its May 2026 refresh — slightly behind the repo) [O2].
- Licence: "As a collection of facts, this data set is in the public domain… released under the CC0 Public Domain Dedication" [O1].
- Conventions [O1]: names are `Family: Variation, Subvariation`; "each name has a unique shortest line"; extra entries exist for transpositions; "The suggested way to classify games is to play moves backwards until a named position is found". Live on lichess.org after each scalachess release and in the explorer daily.
- **Measured on today's download** [X1]: 3,810 rows (a 817, b 772, c 1,250, d 614, e 357); all parse with `chess.pgn.read_game`; 3,810 distinct EPDs, no collisions; 3,174 distinct names, 295 of which have more than one line (transposition entries). Ply-depth histogram: 1: 20, 2: 93, 3: 156, 4: 227, 5: 293, 6: 357, 7: 308, 8: 304, 9: 303, 10: 276, 11: 254, 12: 242, 13: 189, 14: 186, 15: 119, 16: 97, 17: 104, 18: 67, 19: 63, 20: 46, 21–36: 126; max 36, mean 9.7. 149 families; largest: Sicilian Defense 391, Ruy Lopez 235, French Defense 212, Queen's Gambit Declined 198, Italian Game 187, English Opening 175, King's Gambit Accepted 137, King's Indian Defense 119, Caro-Kann 110, Nimzo-Indian 99.
- Offline only, no popularity. Its job is naming: label tree nodes (EPD lookup) and define "main openings" as families.

## 3. Database dumps (`database.lichess.org`)

- "Database exports are released under the Creative Commons CC0 license. Use them for research, commercial purpose, publication, anything you like." [D1]
- Standard rated games: **8,130,696,420** games in 164 monthly `.pgn.zst` files, 2013-01 (17.8 MB, 121,332 games) → 2026-08 (30.1 GB, 91,912,325 games); ≈2.57 TB compressed in total; "Expect uncompressed files to be about 7.1 times larger" [D1].
- Content [D1]: `WhiteElo`/`BlackElo` are Glicko-2; "About 6% of the games include Stockfish analysis evaluations" (`[%eval]`); `[%clk]` since April 2017; bots marked `[WhiteTitle "BOT"]`; every game has `ECO` and `Opening` headers and a speed in `Event` ("Rated Blitz game" etc., seen in the 2013-01 file). "ZStandard archives are partially decompressable, so you can start downloading and then cancel at any point"; `zstdcat file.pgn.zst | python script.py` is the suggested pipeline.
- The explorer is built from exactly these files: "Download database dumps from https://database.lichess.org/ … Import (optionally works directly with compressed files)" [R1].
- Also on the page: 6.1 M puzzles CSV with `OpeningTags`, 409 M Stockfish evaluations (JSONL), broadcasts (CC BY-SA 4.0, not CC0), and a link to a third-party "Elite database containing only games by players rated 2400+" [D1].

### Measured: tree width/depth vs popularity cut-off (2013-01 dump) [X2]

Sequence trie (transpositions not merged), first 24 plies, plain SAN tokenizer, 6 s for 121,332 games (41,796 classical, 46,284 blitz, 32,986 bullet, 266 correspondence). Full output in `refs/lichess/dump-2013-01-tree-stats.txt`.

| Keep lines played in ≥ … of games | all games (121,332) | both players ≥1800 (9,525) | both <1500 (19,771) |
|---|---|---|---|
| 10 % | 5 nodes, ply 3 | 6 nodes, ply 2 | 5 nodes, ply 3 |
| 2 % | 28 nodes, ply 5 | 36 nodes, ply 5 | 25 nodes, ply 5 |
| 1 % | 60 nodes, ply 6 | 89 nodes, ply 8 | 55 nodes, ply 5 |
| 0.5 % | 124 nodes, ply 7 | 188 nodes, ply 13 | 114 nodes, ply 7 |
| 0.2 % | 321 nodes, ply 10 | 450 nodes, ply 18 | 282 nodes, ply 9 |
| 0.1 % | 661 nodes, ply 10 | 1,021 nodes, ply 19 | 612 nodes, ply 10 |

Unpruned, the same 121 k games produce 1.94 M distinct sequences to ply 24 — pruning by popularity is not optional. Rating band changes the tree, not just its size: `1.e4 e5` is 27 % of all games but at ≥1800 `1.e4 c5` (14.9 %) leads and `1.e4 e5` drops to 11.7 %; at <1500 `1.e4 e5` is 33.7 % and `1.e3 e5` makes the top six. One month of 2013 is a toy; one *recent* month is 90 M games (30 GB) and needs a streaming pass with an Elo filter and a ply cap — the resulting trie is a few MB.

## 4. berserk (Python SDK)

- PyPI `berserk` 0.14.0, GPL-3.0-or-later, Python ≥3.8 [K2]. `berserk.Client(session=berserk.TokenSession(token))` supplies the bearer token to every request [K3].
- `client.opening_explorer` (source [K1]): `get_lichess_games(variant, position, play, speeds, ratings, since, until, moves, top_games, recent_games, history)`, `get_masters_games(position, play, since, until, moves, top_games)`, `get_player_games(player, color, …, wait_for_indexing=True)` (consumes the ND-JSON stream and returns the last state) and `stream_player_games(...)` (yields each update), `get_otb_master_game(game_id)`. All return the raw JSON as `dict` (typed `OpeningStatistic`); `play` is a list of UCI strings; warnings are logged if `top_games`/`recent_games` ≥ 4.
- Caveats found in source and verified: `EXPLORER_URL = "https://explorer.lichess.ovh"` (old host, still works); `get_otb_master_game` requests `/master/pgn/{id}` — `curl explorer.lichess.org/master/pgn/aAbqI4ey` → 404, `/masters/pgn/…` → 200 [C2]. No rate-limit handling or retry in the client [K3].
- Verdict: convenient but thin; a 20-line `requests` wrapper with the bearer header and a 25/min limiter is equivalent, and avoids the GPL dependency if that matters.

## 5. python-chess

- PyPI `chess` 1.11.2, GPL-3.0-or-later, Python ≥3.8 [P3][P4].
- `chess.pgn` [P1]: `read_game(handle)` → `Game` tree of `GameNode`s (`variations`, `variation(move)`, `add_variation`, `add_main_variation`, `add_line`, `promote/demote`, `mainline()`, `mainline_moves()`, `board()` — O(n), `ply()`, `san()`, `uci()`, `comment`, `nags`, `eval()`, `clock()`); `Game.headers`, `Game.from_board`; fast paths `read_headers(handle)` and `skip_game(handle)`; custom `Visitor`s (`GameBuilder`, `HeadersBuilder`, `BoardBuilder`, `SkipVisitor`) for streaming; `StringExporter`/`FileExporter` to write PGN. It parsed all 3,810 TSV lines. For dumps, full `read_game` per game is far slower than a tokenizer-plus-`Board.push_san` or a custom Visitor; the 6 s figure above used no board at all.
- `chess.polyglot` [P2]: `open_reader(path)` → `MemoryMappedReader` with `find(board, minimum_weight=1, exclude_moves=[])`, `find_all(...)`, `choice(...)`, **`weighted_choice(board, exclude_moves=[], random=None)`** — random reply weighted by entry weight — and `Entry(key, raw_move, weight, learn, move)`; `zobrist_hash(board)`. Book entries are keyed by position, so transpositions merge for free; weights are 16-bit, so counts must be rescaled. **No writer exists** (`dir(chess.polyglot)` has no write/Writer symbol) [X1]; the 16-byte big-endian entry format (u64 key, u16 move, u16 weight, u32 learn) is simple enough to write with `struct` if a `.bin` book is wanted.
- Position identity for the tree: `Board.epd()` (what `chess-openings/dist` uses) or `zobrist_hash` (what Polyglot uses); both drop move counters, so `fen` from the explorer (`X-FEN or EPD` accepted) round-trips.

## Comparison

| | Live explorer API | Snapshot from a dump month | `chess-openings` TSV |
|---|---|---|---|
| Per-move popularity | yes, exact, filterable by rating/speed/date | yes, computed by us; any filter we like | **no** |
| Opening names | yes (`opening` on node and per move) | via `ECO`/`Opening` headers per game, or EPD lookup in the TSV | yes, that is all it has |
| Depth / width | 50 plies max, `moves` per node (default 12); N nodes = N requests | whatever we keep; measured: ≥0.2 % cut-off ≈ 300–450 nodes, 10–18 plies | 3,810 named lines, 1–36 plies, mean 9.7 |
| Auth | OAuth token on every request (personal token for a single user; Login-with-Lichess for many) | none | none |
| Rate / cost | 25 req/min, one at a time; 401 without token | one-off download: 17.8 MB (2013-01) … 30.1 GB (2026-08); stream + filter, seconds to minutes per 100 k games | 388 KB |
| Freshness | live (explorer indexes daily) | frozen at the chosen month | repo HEAD |
| Offline | no | yes | yes |
| Licence | server AGPL-3; data unstated (Lichess side is CC0) | CC0 | CC0 |
| Python | berserk 0.14.0 (GPL) or plain `requests` | python-chess / `zstandard` / own tokenizer | `csv` + python-chess for EPD |

## Implications for the trainer

1. **Sampling must run off a local snapshot.** "Speed first" means a reply in milliseconds; the explorer is 25 req/min with a token, so it can only fill a cache, never sit in the play loop. Build the opening trie once (dump month + Elo filter + ply cap, or crawl the explorer within the limit) and sample from it locally — `chess.polyglot.weighted_choice` is exactly that operation if the snapshot is written as a Polyglot book, otherwise a dict/SQLite trie keyed by EPD.
2. **Key nodes by position (EPD/Zobrist), not by move sequence** — the explorer, Polyglot and `chess-openings/dist` all do; it settles the "Transpositions" open point from the map for the data layer (credit goes to the position, whichever path reached it).
3. **Prune by popularity cut-off per rating band.** The 2013-01 numbers give a feel: ≥1 % of games ⇒ ~60–90 nodes, 6–8 plies; ≥0.2 % ⇒ ~300–450 nodes, 10–18 plies. "Main openings" at v1 is plausibly the ≥0.5–1 % tree of the learner's rating band, extended on demand at chosen leaves via the explorer.
4. **Names come from the TSV**, both as labels and as the definition of a "family" (149 of them); the explorer's `opening` field uses the same data so the two agree.
5. **Rating band is a first-class parameter** (`ratings` groups on the API, `WhiteElo/BlackElo` on dumps): the opponent's replies should be sampled from players the learner actually meets, not from masters.
6. **Token handling decides the deployment shape.** Local-only tool: the learner pastes a personal token once. Hosted multi-user: "Login with Lichess" OAuth (PKCE), which also unlocks `/player` for seeding branch stats from the learner's own games (indexes on demand, streams).
7. **Licences for the stack decision**: data CC0; python-chess and berserk GPL-3.0-or-later — fine for a personal/hosted service, but a distributed binary would inherit GPL terms. berserk is optional; python-chess is not.
8. **Refresh strategy** can be lazy: a snapshot month goes stale slowly (opening fashion moves in years); a nightly explorer crawl of the repertoire's ~500 nodes fits in 20 minutes under the limit.

## Sources

Primary (downloaded copies in `refs/lichess/`):

- [S1] lichess-org/api commit `ac27c30` "update explorer/tablebase doc", 2026-03-03 — host `.ovh`→`.org`, `security: OAuth2: []` on all explorer endpoints. <https://github.com/lichess-org/api/commit/ac27c30086a66ba6bd00b399341e5e6ca0906eec> (`openapi-commit-ac27c30-explorer-auth.diff.txt`)
- [S2] Explorer endpoint specs: `doc/specs/tags/openingexplorer/{masters,lichess,player,masters-pgn-gameId}.yaml` at <https://github.com/lichess-org/api/tree/master/doc/specs/tags/openingexplorer> (`openapi-explorer-*.yaml`)
- [S3] Lichess API reference root spec (rate limiting, authentication, OAuth2 scheme) <https://raw.githubusercontent.com/lichess-org/api/master/doc/specs/lichess-api.yaml> (`lichess-api-openapi.yaml`)
- [S4] Spec example responses `doc/specs/examples/openingExplorer-{masters,lichess,player}.json.yaml` (`openapi-example-*.yaml`)
- [S5] Response schemas `doc/specs/schemas/OpeningExplorer*.yaml` (`openapi-schema-*.yaml`)
- [B1] thibault, "The opening explorer now requires authentication", 3 Mar 2026 <https://lichess.org/@/thibault/blog/the-opening-explorer-now-requires-authentication/FSWh9Zg3> (`blog-thibault-explorer-requires-authentication.html`)
- [B2] lila commit `cc9d8d9` "using the opening explorer now requires being logged in because we can't defend anon requests against DDoS" <https://github.com/lichess-org/lila/commit/cc9d8d92302f428ed2ce745a421b7f0e05ce2a0c>
- [B3] Forum: "why this change? Using the opening explorer now requires being logged in" <https://lichess.org/forum/lichess-feedback/why-this-change-using-the-opening-explorer-now-requires-being-logged-in> (`forum-explorer-requires-login.html`)
- [B4] lila issue #19610 "Complete outage of explorer.lichess.ovh – all requests return 429", Feb 2026 <https://github.com/lichess-org/lila/issues/19610>
- [A1] Lichess OAuth examples README (personal token vs Login with Lichess) <https://github.com/lichess-org/api/blob/master/example/README.md> (`lichess-api-example-README.md`); token page <https://lichess.org/account/oauth/token>
- [R1] lila-openingexplorer README (server, import from dumps, `/player` query/response documentation, AGPL) <https://github.com/lichess-org/lila-openingexplorer> (`lila-openingexplorer-README.md`)
- [L1] lila `translation/source/site.xml`, `masterDbExplanation` = "OTB games of %1$s+ FIDE-rated players from %2$s to %3$s" <https://github.com/lichess-org/lila/blob/master/translation/source/site.xml>; `minYear = 1952` in `ui/analyse/src/explorer/explorerConfig.ts`
- [O1] lichess-org/chess-openings README and `a–e.tsv` <https://github.com/lichess-org/chess-openings> (`chess-openings-README.md`, `chess-openings-{a..e}.tsv`)
- [O2] Hugging Face dataset card `Lichess/chess-openings` <https://huggingface.co/datasets/Lichess/chess-openings>
- [D1] Lichess open database page <https://database.lichess.org/> (`database-lichess-org.html`)
- [E1] `lichess_db_standard_rated_2013-01.pgn.zst` <https://database.lichess.org/standard/lichess_db_standard_rated_2013-01.pgn.zst> (17.8 MB; kept in `/tmp/lichessdump/`, not in refs)
- [K1] berserk `berserk/clients/opening_explorer.py` <https://github.com/lichess-org/berserk/blob/master/berserk/clients/opening_explorer.py> (`berserk-opening_explorer.py`)
- [K2] PyPI `berserk` metadata <https://pypi.org/pypi/berserk/json>
- [K3] berserk API docs <https://berserk.readthedocs.io/en/master/api.html> (`berserk-api.html`); README (`berserk-README.md`)
- [P1] python-chess `chess.pgn` docs <https://python-chess.readthedocs.io/en/latest/pgn.html> (`python-chess-pgn.html`)
- [P2] python-chess `chess.polyglot` docs <https://python-chess.readthedocs.io/en/latest/polyglot.html> (`python-chess-polyglot.html`)
- [P3] PyPI `chess` metadata <https://pypi.org/pypi/chess/json>
- [P4] python-chess LICENSE (`python-chess-LICENSE.txt`); berserk LICENSE (`berserk-LICENSE.txt`)

Own measurements (reproducible, this repo):

- [C1] `curl -D - https://explorer.lichess.org/masters?play=e2e4` → 401 (`explorer-401-no-token.headers`); `curl https://explorer.lichess.ovh/masters/pgn/aAbqI4ey` → 200 (`masters-pgn-sample.pgn`)
- [C2] `curl -o /dev/null -w '%{http_code}' https://explorer.lichess.org/master/pgn/aAbqI4ey` → 404; `/masters/pgn/aAbqI4ey` → 200
- [X1] TSV parse/EPD/ply statistics and `dir(chess.polyglot)` check, python-chess 1.11.2 in a uv venv (`/tmp/chessvenv`)
- [X2] 2013-01 dump trie statistics (`dump-2013-01-tree-stats.txt`)
