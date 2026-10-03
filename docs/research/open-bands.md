# Open rating bands (1200+, 1500+, 1800+) against the closed bands, on 2026-08

Question from the owner: what do repertoires built from **open-ended bands** look like (a game is kept when **both** players' ratings are >= the bound), with 1500+ as a candidate default, compared with the shipped closed bands of ADR 0003 (both players inside the same 300-wide band)?
Script: [`refs/lichess/open-bands-analysis.py`](../../refs/lichess/open-bands-analysis.py). Generated; every number below is one run of it (`build` then `report`). No recommendation is made here.

## Method and sample

- **Source**: `lichess_db_standard_rated_2026-08.pgn.zst` (30,145,862,359 bytes, CC0), streamed from `https://database.lichess.org/standard/` through the build's own HTTP reader and zstandard stream, nothing written to disk. Reading stopped when every band below was full: **1,474,213 games read, 482,230,272 compressed bytes (1.60 % of the file)**. Date range of the games read (`UTCDate UTCTime`): **2026.08.01 00:00:01 to 2026.08.01 13:15:03**.
- **Same code as the shipped build.** The script imports `chessop.build` (`_Http`, `_Counting`, the tokenizer and `_games` loop, `_band_graph`, `Snapshot`, `write_graph_file`, `load_book`) and `chessop.repertoire` unchanged. The only scratch piece is a `_Sample` subclass whose `band_of` applies the same ADR 0003 filters (ratings present and numeric, no `BOT` title, no Bullet/UltraBullet) and then returns **every** band that wants the game, so one game can feed several tries.
- **Bands built** (each its own trie, capped prefix of the stream, ply cap 36, storage cut-off 0.02 %):

  | band | kept when | cap |
  |---|---|---|
  | 1200+, 1500+, 1800+ | min(WhiteElo, BlackElo) >= bound | 150,000 |
  | 1500-1800, 1800-2100 | both players in the band (as shipped) | 150,000 |
  | 1500+@300k | both >= 1500 | 300,000 (its first 150,000 games are exactly 1500+'s) |
  | 1500+#2 | both >= 1500, only once 1500+ is full | 150,000 (the next, disjoint 150,000 games) |

- **Check against the shipped snapshot**: the 1500-1800 and 1800-2100 band documents this run wrote are identical (positions, edges, counts, names) to those in `src/chessop/data/snapshot.graph.json.gz`.
- **Repertoire**: `Repertoire(graph, Settings(band=...))` at the defaults (learner width 2, opponent width 3, popularity floor 0.02 % of the band's games, share 5 %, nothing opted out). "rep positions" / "max depth" are `build.repertoire_size` (the colour-neutral repertoire: top-3 plus share moves everywhere). **Per colour**: the positions a learner of that colour can reach, following the accepted set (`Repertoire.accepted`) at their turns and the drawable set (`Repertoire.drawable`) at the opponent's, stubs not followed; "learner positions" = positions of that colour with a non-stub move onward; depth = longest path.
- **Compressed bytes**: the band alone serialised as the graph file (`Snapshot.to_json`, compact JSON, gzip `mtime=0`), the same way `write_graph_file` writes the shipped file (945,694 bytes for all five shipped bands).
- **Composition** (open bands only): each kept game counted by the **lower** player's rating in 300-wide buckets aligned with the shipped edges (1200-1499, 1500-1799, 1800-2099, 2100-2399, 2400-2699, 2700+); **cross-bucket** = the two players in different 300-wide buckets; **cross-band** = the two players in different shipped bands (the games the closed bands drop; differs from cross-bucket only above 2100, where the shipped 2100+ band is open).
- **Main-move comparison**: over positions in both repertoires, at shortest depth <= 8 plies in the first-named band's repertoire, the main-move set (`Repertoire.main_moves`: top-3 by count plus every edge with >= 5 % of the position's pooled games, above the floor; stubs included) and the top main move are compared. Shares are the edge's pooled count over the position's pooled count at that band. The tables list positions reached by >= 1 % of the first band's games; the summary counts all shared positions, and **traffic-weighted** = the share of the pooled counts of shared positions held by the differing ones.
- **Cost**: `/usr/bin/time -v` and `/proc/self/status`. A baseline run of the unmodified five-band `build_snapshot` on the same URL ran concurrently on another core (the machine was otherwise idle).

## 1. Games kept, prefix length, composition

Every band reached its cap; the stream stopped when 1800-2100 did. "Games read" counts every game in the stream up to the one that filled the band (all speeds, before filters).

| band | games kept | games read when full | compressed bytes when full | % of the file | last game kept (UTC, 2026-08-01) | games refused as the band was full |
|---|---|---|---|---|---|---|
| 1200+ | 150,000 | 347,416 | 112,992,256 | 0.37 % | 04:27:00 | 520,607 |
| 1500+ | 150,000 | 489,231 | 158,867,456 | 0.53 % | 06:03:33 | 318,907 |
| 1500+@300k | 300,000 | 957,294 | 312,090,624 | 1.04 % | 09:52:33 | 168,907 |
| 1500+#2 (games 150,001-300,000 of 1500+) | 150,000 | 957,294 | 312,090,624 | 1.04 % | 09:52:33 | 168,907 |
| 1800+ | 150,000 | 1,045,176 | 340,926,464 | 1.13 % | 10:29:20 | 63,542 |
| 1500-1800 | 150,000 | 1,045,546 | 341,057,536 | 1.13 % | 10:29:30 | 64,825 |
| 1800-2100 | 150,000 | 1,474,213 | 482,230,272 | 1.60 % | 13:15:03 | 0 |

For reference, the shipped five-band build (re-run here, see §5) reads 4,769,401 games / 1,568,972,800 bytes (5.20 %), 2100+ being the last band to fill. Games dropped by the filters over the 1,474,213 read: bullet or ultrabullet 637,928, BOT title 6,683; 413,428 further games passed the filters but went into no band (below every bound, split across closed bands and not >= the open bound, or every band wanting them full).

Rating composition of each open band's sample (share of kept games):

| band | lower player 1200-1499 | 1500-1799 | 1800-2099 | 2100-2399 | 2400-2699 | 2700+ | cross-bucket (300-wide) | cross-band (shipped bands; dropped by the closed bands) | rating gap 100-199 | gap >= 200 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1200+ | 30.2 % | 37.7 % | 25.7 % | 5.7 % | 0.5 % | 0.0 % | 15.6 % | 15.1 % | 8.4 % | 4.6 % |
| 1500+ | - | 54.2 % | 36.9 % | 8.2 % | 0.7 % | 0.0 % | 13.6 % | 12.9 % | 8.9 % | 3.7 % |
| 1800+ | - | - | 79.5 % | 18.5 % | 2.0 % | 0.0 % | 11.1 % | 9.2 % | 11.3 % | 2.4 % |
| 1500+@300k | - | 54.4 % | 36.3 % | 8.4 % | 0.9 % | 0.0 % | 13.8 % | 12.9 % | 9.0 % | 3.7 % |
| 1500+#2 | - | 54.6 % | 35.7 % | 8.6 % | 1.0 % | 0.0 % | 13.9 % | 13.0 % | 9.0 % | 3.8 % |

So 1500+ is roughly half 1500-1800-level games and half 1800+-level games (45.8 % of games have the lower player at 1800 or above). Speeds: 1200+ Blitz 74.5 % / Rapid 24.5 % / Classical 0.9 % / Correspondence 0.2 %; 1500+ 76.9 / 22.1 / 0.8 / 0.2; 1800+ 81.4 / 17.8 / 0.6 / 0.2.

## 2. Repertoire and snapshot size per band (default settings)

| band | games | stored positions | stored edges | compressed bytes (band alone) | repertoire positions | repertoire max depth | White: positions | White: learner positions | White: max depth | Black: positions | Black: learner positions | Black: max depth |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1200+ | 150,000 | 4,766 | 4,528 | 178,354 | 2,735 | 17 | 2,620 | 815 | 17 | 2,712 | 848 | 17 |
| **1500+** | 150,000 | 5,002 | 4,738 | 190,099 | 2,945 | 17 | 2,779 | 907 | 17 | 2,916 | 938 | 17 |
| 1800+ | 150,000 | 5,568 | 5,280 | 219,852 | 3,191 | 22 | 3,031 | 1,035 | 22 | 3,149 | 1,071 | 22 |
| 1500-1800 (shipped) | 150,000 | 4,702 | 4,451 | 170,641 | 2,695 | 17 | 2,573 | 795 | 17 | 2,685 | 820 | 17 |
| 1800-2100 (shipped) | 150,000 | 5,260 | 5,022 | 202,716 | 3,074 | 21 | 2,893 | 965 | 21 | 3,042 | 990 | 21 |
| 1500+@300k | 300,000 | 4,937 | 4,674 | 189,666 | 2,890 | 17 | 2,723 | 894 | 17 | 2,863 | 914 | 17 |
| 1500+#2 | 150,000 | 5,080 | 4,812 | 192,702 | 2,956 | 19 | 2,784 | 912 | 19 | 2,931 | 945 | 19 |

No band drops an edge closing a cycle or a SAN token. Each open band's repertoire sits between the closed band at its bound and the next one up: 1500+ (2,945 positions) is 9 % larger than 1500-1800 (2,695) and 4 % smaller than 1800-2100 (3,074).

## 3. 1500+ against 1500-1800 and 1800-2100

Overlap of repertoire positions (shared; only in the first; only in the second; Jaccard):

| pair | colour-neutral repertoire | White | Black |
|---|---|---|---|
| 1500+ vs 1500-1800 | 2,225; 720; 470; **J = 0.65** | 2,122; 657; 451; 0.66 | 2,194; 722; 491; 0.64 |
| 1500+ vs 1800-2100 | 2,543; 402; 531; **J = 0.73** | 2,401; 378; 492; 0.73 | 2,515; 401; 527; 0.73 |
| 1500-1800 vs 1800-2100 | 1,964; 731; 1,110; J = 0.52 | 1,857; 716; 1,036; 0.51 | 1,935; 750; 1,107; 0.51 |
| 1200+ vs 1500+ | 2,500; 235; 445; J = 0.79 | 2,375; 245; 404; 0.79 | 2,469; 243; 447; 0.78 |
| 1500+ vs 1800+ | 2,316; 629; 875; J = 0.61 | 2,269; 510; 762; 0.64 | 2,289; 627; 860; 0.61 |
| 1800+ vs 1800-2100 | 2,573; 618; 501; J = 0.70 | 2,549; 482; 344; 0.76 | 2,542; 607; 500; 0.70 |
| 1500+ vs 1500+#2 (sampling noise, §4) | 2,563; 382; 393; J = 0.77 | 2,415; 364; 369; 0.77 | 2,538; 378; 393; 0.77 |

Main-move differences at positions both repertoires hold:

| pair | depth | shared positions | main-move set differs | top move differs | traffic-weighted: set differs | traffic-weighted: top differs | positions >= 1 % of games: shared / set differs / top differs |
|---|---|---|---|---|---|---|---|
| 1500+ vs 1500-1800 | <= 8 | 1,663 | 523 | 305 | 20.3 % | 5.9 % | 65 / 17 / 3 |
| 1500+ vs 1500-1800 | all | 2,225 | 688 | 442 | 21.0 % | 6.9 % | 65 / 17 / 3 |
| 1500+ vs 1800-2100 | <= 8 | 1,733 | 426 | 237 | 19.4 % | 4.1 % | 64 / 13 / 3 |
| 1500+ vs 1800-2100 | all | 2,543 | 590 | 364 | 19.6 % | 4.6 % | 64 / 13 / 3 |
| 1500-1800 vs 1800-2100 | <= 8 | 1,463 | 646 | 383 | 29.0 % | 8.2 % | 58 / 20 / 5 |
| 1500+ vs 1500+#2 (noise) | <= 8 | 1,789 | 394 | 226 | 14.5 % | 3.4 % | 65 / 12 / 2 |

Most set differences are a fourth or fifth move crossing the 5 % share line (e.g. `Bc4 5 %`); the top move differs at 3 of the 64-65 positions reached by >= 1 % of 1500+ games in each comparison with 1500+ (listed below: `1. d4 Nf6 2. Bf4`, `1. d4 d5 2. Nf3 Nf6` and `3. Bb5` of the Ruy Lopez against 1500-1800; `1. d4 Nf6 2. Bf4`, the French `3.` move and the Scandinavian `3... Qd8`/`Qa5` against 1800-2100). The start position's main moves are e4, d4, c4 in all three bands (1500+ 59 / 27 / 4 %, 1500-1800 62 / 25 / 3 %, 1800-2100 58 / 28 / 4 %; 1800+ has Nf3 5 % third instead of c4). At `1. d4`, 1500+ (d5 41 %, Nf6 24 %) is close to 1800-2100 (d5 39 %, Nf6 26 %) and away from 1500-1800 (d5 47 %, Nf6 16 %).

### 1500+ vs 1500-1800: positions at <= 8 plies reached by >= 1 % of 1500+ games whose main moves differ

| ply | line | games reaching (in 1500+) | 1500+ main moves (share) | 1500-1800 main moves (share) | top move differs |
|---|---|---|---|---|---|
| 2 | `1. e4 e6` | 6.5% | d4 50%, Nf3 25%, Nc3 6%, f4 6% | d4 43%, Nf3 30%, f4 6%, Nc3 6%, Bc4 5% |  |
| 2 | `1. e4 c6` | 5.8% | d4 50%, Nf3 25%, Nc3 7%, f4 5% | d4 43%, Nf3 29%, Bc4 8%, Nc3 6%, f4 6% |  |
| 3 | `1. e4 c5 2. Nf3` | 6.9% | Nc6 42%, d6 30%, e6 19%, g6 5% | Nc6 47%, d6 27%, e6 17% |  |
| 3 | `1. e4 e6 2. d4` | 3.6% | d5 73%, c5 6%, d6 5% | d5 64%, c5 8%, d6 6%, c6 6%, b6 6% |  |
| 3 | `1. d4 d5 2. Nf3` | 2.5% | Nf6 34%, e6 16%, Nc6 16%, Bf5 10%, c6 8%, c5 7%, Bg4 5% | Nf6 28%, Nc6 23%, e6 16%, Bf5 12%, Bg4 7%, c5 5% |  |
| 3 | `1. e4 e6 2. Nf3` | 1.7% | d5 66%, c5 8%, c6 5%, b6 5% | d5 58%, c5 8%, b6 7%, c6 7%, d6 6% |  |
| 3 | `1. d4 Nf6 2. Nf3` | 1.4% | g6 33%, e6 25%, d5 23%, d6 7%, c5 7% | g6 31%, d5 26%, e6 25%, d6 7% |  |
| 3 | `1. e4 c5 2. Nc3` | 1.2% | Nc6 45%, e6 22%, d6 21%, g6 6% | Nc6 48%, d6 21%, e6 20% |  |
| 3 | `1. d4 Nf6 2. Bf4` | 1.0% | d5 25%, g6 22%, e6 20%, d6 16%, c5 11% | g6 25%, d5 24%, e6 22%, d6 15%, c5 8% | yes |
| 3 | `1. d4 d5 2. e3` | 1.0% | Nf6 32%, e6 17%, Nc6 15%, Bf5 14%, c6 8%, c5 7% | Nf6 29%, e6 19%, Nc6 17%, Bf5 15%, c5 7% |  |
| 4 | `1. e4 c6 2. d4 d5` | 2.9% | e5 36%, exd5 30%, Nc3 22%, Nd2 5% | e5 43%, exd5 29%, Nc3 19% |  |
| 4 | `1. e4 e6 2. d4 d5` | 2.7% | e5 34%, exd5 30%, Nc3 22%, Nd2 10% | e5 42%, exd5 34%, Nc3 16% |  |
| 4 | `1. d4 d5 2. Nf3 Nf6` | 1.2% | Bf4 27%, e3 24%, c4 18%, g3 10%, Bg5 9% | e3 28%, Bf4 24%, c4 12%, Bg5 9%, g3 9%, Nc3 8% | yes |
| 5 | `1. e4 e5 2. Nf3 Nc6 3. Bc4` | 3.9% | Bc5 35%, Nf6 33%, h6 11%, d6 6%, Be7 5% | Bc5 33%, Nf6 31%, h6 14%, d6 7% |  |
| 5 | `1. e4 e5 2. Nf3 Nc6 3. Bb5` | 1.9% | a6 29%, d6 24%, Nf6 14%, Bc5 14%, Nge7 6% | d6 29%, a6 20%, Nf6 16%, Bc5 13%, Nge7 7%, Nd4 5% | yes |
| 5 | `1. e4 c5 2. Nf3 Nc6 3. d4` | 1.3% | cxd4 96% | cxd4 93%, e6 3% |  |
| 5 | `1. e4 e6 2. d4 d5 3. e5` | 1.0% | c5 87%, Nc6 2%, Bd7 2% | c5 82%, Nc6 5%, a6 2% |  |
| 6 | `1. e4 c5 2. Nf3 d6 3. d4 cxd4` | 1.1% | Nxd4 89%, Qxd4 5%, c3 4% | Nxd4 89%, Qxd4 6% |  |

### 1500+ vs 1800-2100: the same

| ply | line | games reaching (in 1500+) | 1500+ main moves (share) | 1800-2100 main moves (share) | top move differs |
|---|---|---|---|---|---|
| 1 | `1. d4` | 27.0% | d5 41%, Nf6 24%, e6 9%, e5 5% | d5 39%, Nf6 26%, e6 9% |  |
| 3 | `1. e4 c5 2. Nf3` | 6.9% | Nc6 42%, d6 30%, e6 19%, g6 5% | Nc6 44%, d6 29%, e6 19% |  |
| 3 | `1. d4 d5 2. Nf3` | 2.5% | Nf6 34%, e6 16%, Nc6 16%, Bf5 10%, c6 8%, c5 7%, Bg4 5% | Nf6 36%, e6 16%, Nc6 12%, c6 10%, Bf5 10%, c5 7% |  |
| 3 | `1. e4 e6 2. Nf3` | 1.7% | d5 66%, c5 8%, c6 5%, b6 5% | d5 71%, c5 9%, d6 5% |  |
| 3 | `1. d4 Nf6 2. Bf4` | 1.0% | d5 25%, g6 22%, e6 20%, d6 16%, c5 11% | e6 24%, d5 22%, g6 20%, d6 16%, c5 12% | yes |
| 4 | `1. e4 e6 2. d4 d5` | 2.7% | e5 34%, exd5 30%, Nc3 22%, Nd2 10% | exd5 31%, e5 30%, Nc3 23%, Nd2 11% | yes |
| 4 | `1. e4 e5 2. Nf3 d6` | 2.1% | Bc4 42%, d4 34%, Nc3 10%, h3 5% | Bc4 43%, d4 39%, Nc3 7% |  |
| 5 | `1. e4 e5 2. Nf3 Nc6 3. Bc4` | 3.9% | Bc5 35%, Nf6 33%, h6 11%, d6 6%, Be7 5% | Bc5 39%, Nf6 33%, h6 6%, Be7 6%, d6 6%, f5 5% |  |
| 5 | `1. e4 e5 2. Nf3 Nc6 3. Bb5` | 1.9% | a6 29%, d6 24%, Nf6 14%, Bc5 14%, Nge7 6% | a6 34%, d6 20%, Bc5 16%, Nf6 14% |  |
| 5 | `1. e4 d5 2. exd5 Qxd5 3. Nc3` | 1.8% | Qd8 39%, Qa5 38%, Qe5+ 8%, Qd6 8%, Qe6+ 7% | Qa5 44%, Qd8 38%, Qd6 9%, Qe5+ 5% | yes |
| 5 | `1. e4 e6 2. d4 d5 3. e5` | 1.0% | c5 87%, Nc6 2%, Bd7 2% | c5 90% |  |
| 6 | `1. e4 e5 2. Nf3 Nc6 3. d4 exd4` | 1.7% | Nxd4 56%, Bc4 29%, c3 8%, Ng5 6% | Nxd4 57%, Bc4 31%, c3 8% |  |
| 6 | `1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5` | 1.4% | c3 32%, O-O 22%, d3 18%, Nc3 10%, b4 8%, d4 5% | c3 35%, O-O 25%, d3 15%, b4 9%, Nc3 8% |  |
| 7 | `1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4` | 1.2% | e5 27%, g6 22%, Nf6 20%, e6 10%, d6 9%, Nxd4 5% | e5 30%, g6 21%, Nf6 20%, e6 12%, d6 8% |  |
| 7 | `1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4` | 1.0% | Nf6 78%, Nc6 8%, e5 5% | Nf6 77%, Nc6 8%, a6 5% |  |

## 4. Is 150,000 games a fair sample for 1500+?

Two comparisons: 1500+ against **1500+@300k** (the same first 150,000 games plus the next 150,000, so the two overlap by half), and against **1500+#2** (the next 150,000 games alone: a disjoint sample of the same population, 06:03 to 09:52 UTC instead of 00:00 to 06:03, with the same rating and speed composition, §1). The popularity floor and storage cut-off are shares of the band's games, so doubling the sample raises the floor from 30 to 60 games and does not grow the repertoire.

| comparison | repertoire positions | shared; only left; only right | Jaccard | shared positions <= 8 plies: set differs / top differs | traffic-weighted set / top differs (<= 8) | same, all depths | positions >= 1 % of games: set / top differs |
|---|---|---|---|---|---|---|---|
| 1500+ vs 1500+@300k | 2,945 vs 2,890 | 2,711; 234; 179 | 0.87 | 226 / 126 of 1,885 | 8.6 % / 1.9 % | 8.9 % / 2.2 % | 8 / 1 of 65 |
| 1500+ vs 1500+#2 (disjoint) | 2,945 vs 2,956 | 2,563; 382; 393 | 0.77 | 394 / 226 of 1,789 | 14.5 % / 3.4 % | 15.0 % / 4.1 % | 12 / 2 of 65 |
| 1500+@300k vs 1500+#2 | 2,890 vs 2,956 | 2,737; 153; 219 | 0.88 | - | - | - | - |
| for scale: 1500+ vs 1800-2100 | 2,945 vs 3,074 | 2,543; 402; 531 | 0.73 | 426 / 237 of 1,733 | 19.4 % / 4.1 % | 19.6 % / 4.6 % | 13 / 3 of 64 |
| for scale: 1500+ vs 1500-1800 | 2,945 vs 2,695 | 2,225; 720; 470 | 0.65 | 523 / 305 of 1,663 | 20.3 % / 5.9 % | 21.0 % / 6.9 % | 17 / 3 of 65 |

Per colour the Jaccard indices are the same to 0.01 (1500+ vs 1500+#2: White 0.77, Black 0.77; vs 1500+@300k: 0.87 / 0.87). Among positions reached by >= 1 % of games, the one top-move change between 150k and 300k is the Scandinavian `1. e4 d5 2. exd5 Qxd5 3. Nc3` (Qd8 39 % / Qa5 38 % at 150k; Qa5 39 % / Qd8 37 % at 300k); between the two disjoint halves, that one and `1. d4 Nf6 2. Bf4` (d5 25 % / g6 22 % / e6 20 %; g6 23 % / e6 22 % / d5 21 %). The other set changes at >= 1 % are moves at 5-6 % crossing the 5 % share line.

Two disjoint 150k samples of 1500+ disagree on about a quarter of the repertoire's positions (J = 0.77), nearly as much as 1500+ disagrees with 1800-2100 (J = 0.73) and less than with 1500-1800 (J = 0.65); the disagreement sits in the low-traffic tail (traffic-weighted 3-4 % of the shared positions' games change top move, against 4-6 % between bands). The same measurement was not made for the closed bands, which are 150k samples of narrower populations.

## 5. Build cost

| run | tries | trie nodes after the stream | games read | wall time | CPU (user) | peak RSS |
|---|---|---|---|---|---|---|
| shipped `build_snapshot`, 5 closed bands (baseline, this machine) | 5 × 150k | - | 4,769,401 | 9 min 05 s | 540 s | 7,854 MB |
| this script, 7 tries | 6 × 150k + 1 × 300k | 31,896,945 | 1,474,213 | 13 min 24 s | 798 s | 11,030 MB |

Per band in this script: the stream and all seven tries took **53 s** (reading stopped at 1,474,213 games); RSS after the stream **8,209 MB** for 31.9 M trie nodes (about 270 bytes per node, so about **1.0 GB per 150k-game trie**: 4.01 M nodes for 1200+, 4.02 M for 1500+, 3.99 M for 1800+, 4.01 M and 4.00 M for the closed bands, 7.87 M for 1500+@300k); `_band_graph` (keying, pooling, cut, acyclic, repertoire diagnostics) **90.8-98.6 s per 150k band** (1200+ 91.7 s, 1500+ 91.5 s, 1800+ 90.8 s) and 184.1 s for the 300k band. The two runs shared the machine on separate cores.

What adding 1200+, 1500+ and 1800+ to the shipped five bands would cost, from these measurements (an estimate, not a run): no extra reading (all three fill by 1,045,176 games; the shipped build reads 4,769,401 for 2100+); about **+3 GB peak** (three more ~1 GB tries alive at the end of the stream, so about 11 GB); about **+4.5 min** of graph building (3 × ~91 s, so about 14 min instead of 9); and **+588,305 compressed bytes** of snapshot (178,354 + 190,099 + 219,852), about 1.53 MB instead of 945,694 bytes. A 1500+ band at 300,000 games costs about 2 GB of trie and 184 s, and a 190 KB snapshot band (the same as at 150k).
