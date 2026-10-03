#!/usr/bin/env python3
"""Size of the pooled position graph ADR 0006 builds, and what pooling admits (ticket 17).

Same sample and stream as repertoire-rule-analysis-recent.py (ticket 13): the monthly
.pgn.zst dump streamed over HTTP, decompressed on the fly, never stored, read until
band 1800-2100 has TARGET_GAMES games after ADR 0003's filters; one move-sequence
trie per band (1800-2100 and 1500-1800) to ply 36, every node keyed by EPD.

On each band's trie this script then builds what `build-snapshot` + the load-time
rule of ADR 0005 / 0006 would build:

  1. POOL: every trie node keyed by python-chess `Board.epd()`; a position's count
     is the sum over its move orders, a (position, move) edge's count likewise.
  2. MAIN MOVES per position on the pooled counts: edges with >= floor games
     (0.02 % of the band's games), the top-3 (count desc, SAN desc ties) plus every
     further one with >= 5 % of the games reaching the position (pooled).
  3. REACHABLE from the start position (BFS; a position at depth 36 keeps no edge).
  4. DAG: an edge that arrives at a position already reached at a shorter depth
     and would close a cycle is dropped (the shorter path is kept); reported.
  5. PRUNE every position with no exactly-named book position at or below it;
     what the start position still reaches is the repertoire graph.

and measures: size (positions, edges, branches, leaves, depth) against the
sequence tree of ADR 0005 (top-3 + 5 % share, f = 0.02 %, book-pruned) and that
tree merged by position; book lines covered and which of ticket 13's
transposition-only misses come back; cycle edges dropped; junk admitted by
pooling (largest single order's share of every kept position's and edge's pooled
count; kept edges that are main under no single move order); names (exact share,
inherited-name ambiguity, canonical order vs the book's own line); the
per-colour split.

Usage:
    python pooled-repertoire-analysis.py <dump-url-or-path> <chess-openings-dist.tsv> <out.md>
        [--target-games N] [--max-bytes B]

Imports repertoire-rule-analysis-recent.py (stream, filters, tries, width
selection) which imports repertoire-rule-analysis.py (trie keying, rules, book)
and tree-width-analysis.py (tokenizer).  Requires python-chess 1.11.2 and
zstandard.  See docs/research/pooled-repertoire.md.
"""

import importlib.util
import os
import resource
import sys
import time
from collections import Counter, defaultdict

import chess
import zstandard as zstd

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rrr = _load("repertoire_rule_analysis_recent", "repertoire-rule-analysis-recent.py")
rra = rrr.rra

BANDS = rrr.BANDS                # (1800, 1500)
PLY_CAP = rrr.PLY_CAP            # 36
FLOOR = 0.0002                   # ADR 0005: 0.02 % of the band's games
WIDTH = 3                        # top-3
SHARE = 0.05                     # plus every reply with >= 5 % of the games reaching the position
JUNK_SHARE = 0.25                # "no single order holds >= 25 %" listing threshold
SHARE_BINS = ((1.0, "100 % (one order)"), (0.75, "75-100 %"), (0.5, "50-75 %"),
              (0.25, "25-50 %"), (0.0, "below 25 %"))
LIST_CAP = 80                    # junk positions are listed in full; other listings capped
STILL_CAP, PO_CAP, AMB_CAP, CANON_CAP = 30, 60, 40, 40

table, pct, floor_games, band_name = rra.table, rrr.pct, rrr.floor_games, rrr.band_name


def side(epd):
    return "White" if epd.split(" ")[1] == "w" else "Black"


