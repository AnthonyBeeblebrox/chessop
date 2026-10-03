#!/usr/bin/env python3
"""Measure how prevalent transpositions are in the drilled repertoire tree.

Reads a Lichess monthly .pgn.zst dump (streamed), builds ONE move-sequence
trie to ply 21 carrying per-bucket game counts (buckets: all, both>=1800,
both<1500), then for each bucket:

  1. Sequence tree: the cut-off tree (a node survives if >= CUTOFF_PCT of
     the bucket's games pass through it), capped to the k most popular
     surviving replies per node (k = max(width_player, width_opponent)).
     Every node gets its position key (python-chess `Board.epd()`), nodes are
     grouped by key and the groups with >1 move order are the transpositions.
  2. Merged DAG: the same tree with nodes merged by position key.
  3. Pooled DAG: the cut-off applied to per-position game counts pooled over
     every move order in the dump (what a position-keyed build would do).
  4. Names: which tree positions carry a name in the CC0 chess-openings TSV
     (keyed by the `epd` that its `bin/gen.py` derives from `pgn`).

Usage:
    python transposition-analysis.py <dump.pgn.zst> <chess-openings-dist.tsv> <out.md>

`<chess-openings-dist.tsv>` is the 5-column (eco name pgn uci epd) file that
`chess-openings-bin-gen.py a.tsv b.tsv ... e.tsv > dist.tsv` prints.

Reuses the PGN streaming / bucket code of tree-width-analysis.py (same
directory).  Requires python-chess 1.11.2 and zstandard.
See docs/research/transpositions.md.
"""

import importlib.util
import io
import os
import sys
import time
from collections import defaultdict

import chess
import chess.pgn

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "tree_width_analysis", os.path.join(HERE, "tree-width-analysis.py"))
tw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tw)

BUCKETS = tw.BUCKETS                 # ("all", "both>=1800", "both<1500")
PLY_CAP = tw.PLY_CAP                 # 21
CUTOFF_PCT = 0.2                     # absolute: share of the bucket's games
WIDTHS = (3, None)                   # k = max(P, O): (3,3) and uncapped
NB = len(BUCKETS)


# --------------------------------------------------------------------------
# One trie, per-bucket counts
# --------------------------------------------------------------------------

def build_trie(path):
    root = [[0] * NB, {}]            # [[games per bucket], {san: child}]
    n = 0
    t0 = time.time()
    for headers, moves in tw.iter_games(path):
        n += 1
        we, be = tw.elo(headers, "WhiteElo"), tw.elo(headers, "BlackElo")
        idx = [i for i, b in enumerate(BUCKETS) if tw.in_bucket(b, we, be)]
        node = root
        for i in idx:
            node[0][i] += 1
        for mv in moves[:PLY_CAP]:
            ch = node[1].get(mv)
            if ch is None:
                ch = [[0] * NB, {}]
                node[1][mv] = ch
            for i in idx:
                ch[0][i] += 1
            node = ch
    print("parsed %d games in %.0fs" % (n, time.time() - t0), file=sys.stderr)
    return root, n


def count_nodes(root):
    n, stack = 0, [root]
    while stack:
        nd = stack.pop()
        n += 1
        stack.extend(nd[1].values())
    return n


# --------------------------------------------------------------------------
# Pass over the whole trie: pooled per-position and per-edge counts
# --------------------------------------------------------------------------

