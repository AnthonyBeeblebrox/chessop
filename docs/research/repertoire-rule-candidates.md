# Repertoire size under candidate rules

Ticket: [`.scratch/chessop/issues/13-repertoire-named-variations.md`](../../.scratch/chessop/issues/13-repertoire-named-variations.md).
Raw material: `lichess_db_standard_rated_2013-01.pgn.zst` (17,761,302 bytes, 121332 games, CC0), downloaded and parsed locally with python-chess 1.11.2 / zstandard, then deleted. Names: `refs/lichess/chess-openings-{a..e}.tsv` (CC0) through `chess-openings-bin-gen.py` (3810 rows, 3810 distinct EPDs).
Script: [`refs/lichess/repertoire-rule-analysis.py`](../../refs/lichess/repertoire-rule-analysis.py). Generated; every number below is one run of it. No recommendation is made here.

## Method

- **Games**: the prototype's filter (`prototype/play-loop/build_tree.py`), verbatim: both `WhiteElo` and `BlackElo` present, numeric and >= 1800; `TimeControl` not bullet, where bullet means base + 40 x increment < 180 s (ultrabullet included). **5017 games** of the month's 121332; by speed: ? 26, Blitz 3985, Classical 1006. This is the prototype's 5,017-game bucket, *not* the 9,525-game `both>=1800` bucket of `tree-width-measurements.md` (which keeps bullet). The ticket's "235 positions / 86 lines" comes from the 9,525-game bucket; on the 5,017-game bucket the same rule gives the prototype's 289 / 94 (rule A below).
- **Trie**: one move-sequence trie (transpositions not merged; a node is a move sequence), mainline SAN from the shared tokenizer of `tree-width-analysis.py` (strips `?!`-style annotations, which the prototype's tokenizer keeps as part of the token; the cross-check at the end of the A section measures the effect). Built to ply 36 (the deepest line in the chess-openings TSV) so that every book position has a pooled game count; **every rule tree is capped at ply 30** (a node at ply 30 keeps no reply). 138557 trie nodes; 0 games dropped under SAN tokens python-chess rejects.
- **Node count** = games whose sequence passes through the node. **Pooled count of a position** = the sum of the node counts of every trie node with that EPD (all move orders, to ply 36).
- **EPD / names**: every node is keyed by python-chess `Board.epd()`; a node is *named* iff its EPD is one of the 3810 TSV rows (exact position, any move order). `TSV lines in tree` = distinct named EPDs in the tree (the TSV has one row per EPD, so this is a count of TSV lines).
- **top-3**: the (3,3) setting; a node keeps its 3 most popular surviving replies. Ties broken like the prototype (count desc, then SAN desc).
- **nodes** include the root (start position), as in `transpositions.md` and the prototype's 289; `leaf paths` = nodes with no kept reply = rounds / distinct lines. `max ply` counts plies (half-moves).
- **Sicilian subtree** = the sequence subtree rooted at `1.e4 c5` (node included). `Sicilian TSV lines` = the 401 TSV rows whose `uci` starts with `e2e4 c7c5`; 391 of them are named `Sicilian Defense…` (the ticket's 391; all 391 lie under `1.e4 c5`), the other 10 are the Pterodactyl/Bird/King's Gambit Declined entries that also start `1.e4 c5`. Both counts are given.
- **Rule A** (baseline): keep a node iff count >= 0.2% x 5017 = 10.034 games, i.e. **>= 11 games** (the prototype compares against the unrounded threshold; the ticket says "10 games"; a `>= 10` cell is included), top-3.
- **Rule B** (relative): keep a node iff count >= r x (parent's count) **and** count >= m, then top-3. At the root the parent count is the bucket size, so r also gates the first move.
- **Rule C** (book-terminated): top-3 tree with count >= m (ply cap 30), then prune every node with no exactly-named position at or below it (descendant-or-self, by EPD). Popularity sets the width, the book sets the depth. Every leaf of a C tree is a named position by construction. The uncapped rows keep *all* replies with >= m games before pruning.
- **Rule D** (the book itself): every TSV row's `uci` replayed; all prefix positions (named or not) counted, keyed by EPD. Positions = distinct EPDs (start position excluded); sequences = distinct move-sequence prefixes. `zero games` = pooled count 0 in this month's 5017-game bucket. `named continuations` of a position = distinct next moves out of it along book paths. For the Sicilian, positions at ply >= 2 on the paths of the 401 `1.e4 c5` rows.

## Summary: every cell

`hits ply cap` = the tree has a node at ply 30, so a deeper rule tree would have been truncated.

| rule | cell | nodes (root incl.) | leaf paths (lines) | max ply | largest kept-reply count | named nodes | named leaves | TSV lines in tree (of 3810) | Sicilian nodes | Sicilian leaf paths | Sicilian max ply | Sicilian named leaves | Sicilian TSV lines in tree (of 401 under 1.e4 c5 / 391 named Sicilian) | hits ply cap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | count >= 0.2% x 5017 = 10.034 (i.e. >= 11 games), top-3, ply cap 30 | 290 | 94 | 19 | 3 | 175 | 41 | 164 | 47 | 15 | 12 | 8 | 27 / 27 | no |
| A | same, ply cap 18 (the prototype's build) | 289 | 94 | 18 | 3 | 175 | 42 | 164 | 47 | 15 | 12 | 8 | 27 / 27 | no |
| A | count >= 10 games (the ticket's wording), top-3, ply cap 30 | 321 | 100 | 19 | 3 | 185 | 39 | 172 | 53 | 17 | 12 | 8 | 29 / 29 | no |
| A | count >= 11 games, uncapped, ply cap 30 | 511 | 175 | 19 | 11 | 278 | 74 | 258 | 71 | 26 | 12 | 9 | 34 / 34 | no |
| B | r = 0.05, floor m = 2, top-3 | 2821 | 562 | 30 | 3 | 505 | 64 | 388 | 500 | 98 | 25 | 6 | 60 / 60 | yes |
| B | r = 0.05, floor m = 5, top-3 | 727 | 194 | 23 | 3 | 296 | 59 | 253 | 124 | 36 | 16 | 11 | 45 / 45 | no |
| B | r = 0.05, floor m = 10, top-3 | 317 | 97 | 19 | 3 | 183 | 38 | 171 | 52 | 16 | 12 | 7 | 28 / 28 | no |
| B | r = 0.10, floor m = 2, top-3 | 2080 | 402 | 30 | 3 | 341 | 35 | 290 | 384 | 76 | 25 | 4 | 49 / 49 | yes |
| B | r = 0.10, floor m = 5, top-3 | 566 | 142 | 23 | 3 | 224 | 40 | 206 | 100 | 29 | 16 | 8 | 38 / 38 | no |
| B | r = 0.10, floor m = 10, top-3 | 265 | 76 | 19 | 3 | 150 | 28 | 145 | 48 | 14 | 12 | 6 | 25 / 25 | no |
| B | r = 0.20, floor m = 2, top-3 | 646 | 98 | 30 | 3 | 143 | 12 | 129 | 124 | 21 | 25 | 3 | 34 / 34 | yes |
| B | r = 0.20, floor m = 5, top-3 | 235 | 45 | 23 | 3 | 113 | 14 | 107 | 44 | 11 | 14 | 6 | 29 / 29 | no |
| B | r = 0.20, floor m = 10, top-3 | 135 | 28 | 19 | 3 | 86 | 13 | 84 | 27 | 6 | 12 | 4 | 19 / 19 | no |
| C | m = 1, top-3, pruned to named-descendant-or-self | 1679 | 387 | 28 | 3 | 937 | 387 | 601 | 208 | 48 | 24 | 48 | 107 / 107 | no |
| C | m = 2, top-3, pruned to named-descendant-or-self | 797 | 221 | 28 | 3 | 528 | 221 | 404 | 99 | 30 | 17 | 30 | 70 / 70 | no |
| C | m = 5, top-3, pruned to named-descendant-or-self | 390 | 124 | 18 | 3 | 300 | 124 | 255 | 57 | 20 | 14 | 20 | 47 / 47 | no |
| C | m = 10, top-3, pruned to named-descendant-or-self | 218 | 72 | 18 | 3 | 185 | 72 | 172 | 32 | 12 | 10 | 12 | 29 / 29 | no |
| C | m = 1, UNCAPPED, pruned to named-descendant-or-self | 3891 | 999 | 28 | 15 | 2117 | 999 | 1179 | 471 | 107 | 24 | 107 | 159 / 159 | no |
| C | m = 5, UNCAPPED, pruned to named-descendant-or-self | 676 | 243 | 18 | 12 | 528 | 243 | 426 | 81 | 31 | 14 | 31 | 62 / 62 | no |

Rule C, size before the book-pruning step (top-3 or uncapped tree with count >= m, ply cap 30):

| cell | nodes before pruning | leaf paths before pruning | max ply before | Sicilian nodes before | Sicilian leaf paths before |
|---|---|---|---|---|---|
| m = 1, top-3 | 39766 | 1927 | 30 | 7009 | 345 |
| m = 2, top-3 | 2946 | 592 | 30 | 537 | 108 |
| m = 5, top-3 | 744 | 201 | 23 | 129 | 38 |
| m = 10, top-3 | 321 | 100 | 19 | 53 | 17 |
| m = 1, uncapped | 110395 | 4988 | 30 | 17223 | 800 |
| m = 5, uncapped | 1424 | 417 | 27 | 214 | 68 |

The book (rule D) in the same terms: 7854 distinct positions (8652 move-sequence prefixes), max ply 36, 2631 of the 3810 named positions with zero games (pooled over move orders); Sicilian: 822 positions, max ply 27.

## Rule A: absolute cut-off (baseline)

- **count >= 0.2% x 5017 = 10.034 (i.e. >= 11 games), top-3, ply cap 30**: 290 nodes / 94 leaf paths / max ply 19; nodes by ply 1: 3, 2: 9, 3: 24, 4: 37, 5: 46, 6: 44, 7: 40, 8: 30, 9: 19, 10: 14, 11: 7, 12: 5, 13: 2, 14: 2, 15: 2, 16: 2, 17: 1, 18: 1, 19: 1. Sicilian: 47 nodes / 15 leaves / max ply 12.
- **same, ply cap 18 (the prototype's build)**: 289 nodes / 94 leaf paths / max ply 18; nodes by ply 1: 3, 2: 9, 3: 24, 4: 37, 5: 46, 6: 44, 7: 40, 8: 30, 9: 19, 10: 14, 11: 7, 12: 5, 13: 2, 14: 2, 15: 2, 16: 2, 17: 1, 18: 1. Sicilian: 47 nodes / 15 leaves / max ply 12.
- **count >= 10 games (the ticket's wording), top-3, ply cap 30**: 321 nodes / 100 leaf paths / max ply 19; nodes by ply 1: 3, 2: 9, 3: 24, 4: 39, 5: 48, 6: 47, 7: 49, 8: 33, 9: 22, 10: 17, 11: 9, 12: 7, 13: 3, 14: 3, 15: 2, 16: 2, 17: 1, 18: 1, 19: 1. Sicilian: 53 nodes / 17 leaves / max ply 12.
- **count >= 11 games, uncapped, ply cap 30**: 511 nodes / 175 leaf paths / max ply 19; nodes by ply 1: 9, 2: 35, 3: 66, 4: 75, 5: 87, 6: 69, 7: 56, 8: 42, 9: 25, 10: 18, 11: 9, 12: 7, 13: 3, 14: 2, 15: 2, 16: 2, 17: 1, 18: 1, 19: 1. Sicilian: 71 nodes / 26 leaves / max ply 12.

Reproduction check against the prototype (`prototype/play-loop/tree.json`: 5,017 games, 289 nodes, 94 leaf paths, max ply 18, Sicilian 47 nodes / 15 leaves / max ply 12): rerunning rule A at ply cap 18 **with the prototype's own tokenizer** (annotations kept) gives 5017 games, 289 nodes, 94 leaf paths, max ply 18, Sicilian 47 / 15 / 12. With the shared tokenizer (annotations stripped), ply cap 18: 289 nodes / 94 leaf paths (row 2 above). The difference, if any, is `?!`-annotated tokens (518 of the month's 121,332 movetext lines carry them) counted as separate moves by the prototype.

Raising the ply cap from 18 to 30 changes rule A by +1 nodes / +0 leaf paths: the nodes beyond ply 18 are ply 19, 15 games, `e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 O-O c3 d5 exd5 e4 Ng5` (unnamed).

## Rule B: relative cut-off

Nodes / leaf paths / max ply per cell, then nodes by ply.

| r \ m | m = 2 | m = 5 | m = 10 |
|---|---|---|---|
| r = 0.05 | 2821 / 562 / 30 | 727 / 194 / 23 | 317 / 97 / 19 |
| r = 0.10 | 2080 / 402 / 30 | 566 / 142 / 23 | 265 / 76 / 19 |
| r = 0.20 | 646 / 98 / 30 | 235 / 45 / 23 | 135 / 28 / 19 |

Sicilian subtree, nodes / leaf paths / max ply:

| r \ m | m = 2 | m = 5 | m = 10 |
|---|---|---|---|
| r = 0.05 | 500 / 98 / 25 | 124 / 36 / 16 | 52 / 16 / 12 |
| r = 0.10 | 384 / 76 / 25 | 100 / 29 / 16 | 48 / 14 / 12 |
| r = 0.20 | 124 / 21 / 25 | 44 / 11 / 14 | 27 / 6 / 12 |

Cells that reach ply 30 are truncated by the ply cap; their node, leaf and max-ply figures are lower bounds: r = 0.05, floor m = 2, top-3; r = 0.10, floor m = 2, top-3; r = 0.20, floor m = 2, top-3.

- **r = 0.05, floor m = 2, top-3**: nodes by ply 1: 3, 2: 9, 3: 26, 4: 65, 5: 126, 6: 186, 7: 248, 8: 289, 9: 290, 10: 278, 11: 246, 12: 211, 13: 186, 14: 144, 15: 116, 16: 87, 17: 66, 18: 52, 19: 42, 20: 41, 21: 29, 22: 23, 23: 17, 24: 11, 25: 8, 26: 6, 27: 5, 28: 5, 29: 3, 30: 2; first moves kept: e4 3048, d4 1334, Nf3 252.
- **r = 0.05, floor m = 5, top-3**: nodes by ply 1: 3, 2: 9, 3: 24, 4: 55, 5: 88, 6: 91, 7: 99, 8: 87, 9: 79, 10: 58, 11: 42, 12: 26, 13: 19, 14: 11, 15: 9, 16: 7, 17: 5, 18: 4, 19: 3, 20: 3, 21: 2, 22: 1, 23: 1; first moves kept: e4 3048, d4 1334, Nf3 252.
- **r = 0.05, floor m = 10, top-3**: nodes by ply 1: 3, 2: 9, 3: 23, 4: 36, 5: 48, 6: 47, 7: 49, 8: 33, 9: 22, 10: 17, 11: 9, 12: 7, 13: 3, 14: 3, 15: 2, 16: 2, 17: 1, 18: 1, 19: 1; first moves kept: e4 3048, d4 1334, Nf3 252.
- **r = 0.10, floor m = 2, top-3**: nodes by ply 1: 2, 2: 5, 3: 10, 4: 23, 5: 59, 6: 93, 7: 142, 8: 195, 9: 217, 10: 221, 11: 202, 12: 177, 13: 159, 14: 122, 15: 99, 16: 75, 17: 57, 18: 44, 19: 36, 20: 35, 21: 27, 22: 22, 23: 17, 24: 11, 25: 8, 26: 6, 27: 5, 28: 5, 29: 3, 30: 2; first moves kept: e4 3048, d4 1334.
- **r = 0.10, floor m = 5, top-3**: nodes by ply 1: 2, 2: 5, 3: 10, 4: 23, 5: 50, 6: 64, 7: 80, 8: 76, 9: 72, 10: 55, 11: 40, 12: 25, 13: 18, 14: 10, 15: 9, 16: 7, 17: 5, 18: 4, 19: 3, 20: 3, 21: 2, 22: 1, 23: 1; first moves kept: e4 3048, d4 1334.
- **r = 0.10, floor m = 10, top-3**: nodes by ply 1: 2, 2: 5, 3: 10, 4: 23, 5: 36, 6: 41, 7: 46, 8: 33, 9: 22, 10: 17, 11: 9, 12: 7, 13: 3, 14: 3, 15: 2, 16: 2, 17: 1, 18: 1, 19: 1; first moves kept: e4 3048, d4 1334.
- **r = 0.20, floor m = 2, top-3**: nodes by ply 1: 2, 2: 4, 3: 5, 4: 8, 5: 11, 6: 18, 7: 25, 8: 41, 9: 47, 10: 51, 11: 55, 12: 59, 13: 55, 14: 46, 15: 39, 16: 33, 17: 25, 18: 20, 19: 17, 20: 18, 21: 15, 22: 12, 23: 10, 24: 7, 25: 6, 26: 4, 27: 4, 28: 4, 29: 2, 30: 2; first moves kept: e4 3048, d4 1334.
- **r = 0.20, floor m = 5, top-3**: nodes by ply 1: 2, 2: 4, 3: 5, 4: 8, 5: 11, 6: 15, 7: 23, 8: 28, 9: 29, 10: 28, 11: 23, 12: 15, 13: 12, 14: 7, 15: 6, 16: 4, 17: 3, 18: 3, 19: 2, 20: 2, 21: 2, 22: 1, 23: 1; first moves kept: e4 3048, d4 1334.
- **r = 0.20, floor m = 10, top-3**: nodes by ply 1: 2, 2: 4, 3: 5, 4: 8, 5: 11, 6: 13, 7: 18, 8: 18, 9: 14, 10: 14, 11: 7, 12: 7, 13: 3, 14: 3, 15: 2, 16: 2, 17: 1, 18: 1, 19: 1; first moves kept: e4 3048, d4 1334.

## Rule C: book-terminated

- **m = 1, top-3, pruned to named-descendant-or-self**: 1679 nodes / 387 leaf paths / max ply 28 (largest kept-reply count 3); nodes by ply 1: 3, 2: 9, 3: 26, 4: 59, 5: 106, 6: 143, 7: 174, 8: 193, 9: 189, 10: 164, 11: 130, 12: 113, 13: 93, 14: 73, 15: 53, 16: 40, 17: 35, 18: 21, 19: 15, 20: 10, 21: 8, 22: 8, 23: 4, 24: 4, 25: 2, 26: 1, 27: 1, 28: 1. Sicilian: 208 nodes / 48 leaves / max ply 24, 107 of the 401 `1.e4 c5` TSV lines (107 of the 391 `Sicilian Defense` ones) present.
- **m = 2, top-3, pruned to named-descendant-or-self**: 797 nodes / 221 leaf paths / max ply 28 (largest kept-reply count 3); nodes by ply 1: 3, 2: 9, 3: 25, 4: 52, 5: 83, 6: 90, 7: 102, 8: 101, 9: 90, 10: 64, 11: 49, 12: 36, 13: 23, 14: 15, 15: 13, 16: 9, 17: 6, 18: 6, 19: 5, 20: 5, 21: 2, 22: 2, 23: 1, 24: 1, 25: 1, 26: 1, 27: 1, 28: 1. Sicilian: 99 nodes / 30 leaves / max ply 17, 70 of the 401 `1.e4 c5` TSV lines (70 of the 391 `Sicilian Defense` ones) present.
- **m = 5, top-3, pruned to named-descendant-or-self**: 390 nodes / 124 leaf paths / max ply 18 (largest kept-reply count 3); nodes by ply 1: 3, 2: 9, 3: 24, 4: 42, 5: 56, 6: 55, 7: 55, 8: 43, 9: 30, 10: 24, 11: 20, 12: 8, 13: 6, 14: 4, 15: 3, 16: 3, 17: 3, 18: 1. Sicilian: 57 nodes / 20 leaves / max ply 14, 47 of the 401 `1.e4 c5` TSV lines (47 of the 391 `Sicilian Defense` ones) present.
- **m = 10, top-3, pruned to named-descendant-or-self**: 218 nodes / 72 leaf paths / max ply 18 (largest kept-reply count 3); nodes by ply 1: 3, 2: 9, 3: 22, 4: 28, 5: 34, 6: 31, 7: 30, 8: 18, 9: 13, 10: 10, 11: 6, 12: 3, 13: 2, 14: 2, 15: 2, 16: 2, 17: 1, 18: 1. Sicilian: 32 nodes / 12 leaves / max ply 10, 29 of the 401 `1.e4 c5` TSV lines (29 of the 391 `Sicilian Defense` ones) present.
- **m = 1, UNCAPPED, pruned to named-descendant-or-self**: 3891 nodes / 999 leaf paths / max ply 28 (largest kept-reply count 15); nodes by ply 1: 15, 2: 74, 3: 167, 4: 284, 5: 389, 6: 441, 7: 450, 8: 433, 9: 382, 10: 320, 11: 244, 12: 194, 13: 142, 14: 105, 15: 73, 16: 52, 17: 44, 18: 24, 19: 16, 20: 11, 21: 9, 22: 8, 23: 4, 24: 4, 25: 2, 26: 1, 27: 1, 28: 1. Sicilian: 471 nodes / 107 leaves / max ply 24, 159 of the 401 `1.e4 c5` TSV lines (159 of the 391 `Sicilian Defense` ones) present.
- **m = 5, UNCAPPED, pruned to named-descendant-or-self**: 676 nodes / 243 leaf paths / max ply 18 (largest kept-reply count 12); nodes by ply 1: 10, 2: 46, 3: 71, 4: 90, 5: 97, 6: 90, 7: 86, 8: 61, 9: 37, 10: 30, 11: 25, 12: 10, 13: 7, 14: 5, 15: 3, 16: 3, 17: 3, 18: 1. Sicilian: 81 nodes / 31 leaves / max ply 14, 62 of the 401 `1.e4 c5` TSV lines (62 of the 391 `Sicilian Defense` ones) present.

Every leaf of a C tree is a named position (a leaf with no named descendant-or-self would have been pruned), so `named leaves` = `leaf paths` there; a line runs exactly as deep as the deepest named position the kept replies reach.

Coverage of the book by rule C: named TSV lines in the tree against the named lines that have >= m games at all (by the TSV's own move order, and pooled over every move order into the position). The gap is what the top-3 cap and the sequence keying leave out.

| cell | TSV lines in tree / with >= m games (own order) / (pooled) | Sicilian (401 under 1.e4 c5): in tree / >= m (own order) / (pooled) |
|---|---|---|
| m = 1, top-3, pruned to named-descendant-or-self | 601 / 890 / 1179 | 107 / 125 / 162 |
| m = 2, top-3, pruned to named-descendant-or-self | 404 / 614 / 834 | 70 / 82 / 106 |
| m = 5, top-3, pruned to named-descendant-or-self | 255 / 382 / 496 | 47 / 56 / 71 |
| m = 10, top-3, pruned to named-descendant-or-self | 172 / 253 / 326 | 29 / 36 / 42 |
| m = 1, UNCAPPED, pruned to named-descendant-or-self | 1179 / 890 / 1179 | 159 / 125 / 162 |
| m = 5, UNCAPPED, pruned to named-descendant-or-self | 426 / 382 / 496 | 62 / 56 / 71 |

## Rule D: the book itself

### Whole book

- 3810 TSV lines; **7854 distinct positions** on their paths (8652 distinct move-sequence prefixes, so 798 positions are reached by more than one book move order), of which 4044 are unnamed intermediate positions and 3810 named. Max ply 36. Positions by ply: 1: 20, 2: 134, 3: 272, 4: 399, 5: 529, 6: 615, 7: 612, 8: 625, 9: 640, 10: 619, 11: 558, 12: 522, 13: 446, 14: 402, 15: 311, 16: 253, 17: 224, 18: 175, 19: 133, 20: 103, 21: 72, 22: 52, 23: 38, 24: 33, 25: 26, 26: 18, 27: 10, 28: 4, 29: 2, 30: 1, 31: 1, 32: 1, 33: 1, 34: 1, 35: 1, 36: 1.
- **Zero games at 1800+ in the month** (pooled over move orders): 5510 of 7854 positions (2879 of the unnamed intermediates, 2631 of the 3810 named lines). By the TSV's own move order (sequence count): 2920 named lines with zero games.
- Named lines reached by >= 1 / 2 / 5 / 10 / 11 games (pooled): 1179 / 834 / 496 / 326 / 299; by own move order: 890 / 614 / 382 / 253 / 238.
- Named continuations per position (distinct next book moves): 0: 2377, 1: 4216, 2: 710, 3: 270, 4: 131, 5: 60, 6: 28, 7: 19, 8: 10, 9: 9, 10: 12, 11: 2, 12: 1, 13: 2, 14: 1, 17: 1, 18: 1, 19: 3, 20: 1.
- Widest positions:

| ply | named continuations | position | games (pooled) |
|---|---|---|---|
| 2 | 20 | Sicilian Defense | 805 |
| 1 | 19 | Zukertort Opening | 252 |
| 1 | 19 | King's Pawn Game | 3048 |
| 2 | 19 | King's Pawn Game | 765 |
| 5 | 18 | Ruy Lopez | 201 |
| 4 | 17 | King's Gambit Accepted | 28 |
| 1 | 14 | Queen's Pawn Game | 1334 |
| 2 | 13 | Indian Defense | 409 |

### Sicilian (`1.e4 c5` rows, positions at ply >= 2)

- 401 TSV lines; **822 distinct positions** on their paths (884 distinct move-sequence prefixes, so 62 positions are reached by more than one book move order), of which 421 are unnamed intermediate positions and 401 named. Max ply 27. Positions by ply: 2: 1, 3: 20, 4: 27, 5: 55, 6: 57, 7: 44, 8: 51, 9: 53, 10: 60, 11: 75, 12: 68, 13: 62, 14: 56, 15: 45, 16: 35, 17: 30, 18: 26, 19: 17, 20: 15, 21: 7, 22: 5, 23: 5, 24: 3, 25: 2, 26: 2, 27: 1.
- **Zero games at 1800+ in the month** (pooled over move orders): 484 of 822 positions (245 of the unnamed intermediates, 239 of the 401 named lines). By the TSV's own move order (sequence count): 276 named lines with zero games.
- Named lines reached by >= 1 / 2 / 5 / 10 / 11 games (pooled): 162 / 106 / 71 / 42 / 38; by own move order: 125 / 82 / 56 / 36 / 33.
- Named continuations per position (distinct next book moves): 0: 252, 1: 439, 2: 76, 3: 28, 4: 12, 5: 6, 6: 4, 7: 1, 9: 1, 10: 1, 13: 1, 20: 1.
- Widest positions:

| ply | named continuations | position | games (pooled) |
|---|---|---|---|
| 2 | 20 | Sicilian Defense | 805 |
| 3 | 13 | Sicilian Defense | 487 |
| 10 | 10 | Sicilian Defense: Najdorf Variation | 42 |
| 4 | 9 | Sicilian Defense: O'Kelly Variation | 1 |
| 7 | 7 | Sicilian Defense: Open | 128 |
| 4 | 6 | Sicilian Defense: French Variation | 40 |
| 4 | 6 | Sicilian Defense: Modern Variations | 161 |
| 5 | 6 | Sicilian Defense: Smith-Morra Gambit | 17 |

After `1.e4 c5` specifically: 20 named continuations (distinct third-move book moves), 805 games reach the position.

The ticket's 391 `Sicilian Defense` rows alone: zero games for 229 (pooled) / 266 (own move order); reached by >= 1 / 2 / 5 / 10 / 11 games: 162 / 106 / 71 / 42 / 38 (pooled), 125 / 82 / 56 / 36 / 33 (own move order).

Against the ticket's facts (2,922 of 3,810 named lines with no game, 888 with >= 1, 253 with >= 10; Sicilian 266 of 391 with none, 125 with >= 1, 36 with >= 10): the own-move-order counts here give 2920 / 890 / 253 and 266 / 125 / 36. The 253, 36, 266 and 125 match; the whole-book zero / >= 1 split differs by 2 lines, and the ticket does not record how its count was made (a ply-18 trie is not the cause: 11 named lines deeper than ply 18 have >= 1 game in their own order). The pooled counts are higher throughout because a named position is often reached by a move order other than the TSV's.

## Rule E: rule C at m = 5, top-3, the Sicilian in detail

### Sicilian leaf lines (20)

Every leaf is an exactly-named position. Sorted by move sequence.

| ply | ECO | name | games (this order) | line |
|---|---|---|---|---|
| 5 | B23 | Sicilian Defense: Grand Prix Attack | 6 | `e4 c5 Nc3 Nc6 f4` |
| 5 | B24 | Sicilian Defense: Closed, Fianchetto Variation | 17 | `e4 c5 Nc3 Nc6 g3` |
| 5 | B23 | Sicilian Defense: Closed | 6 | `e4 c5 Nc3 e6 g3` |
| 6 | B31 | Sicilian Defense: Nyezhmetdinov-Rossolimo Attack, Fianchetto Variation | 12 | `e4 c5 Nf3 Nc6 Bb5 g6` |
| 11 | B58 | Sicilian Defense: Classical Variation | 6 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 Nf6 Nc3 d6 Be2` |
| 10 | B33 | Sicilian Defense: Lasker-Pelikan Variation | 6 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 Nf6 Nc3 e5` |
| 10 | B45 | Sicilian Defense: Four Knights Variation | 8 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 Nf6 Nc3 e6` |
| 11 | B33 | Sicilian Defense: Lasker-Pelikan Variation, Schlechter Variation | 7 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 e5 Nb3 Nf6 Nc3` |
| 13 | B35 | Sicilian Defense: Accelerated Dragon, Modern Bc4 Variation | 5 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 g6 Nc3 Bg7 Be3 Nf6 Bc4` |
| 9 | B34 | Sicilian Defense: Accelerated Dragon, Exchange Variation | 7 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 g6 Nxc6` |
| 11 | B38 | Sicilian Defense: Accelerated Dragon, Maróczy Bind | 7 | `e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 g6 c4 Bg7 Be3` |
| 6 | B52 | Sicilian Defense: Moscow Variation, Main Line | 13 | `e4 c5 Nf3 d6 Bb5+ Bd7` |
| 5 | B50 | Sicilian Defense: Delayed Alapin Variation, with d6 | 23 | `e4 c5 Nf3 d6 c3` |
| 11 | B92 | Sicilian Defense: Najdorf Variation, Opocensky Variation | 9 | `e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 Be2` |
| 11 | B90 | Sicilian Defense: Najdorf Variation, English Attack | 6 | `e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 Be3` |
| 11 | B94 | Sicilian Defense: Najdorf Variation | 7 | `e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 Bg5` |
| 14 | B76 | Sicilian Defense: Dragon Variation, Yugoslav Attack | 5 | `e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 g6 Be3 Bg7 f3 O-O` |
| 7 | B53 | Sicilian Defense: Chekhover Variation | 6 | `e4 c5 Nf3 d6 d4 cxd4 Qxd4` |
| 6 | B40 | Sicilian Defense: French Variation, Open | 8 | `e4 c5 Nf3 e6 d4 cxd4` |
| 3 | B20 | Sicilian Defense: Wing Gambit | 83 | `e4 c5 b4` |

### Named `1.e4 c5` TSV lines with >= 5 games (pooled) that rule C m = 5 top-3 misses (24)

`games (pooled)` counts every move order into the position; `games (own order)` counts games following the TSV's own `pgn`. `why` walks the TSV's move order through the trie and names the first move that is not in the rule-C tree: its games in that order and its rank among the parent's replies with >= 5 games (the kept top-3 are listed).

| name | ECO | ply | games (pooled) | games (own order) | why | line |
|---|---|---|---|---|---|---|
| Sicilian Defense: Alapin Variation | B22 | 3 | 47 | 47 | ply 3: c3 has 47 games, rank 4 of 11 (outside top-3; kept: Nf3 486, b4 83, Nc3 72) | `1. e4 c5 2. c3` |
| Sicilian Defense: McDonnell Attack | B21 | 3 | 32 | 32 | ply 3: f4 has 32 games, rank 5 of 11 (outside top-3; kept: Nf3 486, b4 83, Nc3 72) | `1. e4 c5 2. f4` |
| Sicilian Defense: Bowdler Attack | B20 | 3 | 26 | 26 | ply 3: Bc4 has 26 games, rank 6 of 11 (outside top-3; kept: Nf3 486, b4 83, Nc3 72) | `1. e4 c5 2. Bc4` |
| Sicilian Defense: Smith-Morra Gambit | B21 | 3 | 23 | 22 | ply 3: d4 has 22 games, rank 7 of 11 (outside top-3; kept: Nf3 486, b4 83, Nc3 72) | `1. e4 c5 2. d4` |
| Sicilian Defense: Hyperaccelerated Dragon | B27 | 4 | 19 | 19 | ply 4: g6 has 19 games, rank 4 of 4 (outside top-3; kept: Nc6 281, d6 159, e6 23) | `1. e4 c5 2. Nf3 g6` |
| Sicilian Defense: Smith-Morra Gambit | B21 | 5 | 17 | 17 | ply 3: d4 has 22 games, rank 7 of 11 (outside top-3; kept: Nf3 486, b4 83, Nc3 72) | `1. e4 c5 2. d4 cxd4 3. c3` |
| Sicilian Defense: Hyperaccelerated Dragon | B27 | 5 | 13 | 13 | ply 4: g6 has 19 games, rank 4 of 4 (outside top-3; kept: Nc6 281, d6 159, e6 23) | `1. e4 c5 2. Nf3 g6 3. d4` |
| Sicilian Defense: Taimanov Variation | B44 | 8 | 12 | 3 | ply 7: Nxd4 (8 games, rank 1) pruned, nothing named with >= 5 games below it in this order; next book move Nc6 has 3 games in this order (< 5) | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6` |
| Sicilian Defense: Taimanov Variation | B45 | 9 | 11 | 3 | ply 7: Nxd4 (8 games, rank 1) pruned, nothing named with >= 5 games below it in this order; next book move Nc6 has 3 games in this order (< 5) | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nc6 5. Nc3` |
| Sicilian Defense: Smith-Morra Gambit Accepted | B21 | 6 | 10 | 10 | ply 3: d4 has 22 games, rank 7 of 11 (outside top-3; kept: Nf3 486, b4 83, Nc3 72) | `1. e4 c5 2. d4 cxd4 3. c3 dxc3` |
| Sicilian Defense: Scheveningen Variation | B80 | 10 | 8 | 0 | ply 7: Nxd4 (8 games, rank 1) pruned, nothing named with >= 5 games below it in this order; next book move Nf6 has 1 games in this order (< 5) | `1. e4 c5 2. Nf3 e6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 d6` |
| Sicilian Defense: Alapin Variation, Barmen Defense, Central Exchange | B22 | 12 | 8 | 0 | ply 3: c3 has 47 games, rank 4 of 11 (outside top-3; kept: Nf3 486, b4 83, Nc3 72) | `1. e4 c5 2. c3 d5 3. exd5 Qxd5 4. d4 cxd4 5. cxd4 Nc6 6. Nf3 Bg4` |
| Sicilian Defense: Keres Variation | B20 | 3 | 7 | 7 | ply 3: Ne2 has 7 games, rank 10 of 11 (outside top-3; kept: Nf3 486, b4 83, Nc3 72) | `1. e4 c5 2. Ne2` |
| Sicilian Defense: Lasker-Dunne Attack | B20 | 3 | 7 | 7 | ply 3: g3 has 7 games, rank 9 of 11 (outside top-3; kept: Nf3 486, b4 83, Nc3 72) | `1. e4 c5 2. g3` |
| Sicilian Defense: Kramnik Variation | B40 | 5 | 7 | 3 | ply 5: c4 has 3 games in this order (< 5) | `1. e4 c5 2. Nf3 e6 3. c4` |
| Sicilian Defense: Najdorf Variation, Lipnitsky Attack | B90 | 11 | 7 | 6 | ply 11: Bc4 has 6 games, rank 4 of 4 (outside top-3; kept: Be2 9, Bg5 7, Be3 6) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Bc4` |
| Sicilian Defense: Najdorf Variation | B95 | 12 | 7 | 4 | ply 12: e6 has 4 games in this order (< 5) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Bg5 e6` |
| Sicilian Defense: Dragon Variation, Yugoslav Attack, Main Line | B77 | 17 | 6 | 2 | ply 15: Qd2 has 3 games in this order (< 5) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6 6. Be3 Bg7 7. f3 O-O 8. Qd2 Nc6 9. Bc4` |
| Sicilian Defense: Staunton-Cochrane Variation | B20 | 3 | 5 | 5 | ply 3: c4 has 5 games, rank 11 of 11 (outside top-3; kept: Nf3 486, b4 83, Nc3 72) | `1. e4 c5 2. c4` |
| Sicilian Defense: Smith-Morra Gambit Declined, Push Variation | B21 | 6 | 5 | 5 | ply 3: d4 has 22 games, rank 7 of 11 (outside top-3; kept: Nf3 486, b4 83, Nc3 72) | `1. e4 c5 2. d4 cxd4 3. c3 d3` |
| Sicilian Defense: Closed, Anti-Sveshnikov Variation | B30 | 6 | 5 | 4 | ply 5: Nc3 has 28 games, rank 5 of 6 (outside top-3; kept: d4 130, Bc4 44, Bb5 35) | `1. e4 c5 2. Nf3 Nc6 3. Nc3 e5` |
| Sicilian Defense: Smith-Morra Gambit Accepted, Fianchetto Defense | B21 | 10 | 5 | 3 | ply 3: d4 has 22 games, rank 7 of 11 (outside top-3; kept: Nf3 486, b4 83, Nc3 72) | `1. e4 c5 2. d4 cxd4 3. c3 dxc3 4. Nxc3 Nc6 5. Nf3 g6` |
| Sicilian Defense: Najdorf Variation, Yates Variation | B90 | 11 | 5 | 4 | ply 11: Bd3 has 4 games in this order (< 5) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Bd3` |
| Sicilian Defense: Najdorf Variation | B96 | 13 | 5 | 3 | ply 12: e6 has 4 games in this order (< 5) | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Bg5 e6 7. f4` |

Reasons: a move on the way ranks outside the top-3: 16; a move on the way has < 5 games in the TSV's move order (the position's traffic comes by transposition): 8.

## Reproduction

The dump is CC0 and was deleted after the run.

```sh
cd /home/anthony/pproj/chessop
S=/tmp/chessop-scratch && mkdir -p $S

# 1. dependencies (python-chess 1.11.2, zstandard 0.25.0)
uv venv $S/venv
uv pip install --python $S/venv/bin/python chess==1.11.2 zstandard==0.25.0

# 2. the 2013-01 standard rated dump: 17,761,302 bytes,
#    sha256 aa40b3671fa3cf1072eb182892cd90b0e1e003a4a5943492f64b77e7f3fd1635
curl -sSL -o $S/lichess_db_standard_rated_2013-01.pgn.zst \
    https://database.lichess.org/standard/lichess_db_standard_rated_2013-01.pgn.zst
sha256sum $S/lichess_db_standard_rated_2013-01.pgn.zst

# 3. the chess-openings dist columns (uci, epd): 3811 lines, exit 0
$S/venv/bin/python refs/lichess/chess-openings-bin-gen.py \
    refs/lichess/chess-openings-a.tsv refs/lichess/chess-openings-b.tsv \
    refs/lichess/chess-openings-c.tsv refs/lichess/chess-openings-d.tsv \
    refs/lichess/chess-openings-e.tsv > $S/chess-openings-dist.tsv

# 4. the measurement; regenerates this file
$S/venv/bin/python refs/lichess/repertoire-rule-analysis.py \
    $S/lichess_db_standard_rated_2013-01.pgn.zst \
    $S/chess-openings-dist.tsv docs/research/repertoire-rule-candidates.md

# 5. do not keep the dump
rm $S/lichess_db_standard_rated_2013-01.pgn.zst
```

