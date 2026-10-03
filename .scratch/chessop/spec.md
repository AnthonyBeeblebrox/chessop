# chessop v1: build-ready spec

Status: written by ticket 20 on 2026-09-22 from the six ADRs, their amendments, the resolved tickets and the glossary. Nothing here is decided by this document: every section names the source it restates, gives its gist and the numbers, and links the source for the reasoning. **Where two sources disagree, the later amendment wins**; the disagreements found while writing are listed in [§15](#15-contradictions-found-resolved-by-ticket-21) and the details no source settled in [§16](#16-gaps-decided-by-ticket-21); ticket 21 decided all five on 2026-09-24 and the sections below are edited accordingly. Everything here is final. Ticket 22 (2026-09-24) later capped the build's sample at 150,000 games per band (§2, §3.1, §3.3, §14), and ticket 23 (2026-09-24) moved the opponent's exploration bonus inside the product (§5.3, §13, §17). Ticket 24 (2026-09-24) dropped the named-position prune, so the popularity floor, not the book, ends a branch (§4, §13).

Sources: the glossary [`CONTEXT.md`](../../CONTEXT.md); ADR [0001 sampling rule](../../docs/adr/0001-sampling-rule.md), [0002 persistence](../../docs/adr/0002-persistence.md), [0003 snapshot](../../docs/adr/0003-opening-tree-snapshot.md), [0004 web stack](../../docs/adr/0004-web-stack.md), [0005 repertoire rule](../../docs/adr/0005-repertoire-rule.md), [0006 position graph](../../docs/adr/0006-position-graph.md); tickets [05](issues/05-confirm-destination-and-repertoire.md), [06](issues/06-success-rule-and-sampling.md), [07](issues/07-users-and-persistence.md), [08](issues/08-data-source-decision.md), [09](issues/09-stack-decision.md), [10](issues/10-play-loop-prototype.md), [11](issues/11-transpositions.md), [13](issues/13-repertoire-named-variations.md), [14](issues/14-lichess-opening-explanations.md), [15](issues/15-opening-explanations-in-the-drill.md), [16](issues/16-gamification.md), [17](issues/17-pooled-repertoire-size.md), [18](issues/18-pooled-only-main-moves.md), [19](issues/19-progress-view.md), [22](issues/22-capped-month-build.md), [23](issues/23-exploration-bonus-inside-the-product.md); the prototypes `prototype/play-loop/` (ticket 10, variant C) and `prototype/progress-view/` (ticket 19, variant A), both throwaway but the closest existing code to the play loop and the ledger.

## 1. What is being built

A local, single-learner web app that drills chess openings by playing rounds against an opponent sampled from the Lichess opening data of one rating band, keeping a half-life memory per position, steering toward what the learner knows least, and showing one Score for how well they know their repertoire (map Destination; tickets 05, 07).

- **Scope**: single learner, local-first, offline at runtime, both colours in one repertoire, the app choosing the side each round (ticket 05, ADR 0002).
- **Out of scope for v1** (map, "Out of scope"): middlegame or engine analysis, multiplayer, hosting, accounts, sync, streaks, daily goals, milestones, session summaries, seeding from the learner's own Lichess games, evaluation or refitting of the memory model. The round log and the daily score table exist so the last two can be done later without a migration.
- **Vocabulary**: use the glossary's terms and avoid the words it lists under *Avoid* in code, UI text and docs. Learner, Opponent, Round, Rating band, Repertoire, Opening, Book, Snapshot, Position, Branch, Main move, Explanation, Progress view; Success, Pass, Miss, Position record, Recall estimate, Known, Half-life, Relearning pass, Need, Floor, Popularity floor, Forced exploration, Sampling weight, Round log, Score.

## 2. Packaging and CLI

Source: ADR 0004 (packaging), ADR 0002 (data directory, LAN bind), ADR 0003 (build and override).

- A **uv-managed project**, Python 3.12 minimum, one console script `chessop`, installed with `uv tool install` from the repository. Licence **GPL-3.0-or-later** (python-chess and chessground both require it).
- Dependencies at runtime: FastAPI, uvicorn, Jinja2, python-chess, SQLite via the standard library. `zstandard` is build-time only, in the optional extra `chessop[build]`, and the build module is imported only when `build-snapshot` runs (ticket 22). No Node, no bundler, no client framework; all static assets vendored (§12).
- `chessop` (no arguments): serve on `127.0.0.1:8000`, fall back to a free port if 8000 is taken, open the browser at the play page.
- `chessop serve --host <addr> --port <n>`: bind another interface for a device on the LAN; no authentication.
- `--data-dir <path>` on either, or the environment variable `CHESSOP_DATA_DIR`, chooses the data directory; default is the XDG data dir, `~/.local/share/chessop/`. A second person on the same machine uses a different data directory; there is no learner identity.
- `--snapshot <path>`: use this snapshot instead of the packaged one; wins over the package data.
- `chessop build-snapshot --month YYYY-MM [--max-games N] [--book <dir>] [--out <path>]`: §3. `--max-games` (games read) is for developer runs only.
- One process, one async worker, all state in memory, SQLite written through at round end (§7).

## 3. `build-snapshot` and the snapshot files

Source: ADR 0003 with its ticket 13, 11 and 15 amendments; ADR 0006 with its ticket 18 amendment; ticket 14 (fetch facts); ticket 17 (the measured build, `docs/research/pooled-repertoire.md`, whose method section is the reference build procedure).

### 3.1 Input and filters

- Input: a **capped prefix of one recent month** of the Lichess standard rated dump (`lichess_db_standard_rated_YYYY-MM.pgn.zst`, CC0), streamed through a zstandard streaming decompressor; nothing large written to disk. Run by the developer at release time; the learner never downloads a dump.
- **Cap: 150,000 kept games per band** (ticket 22, ADR 0003 amended). The dump is read from its start; once a band holds 150,000 games that passed the filters, its further games are dropped; reading stops when every band is full or the month ends. A whole month does not fit in memory (about 400 GB of trie); the cap is ticket 17's sample size, so its numbers stay the sanity bounds (a release build reads about 5–6 % of the file, ~6 GB peak).
- Game filters, fixed: both `WhiteElo` and `BlackElo` present and numeric; both players inside the **same** band; no `WhiteTitle`/`BlackTitle` of `BOT`; `Event` speed not Bullet or UltraBullet; blitz, rapid, classical and correspondence pooled.
- **Five bands**, lower bound inclusive: below 1200, 1200–1500, 1500–1800, 1800–2100, 2100 and above.
- The book: the Lichess `chess-openings` TSV files (`a.tsv`…`e.tsv`, 3,810 rows: `eco`, `name`, `pgn`, `uci`, `epd`), read from `--book <dir>` (default: the copy under `refs/lichess/`); the commit of the copy is recorded in the metadata. A position is **exactly named** when its EPD equals a row's `epd`. The **family** of a name is the part before the first colon (`Sicilian Defense: Najdorf Variation` → `Sicilian Defense`).

### 3.2 Build procedure (per band)

1. Walk every game to **ply 36**, building a move-sequence trie; key every node by `python-chess` `Board.epd()` (placement, side to move, castling, en passant only when a capture is legal). Games with a SAN token python-chess rejects: drop the rest of that game, count it.
2. **Pool by position**: a position's count is the sum over every trie node with its EPD (a game visiting a position twice is pooled twice); a (position, move) edge's count likewise. The **canonical order** of a position is its most popular trie node's path (ties: first seen); for an exactly-named position also store the book's own line (`uci` of the row).
3. Keep every position whose pooled count clears the **storage cut-off, 0.02 % of the band's games** (unrounded threshold, `count >= 0.0002 * N`), and every edge between kept positions whose pooled count clears it.
4. **Guarantee a DAG**: add edges in BFS order from the start position; an edge that would close a cycle over the edges already in is dropped (the shorter path wins) and counted. Ticket 17 measured 0 dropped at 1800–2100 and 1500–1800 on 2026-08.
5. **Diagnostics** printed per band (ticket 18): games kept and dropped per filter, positions and edges stored, dropped-cycle edges, **diffuse traffic** (positions and edges whose largest single move order is below the storage cut-off), and, after applying the default load rule of §4, the repertoire's size (positions, edges, branches, leaves, max depth, book lines covered) so a new month can be checked against the expected size of §4 (ticket 24's numbers). The runtime never reads the diagnostics.
6. **Explanations** (ticket 15, ADR 0003 ticket 15 amendment): for every stored position in every band, build the Wikibooks title from the book's own line (named positions) and from the canonical order: `Chess Opening Theory/1. e4/1...c5/2. Nf3` (`N. SAN` for White, `N...SAN` for Black, `+ # ! ?` stripped, at most 30 plies). Query `https://en.wikibooks.org/w/api.php` for wikitext, 50 titles per request, `redirects=1`, `maxlag=5`, requests in series, a descriptive `User-Agent` with contact (`chessop/<version> (<contact>) python-requests/<v>` or equivalent; a generic one gets HTTP 403). Store each page once. Convert wikitext to plain-text paragraphs: drop the `{{Chess Opening Theory/Position}}` template, the `== N. move ==` heading, the "Theory table", "All possible replies" / "responses" and "External links" sections, references, links' markup, empty paragraphs and the conventions line, the way Lichess's `transformWikiHtml` does (`docs/research/opening-explanations.md` §1b). Keep fair-use quotations and any attribution notation a page carries. The **lead** is the prose before the first remaining sub-heading, capped at a few hundred characters. English Wikibooks only.

