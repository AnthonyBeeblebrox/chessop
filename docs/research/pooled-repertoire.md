# Pooled repertoire: the position graph of ADR 0006 on a recent month (2026-08)

Ticket: [`.scratch/chessop/issues/17-pooled-repertoire-size.md`](../../.scratch/chessop/issues/17-pooled-repertoire-size.md). Measures the graph [ADR 0006](../adr/0006-position-graph.md) builds under [ADR 0005](../adr/0005-repertoire-rule.md)'s rule, on the sample of [`repertoire-rule-candidates-recent.md`](repertoire-rule-candidates-recent.md) (ticket 13), against the sequence tree that document measured (the `top-3 + share 5 %` cell at f = 0.02 %, book-pruned: 996 nodes / 389 lines / 17 plies at 1800-2100).
Script: [`refs/lichess/pooled-repertoire-analysis.py`](../../refs/lichess/pooled-repertoire-analysis.py) (imports the ticket 13 scripts' stream, filters, tries, width rule and book code). Generated; every number below is one run of it. No recommendation is made here.

## Method and sample

- **Source**: `lichess_db_standard_rated_2026-08.pgn.zst` (30,145,862,359 bytes, CC0), streamed over HTTP through a zstandard streaming decompressor and parsed as it arrived; nothing was written to disk. Reading stopped when band 1800-2100 had 150,000 games after filters or after 4,294,967,296 compressed bytes, whichever came first: **stopped because band 1800-2100 reached 150000 games**, after **482,224,925 compressed bytes** (1.60 % of the file) and **1,474,213 games seen**. Date range of the games seen (`UTCDate UTCTime`): 2026.08.01 00:00:00 to 2026.08.01 13:15:03.
- **Filters** (ADR 0003, as in ticket 13): both `WhiteElo` and `BlackElo` present and numeric; no `WhiteTitle`/`BlackTitle` of `BOT`; `Event` speed not Bullet or UltraBullet; both players inside the same 300-wide band, lower bound inclusive. Games dropped: bullet / ultrabullet 637,928, players in different bands 128,270, BOT title 6,683.
- **Games kept per band**: below 1200 **129,724**, 1200-1500 **162,765**, 1500-1800 **214,825**, 1800-2100 **150,000**, 2100 and above **44,018**.
- **Trie**: one move-sequence trie per band to **ply 36**, every node keyed by python-chess `Board.epd()` (`push_san` per node; nodes under a SAN token python-chess rejects dropped). band 1800-2100: 4,001,817 trie nodes, 3,700,092 distinct positions, 3,769,404 distinct (position, move) edges, 0 games dropped for bad SAN; band 1500-1800: 5,682,125 trie nodes, 5,309,999 distinct positions, 5,399,897 distinct (position, move) edges, 0 games dropped for bad SAN. Peak resident memory of the run 5.2 GB; parse 53 s, keying and measuring 222 s.
- **Pooling** (ADR 0006): a position's count is the sum of the counts of every trie node with its EPD (every move order into it, to ply 36); a (position, move) edge's count likewise. A trie node is one **move order** into its position; the **largest single order** of a position (edge) is the largest node (child-node) count among them; the **canonical order** is that most popular order (ties: first seen in the stream). A game that visits one position twice is pooled twice.
- **Build** (ADR 0005 on the graph, ADR 0006): floor **m = 0.02 % of the band's games** (unrounded threshold, count >= f x N); at every position the **main moves** are the edges with >= m pooled games, the top-3 (count desc, SAN desc ties) plus every further edge with >= 5 % of the position's pooled count; what the start position reaches over main moves (BFS; a position at depth 36 expands nothing) is the **pre-prune graph**; an edge that arrives at a position already reached at a shorter depth is added last, in BFS order of its parent, and **dropped iff it closes a cycle** over the edges already in (so the shorter path is kept; an arrival at a longer depth that closes no cycle is kept and reported); then every position with no exactly-named book position at or below it is **pruned** and what the start position still reaches is the **repertoire graph**. A main move at a kept position whose child was pruned is a **stub** (ADR 0005).
- **Sequence tree**: ticket 13's `top-3 + share 5 %` tree at the same floor, book-pruned, rebuilt here by the same code (`select_width` + `prune_to_named`); its **uncapped** sibling (every reply clearing the floor, book-pruned) defines the transposition-only misses as in ticket 13 (a named position with >= m pooled games absent even from the uncapped tree). **Merged by position** = the sequence tree's nodes merged by EPD, edges = distinct (EPD, move) pairs, as in `transpositions.md`.
- **Counting**: **positions** include the start position; **edges** are kept (position, move) pairs; **branches** = root-to-leaf paths (dynamic programming over the DAG); **leaves** = positions with no kept move; **max depth** = the longest root-to-leaf path in plies; **by depth** counts positions at their shortest depth; **internal** positions have >= 1 kept move; **discard %** = over internal positions, games reaching the position minus games continuing along kept moves, over games reaching internal positions (pooled counts); **book lines covered** = distinct named EPDs in the graph, of the book's 3810 rows.
- **Junk**: the share of a kept position's (edge's) pooled count held by its largest single move order; a kept edge is **main under no single order** when at every trie node of its parent position the per-order rule of ticket 13 (replies with >= m games in that order, top-3 plus >= 5 % of that order's games) does not select it. **Reachable by a main order** = the position is in the sequence tree *before* book-pruning (some single move order reaches it through per-order main moves).
- **Names**: a position is **exactly named** when its EPD is a book row's `epd`. Its **inherited names** are its own name if named, else the union of its parents' inherited names over the kept edges; a position with more than one inherited name is the ambiguity ADR 0006 avoids by storing exact names only. **Canonical order vs the book's line** compares the canonical order's UCI path with the row's `uci`.

## Band 1800-2100: 150,000 games, floor 0.02 % = >= 30 games

Pooled count of the start position: 150,000 (150,000 games; the difference is games that return to the start position by a piece shuffle). Positions reached at more than one ply anywhere in the trie: 3,176 of 3,700,092; among the kept positions of the repertoire graph: 15. Kept positions reached by more than one move order in the trie: 1009 of 1104.

### Size

| build | positions | edges | branches (root-to-leaf paths) | leaf positions | max depth (plies) | positions with > 1 kept in-edge | internal positions | kept moves mean / max | discard % | book lines covered (of 3810) |
|---|---|---|---|---|---|---|---|---|---|---|
| sequence tree (ticket 13: top-3 + share 5 %, book-pruned) | 996 nodes (772 distinct positions) | 995 | 389 | 389 leaves (312 distinct positions) | 17 | - | 607 | 1.64 / 7 | 16.1 | 535 |
| the same tree merged by position | 772 | 881 | 789 | 252 | 17 | 102 | 520 | 1.69 / 7 | - | 535 |
| **pooled graph (ADR 0006), book-pruned** | **1104** | **1326** | **1985** | 310 | **17** | 203 | 794 | 1.67 / 7 | 16.7 | **662** |
| pooled graph before the book pruning | 3074 | 3432 | 6018 | 1052 | 21 | 336 | 2022 | 1.70 / 7 | 13.8 | 662 |
| sequence tree before the book pruning | 2491 nodes (2008 distinct positions) | 2490 | 1057 | 1057 leaves (924 distinct positions) | 19 | - | 1434 | 1.74 / 7 | 12.7 | 535 |

Positions with a main move at all on pooled counts (any position of the trie with an edge clearing the floor): 2885. Stubs (main moves at kept positions whose child was pruned): 783, carrying 62,699 games. The pre-prune graph does not hit the ply cap of 36; the book-pruned graph does not hit it.

Positions by depth (shortest path from the start; the sequence tree by ply):

| depth | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sequence tree | 3 | 15 | 49 | 106 | 175 | 173 | 158 | 113 | 81 | 52 | 32 | 17 | 10 | 5 | 3 | 2 | 1 | 0 | 0 | 0 | 0 |
| merged by position | 3 | 15 | 46 | 85 | 119 | 123 | 116 | 85 | 65 | 46 | 32 | 17 | 8 | 5 | 3 | 2 | 1 | 0 | 0 | 0 | 0 |
| pooled graph | 3 | 15 | 50 | 101 | 152 | 171 | 161 | 133 | 115 | 82 | 55 | 30 | 14 | 9 | 6 | 4 | 2 | 0 | 0 | 0 | 0 |
| pooled graph before pruning | 3 | 15 | 60 | 162 | 308 | 442 | 519 | 463 | 390 | 283 | 182 | 114 | 63 | 32 | 16 | 7 | 4 | 3 | 3 | 2 | 2 |

Positions in the pooled graph and not in the sequence tree (**recovered by pooling**): 332 (127 of them exactly named); sequence-tree positions not in the pooled graph (**lost**): 0.

### Book coverage

Of the 996 named book positions with >= 30 pooled games at this band (ticket 13's categories against its sequence tree): how many the pooled graph holds.

| category (ticket 13, sequence tree) | book lines | in the pooled graph | still missed |
|---|---|---|---|
| in sequence tree | 535 | 535 | 0 |
| missed by width only | 266 | 19 | 247 |
| missed by transposition only | 195 | 108 | 87 |
| **all with >= floor (pooled)** | 996 | **662** | 334 |

Why the 334 are still missed: an in-edge clears the floor but is main at no parent (width): 137; main at a parent that is itself out of the graph: 132; no in-edge clears the floor (pooled): 65.

Largest still-missed named positions (up to 30), pooled games / own-order games:

| pooled | own order | name | ECO | ply | why | line |
|---|---|---|---|---|---|---|
| 5499 | 5499 | Zukertort Opening | A04 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. Nf3` |
| 4143 | 4143 | Pirc Defense | B00 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. e4 d6` |
| 2739 | 2739 | Modern Defense | B06 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. e4 g6` |
| 2682 | 2493 | Pirc Defense | B00 | 3 | main at a parent that is itself out of the graph | `1. e4 d6 2. d4` |
| 2259 | 2259 | Bird Opening | A02 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. f4` |
| 1963 | 1963 | Englund Gambit | A40 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. d4 e5` |
| 1956 | 1956 | Zukertort Opening | A06 | 2 | main at a parent that is itself out of the graph | `1. Nf3 d5` |
| 1723 | 1723 | Queen's Pawn Game: Modern Defense | A40 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. d4 g6` |
| 1674 | 1674 | Benoni Defense: Old Benoni | A43 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. d4 c5` |
| 1670 | 1670 | Nimzo-Larsen Attack | A01 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. b3` |
| 1611 | 1611 | Alekhine Defense | B02 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. e4 Nf6` |
| 1592 | 1402 | Modern Defense | B06 | 4 | main at a parent that is itself out of the graph | `1. e4 g6 2. d4 Bg7` |
| 1572 | 1572 | Hungarian Opening | A00 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. g3` |
| 1485 | 1485 | Queen's Pawn Game | A41 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. d4 d6` |
| 1481 | 1481 | Owen Defense | B00 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. e4 b6` |
| 1453 | 1364 | Pirc Defense | B00 | 4 | main at a parent that is itself out of the graph | `1. e4 d6 2. d4 Nf6` |
| 1431 | 1431 | Van't Kruijs Opening | A00 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. e3` |
| 1392 | 1392 | Nimzowitsch Defense | B00 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. e4 Nc6` |
| 1081 | 1081 | Dutch Defense | A80 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. d4 f5` |
| 930 | 930 | Zukertort Opening | A05 | 2 | main at a parent that is itself out of the graph | `1. Nf3 Nf6` |
| 875 | 875 | Bird Opening: Dutch Variation | A03 | 2 | main at a parent that is itself out of the graph | `1. f4 d5` |
| 815 | 815 | Alekhine Defense: Normal Variation | B02 | 4 | main at a parent that is itself out of the graph | `1. e4 Nf6 2. e5 Nd5` |
| 796 | 796 | Mieses Opening | A00 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. d3` |
| 708 | 501 | Blackmar-Diemer Gambit | D00 | 3 | an in-edge clears the floor but is main at no parent (width) | `1. d4 d5 2. e4` |
| 706 | 706 | Polish Opening | A00 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. b4` |
| 693 | 693 | Benoni Defense: Old Benoni | A43 | 3 | main at a parent that is itself out of the graph | `1. d4 c5 2. d5` |
| 683 | 683 | English Defense | A40 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. d4 b6` |
| 614 | 614 | Van Geet Opening | A00 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. Nc3` |
| 607 | 607 | Zukertort Opening: Sicilian Invitation | A04 | 2 | main at a parent that is itself out of the graph | `1. Nf3 c5` |
| 598 | 573 | Old Indian Defense | A41 | 3 | main at a parent that is itself out of the graph | `1. d4 d6 2. c4` |

### Cycles

Edges arriving at a position already reached at a shorter depth: **0 dropped** (each closed a cycle over the edges already in), 0 kept (closed no cycle).

### Junk admitted by pooling

Largest single move order's share of the pooled count, over the 1104 kept positions and the 1326 kept edges:

| largest single order's share | 100 % (one order) | 75-100 % | 50-75 % | 25-50 % | below 25 % | largest single order below the floor |
|---|---|---|---|---|---|---|
| kept positions | 95 | 482 | 252 | 189 | 86 | 163 |
| kept edges | 209 | 612 | 253 | 186 | 66 | 233 |

Kept positions not reachable by any single main order (absent from the sequence tree before book-pruning): 200 of 1104. Kept edges that are **main under no single move order**: 234 of 1326; kept positions whose every kept in-edge is such an edge: 165.

Kept positions where no single order holds >= 25 % of the pooled count (start position excluded): **86**; 70 of them reachable by no single main order; 70 of them entered only by edges main under no single order.

Every such position (`orders` = trie nodes with this EPD, i.e. move orders into it; `in-edges main by no order / kept in-edges`; `expands` = has a kept move):

| depth | games (pooled) | orders | largest order | name | reachable by a main order | in-edges main by no order / kept | expands | canonical order |
|---|---|---|---|---|---|---|---|---|
| 6 | 476 | 17 | 22 % | Queen's Pawn Game: London System, with e6 | yes | 0 / 3 | yes | `1. d4 d5 2. Nf3 Nf6 3. Bf4 e6` |
| 6 | 419 | 24 | 24 % | Queen's Pawn Game: Colle System | yes | 0 / 3 | yes | `1. d4 d5 2. Nf3 Nf6 3. e3 e6` |
| 6 | 109 | 15 | 20 % | (unnamed) | no | 1 / 1 | yes | `1. d4 Nf6 2. c4 d6 3. Nf3 g6` |
| 6 | 81 | 12 | 21 % | Old Indian Defense: Czech Variation, with Nc3 | no | 2 / 2 | no | `1. d4 d6 2. c4 Nf6 3. Nc3 c6` |
| 6 | 77 | 21 | 19 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. Nf3 Nf6 3. Nc3 e6` |
| 6 | 71 | 8 | 21 % | Queen's Gambit Accepted: Rosenthal Variation | no | 1 / 1 | no | `1. d4 e6 2. c4 d5 3. Nf3 dxc4` |
| 6 | 67 | 13 | 24 % | Queen's Gambit Declined: Tarrasch Defense, Pseudo-Tarrasch | no | 1 / 1 | no | `1. d4 d5 2. c4 e6 3. Nf3 c5` |
| 7 | 641 | 23 | 14 % | (unnamed) | yes | 0 / 2 | yes | `1. d4 d5 2. Bf4 Nf6 3. e3 e6 4. Nf3` |
| 7 | 224 | 24 | 24 % | (unnamed) | yes | 1 / 2 | yes | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. e3` |
| 7 | 210 | 54 | 18 % | (unnamed) | yes | 2 / 3 | yes | `1. d4 d5 2. c4 e6 3. e3 Nf6 4. Nf3` |
| 7 | 140 | 24 | 20 % | (unnamed) | no | 2 / 2 | yes | `1. d4 Nf6 2. c4 d6 3. Nc3 g6 4. Nf3` |
| 7 | 118 | 12 | 24 % | (unnamed) | no | 2 / 2 | yes | `1. d4 Nf6 2. Bf4 d6 3. e3 g6 4. Nf3` |
| 7 | 114 | 14 | 19 % | (unnamed) | no | 2 / 2 | yes | `1. d4 d5 2. Nf3 e6 3. Bf4 c5 4. e3` |
| 7 | 97 | 16 | 21 % | (unnamed) | no | 1 / 1 | yes | `1. e4 d6 2. d4 Nf6 3. Nc3 e5 4. Nf3` |
| 7 | 78 | 14 | 22 % | (unnamed) | no | 2 / 2 | yes | `1. d4 d5 2. c4 c6 3. Nc3 Bf5 4. Nf3` |
| 7 | 67 | 27 | 19 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 c6 3. Nf3 e6 4. e3` |
| 7 | 56 | 9 | 20 % | Queen's Gambit Accepted: Showalter Variation | no | 1 / 1 | no | `1. d4 d5 2. c4 dxc4 3. Nf3 Nf6 4. Nc3` |
| 7 | 49 | 25 | 16 % | Queen's Pawn Game: Veresov Attack, Classical Defense | no | 1 / 1 | no | `1. d4 d5 2. Nf3 Nf6 3. Nc3 e6 4. Bg5` |
| 7 | 37 | 13 | 22 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. cxd5` |
| 8 | 502 | 73 | 18 % | Semi-Slav Defense | yes | 0 / 3 | yes | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. Nf3 e6` |
| 8 | 362 | 41 | 21 % | Four Knights Game: Italian Variation | yes | 1 / 3 | yes | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. Nc3 Nf6` |
| 8 | 312 | 53 | 12 % | (unnamed) | yes | 2 / 3 | yes | `1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. Nf3 d6` |
| 8 | 236 | 38 | 11 % | (unnamed) | no | 1 / 1 | yes | `1. d4 Nf6 2. Bf4 e6 3. e3 d5 4. Nf3 c5` |
| 8 | 226 | 27 | 14 % | London System | yes | 1 / 2 | yes | `1. d4 Nf6 2. Nf3 g6 3. Bf4 Bg7 4. e3 d6` |
| 8 | 222 | 35 | 19 % | Queen's Gambit Declined: Ragozin Defense | yes | 0 / 1 | no | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Nf3 Bb4` |
| 8 | 131 | 44 | 13 % | (unnamed) | no | 2 / 2 | yes | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. e3 e6` |
| 8 | 116 | 28 | 20 % | Queen's Gambit Declined: Semi-Tarrasch Defense | no | 1 / 1 | yes | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Nf3 c5` |
| 8 | 87 | 48 | 8 % | (unnamed) | no | 2 / 2 | yes | `1. d4 d5 2. c4 c6 3. e3 Nf6 4. Nf3 e6` |
| 8 | 84 | 29 | 23 % | Philidor Defense: Lion Variation | no | 1 / 1 | no | `1. e4 d6 2. d4 Nf6 3. Nc3 e5 4. Nf3 Nbd7` |
| 8 | 81 | 17 | 15 % | Queen's Gambit Declined: Baltic Defense, Pseudo-Slav | no | 1 / 1 | no | `1. d4 c6 2. c4 d5 3. Nc3 Bf5 4. Nf3 e6` |
| 8 | 75 | 48 | 11 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 e6 3. e3 Nf6 4. Nf3 c5` |
| 8 | 75 | 30 | 16 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 e6 3. Nf3 Nf6 4. g3 c6` |
| 8 | 72 | 14 | 18 % | (unnamed) | no | 1 / 1 | yes | `1. d4 e6 2. Bf4 d5 3. Nf3 c5 4. e3 Nc6` |
| 8 | 65 | 10 | 23 % | Four Knights Game: Spanish Variation, Classical Variation | no | 1 / 1 | no | `1. e4 e5 2. Nf3 Nc6 3. Nc3 Nf6 4. Bb5 Bc5` |
| 8 | 62 | 29 | 13 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 e6 3. e3 Nf6 4. Nf3 Be7` |
| 8 | 55 | 23 | 15 % | Slav Defense: Exchange Variation | no | 1 / 1 | no | `1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. cxd5 cxd5` |
| 8 | 53 | 26 | 25 % | Slav Defense: Quiet Variation, Pin Defense | no | 1 / 1 | no | `1. d4 d5 2. c4 c6 3. e3 Nf6 4. Nf3 Bg4` |
| 8 | 51 | 25 | 20 % | (unnamed) | no | 1 / 1 | yes | `1. d4 Nf6 2. c4 e6 3. Nc3 d5 4. e3 c5` |
| 9 | 325 | 69 | 16 % | (unnamed) | yes | 1 / 2 | yes | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. Nf3 e6 5. Bg5` |
| 9 | 281 | 42 | 20 % | Italian Game: Giuoco Pianissimo, Italian Four Knights Variation | yes | 0 / 2 | yes | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. Nc3 Nf6 5. d3` |
| 9 | 256 | 44 | 24 % | Queen's Gambit Declined | yes | 0 / 2 | yes | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. Nf3` |
| 9 | 215 | 102 | 6 % | Semi-Slav Defense: Main Line | no | 3 / 3 | yes | `1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3 e6 5. e3` |
| 9 | 195 | 49 | 10 % | (unnamed) | no | 1 / 1 | yes | `1. d4 Nf6 2. Bf4 e6 3. e3 d5 4. Nf3 c5 5. c3` |
| 9 | 137 | 30 | 20 % | (unnamed) | no | 2 / 2 | yes | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. Nc3` |
| 9 | 133 | 53 | 17 % | (unnamed) | no | 3 / 3 | yes | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Nf3 Be7 5. e3` |
| 9 | 107 | 63 | 7 % | (unnamed) | no | 3 / 3 | yes | `1. d4 Nf6 2. c4 e6 3. Nc3 d5 4. e3 c5 5. Nf3` |
| 9 | 100 | 45 | 12 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 e6 3. Nf3 Nf6 4. g3 c6 5. Bg2` |
| 9 | 97 | 32 | 12 % | (unnamed) | no | 1 / 1 | yes | `1. d4 e6 2. Bf4 d5 3. e3 c5 4. c3 Nc6 5. Nf3` |
| 9 | 95 | 35 | 12 % | King's Indian Defense: Smyslov Variation | no | 1 / 1 | no | `1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. Nf3 d6 5. Bg5` |
| 9 | 90 | 45 | 12 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. Nf3 Bf5 5. e3` |
| 9 | 53 | 24 | 25 % | Queen's Pawn Game: Colle System, Traditional Colle | no | 1 / 1 | no | `1. d4 Nf6 2. Nf3 e6 3. e3 d5 4. Bd3 c5 5. c3` |
| 9 | 47 | 22 | 15 % | London System, with Be2 | no | 1 / 1 | yes | `1. d4 Nf6 2. Nf3 g6 3. Bf4 Bg7 4. e3 d6 5. Be2` |
| 9 | 42 | 16 | 24 % | (unnamed) | no | 1 / 1 | yes | `1. d4 Nf6 2. Nf3 g6 3. c4 Bg7 4. Nc3 d5 5. cxd5` |
| 9 | 42 | 21 | 12 % | London System, with Bd3 | no | 1 / 1 | no | `1. d4 Nf6 2. Nf3 g6 3. Bf4 Bg7 4. e3 d6 5. Bd3` |
| 9 | 40 | 23 | 20 % | King's Indian Defense: Fianchetto Variation, Delayed Fianchetto | no | 1 / 1 | no | `1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. Nf3 d6 5. g3` |
| 9 | 36 | 15 | 11 % | Queen's Gambit Declined: Semi-Tarrasch Defense, Pillsbury Variation | no | 1 / 1 | no | `1. d4 e6 2. c4 d5 3. Nc3 c5 4. Nf3 Nf6 5. Bg5` |
| 9 | 30 | 16 | 20 % | Queen's Gambit Declined: Semi-Tarrasch Defense | no | 1 / 1 | no | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Nf3 c5 5. cxd5` |
| 10 | 399 | 84 | 22 % | (unnamed) | yes | 1 / 2 | yes | `1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O` |
| 10 | 187 | 83 | 7 % | (unnamed) | no | 2 / 2 | yes | `1. d4 Nf6 2. Bf4 e6 3. e3 d5 4. Nf3 c5 5. c3 Nc6` |
| 10 | 150 | 23 | 23 % | Sicilian Defense: Taimanov Variation | yes | 1 / 2 | no | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nc3 a6` |
| 10 | 128 | 33 | 16 % | (unnamed) | no | 1 / 1 | yes | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d3 Bc5 5. Nc3 d6` |
| 10 | 112 | 66 | 9 % | Slav Defense: Quiet Variation, Schallopp Defense | no | 1 / 1 | no | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. Nf3 Bf5 5. e3 e6` |
| 10 | 96 | 41 | 17 % | Queen's Gambit Declined: Three Knights Variation | no | 1 / 1 | no | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Nf3 Be7 5. e3 O-O` |
| 10 | 83 | 55 | 7 % | Tarrasch Defense: Symmetrical Variation | no | 1 / 1 | no | `1. d4 Nf6 2. c4 e6 3. Nc3 d5 4. e3 c5 5. Nf3 Nc6` |
| 10 | 71 | 33 | 15 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. Nf3 e6 5. Bg5 Nbd7` |
| 10 | 56 | 23 | 18 % | Italian Game: Giuoco Pianissimo | no | 1 / 1 | yes | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. Nc3 O-O` |
| 10 | 54 | 40 | 7 % | Semi-Slav Defense: Normal Variation | no | 1 / 1 | no | `1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3 e6 5. e3 Nbd7` |
| 10 | 51 | 22 | 20 % | (unnamed) | no | 1 / 1 | yes | `1. d4 Nf6 2. Nf3 g6 3. c4 Bg7 4. Nc3 d5 5. cxd5 Nxd5` |
| 10 | 46 | 28 | 13 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 e6 3. Nf3 Nf6 4. g3 Be7 5. Bg2 c6` |
| 10 | 42 | 22 | 19 % | London System, with Be2 | no | 1 / 1 | no | `1. d4 Nf6 2. Nf3 g6 3. Bf4 Bg7 4. e3 O-O 5. Be2 d6` |
| 11 | 213 | 44 | 21 % | Queen's Gambit Declined: Modern Variation, Normal Line | yes | 1 / 2 | yes | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3` |
| 11 | 107 | 73 | 4 % | Queen's Pawn Game: London System | no | 1 / 1 | no | `1. d4 d5 2. Nf3 e6 3. Bf4 Nf6 4. e3 c5 5. c3 Nc6 6. Nbd2` |
| 11 | 81 | 40 | 12 % | Queen's Gambit Declined | no | 1 / 1 | no | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. Nf3 e6 5. Bg5 Nbd7 6. e3` |
| 11 | 80 | 26 | 24 % | Italian Game: Classical Variation, Giuoco Pianissimo | no | 2 / 2 | no | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d3 Bc5 5. O-O d6 6. c3` |
| 11 | 60 | 24 | 17 % | Italian Game: Classical Variation, Giuoco Pianissimo | no | 1 / 1 | no | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. d3 h6 6. c3` |
| 11 | 55 | 27 | 15 % | Italian Game: Giuoco Pianissimo | no | 1 / 1 | no | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. Nc3 O-O 6. d3` |
| 11 | 50 | 25 | 12 % | Italian Game: Giuoco Pianissimo, Canal Variation | no | 1 / 1 | no | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. Nc3 Nf6 5. d3 d6 6. Bg5` |
| 11 | 46 | 11 | 24 % | Sicilian Defense: Four Knights Variation, Exchange Variation | no | 1 / 1 | no | `1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e6 6. Nxc6` |
| 11 | 42 | 28 | 12 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 c6 3. g3 Nf6 4. Bg2 e6 5. Nf3 Be7 6. O-O` |
| 11 | 35 | 16 | 20 % | (unnamed) | no | 1 / 1 | yes | `1. d4 Nf6 2. c4 g6 3. Nc3 d5 4. Nf3 Bg7 5. cxd5 Nxd5 6. e4` |
| 12 | 68 | 44 | 18 % | Catalan Opening: Closed | no | 2 / 2 | no | `1. d4 d5 2. c4 e6 3. Nf3 Nf6 4. g3 Be7 5. Bg2 O-O 6. O-O c6` |
| 12 | 64 | 19 | 16 % | Sicilian Defense: Smith-Morra Gambit Accepted, Paulsen Formation | no | 1 / 1 | no | `1. e4 c5 2. d4 cxd4 3. c3 dxc3 4. Nxc3 Nc6 5. Nf3 e6 6. Bc4 a6` |
| 12 | 54 | 27 | 17 % | Queen's Gambit Declined: Orthodox Defense | no | 1 / 1 | no | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3 Nbd7` |
| 12 | 33 | 15 | 21 % | (unnamed) | no | 1 / 1 | yes | `1. d4 Nf6 2. c4 g6 3. Nc3 d5 4. Nf3 Bg7 5. cxd5 Nxd5 6. e4 Nxc3` |
| 13 | 78 | 38 | 18 % | Queen's Gambit Declined: Neo-Orthodox Variation, Main Line | no | 1 / 1 | yes | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3 h6 7. Bh4` |
| 14 | 34 | 22 | 18 % | Queen's Gambit Declined: Tartakower Defense | no | 1 / 1 | no | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3 h6 7. Bh4 b6` |

Kept edges main under no single move order (up to 60 of 234; `rank` = the move's rank among the parent's replies clearing the floor in that order):

| parent depth | move | games (pooled) | largest single order | share of parent | parent's orders | per-order rank | child's name | parent's canonical order |
|---|---|---|---|---|---|---|---|---|
| 4 | c4 | 64 | 25 | 19.4 % | 4 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. Nf3 d6` |
| 4 | e4 | 51 | 29 | 8.3 % | 2 | below the floor in every order | (unnamed) | `1. d4 g6 2. c4 Bg7` |
| 4 | c4 | 48 | 19 | 12.5 % | 4 | below the floor in every order | (unnamed) | `1. d4 d5 2. e3 e6` |
| 4 | d4 | 45 | 26 | 18.7 % | 2 | below the floor in every order | (unnamed) | `1. c4 Nf6 2. Nc3 e6` |
| 4 | g3 | 43 | 22 | 38.1 % | 2 | below the floor in every order | English Opening: Symmetrical Variation, Fianchetto Variation | `1. c4 Nf6 2. Nc3 c5` |
| 4 | e4 | 43 | 29 | 19.5 % | 4 | below the floor in every order | Caro-Kann Defense | `1. d4 d5 2. Nc3 c6` |
| 4 | Nf3 | 41 | 19 | 13.9 % | 4 | below the floor in every order | Philidor Defense | `1. e4 d6 2. d4 e5` |
| 4 | e3 | 36 | 22 | 26.5 % | 3 | below the floor in every order | Réti Opening: Anglo-Slav Variation, Gurevich System | `1. Nf3 d5 2. c4 c6` |
| 4 | Nf3 | 32 | 16 | 28.3 % | 2 | below the floor in every order | English Opening: Symmetrical Variation, Three Knights Variation | `1. c4 Nf6 2. Nc3 c5` |
| 5 | f5 | 259 | 231 | 5.1 % | 6 | rank 6 of an order with 4690 games | Italian Game: Rousseau Gambit | `1. e4 e5 2. Nf3 Nc6 3. Bc4` |
| 5 | g6 | 85 | 22 | 58.6 % | 10 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. c4 d6 3. Nf3` |
| 5 | g6 | 79 | 27 | 54.5 % | 6 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. Bf4 d6 3. Nf3` |
| 5 | d6 | 66 | 29 | 42.9 % | 6 | below the floor in every order | (unnamed) | `1. d4 g6 2. c4 Bg7 3. Nf3` |
| 5 | dxc4 | 60 | 19 | 12.1 % | 10 | below the floor in every order | Queen's Gambit Accepted | `1. d4 d5 2. Nf3 Nf6 3. c4` |
| 5 | dxc4 | 57 | 15 | 7.5 % | 10 | below the floor in every order | Queen's Gambit Accepted: Rosenthal Variation | `1. d4 d5 2. c4 e6 3. Nf3` |
| 5 | e6 | 52 | 19 | 31.9 % | 11 | below the floor in every order | (unnamed) | `1. d4 d5 2. e3 Nf6 3. c4` |
| 5 | c5 | 47 | 16 | 6.2 % | 10 | below the floor in every order | Queen's Gambit Declined: Tarrasch Defense, Pseudo-Tarrasch | `1. d4 d5 2. c4 e6 3. Nf3` |
| 5 | Nf6 | 46 | 27 | 19.2 % | 7 | below the floor in every order | (unnamed) | `1. e4 e5 2. Nf3 d6 3. Nc3` |
| 5 | c6 | 39 | 15 | 23.9 % | 11 | below the floor in every order | (unnamed) | `1. d4 d5 2. e3 Nf6 3. c4` |
| 5 | c6 | 39 | 17 | 9.7 % | 6 | below the floor in every order | Old Indian Defense: Czech Variation, with Nc3 | `1. d4 Nf6 2. c4 d6 3. Nc3` |
| 5 | Nxe4 | 39 | 19 | 12.5 % | 5 | below the floor in every order | Vienna Game: Frankenstein-Dracula Variation | `1. e4 e5 2. Bc4 Nf6 3. Nc3` |
| 5 | Bg4 | 36 | 9 | 21.6 % | 8 | below the floor in every order | Queen's Gambit Declined: Chigorin Defense, Main Line | `1. Nf3 Nc6 2. d4 d5 3. c4` |
| 5 | e6 | 35 | 15 | 26.7 % | 11 | below the floor in every order | (unnamed) | `1. d4 d5 2. Nf3 Nf6 3. Nc3` |
| 5 | c6 | 33 | 17 | 13.4 % | 10 | below the floor in every order | (unnamed) | `1. d4 d5 2. c4 e6 3. e3` |
| 5 | Nf6 | 32 | 15 | 27.8 % | 5 | below the floor in every order | Old Indian Defense: Czech Variation, with Nc3 | `1. d4 d6 2. c4 c6 3. Nc3` |
| 5 | c6 | 32 | 25 | 17.1 % | 4 | below the floor in every order | English Opening: King's English Variation, Two Knights Variation, Keres Variation | `1. c4 e5 2. Nc3 Nf6 3. g3` |
| 5 | Bb4 | 32 | 28 | 17.1 % | 4 | below the floor in every order | English Opening: King's English Variation, Two Knights Variation, Smyslov System | `1. c4 e5 2. Nc3 Nf6 3. g3` |
| 5 | Bb4 | 32 | 14 | 10.3 % | 5 | below the floor in every order | Vienna Game: Stanley Variation, Reversed Spanish | `1. e4 e5 2. Bc4 Nf6 3. Nc3` |
| 5 | Nf6 | 31 | 8 | 19.5 % | 11 | below the floor in every order | Czech Defense | `1. e4 d6 2. d4 c6 3. Nc3` |
| 5 | cxd4 | 30 | 28 | 81.1 % | 2 | below the floor in every order | Sicilian Defense: Smith-Morra Gambit Declined, Center Formation | `1. e4 c5 2. c3 e5 3. d4` |
| 6 | e3 | 82 | 22 | 73.2 % | 11 | below the floor in every order | (unnamed) | `1. d4 d5 2. Nf3 e6 3. Bf4 c5` |
| 6 | d4 | 76 | 27 | 43.7 % | 10 | below the floor in every order | (unnamed) | `1. e4 c5 2. Nf3 Nc6 3. Nc3 d6` |
| 6 | Nc3 | 73 | 11 | 67.0 % | 15 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. c4 d6 3. Nf3 g6` |
| 6 | d4 | 71 | 16 | 44.1 % | 17 | below the floor in every order | (unnamed) | `1. e4 e5 2. Nf3 Nf6 3. Nc3 d6` |
| 6 | Nc3 | 70 | 29 | 32.6 % | 19 | below the floor in every order | (unnamed) | `1. d4 d5 2. c4 e6 3. e3 Nf6` |
| 6 | d3 | 69 | 28 | 55.2 % | 7 | below the floor in every order | Bishop's Opening: Vienna Hybrid, Spielmann Attack | `1. e4 e5 2. Bc4 Nf6 3. Nc3 Bc5` |
| 6 | Nc3 | 67 | 22 | 45.0 % | 16 | below the floor in every order | (unnamed) | `1. d4 d5 2. c4 c6 3. e3 Nf6` |
| 6 | e3 | 65 | 18 | 67.7 % | 9 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. Bf4 d6 3. Nf3 g6` |
| 6 | Nf3 | 62 | 28 | 20.7 % | 11 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. c4 d6 3. Nc3 g6` |
| 6 | c4 | 62 | 13 | 14.8 % | 24 | below the floor in every order | (unnamed) | `1. d4 d5 2. Nf3 Nf6 3. e3 e6` |
| 6 | h3 | 58 | 28 | 50.4 % | 3 | below the floor in every order | (unnamed) | `1. e4 c6 2. Nf3 d5 3. Nc3 Bg4` |
| 6 | Nc3 | 55 | 14 | 61.8 % | 11 | below the floor in every order | (unnamed) | `1. d4 g6 2. c4 Bg7 3. Nf3 d6` |
| 6 | d4 | 54 | 24 | 40.0 % | 8 | below the floor in every order | (unnamed) | `1. e4 c5 2. Nf3 Nc6 3. Nc3 g6` |
| 6 | Nf3 | 53 | 28 | 47.3 % | 6 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. Bf4 d6 3. e3 g6` |
| 6 | e3 | 49 | 12 | 5.7 % | 28 | below the floor in every order | (unnamed) | `1. d4 d5 2. c4 e6 3. Nf3 Nf6` |
| 6 | d4 | 49 | 29 | 38.6 % | 9 | below the floor in every order | (unnamed) | `1. e4 c5 2. Nf3 d6 3. Nc3 Nf6` |
| 6 | e4 | 45 | 17 | 31.9 % | 5 | below the floor in every order | Slav Defense: Slav Gambit, Alekhine Attack | `1. d4 d5 2. c4 dxc4 3. Nc3 c6` |
| 6 | exd5 | 43 | 26 | 7.2 % | 19 | below the floor in every order | French Defense: Classical Variation, Delayed Exchange Variation | `1. e4 e6 2. d4 d5 3. Nc3 Nf6` |
| 6 | Nf3 | 43 | 21 | 22.3 % | 4 | below the floor in every order | Queen's Pawn Game: London System | `1. d4 Nf6 2. Bf4 d5 3. e3 c5` |
| 6 | Nc3 | 40 | 9 | 48.8 % | 12 | below the floor in every order | (unnamed) | `1. d4 d5 2. c4 c6 3. Nf3 Bf5` |
| 6 | Nc3 | 39 | 16 | 36.1 % | 10 | below the floor in every order | Queen's Indian Defense: Kasparov Variation | `1. d4 Nf6 2. c4 e6 3. Nf3 b6` |
| 6 | Nf3 | 38 | 17 | 30.2 % | 4 | below the floor in every order | (unnamed) | `1. d4 d5 2. c4 c6 3. Nc3 Bf5` |
| 6 | d5 | 38 | 29 | 60.3 % | 6 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. c4 e6 3. Nc3 c5` |
| 6 | Nc3 | 38 | 11 | 38.0 % | 8 | below the floor in every order | Queen's Gambit Accepted: Showalter Variation | `1. d4 d5 2. c4 dxc4 3. Nf3 Nf6` |
| 6 | d4 | 38 | 25 | 71.7 % | 3 | below the floor in every order | (unnamed) | `1. c4 Nf6 2. Nc3 g6 3. e4 d6` |
| 6 | e3 | 37 | 18 | 8.0 % | 25 | below the floor in every order | Slav Defense: Quiet Variation | `1. d4 d5 2. c4 c6 3. Nf3 Nf6` |
| 6 | cxd5 | 37 | 8 | 8.0 % | 25 | below the floor in every order | (unnamed) | `1. d4 d5 2. c4 c6 3. Nf3 Nf6` |
| 6 | Nc3 | 37 | 18 | 37.4 % | 8 | below the floor in every order | Nimzo-Indian Defense: Three Knights Variation | `1. d4 Nf6 2. c4 e6 3. Nf3 Bb4+` |
| 6 | Bg5 | 37 | 8 | 48.1 % | 21 | below the floor in every order | Queen's Pawn Game: Veresov Attack, Classical Defense | `1. d4 d5 2. Nf3 Nf6 3. Nc3 e6` |
| 6 | e3 | 36 | 18 | 36.0 % | 8 | below the floor in every order | Queen's Gambit Accepted: Normal Variation | `1. d4 d5 2. c4 dxc4 3. Nf3 Nf6` |

### Names

- Exactly named kept positions: **662 of 1104** (60.0 %); 442 unnamed (the start position included).
- Unnamed kept positions whose inherited names (over every kept path into them) are more than one book name: **159**; the widest carries 10 names.
- Named kept positions whose canonical (most popular) order differs from the book's own line: **107 of 662**; the book's own order has no game at all in this band for 10 of the named kept positions and fewer than the floor for another 121.

Unnamed positions with more than one inherited name (up to 40, by depth then games):

| depth | games (pooled) | names | inherited names | canonical order |
|---|---|---|---|---|
| 3 | 1562 | 2 | English Opening: Agincourt Defense; Horwitz Defense | `1. d4 e6 2. c4` |
| 4 | 1873 | 3 | English Opening: Agincourt Defense; Horwitz Defense; Indian Defense: Normal Variation | `1. d4 Nf6 2. c4 e6` |
| 4 | 1211 | 2 | Indian Defense: Accelerated London System; Queen's Pawn Game: Accelerated London System | `1. d4 d5 2. Bf4 Nf6` |
| 4 | 1042 | 2 | Horwitz Defense; Queen's Pawn Game: Zukertort Variation | `1. d4 d5 2. Nf3 e6` |
| 4 | 760 | 2 | Horwitz Defense; Queen's Pawn Game: Accelerated London System | `1. d4 d5 2. Bf4 e6` |
| 4 | 626 | 2 | Horwitz Defense; Indian Defense: Knights Variation | `1. d4 Nf6 2. Nf3 e6` |
| 4 | 428 | 2 | Horwitz Defense; Indian Defense: Accelerated London System | `1. d4 Nf6 2. Bf4 e6` |
| 4 | 385 | 2 | Horwitz Defense; Queen's Pawn Game | `1. d4 d5 2. e3 e6` |
| 4 | 179 | 2 | English Opening: Agincourt Defense; Horwitz Defense | `1. d4 e6 2. c4 c5` |
| 4 | 113 | 2 | English Opening: Anglo-Indian Defense, Queen's Knight Variation; English Opening: Symmetrical Variation, Normal Variation | `1. c4 Nf6 2. Nc3 c5` |
| 5 | 1327 | 2 | French Defense: Franco-Sicilian Defense; Sicilian Defense: French Variation | `1. e4 c5 2. Nf3 e6 3. d4` |
| 5 | 1280 | 4 | English Opening: Agincourt Defense; English Opening: Anglo-Indian Defense, Hedgehog System; Horwitz Defense; Indian Defense: Normal Variation | `1. d4 Nf6 2. c4 e6 3. Nc3` |
| 5 | 821 | 2 | Indian Defense: Accelerated London System; Queen's Pawn Game: Accelerated London System | `1. d4 d5 2. Bf4 Nf6 3. e3` |
| 5 | 756 | 3 | Horwitz Defense; Queen's Gambit Declined; Queen's Pawn Game: Zukertort Variation | `1. d4 d5 2. c4 e6 3. Nf3` |
| 5 | 665 | 2 | Sicilian Defense: Alapin Variation; Sicilian Defense: Old Sicilian | `1. e4 c5 2. Nf3 Nc6 3. c3` |
| 5 | 556 | 2 | Sicilian Defense: Closed, Traditional; Sicilian Defense: Old Sicilian | `1. e4 c5 2. Nf3 Nc6 3. Nc3` |
| 5 | 515 | 2 | Horwitz Defense; Queen's Pawn Game: Accelerated London System | `1. d4 d5 2. Bf4 e6 3. e3` |
| 5 | 497 | 2 | Queen's Gambit Declined: Marshall Defense; Queen's Pawn Game: Symmetrical Variation | `1. d4 d5 2. Nf3 Nf6 3. c4` |
| 5 | 471 | 2 | Bishop's Opening; Vienna Game: Max Lange Defense | `1. e4 e5 2. Nc3 Nc6 3. Bc4` |
| 5 | 361 | 3 | Horwitz Defense; Queen's Pawn Game; Queen's Pawn Game: Zukertort Variation | `1. d4 d5 2. Nf3 e6 3. e3` |
| 5 | 361 | 2 | Sicilian Defense: Closed; Sicilian Defense: French Variation | `1. e4 c5 2. Nf3 e6 3. Nc3` |
| 5 | 309 | 2 | French Defense: Franco-Sicilian Defense; Sicilian Defense: Alapin Variation | `1. e4 c5 2. c3 e6 3. d4` |
| 5 | 303 | 2 | Horwitz Defense; Indian Defense: Accelerated London System | `1. d4 Nf6 2. Bf4 e6 3. e3` |
| 5 | 258 | 2 | Sicilian Defense: Closed; Sicilian Defense: Modern Variations | `1. e4 c5 2. Nf3 d6 3. Nc3` |
| 5 | 246 | 3 | Horwitz Defense; Queen's Gambit Declined; Queen's Pawn Game | `1. d4 d5 2. c4 e6 3. e3` |
| 5 | 240 | 2 | Philidor Defense; Vienna Game | `1. e4 e5 2. Nf3 d6 3. Nc3` |
| 5 | 203 | 2 | English Opening: Agincourt Defense; Horwitz Defense | `1. d4 c5 2. d5 e6 3. c4` |
| 5 | 163 | 2 | Queen's Gambit Declined: Marshall Defense; Queen's Pawn Game | `1. d4 d5 2. e3 Nf6 3. c4` |
| 5 | 145 | 2 | Indian Defense: Wade-Tartakower Defense; Old Indian Defense | `1. d4 Nf6 2. c4 d6 3. Nf3` |
| 5 | 145 | 2 | Indian Defense: Accelerated London System; Indian Defense: Wade-Tartakower Defense | `1. d4 Nf6 2. Bf4 d6 3. Nf3` |
| 6 | 1182 | 2 | Queen's Gambit Declined: Marshall Defense; Slav Defense | `1. d4 d5 2. c4 c6 3. Nc3 Nf6` |
| 6 | 953 | 2 | English Opening: Great Snake Variation; King's Indian Defense | `1. d4 Nf6 2. c4 g6 3. Nc3 Bg7` |
| 6 | 854 | 6 | Horwitz Defense; Indian Defense: Anti-Nimzo-Indian; Queen's Gambit Declined; Queen's Gambit Declined: Marshall Defense; Queen's Pawn Game: Symmetrical Variation; Queen's Pawn Game: Zukertort Variation | `1. d4 d5 2. c4 e6 3. Nf3 Nf6` |
| 6 | 502 | 3 | Horwitz Defense; Indian Defense: Accelerated London System; Queen's Pawn Game: Accelerated London System | `1. d4 d5 2. Bf4 Nf6 3. e3 e6` |
| 6 | 465 | 3 | Queen's Gambit Declined: Marshall Defense; Queen's Pawn Game: Symmetrical Variation; Slav Defense: Modern Line | `1. d4 d5 2. c4 c6 3. Nf3 Nf6` |
| 6 | 410 | 2 | Sicilian Defense: Alapin Variation; Sicilian Defense: Smith-Morra Gambit | `1. e4 c5 2. c3 Nc6 3. d4 cxd4` |
| 6 | 300 | 2 | King's Indian Defense; Old Indian Defense | `1. d4 Nf6 2. c4 d6 3. Nc3 g6` |
| 6 | 293 | 4 | Sicilian Defense: Closed; Sicilian Defense: Closed, Traditional; Sicilian Defense: French Variation; Sicilian Defense: Old Sicilian | `1. e4 c5 2. Nf3 Nc6 3. Nc3 e6` |
| 6 | 226 | 4 | Horwitz Defense; Queen's Gambit Declined; Queen's Pawn Game: Zukertort Variation; Slav Defense: Modern Line | `1. d4 d5 2. c4 c6 3. Nf3 e6` |
| 6 | 215 | 4 | Horwitz Defense; Queen's Gambit Declined; Queen's Gambit Declined: Marshall Defense; Queen's Pawn Game | `1. d4 d5 2. c4 e6 3. e3 Nf6` |

Named positions whose canonical order is not the book's line (up to 40, by pooled games; games in the canonical order / in the book's order):

| pooled | canonical order games | book order games | name | ECO | canonical order | book's line |
|---|---|---|---|---|---|---|
| 1598 | 958 | 554 | French Defense: Exchange Variation | C01 | `1. e4 e6 2. Nf3 d5 3. exd5 exd5 4. d4` | `1. e4 e6 2. d4 d5 3. exd5 exd5 4. Nf3` |
| 1178 | 828 | 247 | Caro-Kann Defense: Main Line | B15 | `1. e4 c6 2. d4 d5 3. Nc3 dxe4 4. Nxe4` | `1. e4 c6 2. d4 d5 3. Nd2 dxe4 4. Nxe4` |
| 921 | 269 | 55 | Queen's Gambit Declined: Three Knights Variation | D37 | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Nf3` | `1. d4 Nf6 2. c4 e6 3. Nf3 d5 4. Nc3` |
| 835 | 450 | 351 | Queen's Pawn Game: Chigorin Variation | A45 | `1. d4 d5 2. Nc3 Nf6` | `1. d4 Nf6 2. Nc3 d5` |
| 764 | 511 | 198 | Caro-Kann Defense: Exchange Variation | B13 | `1. e4 c6 2. Nf3 d5 3. exd5 cxd5 4. d4 Nc6` | `1. e4 c6 2. d4 d5 3. exd5 cxd5 4. Nf3 Nc6` |
| 729 | 315 | 100 | Slav Defense: Three Knights Variation | D15 | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. Nf3` | `1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3` |
| 643 | 252 | 233 | Semi-Slav Defense: Accelerated Move Order | D31 | `1. d4 d5 2. c4 c6 3. Nc3 e6` | `1. d4 d5 2. c4 e6 3. Nc3 c6` |
| 504 | 300 | 196 | Caro-Kann Defense: Two Knights Attack | B10 | `1. e4 c6 2. Nf3 d5 3. Nc3` | `1. e4 c6 2. Nc3 d5 3. Nf3` |
| 502 | 89 | 40 | Semi-Slav Defense | D43 | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. Nf3 e6` | `1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3 e6` |
| 476 | 106 | 66 | Queen's Pawn Game: London System, with e6 | D02 | `1. d4 d5 2. Nf3 Nf6 3. Bf4 e6` | `1. d4 d5 2. Nf3 e6 3. Bf4 Nf6` |
| 401 | 217 | 37 | Rat Defense: Small Center Defense | C00 | `1. e4 e6 2. d4 d6` | `1. d4 e6 2. e4 d6` |
| 377 | 276 | 70 | Caro-Kann Defense: Classical Variation | B18 | `1. e4 c6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 Bf5` | `1. e4 c6 2. d4 d5 3. Nd2 dxe4 4. Nxe4 Bf5` |
| 363 | 163 | 137 | King's Indian Defense: Normal Variation, King's Knight Variation | E60 | `1. d4 Nf6 2. c4 g6 3. Nf3` | `1. d4 Nf6 2. Nf3 g6 3. c4` |
| 338 | 299 | 14 | Scotch Game: Lolli Variation | C44 | `1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4` | `1. e4 e5 2. Nf3 Nc6 3. d4 Nxd4 4. Nxd4 exd4 5. Qxd4` |
| 333 | 163 | 146 | French Defense: Exchange Variation | C01 | `1. e4 e6 2. Nc3 d5 3. exd5 exd5 4. d4` | `1. e4 e6 2. d4 d5 3. exd5 exd5 4. Nc3` |
| 325 | 154 | 81 | Queen's Gambit Declined: Exchange Variation | D35 | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. cxd5` | `1. d4 Nf6 2. c4 e6 3. Nc3 d5 4. cxd5` |
| 323 | 170 | 87 | Scotch Game: Scotch Gambit, Dubois Réti Defense | C44 | `1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Bc4 Nf6` | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4` |
| 311 | 159 | 120 | Vienna Game: Stanley Variation | C26 | `1. e4 e5 2. Bc4 Nf6 3. Nc3` | `1. e4 e5 2. Nc3 Nf6 3. Bc4` |
| 281 | 56 | 20 | Italian Game: Giuoco Pianissimo, Italian Four Knights Variation | C50 | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. Nc3 Nf6 5. d3` | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. d3 Nf6 5. Nc3` |
| 271 | 126 | 100 | Italian Game: Classical Variation, Giuoco Pianissimo | C54 | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d3 Bc5 5. c3` | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3` |
| 249 | 76 | 38 | Sicilian Defense: Four Knights Variation | B45 | `1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e6` | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nc3 Nf6` |
| 232 | 102 | 16 | Bishop's Opening: Vienna Hybrid | C24 | `1. e4 e5 2. Nc3 Nc6 3. Bc4 Nf6 4. d3` | `1. e4 e5 2. Bc4 Nf6 3. d3 Nc6 4. Nc3` |
| 222 | 42 | 19 | Queen's Gambit Declined: Ragozin Defense | D38 | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Nf3 Bb4` | `1. d4 Nf6 2. c4 e6 3. Nf3 d5 4. Nc3 Bb4` |
| 221 | 88 | 44 | Queen's Gambit Declined: Exchange Variation, Positional Variation | D35 | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. cxd5 exd5 5. Bg5` | `1. d4 Nf6 2. c4 e6 3. Nc3 d5 4. cxd5 exd5 5. Bg5` |
| 220 | 134 | 76 | King's Gambit Accepted: MacLeod Defense | C34 | `1. e4 e5 2. f4 Nc6 3. Nf3 exf4` | `1. e4 e5 2. f4 exf4 3. Nf3 Nc6` |
| 215 | 12 | 10 | Semi-Slav Defense: Main Line | D45 | `1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3 e6 5. e3` | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. e3 e6 5. Nf3` |
| 213 | 45 | 3 | Queen's Gambit Declined: Modern Variation, Normal Line | D55 | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3` | `1. d4 Nf6 2. c4 e6 3. Nf3 d5 4. Nc3 Be7 5. Bg5 O-O 6. e3` |
| 208 | 66 | 64 | Four Knights Game: Spanish Variation | C48 | `1. e4 e5 2. Nf3 Nf6 3. Nc3 Nc6 4. Bb5` | `1. e4 e5 2. Nf3 Nc6 3. Nc3 Nf6 4. Bb5` |
| 200 | 121 | 73 | Dutch Defense: Classical Variation | A84 | `1. d4 e6 2. c4 f5` | `1. d4 f5 2. c4 e6` |
| 188 | 110 | 78 | English Opening: Symmetrical Variation | A30 | `1. Nf3 c5 2. c4` | `1. c4 c5 2. Nf3` |
| 183 | 86 | 78 | King's Gambit Accepted: Modern Defense | C36 | `1. e4 e5 2. f4 d5 3. exd5 exf4 4. Nf3` | `1. e4 e5 2. f4 exf4 3. Nf3 d5 4. exd5` |
| 164 | 78 | 76 | Queen's Pawn Game: Anglo-Slav Opening | A40 | `1. d4 d6 2. c4 c6` | `1. d4 c6 2. c4 d6` |
| 162 | 109 | 49 | Nimzowitsch Defense: Scandinavian Variation, Exchange Variation | B00 | `1. e4 d5 2. exd5 Qxd5 3. d4 Nc6` | `1. e4 Nc6 2. d4 d5 3. exd5 Qxd5` |
| 145 | 67 | 34 | English Opening: Agincourt Defense | A13 | `1. Nf3 d5 2. c4 e6` | `1. c4 e6 2. Nf3 d5` |
| 141 | 62 | 41 | Slav Defense | D10 | `1. d4 d5 2. c4 dxc4 3. Nc3 c6` | `1. d4 d5 2. c4 c6 3. Nc3 dxc4` |
| 138 | 83 | 55 | English Opening: Agincourt Defense | A13 | `1. Nf3 e6 2. c4` | `1. c4 e6 2. Nf3` |
| 138 | 73 | 52 | Dutch Defense: Rubinstein Variation | A84 | `1. d4 e6 2. c4 f5 3. Nc3` | `1. d4 f5 2. c4 e6 3. Nc3` |
| 137 | 64 | 43 | Italian Game: Classical Variation, Giuoco Pianissimo | C54 | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d3 Bc5 5. c3 d6` | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 d6` |
| 123 | 64 | 48 | Scotch Game: Benima Defense | C44 | `1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Bc4 Be7` | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Be7 4. d4 exd4` |
| 117 | 81 | 27 | Caro-Kann Defense: Karpov Variation | B17 | `1. e4 c6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 Nd7` | `1. e4 c6 2. d4 d5 3. Nd2 dxe4 4. Nxe4 Nd7` |

### Per-colour split

Side to move is part of the EPD; a learner position is one where the learner is to move, so the record key's colour is the side to move.

| kept positions | White to move | Black to move |
|---|---|---|
| kept positions | 546 | 558 |
| internal (with a kept move) | 398 | 396 |
| leaves | 148 | 162 |
| exactly named | 331 | 331 |
| recovered (not in the sequence tree) | 167 | 165 |

## Band 1500-1800: 214,825 games, floor 0.02 % = >= 43 games

Pooled count of the start position: 214,825 (214,825 games; the difference is games that return to the start position by a piece shuffle). Positions reached at more than one ply anywhere in the trie: 4,447 of 5,309,999; among the kept positions of the repertoire graph: 11. Kept positions reached by more than one move order in the trie: 696 of 780.

### Size

| build | positions | edges | branches (root-to-leaf paths) | leaf positions | max depth (plies) | positions with > 1 kept in-edge | internal positions | kept moves mean / max | discard % | book lines covered (of 3810) |
|---|---|---|---|---|---|---|---|---|---|---|
| sequence tree (ticket 13: top-3 + share 5 %, book-pruned) | 729 nodes (561 distinct positions) | 728 | 316 | 316 leaves (252 distinct positions) | 13 | - | 413 | 1.76 / 7 | 16.8 | 424 |
| the same tree merged by position | 561 | 646 | 488 | 210 | 13 | 81 | 351 | 1.84 / 7 | - | 424 |
| **pooled graph (ADR 0006), book-pruned** | **780** | **960** | **1070** | 241 | **15** | 163 | 539 | 1.78 / 7 | 17.4 | **505** |
| pooled graph before the book pruning | 2658 | 2988 | 4304 | 1013 | 17 | 309 | 1645 | 1.82 / 8 | 13.9 | 505 |
| sequence tree before the book pruning | 2246 nodes (1818 distinct positions) | 2245 | 1030 | 1030 leaves (897 distinct positions) | 15 | - | 1216 | 1.85 / 8 | 12.9 | 424 |

Positions with a main move at all on pooled counts (any position of the trie with an edge clearing the floor): 2335. Stubs (main moves at kept positions whose child was pruned): 689, carrying 94,304 games. The pre-prune graph does not hit the ply cap of 36; the book-pruned graph does not hit it.

Positions by depth (shortest path from the start; the sequence tree by ply):

| depth | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sequence tree | 3 | 16 | 47 | 95 | 150 | 148 | 111 | 73 | 46 | 25 | 10 | 3 | 1 | 0 | 0 | 0 | 0 |
| merged by position | 3 | 16 | 45 | 78 | 107 | 109 | 72 | 54 | 37 | 25 | 10 | 3 | 1 | 0 | 0 | 0 | 0 |
| pooled graph | 3 | 16 | 48 | 90 | 133 | 141 | 117 | 92 | 66 | 43 | 21 | 5 | 2 | 1 | 1 | 0 | 0 |
| pooled graph before pruning | 3 | 16 | 61 | 166 | 310 | 444 | 493 | 428 | 326 | 208 | 110 | 58 | 15 | 9 | 8 | 1 | 1 |

Positions in the pooled graph and not in the sequence tree (**recovered by pooling**): 223 (85 of them exactly named); sequence-tree positions not in the pooled graph (**lost**): 4.

Lost positions (ply and games in the sequence tree's order; why, on pooled counts):

| ply | games (pooled) | games (tree order) | name | why | line (tree order) |
|---|---|---|---|---|---|
| 6 | 453 | 45 | Italian Game: Rousseau Gambit | in-edge main at no parent on pooled counts | 1. e4 e5 2. Bc4 Nc6 3. Nf3 f5 |
| 5 | 223 | 211 | French Defense: Tarrasch Variation | in-edge main at no parent on pooled counts | 1. e4 e6 2. d4 d5 3. Nd2 |
| 6 | 75 | 71 | French Defense: Tarrasch Variation, Closed Variation | parent out of the graph or edge dropped | 1. e4 e6 2. d4 d5 3. Nd2 Nf6 |
| 6 | 67 | 61 | French Defense: Tarrasch Variation, Open System | parent out of the graph or edge dropped | 1. e4 e6 2. d4 d5 3. Nd2 c5 |

### Book coverage

Of the 793 named book positions with >= 43 pooled games at this band (ticket 13's categories against its sequence tree): how many the pooled graph holds.

| category (ticket 13, sequence tree) | book lines | in the pooled graph | still missed |
|---|---|---|---|
| in sequence tree | 424 | 420 | 4 |
| missed by width only | 234 | 14 | 220 |
| missed by transposition only | 135 | 71 | 64 |
| **all with >= floor (pooled)** | 793 | **505** | 288 |

Why the 288 are still missed: an in-edge clears the floor but is main at no parent (width): 129; main at a parent that is itself out of the graph: 104; no in-edge clears the floor (pooled): 55.

Largest still-missed named positions (up to 30), pooled games / own-order games:

| pooled | own order | name | ECO | ply | why | line |
|---|---|---|---|---|---|---|
| 5158 | 5158 | Zukertort Opening | A04 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. Nf3` |
| 4913 | 4913 | Pirc Defense | B00 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. e4 d6` |
| 4127 | 4127 | Modern Defense | B06 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. e4 g6` |
| 3136 | 3136 | Van't Kruijs Opening | A00 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. e3` |
| 2895 | 2895 | Owen Defense | B00 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. e4 b6` |
| 2690 | 2690 | Hungarian Opening | A00 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. g3` |
| 2591 | 2591 | Bird Opening | A02 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. f4` |
| 2565 | 2565 | Queen's Pawn Game: Modern Defense | A40 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. d4 g6` |
| 2492 | 2239 | Pirc Defense | B00 | 3 | main at a parent that is itself out of the graph | `1. e4 d6 2. d4` |
| 2425 | 2425 | Nimzo-Larsen Attack | A01 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. b3` |
| 2005 | 1676 | Modern Defense | B06 | 4 | main at a parent that is itself out of the graph | `1. e4 g6 2. d4 Bg7` |
| 1981 | 1981 | Zukertort Opening | A06 | 2 | main at a parent that is itself out of the graph | `1. Nf3 d5` |
| 1729 | 1729 | Benoni Defense: Old Benoni | A43 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. d4 c5` |
| 1694 | 1694 | Nimzowitsch Defense | B00 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. e4 Nc6` |
| 1636 | 1636 | Queen's Pawn Game | A41 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. d4 d6` |
| 1465 | 1380 | King's Pawn Game: Leonardis Variation | C20 | 3 | main at a parent that is itself out of the graph | `1. e4 e5 2. d3` |
| 1408 | 1408 | Alekhine Defense | B02 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. e4 Nf6` |
| 1276 | 1172 | Pirc Defense | B00 | 4 | main at a parent that is itself out of the graph | `1. e4 d6 2. d4 Nf6` |
| 1215 | 967 | Blackmar-Diemer Gambit | D00 | 3 | an in-edge clears the floor but is main at no parent (width) | `1. d4 d5 2. e4` |
| 1146 | 1146 | English Defense | A40 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. d4 b6` |
| 1141 | 1141 | Polish Opening | A00 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. b4` |
| 1107 | 1107 | Dutch Defense | A80 | 2 | an in-edge clears the floor but is main at no parent (width) | `1. d4 f5` |
| 1096 | 1096 | Mieses Opening | A00 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. d3` |
| 1077 | 1077 | Bird Opening: Dutch Variation | A03 | 2 | main at a parent that is itself out of the graph | `1. f4 d5` |
| 1036 | 969 | Ponziani Opening | C44 | 5 | an in-edge clears the floor but is main at no parent (width) | `1. e4 e5 2. Nf3 Nc6 3. c3` |
| 939 | 939 | King's Pawn Game: Busch-Gass Gambit | C40 | 4 | an in-edge clears the floor but is main at no parent (width) | `1. e4 e5 2. Nf3 Bc5` |
| 880 | 879 | Elephant Gambit | C40 | 4 | an in-edge clears the floor but is main at no parent (width) | `1. e4 e5 2. Nf3 d5` |
| 800 | 800 | Nimzo-Larsen Attack: Modern Variation | A01 | 2 | main at a parent that is itself out of the graph | `1. b3 e5` |
| 792 | 713 | Nimzowitsch Defense: Declined Variation | B00 | 3 | main at a parent that is itself out of the graph | `1. e4 Nc6 2. Nf3` |
| 687 | 687 | Grob Opening | A00 | 1 | an in-edge clears the floor but is main at no parent (width) | `1. g4` |

### Cycles

Edges arriving at a position already reached at a shorter depth: **0 dropped** (each closed a cycle over the edges already in), 0 kept (closed no cycle).

### Junk admitted by pooling

Largest single move order's share of the pooled count, over the 780 kept positions and the 960 kept edges:

| largest single order's share | 100 % (one order) | 75-100 % | 50-75 % | 25-50 % | below 25 % | largest single order below the floor |
|---|---|---|---|---|---|---|
| kept positions | 84 | 352 | 173 | 127 | 44 | 108 |
| kept edges | 180 | 467 | 171 | 115 | 27 | 162 |

Kept positions not reachable by any single main order (absent from the sequence tree before book-pruning): 128 of 780. Kept edges that are **main under no single move order**: 162 of 960; kept positions whose every kept in-edge is such an edge: 111.

Kept positions where no single order holds >= 25 % of the pooled count (start position excluded): **44**; 32 of them reachable by no single main order; 32 of them entered only by edges main under no single order.

Every such position (`orders` = trie nodes with this EPD, i.e. move orders into it; `in-edges main by no order / kept in-edges`; `expands` = has a kept move):

| depth | games (pooled) | orders | largest order | name | reachable by a main order | in-edges main by no order / kept | expands | canonical order |
|---|---|---|---|---|---|---|---|---|
| 6 | 536 | 25 | 18 % | Queen's Pawn Game: Colle System | yes | 0 / 3 | yes | `1. d4 d5 2. Nf3 Nf6 3. e3 e6` |
| 6 | 511 | 17 | 19 % | Queen's Pawn Game: London System, with e6 | yes | 0 / 3 | yes | `1. d4 d5 2. Bf4 Nf6 3. Nf3 e6` |
| 6 | 179 | 23 | 19 % | (unnamed) | no | 2 / 2 | yes | `1. d4 d5 2. Nf3 Nf6 3. Nc3 e6` |
| 6 | 82 | 13 | 24 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d6 2. c4 Nf6 3. Nf3 g6` |
| 7 | 700 | 23 | 19 % | (unnamed) | yes | 0 / 2 | yes | `1. d4 d5 2. Bf4 Nf6 3. e3 e6 4. Nf3` |
| 7 | 278 | 23 | 21 % | Queen's Pawn Game: Colle System | yes | 0 / 1 | yes | `1. d4 d5 2. Nf3 Nf6 3. e3 e6 4. Bd3` |
| 7 | 159 | 25 | 25 % | (unnamed) | no | 2 / 2 | yes | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. e3` |
| 7 | 106 | 27 | 16 % | Queen's Pawn Game: Veresov Attack, Classical Defense | no | 1 / 1 | no | `1. d4 d5 2. Nf3 Nf6 3. Nc3 e6 4. Bg5` |
| 7 | 102 | 17 | 21 % | (unnamed) | no | 2 / 2 | yes | `1. d4 d6 2. c4 Nf6 3. Nc3 g6 4. Nf3` |
| 8 | 923 | 47 | 24 % | Four Knights Game: Italian Variation | yes | 1 / 3 | yes | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. Nc3 Nf6` |
| 8 | 283 | 57 | 16 % | Semi-Slav Defense | yes | 2 / 3 | yes | `1. d4 d5 2. c4 c6 3. Nc3 e6 4. Nf3 Nf6` |
| 8 | 253 | 40 | 14 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. Bf4 Nf6 3. e3 e6 4. Nf3 c5` |
| 8 | 249 | 30 | 21 % | Queen's Gambit Declined: Ragozin Defense | yes | 0 / 1 | no | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Nf3 Bb4` |
| 8 | 249 | 27 | 12 % | London System | no | 2 / 2 | yes | `1. d4 Nf6 2. Bf4 g6 3. e3 Bg7 4. Nf3 d6` |
| 8 | 232 | 42 | 15 % | (unnamed) | no | 3 / 3 | yes | `1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. Nf3 d6` |
| 8 | 112 | 25 | 20 % | (unnamed) | no | 1 / 1 | yes | `1. d4 Nf6 2. Nf3 e6 3. e3 d5 4. Bd3 c5` |
| 8 | 104 | 38 | 13 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. e3 e6` |
| 8 | 85 | 28 | 22 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. e3 Bf5` |
| 8 | 59 | 29 | 19 % | Slav Defense: Quiet Variation, Pin Defense | no | 1 / 1 | no | `1. d4 d5 2. c4 c6 3. e3 Nf6 4. Nf3 Bg4` |
| 9 | 632 | 62 | 23 % | Italian Game: Giuoco Pianissimo, Italian Four Knights Variation | yes | 0 / 2 | yes | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. Nc3 Nf6 5. d3` |
| 9 | 323 | 40 | 19 % | (unnamed) | yes | 0 / 2 | yes | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Nc3 Bc5 5. O-O` |
| 9 | 210 | 65 | 11 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. Bf4 Nf6 3. e3 e6 4. Nf3 c5 5. c3` |
| 9 | 142 | 78 | 6 % | Semi-Slav Defense: Main Line | no | 2 / 2 | no | `1. d4 d5 2. c4 c6 3. Nc3 e6 4. Nf3 Nf6 5. e3` |
| 9 | 99 | 43 | 11 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. Nf3 Bf5 5. e3` |
| 9 | 88 | 26 | 16 % | London System, with Bd3 | no | 1 / 1 | no | `1. d4 Nf6 2. Bf4 g6 3. e3 Bg7 4. Nf3 d6 5. Bd3` |
| 9 | 86 | 36 | 15 % | King's Indian Defense: Smyslov Variation | no | 1 / 1 | no | `1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. Nf3 d6 5. Bg5` |
| 9 | 71 | 26 | 18 % | Queen's Pawn Game: Colle System, Traditional Colle | no | 1 / 1 | no | `1. d4 Nf6 2. Nf3 e6 3. e3 d5 4. Bd3 c5 5. c3` |
| 10 | 262 | 53 | 18 % | (unnamed) | yes | 0 / 1 | yes | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Nc3 Bc5 5. d3 d6` |
| 10 | 260 | 73 | 22 % | (unnamed) | yes | 1 / 2 | yes | `1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O` |
| 10 | 222 | 34 | 23 % | (unnamed) | yes | 2 / 3 | yes | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. d3 h6` |
| 10 | 177 | 36 | 18 % | Italian Game: Giuoco Pianissimo | no | 1 / 1 | yes | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. Nc3 O-O` |
| 10 | 166 | 16 | 22 % | Sicilian Defense: Classical Variation | no | 2 / 2 | no | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 Nc6` |
| 10 | 165 | 72 | 8 % | (unnamed) | no | 1 / 1 | yes | `1. d4 Nf6 2. Bf4 e6 3. e3 d5 4. Nf3 c5 5. c3 Nc6` |
| 10 | 125 | 24 | 18 % | Sicilian Defense: Taimanov Variation | no | 2 / 2 | no | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 a6 5. Nc3 Nc6` |
| 10 | 100 | 56 | 9 % | Slav Defense: Quiet Variation, Schallopp Defense | no | 1 / 1 | no | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. Nf3 Bf5 5. e3 e6` |
| 10 | 80 | 22 | 24 % | (unnamed) | no | 1 / 1 | yes | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. Nf3 O-O` |
| 10 | 72 | 13 | 22 % | (unnamed) | no | 1 / 1 | yes | `1. d4 Nf6 2. c4 c5 3. d5 e6 4. Nc3 exd5 5. cxd5 d6` |
| 11 | 153 | 52 | 14 % | Italian Game: Giuoco Pianissimo | no | 1 / 1 | no | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. Nc3 O-O 6. d3` |
| 11 | 130 | 26 | 18 % | Italian Game: Classical Variation, Giuoco Pianissimo | no | 2 / 2 | yes | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 h6 6. O-O` |
| 11 | 101 | 31 | 18 % | Queen's Gambit Declined: Modern Variation, Normal Line | no | 1 / 1 | no | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. Nf3 O-O 6. e3` |
| 11 | 86 | 32 | 14 % | Italian Game: Giuoco Pianissimo, Canal Variation | no | 1 / 1 | no | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Nc3 Bc5 5. d3 d6 6. Bg5` |
| 11 | 69 | 22 | 14 % | Benoni Defense: King's Pawn Line | no | 1 / 1 | no | `1. d4 Nf6 2. c4 c5 3. d5 e6 4. Nc3 exd5 5. cxd5 d6 6. e4` |
| 11 | 66 | 46 | 9 % | Queen's Pawn Game: London System | no | 1 / 1 | no | `1. d4 d5 2. Bf4 Nf6 3. e3 e6 4. Nf3 c5 5. c3 Nc6 6. Nbd2` |
| 12 | 79 | 32 | 14 % | Italian Game: Classical Variation, Giuoco Pianissimo, with h6 | no | 1 / 1 | no | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 h6 6. O-O d6` |

Kept edges main under no single move order (up to 60 of 162; `rank` = the move's rank among the parent's replies clearing the floor in that order):

| parent depth | move | games (pooled) | largest single order | share of parent | parent's orders | per-order rank | child's name | parent's canonical order |
|---|---|---|---|---|---|---|---|---|
| 4 | Nf3 | 62 | 31 | 16.6 % | 4 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. c4 d6` |
| 4 | e4 | 55 | 33 | 20.9 % | 4 | below the floor in every order | Caro-Kann Defense | `1. d4 d5 2. Nc3 c6` |
| 4 | Bf4 | 52 | 27 | 21.1 % | 4 | below the floor in every order | (unnamed) | `1. d4 d6 2. Nf3 Nf6` |
| 4 | e4 | 50 | 39 | 6.5 % | 2 | below the floor in every order | (unnamed) | `1. d4 g6 2. c4 Bg7` |
| 4 | Bg5 | 50 | 38 | 4.3 % | 4 | below the floor in every order | Indian Defense: Seirawan Attack | `1. d4 Nf6 2. c4 e6` |
| 4 | c4 | 48 | 17 | 19.5 % | 4 | below the floor in every order | (unnamed) | `1. d4 d6 2. Nf3 Nf6` |
| 4 | Nf3 | 48 | 29 | 13.2 % | 4 | below the floor in every order | Philidor Defense | `1. e4 e5 2. d4 d6` |
| 4 | e4 | 45 | 27 | 46.9 % | 4 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. Nc3 d6` |
| 5 | c5 | 108 | 36 | 12.8 % | 6 | below the floor in every order | (unnamed) | `1. d4 d5 2. Bf4 Nf6 3. Nf3` |
| 5 | dxe4 | 88 | 37 | 67.2 % | 6 | below the floor in every order | Blackmar-Diemer Gambit | `1. d4 Nf6 2. Nc3 d5 3. e4` |
| 5 | c6 | 87 | 38 | 13.6 % | 11 | below the floor in every order | (unnamed) | `1. d4 d5 2. c4 e6 3. Nf3` |
| 5 | g6 | 86 | 36 | 55.8 % | 6 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. Bf4 d6 3. Nf3` |
| 5 | Nc6 | 81 | 39 | 39.1 % | 5 | below the floor in every order | Nimzowitsch Defense: Kennedy Variation, de Smet Gambit | `1. e4 d6 2. d4 e5 3. dxe5` |
| 5 | e5 | 80 | 40 | 10.5 % | 6 | below the floor in every order | Sicilian Defense: Closed, Anti-Sveshnikov Variation | `1. e4 c5 2. Nf3 Nc6 3. Nc3` |
| 5 | e6 | 77 | 34 | 27.5 % | 12 | below the floor in every order | (unnamed) | `1. d4 d5 2. Nf3 Nf6 3. Nc3` |
| 5 | c5 | 72 | 22 | 11.2 % | 11 | below the floor in every order | Queen's Gambit Declined: Tarrasch Defense, Pseudo-Tarrasch | `1. d4 d5 2. c4 e6 3. Nf3` |
| 5 | Nf6 | 72 | 25 | 37.5 % | 11 | below the floor in every order | (unnamed) | `1. d4 d5 2. Nc3 e6 3. Nf3` |
| 5 | dxc4 | 67 | 21 | 10.4 % | 11 | below the floor in every order | Queen's Gambit Accepted: Rosenthal Variation | `1. d4 d5 2. c4 e6 3. Nf3` |
| 5 | Bb4 | 67 | 41 | 12.7 % | 5 | below the floor in every order | Vienna Game: Stanley Variation, Reversed Spanish | `1. e4 e5 2. Bc4 Nf6 3. Nc3` |
| 5 | g6 | 66 | 20 | 58.4 % | 10 | below the floor in every order | (unnamed) | `1. d4 d6 2. c4 Nf6 3. Nf3` |
| 5 | Nf6 | 63 | 39 | 30.3 % | 3 | below the floor in every order | (unnamed) | `1. e4 e5 2. Nc3 Bc5 3. Bc4` |
| 5 | Nf6 | 61 | 32 | 23.7 % | 6 | below the floor in every order | Queen's Pawn Game: Colle System, Anti-Colle | `1. d4 d5 2. Nf3 Bf5 3. e3` |
| 5 | c6 | 58 | 19 | 15.8 % | 9 | below the floor in every order | (unnamed) | `1. d4 d5 2. c4 Nf6 3. Nf3` |
| 5 | d5 | 58 | 40 | 37.9 % | 8 | below the floor in every order | French Defense: Classical Variation | `1. d4 Nf6 2. Nc3 e6 3. e4` |
| 5 | Nc6 | 53 | 21 | 4.3 % | 11 | below the floor in every order | Sicilian Defense: Franco-Sicilian Variation | `1. e4 c5 2. Nf3 e6 3. d4` |
| 5 | e6 | 51 | 35 | 25.0 % | 5 | below the floor in every order | Benoni Defense: Modern Variation | `1. d4 Nf6 2. c4 c5 3. d5` |
| 5 | dxc4 | 48 | 18 | 13.1 % | 9 | below the floor in every order | Queen's Gambit Accepted | `1. d4 d5 2. c4 Nf6 3. Nf3` |
| 5 | d5 | 47 | 35 | 38.2 % | 4 | below the floor in every order | Rapport-Jobava System | `1. d4 Nf6 2. Nc3 e6 3. Bf4` |
| 5 | c6 | 46 | 23 | 13.7 % | 8 | below the floor in every order | (unnamed) | `1. d4 d5 2. e3 Nf6 3. c4` |
| 5 | b6 | 43 | 33 | 16.9 % | 10 | below the floor in every order | Queen's Indian Defense | `1. d4 Nf6 2. c4 e6 3. Nf3` |
| 6 | Nc3 | 116 | 40 | 55.2 % | 14 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. c4 g6 3. Nf3 Bg7` |
| 6 | d3 | 104 | 39 | 44.1 % | 7 | below the floor in every order | Bishop's Opening: Vienna Hybrid, Spielmann Attack | `1. e4 e5 2. Bc4 Nf6 3. Nc3 Bc5` |
| 6 | e4 | 93 | 38 | 44.1 % | 11 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. c4 d6 3. Nc3 g6` |
| 6 | d4 | 92 | 41 | 55.1 % | 9 | below the floor in every order | (unnamed) | `1. e4 c5 2. Nf3 e6 3. Nc3 a6` |
| 6 | d4 | 88 | 27 | 34.5 % | 4 | below the floor in every order | (unnamed) | `1. e4 c5 2. Nf3 Nc6 3. Nc3 d6` |
| 6 | Nf3 | 84 | 27 | 17.7 % | 14 | below the floor in every order | Four Knights Game: Italian Variation | `1. e4 e5 2. Nc3 Nc6 3. Bc4 Nf6` |
| 6 | e3 | 83 | 39 | 10.1 % | 12 | below the floor in every order | (unnamed) | `1. d4 d5 2. c4 c6 3. Nc3 Nf6` |
| 6 | Bg5 | 78 | 17 | 43.6 % | 23 | below the floor in every order | Queen's Pawn Game: Veresov Attack, Classical Defense | `1. d4 d5 2. Nf3 Nf6 3. Nc3 e6` |
| 6 | Nc3 | 72 | 20 | 44.4 % | 19 | below the floor in every order | (unnamed) | `1. d4 d5 2. c4 c6 3. Nf3 e6` |
| 6 | Bg5 | 70 | 42 | 22.2 % | 16 | below the floor in every order | French Defense: Classical Variation | `1. e4 e6 2. d4 d5 3. Nc3 Nf6` |
| 6 | e3 | 70 | 26 | 63.6 % | 8 | below the floor in every order | Queen's Pawn Game: London System | `1. d4 d5 2. Nf3 Nf6 3. Bf4 c5` |
| 6 | Nf3 | 68 | 36 | 38.2 % | 16 | below the floor in every order | Slav Defense: Quiet Variation | `1. d4 d5 2. c4 c6 3. e3 Nf6` |
| 6 | Nc3 | 68 | 33 | 38.2 % | 16 | below the floor in every order | (unnamed) | `1. d4 d5 2. c4 c6 3. e3 Nf6` |
| 6 | d4 | 67 | 35 | 38.1 % | 7 | below the floor in every order | (unnamed) | `1. e4 c5 2. Nf3 Nc6 3. Nc3 g6` |
| 6 | f3 | 65 | 33 | 7.9 % | 10 | below the floor in every order | Caro-Kann Defense: Rasa-Studier Gambit | `1. e4 c6 2. d4 d5 3. Nc3 dxe4` |
| 6 | e4 | 64 | 35 | 38.1 % | 5 | below the floor in every order | Slav Defense: Slav Gambit, Alekhine Attack | `1. d4 d5 2. c4 dxc4 3. Nc3 c6` |
| 6 | Bg5 | 63 | 35 | 14.4 % | 6 | below the floor in every order | Blackmar-Diemer Gambit: von Popiel Gambit | `1. d4 d5 2. e4 dxe4 3. Nc3 Nf6` |
| 6 | Nf3 | 60 | 40 | 16.0 % | 6 | below the floor in every order | Queen's Gambit Accepted: Showalter Variation | `1. d4 d5 2. c4 dxc4 3. Nc3 Nf6` |
| 6 | Nf3 | 60 | 32 | 47.6 % | 5 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. Bf4 d6 3. e3 g6` |
| 6 | Nc3 | 59 | 29 | 44.0 % | 13 | below the floor in every order | Modern Defense: Averbakh System | `1. e4 g6 2. d4 Bg7 3. c4 d6` |
| 6 | Nc3 | 59 | 23 | 71.1 % | 7 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. c4 c5 3. d5 e6` |
| 6 | e3 | 59 | 22 | 59.6 % | 8 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. Bf4 d6 3. Nf3 g6` |
| 6 | d4 | 58 | 32 | 38.7 % | 7 | below the floor in every order | (unnamed) | `1. e4 c5 2. Nf3 d6 3. Nc3 Nf6` |
| 6 | Nf3 | 54 | 24 | 20.5 % | 6 | below the floor in every order | (unnamed) | `1. e4 e5 2. Nc3 Nc6 3. Bc4 Bc5` |
| 6 | Nc3 | 52 | 11 | 63.4 % | 13 | below the floor in every order | (unnamed) | `1. d4 d6 2. c4 Nf6 3. Nf3 g6` |
| 6 | Nf3 | 51 | 31 | 24.3 % | 7 | below the floor in every order | (unnamed) | `1. d4 g6 2. c4 Bg7 3. Nc3 d6` |
| 6 | a3 | 49 | 38 | 13.4 % | 7 | below the floor in every order | Nimzo-Indian Defense: Sämisch Variation | `1. d4 Nf6 2. c4 e6 3. Nc3 Bb4` |
| 6 | Nf3 | 49 | 21 | 23.2 % | 11 | below the floor in every order | (unnamed) | `1. d4 Nf6 2. c4 d6 3. Nc3 g6` |
| 6 | Bc4 | 47 | 37 | 6.9 % | 13 | below the floor in every order | Pirc Defense: Kholmov System | `1. e4 d6 2. d4 Nf6 3. Nc3 g6` |
| 6 | c3 | 46 | 33 | 4.9 % | 11 | below the floor in every order | Sicilian Defense: Smith-Morra Gambit Deferred | `1. e4 c5 2. Nf3 e6 3. d4 cxd4` |

### Names

- Exactly named kept positions: **505 of 780** (64.7 %); 275 unnamed (the start position included).
- Unnamed kept positions whose inherited names (over every kept path into them) are more than one book name: **102**; the widest carries 6 names.
- Named kept positions whose canonical (most popular) order differs from the book's own line: **78 of 505**; the book's own order has no game at all in this band for 3 of the named kept positions and fewer than the floor for another 84.

Unnamed positions with more than one inherited name (up to 40, by depth then games):

| depth | games (pooled) | names | inherited names | canonical order |
|---|---|---|---|---|
| 3 | 1748 | 2 | English Opening: Agincourt Defense; Horwitz Defense | `1. d4 e6 2. c4` |
| 4 | 1788 | 2 | Indian Defense: Accelerated London System; Queen's Pawn Game: Accelerated London System | `1. d4 d5 2. Bf4 Nf6` |
| 4 | 1521 | 2 | Horwitz Defense; Queen's Pawn Game: Accelerated London System | `1. d4 d5 2. Bf4 e6` |
| 4 | 1264 | 2 | Horwitz Defense; Queen's Pawn Game: Zukertort Variation | `1. d4 d5 2. Nf3 e6` |
| 4 | 1161 | 3 | English Opening: Agincourt Defense; Horwitz Defense; Indian Defense: Normal Variation | `1. d4 Nf6 2. c4 e6` |
| 4 | 836 | 2 | Horwitz Defense; Queen's Pawn Game | `1. d4 d5 2. e3 e6` |
| 4 | 463 | 2 | Horwitz Defense; Indian Defense: Knights Variation | `1. d4 Nf6 2. Nf3 e6` |
| 4 | 452 | 2 | Horwitz Defense; Indian Defense: Accelerated London System | `1. d4 Nf6 2. Bf4 e6` |
| 4 | 147 | 2 | English Opening: Agincourt Defense; Horwitz Defense | `1. d4 e6 2. c4 c6` |
| 5 | 1234 | 2 | French Defense: Franco-Sicilian Defense; Sicilian Defense: French Variation | `1. e4 c5 2. Nf3 e6 3. d4` |
| 5 | 1121 | 2 | Indian Defense: Accelerated London System; Queen's Pawn Game: Accelerated London System | `1. d4 d5 2. Bf4 Nf6 3. e3` |
| 5 | 916 | 2 | Horwitz Defense; Queen's Pawn Game: Accelerated London System | `1. d4 d5 2. Bf4 e6 3. e3` |
| 5 | 812 | 3 | English Opening: Agincourt Defense; Horwitz Defense; Indian Defense: Normal Variation | `1. d4 Nf6 2. c4 e6 3. Nc3` |
| 5 | 807 | 2 | Bishop's Opening; Vienna Game: Max Lange Defense | `1. e4 e5 2. Nc3 Nc6 3. Bc4` |
| 5 | 763 | 2 | Sicilian Defense: Closed, Traditional; Sicilian Defense: Old Sicilian | `1. e4 c5 2. Nf3 Nc6 3. Nc3` |
| 5 | 642 | 3 | Horwitz Defense; Queen's Gambit Declined; Queen's Pawn Game: Zukertort Variation | `1. d4 d5 2. c4 e6 3. Nf3` |
| 5 | 639 | 3 | Horwitz Defense; Queen's Pawn Game; Queen's Pawn Game: Zukertort Variation | `1. d4 d5 2. Nf3 e6 3. e3` |
| 5 | 586 | 2 | French Defense: Knight Variation; Scandinavian Defense | `1. e4 e6 2. Nf3 d5 3. e5` |
| 5 | 435 | 2 | Sicilian Defense: Closed; Sicilian Defense: French Variation | `1. e4 c5 2. Nf3 e6 3. Nc3` |
| 5 | 370 | 2 | Sicilian Defense: Closed; Sicilian Defense: Modern Variations | `1. e4 c5 2. Nf3 d6 3. Nc3` |
| 5 | 367 | 2 | Queen's Gambit Declined: Marshall Defense; Queen's Pawn Game: Symmetrical Variation | `1. d4 d5 2. c4 Nf6 3. Nf3` |
| 5 | 335 | 2 | Queen's Gambit Declined: Marshall Defense; Queen's Pawn Game | `1. d4 d5 2. e3 Nf6 3. c4` |
| 5 | 288 | 2 | Horwitz Defense; Indian Defense: Accelerated London System | `1. d4 Nf6 2. Bf4 e6 3. e3` |
| 5 | 280 | 2 | Queen's Pawn Game: Chigorin Variation; Queen's Pawn Game: Symmetrical Variation | `1. d4 d5 2. Nf3 Nf6 3. Nc3` |
| 5 | 257 | 2 | Queen's Pawn Game; Queen's Pawn Game: Zukertort Variation | `1. d4 d5 2. Nf3 Bf5 3. e3` |
| 5 | 208 | 2 | Bishop's Opening: Boi Variation; Vienna Game: Anderssen Defense | `1. e4 e5 2. Nc3 Bc5 3. Bc4` |
| 5 | 192 | 3 | Horwitz Defense; Queen's Pawn Game: Chigorin Variation; Queen's Pawn Game: Zukertort Variation | `1. d4 d5 2. Nc3 e6 3. Nf3` |
| 5 | 154 | 2 | Indian Defense: Accelerated London System; Indian Defense: Wade-Tartakower Defense | `1. d4 Nf6 2. Bf4 d6 3. Nf3` |
| 5 | 113 | 2 | Indian Defense: Wade-Tartakower Defense; Old Indian Defense | `1. d4 d6 2. c4 Nf6 3. Nf3` |
| 5 | 106 | 2 | English Opening: Agincourt Defense; Horwitz Defense | `1. d4 e6 2. c4 c6 3. Nc3` |
| 6 | 1467 | 2 | Englund Gambit Declined: Reversed French; French Defense: Exchange Variation | `1. e4 e6 2. d4 d5 3. exd5 exd5` |
| 6 | 818 | 2 | Queen's Gambit Declined: Marshall Defense; Slav Defense | `1. d4 d5 2. c4 c6 3. Nc3 Nf6` |
| 6 | 712 | 2 | English Opening: Great Snake Variation; King's Indian Defense | `1. d4 Nf6 2. c4 g6 3. Nc3 Bg7` |
| 6 | 658 | 3 | Horwitz Defense; Indian Defense: Accelerated London System; Queen's Pawn Game: Accelerated London System | `1. d4 d5 2. Bf4 Nf6 3. e3 e6` |
| 6 | 564 | 6 | Horwitz Defense; Indian Defense: Anti-Nimzo-Indian; Queen's Gambit Declined; Queen's Gambit Declined: Marshall Defense; Queen's Pawn Game: Symmetrical Variation; Queen's Pawn Game: Zukertort Variation | `1. d4 d5 2. c4 e6 3. Nf3 Nf6` |
| 6 | 475 | 2 | French Defense: Knight Variation; Scandinavian Defense | `1. e4 e6 2. Nf3 d5 3. e5 c5` |
| 6 | 407 | 4 | Sicilian Defense: Closed; Sicilian Defense: Closed, Traditional; Sicilian Defense: French Variation; Sicilian Defense: Old Sicilian | `1. e4 c5 2. Nf3 Nc6 3. Nc3 e6` |
| 6 | 374 | 2 | Queen's Gambit Accepted; Queen's Gambit Declined: Marshall Defense | `1. d4 d5 2. c4 dxc4 3. Nc3 Nf6` |
| 6 | 361 | 2 | Bishop's Opening; Bishop's Opening: Berlin Defense | `1. e4 e5 2. Bc4 Nc6 3. d3 Nf6` |
| 6 | 264 | 2 | Bishop's Opening; Vienna Game: Max Lange Defense | `1. e4 e5 2. Nc3 Nc6 3. Bc4 Bc5` |

Named positions whose canonical order is not the book's line (up to 40, by pooled games; games in the canonical order / in the book's order):

