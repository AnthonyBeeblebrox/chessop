# Transpositions: how many positions in the repertoire are reachable by more than one move order?

Type: research
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

How prevalent are transpositions in the repertoire the app will actually drill, so ticket 11 can decide whether a branch is a move sequence or a position without guessing?

Using the settings settled in ticket 05 — the learner's band (report `both>=1800`, `both<1500` and all games), an absolute cut-off of 0.2% of the band's games, and widths `(width_player, width_opponent)` of `(3,3)` — measure:

- How many distinct positions in the tree are reachable by more than one move order, and what share of the tree's nodes and leaf paths that is.
- At which plies transpositions first appear and how the count grows with depth.
- How much position-keying would merge: tree size (nodes and leaf paths) as a move-sequence tree versus as a position-keyed DAG, and the size of the largest merged group.
- Of the positions reachable by more than one path, in what share does the learner's *side* differ between the paths (learner as White on one, Black on the other) — this decides whether a position key must carry the learner's colour.
- Whether the CC0 `chess-openings` TSV's `epd`/`uci` columns (`refs/lichess/chess-openings-*.tsv`) give a usable position key for the nodes that carry a name, and how many tree nodes are unnamed.

Write findings to `docs/research/transpositions.md`, with the exact commands so the numbers are reproducible. Extend or reuse `refs/lichess/tree-width-analysis.py` if that is the shortest path; the Lichess 2013-01 dump is not in the repo and must be re-downloaded to `refs/lichess/` (about 17.8 MB) and deleted afterwards.

AFK. Do not modify `.scratch/` or `CONTEXT.md`.

## Answer

Measured on the Lichess 2013-01 dump with ticket 05's settings (absolute 0.2% cut-off, widths (3,3) so k=3); full tables, definitions and commands in [docs/research/transpositions.md](../../../docs/research/transpositions.md), script `refs/lichess/transposition-analysis.py`.

- **Prevalence (`both>=1800`)**: the 235-node / 86-leaf-path tree has 216 distinct positions; **17 positions are reachable by more than one move order** (7.9% of positions), made of 36 nodes (15.3% of the tree). 14 of 86 leaf paths (16.3%) end on a shared position and **35 (40.7%) pass through one**. Uncapped: 31 of 417 positions, 62 of 175 leaf paths. Other bands are far lower: `all` 5 of 133 positions (10 nodes, 7.2%), `both<1500` 3 of 129 (6 nodes, 4.5%).
- **Depth**: first transposition at ply 3 (`Nf3 Nf6 d4` = `d4 Nf6 Nf3`); new shared positions at plies 3-8 only (2, 5, 4, 3, 2, 1), none at ply 9+ where the tree is a single path.
- **Largest group**: 3 move orders at k=3 (QGD Normal Defense `d4 d5 c4 e6 Nc3 Nf6`; Semi-Slav accelerated `d4 d5 c4 e6 Nc3 c6`), 4 uncapped (the Semi-Slav position via every kept `c6/e6/d5` permutation). All groups are `d4`-family or `e4 e6` / `e4 c5` move-order families.
- **What position-keying merges**: 235 nodes / 234 edges -> 216 positions / 226 edges (-8.1%); 86 leaf paths -> 75 leaf positions but 112 root-to-leaf paths, because **14 of the 17 groups keep different replies under different move orders** (the sequence tree drills one position to different depths depending on how it was reached). A build that pools counts per position before the cut-off gives 268 positions / 187 paths: 53 positions qualify only once their move orders are added together.
- **Learner's side**: side to move is in the EPD and **0 groups span more than one ply**, so no pair of paths to one position differs in side to move. Whose order differs: Black's moves only in 12 of 17 groups, White's only in 5, both in 0 (uncapped 24 / 6 / 1). A key needs the learner's colour only because the app drills both colours over one tree (state as White != state as Black), not to tell paths apart.
- **Names**: the `chess-openings` `dist` `epd` column is a usable key (3,810 rows, 3,810 distinct EPDs, replaying `uci` reproduces `epd` in all rows). 159 of 235 nodes (67.7%) are named by exact EPD, 76 unnamed (root + 75 at plies 3-17, mostly 4-9); every non-root node has a named ancestor; 20 named nodes are reached by a non-TSV move order; 11 of 17 shared positions are named.