### 3.3 Files

Two files, shipped as package data, read-only, both versioned by the same string.

- **Graph file** (CC0 data): metadata (dump month, band set, book commit, build revision, storage cut-off, ply cap 36, the per-band cap, games read and compressed bytes read, per band the games kept and the diagnostics of step 5) and per band: positions `{epd, count, name|null, eco|null, canonical: [uci...], book_line: [uci...]|null}` and edges `{epd, uci, san, count, child_epd}`. Only exact names are stored; never an inherited one.
- **Explanation file** (CC BY-SA 4.0 data), separate so the licences never mix: a licence header naming CC BY-SA 4.0 and stating the text was trimmed; pages `{id, title, url, lead, text}`; a map `epd -> page id` (all bands share it). Positions with no page have no entry.
- **Version string**: `<month>/<band set>/<book commit>/<build revision>`; the learner's database records only this string (§7).
- On-disk format is the implementer's choice (compressed JSON or a read-only SQLite file); the server loads one band's positions and edges plus the explanation map into memory at start. Size guide: at 0.02 % a band stores on the order of ten thousand positions; the explanation file is under 5 MB of text for the whole book.
- **Refresh is release-only**. A learner may run `build-snapshot` themselves; `--snapshot` overrides the packaged file. When the loaded version differs from the one recorded in the database, the repertoire regenerates at start, the learner is told on the play page and the progress view once, and no record is touched.

