# Repertoire-size facts
Measured: the count of distinct positions (EPD-keyed, transpositions merged) in a game-share-pruned move-frequency tree from the local Lichess 2013-01 PGN dump, plus the position/ply structure of the 3,810-line lichess `chess-openings` ECO set — every number below is a measured count, not an estimate.

## A. Lichess 2013-01 PGN dump -> pruned opening tree
- Dump: `/tmp/lichessdump/lichess_db_standard_rated_2013-01.pgn.zst` (17,761,302 bytes, valid zstd, decompressed with `zstdcat`).
- Script: `/tmp/repertoire_tree.py` (run as `uv run --offline --no-project --with chess python /tmp/repertoire_tree.py`).
- Parsed 121,332 games; 0 unparsed, 0 non-standard starts (no FEN/SetUp); 218 games have no Elo.
- `both1800` = 9,525 games with WhiteElo >= 1800 AND BlackElo >= 1800; `all` = 121,332 games.
- Node = distinct position, key = `chess.Board.epd()` (en passant only if legal); transpositions merged. Games walked to ply 24.
- Raw distinct positions with no pruning at all: `all` 1,774,426; `both1800` 139,437.
- Two pruning semantics are given because they differ by ~4 orders of magnitude.
```
mode=parent   : edge kept iff games(playing this move at parent) / games(reaching parent) >= cutoff
mode=absolute : edge kept iff games(playing this move at parent) / games(in bucket)        >= cutoff
columns <=8 <=12 <=16 <=20 = cumulative node count when additionally capping depth (ply)
mode   cutoff filter     nodes    leaves maxply     <=8     <=12     <=16      <=20   ply bands 0-4/5-8/9-12/13-16/17-20/21-24
parent 1.0%   all      1,618,271  110,728    28   93,383  375,604   770,659  1,194,958  3229/90154/282221/395055/424299/423275
parent 0.5%   all      1,694,312  114,879    28  106,439  404,675   815,711  1,255,715  4600/101839/298236/411036/440004/438583
parent 0.2%   all      1,741,380  117,387    28  115,579  423,640   844,337  1,293,720  5803/109776/308061/420697/449383/447648
parent 0.1%   all      1,761,327  118,431    26  120,099  432,174   856,786  1,309,983  6639/113460/312075/424612/453197/451342
parent 0.05%  all      1,768,340  118,797    26  121,852  435,303   861,247  1,315,737  7020/114832/313451/425944/454490/452601
parent 0.02%  all      1,772,609  119,017    24  123,007  437,294   864,033  1,319,279  7310/115697/314287/426739/455246/453330
parent 1.0%   1800+      130,569    8,944    24    9,853   31,566    61,775     95,675  873/8980/21713/30209/33900/34894
parent 0.5%   1800+      136,075    9,217    24   11,071   33,842    65,117    100,099  1162/9909/22771/31275/34982/35976
parent 0.2%   1800+      137,828    9,300    24   11,510   34,610    66,220    101,531  1257/10253/23100/31610/35311/36297
parent 0.1%   1800+      138,672    9,341    24   11,723   34,981    66,751    102,219  1315/10408/23258/31770/35468/36453
parent 0.05%  1800+      139,147    9,363    24   11,866   35,209    67,063    102,614  1371/10495/23343/31854/35551/36533
parent 0.02%  1800+      139,331    9,371    24   11,924   35,299    67,185    102,768  1400/10524/23375/31886/35583/36563
absolute 1.0% all             62       36     6       62       62        62         62  54/8/0/0/0/0
absolute 0.5% all            130       66     7      130      130       130        130  97/33/0/0/0/0
absolute 0.2% all            338      165    10      334      338       338        338  198/136/4/0/0/0
absolute 0.1% all            683      310    10      665      683       683        683  349/316/18/0/0/0
absolute 0.05% all         1,407      629    15    1,303    1,402     1,407      1,407  546/757/99/5/0/0
absolute 0.02% all         3,589    1,507    18    3,031    3,558     3,587      3,589  949/2082/527/29/2/0
absolute 1.0% 1800+           92       38     8       92       92        92         92  60/32/0/0/0/0
absolute 0.5% 1800+          200       79    13      192      199       200        200  112/80/7/1/0/0
absolute 0.2% 1800+          491      173    18      432      482       489        491  189/243/50/7/2/0
absolute 0.1% 1800+        1,138      353    19      871    1,097     1,134      1,138  292/579/226/37/4/0
absolute 0.05% 1800+       2,739      772    24    1,690    2,478     2,668      2,722  448/1242/788/190/54/17
absolute 0.02% 1800+      12,270    2,513    24    4,407    8,579    11,032     11,957  836/3571/4172/2453/925/313
```
Exact ply histograms for the two richest (`absolute`, 0.02%) rows, format `ply:count`:
- `all`: 0:1 1:18 2:130 3:316 4:484 5:570 6:574 7:526 8:412 9:246 10:156 11:84 12:41 13:17 14:7 15:4 16:1 17:1 18:1
- `1800+`: 0:1 1:15 2:109 3:270 4:441 5:626 6:833 7:1009 8:1103 9:1138 10:1105 11:1006 12:923 13:803 14:670 15:547 16:433 17:330 18:256 19:193 20:146 21:112 22:88 23:68 24:45

