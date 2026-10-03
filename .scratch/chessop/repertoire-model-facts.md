# Repertoire model facts: position-keyed DAG from a line set

Measured with python-chess 1.11.2; scripts in `/tmp/repmodel/` (scratch); every number below measured.
Node key = `chess.Board.epd()` (placement + side to move + castling + en-passant; clocks omitted, which is
right for merging). Data: `refs/lichess/chess-openings-{a..e}.tsv` (3,810 rows, 0 unparsable, 0 dups).
**A** = all named lines. **B** = synthetic repertoire: names starting `Sicilian Defense` / `French Defense` /
`Queen's Gambit Declined` = 801 lines (Sicilian 391, French 212, QGD 198; 0 cross-family first moves).

## 1. Graph shape, out-degree, transpositions

| metric | A (named) | B (3 families) |
|---|---|---|
| lines / positions (nodes) / edges | 3,810 / 7,855 / 8,058 | 801 / 1,710 / 1,753 |
| leaf positions (line endpoints) | 3,810 | 801 |
| leaf positions that also have children | 1,433 (37.6%) | 314 (39.2%) |
| nodes with out-degree 0 | 2,377 (30.3%) | 487 (28.5%) |
| leaf ply min / median / max | 1 / 10 / 36 | 3 / 11 / 28 |
| EPD collisions within one line | 0 | 0 |
| positions reachable by >1 line | 2,809 (35.8%) | 639 (37.4%) |
| positions with >1 distinct parent | 192 (2.4%) | 42 (2.5%) |
| max distinct parents at a node | 3 | 3 |
| nodes whose leaf-set exceeds their line count | 889 | 211 |

Out-degree (book moves at a position); **A** 0:2,377 | 1:4,216 | 2:710 | 3:270 | 4:131 | 5:60 | 6:28 |
7:19 | 8:10 | 9:9 | 10:12 | 11–15:6 | 17:1 | 18:1 | 19:3 | **20:2**.
**B** 0:487 | 1:945 | 2:168 | 3:58 | 4:21 | 5:14 | 6:8 | 7:2 | 8:1 | 9:1 | 10:2 | 12:1 | 13:1 | **20:1**.
Highest out-degree: A start position 20 (ply 0), `1.e4 c5` 20 (ply 2), `1.Nf3`/`1.e4`/`1.e4 e5` 19;
B `1.e4 c5` 20, `1.e4 c5 Nf3` 13, `1.e4 e6` 12. A has 151 positions with ≥5 book moves, 25 with ≥10;
B has 31 and 5. The maximum is always "every known move at a fork", not a repertoire-sized choice.
Merging is real but shallow: only 2.4% of nodes have multiple parents, while 35.8% sit on >1 line
because rows can share a sequence after an earlier divergence (sibling-line case).

## 2. Role checks — what holds, what breaks

| check | A | B |
|---|---|---|
| line moves missing as DAG edges | 0 | 0 |
| non-terminal positions with 0 book moves | 0 | 0 |
| positions where White / Black to move has 0 book moves | 0 / 0 | 0 / 0 |
| illegal child edges (move illegal at node) | 0 | 0 |
| leaf positions interior to another line | 1,433 | 314 |

**(a) holds structurally**: every child edge is legal, every non-terminal node has ≥1 book move for
whichever side is to move, every line replay is edge-consistent. But the line set is enough only for
"which moves are book here", not "which is the learner's": side to move is in the EPD, yet nothing
records *which* sibling move the learner owns. At `1.e4 c5` (d=20) it cannot say whether the learner
is the Sicilian player facing 20 replies or one of the 20 replies. Mapping gap, not a crash.

**"Leaf" is unstable**: 1,433/3,810 (37.6%) of leaves also have children in another line (`1.e4 c5`
ends the `Sicilian Defense` row and is interior to 391 others). "Leaf ⇒ opponent has no book reply"
is false for 37.6% of leaves, so round termination is line-set dependent.

## 3. Naive leaf-set propagation: overlap bug, memory, scaling
| leaf-set propagation | A | B |
|---|---|---|
| max leaf-set size | 3,810 (at the start) | 801 (at the start) |
| mean leaf-set size | 7.3 | 8.2 |
| total (node, leaf) entries | 56,963 | 13,977 |
| memory: pickle / raw `sys.getsizeof` | 0.2 / 3.9 MiB | 0.03 / 0.9 MiB |
| bytes per node / propagation wall time | 26 / <1 s | 28 / <1 s |
| branching nodes with overlapping child leaf-sets | 119 / 1,262 | 30 / 278 |
| spurious (leaf, edge) pairs from merging | 7,371 (15.0%) | 1,524 (14.6%) |