def pool_positions(root):
    """Walk every trie node once, keying it by EPD.

    Returns (pos, edges, start_epd, bad):
      pos[epd]            = [counts per bucket, min ply, max ply, sequence nodes]
      edges[(epd, uci)]   = [counts per bucket, child epd]
      bad                 = games under SAN tokens python-chess rejects
    A game that reaches the same position twice (at two plies) is counted
    twice in that position's pooled count; `max ply > min ply` flags it.
    """
    board = chess.Board()
    start = board.epd()
    pos = {start: [list(root[0]), 0, 0, 1]}
    edges = {}
    bad = [0] * NB
    t0 = time.time()
    stack = [(iter(root[1].items()), start)]
    visited = 0
    while stack:
        it, pepd = stack[-1]
        nxt = next(it, None)
        if nxt is None:
            stack.pop()
            if stack:
                board.pop()
            continue
        san, ch = nxt
        try:
            move = board.push_san(san)
        except ValueError:
            for i in range(NB):
                bad[i] += ch[0][i]
            continue
        visited += 1
        epd = board.epd()
        ply = len(stack)
        rec = pos.get(epd)
        if rec is None:
            pos[epd] = [list(ch[0]), ply, ply, 1]
        else:
            for i in range(NB):
                rec[0][i] += ch[0][i]
            rec[1] = min(rec[1], ply)
            rec[2] = max(rec[2], ply)
            rec[3] += 1
        ek = (pepd, move.uci())
        erec = edges.get(ek)
        if erec is None:
            edges[ek] = [list(ch[0]), epd]
        else:
            for i in range(NB):
                erec[0][i] += ch[0][i]
        stack.append((iter(ch[1].items()), epd))
    print("keyed %d trie nodes -> %d positions, %d edges in %.0fs"
          % (visited + 1, len(pos), len(edges), time.time() - t0), file=sys.stderr)
    return pos, edges, start, bad


# --------------------------------------------------------------------------
# Sequence tree (cut-off + width cap), keyed
# --------------------------------------------------------------------------

def seq_tree(root, i, thr, k):
    """Nodes of the cut-off tree for bucket i, capped to k replies (None = all).

    Each node: dict(path, ucis, ply, count, epd, kids, parent).
    """
    board = chess.Board()
    nodes = [{"path": (), "ucis": (), "ply": 0, "count": root[0][i],
              "epd": board.epd(), "kids": [], "parent": None}]
    stack = [(0, root)]
    while stack:
        nid, tn = stack.pop()
        nd = nodes[nid]
        if nd["ply"] >= PLY_CAP:
            continue
        kids = sorted(((ch[0][i], san, ch) for san, ch in tn[1].items()
                       if ch[0][i] >= thr), key=lambda t: (-t[0], t[1]))
        if k is not None:
            kids = kids[:k]
        # replay this node's path once to derive the children's keys
        board.reset()
        for u in nd["ucis"]:
            board.push_uci(u)
        for cnt, san, ch in kids:
            move = board.push_san(san)
            cid = len(nodes)
            nodes.append({"path": nd["path"] + (san,),
                          "ucis": nd["ucis"] + (move.uci(),),
                          "ply": nd["ply"] + 1, "count": cnt,
                          "epd": board.epd(), "kids": [], "parent": nid})
            nd["kids"].append(cid)
            board.pop()
            stack.append((cid, ch))
    return nodes


def side_of_ply(p):
    """1-based ply p: odd = White's move, even = Black's."""
    return "White" if p % 2 == 1 else "Black"


