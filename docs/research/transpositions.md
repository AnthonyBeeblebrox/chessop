# Transpositions: how many repertoire positions are reachable by more than one move order?

Ticket: [.scratch/chessop/issues/12-transposition-prevalence.md](../../.scratch/chessop/issues/12-transposition-prevalence.md). Settings are the ones ticket 05 settled: the learner's band (`both>=1800`, with `both<1500` and `all` for comparison), an **absolute** cut-off of 0.2% of the band's games, widths `(3,3)` so `k = max(P, O) = 3` most popular replies per position; the uncapped cut-off tree is reported alongside. Data: Lichess 2013-01 standard rated dump (CC0, 121,332 games), the same file [`tree-width-measurements.md`](tree-width-measurements.md) used; names from the CC0 `chess-openings` TSV. Every number below is measured by [`refs/lichess/transposition-analysis.py`](../../refs/lichess/transposition-analysis.py); the tables under "Measurements" are its output verbatim.

## Headline: `both>=1800`, cut-off 0.2% (>= 19 games), widths (3,3)

- **Prevalence.** The drilled tree has 235 nodes (move sequences) and 86 leaf paths; keyed by position it has 216 distinct positions. **17 positions are reachable by more than one move order** (7.9% of positions); the 36 nodes that make them up are **15.3% of the tree**. 14 of the 86 leaf paths (16.3%) *end* on a shared position and **35 (40.7%) pass through at least one**. Uncapped: 31 shared positions of 417 (7.4%), 65 nodes (14.4%), 62 of 175 leaf paths (35.4%) touch one.
- **Depth.** The first transposition is at ply 3 (`Nf3 Nf6 d4` = `d4 Nf6 Nf3`; `Nf3 d5 d4` = `d4 d5 Nf3`). Shared positions appear at plies 3-8 only (2, 5, 4, 3, 2, 1 new ones per ply at k=3), peaking at plies 4-6; nothing at ply 9 or deeper, where the tree is a single path anyway. Uncapped the profile is the same shape (2, 8, 9, 7, 4, 1 at plies 3-8).
- **Largest group.** Three move orders at k=3: the QGD Normal Defense position after `d4 d5 c4 e6 Nc3 Nf6` (also via `d4 e6 c4 d5 Nc3 Nf6` and `d4 Nf6 c4 e6 Nc3 d5`) and the Semi-Slav "Accelerated Move Order" position after `d4 d5 c4 e6 Nc3 c6`. Uncapped the Semi-Slav position is reached by **four** orders (every permutation of `...c6/...e6/...d5` the cut-off keeps: 26 / 25 / 23 / 22 games). All 17 groups are `d4`-family or `e4 e6`/`e4 c5` move-order families; see the per-position table.
- **What merging changes.** Merging the same tree by position takes it from 235 nodes / 234 edges to **216 positions / 226 edges (-8.1% nodes)**; the 86 leaf paths become 75 leaf positions, but the number of root-to-leaf paths *rises* to 112, because in **14 of the 17 groups the move orders keep different replies** (the sequence tree drills the same position to different depths depending on how it was reached: `Nf3 Nf6 d4` dead-ends on 27 games while `d4 Nf6 Nf3` has 3 kept replies on 116 games; `d4 e6 c4 d5 Nc3` keeps 2 replies, `d4 d5 c4 e6 Nc3` keeps 3). Applying the cut-off to *pooled* per-position counts instead (a position-keyed build) gives 268 positions / 187 paths at k=3: 53 positions enter the repertoire only once their move orders are added together.
- **Learner's side.** Side to move is part of the EPD, so every move order into a shared position has the same side to move; the only way two paths to one position could put the learner on different colours is a repetition (same position at two plies), and **0 of the 17 groups (0 of 31 uncapped) span more than one ply**. What does differ is *whose* move order it is: in 12 of 17 groups only Black's moves are permuted (`...e6/...d5/...Nf6/...c6` orders), in 5 only White's (`d4/Nf3`, `e4/d4` orders), in 0 both (uncapped 24 / 6 / 1). So a position key does not need the learner's colour *to disambiguate paths*; it needs it only because the app drills both colours over one tree and the learner's state at a position as White is not their state at it as Black, which is a design fact, not a data one. A Black-permuted group is the learner's own alternative move orders when they play Black (a `width_player` question) and the opponent's when they play White (a `width_opponent` question).
- **Names.** The `chess-openings` `dist` columns are a usable key: 3,810 rows, 3,810 distinct `epd`, and replaying each row's `uci` with python-chess reproduces its `epd` in every case. **159 of 235 nodes (67.7%) carry an exact-EPD name**, 76 do not (the start position plus 75 nodes at plies 3-17, 5, 12, 12, 11, 10, 7, 11 of them at plies 3-9); every non-root node has a named ancestor-or-self, so "play moves backwards until a named position is found" names all of them. 20 named nodes are reached by a move order other than the TSV's own `pgn` (the name is found *because* the lookup is by position). 11 of the 17 shared positions are named; for 10 of those the TSV's own move order is one of the tree's. Uncapped: 267 of 451 named (59.2%).
- **Other bands.** Transpositions are a `both>=1800` phenomenon: at (3,3) the `all` tree has 5 shared positions of 133 (3.8%; 10 nodes, 7.2%) and `both<1500` has 3 of 129 (2.3%; 6 nodes, 4.5%), against 17 of 216 (7.9%; 36 nodes, 15.3%) at 1800+. The low band's transpositions are `d4 e6 e4` / `e4 e6 d4` French orders; the 1800+ ones are dominated by QGD / Semi-Slav / Nimzo move-order families that only exist there.