**The bug**: EPD merging makes sibling subtrees stop partitioning the leaves. At A's start the child
leaf-set sizes sum to **5,349** but their union is **3,810** — 1,539 (40%) of per-edge probability
mass is double-counted (a leaf counted under both `1.e4` and `1.d4`). Weights summed per edge total
1.40 at the root, so normalised reply-sampling is not the intended per-leaf distribution. Example:
`1.d4` has 197 reachable leaves, but children `1...d5`, `1...Nf6`, `1...e6` have leaf-sets 195, 145,
1 (sum 341). A **line-keyed prefix tree with no merging has zero overlap**: A needs 8,653 nodes
(+10%) but only 40,735 entries (−28%).

Scaling (structural trees, measured): 59,049 leaves/88,573 nodes → 649,539 entries, 2.7 MiB pickled;
1.59 M/2.39 M → 22.3 M entries, 115 MiB, 9 s; 14.3 M/21.5 M → 229.6 M entries, 1,177 MiB, 110 s.
Entries ≈ leaves × mean depth (~5.4 B/entry pickled, ~10 entries/node). On the real 1800+ pruned
repertoire in `repertoire-size-facts.md` (1% cutoff; 130,569 nodes, 8,944 leaves) that is ≈4.6 M
entries ≈ **25 MiB pickled / 320 MiB as raw sets** — viable, but it must be re-propagated whenever a
per-leaf weight changes.

## 4. Weighted opponent sampling: fidelity and popularity
Target = random per-leaf weight vector (the app's sampling weight is per branch-leaf, decreasing with
success). Mean total-variation distance over branching positions, 0 = exact: A: uniform replies
**0.377**, reply ∝ leaf-set size **0.261**, reply ∝ summed per-leaf weights **0.192**; B: 0.385 /
0.259 / 0.196. The third scheme is exact only when leaf sets partition — the residual 0.19 *is* the
merge overlap. **A position-keyed DAG with static edge weights cannot reproduce the required
distribution once weights live on leaves.** Leaf count is also not popularity: real frequencies in
`dump-2013-01-tree-stats.txt` (121,332 games; 1800+ bucket) give `1...c5` 14.9%, `1...e5` 11.7%,
`1...e6` 10.1%, while named-line leaf counts in B give `1...e6` **35.2%** of `1.e4` (French
over-weighted ~3.5×) merely because the ECO set names more French variations.

## Failure modes (numbers)

1. Leaf ambiguity: 1,433/3,810 (37.6%) leaf positions are interior to other lines.
2. Sibling leaf-set overlap: 119 branching nodes in A double-count; root mass reaches 1.40×, not 1.0×.
3. No role ownership: 151 positions have ≥5 book moves for one side with no learner/opponent split;
   20 book first moves for White at the root.
4. No popularity in the line set: named-line share vs observed frequency differ ~3.5× (`1...e6`).
5. Dynamic weights: per-leaf weights change after every round; static edge weights go stale and
   materialised leaf sets need re-propagating (≈4.6 M entries for a real 8,944-leaf repertoire).
6. Stub branches: median leaf ply 10–11 vs longest lines 28–36; naive leaf sampling favours short
   named stubs unless the repertoire is depth-closed.

## Recommendation
**Not sufficient as proposed**: a position-keyed DAG with edge weights and no leaf sets answers (a)
and gives the graph for (b), but fails (c) — 14.6–15% of sibling (leaf, edge) pairs are spurious
under EPD merging, so a normalised reply distribution is not derivable from static weights, and the
weight is a per-leaf learner-history quantity that changes after every round.
**Minimal sufficient representation** (all rebuildable from the line set except the weights):
1. `lines`: ordered move sequences; plus a **line-keyed trie** (node = sequence prefix, no EPD
   merging) storing `children: uci → node` and `is_line_end`: A 8,653 nodes, B 1,966.
2. `learner_move[node]`: the learner's one book move per position (a repertoire attribute, not
   derivable from counts); colour follows side to move.
3. `line_id` per line end and `weight[line_id]` — the "sampling weight" from `CONTEXT.md`, ≥1,
   decreasing with success; one integer per leaf.
4. Opponent reply weight at a position = Σ `weight[leaf]` over leaves whose sequence continues with
   that move, computed on demand over the ≤20 children and memoised per node with a weight-version
   stamp — O(depth) per sample, no leaf-set storage (eager materialisation ≤5.4 B/entry is possible
   but is O(nodes × leaves) to maintain).
5. Seed the initial opponent distribution from real frequencies (Lichess explorer), never from the
   ECO name set. Keep the merged EPD DAG only as an optional "seen this position / is my move
   legal" lookup — never as the carrier of branch identity or sampling weight.