## B. lichess `chess-openings` a-e (3,810 lines)
Files: `refs/lichess/chess-openings-{a,b,c,d,e}.tsv` (columns `eco`,`name`,`pgn`). Script: `/tmp/openings_facts.py`.
Parsed 3,810 data rows, 0 failures; per volume a=817, b=772, c=1,250, d=614, e=357; 36,925 plies in total.
### B1. Transpositions (position key = EPD of each position on each line)
- Distinct **final** EPDs = 3,810 (one per line); **0** lines collide at their final position, 0 collision groups. The set is deduplicated: 0 duplicate PGN strings (295 duplicate display names remain).
- Distinct EPDs across **all** plies/positions of all lines = **7,855**; **2,809** of those are shared by >= 2 lines (2,808 excluding the start position).
- **3,810 of 3,810 lines (100%)** share at least one non-initial position with another line, i.e. mid-line transposition is universal. Shared-position group sizes: max 2,023 (the position after 1.e4), median 3, mean 11.35, 1,023 positions shared by >= 5 lines.
### B2. Families (family = `name` text before the first `:`); 149 distinct families
```
rank family                        lines  cum lines  cum share of 3,810
1    Sicilian Defense                391        391     10.26%
2    Ruy Lopez                       235        626     16.43%
3    French Defense                  212        838     21.99%
4    Queen's Gambit Declined         198      1,036     27.19%
5    Italian Game                    187      1,223     32.10%
6    English Opening                 175      1,398     36.69%
7    King's Gambit Accepted          137      1,535     40.29%
8    King's Indian Defense           119      1,654     43.41%
9    Caro-Kann Defense               110      1,764     46.30%
10   Nimzo-Indian Defense             99      1,863     48.90%
```
Cumulative share of all 3,810 lines: top 5 = 1,223 (32.10%), top 10 = 1,863 (48.90%), top 20 = 2,476 (64.99%), top 50 = 3,457 (90.73%). The remaining 99 families contribute 353 lines (9.27%).
### B3. Share of lines whose first N plies stay inside the top-K families' position set
Main set = union of EPDs at plies 0..N over all lines of the top-K families; a line counts if every position at plies 0..N is in that set.
```
overall share        K=5     K=10    K=20    K=50   (set size at K=50)
N=2                75.3%   82.7%   87.4%   97.3%     105
N=4                48.0%   66.5%   76.5%   96.0%     650
N=6                39.0%   56.6%   70.9%   93.1%   1,638
N=8                34.9%   52.0%   67.2%   92.3%   2,761
N=10               33.9%   50.9%   66.7%   91.8%   3,927
N=12               33.3%   50.3%   66.1%   91.7%   4,937
per volume, K=50 (a=817, b=772, c=1,250, d=614, e=357 lines)
N=2     a 90.9%  b 96.4%  c 99.9%  d 100.0%  e 100.0%   all 97.3%
N=4     a 87.1%  b 95.6%  c 99.0%  d  99.7%  e 100.0%   all 96.0%
N=6     a 79.9%  b 95.3%  c 97.0%  d  96.4%  e  99.4%   all 93.1%
N=8     a 79.8%  b 94.8%  c 96.4%  d  94.5%  e  96.9%   all 92.3%
N=10    a 79.6%  b 94.8%  c 96.2%  d  92.8%  e  95.8%   all 91.8%
N=12    a 79.4%  b 94.8%  c 96.2%  d  92.8%  e  95.0%   all 91.7%
per volume, K=20  N=2 a 66.3 b 73.7 c 99.8 d 100.0 e 100.0 | N=6 a 46.3 b 73.2 c 71.9 d 86.8 e 91.0 | N=12 a 45.9 b 72.7 c 71.1 d 74.4 e 65.8
```
### B4. Ply-depth distribution of lines, top-5 and top-20 families (a line's depth = its ply count)
```
top-5  families: 1,223 lines  min 2   median 11   mean 11.66  max 36
  2:2 3:31 4:31 5:57 6:87 7:65 8:83 9:84 10:103 11:112 12:97 13:77 14:81 15:49 16:46 17:52 18:40 19:34 20:26 21:16 22:13 23:9 24:7 25:7 26:6 27:4 28:3 36:1
top-20 families: 2,476 lines  min 1   median 10   mean 10.70  max 36
  1:2 2:21 3:78 4:115 5:160 6:199 7:168 8:176 9:186 10:181 11:195 12:188 13:149 14:160 15:89 16:81 17:82 18:57 19:55 20:35 21:28 22:19 23:11 24:11 25:10 26:9 27:6 28:3 29:1 36:1
```
Odd depths are legitimate: a line may end after either colour's move.
### B5. Sicilian Defense as White: distinct White-to-move positions per ply
Sicilian Defense family = 391 lines (10.26% of 3,810; 80 distinct ECO codes), max line depth 27 plies.
Positions the learner must answer as **White**, per ply (EPD-keyed, merged across the family):
```
ply        0    2    4    6    8   10   12   14   16   18   20   22   24   26
new        1    1   26   55   49   60   68   56   35   26   15    5    3    2
cumulative 1    2   28   83  132  192  260  316  351  377  392  397  400  402
```
Total distinct White-to-move positions in the whole Sicilian family = **402**; distinct Black-to-move positions = 410; total distinct positions on Sicilian lines = **812**.