## Method

- **Trie.** Stream the `.pgn.zst`, keep each game's mainline SAN to ply 21, build one trie with a game count per node for each bucket (`all` 121,332 games, `both>=1800` 9,525, `both<1500` 19,771, by both players' Elo). 1,597,561 nodes. Streaming, tokenizer and bucket code are imported from `tree-width-analysis.py`, whose tokenizer self-check is in [`tree-width-measurements.md`](tree-width-measurements.md).
- **Sequence tree.** Per bucket: a node survives if its count is >= 0.2% of the bucket's games (`thr = 0.002 * n`, `count >= thr`); each surviving node keeps its `k` most popular surviving replies (`k = 3`, and uncapped). Ties at the k-th reply are broken alphabetically by SAN here and by first-seen order in `tree-width-analysis.py`; the node and leaf-path counts of all six trees (3 buckets x 2 widths) agree with that script and with `refs/lichess/dump-2013-01-tree-stats.txt`. A **leaf path** is a node with no kept reply (dead end or the tree's deepest frontier).
- **Position key.** `chess.Board.epd()` from python-chess 1.11.2: piece placement, side to move, castling rights, and the en-passant square only when a capture is legal; move counters omitted. It is the same call `chess-openings/bin/gen.py` uses to derive the `epd` column, so tree keys and TSV keys are comparable by string equality (checked: 0 mismatches between the TSV's `epd` and the EPD of its replayed `uci`).
- **Shared position** = an EPD that more than one node of the sequence tree maps to ("positions reached by >1 move order"; a "group"). A group is credited to a ply when all its members are at that ply; a group whose members sit at different plies would be a repetition and is counted separately (`groups spanning >1 ply`), so that the per-ply table also answers whether side to move can differ between paths.
- **Merged DAG** = the same tree with nodes merged by EPD: positions = distinct EPDs, edges = distinct (EPD, UCI move) pairs, a leaf = a position with no kept move out of it under *any* of its move orders, root-to-leaf paths counted by dynamic programming (cycle-checked). "Groups where the move orders keep different replies" counts groups whose members' kept-reply sets differ, i.e. where a sequence tree drills one position inconsistently.
- **Pooled DAG** = the cut-off applied to positions rather than sequences: every trie node is keyed (1,433,571 distinct positions, 1,475,243 distinct (position, move) edges over all 1.6 M nodes), a position's count is the sum over its move orders, an edge survives when both it and its parent position reach the cut-off, each position keeps its `k` most popular surviving edges, and the DAG is what is reachable from the start position. A game visiting one position twice would be pooled twice; 1,367 of the 1.43 M positions are reached at more than one ply somewhere in the trie, none of them inside any cut-off tree.
- **Whose move order.** For each group, the plies at which any two member move orders differ, classified by the side that moved at those plies (odd ply = White).
- **Names.** The `dist`-format TSV (`eco name pgn uci epd`) generated by the checked-in `chess-openings-bin-gen.py` from `chess-openings-{a..e}.tsv`; a node is *named* when its EPD is a row's `epd`.
- **Caveats.** One month of 2013; at 1800+ the 0.2% cut-off is 19 games, so the groups at plies 7-8 rest on 20-150 games each and the exact membership of the ply 4-6 groups would move with a bigger month, but the shape (transpositions at plies 3-8, in the `d4` and `e4 e6` families, none deeper) is robust because it is the structure of the openings, not sampling. The `both<1500` band's three groups rest on 40-360 games.

## Measurements

<!-- generated by refs/lichess/transposition-analysis.py; do not edit by hand -->

Dump: 121332 games; one trie to ply 21 with 1597561 nodes (distinct move sequences), keyed to 1433571 distinct positions (EPD) and 1475243 distinct (position, move) edges.
Games under a SAN token python-chess rejected, per bucket: all 0, both>=1800 0, both<1500 0.
chess-openings dist TSV: 3810 rows, 3810 distinct EPDs, 0 rows whose `epd` column differs from replaying its `uci` column with python-chess.
Positions reached at more than one ply anywhere in the trie (a game repeating a position): 1367 of 1433571.

## Bucket `all` (121332 games), cut-off >= 0.2% (>= 243 games)

### Sequence tree vs position-keyed DAG

| width | tree nodes | tree leaf paths | max ply | distinct positions | positions reached by >1 move order | nodes in them (share of nodes) | first ply with a transposition | largest group | groups spanning >1 ply | leaf paths ending on a shared position | leaf paths through >=1 shared position | distinct leaf positions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| k = 3, i.e. widths (3,3) | 138 | 60 | 10 | 133 | 5 (3.8% of nodes) | 10 (7.2%) | 3 | 2 | 0 | 3 (5.0% of leaf paths) | 12 (20.0%) | 60 |
| uncapped (cut-off only) | 322 | 163 | 10 | 314 | 8 (2.5% of nodes) | 16 (5.0%) | 3 | 2 | 0 | 6 (3.7% of leaf paths) | 29 (17.8%) | 163 |

Merging the same tree by position (edges = distinct (position, move) pairs; a leaf is a position with no kept move out of it, so a sequence leaf whose position has kept moves under another move order stops being a leaf):

| width | sequence tree: nodes / edges / leaf paths | merged DAG: positions / edges / leaf positions / root-to-leaf paths | cycles | groups where the move orders keep different replies |
|---|---|---|---|---|
| k = 3, i.e. widths (3,3) | 138 / 137 / 60 | 133 / 135 / 57 / 66 | 0 | 3 of 5 |
| uncapped (cut-off only) | 322 / 321 / 163 | 314 / 319 / 157 / 186 | 0 | 6 of 8 |

### By ply (k = 3)

| ply | nodes | distinct positions | positions reached by >1 order (first at this ply) | nodes in a shared position | cumulative shared positions |
|---|---|---|---|---|---|
| 0 | 1 | 1 | 0 | 0 | 0 |
| 1 | 3 | 3 | 0 | 0 | 0 |
| 2 | 9 | 9 | 0 | 0 | 0 |
| 3 | 18 | 17 | 1 | 2 | 1 |
| 4 | 31 | 29 | 2 | 4 | 3 |
| 5 | 36 | 34 | 2 | 4 | 5 |
| 6 | 18 | 18 | 0 | 0 | 5 |
| 7 | 12 | 12 | 0 | 0 | 5 |
| 8 | 6 | 6 | 0 | 0 | 5 |
| 9 | 3 | 3 | 0 | 0 | 5 |
| 10 | 1 | 1 | 0 | 0 | 5 |

Same table, uncapped:

| ply | nodes | distinct positions | positions reached by >1 order (first at this ply) | nodes in a shared position | cumulative shared positions |
|---|---|---|---|---|---|
| 0 | 1 | 1 | 0 | 0 | 0 |
| 1 | 12 | 12 | 0 | 0 | 0 |
| 2 | 46 | 46 | 0 | 0 | 0 |
| 3 | 75 | 73 | 2 | 4 | 2 |
| 4 | 67 | 63 | 4 | 8 | 6 |
| 5 | 60 | 58 | 2 | 4 | 8 |
| 6 | 34 | 34 | 0 | 0 | 8 |
| 7 | 17 | 17 | 0 | 0 | 8 |
| 8 | 6 | 6 | 0 | 0 | 8 |
| 9 | 3 | 3 | 0 | 0 | 8 |
| 10 | 1 | 1 | 0 | 0 | 8 |

### Whose move order differs

For each shared position, the plies at which its move orders differ, classified by the side that moved at those plies (odd ply = White). Side to move is part of the EPD, so every move order into a shared position has the same side to move; `groups spanning >1 ply` above counts the only way the learner's colour could differ between two paths to one position (a repetition), and is 0.

| width | White's moves only | Black's moves only | both sides |
|---|---|---|---|
| k = 3, i.e. widths (3,3) | 3 | 2 | 0 |
| uncapped (cut-off only) | 4 | 4 | 0 |

### Every shared position (k = 3)

| ply | move orders | games per order | kept replies per order | differing side | chess-openings name | move orders |
|---|---|---|---|---|---|---|
| 3 | 2 | 716 / 2989 | 1 / 1 | White | French Defense: Normal Variation | `d4 e6 e4` ; `e4 e6 d4` |
| 4 | 2 | 565 / 1485 | 1 / 1 | Black | Queen's Gambit Declined | `d4 e6 c4 d5` ; `d4 d5 c4 e6` |
| 4 | 2 | 285 / 1798 | 0 / 3 | White | French Defense | `d4 e6 e4 d5` ; `e4 e6 d4 d5` |
| 5 | 2 | 333 / 788 | 0 / 1 | Black | Queen's Gambit Declined: Queen's Knight Variation | `d4 e6 c4 d5 Nc3` ; `d4 d5 c4 e6 Nc3` |
| 5 | 2 | 265 / 3761 | 0 / 3 | White | Italian Game | `e4 e5 Bc4 Nc6 Nf3` ; `e4 e5 Nf3 Nc6 Bc4` |

Shared positions that exist only in the uncapped tree (3):

| ply | move orders | games per order | differing side | chess-openings name | move orders |
|---|---|---|---|---|---|
| 3 | 2 | 429 / 2370 | White | Queen's Pawn Game: Zukertort Variation | `Nf3 d5 d4` ; `d4 d5 Nf3` |
| 4 | 2 | 303 / 1038 | Black | Slav Defense | `d4 c6 c4 d5` ; `d4 d5 c4 c6` |
| 4 | 2 | 366 / 11003 | Black | King's Knight Opening: Normal Variation | `e4 Nc6 Nf3 e5` ; `e4 e5 Nf3 Nc6` |

### Cut-off on pooled position counts

Alternative build: count games per *position* (summed over every move order in the dump), keep a (position, move) edge when both the edge and its parent position reach the cut-off, keep the k most popular edges per position, take what is reachable from the start position.

| width | pooled DAG: positions / edges / root-to-leaf paths / max depth | of which positions reached by >1 move order in the dump | positions not in the sequence tree | sequence-tree positions not in the pooled DAG | cycles |
|---|---|---|---|---|---|
| k = 3, i.e. widths (3,3) | 151 / 155 / 81 / 10 | 134 | 18 | 0 | 0 |
| uncapped (cut-off only) | 338 / 347 / 212 / 10 | 234 | 24 | 0 | 0 |

### chess-openings names

| width | nodes | named (exact EPD) | unnamed | unnamed by ply | named leaves / leaves | nodes at ply >= 1 with a named ancestor-or-self | named nodes reached by a move order other than the TSV's `pgn` | shared positions named | shared positions where the TSV's own move order is one of the tree's |
|---|---|---|---|---|---|---|---|---|---|
| k = 3, i.e. widths (3,3) | 138 | 94 (68.1%) | 44 | 0: 1, 2: 3, 3: 3, 4: 12, 5: 12, 6: 6, 7: 2, 8: 3, 9: 2 | 30 / 60 | 137 of 137 | 9 | 5 of 5 | 5 of 5 |
| uncapped (cut-off only) | 322 | 200 (62.1%) | 122 | 0: 1, 2: 12, 3: 31, 4: 25, 5: 27, 6: 14, 7: 7, 8: 3, 9: 2 | 89 / 163 | 321 of 321 | 14 | 8 of 8 | 8 of 8 |

## Bucket `both>=1800` (9525 games), cut-off >= 0.2% (>= 19 games)

### Sequence tree vs position-keyed DAG

| width | tree nodes | tree leaf paths | max ply | distinct positions | positions reached by >1 move order | nodes in them (share of nodes) | first ply with a transposition | largest group | groups spanning >1 ply | leaf paths ending on a shared position | leaf paths through >=1 shared position | distinct leaf positions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| k = 3, i.e. widths (3,3) | 235 | 86 | 18 | 216 | 17 (7.9% of nodes) | 36 (15.3%) | 3 | 3 | 0 | 14 (16.3% of leaf paths) | 35 (40.7%) | 82 |
| uncapped (cut-off only) | 451 | 175 | 18 | 417 | 31 (7.4% of nodes) | 65 (14.4%) | 3 | 4 | 0 | 23 (13.1% of leaf paths) | 62 (35.4%) | 168 |

Merging the same tree by position (edges = distinct (position, move) pairs; a leaf is a position with no kept move out of it, so a sequence leaf whose position has kept moves under another move order stops being a leaf):

| width | sequence tree: nodes / edges / leaf paths | merged DAG: positions / edges / leaf positions / root-to-leaf paths | cycles | groups where the move orders keep different replies |
|---|---|---|---|---|
| k = 3, i.e. widths (3,3) | 235 / 234 / 86 | 216 / 226 / 75 / 112 | 0 | 14 of 17 |
| uncapped (cut-off only) | 451 / 450 / 175 | 417 / 431 / 157 / 216 | 0 | 22 of 31 |

### By ply (k = 3)

| ply | nodes | distinct positions | positions reached by >1 order (first at this ply) | nodes in a shared position | cumulative shared positions |
|---|---|---|---|---|---|
| 0 | 1 | 1 | 0 | 0 | 0 |
| 1 | 3 | 3 | 0 | 0 | 0 |
| 2 | 9 | 9 | 0 | 0 | 0 |
| 3 | 23 | 21 | 2 | 4 | 2 |
| 4 | 34 | 29 | 5 | 10 | 7 |
| 5 | 38 | 34 | 4 | 8 | 11 |
| 6 | 41 | 36 | 3 | 8 | 14 |
| 7 | 32 | 30 | 2 | 4 | 16 |
| 8 | 23 | 22 | 1 | 2 | 17 |
| 9 | 16 | 16 | 0 | 0 | 17 |
| 10 | 4 | 4 | 0 | 0 | 17 |
| 11 | 3 | 3 | 0 | 0 | 17 |
| 12 | 2 | 2 | 0 | 0 | 17 |
| 13 | 1 | 1 | 0 | 0 | 17 |
| 14 | 1 | 1 | 0 | 0 | 17 |
| 15 | 1 | 1 | 0 | 0 | 17 |
| 16 | 1 | 1 | 0 | 0 | 17 |
| 17 | 1 | 1 | 0 | 0 | 17 |
| 18 | 1 | 1 | 0 | 0 | 17 |

Same table, uncapped:

| ply | nodes | distinct positions | positions reached by >1 order (first at this ply) | nodes in a shared position | cumulative shared positions |
|---|---|---|---|---|---|
| 0 | 1 | 1 | 0 | 0 | 0 |
| 1 | 10 | 10 | 0 | 0 | 0 |
| 2 | 37 | 37 | 0 | 0 | 0 |
| 3 | 67 | 65 | 2 | 4 | 2 |
| 4 | 78 | 70 | 8 | 16 | 10 |
| 5 | 78 | 69 | 9 | 18 | 19 |
| 6 | 71 | 61 | 7 | 17 | 26 |
| 7 | 47 | 43 | 4 | 8 | 30 |
| 8 | 30 | 29 | 1 | 2 | 31 |
| 9 | 17 | 17 | 0 | 0 | 31 |
| 10 | 4 | 4 | 0 | 0 | 31 |
| 11 | 3 | 3 | 0 | 0 | 31 |
| 12 | 2 | 2 | 0 | 0 | 31 |
| 13 | 1 | 1 | 0 | 0 | 31 |
| 14 | 1 | 1 | 0 | 0 | 31 |
| 15 | 1 | 1 | 0 | 0 | 31 |
| 16 | 1 | 1 | 0 | 0 | 31 |
| 17 | 1 | 1 | 0 | 0 | 31 |
| 18 | 1 | 1 | 0 | 0 | 31 |

### Whose move order differs

For each shared position, the plies at which its move orders differ, classified by the side that moved at those plies (odd ply = White). Side to move is part of the EPD, so every move order into a shared position has the same side to move; `groups spanning >1 ply` above counts the only way the learner's colour could differ between two paths to one position (a repetition), and is 0.

| width | White's moves only | Black's moves only | both sides |
|---|---|---|---|
| k = 3, i.e. widths (3,3) | 5 | 12 | 0 |
| uncapped (cut-off only) | 6 | 24 | 1 |

### Every shared position (k = 3)

| ply | move orders | games per order | kept replies per order | differing side | chess-openings name | move orders |
|---|---|---|---|---|---|---|
| 6 | 3 | 61 / 56 / 125 | 1 / 0 / 2 | Black | Queen's Gambit Declined: Normal Defense | `d4 e6 c4 d5 Nc3 Nf6` ; `d4 Nf6 c4 e6 Nc3 d5` ; `d4 d5 c4 e6 Nc3 Nf6` |
| 6 | 3 | 25 / 23 / 22 | 0 / 0 / 0 | Black | Semi-Slav Defense: Accelerated Move Order | `d4 e6 c4 d5 Nc3 c6` ; `d4 d5 c4 c6 Nc3 e6` ; `d4 d5 c4 e6 Nc3 c6` |
| 3 | 2 | 27 / 116 | 0 / 3 | White | Indian Defense: Knights Variation | `Nf3 Nf6 d4` ; `d4 Nf6 Nf3` |
| 3 | 2 | 30 / 274 | 0 / 3 | White | Queen's Pawn Game: Zukertort Variation | `Nf3 d5 d4` ; `d4 d5 Nf3` |
| 4 | 2 | 23 / 61 | 0 / 1 | Black | Queen's Pawn Game: Symmetrical Variation | `d4 Nf6 Nf3 d5` ; `d4 d5 Nf3 Nf6` |
| 4 | 2 | 53 / 109 | 1 / 2 | Black | (unnamed) | `d4 e6 Nf3 d5` ; `d4 d5 Nf3 e6` |
| 4 | 2 | 55 / 173 | 1 / 2 | Black | (unnamed) | `d4 e6 c4 Nf6` ; `d4 Nf6 c4 e6` |
| 4 | 2 | 135 / 264 | 1 / 2 | Black | Queen's Gambit Declined | `d4 e6 c4 d5` ; `d4 d5 c4 e6` |
| 4 | 2 | 28 / 166 | 0 / 2 | Black | Sicilian Defense: French Variation | `e4 e6 Nf3 c5` ; `e4 c5 Nf3 e6` |
| 5 | 2 | 22 / 26 | 0 / 0 | Black | (unnamed) | `d4 e6 Nf3 d5 e3` ; `d4 d5 Nf3 e6 e3` |
| 5 | 2 | 47 / 117 | 1 / 2 | Black | (unnamed) | `d4 e6 c4 Nf6 Nc3` ; `d4 Nf6 c4 e6 Nc3` |
| 5 | 2 | 108 / 197 | 2 / 3 | Black | Queen's Gambit Declined: Queen's Knight Variation | `d4 e6 c4 d5 Nc3` ; `d4 d5 c4 e6 Nc3` |
| 5 | 2 | 23 / 63 | 0 / 2 | White | (unnamed) | `e4 c5 Nc3 Nc6 Nf3` ; `e4 c5 Nf3 Nc6 Nc3` |
| 6 | 2 | 22 / 43 | 0 / 0 | Black | Nimzo-Indian Defense | `d4 e6 c4 Nf6 Nc3 Bb4` ; `d4 Nf6 c4 e6 Nc3 Bb4` |
| 7 | 2 | 34 / 57 | 1 / 2 | Black | Queen's Gambit Declined: Three Knights Variation | `d4 e6 c4 d5 Nc3 Nf6 Nf3` ; `d4 d5 c4 e6 Nc3 Nf6 Nf3` |
| 7 | 2 | 145 / 45 | 2 / 1 | White | French Defense: Exchange Variation | `e4 e6 Nf3 d5 exd5 exd5 d4` ; `e4 e6 d4 d5 exd5 exd5 Nf3` |
| 8 | 2 | 98 / 33 | 3 / 0 | White | (unnamed) | `e4 e6 Nf3 d5 exd5 exd5 d4 Nf6` ; `e4 e6 d4 d5 exd5 exd5 Nf3 Nf6` |

Shared positions that exist only in the uncapped tree (14):

| ply | move orders | games per order | differing side | chess-openings name | move orders |
|---|---|---|---|---|---|
| 4 | 2 | 25 / 40 | Black+White | Queen's Pawn Game: Chigorin Variation | `Nf3 Nc6 d4 d5` ; `d4 d5 Nf3 Nc6` |
| 4 | 2 | 88 / 133 | Black | Slav Defense | `d4 c6 c4 d5` ; `d4 d5 c4 c6` |
| 4 | 2 | 122 / 582 | Black | King's Knight Opening: Normal Variation | `e4 Nc6 Nf3 e5` ; `e4 e5 Nf3 Nc6` |
| 5 | 2 | 60 / 117 | Black | Slav Defense | `d4 c6 c4 d5 Nc3` ; `d4 d5 c4 c6 Nc3` |
| 5 | 2 | 29 / 205 | Black | Ruy Lopez | `e4 Nc6 Nf3 e5 Bb5` ; `e4 e5 Nf3 Nc6 Bb5` |
| 5 | 2 | 23 / 211 | Black | Italian Game | `e4 Nc6 Nf3 e5 Bc4` ; `e4 e5 Nf3 Nc6 Bc4` |
| 5 | 2 | 21 / 36 | Black | Three Knights Opening | `e4 Nc6 Nf3 e5 Nc3` ; `e4 e5 Nf3 Nc6 Nc3` |
| 5 | 2 | 41 / 89 | Black | Scotch Game | `e4 Nc6 Nf3 e5 d4` ; `e4 e5 Nf3 Nc6 d4` |
| 6 | 2 | 20 / 69 | Black | (unnamed) | `d4 c6 c4 d5 Nc3 Nf6` ; `d4 d5 c4 c6 Nc3 Nf6` |
| 6 | 2 | 23 / 96 | Black | Italian Game: Two Knights Defense | `e4 Nc6 Nf3 e5 Bc4 Nf6` ; `e4 e5 Nf3 Nc6 Bc4 Nf6` |
| 6 | 2 | 20 / 26 | Black | Four Knights Game | `e4 Nc6 Nf3 e5 Nc3 Nf6` ; `e4 e5 Nf3 Nc6 Nc3 Nf6` |
| 6 | 2 | 41 / 83 | Black | Scotch Game | `e4 Nc6 Nf3 e5 d4 exd4` ; `e4 e5 Nf3 Nc6 d4 exd4` |
| 7 | 2 | 26 / 26 | Black | Scotch Game | `e4 Nc6 Nf3 e5 d4 exd4 Nxd4` ; `e4 e5 Nf3 Nc6 d4 exd4 Nxd4` |
| 7 | 2 | 105 / 22 | White | (unnamed) | `e4 c6 Nf3 d5 exd5 cxd5 d4` ; `e4 c6 d4 d5 exd5 cxd5 Nf3` |

### Cut-off on pooled position counts

Alternative build: count games per *position* (summed over every move order in the dump), keep a (position, move) edge when both the edge and its parent position reach the cut-off, keep the k most popular edges per position, take what is reachable from the start position.

| width | pooled DAG: positions / edges / root-to-leaf paths / max depth | of which positions reached by >1 move order in the dump | positions not in the sequence tree | sequence-tree positions not in the pooled DAG | cycles |
|---|---|---|---|---|---|
| k = 3, i.e. widths (3,3) | 268 / 284 / 187 / 18 | 244 | 53 | 1 | 0 |
| uncapped (cut-off only) | 491 / 513 / 305 / 18 | 400 | 74 | 0 | 0 |

### chess-openings names

| width | nodes | named (exact EPD) | unnamed | unnamed by ply | named leaves / leaves | nodes at ply >= 1 with a named ancestor-or-self | named nodes reached by a move order other than the TSV's `pgn` | shared positions named | shared positions where the TSV's own move order is one of the tree's |
|---|---|---|---|---|---|---|---|---|---|
| k = 3, i.e. widths (3,3) | 235 | 159 (67.7%) | 76 | 0: 1, 3: 5, 4: 12, 5: 12, 6: 11, 7: 10, 8: 7, 9: 11, 10: 2, 11: 1, 12: 2, 15: 1, 17: 1 | 47 / 86 | 234 of 234 | 20 | 11 of 17 | 10 of 17 |
| uncapped (cut-off only) | 451 | 267 (59.2%) | 184 | 0: 1, 2: 4, 3: 29, 4: 33, 5: 36, 6: 28, 7: 22, 8: 12, 9: 12, 10: 2, 11: 1, 12: 2, 15: 1, 17: 1 | 86 / 175 | 450 of 450 | 39 | 23 of 31 | 22 of 31 |

## Bucket `both<1500` (19771 games), cut-off >= 0.2% (>= 40 games)

### Sequence tree vs position-keyed DAG

| width | tree nodes | tree leaf paths | max ply | distinct positions | positions reached by >1 move order | nodes in them (share of nodes) | first ply with a transposition | largest group | groups spanning >1 ply | leaf paths ending on a shared position | leaf paths through >=1 shared position | distinct leaf positions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| k = 3, i.e. widths (3,3) | 132 | 61 | 9 | 129 | 3 (2.3% of nodes) | 6 (4.5%) | 3 | 2 | 0 | 3 (4.9% of leaf paths) | 4 (6.6%) | 60 |
| uncapped (cut-off only) | 283 | 158 | 9 | 275 | 8 (2.9% of nodes) | 16 (5.7%) | 3 | 2 | 0 | 11 (7.0% of leaf paths) | 14 (8.9%) | 154 |

Merging the same tree by position (edges = distinct (position, move) pairs; a leaf is a position with no kept move out of it, so a sequence leaf whose position has kept moves under another move order stops being a leaf):

| width | sequence tree: nodes / edges / leaf paths | merged DAG: positions / edges / leaf positions / root-to-leaf paths | cycles | groups where the move orders keep different replies |
|---|---|---|---|---|
| k = 3, i.e. widths (3,3) | 132 / 131 / 61 | 129 / 130 / 59 / 62 | 0 | 2 of 3 |
| uncapped (cut-off only) | 283 / 282 / 158 | 275 / 281 / 151 / 159 | 0 | 4 of 8 |

### By ply (k = 3)

| ply | nodes | distinct positions | positions reached by >1 order (first at this ply) | nodes in a shared position | cumulative shared positions |
|---|---|---|---|---|---|
| 0 | 1 | 1 | 0 | 0 | 0 |
| 1 | 3 | 3 | 0 | 0 | 0 |
| 2 | 9 | 9 | 0 | 0 | 0 |
| 3 | 21 | 20 | 1 | 2 | 1 |
| 4 | 31 | 30 | 1 | 2 | 2 |
| 5 | 26 | 25 | 1 | 2 | 3 |
| 6 | 21 | 21 | 0 | 0 | 3 |
| 7 | 14 | 14 | 0 | 0 | 3 |
| 8 | 4 | 4 | 0 | 0 | 3 |
| 9 | 2 | 2 | 0 | 0 | 3 |

Same table, uncapped:

| ply | nodes | distinct positions | positions reached by >1 order (first at this ply) | nodes in a shared position | cumulative shared positions |
|---|---|---|---|---|---|
| 0 | 1 | 1 | 0 | 0 | 0 |
| 1 | 13 | 13 | 0 | 0 | 0 |
| 2 | 43 | 43 | 0 | 0 | 0 |
| 3 | 70 | 66 | 4 | 8 | 4 |
| 4 | 65 | 64 | 1 | 2 | 5 |
| 5 | 39 | 37 | 2 | 4 | 7 |
| 6 | 30 | 29 | 1 | 2 | 8 |
| 7 | 16 | 16 | 0 | 0 | 8 |
| 8 | 4 | 4 | 0 | 0 | 8 |
| 9 | 2 | 2 | 0 | 0 | 8 |

### Whose move order differs

For each shared position, the plies at which its move orders differ, classified by the side that moved at those plies (odd ply = White). Side to move is part of the EPD, so every move order into a shared position has the same side to move; `groups spanning >1 ply` above counts the only way the learner's colour could differ between two paths to one position (a repetition), and is 0.

| width | White's moves only | Black's moves only | both sides |
|---|---|---|---|
| k = 3, i.e. widths (3,3) | 2 | 0 | 1 |
| uncapped (cut-off only) | 6 | 1 | 1 |

### Every shared position (k = 3)

| ply | move orders | games per order | kept replies per order | differing side | chess-openings name | move orders |
|---|---|---|---|---|---|---|
| 3 | 2 | 166 / 360 | 1 / 2 | White | French Defense: Normal Variation | `d4 e6 e4` ; `e4 e6 d4` |
| 4 | 2 | 40 / 112 | 0 / 1 | White | French Defense | `d4 e6 e4 d5` ; `e4 e6 d4 d5` |
| 5 | 2 | 68 / 59 | 0 / 0 | Black+White | French Defense: Advance Variation | `e4 e6 d4 d5 e5` ; `e4 d5 e5 e6 d4` |

Shared positions that exist only in the uncapped tree (5):

| ply | move orders | games per order | differing side | chess-openings name | move orders |
|---|---|---|---|---|---|
| 3 | 2 | 102 / 212 | White | Queen's Pawn Game: Zukertort Variation | `Nf3 d5 d4` ; `d4 d5 Nf3` |
| 3 | 2 | 60 / 43 | White | Blackmar-Diemer Gambit | `d4 d5 e4` ; `e4 d5 d4` |
| 3 | 2 | 46 / 109 | White | Pirc Defense | `d4 d6 e4` ; `e4 d6 d4` |
| 5 | 2 | 63 / 42 | White | Petrov's Defense: Italian Variation | `e4 e5 Bc4 Nf6 Nf3` ; `e4 e5 Nf3 Nf6 Bc4` |
| 6 | 2 | 46 / 126 | Black | Four Knights Game | `e4 e5 Nf3 Nf6 Nc3 Nc6` ; `e4 e5 Nf3 Nc6 Nc3 Nf6` |

### Cut-off on pooled position counts

Alternative build: count games per *position* (summed over every move order in the dump), keep a (position, move) edge when both the edge and its parent position reach the cut-off, keep the k most popular edges per position, take what is reachable from the start position.

| width | pooled DAG: positions / edges / root-to-leaf paths / max depth | of which positions reached by >1 move order in the dump | positions not in the sequence tree | sequence-tree positions not in the pooled DAG | cycles |
|---|---|---|---|---|---|
| k = 3, i.e. widths (3,3) | 141 / 142 / 66 / 10 | 106 | 12 | 0 | 0 |
| uncapped (cut-off only) | 294 / 302 / 190 / 10 | 191 | 19 | 0 | 0 |

### chess-openings names

| width | nodes | named (exact EPD) | unnamed | unnamed by ply | named leaves / leaves | nodes at ply >= 1 with a named ancestor-or-self | named nodes reached by a move order other than the TSV's `pgn` | shared positions named | shared positions where the TSV's own move order is one of the tree's |
|---|---|---|---|---|---|---|---|---|---|
| k = 3, i.e. widths (3,3) | 132 | 69 (52.3%) | 63 | 0: 1, 2: 3, 3: 10, 4: 16, 5: 12, 6: 10, 7: 7, 8: 3, 9: 1 | 24 / 61 | 131 of 131 | 9 | 3 of 3 | 3 of 3 |
| uncapped (cut-off only) | 283 | 165 (58.3%) | 118 | 0: 1, 2: 11, 3: 32, 4: 32, 5: 18, 6: 12, 7: 8, 8: 3, 9: 1 | 79 / 158 | 282 of 282 | 17 | 8 of 8 | 8 of 8 |


## Reproduction

The dump is CC0 and was deleted after the run. Every number above is produced by one run of [`refs/lichess/transposition-analysis.py`](../../refs/lichess/transposition-analysis.py) (51 s wall, 1.68 GB max RSS: one trie with per-bucket counts, keyed to EPD over all 1.6 M nodes).

```sh
cd /home/anthony/pproj/chessop

# 1. dependencies (python-chess 1.11.2, zstandard 0.25.0), same venv as tree-width-measurements.md
uv venv /tmp/chessvenv
uv pip install --python /tmp/chessvenv/bin/python chess==1.11.2 zstandard==0.25.0

# 2. the 2013-01 standard rated dump: 17,761,302 bytes,
#    sha256 aa40b3671fa3cf1072eb182892cd90b0e1e003a4a5943492f64b77e7f3fd1635
curl -sSL -o refs/lichess/lichess_db_standard_rated_2013-01.pgn.zst \
    https://database.lichess.org/standard/lichess_db_standard_rated_2013-01.pgn.zst
sha256sum refs/lichess/lichess_db_standard_rated_2013-01.pgn.zst

# 3. the chess-openings `dist` columns (uci, epd), derived by the upstream
#    bin/gen.py (checked in as chess-openings-bin-gen.py) from the 3-column TSVs
/tmp/chessvenv/bin/python refs/lichess/chess-openings-bin-gen.py \
    refs/lichess/chess-openings-a.tsv refs/lichess/chess-openings-b.tsv \
    refs/lichess/chess-openings-c.tsv refs/lichess/chess-openings-d.tsv \
    refs/lichess/chess-openings-e.tsv > /tmp/chess-openings-dist.tsv
# -> 3811 lines (header + 3810 rows), exit 0

# 4. the measurement; the output is the "Measurements" section above, verbatim
/tmp/chessvenv/bin/python refs/lichess/transposition-analysis.py \
    refs/lichess/lichess_db_standard_rated_2013-01.pgn.zst \
    /tmp/chess-openings-dist.tsv /tmp/transpositions-generated.md

# 5. do not keep the 17.8 MB dump in the repo
rm refs/lichess/lichess_db_standard_rated_2013-01.pgn.zst
```

Cross-checks: per-bucket game counts (121,332 / 9,525 / 19,771), node counts and leaf paths of all six trees (`all` 138/60 and 322/163, `both>=1800` 235/86 and 451/175, `both<1500` 132/61 and 283/158) and maximum plies (10, 18, 9) equal the `(3,3)` and `no cap` rows of [`tree-width-measurements.md`](tree-width-measurements.md) at the 0.2% cut-off (that file's "Tree: N nodes" lines count without the root; its width tables count with it, as here). 0 SAN tokens rejected by python-chess in any bucket. The per-ply node columns sum to the tree totals.

## Sources

- Lichess open database, standard rated games 2013-01, CC0: <https://database.lichess.org/standard/lichess_db_standard_rated_2013-01.pgn.zst> (sha256 above); licence page saved as `refs/lichess/database-lichess-org.html`.
- `lichess-org/chess-openings` (CC0): `refs/lichess/chess-openings-{a..e}.tsv`, `refs/lichess/chess-openings-README.md` (defines `dist/`'s `uci` and `epd` columns: "EPD (FEN without move numbers) of the opening position, en passant field only if legal"; "multiple entries for a single opening may be added" for transpositions; "each name has a unique shortest line"), `refs/lichess/chess-openings-bin-gen.py` (the generator: `board.epd()` per row, duplicate EPDs are a build error).
- python-chess 1.11.2, `chess.Board.epd()` (default `en_passant="legal"`, no move counters) and `push_san`, used for every key; `refs/lichess/tree-width-analysis.py` for streaming and buckets.
- Settings: ticket 05's answer (`.scratch/chessop/issues/05-confirm-destination-and-repertoire.md`) and [`tree-width-measurements.md`](tree-width-measurements.md).