def analyse_seq(nodes, names):
    """Transposition statistics of one sequence tree."""
    N = len(nodes)
    leaves = [n for n in nodes if not n["kids"]]
    by_epd = defaultdict(list)
    for idx, n in enumerate(nodes):
        by_epd[n["epd"]].append(idx)
    groups = {e: ids for e, ids in by_epd.items() if len(ids) > 1}
    merged_ids = {i for ids in groups.values() for i in ids}
    max_ply = max(n["ply"] for n in nodes)

    per_ply = []
    cum = 0
    for p in range(max_ply + 1):
        ids = [i for i, n in enumerate(nodes) if n["ply"] == p]
        epds = {nodes[i]["epd"] for i in ids}
        g = [e for e in epds if e in groups
             and all(nodes[j]["ply"] == p for j in groups[e])]
        # a group spanning plies is counted at its min ply
        g_span = [e for e in epds if e in groups
                  and min(nodes[j]["ply"] for j in groups[e]) == p
                  and not all(nodes[j]["ply"] == p for j in groups[e])]
        m = len([i for i in ids if i in merged_ids])
        cum += len(g) + len(g_span)
        per_ply.append({"ply": p, "nodes": len(ids), "positions": len(epds),
                        "merged": len(g) + len(g_span), "merged_nodes": m,
                        "cum": cum})

    # leaf paths
    leaf_in_group = sum(1 for n in leaves if n["epd"] in groups)
    def passes_merged(n):
        while n is not None:
            if n["epd"] in groups:
                return True
            n = nodes[n["parent"]] if n["parent"] is not None else None
        return False
    leaf_through = sum(1 for n in leaves if passes_merged(n))
    leaf_epds = {n["epd"] for n in leaves}

    # group classification
    span_plies = 0
    side_class = {"White's moves only": 0, "Black's moves only": 0, "both sides": 0}
    subtree_differs = 0
    details = []
    for e, ids in groups.items():
        mem = [nodes[i] for i in ids]
        plies = {m["ply"] for m in mem}
        if len(plies) > 1:
            span_plies += 1
        diff = set()
        L = min(len(m["ucis"]) for m in mem)
        for a in range(len(mem)):
            for b in range(a + 1, len(mem)):
                for p in range(L):
                    if mem[a]["ucis"][p] != mem[b]["ucis"][p]:
                        diff.add(p + 1)
        sides = {side_of_ply(p) for p in diff}
        if sides == {"White"}:
            side_class["White's moves only"] += 1
        elif sides == {"Black"}:
            side_class["Black's moves only"] += 1
        else:
            side_class["both sides"] += 1
        kidsets = {frozenset(nodes[c]["ucis"][-1] for c in m["kids"]) for m in mem}
        if len(kidsets) > 1:
            subtree_differs += 1
        details.append({"epd": e, "size": len(ids), "ply": min(plies),
                        "paths": [" ".join(m["path"]) for m in mem],
                        "counts": [m["count"] for m in mem],
                        "kids": [len(m["kids"]) for m in mem],
                        "sides": sides, "name": names.get(e, (None, None, None))[1]})
    details.sort(key=lambda d: (-d["size"], d["ply"], d["paths"][0]))

    # merged DAG: positions = distinct epds; edges = distinct (epd, uci)
    dag_edges = {}
    for n in nodes:
        for c in n["kids"]:
            dag_edges[(n["epd"], nodes[c]["ucis"][-1])] = nodes[c]["epd"]
    out = defaultdict(set)
    for (pe, u), ce in dag_edges.items():
        out[pe].add(ce)
    dag_leaf_positions = [e for e in by_epd if not out[e]]
    memo, cycles = {}, [0]
    def paths_from(e, onstack):
        if e in memo:
            return memo[e]
        if not out[e]:
            return 1
        if e in onstack:
            cycles[0] += 1
            return 0
        onstack.add(e)
        r = sum(paths_from(c, onstack) for c in out[e])
        onstack.discard(e)
        memo[e] = r
        return r
    dag_paths = paths_from(nodes[0]["epd"], set())

    # names
    named = [n for n in nodes if n["epd"] in names]
    unnamed_by_ply = defaultdict(int)
    for n in nodes:
        if n["epd"] not in names:
            unnamed_by_ply[n["ply"]] += 1
    named_by_transposition = sum(
        1 for n in named if tuple(names[n["epd"]][2].split()) != n["ucis"])
    def nearest_named(n):
        while n is not None:
            if n["epd"] in names:
                return True
            n = nodes[n["parent"]] if n["parent"] is not None else None
        return False
    has_named_ancestor = sum(1 for n in nodes if n["ply"] > 0 and nearest_named(n))
    named_groups = sum(1 for e in groups if e in names)
    tsv_order_in_tree = sum(
        1 for e, ids in groups.items() if e in names
        and any(tuple(names[e][2].split()) == nodes[i]["ucis"] for i in ids))
    named_leaves = sum(1 for n in leaves if n["epd"] in names)

    return {
        "N": N, "leaves": len(leaves), "positions": len(by_epd),
        "groups": len(groups), "merged_nodes": len(merged_ids),
        "max_ply": max_ply, "per_ply": per_ply,
        "first_ply": min((d["ply"] for d in details), default=None),
        "largest": details[0]["size"] if details else 0,
        "details": details, "span_plies": span_plies,
        "side_class": side_class, "subtree_differs": subtree_differs,
        "leaf_in_group": leaf_in_group, "leaf_through": leaf_through,
        "leaf_positions": len(leaf_epds),
        "dag_positions": len(by_epd), "dag_edges": len(dag_edges),
        "dag_leaf_positions": len(dag_leaf_positions), "dag_paths": dag_paths,
        "dag_cycles": cycles[0], "tree_edges": N - 1,
        "named": len(named), "unnamed": N - len(named),
        "unnamed_by_ply": dict(unnamed_by_ply),
        "named_by_transposition": named_by_transposition,
        "has_named_ancestor": has_named_ancestor,
        "named_groups": named_groups, "tsv_order_in_tree": tsv_order_in_tree,
        "named_leaves": named_leaves,
    }