| pooled | canonical order games | book order games | name | ECO | canonical order | book's line |
|---|---|---|---|---|---|---|
| 1812 | 1181 | 539 | French Defense: Exchange Variation | C01 | `1. e4 e6 2. Nf3 d5 3. exd5 exd5 4. d4` | `1. e4 e6 2. d4 d5 3. exd5 exd5 4. Nf3` |
| 1122 | 996 | 70 | Scotch Game: Lolli Variation | C44 | `1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4` | `1. e4 e5 2. Nf3 Nc6 3. d4 Nxd4 4. Nxd4 exd4 5. Qxd4` |
| 1104 | 817 | 256 | Queen's Pawn Game: Chigorin Variation | A45 | `1. d4 d5 2. Nc3 Nf6` | `1. d4 Nf6 2. Nc3 d5` |
| 843 | 330 | 315 | Queen's Pawn Game: London System | D02 | `1. d4 d5 2. Bf4 Nf6 3. Nf3` | `1. d4 d5 2. Nf3 Nf6 3. Bf4` |
| 811 | 638 | 92 | Caro-Kann Defense: Main Line | B15 | `1. e4 c6 2. d4 d5 3. Nc3 dxe4 4. Nxe4` | `1. e4 c6 2. d4 d5 3. Nd2 dxe4 4. Nxe4` |
| 765 | 560 | 165 | Caro-Kann Defense: Exchange Variation | B13 | `1. e4 c6 2. Nf3 d5 3. exd5 cxd5 4. d4 Nc6` | `1. e4 c6 2. d4 d5 3. exd5 cxd5 4. Nf3 Nc6` |
| 756 | 303 | 193 | Queen's Pawn Game: London System, with e6 | D02 | `1. d4 d5 2. Bf4 e6 3. Nf3` | `1. d4 d5 2. Nf3 e6 3. Bf4` |
| 668 | 224 | 25 | Queen's Gambit Declined: Three Knights Variation | D37 | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Nf3` | `1. d4 Nf6 2. c4 e6 3. Nf3 d5 4. Nc3` |
| 632 | 146 | 34 | Italian Game: Giuoco Pianissimo, Italian Four Knights Variation | C50 | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. Nc3 Nf6 5. d3` | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. d3 Nf6 5. Nc3` |
| 606 | 304 | 67 | Rat Defense: Small Center Defense | C00 | `1. e4 e6 2. d4 d6` | `1. d4 e6 2. e4 d6` |
| 593 | 423 | 165 | Nimzowitsch Defense: Kennedy Variation | B00 | `1. e4 e5 2. d4 Nc6` | `1. e4 Nc6 2. d4 e5` |
| 526 | 335 | 161 | Vienna Game: Stanley Variation | C26 | `1. e4 e5 2. Bc4 Nf6 3. Nc3` | `1. e4 e5 2. Nc3 Nf6 3. Bc4` |
| 511 | 97 | 55 | Queen's Pawn Game: London System, with e6 | D02 | `1. d4 d5 2. Bf4 Nf6 3. Nf3 e6` | `1. d4 d5 2. Nf3 e6 3. Bf4 Nf6` |
| 447 | 200 | 128 | Semi-Slav Defense: Accelerated Move Order | D31 | `1. d4 d5 2. c4 c6 3. Nc3 e6` | `1. d4 d5 2. c4 e6 3. Nc3 c6` |
| 443 | 190 | 152 | Scotch Game: Scotch Gambit, Dubois Réti Defense | C44 | `1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Bc4 Nf6` | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d4 exd4` |
| 441 | 221 | 55 | Slav Defense: Three Knights Variation | D15 | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. Nf3` | `1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3` |
| 403 | 255 | 141 | Caro-Kann Defense: Two Knights Attack | B10 | `1. e4 c6 2. Nf3 d5 3. Nc3` | `1. e4 c6 2. Nc3 d5 3. Nf3` |
| 382 | 237 | 136 | Nimzowitsch Defense: Kennedy Variation, Linksspringer Variation | B00 | `1. e4 e5 2. d4 Nc6 3. d5` | `1. e4 Nc6 2. d4 e5 3. d5` |
| 365 | 280 | 46 | Caro-Kann Defense: Classical Variation | B18 | `1. e4 c6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 Bf5` | `1. e4 c6 2. d4 d5 3. Nd2 dxe4 4. Nxe4 Bf5` |
| 364 | 175 | 161 | King's Pawn Game: Maróczy Defense | B07 | `1. e4 e5 2. d4 d6` | `1. e4 d6 2. d4 e5` |
| 344 | 275 | 69 | Queen's Pawn Game: Anti-Torre | D02 | `1. d4 d5 2. Nf3 Bg4` | `1. Nf3 d5 2. d4 Bg4` |
| 340 | 147 | 16 | Bishop's Opening: Vienna Hybrid | C24 | `1. e4 e5 2. Nc3 Nc6 3. Bc4 Nf6 4. d3` | `1. e4 e5 2. Bc4 Nf6 3. d3 Nc6 4. Nc3` |
| 283 | 46 | 15 | Semi-Slav Defense | D43 | `1. d4 d5 2. c4 c6 3. Nc3 e6 4. Nf3 Nf6` | `1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. Nc3 e6` |
| 249 | 127 | 111 | Nimzowitsch Defense: Scandinavian Variation, Advance Variation | B00 | `1. e4 d5 2. e5 Nc6 3. d4` | `1. e4 Nc6 2. d4 d5 3. e5` |
| 249 | 53 | 10 | Queen's Gambit Declined: Ragozin Defense | D38 | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Nf3 Bb4` | `1. d4 Nf6 2. c4 e6 3. Nf3 d5 4. Nc3 Bb4` |
| 249 | 30 | 22 | London System | A48 | `1. d4 Nf6 2. Bf4 g6 3. e3 Bg7 4. Nf3 d6` | `1. d4 Nf6 2. Nf3 g6 3. Bf4 Bg7 4. e3 d6` |
| 246 | 105 | 96 | Indian Defense: Wade-Tartakower Defense | A46 | `1. d4 d6 2. Nf3 Nf6` | `1. d4 Nf6 2. Nf3 d6` |
| 228 | 86 | 45 | London System | A48 | `1. d4 Nf6 2. Bf4 g6 3. e3 Bg7 4. Nf3` | `1. d4 Nf6 2. Nf3 g6 3. Bf4 Bg7 4. e3` |
| 225 | 159 | 54 | Nimzowitsch Defense: Scandinavian Variation, Exchange Variation | B00 | `1. e4 d5 2. exd5 Qxd5 3. d4 Nc6` | `1. e4 Nc6 2. d4 d5 3. exd5 Qxd5` |
| 223 | 97 | 60 | Queen's Gambit Declined: Exchange Variation | D35 | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. cxd5` | `1. d4 Nf6 2. c4 e6 3. Nc3 d5 4. cxd5` |
| 205 | 117 | 54 | King's Indian Defense: Normal Variation, King's Knight Variation | E60 | `1. d4 Nf6 2. c4 g6 3. Nf3` | `1. d4 Nf6 2. Nf3 g6 3. c4` |
| 196 | 56 | 55 | Italian Game: Classical Variation, Albin Gambit | C50 | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. O-O Bc5 5. c3` | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. c3` |
| 177 | 32 | 16 | Italian Game: Giuoco Pianissimo | C50 | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. Nc3 O-O` | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. Nc3 Nf6 5. O-O O-O` |
| 172 | 115 | 38 | Richter-Veresov Attack | D01 | `1. d4 d5 2. Nc3 Nf6 3. Bg5` | `1. d4 Nf6 2. Nc3 d5 3. Bg5` |
| 170 | 49 | 19 | Sicilian Defense: Four Knights Variation | B45 | `1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e6` | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nc3 Nf6` |
| 168 | 83 | 39 | Slav Defense | D10 | `1. d4 d5 2. c4 dxc4 3. Nc3 c6` | `1. d4 d5 2. c4 c6 3. Nc3 dxc4` |
| 166 | 47 | 29 | Four Knights Game: Spanish Variation, Classical Variation | C48 | `1. e4 e5 2. Nf3 Nc6 3. Bb5 Nf6 4. Nc3 Bc5` | `1. e4 e5 2. Nf3 Nc6 3. Nc3 Nf6 4. Bb5 Bc5` |
| 153 | 21 | 8 | Italian Game: Giuoco Pianissimo | C50 | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. Nc3 O-O 6. d3` | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. Nc3 Nf6 5. O-O O-O 6. d3` |
| 142 | 8 | 7 | Semi-Slav Defense: Main Line | D45 | `1. d4 d5 2. c4 c6 3. Nc3 e6 4. Nf3 Nf6 5. e3` | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. e3 e6 5. Nf3` |
| 139 | 78 | 53 | Queen's Gambit Declined: Chigorin Defense | D07 | `1. d4 d5 2. c4 dxc4 3. Nc3 Nc6` | `1. d4 d5 2. c4 Nc6 3. Nc3 dxc4` |

