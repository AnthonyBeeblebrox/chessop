# How a reply-width cap trades against popularity coverage

Ticket: [.scratch/chessop/issues/](../../.scratch/chessop/issues/) (measurement requested by the parent session).
Raw material: `lichess_db_standard_rated_2013-01.pgn.zst` (17,761,302 bytes, 121,332 games), downloaded and parsed locally with python-chess 1.11.2 / zstandard, then deleted (CC0).
Script: [`refs/lichess/tree-width-analysis.py`](../../refs/lichess/tree-width-analysis.py).

## Method

- Streamed the `.pgn.zst` (never fully in memory), kept the mainline SAN of each game to ply 21, built one trie per bucket. **Transpositions are not merged**: a node is a move *sequence*, matching the earlier `dump-2013-01-tree-stats.txt` measurement.
- Buckets, by both players' Elo: `all` = 121332 games, `both>=1800` = 9525 games, `both<1500` = 19771 games.
- `games reaching a node` = number of games in the bucket whose move sequence passes through it (the node's count).
- **Cut-off**: a node/edge survives if its count is >= X% of the bucket's games. Surviving edges are exactly the sampled candidate replies; because a parent's count is never below a child's, no reachability repair is needed.
- **Width cap W**: on top of the cut-off, a position keeps only its W most popular surviving replies; the sampling weights are renormalised over those W. Two variants are reported: `cap every node` (the learner's own moves are capped too, which is what bounds the repertoire size) and `cap opponent (Black) only` (the literal drill: learner has White, only Black's replies are sampled).
- `reply mass discarded, % of decision-point mass` is the traffic-weighted average over every position where the cap applies: sum over positions of (surviving reply mass - mass kept by the cap) divided by the surviving reply mass at those positions. Mass already removed by the popularity cut-off is not counted as width-cap loss, and for `cap opponent only` the denominator only covers the plies where Black is to move. `discarded game-replies` is the numerator in absolute terms; a game contributes once per position along its path where its reply falls outside the cap, so the total can exceed the number of games.
- `distinct paths at ply p` = number of nodes at ply p in the capped tree = number of distinct repertoire lines of that length. `all leaf paths` = paths that dead-end (no surviving reply) plus the ply-18 frontier; that is the total size of the drilled repertoire. No cut-off tree below reaches ply 20, so the `paths at ply 20` column is 0 throughout and the termination column carries the real number.
- Nodes at the termination ply have 0 surviving replies by definition, so the last row of each per-ply table is an artefact of the tree ending, not a real position.
- The trie is built to ply 21, so a bucket whose cut-off tree still has nodes at ply 21 would be truncated; none of the trees below is (max depth 18).

Tokenizer self-check (500 games, plain tokenizer vs `chess.pgn.read_game`): 499 identical move lists; the one difference is a move the dump writes fully disambiguated (`Nb4c6`) and python-chess re-renders minimally (`N4c6`) - same ply, spelling only. Command at the end.

## Headline: top-3 cumulative share for both players >= 1800

The opponent's reply at ply p (the p/2-th Black move), aggregated over every parent position at ply p-1 in the cut-off tree and weighted by the games reaching it. The top-k shares use those games as denominator (what the task asked for); `top-3, % of surviving reply mass` uses only the reply mass the cut-off itself kept, which is the denominator the width-cap tables below use, so the two numbers differ slightly.

### cut-off >= 1.0% of games (>= 95 games)
| opponent move at ply | parent positions | games reaching them | replies mean | replies max | top-1 % | top-2 % | top-3 % | top-4 % | top-5 % | top-3, % of surviving reply mass | top-5, % of surviving reply mass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 6 | 9276 | 3.17 | 10 | 29.24 | 48.23 | 62.70 | 69.40 | 74.91 | 71.28 | 85.17 |
| 4 | 19 | 5642 | 0.89 | 3 | 54.50 | 65.77 | 68.72 | 68.72 | 68.72 | 100.00 | 100.00 |
| 6 | 15 | 2193 | 0.60 | 2 | 47.83 | 52.21 | 52.21 | 52.21 | 52.21 | 100.00 | 100.00 |
| 8 | 3 | 421 | 0.33 | 1 | 23.28 | 23.28 | 23.28 | 23.28 | 23.28 | 100.00 | 100.00 |

Same top-3 numbers expressed as a share of **all** 9525 games in the bucket (they differ by the share of games that even reach the position in this cut-off tree):
| opponent move at ply | games reaching % | top-3 % of all games |
|---|---|---|
| 2 | 97.39 | 61.06 |
| 4 | 59.23 | 40.70 |
| 6 | 23.02 | 12.02 |
| 8 | 4.42 | 1.03 |

### cut-off >= 0.2% of games (>= 19 games)
| opponent move at ply | parent positions | games reaching them | replies mean | replies max | top-1 % | top-2 % | top-3 % | top-4 % | top-5 % | top-3, % of surviving reply mass | top-5, % of surviving reply mass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 10 | 9487 | 3.70 | 11 | 29.28 | 49.96 | 65.45 | 73.01 | 79.14 | 68.68 | 83.05 |
| 4 | 67 | 7938 | 1.16 | 5 | 59.15 | 72.71 | 78.28 | 80.51 | 81.37 | 96.21 | 100.00 |
| 6 | 78 | 4725 | 0.91 | 4 | 60.02 | 69.31 | 70.84 | 71.26 | 71.26 | 99.41 | 100.00 |
| 8 | 47 | 1870 | 0.64 | 3 | 47.43 | 53.32 | 55.51 | 55.51 | 55.51 | 100.00 | 100.00 |

Same top-3 numbers expressed as a share of **all** 9525 games in the bucket (they differ by the share of games that even reach the position in this cut-off tree):
| opponent move at ply | games reaching % | top-3 % of all games |
|---|---|---|
| 2 | 99.60 | 65.19 |
| 4 | 83.34 | 65.24 |
| 6 | 49.61 | 35.14 |
| 8 | 19.63 | 10.90 |

## Per-bucket detail

### Bucket: all (121332 games)

#### cut-off >= 1.0% of games (>= 1213 games)

Tree: 60 nodes, maximum ply 6, nodes by ply [7, 17, 16, 13, 6, 1].

Top-1..5 cumulative reply mass **as a share of all games in the bucket** (sum of the top-k reply counts / 121332):

| ply | positions | games reaching | replies mean | replies max | top-1 | top-2 | top-3 | top-4 | top-5 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 7 | 117058 | 2.43 | 10 | 41.04 | 53.60 | 63.07 | 69.15 | 72.90 |
| 2 | 17 | 98743 | 0.94 | 5 | 32.68 | 41.21 | 45.15 | 48.15 | 49.42 |
| 3 | 16 | 59968 | 0.81 | 3 | 20.95 | 26.91 | 28.13 | 28.13 | 28.13 |
| 4 | 13 | 34132 | 0.46 | 3 | 6.44 | 10.35 | 11.81 | 11.81 | 11.81 |
| 5 | 6 | 14327 | 0.17 | 1 | 1.06 | 1.06 | 1.06 | 1.06 | 1.06 |
| 6 | 1 | 1285 | 0.00 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Top-1..5 cumulative reply mass **as a share of the games reaching the node** (traffic-weighted), plus the mean per-node top-3 share:

| ply | top-1 | top-2 | top-3 | top-4 | top-5 | mean top-3 (per node) |
|---|---|---|---|---|---|---|
| 1 | 42.54 | 55.56 | 65.37 | 71.68 | 75.56 | 31.3 |
| 2 | 40.15 | 50.64 | 55.48 | 59.16 | 60.73 | 25.0 |
| 3 | 42.39 | 54.46 | 56.92 | 56.92 | 56.92 | 35.2 |
| 4 | 22.91 | 36.79 | 41.98 | 41.98 | 41.98 | 17.6 |
| 5 | 8.97 | 8.97 | 8.97 | 8.97 | 8.97 | 12.1 |
| 6 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.0 |

Width caps on top of this cut-off:

| cap applied to | width W | reply mass discarded, % of decision-point mass | worst ply (discard there, % of its reply mass) | discarded game-replies (summed over positions) | nodes in capped tree | paths at ply 20 | paths at ply 6 (termination) | all leaf paths |
|---|---|---|---|---|---|---|---|---|
| cap every node | 3 | 11.83 | ply 1: 22.5% | 38500 | 40 | 0 | 1 | 20 |
| cap every node | 4 | 7.26 | ply 1: 15.0% | 23618 | 50 | 0 | 1 | 25 |
| cap every node | 5 | 4.44 | ply 1: 10.4% | 14451 | 54 | 0 | 1 | 29 |
| cap opponent (Black) only | 3 | 16.56 | ply 1: 22.5% | 22217 | 49 | 0 | 1 | 27 |
| cap opponent (Black) only | 4 | 11.06 | ply 1: 15.0% | 14836 | 54 | 0 | 1 | 29 |
| cap opponent (Black) only | 5 | 7.68 | ply 1: 10.4% | 10297 | 56 | 0 | 1 | 31 |
| no cap (cut-off only) | - | 0.00 | ply 0: 0.0% | 0 | 61 | 0 | 1 | 36 |

#### cut-off >= 0.2% of games (>= 243 games)

Tree: 321 nodes, maximum ply 10, nodes by ply [12, 46, 75, 67, 60, 34, 17, 6, 3, 1].

Top-1..5 cumulative reply mass **as a share of all games in the bucket** (sum of the top-k reply counts / 121332):

| ply | positions | games reaching | replies mean | replies max | top-1 | top-2 | top-3 | top-4 | top-5 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 12 | 120587 | 3.83 | 11 | 42.91 | 57.61 | 68.52 | 75.85 | 80.61 |
| 2 | 46 | 113114 | 1.63 | 9 | 42.47 | 56.44 | 63.15 | 67.72 | 70.39 |
| 3 | 75 | 90706 | 0.89 | 7 | 33.43 | 43.64 | 47.73 | 49.13 | 49.41 |
| 4 | 67 | 60595 | 0.90 | 5 | 19.26 | 26.56 | 30.08 | 31.39 | 31.68 |
| 5 | 60 | 38436 | 0.57 | 5 | 10.66 | 12.99 | 14.33 | 15.26 | 15.50 |
| 6 | 34 | 18801 | 0.50 | 2 | 5.50 | 6.26 | 6.26 | 6.26 | 6.26 |
| 7 | 17 | 7591 | 0.35 | 1 | 1.66 | 1.66 | 1.66 | 1.66 | 1.66 |
| 8 | 6 | 2019 | 0.50 | 1 | 0.88 | 0.88 | 0.88 | 0.88 | 0.88 |
| 9 | 3 | 1063 | 0.33 | 1 | 0.21 | 0.21 | 0.21 | 0.21 | 0.21 |
| 10 | 1 | 250 | 0.00 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Top-1..5 cumulative reply mass **as a share of the games reaching the node** (traffic-weighted), plus the mean per-node top-3 share:

| ply | top-1 | top-2 | top-3 | top-4 | top-5 | mean top-3 (per node) |
|---|---|---|---|---|---|---|
| 1 | 43.17 | 57.97 | 68.94 | 76.32 | 81.10 | 40.0 |
| 2 | 45.55 | 60.54 | 67.74 | 72.64 | 75.51 | 43.2 |
| 3 | 44.72 | 58.37 | 63.84 | 65.71 | 66.09 | 35.6 |
| 4 | 38.57 | 53.19 | 60.23 | 62.85 | 63.43 | 35.7 |
| 5 | 33.65 | 41.01 | 45.24 | 48.17 | 48.92 | 28.0 |
| 6 | 35.51 | 40.38 | 40.38 | 40.38 | 40.38 | 31.0 |
| 7 | 26.60 | 26.60 | 26.60 | 26.60 | 26.60 | 20.1 |
| 8 | 52.65 | 52.65 | 52.65 | 52.65 | 52.65 | 47.6 |
| 9 | 23.52 | 23.52 | 23.52 | 23.52 | 23.52 | 20.7 |
| 10 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.0 |

Width caps on top of this cut-off:

| cap applied to | width W | reply mass discarded, % of decision-point mass | worst ply (discard there, % of its reply mass) | discarded game-replies (summed over positions) | nodes in capped tree | paths at ply 20 | paths at ply 10 (termination) | all leaf paths |
|---|---|---|---|---|---|---|---|---|
| cap every node | 3 | 14.28 | ply 1: 26.5% | 64727 | 138 | 0 | 1 | 60 |
| cap every node | 4 | 9.27 | ply 1: 18.6% | 42014 | 197 | 0 | 1 | 94 |
| cap every node | 5 | 6.39 | ply 1: 13.5% | 28938 | 237 | 0 | 1 | 115 |
| cap opponent (Black) only | 3 | 17.50 | ply 1: 26.5% | 34079 | 218 | 0 | 1 | 108 |
| cap opponent (Black) only | 4 | 11.48 | ply 1: 18.6% | 22363 | 250 | 0 | 1 | 129 |
| cap opponent (Black) only | 5 | 8.19 | ply 1: 13.5% | 15959 | 274 | 0 | 1 | 141 |
| no cap (cut-off only) | - | 0.00 | ply 0: 0.0% | 0 | 322 | 0 | 1 | 163 |

### Bucket: both>=1800 (9525 games)

#### cut-off >= 1.0% of games (>= 95 games)

Tree: 89 nodes, maximum ply 8, nodes by ply [6, 19, 19, 17, 15, 9, 3, 1].

Top-1..5 cumulative reply mass **as a share of all games in the bucket** (sum of the top-k reply counts / 9525):

| ply | positions | games reaching | replies mean | replies max | top-1 | top-2 | top-3 | top-4 | top-5 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 6 | 9276 | 3.17 | 10 | 28.47 | 46.97 | 61.06 | 67.59 | 72.96 |
| 2 | 19 | 8159 | 1.00 | 3 | 44.22 | 57.00 | 59.23 | 59.23 | 59.23 |
| 3 | 19 | 5642 | 0.89 | 3 | 32.28 | 38.96 | 40.70 | 40.70 | 40.70 |
| 4 | 17 | 3877 | 0.88 | 3 | 18.19 | 21.82 | 23.02 | 23.02 | 23.02 |
| 5 | 15 | 2193 | 0.60 | 2 | 11.01 | 12.02 | 12.02 | 12.02 | 12.02 |
| 6 | 9 | 1145 | 0.33 | 1 | 4.42 | 4.42 | 4.42 | 4.42 | 4.42 |
| 7 | 3 | 421 | 0.33 | 1 | 1.03 | 1.03 | 1.03 | 1.03 | 1.03 |
| 8 | 1 | 98 | 0.00 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Top-1..5 cumulative reply mass **as a share of the games reaching the node** (traffic-weighted), plus the mean per-node top-3 share:

| ply | top-1 | top-2 | top-3 | top-4 | top-5 | mean top-3 (per node) |
|---|---|---|---|---|---|---|
| 1 | 29.24 | 48.23 | 62.70 | 69.40 | 74.91 | 32.2 |
| 2 | 51.62 | 66.54 | 69.15 | 69.15 | 69.15 | 41.1 |
| 3 | 54.50 | 65.77 | 68.72 | 68.72 | 68.72 | 48.9 |
| 4 | 44.70 | 53.60 | 56.56 | 56.56 | 56.56 | 50.5 |
| 5 | 47.83 | 52.21 | 52.21 | 52.21 | 52.21 | 46.4 |
| 6 | 36.77 | 36.77 | 36.77 | 36.77 | 36.77 | 29.8 |
| 7 | 23.28 | 23.28 | 23.28 | 23.28 | 23.28 | 22.5 |
| 8 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.0 |

Width caps on top of this cut-off:

| cap applied to | width W | reply mass discarded, % of decision-point mass | worst ply (discard there, % of its reply mass) | discarded game-replies (summed over positions) | nodes in capped tree | paths at ply 20 | paths at ply 8 (termination) | all leaf paths |
|---|---|---|---|---|---|---|---|---|
| cap every node | 3 | 9.44 | ply 1: 28.7% | 2908 | 61 | 0 | 1 | 23 |
| cap every node | 4 | 6.28 | ply 1: 21.1% | 1934 | 72 | 0 | 1 | 27 |
| cap every node | 5 | 4.25 | ply 1: 14.8% | 1311 | 78 | 0 | 1 | 30 |
| cap opponent (Black) only | 3 | 17.64 | ply 1: 28.7% | 2343 | 65 | 0 | 1 | 26 |
| cap opponent (Black) only | 4 | 12.96 | ply 1: 21.1% | 1721 | 74 | 0 | 1 | 29 |
| cap opponent (Black) only | 5 | 9.11 | ply 1: 14.8% | 1210 | 79 | 0 | 1 | 31 |
| no cap (cut-off only) | - | 0.00 | ply 0: 0.0% | 0 | 90 | 0 | 1 | 39 |

#### cut-off >= 0.2% of games (>= 19 games)

Tree: 450 nodes, maximum ply 18, nodes by ply [10, 37, 67, 78, 78, 71, 47, 30, 17, 4, 3, 2, 1, 1, 1, 1, 1, 1].

Top-1..5 cumulative reply mass **as a share of all games in the bucket** (sum of the top-k reply counts / 9525):

| ply | positions | games reaching | replies mean | replies max | top-1 | top-2 | top-3 | top-4 | top-5 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 10 | 9487 | 3.70 | 11 | 29.17 | 49.76 | 65.19 | 72.71 | 78.82 |
| 2 | 37 | 9040 | 1.81 | 8 | 55.45 | 73.82 | 79.16 | 81.02 | 82.02 |
| 3 | 67 | 7938 | 1.16 | 5 | 49.29 | 60.60 | 65.24 | 67.10 | 67.81 |
| 4 | 78 | 6459 | 1.00 | 5 | 32.94 | 43.27 | 47.33 | 48.79 | 49.61 |
| 5 | 78 | 4725 | 0.91 | 4 | 29.77 | 34.38 | 35.14 | 35.35 | 35.35 |
| 6 | 71 | 3367 | 0.66 | 3 | 16.29 | 18.83 | 19.63 | 19.63 | 19.63 |
| 7 | 47 | 1870 | 0.64 | 3 | 9.31 | 10.47 | 10.90 | 10.90 | 10.90 |
| 8 | 30 | 1038 | 0.57 | 3 | 5.02 | 5.24 | 5.45 | 5.45 | 5.45 |
| 9 | 17 | 519 | 0.24 | 1 | 1.67 | 1.67 | 1.67 | 1.67 | 1.67 |
| 10 | 4 | 159 | 0.75 | 1 | 1.02 | 1.02 | 1.02 | 1.02 | 1.02 |
| 11 | 3 | 97 | 0.67 | 1 | 0.75 | 0.75 | 0.75 | 0.75 | 0.75 |
| 12 | 2 | 71 | 0.50 | 1 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 |
| 13 | 1 | 48 | 1.00 | 1 | 0.39 | 0.39 | 0.39 | 0.39 | 0.39 |
| 14 | 1 | 37 | 1.00 | 1 | 0.28 | 0.28 | 0.28 | 0.28 | 0.28 |
| 15 | 1 | 27 | 1.00 | 1 | 0.28 | 0.28 | 0.28 | 0.28 | 0.28 |
| 16 | 1 | 27 | 1.00 | 1 | 0.25 | 0.25 | 0.25 | 0.25 | 0.25 |
| 17 | 1 | 24 | 1.00 | 1 | 0.21 | 0.21 | 0.21 | 0.21 | 0.21 |
| 18 | 1 | 20 | 0.00 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Top-1..5 cumulative reply mass **as a share of the games reaching the node** (traffic-weighted), plus the mean per-node top-3 share:

| ply | top-1 | top-2 | top-3 | top-4 | top-5 | mean top-3 (per node) |
|---|---|---|---|---|---|---|
| 1 | 29.28 | 49.96 | 65.45 | 73.01 | 79.14 | 36.7 |
| 2 | 58.43 | 77.78 | 83.41 | 85.37 | 86.42 | 62.7 |
| 3 | 59.15 | 72.71 | 78.28 | 80.51 | 81.37 | 56.5 |
| 4 | 48.58 | 63.80 | 69.79 | 71.95 | 73.15 | 46.8 |
| 5 | 60.02 | 69.31 | 70.84 | 71.26 | 71.26 | 57.1 |
| 6 | 46.09 | 53.28 | 55.54 | 55.54 | 55.54 | 37.0 |
| 7 | 47.43 | 53.32 | 55.51 | 55.51 | 55.51 | 43.1 |
| 8 | 46.05 | 48.07 | 50.00 | 50.00 | 50.00 | 39.6 |
| 9 | 30.64 | 30.64 | 30.64 | 30.64 | 30.64 | 19.4 |
| 10 | 61.01 | 61.01 | 61.01 | 61.01 | 61.01 | 68.7 |
| 11 | 73.20 | 73.20 | 73.20 | 73.20 | 73.20 | 64.1 |
| 12 | 67.61 | 67.61 | 67.61 | 67.61 | 67.61 | 50.0 |
| 13 | 77.08 | 77.08 | 77.08 | 77.08 | 77.08 | 77.1 |
| 14 | 72.97 | 72.97 | 72.97 | 72.97 | 72.97 | 73.0 |
| 15 | 100.00 | 100.00 | 100.00 | 100.00 | 100.00 | 100.0 |
| 16 | 88.89 | 88.89 | 88.89 | 88.89 | 88.89 | 88.9 |
| 17 | 83.33 | 83.33 | 83.33 | 83.33 | 83.33 | 83.3 |
| 18 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.0 |

Width caps on top of this cut-off:

| cap applied to | width W | reply mass discarded, % of decision-point mass | worst ply (discard there, % of its reply mass) | discarded game-replies (summed over positions) | nodes in capped tree | paths at ply 20 | paths at ply 18 (termination) | all leaf paths |
|---|---|---|---|---|---|---|---|---|
| cap every node | 3 | 9.98 | ply 1: 31.3% | 4487 | 235 | 0 | 1 | 86 |
| cap every node | 4 | 6.46 | ply 1: 23.4% | 2905 | 302 | 0 | 1 | 116 |
| cap every node | 5 | 4.38 | ply 1: 16.9% | 1970 | 343 | 0 | 1 | 137 |
| cap opponent (Black) only | 3 | 15.31 | ply 1: 31.3% | 3096 | 283 | 0 | 1 | 112 |
| cap opponent (Black) only | 4 | 10.79 | ply 1: 23.4% | 2182 | 327 | 0 | 1 | 131 |
| cap opponent (Black) only | 5 | 7.58 | ply 1: 16.9% | 1532 | 358 | 0 | 1 | 146 |
| no cap (cut-off only) | - | 0.00 | ply 0: 0.0% | 0 | 451 | 0 | 1 | 175 |

### Bucket: both<1500 (19771 games)

#### cut-off >= 1.0% of games (>= 198 games)

Tree: 55 nodes, maximum ply 5, nodes by ply [8, 15, 16, 8, 8].

Top-1..5 cumulative reply mass **as a share of all games in the bucket** (sum of the top-k reply counts / 19771):

| ply | positions | games reaching | replies mean | replies max | top-1 | top-2 | top-3 | top-4 | top-5 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 8 | 19066 | 1.88 | 9 | 49.58 | 60.52 | 67.69 | 72.76 | 74.53 |
| 2 | 15 | 15878 | 1.07 | 6 | 28.60 | 39.33 | 44.02 | 48.07 | 49.38 |
| 3 | 16 | 10001 | 0.50 | 3 | 17.83 | 22.27 | 23.93 | 23.93 | 23.93 |
| 4 | 8 | 4732 | 1.00 | 4 | 7.74 | 11.78 | 13.35 | 14.84 | 14.84 |
| 5 | 8 | 2935 | 0.00 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Top-1..5 cumulative reply mass **as a share of the games reaching the node** (traffic-weighted), plus the mean per-node top-3 share:

| ply | top-1 | top-2 | top-3 | top-4 | top-5 | mean top-3 (per node) |
|---|---|---|---|---|---|---|
| 1 | 51.42 | 62.76 | 70.19 | 75.45 | 77.28 | 33.6 |
| 2 | 35.62 | 48.97 | 54.82 | 59.85 | 61.48 | 21.8 |
| 3 | 35.25 | 44.03 | 47.32 | 47.32 | 47.32 | 21.0 |
| 4 | 32.35 | 49.24 | 55.77 | 62.02 | 62.02 | 37.4 |
| 5 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.0 |

Width caps on top of this cut-off:

| cap applied to | width W | reply mass discarded, % of decision-point mass | worst ply (discard there, % of its reply mass) | discarded game-replies (summed over positions) | nodes in capped tree | paths at ply 20 | paths at ply 5 (termination) | all leaf paths |
|---|---|---|---|---|---|---|---|---|
| cap every node | 3 | 11.15 | ply 1: 15.7% | 5866 | 35 | 0 | 6 | 19 |
| cap every node | 4 | 6.14 | ply 1: 9.4% | 3230 | 45 | 0 | 8 | 25 |
| cap every node | 5 | 4.08 | ply 1: 7.2% | 2146 | 48 | 0 | 8 | 28 |
| cap opponent (Black) only | 3 | 12.11 | ply 1: 15.7% | 2495 | 48 | 0 | 8 | 29 |
| cap opponent (Black) only | 4 | 7.24 | ply 1: 9.4% | 1492 | 51 | 0 | 8 | 31 |
| cap opponent (Black) only | 5 | 5.55 | ply 1: 7.2% | 1143 | 52 | 0 | 8 | 32 |
| no cap (cut-off only) | - | 0.00 | ply 0: 0.0% | 0 | 56 | 0 | 8 | 36 |

#### cut-off >= 0.2% of games (>= 40 games)

Tree: 282 nodes, maximum ply 9, nodes by ply [13, 43, 70, 65, 39, 30, 16, 4, 2].

Top-1..5 cumulative reply mass **as a share of all games in the bucket** (sum of the top-k reply counts / 19771):

| ply | positions | games reaching | replies mean | replies max | top-1 | top-2 | top-3 | top-4 | top-5 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 13 | 19648 | 3.31 | 11 | 52.88 | 65.65 | 74.16 | 80.61 | 83.37 |
| 2 | 43 | 18289 | 1.63 | 9 | 36.48 | 51.26 | 59.41 | 65.30 | 68.51 |
| 3 | 70 | 14406 | 0.93 | 8 | 27.28 | 37.41 | 42.15 | 44.36 | 44.87 |
| 4 | 65 | 9096 | 0.60 | 5 | 14.76 | 20.49 | 23.33 | 25.27 | 25.80 |
| 5 | 39 | 5101 | 0.77 | 5 | 7.73 | 10.52 | 11.96 | 12.70 | 12.91 |
| 6 | 30 | 2553 | 0.53 | 2 | 4.35 | 5.06 | 5.06 | 5.06 | 5.06 |
| 7 | 16 | 1001 | 0.25 | 1 | 1.15 | 1.15 | 1.15 | 1.15 | 1.15 |
| 8 | 4 | 227 | 0.50 | 1 | 0.58 | 0.58 | 0.58 | 0.58 | 0.58 |
| 9 | 2 | 115 | 0.00 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Top-1..5 cumulative reply mass **as a share of the games reaching the node** (traffic-weighted), plus the mean per-node top-3 share:

| ply | top-1 | top-2 | top-3 | top-4 | top-5 | mean top-3 (per node) |
|---|---|---|---|---|---|---|
| 1 | 53.21 | 66.06 | 74.62 | 81.12 | 83.90 | 54.2 |
| 2 | 39.44 | 55.42 | 64.22 | 70.59 | 74.07 | 34.7 |
| 3 | 37.44 | 51.35 | 57.84 | 60.88 | 61.59 | 28.3 |
| 4 | 32.08 | 44.55 | 50.70 | 54.93 | 56.08 | 25.9 |
| 5 | 29.97 | 40.76 | 46.36 | 49.23 | 50.05 | 25.8 |
| 6 | 33.69 | 39.21 | 39.21 | 39.21 | 39.21 | 30.7 |
| 7 | 22.68 | 22.68 | 22.68 | 22.68 | 22.68 | 15.8 |
| 8 | 50.66 | 50.66 | 50.66 | 50.66 | 50.66 | 47.2 |
| 9 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.0 |

Width caps on top of this cut-off:

| cap applied to | width W | reply mass discarded, % of decision-point mass | worst ply (discard there, % of its reply mass) | discarded game-replies (summed over positions) | nodes in capped tree | paths at ply 20 | paths at ply 9 (termination) | all leaf paths |
|---|---|---|---|---|---|---|---|---|
| cap every node | 3 | 14.32 | ply 1: 19.8% | 10088 | 132 | 0 | 2 | 61 |
| cap every node | 4 | 8.72 | ply 1: 12.9% | 6142 | 188 | 0 | 2 | 96 |
| cap every node | 5 | 6.01 | ply 1: 9.9% | 4235 | 216 | 0 | 2 | 116 |
| cap opponent (Black) only | 3 | 15.18 | ply 1: 19.8% | 4578 | 213 | 0 | 2 | 111 |
| cap opponent (Black) only | 4 | 9.01 | ply 1: 12.9% | 2719 | 244 | 0 | 2 | 131 |
| cap opponent (Black) only | 5 | 6.73 | ply 1: 9.9% | 2029 | 253 | 0 | 2 | 138 |
| no cap (cut-off only) | - | 0.00 | ply 0: 0.0% | 0 | 283 | 0 | 2 | 158 |

## Two-parameter grid: width_player x width_opponent

The sections above cap a single width and assume a White learner (`cap every node` W caps both sides, `cap opponent (Black) only` W caps only Black's plies). The app now has two independent knobs and drills **both colours** - it samples which side the learner plays each iteration:

- **`width_player` P**: at a position where the learner is to move, any of the P most popular surviving moves is acceptable; any other move is a failure (the round leaves the repertoire). Nothing is sampled *for* the learner, so P measures how much of a position's move mass the learner must have ready.
- **`width_opponent` O**: the app samples the opponent's reply among the O most popular surviving moves, renormalised over those O.

**The resulting tree.** Every position must hold both what the learner may legitimately play (top P) and what the opponent may spring (top O), so the tree keeps their union. Both sets are prefixes of one popularity ordering, so that union is exactly the top `max(P, O)` surviving replies: **iteration and node counts depend only on `k = max(P, O)`**, while P and O drive the two discard columns independently. Capping only removes edges, so no cap can make a tree deeper than its cut-off.

- **iterations** = distinct full games the learner can be shown = leaf paths of the tree (paths that dead-end plus the deepest frontier). A move sequence is counted once even though the learner meets it once as White and once as Black.
- **positions** = every node of the tree, root included. The learner plays both colours, so the learner is to move at every ply in the iterations where the learner has that colour and must be prepared at every node.
- **positions where the learner must move** = the tree's internal nodes (at least one kept reply), root included. **acceptable learner moves** at such a position = `min(P, replies the tree keeps there)`.

**Discard denominators, stated explicitly.** A position of the cut-off tree that still has surviving replies carries those replies' game counts as mass. All three discard figures below share one denominator **D = the surviving reply mass summed over every cut-off position that has at least one surviving reply** (traffic-weighted by the games reaching each position); each table's caption gives D for its bucket/cut-off.

- **learner decision points** = those positions read in the iterations where the learner has the move; the figure is the share of D that lies outside the top P, i.e. the traffic-weighted chance that the learner plays a move the repertoire does not accept.
- **opponent decision points** = the same positions read in the iterations where the opponent has the move; the share of D outside the top O.
- **combined** = the share of D outside `top P ∪ top O`, which equals outside `top max(P, O)`. It is *not* the sum of the two columns: mass outside both caps is counted once.

Because both colours are drilled, both sides are to move at every ply, so the learner's and the opponent's decision-point sets coincide (the same positions, opposite iterations); the columns differ only in which width is applied. The old `cap opponent (Black) only` rows are narrower than the opponent column here: they capped odd plies only.

### Full grid: `both>=1800`, both cut-offs

#### `both>=1800`, cut-off >= 1.0% of games (>= 95 games)

Iterations (leaf paths) / positions (nodes, root included), per cell. Values repeat along every anti-diagonal `max(P, O) = k`: the tree is the top-k tree.

| wp \ wo | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 1 | 1 / 8 | 14 / 39 | 23 / 61 | 27 / 72 | 30 / 78 |
| 2 | 14 / 39 | 14 / 39 | 23 / 61 | 27 / 72 | 30 / 78 |
| 3 | 23 / 61 | 23 / 61 | 23 / 61 | 27 / 72 | 30 / 78 |
| 4 | 27 / 72 | 27 / 72 | 27 / 72 | 27 / 72 | 30 / 78 |
| 5 | 30 / 78 | 30 / 78 | 30 / 78 | 30 / 78 | 30 / 78 |

Denominator D for every percentage in the table below: **30811 surviving game-replies over 51 positions** (every cut-off position with at least one surviving reply). `learner: discarded game-replies` is the numerator behind the learner percentage, in game-replies summed over positions - a game counts once per position where its reply falls outside the accepted set.

| width_player | width_opponent | iterations | positions | positions learner moves at | acceptable learner moves mean | acceptable learner moves max | learner decision points: discard % | learner: discarded game-replies | opponent decision points: discard % | opponent: discarded game-replies | combined: discard % | combined: discarded game-replies | max ply |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 8 | 7 | 1.00 | 1 | 39.48 | 12164 | 39.48 | 12164 | 39.48 | 12164 | 7 |
| 1 | 2 | 14 | 39 | 25 | 1.00 | 1 | 39.48 | 12164 | 16.83 | 5184 | 16.83 | 5184 | 7 |
| 1 | 3 | 23 | 61 | 38 | 1.00 | 1 | 39.48 | 12164 | 9.44 | 2908 | 9.44 | 2908 | 8 |
| 1 | 4 | 27 | 72 | 45 | 1.00 | 1 | 39.48 | 12164 | 6.28 | 1934 | 6.28 | 1934 | 8 |
| 1 | 5 | 30 | 78 | 48 | 1.00 | 1 | 39.48 | 12164 | 4.25 | 1311 | 4.25 | 1311 | 8 |
| 2 | 1 | 14 | 39 | 25 | 1.52 | 2 | 16.83 | 5184 | 39.48 | 12164 | 16.83 | 5184 | 7 |
| 2 | 2 | 14 | 39 | 25 | 1.52 | 2 | 16.83 | 5184 | 16.83 | 5184 | 16.83 | 5184 | 7 |
| 2 | 3 | 23 | 61 | 38 | 1.39 | 2 | 16.83 | 5184 | 9.44 | 2908 | 9.44 | 2908 | 8 |
| 2 | 4 | 27 | 72 | 45 | 1.36 | 2 | 16.83 | 5184 | 6.28 | 1934 | 6.28 | 1934 | 8 |
| 2 | 5 | 30 | 78 | 48 | 1.33 | 2 | 16.83 | 5184 | 4.25 | 1311 | 4.25 | 1311 | 8 |
| 3 | 1 | 23 | 61 | 38 | 1.58 | 3 | 9.44 | 2908 | 39.48 | 12164 | 9.44 | 2908 | 8 |
| 3 | 2 | 23 | 61 | 38 | 1.58 | 3 | 9.44 | 2908 | 16.83 | 5184 | 9.44 | 2908 | 8 |
| 3 | 3 | 23 | 61 | 38 | 1.58 | 3 | 9.44 | 2908 | 9.44 | 2908 | 9.44 | 2908 | 8 |
| 3 | 4 | 27 | 72 | 45 | 1.51 | 3 | 9.44 | 2908 | 6.28 | 1934 | 6.28 | 1934 | 8 |
| 3 | 5 | 30 | 78 | 48 | 1.48 | 3 | 9.44 | 2908 | 4.25 | 1311 | 4.25 | 1311 | 8 |
| 4 | 1 | 27 | 72 | 45 | 1.58 | 4 | 6.28 | 1934 | 39.48 | 12164 | 6.28 | 1934 | 8 |
| 4 | 2 | 27 | 72 | 45 | 1.58 | 4 | 6.28 | 1934 | 16.83 | 5184 | 6.28 | 1934 | 8 |
| 4 | 3 | 27 | 72 | 45 | 1.58 | 4 | 6.28 | 1934 | 9.44 | 2908 | 6.28 | 1934 | 8 |
| 4 | 4 | 27 | 72 | 45 | 1.58 | 4 | 6.28 | 1934 | 6.28 | 1934 | 6.28 | 1934 | 8 |
| 4 | 5 | 30 | 78 | 48 | 1.54 | 4 | 6.28 | 1934 | 4.25 | 1311 | 4.25 | 1311 | 8 |
| 5 | 1 | 30 | 78 | 48 | 1.60 | 5 | 4.25 | 1311 | 39.48 | 12164 | 4.25 | 1311 | 8 |
| 5 | 2 | 30 | 78 | 48 | 1.60 | 5 | 4.25 | 1311 | 16.83 | 5184 | 4.25 | 1311 | 8 |
| 5 | 3 | 30 | 78 | 48 | 1.60 | 5 | 4.25 | 1311 | 9.44 | 2908 | 4.25 | 1311 | 8 |
| 5 | 4 | 30 | 78 | 48 | 1.60 | 5 | 4.25 | 1311 | 6.28 | 1934 | 4.25 | 1311 | 8 |
| 5 | 5 | 30 | 78 | 48 | 1.60 | 5 | 4.25 | 1311 | 4.25 | 1311 | 4.25 | 1311 | 8 |

#### `both>=1800`, cut-off >= 0.2% of games (>= 19 games)

Iterations (leaf paths) / positions (nodes, root included), per cell. Values repeat along every anti-diagonal `max(P, O) = k`: the tree is the top-k tree.

| wp \ wo | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 1 | 1 / 10 | 36 / 120 | 86 / 235 | 116 / 302 | 137 / 343 |
| 2 | 36 / 120 | 36 / 120 | 86 / 235 | 116 / 302 | 137 / 343 |
| 3 | 86 / 235 | 86 / 235 | 86 / 235 | 116 / 302 | 137 / 343 |
| 4 | 116 / 302 | 116 / 302 | 116 / 302 | 116 / 302 | 137 / 343 |
| 5 | 137 / 343 | 137 / 343 | 137 / 343 | 137 / 343 | 137 / 343 |

Denominator D for every percentage in the table below: **44953 surviving game-replies over 276 positions** (every cut-off position with at least one surviving reply). `learner: discarded game-replies` is the numerator behind the learner percentage, in game-replies summed over positions - a game counts once per position where its reply falls outside the accepted set.

| width_player | width_opponent | iterations | positions | positions learner moves at | acceptable learner moves mean | acceptable learner moves max | learner decision points: discard % | learner: discarded game-replies | opponent decision points: discard % | opponent: discarded game-replies | combined: discard % | combined: discarded game-replies | max ply |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 10 | 9 | 1.00 | 1 | 38.82 | 17450 | 38.82 | 17450 | 38.82 | 17450 | 9 |
| 1 | 2 | 36 | 120 | 84 | 1.00 | 1 | 38.82 | 17450 | 17.67 | 7943 | 17.67 | 7943 | 18 |
| 1 | 3 | 86 | 235 | 149 | 1.00 | 1 | 38.82 | 17450 | 9.98 | 4487 | 9.98 | 4487 | 18 |
| 1 | 4 | 116 | 302 | 186 | 1.00 | 1 | 38.82 | 17450 | 6.46 | 2905 | 6.46 | 2905 | 18 |
| 1 | 5 | 137 | 343 | 206 | 1.00 | 1 | 38.82 | 17450 | 4.38 | 1970 | 4.38 | 1970 | 18 |
| 2 | 1 | 36 | 120 | 84 | 1.42 | 2 | 17.67 | 7943 | 38.82 | 17450 | 17.67 | 7943 | 18 |
| 2 | 2 | 36 | 120 | 84 | 1.42 | 2 | 17.67 | 7943 | 17.67 | 7943 | 17.67 | 7943 | 18 |
| 2 | 3 | 86 | 235 | 149 | 1.38 | 2 | 17.67 | 7943 | 9.98 | 4487 | 9.98 | 4487 | 18 |
| 2 | 4 | 116 | 302 | 186 | 1.35 | 2 | 17.67 | 7943 | 6.46 | 2905 | 6.46 | 2905 | 18 |
| 2 | 5 | 137 | 343 | 206 | 1.35 | 2 | 17.67 | 7943 | 4.38 | 1970 | 4.38 | 1970 | 18 |
| 3 | 1 | 86 | 235 | 149 | 1.57 | 3 | 9.98 | 4487 | 38.82 | 17450 | 9.98 | 4487 | 18 |
| 3 | 2 | 86 | 235 | 149 | 1.57 | 3 | 9.98 | 4487 | 17.67 | 7943 | 9.98 | 4487 | 18 |
| 3 | 3 | 86 | 235 | 149 | 1.57 | 3 | 9.98 | 4487 | 9.98 | 4487 | 9.98 | 4487 | 18 |
| 3 | 4 | 116 | 302 | 186 | 1.52 | 3 | 9.98 | 4487 | 6.46 | 2905 | 6.46 | 2905 | 18 |
| 3 | 5 | 137 | 343 | 206 | 1.52 | 3 | 9.98 | 4487 | 4.38 | 1970 | 4.38 | 1970 | 18 |
| 4 | 1 | 116 | 302 | 186 | 1.62 | 4 | 6.46 | 2905 | 38.82 | 17450 | 6.46 | 2905 | 18 |
| 4 | 2 | 116 | 302 | 186 | 1.62 | 4 | 6.46 | 2905 | 17.67 | 7943 | 6.46 | 2905 | 18 |
| 4 | 3 | 116 | 302 | 186 | 1.62 | 4 | 6.46 | 2905 | 9.98 | 4487 | 6.46 | 2905 | 18 |
| 4 | 4 | 116 | 302 | 186 | 1.62 | 4 | 6.46 | 2905 | 6.46 | 2905 | 6.46 | 2905 | 18 |
| 4 | 5 | 137 | 343 | 206 | 1.61 | 4 | 6.46 | 2905 | 4.38 | 1970 | 4.38 | 1970 | 18 |
| 5 | 1 | 137 | 343 | 206 | 1.66 | 5 | 4.38 | 1970 | 38.82 | 17450 | 4.38 | 1970 | 18 |
| 5 | 2 | 137 | 343 | 206 | 1.66 | 5 | 4.38 | 1970 | 17.67 | 7943 | 4.38 | 1970 | 18 |
| 5 | 3 | 137 | 343 | 206 | 1.66 | 5 | 4.38 | 1970 | 9.98 | 4487 | 4.38 | 1970 | 18 |
| 5 | 4 | 137 | 343 | 206 | 1.66 | 5 | 4.38 | 1970 | 6.46 | 2905 | 4.38 | 1970 | 18 |
| 5 | 5 | 137 | 343 | 206 | 1.66 | 5 | 4.38 | 1970 | 4.38 | 1970 | 4.38 | 1970 | 18 |

### Headline rows: `all` and `both<1500`

Because the tree shape depends only on `k = max(P, O)`, two families cover the grid: the strict-learner cells `(1, k)` and the matched cells `(k, k)`. Same columns as the full grid minus the absolute numerators.

#### Bucket `all` (121332 games), cut-off >= 1.0% of games (>= 1213 games); D = 325513 surviving game-replies over 25 positions

| case | width_player | width_opponent | iterations | positions | positions learner moves at | acceptable learner moves mean | acceptable learner moves max | learner decision points: discard % | opponent decision points: discard % | combined: discard % | max ply |
|---|---|---|---|---|---|---|---|---|---|---|---|
| strict learner (P=1) | 1 | 1 | 1 | 6 | 5 | 1.00 | 1 | 39.65 | 39.65 | 39.65 | 5 |
| strict learner (P=1) | 1 | 2 | 12 | 25 | 13 | 1.00 | 1 | 39.65 | 19.18 | 19.18 | 5 |
| matched (P=O) | 2 | 2 | 12 | 25 | 13 | 1.85 | 2 | 19.18 | 19.18 | 19.18 | 5 |
| strict learner (P=1) | 1 | 3 | 20 | 40 | 20 | 1.00 | 1 | 39.65 | 11.83 | 11.83 | 6 |
| matched (P=O) | 3 | 3 | 20 | 40 | 20 | 1.95 | 3 | 11.83 | 11.83 | 11.83 | 6 |
| strict learner (P=1) | 1 | 4 | 25 | 50 | 25 | 1.00 | 1 | 39.65 | 7.26 | 7.26 | 6 |
| matched (P=O) | 4 | 4 | 25 | 50 | 25 | 1.96 | 4 | 7.26 | 7.26 | 7.26 | 6 |
| strict learner (P=1) | 1 | 5 | 29 | 54 | 25 | 1.00 | 1 | 39.65 | 4.44 | 4.44 | 6 |
| matched (P=O) | 5 | 5 | 29 | 54 | 25 | 2.12 | 5 | 4.44 | 4.44 | 4.44 | 6 |

#### Bucket `all` (121332 games), cut-off >= 0.2% of games (>= 243 games); D = 453162 surviving game-replies over 159 positions

| case | width_player | width_opponent | iterations | positions | positions learner moves at | acceptable learner moves mean | acceptable learner moves max | learner decision points: discard % | opponent decision points: discard % | combined: discard % | max ply |
|---|---|---|---|---|---|---|---|---|---|---|---|
| strict learner (P=1) | 1 | 1 | 1 | 10 | 9 | 1.00 | 1 | 41.97 | 41.97 | 41.97 | 9 |
| strict learner (P=1) | 1 | 2 | 26 | 71 | 45 | 1.00 | 1 | 41.97 | 22.37 | 22.37 | 10 |
| matched (P=O) | 2 | 2 | 26 | 71 | 45 | 1.56 | 2 | 22.37 | 22.37 | 22.37 | 10 |
| strict learner (P=1) | 1 | 3 | 60 | 138 | 78 | 1.00 | 1 | 41.97 | 14.28 | 14.28 | 10 |
| matched (P=O) | 3 | 3 | 60 | 138 | 78 | 1.76 | 3 | 14.28 | 14.28 | 14.28 | 10 |
| strict learner (P=1) | 1 | 4 | 94 | 197 | 103 | 1.00 | 1 | 41.97 | 9.27 | 9.27 | 10 |
| matched (P=O) | 4 | 4 | 94 | 197 | 103 | 1.90 | 4 | 9.27 | 9.27 | 9.27 | 10 |
| strict learner (P=1) | 1 | 5 | 115 | 237 | 122 | 1.00 | 1 | 41.97 | 6.39 | 6.39 | 10 |
| matched (P=O) | 5 | 5 | 115 | 237 | 122 | 1.93 | 5 | 6.39 | 6.39 | 6.39 | 10 |

#### Bucket `both<1500` (19771 games), cut-off >= 1.0% of games (>= 198 games); D = 52612 surviving game-replies over 20 positions

| case | width_player | width_opponent | iterations | positions | positions learner moves at | acceptable learner moves mean | acceptable learner moves max | learner decision points: discard % | opponent decision points: discard % | combined: discard % | max ply |
|---|---|---|---|---|---|---|---|---|---|---|---|
| strict learner (P=1) | 1 | 1 | 1 | 6 | 5 | 1.00 | 1 | 38.11 | 38.11 | 38.11 | 5 |
| strict learner (P=1) | 1 | 2 | 10 | 23 | 13 | 1.00 | 1 | 38.11 | 19.48 | 19.48 | 5 |
| matched (P=O) | 2 | 2 | 10 | 23 | 13 | 1.69 | 2 | 19.48 | 19.48 | 19.48 | 5 |
| strict learner (P=1) | 1 | 3 | 19 | 35 | 16 | 1.00 | 1 | 38.11 | 11.15 | 11.15 | 5 |
| matched (P=O) | 3 | 3 | 19 | 35 | 16 | 2.12 | 3 | 11.15 | 11.15 | 11.15 | 5 |
| strict learner (P=1) | 1 | 4 | 25 | 45 | 20 | 1.00 | 1 | 38.11 | 6.14 | 6.14 | 5 |
| matched (P=O) | 4 | 4 | 25 | 45 | 20 | 2.20 | 4 | 6.14 | 6.14 | 6.14 | 5 |
| strict learner (P=1) | 1 | 5 | 28 | 48 | 20 | 1.00 | 1 | 38.11 | 4.08 | 4.08 | 5 |
| matched (P=O) | 5 | 5 | 28 | 48 | 20 | 2.35 | 5 | 4.08 | 4.08 | 4.08 | 5 |

#### Bucket `both<1500` (19771 games), cut-off >= 0.2% of games (>= 40 games); D = 70436 surviving game-replies over 125 positions

| case | width_player | width_opponent | iterations | positions | positions learner moves at | acceptable learner moves mean | acceptable learner moves max | learner decision points: discard % | opponent decision points: discard % | combined: discard % | max ply |
|---|---|---|---|---|---|---|---|---|---|---|---|
| strict learner (P=1) | 1 | 1 | 1 | 10 | 9 | 1.00 | 1 | 42.14 | 42.14 | 42.14 | 9 |
| strict learner (P=1) | 1 | 2 | 26 | 59 | 33 | 1.00 | 1 | 42.14 | 23.51 | 23.51 | 9 |
| matched (P=O) | 2 | 2 | 26 | 59 | 33 | 1.76 | 2 | 23.51 | 23.51 | 23.51 | 9 |
| strict learner (P=1) | 1 | 3 | 61 | 132 | 71 | 1.00 | 1 | 42.14 | 14.32 | 14.32 | 9 |
| matched (P=O) | 3 | 3 | 61 | 132 | 71 | 1.85 | 3 | 14.32 | 14.32 | 14.32 | 9 |
| strict learner (P=1) | 1 | 4 | 96 | 188 | 92 | 1.00 | 1 | 42.14 | 8.72 | 8.72 | 9 |
| matched (P=O) | 4 | 4 | 96 | 188 | 92 | 2.03 | 4 | 8.72 | 8.72 | 8.72 | 9 |
| strict learner (P=1) | 1 | 5 | 116 | 216 | 100 | 1.00 | 1 | 42.14 | 6.01 | 6.01 | 9 |
| matched (P=O) | 5 | 5 | 116 | 216 | 100 | 2.15 | 5 | 6.01 | 6.01 | 6.01 | 9 |

### Strict mode in detail: `width_player = 1` (force the top move)

The learner must reproduce the single most popular surviving move at every one of their turns, in both colours; only the opponent's pool widens. `max(P, O) = O`, so these rows are the top-O trees.

#### Bucket `all` (121332 games), cut-off >= 1.0% of games (>= 1213 games); D = 325513 surviving game-replies over 25 positions

| width_opponent | iterations | positions | positions learner moves at | acceptable learner moves mean | acceptable learner moves max | learner decision points: discard % | learner: discarded game-replies | opponent decision points: discard % | opponent: discarded game-replies | combined: discard % | combined: discarded game-replies | max ply |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 6 | 5 | 1.00 | 1 | 39.65 | 129061 | 39.65 | 129061 | 39.65 | 129061 | 5 |
| 2 | 12 | 25 | 13 | 1.00 | 1 | 39.65 | 129061 | 19.18 | 62426 | 19.18 | 62426 | 5 |
| 3 | 20 | 40 | 20 | 1.00 | 1 | 39.65 | 129061 | 11.83 | 38500 | 11.83 | 38500 | 6 |
| 4 | 25 | 50 | 25 | 1.00 | 1 | 39.65 | 129061 | 7.26 | 23618 | 7.26 | 23618 | 6 |
| 5 | 29 | 54 | 25 | 1.00 | 1 | 39.65 | 129061 | 4.44 | 14451 | 4.44 | 14451 | 6 |

#### Bucket `all` (121332 games), cut-off >= 0.2% of games (>= 243 games); D = 453162 surviving game-replies over 159 positions

| width_opponent | iterations | positions | positions learner moves at | acceptable learner moves mean | acceptable learner moves max | learner decision points: discard % | learner: discarded game-replies | opponent decision points: discard % | opponent: discarded game-replies | combined: discard % | combined: discarded game-replies | max ply |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 10 | 9 | 1.00 | 1 | 41.97 | 190205 | 41.97 | 190205 | 41.97 | 190205 | 9 |
| 2 | 26 | 71 | 45 | 1.00 | 1 | 41.97 | 190205 | 22.37 | 101364 | 22.37 | 101364 | 10 |
| 3 | 60 | 138 | 78 | 1.00 | 1 | 41.97 | 190205 | 14.28 | 64727 | 14.28 | 64727 | 10 |
| 4 | 94 | 197 | 103 | 1.00 | 1 | 41.97 | 190205 | 9.27 | 42014 | 9.27 | 42014 | 10 |
| 5 | 115 | 237 | 122 | 1.00 | 1 | 41.97 | 190205 | 6.39 | 28938 | 6.39 | 28938 | 10 |

#### Bucket `both>=1800` (9525 games), cut-off >= 1.0% of games (>= 95 games); D = 30811 surviving game-replies over 51 positions

| width_opponent | iterations | positions | positions learner moves at | acceptable learner moves mean | acceptable learner moves max | learner decision points: discard % | learner: discarded game-replies | opponent decision points: discard % | opponent: discarded game-replies | combined: discard % | combined: discarded game-replies | max ply |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 8 | 7 | 1.00 | 1 | 39.48 | 12164 | 39.48 | 12164 | 39.48 | 12164 | 7 |
| 2 | 14 | 39 | 25 | 1.00 | 1 | 39.48 | 12164 | 16.83 | 5184 | 16.83 | 5184 | 7 |
| 3 | 23 | 61 | 38 | 1.00 | 1 | 39.48 | 12164 | 9.44 | 2908 | 9.44 | 2908 | 8 |
| 4 | 27 | 72 | 45 | 1.00 | 1 | 39.48 | 12164 | 6.28 | 1934 | 6.28 | 1934 | 8 |
| 5 | 30 | 78 | 48 | 1.00 | 1 | 39.48 | 12164 | 4.25 | 1311 | 4.25 | 1311 | 8 |

#### Bucket `both>=1800` (9525 games), cut-off >= 0.2% of games (>= 19 games); D = 44953 surviving game-replies over 276 positions

| width_opponent | iterations | positions | positions learner moves at | acceptable learner moves mean | acceptable learner moves max | learner decision points: discard % | learner: discarded game-replies | opponent decision points: discard % | opponent: discarded game-replies | combined: discard % | combined: discarded game-replies | max ply |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 10 | 9 | 1.00 | 1 | 38.82 | 17450 | 38.82 | 17450 | 38.82 | 17450 | 9 |
| 2 | 36 | 120 | 84 | 1.00 | 1 | 38.82 | 17450 | 17.67 | 7943 | 17.67 | 7943 | 18 |
| 3 | 86 | 235 | 149 | 1.00 | 1 | 38.82 | 17450 | 9.98 | 4487 | 9.98 | 4487 | 18 |
| 4 | 116 | 302 | 186 | 1.00 | 1 | 38.82 | 17450 | 6.46 | 2905 | 6.46 | 2905 | 18 |
| 5 | 137 | 343 | 206 | 1.00 | 1 | 38.82 | 17450 | 4.38 | 1970 | 4.38 | 1970 | 18 |

#### Bucket `both<1500` (19771 games), cut-off >= 1.0% of games (>= 198 games); D = 52612 surviving game-replies over 20 positions

| width_opponent | iterations | positions | positions learner moves at | acceptable learner moves mean | acceptable learner moves max | learner decision points: discard % | learner: discarded game-replies | opponent decision points: discard % | opponent: discarded game-replies | combined: discard % | combined: discarded game-replies | max ply |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 6 | 5 | 1.00 | 1 | 38.11 | 20051 | 38.11 | 20051 | 38.11 | 20051 | 5 |
| 2 | 10 | 23 | 13 | 1.00 | 1 | 38.11 | 20051 | 19.48 | 10250 | 19.48 | 10250 | 5 |
| 3 | 19 | 35 | 16 | 1.00 | 1 | 38.11 | 20051 | 11.15 | 5866 | 11.15 | 5866 | 5 |
| 4 | 25 | 45 | 20 | 1.00 | 1 | 38.11 | 20051 | 6.14 | 3230 | 6.14 | 3230 | 5 |
| 5 | 28 | 48 | 20 | 1.00 | 1 | 38.11 | 20051 | 4.08 | 2146 | 4.08 | 2146 | 5 |

#### Bucket `both<1500` (19771 games), cut-off >= 0.2% of games (>= 40 games); D = 70436 surviving game-replies over 125 positions

| width_opponent | iterations | positions | positions learner moves at | acceptable learner moves mean | acceptable learner moves max | learner decision points: discard % | learner: discarded game-replies | opponent decision points: discard % | opponent: discarded game-replies | combined: discard % | combined: discarded game-replies | max ply |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 10 | 9 | 1.00 | 1 | 42.14 | 29680 | 42.14 | 29680 | 42.14 | 29680 | 9 |
| 2 | 26 | 59 | 33 | 1.00 | 1 | 42.14 | 29680 | 23.51 | 16563 | 23.51 | 16563 | 9 |
| 3 | 61 | 132 | 71 | 1.00 | 1 | 42.14 | 29680 | 14.32 | 10088 | 14.32 | 10088 | 9 |
| 4 | 96 | 188 | 92 | 1.00 | 1 | 42.14 | 29680 | 8.72 | 6142 | 8.72 | 6142 | 9 |
| 5 | 116 | 216 | 100 | 1.00 | 1 | 42.14 | 29680 | 6.01 | 4235 | 6.01 | 4235 | 9 |

### Does any cell reach ply 20?

**No.** Across all 150 cells (3 buckets x 2 cut-offs x 25 (P, O) combinations) **no capped tree reaches ply 20, or even ply 19**. The deepest cell is `both>=1800`, cut-off >= 0.2%, (width_player=1, width_opponent=2) at **ply 18**; the deepest trees are the 0.2% `both>=1800` ones, and their cut-off trees already stop at ply 18 (the uncapped maximum over every bucket and cut-off is ply 18). The width caps can only remove edges, so they cannot add depth: the old doc's "no tree reaches ply 20" holds a fortiori for every capped tree here (`paths at ply 20` = 0 in all 150 cells). The trie is built to ply 21, so nothing in this section is truncation.

Structural self-checks over the same 150 cells: cells sharing `max(P, O) = k` give identical iteration and node counts (verified); the learner discard rate is a function of `width_player` alone and the opponent rate of `width_opponent` alone (verified); every `(k, k)` cell reproduces the old `cap every node` W=k row exactly - same nodes, same leaf paths, same discarded mass, same denominator (verified); and the matched cell `(k, k)` weakly dominates every cell with `max(P, O) = k` (verified).

**Dominated cells.** Because the tree is the top-`k` tree, every off-diagonal cell is weakly dominated by the matched cell `(k, k) = (max(P, O), max(P, O))`: identical iterations and positions, and both discard figures weakly smaller (verified for all 150 cells). Turning a knob up to `k` is free, so the only real decision is `k`; the Pareto frontier of the whole grid is the diagonal `P = O`:


`both>=1800`, cut-off >= 1.0% (D = 30811 surviving game-replies over 51 positions):

| k = P = O | iterations | positions | iterations / positions | extra positions vs k-1 | coverage gained vs k-1 (points) | learner discard % | opponent discard % | max ply |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 8 | 0.12 | - | - | 39.48 | 39.48 | 7 |
| 2 | 14 | 39 | 0.36 | +31 | 22.65 | 16.83 | 16.83 | 7 |
| 3 | 23 | 61 | 0.38 | +22 | 7.39 | 9.44 | 9.44 | 8 |
| 4 | 27 | 72 | 0.38 | +11 | 3.16 | 6.28 | 6.28 | 8 |
| 5 | 30 | 78 | 0.38 | +6 | 2.02 | 4.25 | 4.25 | 8 |

`both>=1800`, cut-off >= 0.2% (D = 44953 surviving game-replies over 276 positions):

| k = P = O | iterations | positions | iterations / positions | extra positions vs k-1 | coverage gained vs k-1 (points) | learner discard % | opponent discard % | max ply |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 10 | 0.10 | - | - | 38.82 | 38.82 | 9 |
| 2 | 36 | 120 | 0.30 | +110 | 21.15 | 17.67 | 17.67 | 18 |
| 3 | 86 | 235 | 0.37 | +115 | 7.69 | 9.98 | 9.98 | 18 |
| 4 | 116 | 302 | 0.38 | +67 | 3.52 | 6.46 | 6.46 | 18 |
| 5 | 137 | 343 | 0.40 | +41 | 2.08 | 4.38 | 4.38 | 18 |

### How to read the two discard columns

At a fixed cut-off the two columns mean different things, and only one of them is a coverage loss:

- the **opponent** column is coverage: the share of the surviving reply mass the app will never show because the sampled pool is capped at O. `width_player` does not change it.
- the **learner** column is the pass bar: the share of the mass at the learner's decision points that lies outside the accepted set, i.e. the traffic-weighted chance that the move the learner would play is not one of the P accepted ones. It removes no games from the tree. Because it is dominated by the first move - the only position with many surviving replies - O does not change it either.
- **combined** is the tree's coverage loss: mass outside `top P ∪ top O`, i.e. the share of replies neither side of the drill can ever produce. It equals whichever of the two caps is the wider (`k = max(P, O)`).

Concretely for `both>=1800` at the 1% cut-off: **(width_player=1, width_opponent=3)** gives 23 iterations over 61 positions, discards 39.48% at the learner's decision points and 9.44% at the opponent's (combined 9.44%); **(3, 3)** gives the *same* 23 iterations over the same 61 positions, but the learner's obligation drops to 9.44% (combined unchanged at 9.44%); **(1, 5)** widens the tree to 30 iterations and 78 positions, keeps the learner bar at 39.48% and cuts the opponent's loss to 4.25%. Going from P=3 to P=1 therefore buys nothing in coverage (the tree is set by O whenever O >= P) and costs 30.04 points of learner failure risk; going from O=3 to O=5 buys 5.18 points of coverage for 7 extra iterations and 17 extra positions to prepare. The learner-side penalty is concentrated where branching is real: the 1% cut-off tree offers a mean of 1.75 surviving replies per decision point (max 10, at the very first move for White), so most positions accept the single top move anyway and P=1 discards almost all of its mass at the shallow, wide plies.


## What this implies for a width parameter

**How much does a width cap of 3 or 5 discard?** Capping only the opponent (Black) for the `both>=1800` population: **width 3 discards 17.6% of the opponent's reply probability at the 1% cut-off and 15.3% at 0.2%; width 5 discards 9.1% and 7.6%** - a traffic-weighted average over every position where the cap applies. That average is almost entirely Black's *first* move, the one position every game passes through. At ply 2 the top-3 replies keep 62.7% of the games reaching the position (71.3% of the reply mass that survived the 1% cut-off, so 28.7% is discarded) and the top-5 keep 74.9% / 85.2%; by ply 4 the 1% tree has so few surviving replies per position that the top 3 keep 100% of the surviving reply mass (68.7% of the games reaching the position), while at the 0.2% cut-off the top 3 still keep 96.2% of it. Going from width 5 to width 3 costs 8.5 points of reply mass at the 1% cut-off and 7.7 at 0.2%, concentrated on Black's first move; from ply 4 onward both caps are nearly free.

The larger popularity loss is **not** the width cap but the cut-off itself, and the width cap is what makes the repertoire finite. At >=1800 the 1% tree stops at ply 8 (89 nodes, 39 leaf paths) and the 0.2% tree at ply 18 (450 nodes, 175 leaf paths). Depth 20 is never reached, so `paths at ply 20` is 0 for every configuration and the informative size numbers are the termination ply (always exactly one deepest path) and the total repertoire: capping every node at width 3 leaves 86 leaf paths at the 0.2% cut-off against 175 uncapped (width 4: 116, width 5: 137), and 23 / 27 / 30 at the 1% cut-off. Capping only the opponent is cheaper: 112 leaf paths at width 3 on the 0.2% cut-off against 175 uncapped, because the learner's own moves stay free - W bounds what the opponent can spring on the learner, not the learner's repertoire.

Rating band matters more than the width cap. At the same 1% cut-off the >=1800 tree reaches ply 8 while `both<1500` stops at ply 5, and the low-band mix is far more concentrated: `1.e4 e5` alone is 33.7% of games there against 11.7% at >=1800, and `both<1500` still has a detectable `1.e3 e5` (3.6%) where >=1800 does not (see `refs/lichess/dump-2013-01-tree-stats.txt`; this run reproduces its node counts). Width 3 therefore approximates the low band better (12.1% vs 17.6% discarded on average), and the low band's tree is also shallow. Recommendation: **width 5 on a 1% cut-off of the learner's own rating band** - it discards 9.1% of the opponent's reply mass on average at >=1800 (worst single ply 14.8%) and keeps 30 leaf paths - and expose width 3 as the "main lines only" setting rather than the default, since it distorts Black's first move most (29% of surviving reply mass discarded there).

Caveat: one month of 2013 (121 k games, 9.5 k at >=1800) is a small sample. At the 0.2% cut-off a node needs only 19 games at >=1800, so the ply-8+ rows are single-game paths and their shares are noisy; the ply 2/4/6 numbers are solid. `both<1500` at the 0.2% cut-off is thinner still (19771 games, a 40-game threshold). A recent month (~90 M games) would firm the tail up and is the natural next step.

## Reproduction

The dump is CC0 and was deleted after the run; the script in [`refs/lichess/tree-width-analysis.py`](../../refs/lichess/tree-width-analysis.py) regenerates this whole file.

```sh
cd /home/anthony/pproj/chessop

# 1. dependencies (python-chess 1.11.2, zstandard 0.25.0)
uv venv /tmp/chessvenv
uv pip install --python /tmp/chessvenv/bin/python chess==1.11.2 zstandard

# 2. the 2013-01 standard rated dump: 17,761,302 bytes,
#    sha256 aa40b3671fa3cf1072eb182892cd90b0e1e003a4a5943492f64b77e7f3fd1635
curl -sSL -o refs/lichess/lichess_db_standard_rated_2013-01.pgn.zst \
    https://database.lichess.org/standard/lichess_db_standard_rated_2013-01.pgn.zst

# 3. tokenizer self-check: plain scanner vs chess.pgn.read_game
/tmp/chessvenv/bin/python refs/lichess/tree-width-analysis.py --verify 500 \
    refs/lichess/lichess_db_standard_rated_2013-01.pgn.zst

# 4. the measurement (8.3 s wall, 617 MB max RSS: three tries over 121,332 games)
/tmp/chessvenv/bin/python refs/lichess/tree-width-analysis.py \
    refs/lichess/lichess_db_standard_rated_2013-01.pgn.zst \
    docs/research/tree-width-measurements.md

# 5. do not keep the 17.8 MB dump in the repo
rm refs/lichess/lichess_db_standard_rated_2013-01.pgn.zst
```

Cross-checks: the per-bucket game counts (121,332 / 9,525 / 19,771), the pruned node counts by ply at every cut-off (1%, 0.2%) and the maximum plies (6, 8, 5 at 1%; 10, 18, 9 at 0.2%) reproduce `refs/lichess/dump-2013-01-tree-stats.txt` exactly. The tokenizer check found 499/500 identical move lists and one spelling-only difference.

