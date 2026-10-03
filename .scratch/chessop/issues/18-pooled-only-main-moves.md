# Pooled-only main moves: keep every edge that clears the floor only as a sum of orders, or require one order to clear it?

Type: grilling
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

Ticket 17 measured ADR 0006's pooled graph at 1800-2100 (`docs/research/pooled-repertoire.md`): 1,104 positions and 1,985 branches, 108 of the 195 transposition-only book lines recovered, no cycles. It also found the junk ADR 0006 accepted blind: **234 of the 1,326 kept edges (18 %) are main under no single move order** (no one order into the edge's position clears the 30-game floor), concentrated at plies 6-10 in the `d4` families; 165 positions are entered only by such edges, and for 86 positions the most popular order holds under 25 % of the pooled count (70 of them entered only by pooled-only edges; the other 16 are London/Colle-type systems reached by 15-24 popular orders, which is the case pooling exists for). Pooling also *loses* lines when the share base grows: at 1500-1800 four sequence-tree positions drop out (French Tarrasch `3.Nd2` at 223 games falls below 5 % of the pooled `1.e4 e6 2.d4 d5`; Rousseau Gambit ranks below 3 under the pooled Italian). Decide:

- Is an edge that no single order makes popular a line the learner should be drilled on, or noise the floor was meant to exclude? Options: keep them (the position is real theory whatever the orders, the London case); require at least one order into the position to clear the floor (drops the 165 positions, keeps the London systems); require the edge itself to clear some share under one order; or a second, lower per-order floor.
- Whether the share clause (>= 5 % of the games reaching the position) should be measured on pooled or on own-order counts, given it now prunes the Tarrasch at one band.
- Whether ADR 0005's quoted sizes should be restated in positions (the "996 positions" were 996 trie nodes, 772 positions).

Resolve as an amendment to ADR 0006 (and ADR 0005 if the share base changes). HITL: grill the learner; do not answer for them. Facts: `docs/research/pooled-repertoire.md` lists all 86 low-share positions and the 234 pooled-only edges by ply.

## Answer

Resolved 2026-09-22 by grilling the learner (five questions, all recommendations accepted).

1. **Keep them: pooled counts are the counts.** A position's traffic is its pooled traffic over every move order; the popularity floor, the top-3 rank and the 5 % share all apply to pooled counts, with no per-order floor, share or rank. The 234 edges are theory, not junk: they are largely the lines ADR 0006 exists to recover (the Semi-Slav Main Line has every in-edge main under no order: 215 games over 102 orders, none above 13), ADR 0005 promises a move real players make is never a miss (`1.d4 Nf6 2.Nf3 d6 3.c4` is one opponent in five at that position), and the London/Colle systems are the same phenomenon with more orders, not a separable case. Options B (one order clears the floor), C (per-order share) and D (a second lower per-order floor) rejected. "Junk admitted by pooling" is renamed **diffuse traffic** and kept as a diagnostic: `build-snapshot` reports per band the counts of positions and edges whose largest order is below the floor, beside the dropped-cycle count.
2. **Share on pooled counts, 5 % unchanged.** The 1500-1800 losses (French Tarrasch `3.Nd2`, Rousseau Gambit) are threshold cases just under 5 %, accepted; an own-order share would bring order dependence back. Lowering the share to 3-4 % was not measured on the pooled graph and is not chosen blind.
3. **ADR 0005's sizes restated in positions**: 996 trie nodes were 772 distinct positions; the pooled graph is 1,104 / 1,326 edges / 1,985 branches.
4. **Glossary**: `CONTEXT.md` gains **Popularity floor** for the 0.02 % rule; **Floor** stays the need floor with "popularity floor" in its Avoid list. ADR 0005's "floor" reads as the popularity floor.
5. **Build-time report** of diffuse traffic: yes (folded into 1).

Recorded as the ticket 18 amendments to `docs/adr/0006-position-graph.md` and `docs/adr/0005-repertoire-rule.md`. No new tickets; no fog graduated.