### Per-colour split

Side to move is part of the EPD; a learner position is one where the learner is to move, so the record key's colour is the side to move.

| kept positions | White to move | Black to move |
|---|---|---|
| kept positions | 389 | 391 |
| internal (with a kept move) | 264 | 275 |
| leaves | 125 | 116 |
| exactly named | 259 | 246 |
| recovered (not in the sequence tree) | 106 | 117 |

## Reproduction

Nothing is stored: the dump is streamed and the prefix read is whatever the stop rule allows, so a rerun on the same URL reads the same prefix and gives the same numbers.

```sh
cd /home/anthony/pproj/chessop
S=/tmp/chessop-scratch && mkdir -p $S

# 1. dependencies (python-chess 1.11.2, zstandard 0.25.0)
uv venv $S/venv
uv pip install --python $S/venv/bin/python chess==1.11.2 zstandard==0.25.0

# 2. the chess-openings dist columns (uci, epd): 3811 lines, exit 0
$S/venv/bin/python refs/lichess/chess-openings-bin-gen.py \
    refs/lichess/chess-openings-a.tsv refs/lichess/chess-openings-b.tsv \
    refs/lichess/chess-openings-c.tsv refs/lichess/chess-openings-d.tsv \
    refs/lichess/chess-openings-e.tsv > $S/chess-openings-dist.tsv

# 3. the measurement, streaming the dump (no download); regenerates this file
$S/venv/bin/python refs/lichess/pooled-repertoire-analysis.py \
    https://database.lichess.org/standard/lichess_db_standard_rated_2026-08.pgn.zst \
    $S/chess-openings-dist.tsv docs/research/pooled-repertoire.md \
    --target-games 150000 --max-bytes 4294967296
```