## 4. The repertoire at load

Source: ADR 0005 (rule) with its ticket 11 and 18 amendments; ADR 0006 (graph, opt-out, canonical order); ADR 0003 (band, floor bounded by the cut-off); ticket 05 (widths, sides).

Inputs from settings (§11): the learner's band (declared rating mapped to a band; 1500–1800 when none), `width_player` P and `width_opponent` O (default 2 and 3, the learner's width lowered from 3 on 2026-09-24; 1 and 3 is "strict recall"), the **popularity floor** f (default 0.02 % of the band's games, never below the storage cut-off), the **share** s (default 5 %), the opted-out openings (families).

Procedure, run at start and again whenever any of those settings changes (in memory, well under a second on ~10k positions):

1. Load the band's positions and edges. `k = max(P, O)`.
2. At every position, the **main moves** are, among the edges whose pooled count clears f: the top-`k` by count (ties: count descending, then SAN descending, the order the measurements used) plus every further edge holding at least s of the position's pooled count. All on pooled counts; no per-order rule of any kind.
3. **Opt-out**: remove every position whose exact name's family is opted out.
4. **Reach**: keep only what the start position reaches over main moves. Repeat 3–4 until stable. There is no named-position prune (ticket 24, ADR 0005 amended): a branch runs until no move at its end clears the floor.
5. A main move whose child is not in the graph after 4 (unreachable, or never stored: in practice only an edge the build dropped) is a **stub**: it stays a main move for the learner (accepted, ends the round as a success with a pass on the position it was played from) and is never drawn by the opponent.
6. **Learner accepted set** at a learner position: the top-P main moves by count plus the share moves (stubs included). **Opponent drawable set** at an opponent position: the top-O main moves plus the share moves, minus stubs. With P = O both sets are the main moves.
7. A **leaf** is a position with no kept (non-stub) main move. A **learner position** is one where the learner is to move, i.e. the side to move in its EPD is the learner's colour, and which is not a leaf; the same graph serves both colours. A leaf with the learner to move is never drilled (the round ends on reaching it, §5.3), so it holds no record and is left out of the aggregates, the Score, the side draw and the never-passed list (ticket 21).
8. A **branch** is one path from the start to a leaf; a position reached by several orders is one position with one record and one reveal.
9. Names: the graph carries only exact names. During a round the banner shows the last exact name seen on the path walked; outside a round (progress view, explanation lookup) a position's name and family are inherited along its **canonical order** (ticket 19's prototype rule: the nearest exactly-named position that is a prefix of the canonical order), and positions at ply 0 and 1 form the "First moves" group.