## Files, scripts, provenance
- Inputs (read-only): `/home/anthony/pproj/chessop/refs/lichess/chess-openings-{a,b,c,d,e}.tsv`, `/tmp/lichessdump/lichess_db_standard_rated_2013-01.pgn.zst`, `/home/anthony/pproj/chessop/refs/lichess/dump-2013-01-tree-stats.txt`.
- Scripts (both kept in `/tmp`, as instructed): `/tmp/repertoire_tree.py`, `/tmp/openings_facts.py`; full Task A output also at `/tmp/tree_stats.json`, Task B at `/tmp/openings_facts.json`.
- Runtime: python-chess 1.11.2 via `uv run --offline --no-project --with chess`. This file is the only file written inside the project.

## Gaps / caveats
- **Raw dump WAS available locally.** No download was performed and **no network access was used at all** for either task (verified: `uv run --offline` resolves and imports `chess` 1.11.2). The GB-scale dumps were never fetched.
- **The literal "share at the parent position" definition barely prunes.** Table A `parent` rows keep 1.62-1.77M positions (`all`) at every cutoff from 1% to 0.02%: a deep position reached by 3 games where 2 games play the same move still has share 67%. It is not a repertoire-size bound. The `absolute` rows are the usable numbers, and they cross-check `refs/lichess/dump-2013-01-tree-stats.txt`, which used the absolute convention on a sequence-keyed (non-merged) tree: at 1% it reported 60 nodes (`all`) and 89 (`both1800`), vs 62 and 92 here.
- Only one dump was measured: 2013-01, an early-Lichess sample of 121,332 games, not modern Lichess and not the masters DB; absolute frequencies would shift on current data.
- `both1800` uses self-reported 2013 Lichess Elo (218 Elo-less games excluded); it is not a FIDE/modern-rating filter.
- Games were walked to ply 24, so `absolute` node counts are lower bounds beyond that. A few `parent` rows show max ply 25-28 (<=38 nodes) because EPD merging of transpositions can lengthen shortest paths; this is an artifact, not extra data.
- The 687-byte `refs/lichess/masters-pgn-sample.pgn` is far too small to build a tree and was deliberately not analysed.
- B2/B3 family = text before the first `:`, so multi-colon subvariations are lumped into the family; B3's "main openings" set is one defensible choice (top-K families, plies 0..N) and other definitions give other shares.
- `chess-openings` is a curated list of named lines (3,810), not a repertoire, so B4/B5 count positions appearing on named lines only — a real repertoire would include unnamed transpositions and moves not in the list.