## Sources

- Lichess open database, standard rated games 2026-08, CC0: <https://database.lichess.org/standard/lichess_db_standard_rated_2026-08.pgn.zst> (streamed, not stored; the prefix read is stated under Method); licence page saved as `refs/lichess/database-lichess-org.html`.
- `lichess-org/chess-openings` (CC0): `refs/lichess/chess-openings-{a..e}.tsv`, `refs/lichess/chess-openings-README.md`, `refs/lichess/chess-openings-bin-gen.py` (the upstream generator deriving `uci` and `epd`; `Board.epd()` per row).
- python-chess 1.11.2: `chess.Board.epd()` (placement, side to move, castling, en passant only when a capture is legal; no move counters) and `push_san`, used for every key; zstandard 0.25.0 for the streaming decompressor.
- The rule: [`docs/adr/0005-repertoire-rule.md`](../adr/0005-repertoire-rule.md); the graph: [`docs/adr/0006-position-graph.md`](../adr/0006-position-graph.md).
- The sample, the sequence tree and the transposition-only misses: [`repertoire-rule-candidates-recent.md`](repertoire-rule-candidates-recent.md) and `refs/lichess/repertoire-rule-analysis-recent.py`; the merged-DAG and cycle-check method: [`transpositions.md`](transpositions.md) and `refs/lichess/transposition-analysis.py`.

