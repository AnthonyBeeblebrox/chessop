# Repertoire size under candidate rules, on a recent month (2026-08)

Ticket: [`.scratch/chessop/issues/13-repertoire-named-variations.md`](../../.scratch/chessop/issues/13-repertoire-named-variations.md). Rerun of [`repertoire-rule-candidates.md`](repertoire-rule-candidates.md) (2013-01, 5,017 games at 1800+) on `lichess_db_standard_rated_2026-08.pgn.zst`, with ADR 0003's bands and filters.
Script: [`refs/lichess/repertoire-rule-analysis-recent.py`](../../refs/lichess/repertoire-rule-analysis-recent.py) (imports the 2013 script's trie, rules and book code and the shared tokenizer). Generated; every number below is one run of it. No recommendation is made here.

## Method and sample

- **Source**: `lichess_db_standard_rated_2026-08.pgn.zst` (30,145,862,359 bytes, CC0), streamed over HTTP through a zstandard streaming decompressor and parsed as it arrived; nothing was written to disk. The dump is ordered by game time, so a prefix is a sample of the **start of the month**, not of the whole month (here: a single day, see the date range below). Reading stopped when band 1800-2100 had 150,000 games after filters or after 4,294,967,296 compressed bytes, whichever came first: **stopped because band 1800-2100 reached 150000 games**, after **482,224,925 compressed bytes** (1.60 % of the file) and **1,474,213 games seen**.
- **Date range of the games seen** (`UTCDate UTCTime`): 2026.08.01 00:00:00 to 2026.08.01 13:15:03. Per band kept: below 1200 2026.08.01 00:00:00 to 2026.08.01 13:15:03; 1200-1500 2026.08.01 00:00:00 to 2026.08.01 13:15:03; 1500-1800 2026.08.01 00:00:01 to 2026.08.01 13:15:03; 1800-2100 2026.08.01 00:00:00 to 2026.08.01 13:15:03; 2100 and above 2026.08.01 00:00:01 to 2026.08.01 13:15:02.
- **Filters** (ADR 0003): both `WhiteElo` and `BlackElo` present and numeric; no `WhiteTitle`/`BlackTitle` of `BOT`; `Event` speed not Bullet or UltraBullet (Blitz, Rapid, Classical and Correspondence pooled; an Event without a speed word falls back to the prototype's base + 40 x increment < 180 s rule); both players inside the same 300-wide band, lower bound inclusive. Games dropped: bullet / ultrabullet 637,928, players in different bands 128,270, BOT title 6,683.
- **Games kept per band** (all five bands counted; tries built for two): below 1200 **129,724**, 1200-1500 **162,765**, 1500-1800 **214,825**, 1800-2100 **150,000**, 2100 and above **44,018**.
- **Speeds of the games in the two trie bands**: 1800-2100: Blitz 118,516, Classical 1,017, Correspondence 233, Rapid 30,234; 1500-1800: Blitz 154,450, Classical 2,612, Correspondence 289, Rapid 57,474.
- **Trie**: one move-sequence trie per band (transpositions not merged), mainline SAN from the shared tokenizer of `tree-width-analysis.py` (annotations stripped), built to **ply 36** (the deepest book line) with no thinning: every node was kept and keyed by python-chess `Board.epd()`. band 1800-2100: 4,001,817 nodes; band 1500-1800: 5,682,125 nodes. Games dropped under SAN tokens python-chess rejects: 1800-2100 0, 1500-1800 0. Peak resident memory of the whole run 4.8 GB; parse 53 s, keying and measuring 201 s.
- **Node count**, **pooled count**, **named**, **top-3** (count desc, then SAN desc ties), **nodes** (root included), **lines** (= leaf paths), **Sicilian subtree** (sequence subtree under `1.e4 c5`; 401 book rows start `e2e4 c7c5`, 391 of them named `Sicilian Defense…`): as in the 2013 document.
- **Floors** are a share of the band's kept games; the threshold is unrounded (count >= f x N), and the table gives the resulting integer game count. **Every rule tree is capped at ply 36** (a node at ply 36 keeps no reply); `hits ply cap` flags a tree with a node there.
- **Rule A**: the old rule, count >= 0.2 %, top-3. **Rule C**: top-3 tree at the floor, then every node with no exactly-named position at or below it (by EPD) pruned; the uncapped row keeps every reply clearing the floor before pruning. **Rule D**: the book's 3810 rows against the band's traffic, by the row's own move order (sequence count) and pooled over every move order into the position (EPD).

## Band 1800-2100: 150,000 games

First moves: e4 86,436, d4 41,547, c4 6,091, Nf3 5,499, f4 2,259, b3 1,670.

### Summary

| rule | cell | floor (games) | nodes (root incl.) | lines (leaf paths) | max ply | largest kept-reply count | book lines covered (of 3810) | Sicilian nodes | Sicilian lines | Sicilian max ply | Sicilian book lines covered (of 401 / 391) | hits ply cap 36 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | old rule: count >= 0.2 %, top-3 | >= 300 | 173 | 69 | 10 | 3 | 117 | 37 | 14 | 10 | 26 / 26 | no |
| C | f = 0.2 %, top-3, book-pruned | >= 300 | 137 | 52 | 10 | 3 | 117 | 31 | 11 | 10 | 26 / 26 | no |
| C | f = 0.1 %, top-3, book-pruned | >= 150 | 212 | 83 | 11 | 3 | 173 | 43 | 15 | 10 | 36 / 36 | no |
| C | f = 0.04 %, top-3, book-pruned | >= 60 | 369 | 148 | 13 | 3 | 260 | 65 | 28 | 13 | 53 / 53 | no |
| C | f = 0.02 %, top-3, book-pruned | >= 30 | 592 | 213 | 17 | 3 | 342 | 112 | 40 | 17 | 70 / 70 | no |
| C | f = 0.01 %, top-3, book-pruned | >= 15 | 884 | 295 | 22 | 3 | 426 | 174 | 56 | 17 | 83 / 83 | no |
| C | f = 0.02 %, UNCAPPED, book-pruned | >= 30 | 1491 | 650 | 17 | 18 | 801 | 190 | 71 | 17 | 109 / 108 | no |

Rule C, size before the book-pruning step (top-3 or uncapped tree at the floor, ply cap 36):

| cell | nodes before pruning | lines before pruning | max ply before | Sicilian nodes before | Sicilian lines before |
|---|---|---|---|---|---|
| f = 0.2 %, top-3, book-pruned | 173 | 69 | 10 | 37 | 14 |
| f = 0.1 %, top-3, book-pruned | 292 | 120 | 13 | 61 | 23 |
| f = 0.04 %, top-3, book-pruned | 673 | 284 | 14 | 142 | 65 |
| f = 0.02 %, top-3, book-pruned | 1225 | 473 | 19 | 283 | 104 |
| f = 0.01 %, top-3, book-pruned | 2230 | 813 | 22 | 497 | 178 |
| f = 0.02 %, UNCAPPED, book-pruned | 3988 | 1760 | 19 | 606 | 253 |

### Per-rule detail

- **A, old rule: count >= 0.2 %, top-3 (>= 300 games)**: 173 nodes / 69 lines / max ply 10 (largest kept-reply count 3); book lines covered 117 of 3810; nodes by ply 1: 3, 2: 9, 3: 21, 4: 40, 5: 37, 6: 23, 7: 19, 8: 14, 9: 4, 10: 2. Sicilian: 37 nodes / 14 lines / max ply 10, 26 of the 401 `1.e4 c5` book lines (26 of the 391 `Sicilian Defense` ones) covered.
- **C, f = 0.2 %, top-3, book-pruned (>= 300 games)**: 137 nodes / 52 lines / max ply 10 (largest kept-reply count 3); book lines covered 117 of 3810; nodes by ply 1: 3, 2: 9, 3: 18, 4: 26, 5: 29, 6: 22, 7: 15, 8: 11, 9: 2, 10: 1. Sicilian: 31 nodes / 11 lines / max ply 10, 26 of the 401 `1.e4 c5` book lines (26 of the 391 `Sicilian Defense` ones) covered.
- **C, f = 0.1 %, top-3, book-pruned (>= 150 games)**: 212 nodes / 83 lines / max ply 11 (largest kept-reply count 3); book lines covered 173 of 3810; nodes by ply 1: 3, 2: 9, 3: 18, 4: 36, 5: 44, 6: 36, 7: 28, 8: 21, 9: 10, 10: 5, 11: 1. Sicilian: 43 nodes / 15 lines / max ply 10, 36 of the 401 `1.e4 c5` book lines (36 of the 391 `Sicilian Defense` ones) covered.
- **C, f = 0.04 %, top-3, book-pruned (>= 60 games)**: 369 nodes / 148 lines / max ply 13 (largest kept-reply count 3); book lines covered 260 of 3810; nodes by ply 1: 3, 2: 9, 3: 21, 4: 45, 5: 71, 6: 63, 7: 57, 8: 37, 9: 29, 10: 17, 11: 10, 12: 4, 13: 2. Sicilian: 65 nodes / 28 lines / max ply 13, 53 of the 401 `1.e4 c5` book lines (53 of the 391 `Sicilian Defense` ones) covered.
- **C, f = 0.02 %, top-3, book-pruned (>= 30 games)**: 592 nodes / 213 lines / max ply 17 (largest kept-reply count 3); book lines covered 342 of 3810; nodes by ply 1: 3, 2: 9, 3: 23, 4: 53, 5: 93, 6: 94, 7: 96, 8: 68, 9: 56, 10: 38, 11: 23, 12: 14, 13: 10, 14: 5, 15: 3, 16: 2, 17: 1. Sicilian: 112 nodes / 40 lines / max ply 17, 70 of the 401 `1.e4 c5` book lines (70 of the 391 `Sicilian Defense` ones) covered.
- **C, f = 0.01 %, top-3, book-pruned (>= 15 games)**: 884 nodes / 295 lines / max ply 22 (largest kept-reply count 3); book lines covered 426 of 3810; nodes by ply 1: 3, 2: 9, 3: 23, 4: 54, 5: 108, 6: 143, 7: 136, 8: 112, 9: 96, 10: 67, 11: 42, 12: 30, 13: 21, 14: 13, 15: 10, 16: 6, 17: 5, 18: 1, 19: 1, 20: 1, 21: 1, 22: 1. Sicilian: 174 nodes / 56 lines / max ply 17, 83 of the 401 `1.e4 c5` book lines (83 of the 391 `Sicilian Defense` ones) covered.
- **C, f = 0.02 %, UNCAPPED, book-pruned (>= 30 games)**: 1491 nodes / 650 lines / max ply 17 (largest kept-reply count 18); book lines covered 801 of 3810; nodes by ply 1: 18, 2: 74, 3: 154, 4: 223, 5: 255, 6: 231, 7: 191, 8: 130, 9: 89, 10: 55, 11: 32, 12: 17, 13: 10, 14: 5, 15: 3, 16: 2, 17: 1. Sicilian: 190 nodes / 71 lines / max ply 17, 109 of the 401 `1.e4 c5` book lines (108 of the 391 `Sicilian Defense` ones) covered.

### Rule C coverage of the book

Book lines in the tree against the book lines with >= floor games at all (own move order / pooled over move orders).

| cell | floor (games) | book lines in tree / with >= floor (own order) / (pooled) | Sicilian 401: in tree / >= floor (own order) / (pooled) |
|---|---|---|---|
| f = 0.2 %, top-3, book-pruned | >= 300 | 117 / 217 / 261 | 26 / 30 / 32 |
| f = 0.1 %, top-3, book-pruned | >= 150 | 173 / 347 / 427 | 36 / 47 / 53 |
| f = 0.04 %, top-3, book-pruned | >= 60 | 260 / 562 / 707 | 53 / 73 / 94 |
| f = 0.02 %, top-3, book-pruned | >= 30 | 342 / 768 / 996 | 70 / 106 / 133 |
| f = 0.01 %, top-3, book-pruned | >= 15 | 426 / 1006 / 1322 | 83 / 137 / 167 |
| f = 0.02 %, UNCAPPED, book-pruned | >= 30 | 801 / 768 / 996 | 109 / 106 / 133 |

### Rule D: the book itself

Named book lines with traffic in this band, by the row's own move order and pooled over every move order.

| rows | n | any game (own order / pooled) | 0.2 % = >= 300 games (own / pooled) | 0.1 % = >= 150 games (own / pooled) | 0.04 % = >= 60 games (own / pooled) | 0.02 % = >= 30 games (own / pooled) | 0.01 % = >= 15 games (own / pooled) |
|---|---|---|---|---|---|---|---|
| whole book (3810) | 3810 | 2173 / 2756 | 217 / 261 | 347 / 427 | 562 / 707 | 768 / 996 | 1006 / 1322 |
| `1.e4 c5` rows (401) | 401 | 272 / 317 | 30 / 32 | 47 / 53 | 73 / 94 | 106 / 133 | 137 / 167 |
| `Sicilian Defense` rows (391) | 391 | 267 / 311 | 30 / 32 | 47 / 53 | 73 / 94 | 105 / 132 | 136 / 165 |

`1.e4 c5` is reached by 20,806 games (pooled).

### Transposition-only misses at f = 0.02 % (>= 30 games)

Of the named lines with >= floor pooled games: in the top-3 tree; missed by width only (present in the uncapped tree, absent from the top-3 one); missed only because the traffic arrives by move orders other than the book's own (no single move order into the position clears the floor, so the line is absent even from the uncapped tree).

| rows | with >= floor (pooled) | in top-3 tree | missed by width only | missed by transposition only |
|---|---|---|---|---|
| whole book | 996 | 342 | 459 | 195 |
| `1.e4 c5` rows | 133 | 70 | 40 | 23 |

Largest transposition-only misses (whole book), pooled games / own-order games:

| pooled | own order | name | ECO | ply | line |
|---|---|---|---|---|---|
| 215 | 10 | Semi-Slav Defense: Main Line | D45 | 9 | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. e3 e6 5. Nf3` |
| 116 | 9 | Queen's Gambit Declined: Semi-Tarrasch Defense | D40 | 8 | `1. d4 Nf6 2. c4 e6 3. Nf3 d5 4. Nc3 c5` |
| 112 | 4 | Slav Defense: Quiet Variation, Schallopp Defense | D12 | 10 | `1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. e3 Bf5 5. Nc3 e6` |
| 107 | 1 | Queen's Pawn Game: London System | D02 | 11 | `1. d4 d5 2. Nf3 Nf6 3. Bf4 c5 4. e3 Nc6 5. Nbd2 e6 6. c3` |
| 98 | 21 | French Defense: Classical Variation | C13 | 10 | `1. e4 e6 2. d4 d5 3. Nc3 Nf6 4. Bg5 dxe4 5. Nxe4 Be7` |
| 96 | 16 | Queen's Gambit Declined: Three Knights Variation | D37 | 10 | `1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Nf3 Be7 5. e3 O-O` |
| 95 | 11 | King's Indian Defense: Smyslov Variation | E61 | 9 | `1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. Nf3 d6 5. Bg5` |
| 86 | 25 | Bishop's Opening: Vienna Hybrid, Spielmann Attack | C26 | 7 | `1. e4 e5 2. Nc3 Nf6 3. Bc4 Bc5 4. d3` |
| 84 | 1 | Philidor Defense: Lion Variation | C41 | 8 | `1. e4 e5 2. Nf3 d6 3. d4 Nf6 4. Nc3 Nbd7` |
| 83 | 3 | Tarrasch Defense: Symmetrical Variation | D32 | 10 | `1. d4 d5 2. c4 e6 3. Nc3 c5 4. e3 Nf6 5. Nf3 Nc6` |
| 82 | 10 | Modern Defense: Geller's System | B07 | 7 | `1. e4 g6 2. d4 Bg7 3. Nf3 d6 4. c3` |
| 81 | 16 | Old Indian Defense: Czech Variation, with Nc3 | A53 | 6 | `1. d4 Nf6 2. c4 d6 3. Nc3 c6` |

## Band 1500-1800: 214,825 games

First moves: e4 134,140, d4 53,716, c4 6,085, Nf3 5,158, e3 3,136, g3 2,690.

### Summary

| rule | cell | floor (games) | nodes (root incl.) | lines (leaf paths) | max ply | largest kept-reply count | book lines covered (of 3810) | Sicilian nodes | Sicilian lines | Sicilian max ply | Sicilian book lines covered (of 401 / 391) | hits ply cap 36 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | old rule: count >= 0.2 %, top-3 | >= 430 | 157 | 70 | 9 | 3 | 97 | 27 | 10 | 9 | 18 / 18 | no |
| C | f = 0.2 %, top-3, book-pruned | >= 430 | 107 | 47 | 9 | 3 | 97 | 20 | 7 | 8 | 18 / 18 | no |
| C | f = 0.1 %, top-3, book-pruned | >= 215 | 166 | 66 | 11 | 3 | 137 | 28 | 11 | 10 | 24 / 24 | no |
| C | f = 0.04 %, top-3, book-pruned | >= 86 | 263 | 106 | 13 | 3 | 196 | 39 | 17 | 10 | 35 / 35 | no |
| C | f = 0.02 %, top-3, book-pruned | >= 43 | 375 | 148 | 13 | 3 | 239 | 49 | 21 | 12 | 43 / 43 | no |
| C | f = 0.01 %, top-3, book-pruned | >= 22 | 545 | 210 | 16 | 3 | 297 | 78 | 31 | 12 | 51 / 51 | no |
| C | f = 0.02 %, UNCAPPED, book-pruned | >= 43 | 1133 | 547 | 13 | 18 | 658 | 88 | 42 | 12 | 68 / 68 | no |

Rule C, size before the book-pruning step (top-3 or uncapped tree at the floor, ply cap 36):

| cell | nodes before pruning | lines before pruning | max ply before | Sicilian nodes before | Sicilian lines before |
|---|---|---|---|---|---|
| f = 0.2 %, top-3, book-pruned | 157 | 70 | 9 | 27 | 10 |
| f = 0.1 %, top-3, book-pruned | 268 | 117 | 11 | 42 | 17 |
| f = 0.04 %, top-3, book-pruned | 566 | 247 | 14 | 86 | 40 |
| f = 0.02 %, top-3, book-pruned | 1023 | 437 | 15 | 171 | 76 |
| f = 0.01 %, top-3, book-pruned | 1864 | 764 | 18 | 322 | 124 |
| f = 0.02 %, UNCAPPED, book-pruned | 3552 | 1699 | 15 | 386 | 183 |

### Per-rule detail

- **A, old rule: count >= 0.2 %, top-3 (>= 430 games)**: 157 nodes / 70 lines / max ply 9 (largest kept-reply count 3); book lines covered 97 of 3810; nodes by ply 1: 3, 2: 9, 3: 20, 4: 34, 5: 37, 6: 23, 7: 18, 8: 9, 9: 3. Sicilian: 27 nodes / 10 lines / max ply 9, 18 of the 401 `1.e4 c5` book lines (18 of the 391 `Sicilian Defense` ones) covered.
- **C, f = 0.2 %, top-3, book-pruned (>= 430 games)**: 107 nodes / 47 lines / max ply 9 (largest kept-reply count 3); book lines covered 97 of 3810; nodes by ply 1: 3, 2: 9, 3: 17, 4: 22, 5: 20, 6: 16, 7: 10, 8: 8, 9: 1. Sicilian: 20 nodes / 7 lines / max ply 8, 18 of the 401 `1.e4 c5` book lines (18 of the 391 `Sicilian Defense` ones) covered.
- **C, f = 0.1 %, top-3, book-pruned (>= 215 games)**: 166 nodes / 66 lines / max ply 11 (largest kept-reply count 3); book lines covered 137 of 3810; nodes by ply 1: 3, 2: 9, 3: 18, 4: 30, 5: 34, 6: 29, 7: 19, 8: 16, 9: 4, 10: 2, 11: 1. Sicilian: 28 nodes / 11 lines / max ply 10, 24 of the 401 `1.e4 c5` book lines (24 of the 391 `Sicilian Defense` ones) covered.
- **C, f = 0.04 %, top-3, book-pruned (>= 86 games)**: 263 nodes / 106 lines / max ply 13 (largest kept-reply count 3); book lines covered 196 of 3810; nodes by ply 1: 3, 2: 9, 3: 21, 4: 39, 5: 55, 6: 50, 7: 32, 8: 28, 9: 14, 10: 6, 11: 3, 12: 1, 13: 1. Sicilian: 39 nodes / 17 lines / max ply 10, 35 of the 401 `1.e4 c5` book lines (35 of the 391 `Sicilian Defense` ones) covered.
- **C, f = 0.02 %, top-3, book-pruned (>= 43 games)**: 375 nodes / 148 lines / max ply 13 (largest kept-reply count 3); book lines covered 239 of 3810; nodes by ply 1: 3, 2: 9, 3: 21, 4: 42, 5: 71, 6: 72, 7: 57, 8: 44, 9: 28, 10: 15, 11: 8, 12: 3, 13: 1. Sicilian: 49 nodes / 21 lines / max ply 12, 43 of the 401 `1.e4 c5` book lines (43 of the 391 `Sicilian Defense` ones) covered.
- **C, f = 0.01 %, top-3, book-pruned (>= 22 games)**: 545 nodes / 210 lines / max ply 16 (largest kept-reply count 3); book lines covered 297 of 3810; nodes by ply 1: 3, 2: 9, 3: 21, 4: 45, 5: 84, 6: 100, 7: 89, 8: 72, 9: 58, 10: 38, 11: 13, 12: 5, 13: 2, 14: 2, 15: 2, 16: 1. Sicilian: 78 nodes / 31 lines / max ply 12, 51 of the 401 `1.e4 c5` book lines (51 of the 391 `Sicilian Defense` ones) covered.
- **C, f = 0.02 %, UNCAPPED, book-pruned (>= 43 games)**: 1133 nodes / 547 lines / max ply 13 (largest kept-reply count 18); book lines covered 658 of 3810; nodes by ply 1: 18, 2: 72, 3: 138, 4: 199, 5: 214, 6: 188, 7: 132, 8: 82, 9: 49, 10: 26, 11: 10, 12: 3, 13: 1. Sicilian: 88 nodes / 42 lines / max ply 12, 68 of the 401 `1.e4 c5` book lines (68 of the 391 `Sicilian Defense` ones) covered.

### Rule C coverage of the book

Book lines in the tree against the book lines with >= floor games at all (own move order / pooled over move orders).

| cell | floor (games) | book lines in tree / with >= floor (own order) / (pooled) | Sicilian 401: in tree / >= floor (own order) / (pooled) |
|---|---|---|---|
| f = 0.2 %, top-3, book-pruned | >= 430 | 97 / 200 / 239 | 18 / 24 / 25 |
| f = 0.1 %, top-3, book-pruned | >= 215 | 137 / 295 / 361 | 24 / 32 / 35 |
| f = 0.04 %, top-3, book-pruned | >= 86 | 196 / 473 / 571 | 35 / 53 / 60 |
| f = 0.02 %, top-3, book-pruned | >= 43 | 239 / 630 / 793 | 43 / 67 / 85 |
| f = 0.01 %, top-3, book-pruned | >= 22 | 297 / 823 / 1041 | 51 / 96 / 121 |
| f = 0.02 %, UNCAPPED, book-pruned | >= 43 | 658 / 630 / 793 | 68 / 67 / 85 |

### Rule D: the book itself

Named book lines with traffic in this band, by the row's own move order and pooled over every move order.

| rows | n | any game (own order / pooled) | 0.2 % = >= 430 games (own / pooled) | 0.1 % = >= 215 games (own / pooled) | 0.04 % = >= 86 games (own / pooled) | 0.02 % = >= 43 games (own / pooled) | 0.01 % = >= 22 games (own / pooled) |
|---|---|---|---|---|---|---|---|
| whole book (3810) | 3810 | 1973 / 2486 | 200 / 239 | 295 / 361 | 473 / 571 | 630 / 793 | 823 / 1041 |
| `1.e4 c5` rows (401) | 401 | 236 / 286 | 24 / 25 | 32 / 35 | 53 / 60 | 67 / 85 | 96 / 121 |
| `Sicilian Defense` rows (391) | 391 | 233 / 280 | 24 / 25 | 32 / 35 | 53 / 60 | 67 / 85 | 96 / 121 |

`1.e4 c5` is reached by 22,488 games (pooled).

### Transposition-only misses at f = 0.02 % (>= 43 games)

Of the named lines with >= floor pooled games: in the top-3 tree; missed by width only (present in the uncapped tree, absent from the top-3 one); missed only because the traffic arrives by move orders other than the book's own (no single move order into the position clears the floor, so the line is absent even from the uncapped tree).

| rows | with >= floor (pooled) | in top-3 tree | missed by width only | missed by transposition only |
|---|---|---|---|---|
| whole book | 793 | 239 | 419 | 135 |
| `1.e4 c5` rows | 85 | 43 | 25 | 17 |

Largest transposition-only misses (whole book), pooled games / own-order games:

| pooled | own order | name | ECO | ply | line |
|---|---|---|---|---|---|
| 249 | 22 | London System | A48 | 8 | `1. d4 Nf6 2. Nf3 g6 3. Bf4 Bg7 4. e3 d6` |
| 177 | 16 | Italian Game: Giuoco Pianissimo | C50 | 10 | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. Nc3 Nf6 5. O-O O-O` |
| 166 | 37 | Sicilian Defense: Classical Variation | B56 | 10 | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 Nc6` |
| 153 | 8 | Italian Game: Giuoco Pianissimo | C50 | 11 | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. Nc3 Nf6 5. O-O O-O 6. d3` |
| 142 | 13 | Modern Defense: Geller's System | B07 | 7 | `1. e4 g6 2. d4 Bg7 3. Nf3 d6 4. c3` |
| 142 | 7 | Semi-Slav Defense: Main Line | D45 | 9 | `1. d4 d5 2. c4 c6 3. Nc3 Nf6 4. e3 e6 5. Nf3` |
| 132 | 25 | Bishop's Opening: Vienna Hybrid, Spielmann Attack | C26 | 7 | `1. e4 e5 2. Nc3 Nf6 3. Bc4 Bc5 4. d3` |
| 130 | 17 | Italian Game: Classical Variation, Giuoco Pianissimo | C54 | 11 | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. d3 h6 6. c3` |
| 125 | 22 | Sicilian Defense: Taimanov Variation | B46 | 10 | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nc3 a6` |
| 123 | 18 | Slav Defense: Quiet Variation | D11 | 7 | `1. d4 d5 2. c4 c6 3. Nf3 Nf6 4. e3` |
| 123 | 4 | Queen's Gambit Declined: Semi-Tarrasch Defense | D40 | 8 | `1. d4 Nf6 2. c4 e6 3. Nf3 d5 4. Nc3 c5` |
| 116 | 34 | Italian Game: Classical Variation, Giuoco Pianissimo | C54 | 10 | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 d6` |

## Rule E: band 1800-2100, rule C top-3, the Sicilian in detail

### f = 0.02 % (>= 30 games): Sicilian leaf lines (40)

Every leaf is an exactly-named position. Sorted by move sequence.

| ply | ECO | name | games (this order) | line |
|---|---|---|---|---|
| 9 | B45 | Sicilian Defense: Taimanov Variation | 30 | `e4 c5 Nc3 Nc6 Nf3 e6 d4 cxd4 Nxd4` |
| 5 | B23 | Sicilian Defense: Grand Prix Attack | 253 | `e4 c5 Nc3 Nc6 f4` |
| 8 | B24 | Sicilian Defense: Closed | 53 | `e4 c5 Nc3 Nc6 g3 g6 Bg2 Bg7` |
| 5 | B23 | Sicilian Defense: Closed | 81 | `e4 c5 Nc3 e6 g3` |
| 6 | B31 | Sicilian Defense: Nyezhmetdinov-Rossolimo Attack, Fianchetto Variation | 155 | `e4 c5 Nf3 Nc6 Bb5 g6` |
| 10 | B56 | Sicilian Defense: Classical Variation | 64 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 Nf6 Nc3 d6` |
| 17 | B33 | Sicilian Defense: Lasker-Pelikan Variation, Sveshnikov Variation, Chelyabinsk Variation | 34 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 Nf6 Nc3 e5 Ndb5 d6 Bg5 a6 Na3 b5 Nd5` |
| 10 | B45 | Sicilian Defense: Four Knights Variation | 76 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 Nf6 Nc3 e6` |
| 11 | B33 | Sicilian Defense: Lasker-Pelikan Variation, Schlechter Variation | 48 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 e5 Nb3 Nf6 Nc3` |
| 10 | B32 | Sicilian Defense: Kalashnikov Variation | 203 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 e5 Nb5 d6` |
| 9 | B34 | Sicilian Defense: Accelerated Dragon, Modern Variation | 210 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 g6 Nc3` |
| 9 | B34 | Sicilian Defense: Accelerated Dragon, Exchange Variation | 98 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 g6 Nxc6` |
| 5 | B50 | Sicilian Defense: Delayed Alapin Variation, with d6 | 364 | `e4 c5 Nf3 d6 c3` |
| 10 | B56 | Sicilian Defense: Classical Variation | 80 | `e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 Nc6` |
| 11 | B90 | Sicilian Defense: Najdorf Variation, Lipnitsky Attack | 94 | `e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 Bc4` |
| 11 | B90 | Sicilian Defense: Najdorf Variation, English Attack | 141 | `e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 Be3` |
| 14 | B98 | Sicilian Defense: Najdorf Variation | 43 | `e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 Bg5 e6 f4 Be7` |
| 16 | B76 | Sicilian Defense: Dragon Variation, Yugoslav Attack | 36 | `e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 g6 Be3 Bg7 f3 O-O Qd2 Nc6` |
| 13 | B75 | Sicilian Defense: Dragon Variation, Yugoslav Attack, Early Deviations | 30 | `e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 g6 f3 Bg7 Be3` |
| 9 | B54 | Sicilian Defense: Prins Variation | 36 | `e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 f3` |
| 7 | B53 | Sicilian Defense: Chekhover Variation | 83 | `e4 c5 Nf3 d6 d4 cxd4 Qxd4` |
| 7 | B50 | Sicilian Defense: Modern Variations, Tartakower | 71 | `e4 c5 Nf3 d6 d4 cxd4 c3` |
| 9 | B45 | Sicilian Defense: Taimanov Variation | 30 | `e4 c5 Nf3 e6 Nc3 Nc6 d4 cxd4 Nxd4` |
| 9 | B43 | Sicilian Defense: Kan Variation, Knight Variation | 35 | `e4 c5 Nf3 e6 Nc3 a6 d4 cxd4 Nxd4` |
| 5 | B40 | Sicilian Defense: Delayed Alapin Variation, with e6 | 321 | `e4 c5 Nf3 e6 c3` |
| 6 | B40 | Sicilian Defense: Drazic Variation | 31 | `e4 c5 Nf3 e6 d4 a6` |
| 10 | B45 | Sicilian Defense: Four Knights Variation | 38 | `e4 c5 Nf3 e6 d4 cxd4 Nxd4 Nc6 Nc3 Nf6` |
| 10 | B47 | Sicilian Defense: Taimanov Variation, Bastrikov Variation | 39 | `e4 c5 Nf3 e6 d4 cxd4 Nxd4 Nc6 Nc3 Qc7` |
| 10 | B46 | Sicilian Defense: Taimanov Variation | 35 | `e4 c5 Nf3 e6 d4 cxd4 Nxd4 Nc6 Nc3 a6` |
| 10 | B40 | Sicilian Defense: Pin Variation | 32 | `e4 c5 Nf3 e6 d4 cxd4 Nxd4 Nf6 Nc3 Bb4` |
| 10 | B45 | Sicilian Defense: Four Knights Variation | 59 | `e4 c5 Nf3 e6 d4 cxd4 Nxd4 Nf6 Nc3 Nc6` |
| 9 | B42 | Sicilian Defense: Kan Variation, Modern Variation | 40 | `e4 c5 Nf3 e6 d4 cxd4 Nxd4 a6 Bd3` |
| 10 | B43 | Sicilian Defense: Kan Variation, Wing Attack | 38 | `e4 c5 Nf3 e6 d4 cxd4 Nxd4 a6 Nc3 b5` |
| 9 | B41 | Sicilian Defense: Kan Variation, Maróczy Bind, Réti Variation | 70 | `e4 c5 Nf3 e6 d4 cxd4 Nxd4 a6 c4` |
| 7 | B40 | Sicilian Defense: Smith-Morra Gambit Deferred | 39 | `e4 c5 Nf3 e6 d4 cxd4 c3` |
| 6 | B40 | Sicilian Defense: Marshall Counterattack | 72 | `e4 c5 Nf3 e6 d4 d5` |
| 7 | B32 | Sicilian Defense: Open | 62 | `e4 c5 d4 cxd4 Nf3 Nc6 Nxd4` |
| 6 | B21 | Sicilian Defense: Smith-Morra Gambit Declined, Push Variation | 96 | `e4 c5 d4 cxd4 c3 d3` |
| 6 | B21 | Sicilian Defense: Smith-Morra Gambit Accepted | 610 | `e4 c5 d4 cxd4 c3 dxc3` |
| 5 | A43 | Benoni Defense: French Benoni | 33 | `e4 c5 d4 e6 d5` |

### f = 0.02 %: named `1.e4 c5` book lines with >= 30 games (pooled) that top-3 misses (63)

`why` walks the book's own move order through the trie and names the first move not in the rule-C tree: its games in that order and its rank among the parent's replies with >= 30 games (the kept top-3 are listed).

| name | ECO | ply | games (pooled) | games (own order) | why | line |
|---|---|---|---|---|---|---|
| Sicilian Defense: Alapin Variation | B22 | 3 | 1648 | 1648 | ply 3: c3 has 1648 games, rank 4 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. c3` |
| Sicilian Defense: Bowdler Attack | B20 | 3 | 1340 | 1340 | ply 3: Bc4 has 1340 games, rank 5 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. Bc4` |
| Sicilian Defense: McDonnell Attack | B21 | 3 | 1287 | 1242 | ply 3: f4 has 1242 games, rank 6 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. f4` |
| Sicilian Defense: Hyperaccelerated Dragon | B27 | 4 | 525 | 516 | ply 4: g6 has 516 games, rank 4 of 7 (outside top-3; kept: Nc6 4950, d6 3250, e6 2098) | `1. e4 c5 2. Nf3 g6` |
| Sicilian Defense: Wing Gambit | B20 | 3 | 285 | 285 | ply 3: b4 has 285 games, rank 8 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. b4` |
| Sicilian Defense: Hyperaccelerated Dragon | B27 | 5 | 270 | 263 | ply 4: g6 has 516 games, rank 4 of 7 (outside top-3; kept: Nc6 4950, d6 3250, e6 2098) | `1. e4 c5 2. Nf3 g6 3. d4` |
| Sicilian Defense: Staunton-Cochrane Variation | B20 | 3 | 266 | 260 | ply 3: c4 has 260 games, rank 9 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. c4` |
| Sicilian Defense: Mengarini Variation | B20 | 3 | 241 | 241 | ply 3: a3 has 241 games, rank 10 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. a3` |
| Sicilian Defense: Moscow Variation | B51 | 5 | 241 | 238 | ply 5: Bb5+ has 238 games, rank 4 of 10 (outside top-3; kept: d4 1829, Bc4 422, c3 364) | `1. e4 c5 2. Nf3 d6 3. Bb5+` |
| Sicilian Defense: O'Kelly Variation | B28 | 4 | 236 | 230 | ply 4: a6 has 230 games, rank 5 of 7 (outside top-3; kept: Nc6 4950, d6 3250, e6 2098) | `1. e4 c5 2. Nf3 a6` |
| Sicilian Defense: Alapin Variation, Barmen Defense | B22 | 6 | 233 | 233 | ply 3: c3 has 1648 games, rank 4 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. c3 d5 3. exd5 Qxd5` |
| Sicilian Defense: Alapin Variation, Smith-Morra Declined | B22 | 8 | 166 | 108 | ply 3: c3 has 1648 games, rank 4 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. c3 Nf6 3. e5 Nd5 4. d4 cxd4` |
| Sicilian Defense: Moscow Variation, Main Line | B52 | 6 | 143 | 142 | ply 5: Bb5+ has 238 games, rank 4 of 10 (outside top-3; kept: d4 1829, Bc4 422, c3 364) | `1. e4 c5 2. Nf3 d6 3. Bb5+ Bd7` |
| Sicilian Defense: O'Kelly Variation, Normal System | B28 | 5 | 142 | 137 | ply 4: a6 has 230 games, rank 5 of 7 (outside top-3; kept: Nc6 4950, d6 3250, e6 2098) | `1. e4 c5 2. Nf3 a6 3. d4` |
| Sicilian Defense: Lasker-Dunne Attack | B20 | 3 | 129 | 129 | ply 3: g3 has 129 games, rank 11 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. g3` |
| Sicilian Defense: Hyperaccelerated Pterodactyl | B27 | 6 | 119 | 27 | ply 4: g6 has 516 games, rank 4 of 7 (outside top-3; kept: Nc6 4950, d6 3250, e6 2098) | `1. e4 c5 2. Nf3 g6 3. d4 Bg7` |
| Sicilian Defense: Czerniak Attack | B20 | 3 | 118 | 117 | ply 3: b3 has 117 games, rank 12 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. b3` |
| Sicilian Defense: Wing Gambit, Marshall Variation | B20 | 5 | 97 | 97 | ply 3: b4 has 285 games, rank 8 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. b4 cxb4 3. a3` |
| Sicilian Defense: Alapin Variation, Barmen Defense | B22 | 9 | 95 | 31 | ply 3: c3 has 1648 games, rank 4 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. c3 d5 3. exd5 Qxd5 4. d4 Nc6 5. Nf3` |
| Sicilian Defense: Najdorf Variation, Opocensky Variation | B92 | 11 | 94 | 87 | ply 11: Be2 has 87 games, rank 4 of 7 (outside top-3; kept: Bg5 143, Be3 141, Bc4 94) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be2` |
| Sicilian Defense: Keres Variation | B20 | 3 | 93 | 93 | ply 3: Ne2 has 93 games, rank 13 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. Ne2` |
| Sicilian Defense: Accelerated Dragon, Maróczy Bind | B37 | 10 | 90 | 43 | ply 9: c4 has 53 games, rank 4 of 4 (outside top-3; kept: Nc3 210, Nxc6 98, Be3 66) | `1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 5. c4 Bg7` |
| Sicilian Defense: Scheveningen Variation | B80 | 10 | 87 | 25 | ply 10: d6 has 25 games in this order (< 30) | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 d6` |
| Sicilian Defense: Accelerated Dragon, Maróczy Bind | B38 | 11 | 86 | 40 | ply 9: c4 has 53 games, rank 4 of 4 (outside top-3; kept: Nc3 210, Nxc6 98, Be3 66) | `1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 5. c4 Bg7 6. Be3` |
| Sicilian Defense: Closed, Anti-Sveshnikov Variation | B30 | 6 | 82 | 34 | ply 5: Nc3 has 307 games, rank 5 of 10 (outside top-3; kept: d4 2395, Bb5 675, Bc4 637) | `1. e4 c5 2. Nf3 Nc6 3. Nc3 e5` |
| Sicilian Defense: Accelerated Dragon, Maróczy Bind | B36 | 9 | 81 | 53 | ply 9: c4 has 53 games, rank 4 of 4 (outside top-3; kept: Nc3 210, Nxc6 98, Be3 66) | `1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 5. c4` |
| Sicilian Defense: Alapin Variation, Barmen Defense, Central Exchange | B22 | 12 | 80 | 18 | ply 3: c3 has 1648 games, rank 4 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. c3 d5 3. exd5 Qxd5 4. d4 cxd4 5. cxd4 Nc6 6. Nf3 Bg4` |
| Sicilian Defense: Accelerated Dragon, Modern Bc4 Variation | B35 | 13 | 74 | 28 | ply 10: Bg7 (204 games, rank 1) pruned, nothing named with >= 30 games below it in this order; the book's own order drops below the floor at ply 13: Bc4 has 28 games in this order (< 30) | `1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 5. Nc3 Bg7 6. Be3 Nf6 7. Bc4` |
| Sicilian Defense: Nimzowitsch Variation | B29 | 4 | 71 | 68 | ply 4: Nf6 has 68 games, rank 6 of 7 (outside top-3; kept: Nc6 4950, d6 3250, e6 2098) | `1. e4 c5 2. Nf3 Nf6` |
| Sicilian Defense: Kramnik Variation | B40 | 5 | 70 | 50 | ply 5: c4 has 50 games, rank 6 of 7 (outside top-3; kept: d4 1152, c3 321, Nc3 192) | `1. e4 c5 2. Nf3 e6 3. c4` |
| Sicilian Defense: Dragon Variation, Yugoslav Attack, Modern Line | B76 | 17 | 70 | 4 | ply 14: Nc6 has 11 games in this order (< 30) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6 6. Be3 Bg7 7. f3 Nc6 8. Qd2 O-O 9. O-O-O` |
| Sicilian Defense: Smith-Morra Gambit Declined, Alapin Formation | B21 | 6 | 67 | 62 | ply 6: Nf6 has 62 games, rank 4 of 5 (outside top-3; kept: dxc3 610, d3 96, Nc6 68) | `1. e4 c5 2. d4 cxd4 3. c3 Nf6` |
| Sicilian Defense: Smith-Morra Gambit Accepted, Paulsen Formation | B21 | 12 | 64 | 10 | ply 7: Nxc3 (545 games, rank 1) pruned, nothing named with >= 30 games below it in this order; the book's own order drops below the floor at ply 12: a6 has 10 games in this order (< 30) | `1. e4 c5 2. d4 cxd4 3. c3 dxc3 4. Nxc3 Nc6 5. Nf3 e6 6. Bc4 a6` |
| Sicilian Defense: Dragon Variation, Yugoslav Attack, Belezky Line | B75 | 14 | 62 | 11 | ply 14: Nc6 has 11 games in this order (< 30) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6 6. Be3 Bg7 7. f3 Nc6` |
| Sicilian Defense: Najdorf Variation, Yates Variation | B90 | 11 | 61 | 53 | ply 11: Bd3 has 53 games, rank 6 of 7 (outside top-3; kept: Bg5 143, Be3 141, Bc4 94) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Bd3` |
| Sicilian Defense: Portsmouth Gambit | B30 | 5 | 55 | 55 | ply 5: b4 has 55 games, rank 7 of 10 (outside top-3; kept: d4 2395, Bb5 675, Bc4 637) | `1. e4 c5 2. Nf3 Nc6 3. b4` |
| Sicilian Defense: Smith-Morra Gambit Declined, Center Formation | B21 | 6 | 55 | 25 | ply 6: e5 has 25 games in this order (< 30) | `1. e4 c5 2. d4 cxd4 3. c3 e5` |
| Sicilian Defense: Dragon Variation, Accelerated Dragon | B54 | 8 | 55 | 53 | ply 8: g6 has 53 games, rank 5 of 6 (outside top-3; kept: Nf6 1239, Nc6 128, a6 84) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 g6` |
| Sicilian Defense: Smith-Morra Gambit Declined, Scandinavian Formation | B21 | 6 | 52 | 52 | ply 6: d5 has 52 games, rank 5 of 5 (outside top-3; kept: dxc3 610, d3 96, Nc6 68) | `1. e4 c5 2. d4 cxd4 3. c3 d5` |
| Sicilian Defense: Paulsen-Basman Defense | B40 | 8 | 52 | 40 | ply 8: Bc5 has 40 games, rank 4 of 4 (outside top-3; kept: a6 378, Nc6 266, Nf6 174) | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Bc5` |
| Sicilian Defense: Scheveningen Variation, English Attack, with f3 | B90 | 13 | 50 | 20 | ply 12: e6 (40 games, rank 2) pruned, nothing named with >= 30 games below it in this order; the book's own order drops below the floor at ply 13: f3 has 20 games in this order (< 30) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be3 e6 7. f3` |
| Sicilian Defense: Wing Gambit, Carlsbad Variation | B20 | 6 | 48 | 48 | ply 3: b4 has 285 games, rank 8 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. b4 cxb4 3. a3 bxa3` |
| Sicilian Defense: Godiva Variation | B32 | 8 | 46 | 44 | ply 8: Qb6 has 44 games, rank 8 of 8 (outside top-3; kept: e5 655, g6 475, Nf6 435) | `1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Qb6` |
| Sicilian Defense: Four Knights Variation, Exchange Variation | B45 | 11 | 46 | 4 | ply 11: Nxc6 has 4 games in this order (< 30) | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nc3 Nf6 6. Nxc6` |
| Sicilian Defense: Classical Variation, Sozin Attack | B57 | 11 | 46 | 11 | ply 11: Bc4 has 11 games in this order (< 30) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 Nc6 6. Bc4` |
| Sicilian Defense: Smith-Morra Gambit Accepted, Fianchetto Defense | B21 | 8 | 45 | 45 | ply 7: Nxc3 (545 games, rank 1) pruned, nothing named with >= 30 games below it in this order; the book's own order drops below the floor at ply 0: ? has 0 games in this order (< 30) | `1. e4 c5 2. d4 cxd4 3. c3 dxc3 4. Nxc3 g6` |
| Sicilian Defense: Smith-Morra Gambit Accepted, Pin Defense | B21 | 12 | 45 | 14 | ply 7: Nxc3 (545 games, rank 1) pruned, nothing named with >= 30 games below it in this order; the book's own order drops below the floor at ply 12: Bb4 has 14 games in this order (< 30) | `1. e4 c5 2. d4 cxd4 3. c3 dxc3 4. Nxc3 Nc6 5. Nf3 e6 6. Bc4 Bb4` |
| Sicilian Defense: Franco-Sicilian Variation | B32 | 6 | 42 | 24 | ply 6: e6 has 24 games in this order (< 30) | `1. e4 c5 2. Nf3 Nc6 3. d4 e6` |
| Sicilian Defense: Dragon Variation, Yugoslav Attack, Main Line | B77 | 17 | 42 | 8 | ply 17: Bc4 has 8 games in this order (< 30) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6 6. Be3 Bg7 7. f3 O-O 8. Qd2 Nc6 9. Bc4` |
| Sicilian Defense: Richter-Rauzer Variation | B60 | 11 | 40 | 12 | ply 11: Bg5 has 12 games in this order (< 30) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 Nc6 6. Bg5` |
| Sicilian Defense: Delayed Alapin Variation | B22 | 10 | 38 | 13 | ply 6: d5 (141 games, rank 1) pruned, nothing named with >= 30 games below it in this order; the book's own order drops below the floor at ply 9: d4 has 23 games in this order (< 30) | `1. e4 c5 2. Nf3 e6 3. c3 d5 4. exd5 Qxd5 5. d4 Nf6` |
| Sicilian Defense: Smith-Morra Gambit Accepted, Scheveningen Formation | B21 | 12 | 38 | 15 | ply 7: Nxc3 (545 games, rank 1) pruned, nothing named with >= 30 games below it in this order; the book's own order drops below the floor at ply 12: e6 has 15 games in this order (< 30) | `1. e4 c5 2. d4 cxd4 3. c3 dxc3 4. Nxc3 Nc6 5. Nf3 d6 6. Bc4 e6` |
| King's Gambit Declined: Mafia Defense | C30 | 4 | 37 | 35 | ply 3: f4 has 1242 games, rank 6 of 16 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. f4 e5` |
| Sicilian Defense: Smith-Morra Gambit Accepted, Kan Formation | B21 | 10 | 37 | 25 | ply 7: Nxc3 (545 games, rank 1) pruned, nothing named with >= 30 games below it in this order; the book's own order drops below the floor at ply 10: a6 has 25 games in this order (< 30) | `1. e4 c5 2. d4 cxd4 3. c3 dxc3 4. Nxc3 e6 5. Nf3 a6` |
| Sicilian Defense: Taimanov Variation, Szén Variation | B44 | 9 | 35 | 14 | ply 9: Nb5 has 14 games in this order (< 30) | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nb5` |
| Sicilian Defense: Scheveningen Variation, Classical Variation | B84 | 12 | 35 | 22 | ply 11: Be2 has 87 games, rank 4 of 7 (outside top-3; kept: Bg5 143, Be3 141, Bc4 94) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be2 e6` |
| Sicilian Defense: O'Kelly Variation, Normal System, Taimanov Line | B28 | 8 | 34 | 33 | ply 4: a6 has 230 games, rank 5 of 7 (outside top-3; kept: Nc6 4950, d6 3250, e6 2098) | `1. e4 c5 2. Nf3 a6 3. d4 cxd4 4. Nxd4 e5` |
| Sicilian Defense: Najdorf Variation, English Attack | B90 | 15 | 34 | 17 | ply 12: e5 (62 games, rank 1) pruned, nothing named with >= 30 games below it in this order; the book's own order drops below the floor at ply 15: f3 has 17 games in this order (< 30) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be3 e5 7. Nb3 Be6 8. f3` |
| Sicilian Defense: Smith-Morra Gambit Accepted, Fianchetto Defense | B21 | 10 | 33 | 22 | ply 7: Nxc3 (545 games, rank 1) pruned, nothing named with >= 30 games below it in this order; the book's own order drops below the floor at ply 10: g6 has 22 games in this order (< 30) | `1. e4 c5 2. d4 cxd4 3. c3 dxc3 4. Nxc3 Nc6 5. Nf3 g6` |
| Sicilian Defense: Closed | B25 | 10 | 33 | 11 | ply 9: d3 has 22 games in this order (< 30) | `1. e4 c5 2. Nc3 Nc6 3. g3 g6 4. Bg2 Bg7 5. d3 d6` |
| Sicilian Defense: Lasker-Pelikan Variation, Retreat Variation | B33 | 11 | 31 | 9 | ply 11: Nf3 has 9 games in this order (< 30) | `1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e5 6. Nf3` |
| Sicilian Defense: Dragon Variation, Classical Variation | B70 | 11 | 31 | 29 | ply 11: Be2 has 29 games in this order (< 30) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6 6. Be2` |
| Sicilian Defense: Sozin Attack | B86 | 11 | 30 | 3 | ply 10: d6 has 25 games in this order (< 30) | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 d6 6. Bc4` |

Reasons: a move on the way ranks outside the top-3: 39; a move on the way is below the floor in the book's own move order (traffic by transposition): 24.

### f = 0.1 % (>= 150 games): Sicilian leaf lines (15)

Every leaf is an exactly-named position. Sorted by move sequence.

| ply | ECO | name | games (this order) | line |
|---|---|---|---|---|
| 5 | B23 | Sicilian Defense: Grand Prix Attack | 253 | `e4 c5 Nc3 Nc6 f4` |
| 4 | B23 | Sicilian Defense: Closed | 476 | `e4 c5 Nc3 e6` |
| 6 | B31 | Sicilian Defense: Nyezhmetdinov-Rossolimo Attack, Fianchetto Variation | 155 | `e4 c5 Nf3 Nc6 Bb5 g6` |
| 10 | B33 | Sicilian Defense: Lasker-Pelikan Variation | 151 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 Nf6 Nc3 e5` |
| 10 | B32 | Sicilian Defense: Kalashnikov Variation | 203 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 e5 Nb5 d6` |
| 9 | B34 | Sicilian Defense: Accelerated Dragon, Modern Variation | 210 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 g6 Nc3` |
| 5 | B50 | Sicilian Defense: Delayed Alapin Variation, with d6 | 364 | `e4 c5 Nf3 d6 c3` |
| 10 | B90 | Sicilian Defense: Najdorf Variation | 681 | `e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6` |
| 10 | B70 | Sicilian Defense: Dragon Variation | 261 | `e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 g6` |
| 5 | B40 | Sicilian Defense: Delayed Alapin Variation, with e6 | 321 | `e4 c5 Nf3 e6 c3` |
| 8 | B44 | Sicilian Defense: Taimanov Variation | 266 | `e4 c5 Nf3 e6 d4 cxd4 Nxd4 Nc6` |
| 8 | B40 | Sicilian Defense: French Variation, Normal | 174 | `e4 c5 Nf3 e6 d4 cxd4 Nxd4 Nf6` |
| 9 | B43 | Sicilian Defense: Kan Variation, Knight Variation | 188 | `e4 c5 Nf3 e6 d4 cxd4 Nxd4 a6 Nc3` |
| 5 | B21 | Sicilian Defense: Morphy Gambit | 192 | `e4 c5 d4 cxd4 Nf3` |
| 6 | B21 | Sicilian Defense: Smith-Morra Gambit Accepted | 610 | `e4 c5 d4 cxd4 c3 dxc3` |

### f = 0.1 %: named `1.e4 c5` book lines with >= 150 games (pooled) that top-3 misses (17)

`why` walks the book's own move order through the trie and names the first move not in the rule-C tree: its games in that order and its rank among the parent's replies with >= 150 games (the kept top-3 are listed).

| name | ECO | ply | games (pooled) | games (own order) | why | line |
|---|---|---|---|---|---|---|
| Sicilian Defense: Alapin Variation | B22 | 3 | 1648 | 1648 | ply 3: c3 has 1648 games, rank 4 of 10 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. c3` |
| Sicilian Defense: Bowdler Attack | B20 | 3 | 1340 | 1340 | ply 3: Bc4 has 1340 games, rank 5 of 10 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. Bc4` |
| Sicilian Defense: McDonnell Attack | B21 | 3 | 1287 | 1242 | ply 3: f4 has 1242 games, rank 6 of 10 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. f4` |
| Sicilian Defense: Hyperaccelerated Dragon | B27 | 4 | 525 | 516 | ply 4: g6 has 516 games, rank 4 of 5 (outside top-3; kept: Nc6 4950, d6 3250, e6 2098) | `1. e4 c5 2. Nf3 g6` |
| Sicilian Defense: Taimanov Variation | B45 | 9 | 400 | 145 | ply 9: Nc3 has 145 games in this order (< 150) | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nc3` |
| Sicilian Defense: Wing Gambit | B20 | 3 | 285 | 285 | ply 3: b4 has 285 games, rank 8 of 10 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. b4` |
| Sicilian Defense: Hyperaccelerated Dragon | B27 | 5 | 270 | 263 | ply 4: g6 has 516 games, rank 4 of 5 (outside top-3; kept: Nc6 4950, d6 3250, e6 2098) | `1. e4 c5 2. Nf3 g6 3. d4` |
| Sicilian Defense: Staunton-Cochrane Variation | B20 | 3 | 266 | 260 | ply 3: c4 has 260 games, rank 9 of 10 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. c4` |
| Sicilian Defense: Four Knights Variation | B45 | 10 | 249 | 38 | ply 9: Nc3 has 145 games in this order (< 150) | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nc3 Nf6` |
| Sicilian Defense: Mengarini Variation | B20 | 3 | 241 | 241 | ply 3: a3 has 241 games, rank 10 of 10 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. a3` |
| Sicilian Defense: Moscow Variation | B51 | 5 | 241 | 238 | ply 5: Bb5+ has 238 games, rank 4 of 5 (outside top-3; kept: d4 1829, Bc4 422, c3 364) | `1. e4 c5 2. Nf3 d6 3. Bb5+` |
| Sicilian Defense: Classical Variation | B56 | 10 | 237 | 80 | ply 10: Nc6 has 80 games in this order (< 150) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 Nc6` |
| Sicilian Defense: O'Kelly Variation | B28 | 4 | 236 | 230 | ply 4: a6 has 230 games, rank 5 of 5 (outside top-3; kept: Nc6 4950, d6 3250, e6 2098) | `1. e4 c5 2. Nf3 a6` |
| Sicilian Defense: Alapin Variation, Barmen Defense | B22 | 6 | 233 | 233 | ply 3: c3 has 1648 games, rank 4 of 10 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. c3 d5 3. exd5 Qxd5` |
| Sicilian Defense: Alapin Variation, Smith-Morra Declined | B22 | 8 | 166 | 108 | ply 3: c3 has 1648 games, rank 4 of 10 (outside top-3; kept: Nf3 11186, Nc3 2080, d4 1695) | `1. e4 c5 2. c3 Nf6 3. e5 Nd5 4. d4 cxd4` |
| Sicilian Defense: Najdorf Variation | B94 | 11 | 161 | 143 | ply 11: Bg5 has 143 games in this order (< 150) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Bg5` |
| Sicilian Defense: Taimanov Variation | B46 | 10 | 150 | 35 | ply 9: Nc3 has 145 games in this order (< 150) | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nc3 a6` |

Reasons: a move on the way ranks outside the top-3: 12; a move on the way is below the floor in the book's own move order (traffic by transposition): 5.

Against the 0.02 % set: 97 named `1.e4 c5` lines with >= 30 pooled games are not in this tree; by reason: a move on the way is below the floor in the book's own move order (traffic by transposition): 75; a move on the way ranks outside the top-3: 22.

## Width variants

Rule C (width-limited tree at the floor, then every node with no exactly-named position at or below it pruned) under other width rules, at floors 0.02 % and 0.04 %. **top-k**: the k most played replies clearing the floor (count desc, SAN desc ties). **top-3 + share s %**: the top-3 plus every further reply clearing the floor whose count is >= s % of the games reaching the parent position in this move order (a fourth or later reply survives only as a real share of that position's traffic). **UNCAPPED**: every reply clearing the floor. The top-3 and 0.02 % UNCAPPED rows repeat the summary cells above (same trees) for reference. **Internal nodes** are the tree's nodes with >= 1 kept reply (the learner's decision points); **kept replies** mean / max are over them; **discard %** is the traffic-weighted share of replies at internal nodes outside the kept set (`tree-width-measurements.md`): the sum over internal nodes of games reaching the node minus games continuing along kept replies, over the sum of games reaching internal nodes; it is given for the pruned tree (the cell) and for the width-limited tree before book-pruning. Ply cap 36 throughout; no tree below hits it.

### Band 1800-2100: 150,000 games

| cell | floor (games) | nodes (root incl.) | lines (leaf paths) | max ply | largest kept-reply count | book lines covered (of 3810) | Sicilian nodes | Sicilian lines | Sicilian max ply | Sicilian book lines covered (of 401 / 391) | internal nodes | kept replies mean | kept replies max | discard % | discard % before pruning |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| top-3 | f = 0.02 % (>= 30) | 592 | 213 | 17 | 3 | 342 | 112 | 40 | 17 | 70 / 70 | 379 | 1.56 | 3 | 21.9 | 19.9 |
| top-4 | f = 0.02 % (>= 30) | 927 | 354 | 17 | 4 | 505 | 160 | 53 | 17 | 88 / 88 | 573 | 1.62 | 4 | 17.5 | 14.5 |
| top-5 | f = 0.02 % (>= 30) | 1112 | 446 | 17 | 5 | 595 | 174 | 59 | 17 | 94 / 94 | 666 | 1.67 | 5 | 15.0 | 11.4 |
| top-3 + share 5 % | f = 0.02 % (>= 30) | 996 | 389 | 17 | 7 | 535 | 163 | 56 | 17 | 88 / 88 | 607 | 1.64 | 7 | 16.1 | 12.7 |
| top-3 + share 8 % | f = 0.02 % (>= 30) | 818 | 311 | 17 | 5 | 462 | 127 | 45 | 17 | 77 / 77 | 507 | 1.61 | 5 | 18.0 | 15.1 |
| top-3 + share 10 % | f = 0.02 % (>= 30) | 740 | 278 | 17 | 5 | 413 | 125 | 45 | 17 | 76 / 76 | 462 | 1.60 | 5 | 19.4 | 16.9 |
| UNCAPPED | f = 0.02 % (>= 30) | 1491 | 650 | 17 | 18 | 801 | 190 | 71 | 17 | 109 / 108 | 841 | 1.77 | 18 | 11.4 | 7.5 |
| top-3 | f = 0.04 % (>= 60) | 369 | 148 | 13 | 3 | 260 | 65 | 28 | 13 | 53 / 53 | 221 | 1.67 | 3 | 22.1 | 20.2 |
| top-4 | f = 0.04 % (>= 60) | 566 | 237 | 13 | 4 | 375 | 82 | 35 | 13 | 62 / 62 | 329 | 1.72 | 4 | 17.7 | 15.1 |
| top-5 | f = 0.04 % (>= 60) | 683 | 299 | 13 | 5 | 449 | 85 | 37 | 13 | 65 / 65 | 384 | 1.78 | 5 | 15.1 | 12.1 |
| top-3 + share 5 % | f = 0.04 % (>= 60) | 610 | 262 | 13 | 7 | 402 | 82 | 36 | 13 | 62 / 62 | 348 | 1.75 | 7 | 16.2 | 13.4 |
| top-3 + share 8 % | f = 0.04 % (>= 60) | 508 | 210 | 13 | 5 | 344 | 68 | 30 | 13 | 54 / 54 | 298 | 1.70 | 5 | 18.1 | 15.5 |
| top-3 + share 10 % | f = 0.04 % (>= 60) | 457 | 186 | 13 | 4 | 309 | 68 | 30 | 13 | 54 / 54 | 271 | 1.68 | 4 | 19.7 | 17.3 |
| UNCAPPED | f = 0.04 % (>= 60) | 893 | 418 | 13 | 16 | 587 | 95 | 45 | 13 | 74 / 74 | 475 | 1.88 | 16 | 11.5 | 8.3 |

Size before the book-pruning step (width-limited tree at the floor, ply cap 36):

| cell | floor (games) | nodes before pruning | lines before pruning | max ply before | Sicilian nodes before | Sicilian lines before | internal nodes before | kept replies mean before | kept replies max before | discard % before |
|---|---|---|---|---|---|---|---|---|---|---|
| top-3 | f = 0.02 % (>= 30) | 1225 | 473 | 19 | 283 | 104 | 752 | 1.63 | 3 | 19.9 |
| top-4 | f = 0.02 % (>= 30) | 2131 | 864 | 19 | 419 | 156 | 1267 | 1.68 | 4 | 14.5 |
| top-5 | f = 0.02 % (>= 30) | 2813 | 1193 | 19 | 498 | 195 | 1620 | 1.74 | 5 | 11.4 |
| top-3 + share 5 % | f = 0.02 % (>= 30) | 2491 | 1057 | 19 | 495 | 195 | 1434 | 1.74 | 7 | 12.7 |
| top-3 + share 8 % | f = 0.02 % (>= 30) | 1950 | 796 | 19 | 346 | 129 | 1154 | 1.69 | 6 | 15.1 |
| top-3 + share 10 % | f = 0.02 % (>= 30) | 1647 | 656 | 19 | 338 | 124 | 991 | 1.66 | 6 | 16.9 |
| UNCAPPED | f = 0.02 % (>= 30) | 3988 | 1760 | 19 | 606 | 253 | 2228 | 1.79 | 18 | 7.5 |
| top-3 | f = 0.04 % (>= 60) | 673 | 284 | 14 | 142 | 65 | 389 | 1.73 | 3 | 20.2 |
| top-4 | f = 0.04 % (>= 60) | 1106 | 472 | 14 | 202 | 88 | 634 | 1.74 | 4 | 15.1 |
| top-5 | f = 0.04 % (>= 60) | 1426 | 622 | 14 | 238 | 107 | 804 | 1.77 | 5 | 12.1 |
| top-3 + share 5 % | f = 0.04 % (>= 60) | 1259 | 555 | 14 | 240 | 109 | 704 | 1.79 | 7 | 13.4 |
| top-3 + share 8 % | f = 0.04 % (>= 60) | 1011 | 438 | 14 | 168 | 77 | 573 | 1.76 | 6 | 15.5 |
| top-3 + share 10 % | f = 0.04 % (>= 60) | 879 | 375 | 14 | 167 | 76 | 504 | 1.74 | 6 | 17.3 |
| UNCAPPED | f = 0.04 % (>= 60) | 1945 | 867 | 14 | 280 | 130 | 1078 | 1.80 | 16 | 8.3 |

Book coverage at f = 0.02 % (>= 30 games), per width rule: of the named lines with >= floor pooled games, in the (pruned) tree; missed by width only (present in the uncapped tree at this floor, absent from this one); missed by transposition only (absent even from the uncapped tree), as in the transposition table above.

| width rule | whole book: with >= floor (pooled) | in tree | missed by width only | missed by transposition only | `1.e4 c5` rows: with >= floor (pooled) | in tree | missed by width only | missed by transposition only |
|---|---|---|---|---|---|---|---|---|
| top-3 | 996 | 342 | 459 | 195 | 133 | 70 | 40 | 23 |
| top-4 | 996 | 505 | 296 | 195 | 133 | 88 | 22 | 23 |
| top-5 | 996 | 595 | 206 | 195 | 133 | 95 | 15 | 23 |
| top-3 + share 5 % | 996 | 535 | 266 | 195 | 133 | 88 | 22 | 23 |
| top-3 + share 8 % | 996 | 462 | 339 | 195 | 133 | 77 | 33 | 23 |
| top-3 + share 10 % | 996 | 413 | 388 | 195 | 133 | 76 | 34 | 23 |
| UNCAPPED | 996 | 801 | 0 | 195 | 133 | 110 | 0 | 23 |

### Band 1500-1800: 214,825 games

| cell | floor (games) | nodes (root incl.) | lines (leaf paths) | max ply | largest kept-reply count | book lines covered (of 3810) | Sicilian nodes | Sicilian lines | Sicilian max ply | Sicilian book lines covered (of 401 / 391) | internal nodes | kept replies mean | kept replies max | discard % | discard % before pruning |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| top-3 | f = 0.02 % (>= 43) | 375 | 148 | 13 | 3 | 239 | 49 | 21 | 12 | 43 / 43 | 227 | 1.65 | 3 | 23.1 | 20.6 |
| top-4 | f = 0.02 % (>= 43) | 614 | 263 | 13 | 4 | 355 | 62 | 27 | 12 | 50 / 50 | 351 | 1.75 | 4 | 18.8 | 15.4 |
| top-5 | f = 0.02 % (>= 43) | 808 | 351 | 13 | 5 | 469 | 77 | 33 | 12 | 58 / 58 | 457 | 1.77 | 5 | 16.1 | 12.0 |
| top-3 + share 5 % | f = 0.02 % (>= 43) | 729 | 316 | 13 | 7 | 424 | 73 | 31 | 12 | 54 / 54 | 413 | 1.76 | 7 | 16.8 | 12.9 |
| top-3 + share 8 % | f = 0.02 % (>= 43) | 571 | 233 | 13 | 5 | 327 | 51 | 22 | 12 | 43 / 43 | 338 | 1.69 | 5 | 19.0 | 15.6 |
| top-3 + share 10 % | f = 0.02 % (>= 43) | 500 | 205 | 13 | 5 | 292 | 51 | 22 | 12 | 43 / 43 | 295 | 1.69 | 5 | 20.7 | 17.7 |
| UNCAPPED | f = 0.02 % (>= 43) | 1133 | 547 | 13 | 18 | 658 | 88 | 42 | 12 | 68 / 68 | 586 | 1.93 | 18 | 12.4 | 7.8 |
| top-3 | f = 0.04 % (>= 86) | 263 | 106 | 13 | 3 | 196 | 39 | 17 | 10 | 35 / 35 | 157 | 1.67 | 3 | 23.1 | 20.9 |
| top-4 | f = 0.04 % (>= 86) | 410 | 179 | 13 | 4 | 274 | 49 | 22 | 10 | 41 / 41 | 231 | 1.77 | 4 | 18.8 | 16.0 |
| top-5 | f = 0.04 % (>= 86) | 529 | 238 | 13 | 5 | 358 | 57 | 25 | 10 | 47 / 47 | 291 | 1.81 | 5 | 15.9 | 12.6 |
| top-3 + share 5 % | f = 0.04 % (>= 86) | 487 | 219 | 13 | 7 | 332 | 54 | 24 | 10 | 44 / 44 | 268 | 1.81 | 7 | 16.7 | 13.5 |
| top-3 + share 8 % | f = 0.04 % (>= 86) | 386 | 159 | 13 | 5 | 258 | 40 | 18 | 10 | 35 / 35 | 227 | 1.70 | 5 | 19.1 | 16.1 |
| top-3 + share 10 % | f = 0.04 % (>= 86) | 341 | 140 | 13 | 5 | 234 | 40 | 18 | 10 | 35 / 35 | 201 | 1.69 | 5 | 20.7 | 18.1 |
| UNCAPPED | f = 0.04 % (>= 86) | 723 | 355 | 13 | 17 | 491 | 63 | 31 | 10 | 53 / 53 | 368 | 1.96 | 17 | 12.3 | 8.7 |

Size before the book-pruning step (width-limited tree at the floor, ply cap 36):

| cell | floor (games) | nodes before pruning | lines before pruning | max ply before | Sicilian nodes before | Sicilian lines before | internal nodes before | kept replies mean before | kept replies max before | discard % before |
|---|---|---|---|---|---|---|---|---|---|---|
| top-3 | f = 0.02 % (>= 43) | 1023 | 437 | 15 | 171 | 76 | 586 | 1.74 | 3 | 20.6 |
| top-4 | f = 0.02 % (>= 43) | 1781 | 809 | 15 | 248 | 114 | 972 | 1.83 | 4 | 15.4 |
| top-5 | f = 0.02 % (>= 43) | 2442 | 1123 | 15 | 314 | 142 | 1319 | 1.85 | 5 | 12.0 |
| top-3 + share 5 % | f = 0.02 % (>= 43) | 2246 | 1030 | 15 | 324 | 147 | 1216 | 1.85 | 8 | 12.9 |
| top-3 + share 8 % | f = 0.02 % (>= 43) | 1686 | 759 | 15 | 219 | 98 | 927 | 1.82 | 6 | 15.6 |
| top-3 + share 10 % | f = 0.02 % (>= 43) | 1391 | 618 | 15 | 208 | 92 | 773 | 1.80 | 6 | 17.7 |
| UNCAPPED | f = 0.02 % (>= 43) | 3552 | 1699 | 15 | 386 | 183 | 1853 | 1.92 | 18 | 7.8 |
| top-3 | f = 0.04 % (>= 86) | 566 | 247 | 14 | 86 | 40 | 319 | 1.77 | 3 | 20.9 |
| top-4 | f = 0.04 % (>= 86) | 936 | 431 | 14 | 123 | 60 | 505 | 1.85 | 4 | 16.0 |
| top-5 | f = 0.04 % (>= 86) | 1257 | 581 | 14 | 154 | 72 | 676 | 1.86 | 5 | 12.6 |
| top-3 + share 5 % | f = 0.04 % (>= 86) | 1159 | 530 | 14 | 157 | 76 | 629 | 1.84 | 8 | 13.5 |
| top-3 + share 8 % | f = 0.04 % (>= 86) | 887 | 404 | 14 | 102 | 52 | 483 | 1.83 | 6 | 16.1 |
| top-3 + share 10 % | f = 0.04 % (>= 86) | 744 | 338 | 14 | 99 | 50 | 406 | 1.83 | 5 | 18.1 |
| UNCAPPED | f = 0.04 % (>= 86) | 1757 | 840 | 14 | 183 | 90 | 917 | 1.91 | 17 | 8.7 |

Book coverage at f = 0.02 % (>= 43 games), per width rule: of the named lines with >= floor pooled games, in the (pruned) tree; missed by width only (present in the uncapped tree at this floor, absent from this one); missed by transposition only (absent even from the uncapped tree), as in the transposition table above.

| width rule | whole book: with >= floor (pooled) | in tree | missed by width only | missed by transposition only | `1.e4 c5` rows: with >= floor (pooled) | in tree | missed by width only | missed by transposition only |
|---|---|---|---|---|---|---|---|---|
| top-3 | 793 | 239 | 419 | 135 | 85 | 43 | 25 | 17 |
| top-4 | 793 | 355 | 303 | 135 | 85 | 50 | 18 | 17 |
| top-5 | 793 | 469 | 189 | 135 | 85 | 58 | 10 | 17 |
| top-3 + share 5 % | 793 | 424 | 234 | 135 | 85 | 54 | 14 | 17 |
| top-3 + share 8 % | 793 | 327 | 331 | 135 | 85 | 43 | 25 | 17 |
| top-3 + share 10 % | 793 | 292 | 366 | 135 | 85 | 43 | 25 | 17 |
| UNCAPPED | 793 | 658 | 0 | 135 | 85 | 68 | 0 | 17 |

### Band 1800-2100: kept replies after `1.e4 c5` and after `1.e4 c5 2.Nf3`

Replies kept in the pruned tree of each cell, with their game counts in this move order; `games` is the number of games reaching the position in this move order (the share base). `-` marks a position that is not in the tree.

After `1.e4 c5` (20,806 games in this order):

| floor (games) | width rule | kept replies | kept replies (san count) |
|---|---|---|---|
| f = 0.02 % (>= 30) | top-3 | 3 | Nf3 11186, Nc3 2080, d4 1695 |
| f = 0.02 % (>= 30) | top-4 | 4 | Nf3 11186, Nc3 2080, d4 1695, c3 1648 |
| f = 0.02 % (>= 30) | top-5 | 5 | Nf3 11186, Nc3 2080, d4 1695, c3 1648, Bc4 1340 |
| f = 0.02 % (>= 30) | top-3 + share 5 % | 6 | Nf3 11186, Nc3 2080, d4 1695, c3 1648, Bc4 1340, f4 1242 |
| f = 0.02 % (>= 30) | top-3 + share 8 % | 3 | Nf3 11186, Nc3 2080, d4 1695 |
| f = 0.02 % (>= 30) | top-3 + share 10 % | 3 | Nf3 11186, Nc3 2080, d4 1695 |
| f = 0.02 % (>= 30) | UNCAPPED | 12 | Nf3 11186, Nc3 2080, d4 1695, c3 1648, Bc4 1340, f4 1242, b4 285, c4 260, a3 241, g3 129, b3 117, Ne2 93 |
| f = 0.04 % (>= 60) | top-3 | 3 | Nf3 11186, Nc3 2080, d4 1695 |
| f = 0.04 % (>= 60) | top-4 | 4 | Nf3 11186, Nc3 2080, d4 1695, c3 1648 |
| f = 0.04 % (>= 60) | top-5 | 5 | Nf3 11186, Nc3 2080, d4 1695, c3 1648, Bc4 1340 |
| f = 0.04 % (>= 60) | top-3 + share 5 % | 6 | Nf3 11186, Nc3 2080, d4 1695, c3 1648, Bc4 1340, f4 1242 |
| f = 0.04 % (>= 60) | top-3 + share 8 % | 3 | Nf3 11186, Nc3 2080, d4 1695 |
| f = 0.04 % (>= 60) | top-3 + share 10 % | 3 | Nf3 11186, Nc3 2080, d4 1695 |
| f = 0.04 % (>= 60) | UNCAPPED | 12 | Nf3 11186, Nc3 2080, d4 1695, c3 1648, Bc4 1340, f4 1242, b4 285, c4 260, a3 241, g3 129, b3 117, Ne2 93 |

After `1.e4 c5 2.Nf3` (11,186 games in this order):

| floor (games) | width rule | kept replies | kept replies (san count) |
|---|---|---|---|
| f = 0.02 % (>= 30) | top-3 | 3 | Nc6 4950, d6 3250, e6 2098 |
| f = 0.02 % (>= 30) | top-4 | 4 | Nc6 4950, d6 3250, e6 2098, g6 516 |
| f = 0.02 % (>= 30) | top-5 | 5 | Nc6 4950, d6 3250, e6 2098, g6 516, a6 230 |
| f = 0.02 % (>= 30) | top-3 + share 5 % | 3 | Nc6 4950, d6 3250, e6 2098 |
| f = 0.02 % (>= 30) | top-3 + share 8 % | 3 | Nc6 4950, d6 3250, e6 2098 |
| f = 0.02 % (>= 30) | top-3 + share 10 % | 3 | Nc6 4950, d6 3250, e6 2098 |
| f = 0.02 % (>= 30) | UNCAPPED | 6 | Nc6 4950, d6 3250, e6 2098, g6 516, a6 230, Nf6 68 |
| f = 0.04 % (>= 60) | top-3 | 3 | Nc6 4950, d6 3250, e6 2098 |
| f = 0.04 % (>= 60) | top-4 | 4 | Nc6 4950, d6 3250, e6 2098, g6 516 |
| f = 0.04 % (>= 60) | top-5 | 5 | Nc6 4950, d6 3250, e6 2098, g6 516, a6 230 |
| f = 0.04 % (>= 60) | top-3 + share 5 % | 3 | Nc6 4950, d6 3250, e6 2098 |
| f = 0.04 % (>= 60) | top-3 + share 8 % | 3 | Nc6 4950, d6 3250, e6 2098 |
| f = 0.04 % (>= 60) | top-3 + share 10 % | 3 | Nc6 4950, d6 3250, e6 2098 |
| f = 0.04 % (>= 60) | UNCAPPED | 6 | Nc6 4950, d6 3250, e6 2098, g6 516, a6 230, Nf6 68 |

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
$S/venv/bin/python refs/lichess/repertoire-rule-analysis-recent.py \
    https://database.lichess.org/standard/lichess_db_standard_rated_2026-08.pgn.zst \
    $S/chess-openings-dist.tsv docs/research/repertoire-rule-candidates-recent.md \
    --target-games 150000 --max-bytes 4294967296
```