def san_line(sans):
    """`1. e4 c5 2. Nf3` from a SAN tuple."""
    return " ".join(("%d. %s" % (i // 2 + 1, s)) if i % 2 == 0 else s for i, s in enumerate(sans))


def share_bin(x):
    for lo, label in SHARE_BINS:
        if x >= lo - 1e-12:
            return label
    return SHARE_BINS[-1][1]


# --------------------------------------------------------------------------
# Pooling: one walk over the keyed trie (no board needed, key_trie stored epd/uci)
# --------------------------------------------------------------------------

def pool(root):
    """pos[epd] = [pooled count, largest single-order count, orders, min ply, max ply, best node]
    edges[(epd, uci)] = [pooled count, child epd, san, largest single-order count]
    A trie node is one move order into its position; `best node` is the most
    popular order (ties: first seen in the stream)."""
    pos = {root.epd: [root.count, root.count, 1, 0, 0, root]}
    edges = {}
    stack = [root]
    while stack:
        nd = stack.pop()
        for ch in nd.kids.values():
            rec = pos.get(ch.epd)
            if rec is None:
                pos[ch.epd] = [ch.count, ch.count, 1, ch.ply, ch.ply, ch]
            else:
                rec[0] += ch.count
                rec[2] += 1
                if ch.count > rec[1]:
                    rec[1], rec[5] = ch.count, ch
                if ch.ply < rec[3]:
                    rec[3] = ch.ply
                if ch.ply > rec[4]:
                    rec[4] = ch.ply
            ek = (nd.epd, ch.uci)
            er = edges.get(ek)
            if er is None:
                edges[ek] = [ch.count, ch.epd, ch.san, ch.count]
            else:
                er[0] += ch.count
                if ch.count > er[3]:
                    er[3] = ch.count
            stack.append(ch)
    return pos, edges


def collect_orders(root, want):
    """Second walk with a path stack: for every EPD in `want`, its trie nodes
    (the move orders into it) and the SAN / UCI path of each."""
    orders = defaultdict(list)          # epd -> [(node, san path, uci path)]
    stack = [(root, iter(root.kids.values()))]
    sans, ucis = [], []
    if root.epd in want:
        orders[root.epd].append((root, (), ()))
    while stack:
        nd, it = stack[-1]
        ch = next(it, None)
        if ch is None:
            stack.pop()
            if stack:
                sans.pop()
                ucis.pop()
            continue
        sans.append(ch.san)
        ucis.append(ch.uci)
        if ch.epd in want:
            orders[ch.epd].append((ch, tuple(sans), tuple(ucis)))
        stack.append((ch, iter(ch.kids.values())))
    return orders


# --------------------------------------------------------------------------
# The graph
# --------------------------------------------------------------------------

def main_edges(pos, edges, m):
    """Candidate main moves per position on pooled counts: edges with >= m games,
    the top-WIDTH (count desc, SAN desc) plus every further one with >= SHARE of
    the position's pooled count.  {epd: [(count, san, uci, child, max_single)]}."""
    out = defaultdict(list)
    for (pe, u), (cnt, ce, san, mx) in edges.items():
        if cnt >= m:
            out[pe].append((cnt, san, u, ce, mx))
    cand = {}
    for pe, lst in out.items():
        lst.sort(key=lambda t: (t[0], t[1]), reverse=True)
        base = pos[pe][0]
        cand[pe] = [e for i, e in enumerate(lst) if i < WIDTH or e[0] >= SHARE * base]
    return cand


def bfs_depth(G, start, cap=None):
    """Shortest depth of every position reachable from start over G
    ({epd: [edge tuples with child at index 3]}); with `cap`, positions at depth
    >= cap expand nothing.  Returns (depth dict, BFS order)."""
    depth, order = {start: 0}, [start]
    i = 0
    while i < len(order):
        p = order[i]
        i += 1
        if cap is not None and depth[p] >= cap:
            continue
        for e in G.get(p, ()):
            c = e[3]
            if c not in depth:
                depth[c] = depth[p] + 1
                order.append(c)
    return depth, order


def reaches(G, a, b):
    """Is b reachable from a over G (edge child at index 3)?"""
    seen, stack = {a}, [a]
    while stack:
        p = stack.pop()
        if p == b:
            return True
        for e in G.get(p, ()):
            if e[3] not in seen:
                seen.add(e[3])
                stack.append(e[3])
    return False


def build_graph(pos, edges, start, m, names):
    """ADR 0006's build on pooled counts.  Returns a dict with the pre-prune
    reachable graph, the dropped cycle edges, the longer-arrival edges kept, the
    pruned repertoire graph, the stub edges, and the candidate map."""
    cand = main_edges(pos, edges, m)
    depth, order = bfs_depth(cand, start, PLY_CAP)
    # forward edges first (depth[c] == depth[p] + 1: they cannot close a cycle);
    # then every edge arriving at a position already reached at a shorter or
    # equal depth, in BFS order of its parent, kept unless it closes a cycle
    G = {}
    back = []
    for p in order:
        G[p] = []
        if depth[p] >= PLY_CAP:
            continue
        for e in cand.get(p, ()):
            if depth[e[3]] == depth[p] + 1:
                G[p].append(e)
            else:
                back.append((depth[p], -e[0], p, e))
    back.sort()
    dropped, longer = [], []
    for _, _, p, e in back:
        if reaches(G, e[3], p):
            dropped.append((p, e, depth[p], depth[e[3]]))
        else:
            G[p].append(e)
            longer.append((p, e, depth[p], depth[e[3]]))
    for p in G:
        G[p].sort(key=lambda t: (t[0], t[1]), reverse=True)
    hits_cap = any(d >= PLY_CAP for d in depth.values())
    # prune: positions with an exactly-named position at or below them
    topo = topo_order(G, start)
    has = {}
    for p in reversed(topo):
        has[p] = (p in names) or any(has[e[3]] for e in G[p])
    K = {}
    stubs = []
    stack = [start]
    while stack:
        p = stack.pop()
        if p in K:
            continue
        K[p] = [e for e in G[p] if has[e[3]]]
        stubs.extend((p, e) for e in G[p] if not has[e[3]])
        stack.extend(e[3] for e in K[p])
    return {"cand": cand, "pre": G, "pre_depth": depth, "dropped": dropped, "longer": longer,
            "graph": K, "stubs": stubs, "hits_cap": hits_cap}


def topo_order(G, start):
    """Iterative DFS post-order reversed = a topological order of the DAG G."""
    seen, post = set(), []
    stack = [(start, iter(G.get(start, ())))]
    seen.add(start)
    while stack:
        p, it = stack[-1]
        e = next(it, None)
        if e is None:
            stack.pop()
            post.append(p)
            continue
        c = e[3]
        if c not in seen:
            seen.add(c)
            stack.append((c, iter(G.get(c, ()))))
    post.reverse()
    return post


def dag_stats(G, start):
    """positions, edges, leaves, root-to-leaf paths, longest path, in-degree > 1,
    depth histogram (shortest), internal count, kept-edge mean / max, discard %
    needs counts so is done by the caller.  G: {epd: [edges (child at 3)]}."""
    depth, order = bfs_depth(G, start)
    indeg = Counter(e[3] for p in G for e in G[p])
    memo_paths, memo_long = {}, {}
    cycles = [0]

    def paths(p, onstack):
        if p in memo_paths:
            return memo_paths[p]
        if not G[p]:
            return 1
        if p in onstack:
            cycles[0] += 1
            return 0
        onstack.add(p)
        r = sum(paths(e[3], onstack) for e in G[p])
        onstack.discard(p)
        memo_paths[p] = r
        return r

    def longest(p, onstack=frozenset()):
        if p in memo_long:
            return memo_long[p]
        r = 1 + max((longest(e[3], onstack | {p}) for e in G[p] if e[3] not in onstack), default=-1)
        memo_long[p] = r
        return r

    n_paths = paths(start, set())
    leaves = [p for p in G if not G[p]]
    internal = [p for p in G if G[p]]
    ks = [len(G[p]) for p in internal]
    return {"positions": len(G), "edges": sum(len(v) for v in G.values()),
            "leaves": len(leaves), "paths": n_paths, "max_depth": longest(start),
            "by_depth": Counter(depth.values()), "depth": depth,
            "multi_in": sum(1 for p in G if indeg[p] > 1), "cycles": cycles[0],
            "internal": len(internal),
            "mean_kids": (float(sum(ks)) / len(ks)) if ks else 0.0,
            "max_kids": max(ks) if ks else 0}


def merged_tree(T, root):
    """A sequence tree {node: [kids]} merged by position: {epd: [(count, san, uci, child)]}
    with edge counts summed over the orders that keep the edge."""
    acc = {}
    for nd, kids in T.items():
        acc.setdefault(nd.epd, {})
        for c in kids:
            k = acc[nd.epd].get(c.uci)
            if k is None:
                acc[nd.epd][c.uci] = [c.count, c.san, c.uci, c.epd]
            else:
                k[0] += c.count
            acc.setdefault(c.epd, {})
    return {p: sorted((tuple(v) for v in d.values()), key=lambda t: (t[0], t[1]), reverse=True)
            for p, d in acc.items()}


# --------------------------------------------------------------------------
# Per-band measurement
# --------------------------------------------------------------------------

def order_main(nd, m):
    """The main-move UCIs at one trie node under the per-order rule (ADR 0005 as
    ticket 13 measured it): replies with >= m games in this order, top-WIDTH
    plus >= SHARE of the games reaching the node in this order."""
    kids = sorted((c for c in nd.kids.values() if c.count >= m),
                  key=lambda c: (c.count, c.san), reverse=True)
    return {c.uci for i, c in enumerate(kids) if i < WIDTH or c.count >= SHARE * nd.count}


def measure_band(band, root, n_games, rows, names):
    t0 = time.time()
    n_raw = len(rra.all_nodes(root))
    visited, dropped_games = rra.key_trie(root)
    start = root.epd
    m = floor_games(FLOOR, n_games)
    pos, edges = pool(root)
    print("band %d: %d trie nodes keyed -> %d positions, %d edges, %.0fs"
          % (band, visited + 1, len(pos), len(edges), time.time() - t0), file=sys.stderr)
    seq_count = {}
    for eco, name, pgn, uci, epd in rows:
        nd = rrr.seq_node(root, uci)
        seq_count[uci] = nd.count if nd is not None else 0

    # --- the sequence trees of ticket 13 at this floor
    T0_seq = rrr.select_width(root, m, WIDTH, SHARE, PLY_CAP)
    T_seq = rra.prune_to_named(T0_seq, root, names)
    T_unc = rra.prune_to_named(rrr.select_width(root, m, None, None, PLY_CAP), root, names)
    seq_epds = {n.epd for n in T_seq}
    seq0_epds = {n.epd for n in T0_seq}
    unc_epds = {n.epd for n in T_unc}
    seq_leaves = [n for n in T_seq if not T_seq[n]]
    seq_ws = rrr.width_stats(T_seq)
    seq_stats = {"nodes": len(T_seq), "edges": len(T_seq) - 1, "leaves": len(seq_leaves),
                 "paths": len(seq_leaves), "max_depth": max(n.ply for n in T_seq),
                 "positions": len(seq_epds), "leaf_positions": len({n.epd for n in seq_leaves}),
                 "internal": seq_ws["internal"], "mean_kids": seq_ws["mean_kids"],
                 "max_kids": seq_ws["max_kids"], "discard": seq_ws["discard"],
                 "book": len(seq_epds & set(names)),
                 "by_ply": Counter(n.ply for n in T_seq)}
    seq0_leaves = [n for n in T0_seq if not T0_seq[n]]
    seq0_ws = rrr.width_stats(T0_seq)
    seq0_stats = {"nodes": len(T0_seq), "edges": len(T0_seq) - 1, "leaves": len(seq0_leaves),
                  "paths": len(seq0_leaves), "max_depth": max(n.ply for n in T0_seq),
                  "positions": len(seq0_epds), "leaf_positions": len({n.epd for n in seq0_leaves}),
                  "internal": seq0_ws["internal"], "mean_kids": seq0_ws["mean_kids"],
                  "max_kids": seq0_ws["max_kids"], "discard": seq0_ws["discard"],
                  "book": len(seq0_epds & set(names))}
    M_seq = merged_tree(T_seq, root)
    ms = dag_stats(M_seq, start)
    ms["book"] = len(set(M_seq) & set(names))

    # --- the pooled graph
    B = build_graph(pos, edges, start, m, names)
    K, G0 = B["graph"], B["pre"]
    ks = dag_stats(K, start)
    ps = dag_stats(G0, start)
    for st_, GG in ((ks, K), (ps, G0)):
        reach = sum(pos[p][0] for p in GG if GG[p])
        kept = sum(e[0] for p in GG for e in GG[p])
        st_["discard"] = 100.0 * (reach - kept) / reach if reach else 0.0
        st_["book"] = len(set(GG) & set(names))
        st_["named"] = sum(1 for p in GG if p in names)
    kept_set = set(K)
    depth = ks["depth"]
    parents = defaultdict(list)
    for p in K:
        for e in K[p]:
            parents[e[3]].append((p, e))

    # --- book coverage
    withm = [r for r in rows if pos.get(r[4], [0])[0] >= m]
    cat = {}
    for r in withm:
        e = r[4]
        cat[e] = ("in sequence tree" if e in seq_epds else
                  "missed by width only" if e in unc_epds else "missed by transposition only")
    cov = {}
    for c in ("in sequence tree", "missed by width only", "missed by transposition only"):
        rs = [r for r in withm if cat[r[4]] == c]
        cov[c] = (len(rs), sum(1 for r in rs if r[4] in kept_set))
    still = [r for r in withm if r[4] not in kept_set]
    # why a named position with >= m pooled games is still out of the graph
    in_edges = defaultdict(list)
    for (pe, u), (cnt, ce, san, mx) in edges.items():
        if cnt >= m:
            in_edges[ce].append((pe, u, cnt))
    why = Counter()
    still_rows = []
    for r in still:
        e = r[4]
        ins = in_edges.get(e, [])
        if not ins:
            k = "no in-edge clears the floor (pooled)"
        else:
            mains = [(pe, u, cnt) for pe, u, cnt in ins
                     if any(x[2] == u for x in B["cand"].get(pe, ()))]
            if not mains:
                k = "an in-edge clears the floor but is main at no parent (width)"
            elif any(pe in G0 for pe, u, cnt in mains):
                k = "main at a reachable parent but dropped as a cycle edge"
            else:
                k = "main at a parent that is itself out of the graph"
        why[k] += 1
        still_rows.append((pos[e][0], seq_count.get(r[3], 0), r[1], r[0], len(r[3]), k, r[2]))
    still_rows.sort(reverse=True)

    # --- recovered / lost vs the sequence tree
    recovered = kept_set - seq_epds
    lost = seq_epds - kept_set
    lost_rows = []
    par_seq = rra.parents_of(T_seq, root)
    for e in sorted(lost, key=lambda x: -pos[x][0]):
        nd = max((n for n in T_seq if n.epd == e), key=lambda n: n.count)
        ins = in_edges.get(e, [])
        why_l = ("no in-edge clears the floor pooled" if not ins else
                 "in-edge main at no parent on pooled counts" if not any(
                     any(x[2] == u for x in B["cand"].get(pe, ())) for pe, u, cnt in ins)
                 else "parent out of the graph or edge dropped")
        lost_rows.append((nd.ply, pos[e][0], nd.count, names[e][1] if e in names else "(unnamed)",
                          why_l, san_line(rra.node_path(root, nd, par_seq).split())))

    # --- junk: largest single order's share
    orders = collect_orders(root, set(G0))
    pos_share = {p: pos[p][1] / float(pos[p][0]) for p in K}
    pos_hist = Counter(share_bin(x) for p, x in pos_share.items())
    pos_below_floor = sum(1 for p in K if pos[p][1] < m)
    edge_share = {(p, e[2]): e[4] / float(e[0]) for p in K for e in K[p]}
    edge_hist = Counter(share_bin(x) for x in edge_share.values())
    edge_below_floor = sum(1 for p in K for e in K[p] if e[4] < m)
    # edges main under no single move order
    pooled_only = []
    for p in K:
        mains_by_order = [order_main(nd, m) for nd, s, u in orders[p]]
        for e in K[p]:
            n_main = sum(1 for mm in mains_by_order if e[2] in mm)
            if n_main == 0:
                pooled_only.append((p, e))
    pooled_only_set = {(p, e[2]) for p, e in pooled_only}
    junk_pos = [p for p in K if p != start and pos_share[p] < JUNK_SHARE]
    junk_rows = []
    for p in sorted(junk_pos, key=lambda x: (depth[x], -pos[x][0])):
        best = pos[p][5]
        bo = next((s for nd, s, u in orders[p] if nd is best), ())
        ins = parents[p]
        junk_rows.append((depth[p], pos[p][0], pos[p][2], "%.0f %%" % (100 * pos_share[p]),
                          names[p][1] if p in names else "(unnamed)",
                          "yes" if p in seq0_epds else "no",
                          "%d / %d" % (sum(1 for q, e in ins if (q, e[2]) in pooled_only_set), len(ins)),
                          "yes" if K[p] else "no", san_line(bo)))
    junk_all_pooled_only = sum(1 for p in junk_pos
                               if parents[p] and all((q, e[2]) in pooled_only_set for q, e in parents[p]))
    junk_not_seq0 = sum(1 for p in junk_pos if p not in seq0_epds)
    po_rows = []
    for p, e in sorted(pooled_only, key=lambda t: (depth[t[0]], -t[1][0])):
        best = pos[p][5]
        bo = next((s for nd, s, u in orders[p] if nd is best), ())
        ranks = []
        for nd, s, u in orders[p]:
            kids = sorted((c for c in nd.kids.values() if c.count >= m),
                          key=lambda c: (c.count, c.san), reverse=True)
            rk = next((i + 1 for i, c in enumerate(kids) if c.uci == e[2]), None)
            if rk is not None:
                ranks.append((rk, nd.count))
        po_rows.append((depth[p], e[1], e[0], e[4], "%.1f %%" % (100.0 * e[0] / pos[p][0]),
                        len(orders[p]),
                        ", ".join("rank %d of an order with %d games" % rk for rk in sorted(ranks)[:3])
                        or "below the floor in every order",
                        names[e[3]][1] if e[3] in names else "(unnamed)", san_line(bo)))
    # positions whose every kept in-edge is pooled-only, any share
    all_po_pos = [p for p in K if p != start and parents[p]
                  and all((q, e[2]) in pooled_only_set for q, e in parents[p])]

    # --- names
    inherited = {}
    for p in topo_order(K, start):
        if p in names:
            inherited[p] = frozenset([names[p][1]])
        else:
            s = set()
            for q, e in parents[p]:
                s |= inherited[q]
            inherited[p] = frozenset(s)
    ambiguous = [p for p in K if p not in names and len(inherited[p]) > 1]
    amb_rows = []
    for p in sorted(ambiguous, key=lambda x: (depth[x], -pos[x][0])):
        best = pos[p][5]
        bo = next((s for nd, s, u in orders[p] if nd is best), ())
        amb_rows.append((depth[p], pos[p][0], len(inherited[p]),
                         "; ".join(sorted(inherited[p])), san_line(bo)))
    named_kept = [p for p in K if p in names]
    canon_differs, canon_rows, book_order_zero, book_order_below = 0, [], 0, 0
    for p in named_kept:
        best = pos[p][5]
        bo = next(((s, u) for nd, s, u in orders[p] if nd is best), ((), ()))
        book_uci = names[p][3]
        sc = seq_count.get(book_uci, 0)
        if sc == 0:
            book_order_zero += 1
        elif sc < m:
            book_order_below += 1
        if bo[1] != book_uci:
            canon_differs += 1
            canon_rows.append((pos[p][0], best.count, sc, names[p][1], names[p][0],
                               san_line(bo[0]), names[p][2]))
    canon_rows.sort(reverse=True)

    # --- per colour
    col = {}
    for label, sel in (("kept positions", list(K)), ("internal (with a kept move)", [p for p in K if K[p]]),
                       ("leaves", [p for p in K if not K[p]]), ("exactly named", named_kept),
                       ("recovered (not in the sequence tree)", list(recovered))):
        col[label] = (sum(1 for p in sel if side(p) == "White"), sum(1 for p in sel if side(p) == "Black"))

    # --- cycles and repeats
    multi_ply_trie = sum(1 for r in pos.values() if r[4] > r[3])
    multi_ply_kept = sum(1 for p in K if pos[p][4] > pos[p][3])
    drop_rows = []
    for p, e, dp, dc in B["dropped"] + B["longer"]:
        best = pos[p][5]
        bo = next((s for nd, s, u in orders[p] if nd is best), ())
        drop_rows.append((dp, dc, e[0], e[1], "dropped" if (p, e, dp, dc) in B["dropped"] else "kept (no cycle)",
                          names[e[3]][1] if e[3] in names else "(unnamed)", san_line(bo)))

    print("band %d measured in %.0fs" % (band, time.time() - t0), file=sys.stderr)
    return {"band": band, "n_games": n_games, "m": m, "trie_nodes": visited + 1, "n_raw": n_raw,
            "dropped_games": dropped_games, "positions_all": len(pos), "edges_all": len(edges),
            "root_pooled": pos[start][0], "seq": seq_stats, "seq0": seq0_stats, "merged": ms, "pooled": ks, "pre": ps,
            "hits_cap": B["hits_cap"], "hits_cap_kept": any(d >= PLY_CAP for d in depth.values()),
            "n_cand_pos": len(B["cand"]),
            "stubs": len(B["stubs"]), "stub_games": sum(e[0] for p, e in B["stubs"]),
            "withm": len(withm), "cov": cov, "still": len(still), "why": why, "still_rows": still_rows[:STILL_CAP],
            "recovered": len(recovered), "recovered_named": sum(1 for p in recovered if p in names),
            "lost": len(lost), "lost_rows": lost_rows[:LIST_CAP],
            "pos_hist": pos_hist, "pos_below_floor": pos_below_floor,
            "edge_hist": edge_hist, "edge_below_floor": edge_below_floor,
            "junk_n": len(junk_pos), "junk_rows": junk_rows, "junk_not_seq0": junk_not_seq0,
            "junk_all_pooled_only": junk_all_pooled_only,
            "pooled_only_n": len(pooled_only), "po_rows": po_rows, "all_po_pos": len(all_po_pos),
            "not_seq0": sum(1 for p in K if p not in seq0_epds),
            "named_kept": len(named_kept), "ambiguous": len(ambiguous), "amb_rows": amb_rows,
            "inherited_max": max((len(v) for v in inherited.values()), default=0),
            "canon_differs": canon_differs, "canon_rows": canon_rows,
            "book_order_zero": book_order_zero, "book_order_below": book_order_below,
            "col": col, "multi_ply_trie": multi_ply_trie, "multi_ply_kept": multi_ply_kept,
            "n_dropped": len(B["dropped"]), "n_longer": len(B["longer"]), "drop_rows": drop_rows,
            "n_multi_order_kept": sum(1 for p in K if pos[p][2] > 1)}


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def write_report(out_path, url, st, results, rows, timing):
    L = []
    A = L.append
    fname = url.rsplit("/", 1)[-1]
    month = fname.split("_")[-1].split(".")[0]
    A("# Pooled repertoire: the position graph of ADR 0006 on a recent month (%s)" % month)
    A("")
    A("Ticket: [`.scratch/chessop/issues/17-pooled-repertoire-size.md`]"
      "(../../.scratch/chessop/issues/17-pooled-repertoire-size.md). Measures the graph "
      "[ADR 0006](../adr/0006-position-graph.md) builds under [ADR 0005](../adr/0005-repertoire-rule.md)'s "
      "rule, on the sample of [`repertoire-rule-candidates-recent.md`](repertoire-rule-candidates-recent.md) "
      "(ticket 13), against the sequence tree that document measured (the `top-3 + share 5 %` cell "
      "at f = 0.02 %, book-pruned: 996 nodes / 389 lines / 17 plies at 1800-2100).")
    A("Script: [`refs/lichess/pooled-repertoire-analysis.py`]"
      "(../../refs/lichess/pooled-repertoire-analysis.py) (imports the ticket 13 scripts' stream, "
      "filters, tries, width rule and book code). Generated; every number below is one run of it. "
      "No recommendation is made here.")
    A("")
    A("## Method and sample")
    A("")
    A("- **Source**: `%s` (%s bytes, CC0), streamed over HTTP through a zstandard streaming "
      "decompressor and parsed as it arrived; nothing was written to disk. Reading stopped when "
      "band 1800-2100 had %s games after filters or after %s compressed bytes, whichever came "
      "first: **stopped because %s**, after **%s compressed bytes** (%.2f %% of the file) and "
      "**%s games seen**. Date range of the games seen (`UTCDate UTCTime`): %s to %s."
      % (fname, format(st["length"], ","), format(st["target"], ","), format(st["max_bytes"], ","),
         st["stop"], format(st["bytes"], ","), 100.0 * st["bytes"] / st["length"],
         format(st["seen"], ","), st["all_dates"][0], st["all_dates"][1]))
    A("- **Filters** (ADR 0003, as in ticket 13): both `WhiteElo` and `BlackElo` present and numeric; "
      "no `WhiteTitle`/`BlackTitle` of `BOT`; `Event` speed not Bullet or UltraBullet; both players "
      "inside the same 300-wide band, lower bound inclusive. Games dropped: %s."
      % ", ".join("%s %s" % (k, format(v, ",")) for k, v in st["drops"].most_common()))
    A("- **Games kept per band**: %s."
      % ", ".join("%s **%s**" % (band_name(b), format(st["kept"][b], ",")) for b in rrr.ALL_BANDS))
    A("- **Trie**: one move-sequence trie per band to **ply %d**, every node keyed by python-chess "
      "`Board.epd()` (`push_san` per node; nodes under a SAN token python-chess rejects dropped). %s. "
      "Peak resident memory of the run %.1f GB; parse %.0f s, keying and measuring %.0f s."
      % (PLY_CAP,
         "; ".join("band %s: %s trie nodes, %s distinct positions, %s distinct (position, move) edges, "
                   "%d games dropped for bad SAN"
                   % (band_name(R["band"]), format(R["trie_nodes"], ","), format(R["positions_all"], ","),
                      format(R["edges_all"], ","), R["dropped_games"]) for R in results),
         timing["rss_gb"], st["parse_s"], timing["measure_s"]))
    A("- **Pooling** (ADR 0006): a position's count is the sum of the counts of every trie node with "
      "its EPD (every move order into it, to ply %d); a (position, move) edge's count likewise. "
      "A trie node is one **move order** into its position; the **largest single order** of a "
      "position (edge) is the largest node (child-node) count among them; the **canonical order** "
      "is that most popular order (ties: first seen in the stream). A game that visits one position "
      "twice is pooled twice." % PLY_CAP)
    A("- **Build** (ADR 0005 on the graph, ADR 0006): floor **m = 0.02 %% of the band's games** "
      "(unrounded threshold, count >= f x N); at every position the **main moves** are the edges with "
      ">= m pooled games, the top-3 (count desc, SAN desc ties) plus every further edge with >= 5 %% of "
      "the position's pooled count; what the start position reaches over main moves (BFS; a position "
      "at depth %d expands nothing) is the **pre-prune graph**; an edge that arrives at a position "
      "already reached at a shorter depth is added last, in BFS order of its parent, and **dropped iff "
      "it closes a cycle** over the edges already in (so the shorter path is kept; an arrival at a "
      "longer depth that closes no cycle is kept and reported); then every position with no "
      "exactly-named book position at or below it is **pruned** and what the start position still "
      "reaches is the **repertoire graph**. A main move at a kept position whose child was pruned "
      "is a **stub** (ADR 0005)." % PLY_CAP)
    A("- **Sequence tree**: ticket 13's `top-3 + share 5 %` tree at the same floor, book-pruned, "
      "rebuilt here by the same code (`select_width` + `prune_to_named`); its **uncapped** sibling "
      "(every reply clearing the floor, book-pruned) defines the transposition-only misses as in "
      "ticket 13 (a named position with >= m pooled games absent even from the uncapped tree). "
      "**Merged by position** = the sequence tree's nodes merged by EPD, edges = distinct "
      "(EPD, move) pairs, as in `transpositions.md`.")
    A("- **Counting**: **positions** include the start position; **edges** are kept (position, move) "
      "pairs; **branches** = root-to-leaf paths (dynamic programming over the DAG); **leaves** = "
      "positions with no kept move; **max depth** = the longest root-to-leaf path in plies; "
      "**by depth** counts positions at their shortest depth; **internal** positions have >= 1 kept "
      "move; **discard %%** = over internal positions, games reaching the position minus games "
      "continuing along kept moves, over games reaching internal positions (pooled counts); "
      "**book lines covered** = distinct named EPDs in the graph, of the book's %d rows."
      % len(rows))
    A("- **Junk**: the share of a kept position's (edge's) pooled count held by its largest single "
      "move order; a kept edge is **main under no single order** when at every trie node of its "
      "parent position the per-order rule of ticket 13 (replies with >= m games in that order, top-3 "
      "plus >= 5 % of that order's games) does not select it. **Reachable by a main order** = the "
      "position is in the sequence tree *before* book-pruning (some single move order reaches it "
      "through per-order main moves).")
    A("- **Names**: a position is **exactly named** when its EPD is a book row's `epd`. Its "
      "**inherited names** are its own name if named, else the union of its parents' inherited names "
      "over the kept edges; a position with more than one inherited name is the ambiguity ADR 0006 "
      "avoids by storing exact names only. **Canonical order vs the book's line** compares the "
      "canonical order's UCI path with the row's `uci`.")
    A("")

    for R in results:
        b, n, m = R["band"], R["n_games"], R["m"]
        A("## Band %s: %s games, floor %s = >= %d games" % (band_name(b), format(n, ","), pct(FLOOR), m))
        A("")
        A("Pooled count of the start position: %s (%s games; the difference is games that return "
          "to the start position by a piece shuffle). Positions reached at more than one ply anywhere "
          "in the trie: %s of %s; among the kept positions of the repertoire graph: %d. Kept positions "
          "reached by more than one move order in the trie: %d of %d."
          % (format(R["root_pooled"], ","), format(n, ","), format(R["multi_ply_trie"], ","),
             format(R["positions_all"], ","), R["multi_ply_kept"], R["n_multi_order_kept"],
             R["pooled"]["positions"]))
        A("")
        A("### Size")
        A("")
        s, s0, ms, ks, ps = R["seq"], R["seq0"], R["merged"], R["pooled"], R["pre"]
        A(table(["build", "positions", "edges", "branches (root-to-leaf paths)", "leaf positions",
                 "max depth (plies)", "positions with > 1 kept in-edge", "internal positions",
                 "kept moves mean / max", "discard %", "book lines covered (of %d)" % len(rows)],
                [["sequence tree (ticket 13: top-3 + share 5 %, book-pruned)",
                  "%d nodes (%d distinct positions)" % (s["nodes"], s["positions"]), s["edges"],
                  s["paths"], "%d leaves (%d distinct positions)" % (s["leaves"], s["leaf_positions"]),
                  s["max_depth"], "-", s["internal"], "%.2f / %d" % (s["mean_kids"], s["max_kids"]),
                  "%.1f" % s["discard"], s["book"]],
                 ["the same tree merged by position", ms["positions"], ms["edges"], ms["paths"],
                  ms["leaves"], ms["max_depth"], ms["multi_in"], ms["internal"],
                  "%.2f / %d" % (ms["mean_kids"], ms["max_kids"]), "-", ms["book"]],
                 ["**pooled graph (ADR 0006), book-pruned**", "**%d**" % ks["positions"],
                  "**%d**" % ks["edges"], "**%d**" % ks["paths"], ks["leaves"],
                  "**%d**" % ks["max_depth"], ks["multi_in"], ks["internal"],
                  "%.2f / %d" % (ks["mean_kids"], ks["max_kids"]), "%.1f" % ks["discard"],
                  "**%d**" % ks["book"]],
                 ["pooled graph before the book pruning", ps["positions"], ps["edges"], ps["paths"],
                  ps["leaves"], ps["max_depth"], ps["multi_in"], ps["internal"],
                  "%.2f / %d" % (ps["mean_kids"], ps["max_kids"]), "%.1f" % ps["discard"], ps["book"]],
                 ["sequence tree before the book pruning",
                  "%d nodes (%d distinct positions)" % (s0["nodes"], s0["positions"]), s0["edges"],
                  s0["paths"], "%d leaves (%d distinct positions)" % (s0["leaves"], s0["leaf_positions"]),
                  s0["max_depth"], "-", s0["internal"], "%.2f / %d" % (s0["mean_kids"], s0["max_kids"]),
                  "%.1f" % s0["discard"], s0["book"]]]))
        A("")
        if ms["cycles"]:
            A("The merged sequence tree has %d cycle(s) (paths counted below the cut)." % ms["cycles"])
            A("")
        A("Positions with a main move at all on pooled counts (any position of the trie with an edge "
          "clearing the floor): %d. Stubs (main moves at kept positions whose child was pruned): %d, "
          "carrying %s games. The pre-prune graph %s the ply cap of %d; the book-pruned graph %s it."
          % (R["n_cand_pos"], R["stubs"], format(R["stub_games"], ","),
             "hits" if R["hits_cap"] else "does not hit", PLY_CAP,
             "hits" if R["hits_cap_kept"] else "does not hit"))
        A("")
        A("Positions by depth (shortest path from the start; the sequence tree by ply):")
        A("")
        maxd = max(list(ks["by_depth"]) + list(s["by_ply"]) + list(ps["by_depth"]))
        A(table(["depth"] + [str(d) for d in range(1, maxd + 1)],
                [["sequence tree"] + [s["by_ply"].get(d, 0) for d in range(1, maxd + 1)],
                 ["merged by position"] + [ms["by_depth"].get(d, 0) for d in range(1, maxd + 1)],
                 ["pooled graph"] + [ks["by_depth"].get(d, 0) for d in range(1, maxd + 1)],
                 ["pooled graph before pruning"] + [ps["by_depth"].get(d, 0) for d in range(1, maxd + 1)]]))
        A("")
        A("Positions in the pooled graph and not in the sequence tree (**recovered by pooling**): "
          "%d (%d of them exactly named); sequence-tree positions not in the pooled graph (**lost**): %d."
          % (R["recovered"], R["recovered_named"], R["lost"]))
        if R["lost_rows"]:
            A("")
            A("Lost positions (ply and games in the sequence tree's order; why, on pooled counts):")
            A("")
            A(table(["ply", "games (pooled)", "games (tree order)", "name", "why", "line (tree order)"],
                    [list(r) for r in R["lost_rows"]]))
        A("")
        A("### Book coverage")
        A("")
        A("Of the %d named book positions with >= %d pooled games at this band (ticket 13's "
          "categories against its sequence tree): how many the pooled graph holds."
          % (R["withm"], m))
        A("")
        A(table(["category (ticket 13, sequence tree)", "book lines", "in the pooled graph", "still missed"],
                [[c, a, k, a - k] for c, (a, k) in R["cov"].items()]
                + [["**all with >= floor (pooled)**", R["withm"], "**%d**" % ks["book"], R["still"]]]))
        A("")
        A("Why the %d are still missed: %s."
          % (R["still"], "; ".join("%s: %d" % (k, v) for k, v in R["why"].most_common()) or "none"))
        if R["still_rows"]:
            A("")
            A("Largest still-missed named positions (up to %d), pooled games / own-order games:" % STILL_CAP)
            A("")
            A(table(["pooled", "own order", "name", "ECO", "ply", "why", "line"],
                    [[p, so, nm, eco, ply, why, "`%s`" % pgn] for p, so, nm, eco, ply, why, pgn in R["still_rows"]]))
        A("")
        A("### Cycles")
        A("")
        A("Edges arriving at a position already reached at a shorter depth: **%d dropped** (each "
          "closed a cycle over the edges already in), %d kept (closed no cycle)."
          % (R["n_dropped"], R["n_longer"]))
        if R["drop_rows"]:
            A("")
            A(table(["parent depth", "child's depth", "games (pooled)", "move", "fate", "child's name",
                     "parent's canonical order"],
                    [[dp, dc, g, mv, fate, nm, "`%s`" % line] for dp, dc, g, mv, fate, nm, line in R["drop_rows"]]))
        A("")
        A("### Junk admitted by pooling")
        A("")
        A("Largest single move order's share of the pooled count, over the %d kept positions and "
          "the %d kept edges:" % (ks["positions"], ks["edges"]))
        A("")
        A(table(["largest single order's share"] + [lab for lo, lab in SHARE_BINS] + ["largest single order below the floor"],
                [["kept positions"] + [R["pos_hist"].get(lab, 0) for lo, lab in SHARE_BINS] + [R["pos_below_floor"]],
                 ["kept edges"] + [R["edge_hist"].get(lab, 0) for lo, lab in SHARE_BINS] + [R["edge_below_floor"]]]))
        A("")
        A("Kept positions not reachable by any single main order (absent from the sequence tree before "
          "book-pruning): %d of %d. Kept edges that are **main under no single move order**: %d of %d; "
          "kept positions whose every kept in-edge is such an edge: %d."
          % (R["not_seq0"], ks["positions"], R["pooled_only_n"], ks["edges"], R["all_po_pos"]))
        A("")
        A("Kept positions where no single order holds >= %d %% of the pooled count (start position "
          "excluded): **%d**; %d of them reachable by no single main order; %d of them entered only by "
          "edges main under no single order." % (int(JUNK_SHARE * 100), R["junk_n"], R["junk_not_seq0"],
                                                  R["junk_all_pooled_only"]))
        if R["junk_rows"]:
            A("")
            A("Every such position (`orders` = trie nodes with this EPD, i.e. move orders into it; "
              "`in-edges main by no order / kept in-edges`; `expands` = has a kept move):")
            A("")
            A(table(["depth", "games (pooled)", "orders", "largest order", "name", "reachable by a main order",
                     "in-edges main by no order / kept", "expands", "canonical order"],
                    [list(r[:-1]) + ["`%s`" % r[-1]] for r in R["junk_rows"]]))
        if R["po_rows"]:
            A("")
            A("Kept edges main under no single move order (up to %d of %d; `rank` = the move's rank "
              "among the parent's replies clearing the floor in that order):"
              % (PO_CAP, R["pooled_only_n"]))
            A("")
            A(table(["parent depth", "move", "games (pooled)", "largest single order", "share of parent",
                     "parent's orders", "per-order rank", "child's name", "parent's canonical order"],
                    [list(r[:-1]) + ["`%s`" % r[-1]] for r in R["po_rows"][:PO_CAP]]))
        A("")
        A("### Names")
        A("")
        A("- Exactly named kept positions: **%d of %d** (%.1f %%); %d unnamed (the start position "
          "included)." % (R["named_kept"], ks["positions"], 100.0 * R["named_kept"] / ks["positions"],
                          ks["positions"] - R["named_kept"]))
        A("- Unnamed kept positions whose inherited names (over every kept path into them) are more "
          "than one book name: **%d**; the widest carries %d names."
          % (R["ambiguous"], R["inherited_max"]))
        A("- Named kept positions whose canonical (most popular) order differs from the book's own "
          "line: **%d of %d**; the book's own order has no game at all in this band for %d of the "
          "named kept positions and fewer than the floor for another %d."
          % (R["canon_differs"], R["named_kept"], R["book_order_zero"], R["book_order_below"]))
        if R["amb_rows"]:
            A("")
            A("Unnamed positions with more than one inherited name (up to %d, by depth then games):" % AMB_CAP)
            A("")
            A(table(["depth", "games (pooled)", "names", "inherited names", "canonical order"],
                    [[d, g, k, nm, "`%s`" % line] for d, g, k, nm, line in R["amb_rows"][:AMB_CAP]]))
        if R["canon_rows"]:
            A("")
            A("Named positions whose canonical order is not the book's line (up to %d, by pooled "
              "games; games in the canonical order / in the book's order):" % CANON_CAP)
            A("")
            A(table(["pooled", "canonical order games", "book order games", "name", "ECO",
                     "canonical order", "book's line"],
                    [[p, c, s_, nm, eco, "`%s`" % co, "`%s`" % bl]
                     for p, c, s_, nm, eco, co, bl in R["canon_rows"][:CANON_CAP]]))
        A("")
        A("### Per-colour split")
        A("")
        A("Side to move is part of the EPD; a learner position is one where the learner is to move, "
          "so the record key's colour is the side to move.")
        A("")
        A(table(["kept positions", "White to move", "Black to move"],
                [[k, w, bl] for k, (w, bl) in R["col"].items()]))
        A("")

    A("## Reproduction")
    A("")
    A("Nothing is stored: the dump is streamed and the prefix read is whatever the stop rule allows, "
      "so a rerun on the same URL reads the same prefix and gives the same numbers.")
    A("")
    A("```sh")
    A("cd /home/anthony/pproj/chessop")
    A("S=/tmp/chessop-scratch && mkdir -p $S")
    A("")
    A("# 1. dependencies (python-chess %s, zstandard %s)" % (chess.__version__, zstd.__version__))
    A("uv venv $S/venv")
    A("uv pip install --python $S/venv/bin/python chess==%s zstandard==%s"
      % (chess.__version__, zstd.__version__))
    A("")
    A("# 2. the chess-openings dist columns (uci, epd): 3811 lines, exit 0")
    A("$S/venv/bin/python refs/lichess/chess-openings-bin-gen.py \\")
    A("    refs/lichess/chess-openings-a.tsv refs/lichess/chess-openings-b.tsv \\")
    A("    refs/lichess/chess-openings-c.tsv refs/lichess/chess-openings-d.tsv \\")
    A("    refs/lichess/chess-openings-e.tsv > $S/chess-openings-dist.tsv")
    A("")
    A("# 3. the measurement, streaming the dump (no download); regenerates this file")
    A("$S/venv/bin/python refs/lichess/pooled-repertoire-analysis.py \\")
    A("    %s \\" % url)
    A("    $S/chess-openings-dist.tsv docs/research/pooled-repertoire.md \\")
    A("    --target-games %d --max-bytes %d" % (st["target"], st["max_bytes"]))
    A("```")
    A("")
    A("## Sources")
    A("")
    A("- Lichess open database, standard rated games %s, CC0: <%s> (streamed, not stored; the "
      "prefix read is stated under Method); licence page saved as `refs/lichess/database-lichess-org.html`."
      % (month, url))
    A("- `lichess-org/chess-openings` (CC0): `refs/lichess/chess-openings-{a..e}.tsv`, "
      "`refs/lichess/chess-openings-README.md`, `refs/lichess/chess-openings-bin-gen.py` (the "
      "upstream generator deriving `uci` and `epd`; `Board.epd()` per row).")
    A("- python-chess %s: `chess.Board.epd()` (placement, side to move, castling, en passant only "
      "when a capture is legal; no move counters) and `push_san`, used for every key; zstandard %s "
      "for the streaming decompressor." % (chess.__version__, zstd.__version__))
    A("- The rule: [`docs/adr/0005-repertoire-rule.md`](../adr/0005-repertoire-rule.md); the graph: "
      "[`docs/adr/0006-position-graph.md`](../adr/0006-position-graph.md).")
    A("- The sample, the sequence tree and the transposition-only misses: "
      "[`repertoire-rule-candidates-recent.md`](repertoire-rule-candidates-recent.md) and "
      "`refs/lichess/repertoire-rule-analysis-recent.py`; the merged-DAG and cycle-check method: "
      "[`transpositions.md`](transpositions.md) and `refs/lichess/transposition-analysis.py`.")
    A("")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out_path, file=sys.stderr)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    target, max_bytes = rrr.TARGET_GAMES, rrr.MAX_BYTES
    if "--target-games" in args:
        i = args.index("--target-games")
        target = int(args[i + 1])
        del args[i:i + 2]
    if "--max-bytes" in args:
        i = args.index("--max-bytes")
        max_bytes = int(args[i + 1])
        del args[i:i + 2]
    url, dist, out_path = args
    rows, names = rra.load_book(dist)
    assert max(len(r[3]) for r in rows) <= PLY_CAP

    src = rrr.HttpStream(url) if url.startswith("http") else rrr.FileStream(url)
    try:
        roots, st = rrr.build_tries(src, target, max_bytes)
    finally:
        src.close()
    st["target"], st["max_bytes"] = target, max_bytes
    t0 = time.time()
    results = []
    for b in BANDS:
        results.append(measure_band(b, roots[b], st["kept"][b], rows, names))
        roots[b] = None            # free the trie before the next band
    timing = {"measure_s": time.time() - t0,
              "rss_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6}
    write_report(out_path, url, st, results, rows, timing)


if __name__ == "__main__":
    main()