# --------------------------------------------------------------------------
# Pooled DAG: cut-off on per-position counts summed over move orders
# --------------------------------------------------------------------------

def pooled_dag(pos, edges, start, i, thr, k):
    out = defaultdict(list)
    for (pe, u), rec in edges.items():
        if rec[0][i] >= thr and pos[pe][0][i] >= thr:
            out[pe].append((rec[0][i], u, rec[1]))
    for pe in out:
        out[pe].sort(key=lambda t: (-t[0], t[1]))
        if k is not None:
            out[pe] = out[pe][:k]
    seen = {start: 0}
    kept_edges = 0
    frontier = [start]
    while frontier:
        nxt = []
        for pe in frontier:
            for cnt, u, ce in out.get(pe, ()):
                kept_edges += 1
                if ce not in seen:
                    seen[ce] = seen[pe] + 1
                    nxt.append(ce)
        frontier = nxt
    memo, cycles = {}, [0]
    def paths_from(e, onstack, depth):
        if e in memo:
            return memo[e]
        kids = out.get(e, ())
        if not kids:
            return (1, depth)
        if e in onstack:
            cycles[0] += 1
            return (0, depth)
        onstack.add(e)
        tot, dmax = 0, depth
        for cnt, u, ce in kids:
            t, d = paths_from(ce, onstack, depth + 1)
            tot += t
            dmax = max(dmax, d)
        onstack.discard(e)
        memo[e] = (tot, dmax)
        return memo[e]
    paths, depth = paths_from(start, set(), 0)
    return {"positions": len(seen), "edges": kept_edges, "paths": paths,
            "depth": depth, "cycles": cycles[0], "keys": set(seen),
            "multi_order": sum(1 for e in seen if pos[e][3] > 1)}


# --------------------------------------------------------------------------
# chess-openings names
# --------------------------------------------------------------------------