Expected size on the packaged 2026-08 snapshot at the defaults (ticket 24): 1800–2100 about 3,074 positions, 3,432 edges, 1,052 leaves, 21 plies deep, 22 % of positions exactly named, no stubs; 1500–1800 about 2,695 positions, 3,030 edges, 1,043 leaves, 17 plies deep. (Ticket 17's figures, 1,104 positions and 17 plies at 1800–2100, were measured with the prune.) Tests may use these as sanity bounds for the build, not as exact targets.

## 5. Memory model and sampling rule

Source: ADR 0001 with its ticket 10, 13, 11, 16, 21 and 23 amendments; ticket 06 (parameters); ticket 05 (widths, forced exploration invariant). The prototype `prototype/play-loop/server.py` implements it on a tree and is the reference for feel, not for the DAG details.

### 5.1 Position record

One record per learner position, keyed by EPD (colour is the side to move inside it): counted passes `s`, misses `f`, time of the last pass `t_last` (null if never passed), relearning mark `relearn`.

- Half-life `h = clip(h0 * 2^(s - f), h_min, h_max)`.
- Recall estimate `R = 2^(-(now - t_last) / h)`; `R = 0` when never passed.
- Need `u = max(floor, 1 - R)`.
- **Pass** at a position (learner produced an accepted move, first try, that round): if `relearn` is set, clear it and set `t_last = now`, not counted (a *relearning pass*); else if `R >= sure` at that moment, set `t_last = now` only (a *sure* pass); else `s += 1`, `t_last = now` (a *counted* pass).
- **Miss** (learner produced a move outside the accepted set): `f += 1`, `relearn = true`; the clock is untouched. Charged to that position alone.
- **Forced outcome** (learner played the set-aside move): the record is untouched.
- Passes and misses of a round are judged at the moment of each move (the pass kind depends on `R` then) and applied to the store at round end in one transaction (§7); a round that does not end (socket dropped, process killed, repertoire regenerated under it) applies nothing.

### 5.2 Aggregates

- **Weight of a learner position** for aggregation: its pooled snapshot count `count(p)` (the weighting ticket 16 fixed for the Score, "the same root aggregate the opponent memoises").
- **Mean need below an edge** `m` from position `q` to child `c`: `mean_need(m) = sum(count(p) * u(p)) / sum(count(p))` over the learner positions `p` in the set of positions reachable from `c` over kept (non-stub) main moves, `c` included if it is a learner position, each position once (it is a DAG: do not sum children's sums, or a shared descendant is counted twice; memoise the descendant set or the pair of sums per position and invalidate the memo of every ancestor of a position whose record changed). If the set is empty (a stub, a move onto a leaf, nothing drillable below), `mean_need(m) = floor`: nothing left to learn below it, so forced exploration sets such a move aside first and the opponent weights it by its popularity times the floor (ticket 21).
- **Per-colour need at the root**: `need_white = sum(count(p) * u(p))` over White-to-move learner positions of the scoped repertoire, likewise `need_black`.
- **Times faced** `faced(m)`: how many rounds the opponent has played edge `m`; rebuilt from the round log's paths at start, kept in memory, counted when the opponent plays the edge.

### 5.3 The round

1. **Side**: `p_white = clip(need_white / (need_white + need_black), side_floor, 1 - side_floor)`; draw. When both needs are 0 use 0.5.
2. From the start position, alternate. At an **opponent position** `q` with drawable set `M`: `pop(m) = count(m) / sum(count(m') for m' in M)`; `weight(m) = pop(m)^alpha * (mean_need(m) + C / sqrt(1 + faced(m)))`; draw `m` with probability proportional to `weight(m)`. No noise term and no clamp: the draw is the randomness and every weight is at least `pop * floor > 0` (ticket 23, ADR 0001 amended; the prototype's added Gumbel noise swamped popularity). With no history every weight is `pop * (1 + C)`, so this is exactly the band's opponent restricted to the repertoire.
3. At a **learner position** `p` with accepted set `A`, `|A| >= 2`: with probability `forced_rate`, compute `mean_need(a)` for each `a` in `A`; if the lowest is **strictly** below the second lowest, set aside the lowest for this turn and announce it (§8, §9). Ties, and positions never seen, force nothing. When P = 1 there is nothing to set aside: `forced_rate` is treated as 0 (ticket 05's invariant).
4. The learner may play any **legal** move (auto-queen on promotion). If it is in `A` minus the set-aside move: pass; continue to the child, or end the round as a **success** when the move is a stub or the child is a leaf. If it is the set-aside move: the round ends as **forced**. Otherwise: **miss**, round ends.
5. After a pass at a non-leaf child the opponent draws; if the opponent's reply lands on a leaf the round ends as a **success**.
6. Round end: commit (§7), then wait for `next`.

### 5.4 Parameters (settings, §11)

| name | default | note |
|---|---|---|
| `h0` | 1 day | initial half-life |
| `h_min`, `h_max` | 15 min, 9 months | clip |
| `sure` | 0.9 | sure threshold; also the Known threshold |
| `floor` | 0.1 | need floor |
| `C` | 1.0 | exploration scale: the bonus `C / sqrt(1 + faced)` added to the mean need |
| `alpha` | 1 | popularity exponent |
| `forced_rate` | 0.1 | forced exploration probability |
| `side_floor` | 0.2 | per-colour floor on the side draw |
| target in-session success | 80–90 % | displayed only; nothing self-adjusts |

No cap on never-seen material.

## 6. The Score

Source: ADR 0001, ticket 16 amendment; ticket 16.

- `Score = sum(count(p) * R(p)) / sum(count(p))` over every learner position `p` of the **scoped** repertoire (both colours), `R` the raw recall estimate (0 when never passed; not `1 - u`, so the floor does not cap it). White and Black scores are the same sum restricted to one colour; per-opening scores (progress view) the same sum over the opening's learner positions as grouped in §4 step 9, opted-out openings included for display.
- Shown as a percentage with one decimal. A live number: it decays between sessions like the estimates under it.
- Computed at every round-end commit (it is the same walk as the root aggregate) and on demand for the pages.
- Play page: in the banner permanently; the per-round change on the verdict strip (`+0.4`), none after a `forced` outcome; when a tab opens, the change since the last round played, once, until the first round of that tab ends (`81.3 % (−6.1 since Tue)`), taken from the latest daily score row (§7).
- Rejected variants (do not add): unweighted mean, share of known positions, share of branches playable end to end, a high-water mark, a second number on the play page.

## 7. Persistence and schema

Source: ADR 0002 with its ticket 19 amendment; ADR 0003 (snapshot version); ADR 0001 (round log content); ticket 16 (score).

One SQLite file, `<data-dir>/chessop.sqlite`, the only mutable store. No config file. Forward-only migrations tracked in `schema_version`. Backup is copying the file; no export or import.

| table | columns | notes |
|---|---|---|
| `schema_version` | `version INTEGER` | one row |
| `settings` | `key TEXT PRIMARY KEY, value TEXT (JSON)` | §11's keys, plus `snapshot_version` (the version the repertoire came from) |
| `position_record` | `epd TEXT PRIMARY KEY, passes INTEGER, misses INTEGER, last_pass REAL NULL, relearn INTEGER` | one row per learner position ever passed or missed; colour is inside the EPD; outlives every regeneration; deleted only by a reset |
| `round_log` | `id INTEGER PRIMARY KEY, started_at REAL, ended_at REAL, side TEXT, path TEXT (JSON list of UCI), outcome TEXT (success/miss/forced), end_epd TEXT, plies INTEGER, before TEXT (JSON), snapshot_version TEXT` | append-only, never pruned; `before` maps each visited learner position's EPD to `{passes, misses, relearn, last_pass, R}` as they stood before the round; the position missed or forced is the last learner position of `path` |
| `daily_score` | `day TEXT PRIMARY KEY (local ISO date), score REAL, white_score REAL, black_score REAL, rounds INTEGER, successes INTEGER, updated_at REAL` | upserted at every round-end commit with the scores after the commit and the day's running counts; `rounds` and `successes` exclude forced rounds (ticket 21), which appear only in `round_log` |

- **Round-end commit**, one transaction under one process-wide lock: apply the round's passes and the miss to `position_record`, append to `round_log`, upsert `daily_score`, then refresh the memoised aggregates and the Score. Every round end (success, miss, forced) commits; a round that does not end writes nothing.
- Timestamps are Unix seconds UTC; `day` is the machine's local date.
- **Resets**: "reset all history" (settings, confirmed) deletes every `position_record` row; "reset this opening" and "reset this position" (progress view, confirmed) delete the records of that opening's learner positions (grouped as in §4 step 9) or that position. The round log and daily scores are never deleted.
- History is global: changing the band, widths, floor, share or opt-outs never touches a record; positions that leave the repertoire go dormant and return with their records.
- Settings changes and resets take effect in the running process immediately (regeneration per §4); rounds in flight in other tabs are abandoned unrecorded and those tabs receive a fresh `round`.

## 8. The WebSocket protocol and the latency budget

Source: ADR 0004; ticket 10 (forced, empty dests, reveal at round end); ticket 15 (explanation on the wire); ticket 16 (score on the wire, derived from "in the banner" and "on the verdict strip").

One WebSocket per tab at `/ws`. JSON messages with a `type` field. A socket starts a round on connect and sends `round`; the client asks for every later round with `next`. One round per socket; commits are serialised (§7); a closed socket abandons its round.

Client to server:

```json
{"type": "move", "from": "e2", "to": "e4"}
{"type": "next"}
{"type": "sound", "on": false}
```

`sound` is sent when the learner toggles sound with `m` on the play page; the server writes the `sound` setting (§11) and sends nothing back (ticket 21, ADR 0004 amended). It is valid with or without a round in flight.

Promotion: the client sends `from`/`to` only; the server queens. A `move` that is not legal in the current position, or arrives when no round is in flight, gets `{"type": "error", "text": "illegal"}` and changes nothing; a `next` while a round is in flight abandons it unrecorded and starts a new one.

Server to client:

```json
{"type": "round",
 "side": "white" | "black", "orientation": "white" | "black",
 "fen": "...", "dests": {"e2": ["e3", "e4"], ...},
 "opening": "Sicilian Defense: Najdorf Variation" | null, "eco": "B90" | null,
 "forced": "e5" | null, "forced_uci": "e7e5" | null,
 "score": 71.2, "score_since": {"delta": -6.1, "day": "2026-09-20"} | null,
 "notice": "..." | null}
```

`opening` is the last exact name on the path walked so far (null at the start). `forced`/`forced_uci` name the move set aside at the position now to move at (null otherwise). `score_since` is filled on the first `round` of a socket only, from the latest `daily_score` row before now; `notice` carries the one-time regeneration notice of §3.3 or null.

```json
{"type": "moved",
 "verdict": "pass" | "miss" | "forced",
 "played": {"san": "e5", "uci": "e7e5"},
 "reply": {"san": "Nf3", "uci": "g1f3"} | null,
 "fen": "...", "dests": {...},
 "opening": "..." | null, "eco": "..." | null,
 "forced": "..." | null, "forced_uci": "..." | null}
```

After every learner move. `reply` is the opponent's move (null on `miss`, `forced`, or a success on the learner's own move). `fen`/`dests` describe the position now to move at, after the reply; **a `moved` that ends the round carries an empty `dests`**, which is the client's "round over" signal, and is followed by `round_over` in the same flush. `forced`/`forced_uci` are for the new learner turn. A `moved` carries no reveal: the main moves leave the server only in `round_over` (ticket 21, ADR 0004 amended).

```json
{"type": "round_over",
 "outcome": "success" | "miss" | "forced",
 "reveal": {"epd": "...", "fen": "...", "main": [{"san": "c5", "uci": "c7c5"}, ...],
            "played": {"san": "e5", "uci": "e7e5"} | null},
 "path": ["e2e4", "e7e5", ...], "plies": 9,
 "opening": "..." | null, "eco": "..." | null,
 "explanation": {"lead": "...", "text": "...", "title": "Chess Opening Theory/1. e4/1...c5",
                 "url": "https://en.wikibooks.org/wiki/...", "borrowed_from": "1.e4 c5" | null} | null,
 "score": {"value": 71.6, "delta": 0.4 | null}}
```

`reveal.main` are the main moves (accepted set, stubs included, the set-aside move included) of the revealed position; `reveal.played` is the learner's move on `miss` and `forced`, null on `success`. The **revealed position** is the one the round's last move was played from: the learner's position on `miss`, `forced`, and a success on the learner's own move; on a success on the opponent's reply, the opponent's position before that reply, whose arrows show the other replies it might have drawn (ticket 21, as ticket 10's prototype). `explanation` is the text for the position where the round ended (ticket 15), which on a success is the leaf and so may differ from the revealed position (ticket 21): its own page, else the nearest position with a page on the path walked, with `borrowed_from` naming that position's moves in SAN; null only if no position on the path has a page (ticket 14 measured none such at the defaults). `score.delta` is the change over this round, null after `forced`.

**Latency budget** (localhost): server handling of a `move` under 10 ms at p95; drop to the opponent's reply visible under 100 ms end to end; the next round on the board within 200 ms of `next`; piece animation at most 100 ms and settable to zero; no loading indicator anywhere in the loop. The prototype handled a move in 0.13 ms mean / 0.43 ms max on a 289-node tree.

## 9. The play page

Source: ticket 10 (variant C, amended by the learner), ticket 16 (score, sounds), ticket 15 (explanation), ADR 0004 (board, one JS module).

Route `/` (also `/play`). Jinja2 page plus the one hand-written JS module of the app; chessground vendored, Lichess defaults (brown board, cburnett pieces), no theme picker. The browser holds no chess logic: it restricts drags to `dests`, sends `move`, renders what comes back.

- **Mid-round**: nothing is revealed. The only text is the **banner**: the learner's colour (badge plus board orientation), the opening name (`opening` of the last message, or nothing), the Score with one decimal, and once per tab the since-last-round delta. When `forced` is set, the set-aside move is drawn as a **yellow arrow** before the learner moves and the banner says "not e5 this time". No pass kind, no recall numbers, no explanation, no on-demand reveal key.
- **Round end**: the revealed position's main moves as **green arrows**, the learner's move **red** (yellow when it was the set-aside move); a one-line **verdict strip** under the board: `✗ e5 · main: c5 · e6`, `✓ 9 plies · Sicilian Defense: Najdorf Variation · 71.6 % (+0.4)`, or the forced form with no delta; under the strip the **Explanation**: the lead, a "more" toggle expanding the full text in place (the board never moves), the borrowed-text label when `borrowed_from` is set, and the footer "From Wikibooks, *Chess Opening Theory* · CC BY-SA 4.0 · trimmed" with the title linking to `url`. Nothing covers the board.
- **Next round**: Space, Enter, or a click on the strip sends `next`, after every outcome; no timer.
- **Sounds** (ticket 16): Move on every move, Capture on a capture, Check when the move gives check (as Lichess does), Victory on `success`, Error on `miss` (the set's Defeat: its Error is only a link to the non-free `standard` set), nothing extra on `forced`, nothing else mid-round. On by default; the `m` key toggles and sends the `sound` message (§8), which persists the `sound` setting (ticket 21).
- **Animation** 100 ms by default, 0 when the setting says so.
- Links to the progress view and settings sit outside the board area; nothing on the page waits on the network but the socket.

## 10. The progress view

Source: ticket 19 (variant A, amended), ADR 0004 ticket 19 amendment (routes, no JS), ADR 0002 ticket 19 amendment (daily table, resets), ticket 16 (per-colour and per-opening scores), ticket 15 (explanation), ADR 0006 (canonical order, opt-out), ADR 0001 (numbers).

Server-rendered Jinja2, plain HTML forms, **no JavaScript**; nothing here is latency-sensitive.

### 10.1 `/progress`, the ledger

- **Head**: the Score with its change since the last day played (latest `daily_score` row before today); the White and Black scores; the known / learning / never-passed counts; the **in-session success rate** `successes / rounds` since this server process started, against the 80–90 % target and coloured when outside it, forced rounds excluded from both terms (ticket 21, ADR 0001's "net of forced exploration"); a **sparkline** of `daily_score.score` (inline SVG); the never-passed count as a link to `/progress?never=1`.
- **Table of openings** (families, §4 step 9), the "First moves" group first, then in order of the sum of pooled counts of each opening's learner positions (the score's own weighting; no sort control). Per row: name, ECO range, position count, a known / learning / never-passed bar, the opening's Score, its White and Black scores, an in/out toggle (form POST), a reset (form POST to a confirmation page). Opted-out openings stay listed with their scores.
- A row unfolds (`<details>`) into one row per **exactly-named line** of that family, same columns and its own score; a line unfolds into its **branches**, each a move string in canonical order with every learner move coloured by that position's recall estimate: green ≥ 0.9, yellow 0.5–0.9, orange < 0.5, red while a relearning pass is owed, grey never passed (the prototype's scale). A position reached by several orders appears once, under its canonical order. Each learner move links to its position page.
- `/progress?never=1`: the never-passed learner positions of the scoped repertoire sorted by pooled count, each linking to its page.

### 10.2 `/progress/position/<epd>`, one position

`<epd>` URL-encoded. Content: the board as an SVG from `chess.svg` with the learner's colour at the bottom; the name (marked *inherited* when the position is not exactly named), ECO, the canonical line; the numbers: recall estimate, half-life, counted passes and misses (with "relearning pass owed" when set), time since the last pass, share of the band's games reaching the position and the number of move orders; the **state word**: **known** at `R >= 0.9`, **learning** at `0.5 <= R < 0.9`, **fading** below 0.5, **relearning** while a relearning pass is owed, **never passed** with no pass at all (pass counts are shown but decide nothing); the main moves as chips coloured by the child's recall (stubs marked); the Explanation with lead, "more", the borrowed-text label and the CC BY-SA footer (the fallback here follows the canonical order, since there is no path walked); a reset (confirmed). Browser back returns to the ledger.

### 10.3 Actions

`POST /progress/opening/<family>/toggle` flips the opening in or out (a settings write, then regeneration); `POST /progress/opening/<family>/reset` and `POST /progress/position/<epd>/reset` show a confirmation page whose form performs the delete of §7. "Drill from here" does not exist in v1.

## 11. Settings

Source: ADR 0002 (what settings hold), ADR 0003 (rating), ADR 0005 (floor, share, widths), ADR 0001 (parameters), ADR 0004 (animation), ticket 16 (sound), ticket 19 (opt-in/out lives on the progress view, not here).

Route `/settings`, a Jinja2 form. Keys in `settings`:

| key | default | constraint |
|---|---|---|
| `rating` | null → band 1500–1800 | integer; mapped to the five bands |
| `width_player`, `width_opponent` | 2, 3 | integers ≥ 1; (1, 3) is strict recall |
| `popularity_floor` | 0.0002 | ≥ the snapshot's storage cut-off |
| `share` | 0.05 | 0–1 |
| `opted_out` | [] | families; edited from the progress view |
| `h0`, `h_min`, `h_max`, `sure`, `floor`, `C`, `alpha`, `forced_rate`, `side_floor` | §5.4 | `forced_rate` ignored when `width_player` = 1 |
| `sound` | true | also toggled by `m` through the `sound` socket message |
| `animation_ms` | 100 | 0–100 |
| `snapshot_version` | set by the app | read-only display |

Plus the one **reset all history** action behind a confirmation. Saving regenerates the repertoire in the process (§4, §7). The declared band and the snapshot version are shown so the learner knows which data they are drilling.

## 12. Sounds, static assets and licences

Source: ADR 0004 (chessground, GPL, attribution), ticket 16 (sfx set, AGPLv3+), ticket 15 (CC BY-SA obligations), ticket 14.

- **chessground** (GPL-3.0-or-later): `chessground.min.js`, `chessground.base.css`, `chessground.brown.css`, `chessground.cburnett.css` and the cburnett piece set (CC BY-SA 3.0), vendored under the package's static directory with their LICENSE, copied by hand on upgrade (the play-loop prototype's `static/chessground/` is the current copy).
- **Sounds**: Lichess's `sfx` set by Enigmahack (AGPLv3+): Move, Capture, Check, Victory, and Defeat as the Error sound (the set's own Error is a link to the `standard` set), vendored likewise. The default `standard` set is non-free and must not ship.
- **Book**: `chess-openings` TSV (CC0), used at build time only; the graph file is CC0 data.
- **Explanations**: CC BY-SA 4.0 data file (§3.3), per-text footer with the page link, "trimmed" stated.
- `LICENSES/`: GPL-3.0-or-later (the app), AGPL-3.0 (sfx), CC-BY-SA-4.0 (Wikibooks text), CC-BY-SA-3.0 (cburnett), CC0 (book and dump). README: a Licences section listing each with its attribution.
- No network access at runtime; no CDN.

## 13. Tests

Source: ADR 0004.

pytest, no browser automation. The play page is verified by hand and was validated by the ticket 10 prototype.

- **Memory model**: the pass kinds (counted, sure, relearning), miss halving without touching the clock, clipping, `R = 0` never passed, Need floor.
- **Aggregates**: mean need on a small DAG with a shared descendant (counted once), memo invalidation, per-colour root need, the Score against a hand computation, decay over time.
- **Repertoire load**: on a fixture graph, main moves (top-k, share, floor, tie order), opt-out plus reachability to a fixed point, unnamed positions kept below the last name, stubs, leaves; the bounds of §4 on a real snapshot when one is available (marked slow).
- **Sampling**: with no history the opponent's frequencies match renormalised popularity within tolerance at the default `C = 1`; a rarely faced move's share rises above its popularity once the others have been faced; stubs never drawn; forced exploration only on a strict minimum, never at P = 1; side floor honoured.
- **Persistence**: round-end transaction atomicity, daily upsert, resets, regeneration leaving records intact, migrations from an empty file.
- **Wire**: the FastAPI test client over `/ws` through whole rounds: pass, miss, success on the learner's move, success on the opponent's reply, forced, relearning, empty `dests` on the round-ending `moved`, explanation and score fields present, `next` and `error` behaviour, the `sound` message persisting the setting, no `revealed` field on a `moved`, the revealed position on a success on the opponent's reply, forced rounds absent from `daily_score` counts, `mean_need` of a stub equal to the floor, two sockets with concurrent rounds committing serially.
- **Build**: `build-snapshot` on a tiny PGN fixture: filters, pooling, cycle dropping on a constructed shuffle, names, canonical orders, diagnostics, both files and the version string; the explanation converter on saved wikitext samples from `refs/openings-text/` (offline).

## 14. Deliverables checklist

The package (`chessop` CLI, server, pages, JS module, vendored assets), the two snapshot files built from a capped prefix of a recent month (§3.1), `LICENSES/` and the README Licences section, and the test suite of §13.

## 15. Contradictions found, resolved by ticket 21

Found while writing (ticket 20); decided by the learner in [ticket 21](issues/21-spec-gaps.md) on 2026-09-24 and folded into the sections named.

- **C1. Does a mid-round `moved` carry the reveal?** No. The field is dropped: nothing leaves the server that the page must hide; the main moves travel only in `round_over` (§8; ADR 0004 amended).
- **C2. Which position is revealed on a success?** The arrows show the position the last move was played from (the opponent's position before its reply when the reply ended the round); the explanation is for the position where the round ended, the leaf on a success. They differ only on a success (§8, §9; ticket 15's "the leaf" read as the explanation's position).

## 16. Gaps, decided by ticket 21

- **G1. Empty subtrees in the need aggregation.** An empty set of learner positions below an edge has mean need equal to the floor; a leaf with the learner to move is not a learner position (§4 step 7, §5.2; ADR 0001 amended).
- **G2. Forced outcomes in the counts.** Excluded from both `daily_score.rounds`/`successes` and the in-session `successes / rounds`; still logged in `round_log` (§7, §10.1; ADR 0001 amended).
- **G3. Persisting the `m` toggle.** A fifth socket message, `{"type": "sound", "on": bool}`, client to server, no reply; the server writes the `sound` setting (§8, §9, §11; ADR 0004 amended).

## 17. Derived, not decided

Readings the spec had to make where the sources are silent on a detail but not on the design; each follows from a source named beside it. They are here so a reviewer can veto one without hunting.

- Aggregation weights are pooled counts, each descendant once (ticket 16's Score formula and its "same root aggregate" sentence; the prototype used path-product weights on a tree).
- Passes are judged at the move and applied at round end (ADR 0002 "written through at every round end"; ADR 0004 "a dropped socket abandons the round, nothing is written").
- `faced` counts are rebuilt from the round log at start (ADR 0001 makes the log "a first-class store"; ADR 0002 lists no other table).
- Reset all deletes position records only (the glossary: history *is* the position records; the round log is never pruned).
- The since-last-round score delta comes from the latest daily score row (ticket 19's table is upserted at every round end, so its last row is the score after the last round).
- Openings are ordered by the sum of their learner positions' pooled counts (ticket 19: "the score's own weighting").
- The opening of an unnamed position, for grouping and per-opening scores, is inherited along the canonical order (ticket 19's prototype, accepted with variant A); opt-out acts on exact names (ADR 0006). The two rules differ on purpose: a shared position named in a kept opening survives an opt-out.
- A socket starts a round on connect; `next` during a round abandons it; settings changes abandon in-flight rounds (ADR 0004's abandon semantics applied to the two cases it did not name).
- Route names, the `--data-dir` flag and `CHESSOP_DATA_DIR`, the file name `chessop.sqlite`, the version string layout and the tie order of main moves are conventions, not decisions.