def load_names(dist_path):
    names = {}
    rows = 0
    mismatch = 0
    with open(dist_path, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        assert header == ["eco", "name", "pgn", "uci", "epd"], header
        for line in fh:
            eco, name, pgn, uci, epd = line.rstrip("\n").split("\t")
            rows += 1
            b = chess.Board()
            for u in uci.split():
                b.push_uci(u)
            if b.epd() != epd:
                mismatch += 1
            names[epd] = (eco, name, uci)
    return names, rows, mismatch


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def pct(a, b):
    return "%.1f%%" % (100.0 * a / b) if b else "-"


def main():
    dump, dist, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    names, tsv_rows, tsv_mismatch = load_names(dist)
    root, n_games = build_trie(dump)
    n_trie = count_nodes(root)
    pos, edges, start, bad = pool_positions(root)
    counts = {b: root[0][i] for i, b in enumerate(BUCKETS)}

    L = []
    A = L.append
    A("<!-- generated by refs/lichess/transposition-analysis.py; do not edit by hand -->")
    A("")
    A("Dump: %d games; one trie to ply %d with %d nodes (distinct move sequences), "
      "keyed to %d distinct positions (EPD) and %d distinct (position, move) edges."
      % (n_games, PLY_CAP, n_trie, len(pos), len(edges)))
    A("Games under a SAN token python-chess rejected, per bucket: %s."
      % ", ".join("%s %d" % (b, bad[i]) for i, b in enumerate(BUCKETS)))
    A("chess-openings dist TSV: %d rows, %d distinct EPDs, %d rows whose `epd` "
      "column differs from replaying its `uci` column with python-chess."
      % (tsv_rows, len(names), tsv_mismatch))
    multi_ply = sum(1 for r in pos.values() if r[2] > r[1])
    A("Positions reached at more than one ply anywhere in the trie (a game "
      "repeating a position): %d of %d." % (multi_ply, len(pos)))
    A("")

    for i, b in enumerate(BUCKETS):
        n = counts[b]
        thr = CUTOFF_PCT / 100.0 * n
        A("## Bucket `%s` (%d games), cut-off >= %.1f%% (>= %d games)"
          % (b, n, CUTOFF_PCT, round(thr)))
        A("")
        results = {}
        for k in WIDTHS:
            nodes = seq_tree(root, i, thr, k)
            results[k] = (nodes, analyse_seq(nodes, names))
        klabel = {3: "k = 3, i.e. widths (3,3)", None: "uncapped (cut-off only)"}

        A("### Sequence tree vs position-keyed DAG")
        A("")
        A("| width | tree nodes | tree leaf paths | max ply | distinct positions | "
          "positions reached by >1 move order | nodes in them (share of nodes) | "
          "first ply with a transposition | largest group | groups spanning >1 ply | "
          "leaf paths ending on a shared position | leaf paths through >=1 shared position | "
          "distinct leaf positions |")
        A("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for k in WIDTHS:
            nodes, r = results[k]
            A("| %s | %d | %d | %d | %d | %d (%s of nodes) | %d (%s) | %s | %d | %d | %d (%s of leaf paths) | %d (%s) | %d |"
              % (klabel[k], r["N"], r["leaves"], r["max_ply"], r["positions"],
                 r["groups"], pct(r["groups"], r["positions"]),
                 r["merged_nodes"], pct(r["merged_nodes"], r["N"]),
                 r["first_ply"], r["largest"], r["span_plies"],
                 r["leaf_in_group"], pct(r["leaf_in_group"], r["leaves"]),
                 r["leaf_through"], pct(r["leaf_through"], r["leaves"]),
                 r["leaf_positions"]))
        A("")
        A("Merging the same tree by position (edges = distinct (position, move) pairs; "
          "a leaf is a position with no kept move out of it, so a sequence leaf whose "
          "position has kept moves under another move order stops being a leaf):")
        A("")
        A("| width | sequence tree: nodes / edges / leaf paths | merged DAG: positions / edges / leaf positions / root-to-leaf paths | cycles | groups where the move orders keep different replies |")
        A("|---|---|---|---|---|")
        for k in WIDTHS:
            nodes, r = results[k]
            A("| %s | %d / %d / %d | %d / %d / %d / %d | %d | %d of %d |"
              % (klabel[k], r["N"], r["tree_edges"], r["leaves"],
                 r["dag_positions"], r["dag_edges"], r["dag_leaf_positions"],
                 r["dag_paths"], r["dag_cycles"], r["subtree_differs"], r["groups"]))
        A("")

        A("### By ply (k = 3)")
        A("")
        A("| ply | nodes | distinct positions | positions reached by >1 order (first at this ply) | nodes in a shared position | cumulative shared positions |")
        A("|---|---|---|---|---|---|")
        for row in results[3][1]["per_ply"]:
            A("| %d | %d | %d | %d | %d | %d |" % (
                row["ply"], row["nodes"], row["positions"], row["merged"],
                row["merged_nodes"], row["cum"]))
        A("")
        A("Same table, uncapped:")
        A("")
        A("| ply | nodes | distinct positions | positions reached by >1 order (first at this ply) | nodes in a shared position | cumulative shared positions |")
        A("|---|---|---|---|---|---|")
        for row in results[None][1]["per_ply"]:
            A("| %d | %d | %d | %d | %d | %d |" % (
                row["ply"], row["nodes"], row["positions"], row["merged"],
                row["merged_nodes"], row["cum"]))
        A("")

        A("### Whose move order differs")
        A("")
        A("For each shared position, the plies at which its move orders differ, "
          "classified by the side that moved at those plies (odd ply = White). "
          "Side to move is part of the EPD, so every move order into a shared "
          "position has the same side to move; `groups spanning >1 ply` above "
          "counts the only way the learner's colour could differ between two "
          "paths to one position (a repetition), and is 0.")
        A("")
        A("| width | White's moves only | Black's moves only | both sides |")
        A("|---|---|---|---|")
        for k in WIDTHS:
            sc = results[k][1]["side_class"]
            A("| %s | %d | %d | %d |" % (klabel[k], sc["White's moves only"],
                                         sc["Black's moves only"], sc["both sides"]))
        A("")

        A("### Every shared position (k = 3)")
        A("")
        A("| ply | move orders | games per order | kept replies per order | differing side | chess-openings name | move orders |")
        A("|---|---|---|---|---|---|---|")
        for d in results[3][1]["details"]:
            A("| %d | %d | %s | %s | %s | %s | %s |" % (
                d["ply"], d["size"], " / ".join(map(str, d["counts"])),
                " / ".join(map(str, d["kids"])),
                "+".join(sorted(d["sides"])) or "-",
                d["name"] or "(unnamed)",
                " ; ".join("`%s`" % p for p in d["paths"])))
        A("")
        extra = [d for d in results[None][1]["details"]
                 if d["epd"] not in {x["epd"] for x in results[3][1]["details"]}]
        A("Shared positions that exist only in the uncapped tree (%d):" % len(extra))
        A("")
        A("| ply | move orders | games per order | differing side | chess-openings name | move orders |")
        A("|---|---|---|---|---|---|")
        for d in extra:
            A("| %d | %d | %s | %s | %s | %s |" % (
                d["ply"], d["size"], " / ".join(map(str, d["counts"])),
                "+".join(sorted(d["sides"])) or "-",
                d["name"] or "(unnamed)",
                " ; ".join("`%s`" % p for p in d["paths"])))
        A("")

        A("### Cut-off on pooled position counts")
        A("")
        A("Alternative build: count games per *position* (summed over every move "
          "order in the dump), keep a (position, move) edge when both the edge and "
          "its parent position reach the cut-off, keep the k most popular edges per "
          "position, take what is reachable from the start position.")
        A("")
        A("| width | pooled DAG: positions / edges / root-to-leaf paths / max depth | of which positions reached by >1 move order in the dump | positions not in the sequence tree | sequence-tree positions not in the pooled DAG | cycles |")
        A("|---|---|---|---|---|---|")
        for k in WIDTHS:
            pd = pooled_dag(pos, edges, start, i, thr, k)
            seq_keys = {n["epd"] for n in results[k][0]}
            A("| %s | %d / %d / %d / %d | %d | %d | %d | %d |" % (
                klabel[k], pd["positions"], pd["edges"], pd["paths"], pd["depth"],
                pd["multi_order"], len(pd["keys"] - seq_keys),
                len(seq_keys - pd["keys"]), pd["cycles"]))
        A("")

        A("### chess-openings names")
        A("")
        A("| width | nodes | named (exact EPD) | unnamed | unnamed by ply | named leaves / leaves | nodes at ply >= 1 with a named ancestor-or-self | named nodes reached by a move order other than the TSV's `pgn` | shared positions named | shared positions where the TSV's own move order is one of the tree's |")
        A("|---|---|---|---|---|---|---|---|---|---|")
        for k in WIDTHS:
            r = results[k][1]
            ub = ", ".join("%d: %d" % (p, c) for p, c in sorted(r["unnamed_by_ply"].items()))
            A("| %s | %d | %d (%s) | %d | %s | %d / %d | %d of %d | %d | %d of %d | %d of %d |" % (
                klabel[k], r["N"], r["named"], pct(r["named"], r["N"]), r["unnamed"],
                ub or "-", r["named_leaves"], r["leaves"],
                r["has_named_ancestor"], r["N"] - 1, r["named_by_transposition"],
                r["named_groups"], r["groups"], r["tsv_order_in_tree"], r["groups"]))
        A("")

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out_path, file=sys.stderr)


if __name__ == "__main__":
    main()
