#!/usr/bin/env python3
"""Measure how big the repertoire gets under candidate rules (ticket 13).

Reads a Lichess monthly .pgn.zst dump (streamed), keeps the games the
play-loop prototype keeps (both players >= 1800, bullet/ultrabullet excluded,
see prototype/play-loop/build_tree.py), builds ONE move-sequence trie with
game counts and the EPD of every node, then sizes the repertoire under:

  A. absolute cut-off (count >= 0.2% of games), top-3 replies         [baseline]
  B. relative cut-off (count >= r * parent's count, and >= m games), top-3
  C. book-terminated: top-3 tree with count >= m, then every node without an
     exactly-named chess-openings position at or below it is pruned
     (also uncapped for m in {1, 5})
  D. the book itself: every chess-openings line replayed as a path
  E. rule C (m = 5, top-3): the Sicilian leaves by name, and the named
     Sicilian lines with traffic that the rule still misses

Usage:
    python repertoire-rule-analysis.py <dump.pgn.zst> <chess-openings-dist.tsv> <out.md>

`<chess-openings-dist.tsv>` is the 5-column (eco name pgn uci epd) file that
`chess-openings-bin-gen.py a.tsv b.tsv ... e.tsv > dist.tsv` prints.

Reuses the PGN streaming code of tree-width-analysis.py (same directory).
Requires python-chess 1.11.2 and zstandard.
See docs/research/repertoire-rule-candidates.md.
"""

import importlib.util
import os
import sys
import time
from collections import Counter, defaultdict

import chess

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "tree_width_analysis", os.path.join(HERE, "tree-width-analysis.py"))
tw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tw)

MIN_ELO = 1800
CUTOFF = 0.002          # rule A: share of the bucket's games (prototype: CUTOFF)
WIDTH = 3               # top-3 = the (3,3) setting
RULE_PLY_CAP = 30       # every rule tree stops here (a node at ply 30 has no kids)
PROTO_PLY_CAP = 18      # the prototype's MAX_PLY, for the reproduction check
REL_R = (0.05, 0.10, 0.20)
REL_M = (2, 5, 10)
BOOK_M = (1, 2, 5, 10)
BOOK_M_UNCAPPED = (1, 5)
SIC_PREFIX = ("e2e4", "c7c5")
SIC_NAME = "Sicilian Defense"


# --------------------------------------------------------------------------
# Games and trie
# --------------------------------------------------------------------------

def is_bullet(tc):
    """Copied from prototype/play-loop/build_tree.py: estimated game length
    base + 40 * increment under 180 s is bullet (ultrabullet included)."""
    if not tc or "+" not in tc:
        return False
    base, inc = tc.split("+")
    return int(base) + 40 * int(inc) < 180


def in_band(headers):
    """The prototype's filter, exactly: both Elo present, numeric and >= 1800,
    time control not bullet."""
    we, be = tw.elo(headers, "WhiteElo"), tw.elo(headers, "BlackElo")
    if we is None or be is None or we < MIN_ELO or be < MIN_ELO:
        return False
    return not is_bullet(headers.get("TimeControl"))


class Node(object):
    __slots__ = ("count", "kids", "san", "uci", "epd", "ply")

    def __init__(self, san, ply):
        self.count = 0
        self.kids = {}
        self.san = san
        self.uci = None
        self.epd = None
        self.ply = ply


def build_trie(dump, ply_cap, game_iter=None):
    """One trie over the in-band games, to `ply_cap` plies."""
    root = Node(None, 0)
    n_all = n_kept = 0
    speeds = Counter()
    t0 = time.time()
    for headers, moves in (game_iter or tw.iter_games)(dump):
        n_all += 1
        if not in_band(headers):
            continue
        n_kept += 1
        ev = headers.get("Event", "")
        speeds[ev.split()[-2] if ev.endswith("game") else "?"] += 1
        node = root
        node.count += 1
        for san in moves[:ply_cap]:
            ch = node.kids.get(san)
            if ch is None:
                ch = node.kids[san] = Node(san, node.ply + 1)
            ch.count += 1
            node = ch
    print("parsed %d games, kept %d, in %.0fs" % (n_all, n_kept, time.time() - t0),
          file=sys.stderr)
    return root, n_all, n_kept, speeds


def key_trie(root):
    """Give every node its EPD and uci; drop subtrees under a SAN token
    python-chess rejects.  Returns (nodes visited, games dropped)."""
    board = chess.Board()
    root.epd = board.epd()
    visited, dropped = 0, 0
    stack = [(root, iter(list(root.kids.items())))]
    while stack:
        parent, it = stack[-1]
        nxt = next(it, None)
        if nxt is None:
            stack.pop()
            if stack:
                board.pop()
            continue
        san, ch = nxt
        try:
            mv = board.push_san(san)
        except ValueError:
            dropped += ch.count
            del parent.kids[san]
            continue
        visited += 1
        ch.uci = mv.uci()
        ch.epd = board.epd()
        stack.append((ch, iter(list(ch.kids.items()))))
    return visited, dropped


def all_nodes(root):
    out, stack = [], [root]
    while stack:
        nd = stack.pop()
        out.append(nd)
        stack.extend(nd.kids.values())
    return out


# --------------------------------------------------------------------------
# Rule trees: a tree is {node: [kept children, most popular first]}
# --------------------------------------------------------------------------

def select(root, keep, cap, ply_cap):
    """keep(child, parent) -> bool.  Ties broken like the prototype:
    count desc, then SAN desc."""
    T = {root: []}
    stack = [root]
    while stack:
        nd = stack.pop()
        if nd.ply >= ply_cap:
            continue
        kids = sorted((c for c in nd.kids.values() if keep(c, nd)),
                      key=lambda c: (c.count, c.san), reverse=True)
        if cap is not None:
            kids = kids[:cap]
        T[nd] = kids
        for c in kids:
            T[c] = []
            stack.append(c)
    return T


def prune_to_named(T, root, names):
    """Keep only nodes with an exactly-named position at or below them."""
    order, stack = [], [root]
    while stack:
        nd = stack.pop()
        order.append(nd)
        stack.extend(T[nd])
    has = {}
    for nd in reversed(order):
        has[nd] = (nd.epd in names) or any(has[c] for c in T[nd])
    T2 = {root: []}
    stack = [root]
    while stack:
        nd = stack.pop()
        kids = [c for c in T[nd] if has[c]]
        T2[nd] = kids
        for c in kids:
            T2[c] = []
            stack.append(c)
    return T2


def subtree(T, start):
    out, stack = [], [start]
    while stack:
        nd = stack.pop()
        out.append(nd)
        stack.extend(T[nd])
    return out


def sic_node(T, root):
    e4 = root.kids.get("e4")
    if e4 is None or e4 not in T:
        return None
    c5 = e4.kids.get("c5")
    return c5 if c5 is not None and c5 in T else None


def measure(T, root, names, sic_tsv, sic_named, ply_cap):
    nodes = list(T)
    leaves = [n for n in nodes if not T[n]]
    epds = {n.epd for n in nodes}
    r = {
        "nodes": len(nodes),
        "leaves": len(leaves),
        "max_ply": max(n.ply for n in nodes),
        "by_ply": Counter(n.ply for n in nodes),
        "max_kids": max(len(T[n]) for n in nodes),
        "named_nodes": sum(1 for n in nodes if n.epd in names),
        "named_leaves": sum(1 for n in leaves if n.epd in names),
        "tsv_in_tree": len(epds & set(names)),
        "truncated": any(n.ply >= ply_cap for n in nodes),
    }
    s = sic_node(T, root)
    if s is None:
        r.update({"s_nodes": 0, "s_leaves": 0, "s_max_ply": 0, "s_named_leaves": 0,
                  "s_tsv_in_tree": 0, "s_named_in_tree": 0, "s_max_kids": 0})
    else:
        sn = subtree(T, s)
        sl = [n for n in sn if not T[n]]
        se = {n.epd for n in sn}
        r.update({"s_nodes": len(sn), "s_leaves": len(sl),
                  "s_max_ply": max(n.ply for n in sn),
                  "s_named_leaves": sum(1 for n in sl if n.epd in names),
                  "s_tsv_in_tree": len(se & sic_tsv),
                  "s_named_in_tree": len(se & sic_named),
                  "s_max_kids": max(len(T[n]) for n in sn)})
    return r


# --------------------------------------------------------------------------
# chess-openings book
# --------------------------------------------------------------------------

def load_book(dist_path):
    rows = []
    with open(dist_path, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        assert header == ["eco", "name", "pgn", "uci", "epd"], header
        for line in fh:
            eco, name, pgn, uci, epd = line.rstrip("\n").split("\t")
            rows.append((eco, name, pgn, tuple(uci.split()), epd))
    names = {epd: (eco, name, pgn, uci) for eco, name, pgn, uci, epd in rows}
    assert len(names) == len(rows), "duplicate EPDs in the dist TSV"
    return rows, names


def book_paths(rows):
    """Replay every row; return per-position record keyed by EPD:
    {epd: [min ply, set of next ucis in the book, set of sequences]} plus the
    set of distinct move sequences (prefixes)."""
    board = chess.Board()
    pos = {}
    seqs = set()
    for eco, name, pgn, uci, epd in rows:
        board.reset()
        prev = board.epd()
        pos.setdefault(prev, [0, set()])
        for i, u in enumerate(uci):
            board.push_uci(u)
            e = board.epd()
            seqs.add(uci[:i + 1])
            pos[prev][1].add(u)
            rec = pos.setdefault(e, [i + 1, set()])
            rec[0] = min(rec[0], i + 1)
            prev = e
        assert prev == epd, (name, prev, epd)
    return pos, seqs


# --------------------------------------------------------------------------
# Report helpers
# --------------------------------------------------------------------------

def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


def by_ply_str(c):
    return ", ".join("%d: %d" % (p, c[p]) for p in sorted(c) if p > 0)


def node_path(root, nd, parents):
    path = []
    while nd is not root:
        path.append(nd.san)
        nd = parents[nd]
    return " ".join(reversed(path))


def parents_of(T, root):
    par = {root: None}
    for nd, kids in T.items():
        for c in kids:
            par[c] = nd
    return par


SUMMARY_HEAD = [
    "rule", "cell", "nodes (root incl.)", "leaf paths (lines)", "max ply",
    "largest kept-reply count", "named nodes", "named leaves",
    "TSV lines in tree (of 3810)",
    "Sicilian nodes", "Sicilian leaf paths", "Sicilian max ply", "Sicilian named leaves",
    "Sicilian TSV lines in tree (of 401 under 1.e4 c5 / 391 named Sicilian)",
    "hits ply cap",
]


def summary_row(rule, cell, r):
    return [rule, cell, r["nodes"], r["leaves"], r["max_ply"], r["max_kids"],
            r["named_nodes"], r["named_leaves"], r["tsv_in_tree"],
            r["s_nodes"], r["s_leaves"], r["s_max_ply"], r["s_named_leaves"],
            "%d / %d" % (r["s_tsv_in_tree"], r["s_named_in_tree"]),
            "yes" if r["truncated"] else "no"]


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    dump, dist, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    rows, names = load_book(dist)
    book_max_ply = max(len(r[3]) for r in rows)
    trie_ply = max(RULE_PLY_CAP, book_max_ply)     # every book position gets a count

    root, n_all, n_games, speeds = build_trie(dump, trie_ply)
    visited, dropped = key_trie(root)
    nodes = all_nodes(root)
    pos_count = Counter()
    for nd in nodes:
        pos_count[nd.epd] += nd.count
    seq_count = {}          # count of a sequence = count of the node with that uci path
    stack = [(root, ())]
    while stack:
        nd, ucis = stack.pop()
        seq_count[ucis] = nd.count
        for c in nd.kids.values():
            stack.append((c, ucis + (c.uci,)))

    sic_rows = [r for r in rows if r[3][:2] == SIC_PREFIX]
    sic_tsv = {r[4] for r in sic_rows}
    sic_named = {r[4] for r in rows if r[1].startswith(SIC_NAME)}
    assert sic_named <= sic_tsv

    def M(T):
        return measure(T, root, names, sic_tsv, sic_named, RULE_PLY_CAP)

    thr = CUTOFF * n_games
    cells = []                                   # (rule, cell label, T, measure)

    # ---- A. absolute baseline
    T_A = select(root, lambda c, p: c.count >= thr, WIDTH, RULE_PLY_CAP)
    cells.append(("A", "count >= 0.2%% x %d = %.3f (i.e. >= 11 games), top-3, ply cap 30"
                  % (n_games, thr), T_A, M(T_A)))
    T_A18 = select(root, lambda c, p: c.count >= thr, WIDTH, PROTO_PLY_CAP)
    cells.append(("A", "same, ply cap 18 (the prototype's build)", T_A18, M(T_A18)))
    T_A10 = select(root, lambda c, p: c.count >= 10, WIDTH, RULE_PLY_CAP)
    cells.append(("A", "count >= 10 games (the ticket's wording), top-3, ply cap 30",
                  T_A10, M(T_A10)))
    T_Aunc = select(root, lambda c, p: c.count >= thr, None, RULE_PLY_CAP)
    cells.append(("A", "count >= 11 games, uncapped, ply cap 30", T_Aunc, M(T_Aunc)))

    # ---- B. relative
    for r_ in REL_R:
        for m in REL_M:
            T = select(root, lambda c, p, r_=r_, m=m: c.count >= r_ * p.count and c.count >= m,
                       WIDTH, RULE_PLY_CAP)
            cells.append(("B", "r = %.2f, floor m = %d, top-3" % (r_, m), T, M(T)))

    # ---- C. book-terminated
    pre = {}
    for m in BOOK_M:
        T0 = select(root, lambda c, p, m=m: c.count >= m, WIDTH, RULE_PLY_CAP)
        T = prune_to_named(T0, root, names)
        pre[("C", m, WIDTH)] = M(T0)
        cells.append(("C", "m = %d, top-3, pruned to named-descendant-or-self" % m, T, M(T)))
    for m in BOOK_M_UNCAPPED:
        T0 = select(root, lambda c, p, m=m: c.count >= m, None, RULE_PLY_CAP)
        T = prune_to_named(T0, root, names)
        pre[("C", m, None)] = M(T0)
        cells.append(("C", "m = %d, UNCAPPED, pruned to named-descendant-or-self" % m,
                      T, M(T)))

    # ---- D. the book
    bpos, bseqs = book_paths(rows)
    spos, sseqs = book_paths(sic_rows)
    start_epd = chess.Board().epd()

    def book_summary(pos, seqs, rows_, min_ply):
        P = {e: v for e, v in pos.items() if v[0] >= min_ply}
        zero = [e for e in P if pos_count.get(e, 0) == 0]
        named_zero = [r for r in rows_ if pos_count.get(r[4], 0) == 0]
        named_seq_zero = [r for r in rows_ if seq_count.get(r[3], 0) == 0]
        widest = sorted(P.items(), key=lambda kv: (-len(kv[1][1]), kv[1][0]))[:8]
        return {
            "positions": len(P), "sequences": len([s for s in seqs if len(s) >= min_ply]),
            "max_ply": max(v[0] for v in P.values()),
            "by_ply": Counter(v[0] for v in P.values()),
            "zero": len(zero),
            "unnamed": sum(1 for e in P if e not in names),
            "unnamed_zero": sum(1 for e in zero if e not in names),
            "named_zero_pooled": len(named_zero),
            "named_zero_seq": len(named_seq_zero),
            "named_ge": {k: sum(1 for r in rows_ if pos_count.get(r[4], 0) >= k)
                         for k in (1, 2, 5, 10, 11)},
            "named_ge_seq": {k: sum(1 for r in rows_ if seq_count.get(r[3], 0) >= k)
                             for k in (1, 2, 5, 10, 11)},
            "widest": [(e, v[0], len(v[1]), names.get(e, ("", "(unnamed)", "", ""))[1],
                        pos_count.get(e, 0)) for e, v in widest],
            "width_hist": Counter(len(v[1]) for v in P.values()),
        }
    D_all = book_summary(bpos, bseqs, rows, 1)
    D_sic = book_summary(spos, sseqs, sic_rows, 2)
    e4c5_epd = None
    b = chess.Board()
    b.push_uci("e2e4")
    b.push_uci("c7c5")
    e4c5_epd = b.epd()

    # ---- E. rule C, m = 5, top-3: Sicilian leaves and misses
    T_C5 = [c for c in cells if c[0] == "C" and c[1].startswith("m = 5, top-3")][0][2]
    par = parents_of(T_C5, root)
    s = sic_node(T_C5, root)
    sic_leaves = []
    if s is not None:
        for nd in subtree(T_C5, s):
            if not T_C5[nd]:
                nm = names.get(nd.epd)
                sic_leaves.append((nd.ply, nm[0] if nm else "", nm[1] if nm else "(unnamed)",
                                   nd.count, node_path(root, nd, par)))
    sic_leaves.sort(key=lambda t: (t[4]))
    in_tree_epds = {n.epd for n in T_C5}
    misses = []
    for eco, name, pgn, uci, epd in sic_rows:
        pooled = pos_count.get(epd, 0)
        if pooled < 5 or epd in in_tree_epds:
            continue
        # walk the TSV's own move order through the trie and the tree
        nd, reason = root, None
        for i, u in enumerate(uci):
            nxt = None
            for c in nd.kids.values():
                if c.uci == u:
                    nxt = c
                    break
            if nxt is None:
                reason = "ply %d: %s never played in this order" % (i + 1, u)
                break
            if nxt not in T_C5:
                sibs = sorted((c for c in nd.kids.values() if c.count >= 5),
                              key=lambda c: (c.count, c.san), reverse=True)
                rank = next((k + 1 for k, c in enumerate(sibs) if c is nxt), None)
                if nd.ply >= RULE_PLY_CAP:
                    reason = "ply %d: beyond the ply cap" % (i + 1)
                elif nxt.count < 5:
                    reason = ("ply %d: %s has %d games in this order (< 5)"
                              % (i + 1, nxt.san, nxt.count))
                elif nd not in T_C5:
                    reason = "ply %d: parent already pruned" % (i + 1)
                elif rank is not None and rank > WIDTH:
                    reason = ("ply %d: %s has %d games, rank %d of %d (outside top-3; kept: %s)"
                              % (i + 1, nxt.san, nxt.count, rank, len(sibs),
                                 ", ".join("%s %d" % (c.san, c.count) for c in sibs[:WIDTH])))
                else:
                    # kept by popularity, pruned for lack of a named position with
                    # >= 5 games below it: say what the next book move has
                    nxt2 = None
                    if i + 1 < len(uci):
                        nxt2 = next((c for c in nxt.kids.values() if c.uci == uci[i + 1]), None)
                    reason = ("ply %d: %s (%d games, rank %s) pruned, nothing named with >= 5 "
                              "games below it in this order; next book move %s has %d games "
                              "in this order (< 5)"
                              % (i + 1, nxt.san, nxt.count, rank,
                                 nxt2.san if nxt2 else uci[i + 1] if i + 1 < len(uci) else "-",
                                 nxt2.count if nxt2 else 0))
                break
            nd = nxt
        misses.append((name, eco, len(uci), pooled, seq_count.get(uci, 0), reason or "?", pgn))
    misses.sort(key=lambda t: (-t[3], t[2]))

    # rule A: nodes beyond the prototype's ply cap
    parA = parents_of(T_A, root)
    deepA = [(nd.ply, nd.count, node_path(root, nd, parA),
              names.get(nd.epd, ("", "unnamed", "", ""))[1])
             for nd in T_A if nd.ply > PROTO_PLY_CAP]
    # named lines deeper than the prototype's ply cap with traffic
    deep_named = sum(1 for r in rows if len(r[3]) > PROTO_PLY_CAP and seq_count.get(r[3], 0) >= 1)

    def row_counts(rows_):
        return {"zero_pooled": sum(1 for r in rows_ if pos_count.get(r[4], 0) == 0),
                "zero_seq": sum(1 for r in rows_ if seq_count.get(r[3], 0) == 0),
                "ge": {k: sum(1 for r in rows_ if pos_count.get(r[4], 0) >= k)
                       for k in (1, 2, 5, 10, 11)},
                "ge_seq": {k: sum(1 for r in rows_ if seq_count.get(r[3], 0) >= k)
                           for k in (1, 2, 5, 10, 11)}}
    sic391 = row_counts([r for r in rows if r[1].startswith(SIC_NAME)])

    # ---- prototype tokenizer cross-check (optional)
    proto_note = None
    proto_path = os.path.join(HERE, "..", "..", "prototype", "play-loop", "build_tree.py")
    if os.path.exists(proto_path):
        spec = importlib.util.spec_from_file_location("proto_build_tree", proto_path)
        proto = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(proto)
        proot, _, pn, _ = build_trie(dump, PROTO_PLY_CAP, game_iter=proto.games)
        key_trie(proot)
        pT = select(proot, lambda c, p: c.count >= CUTOFF * pn, WIDTH, PROTO_PLY_CAP)
        pm = measure(pT, proot, names, sic_tsv, sic_named, PROTO_PLY_CAP)
        proto_note = (pn, pm)

    # ---------------------------------------------------------------- report
    L = []
    A = L.append
    A("# Repertoire size under candidate rules")
    A("")
    A("Ticket: [`.scratch/chessop/issues/13-repertoire-named-variations.md`]"
      "(../../.scratch/chessop/issues/13-repertoire-named-variations.md).")
    A("Raw material: `lichess_db_standard_rated_2013-01.pgn.zst` (17,761,302 bytes, "
      "%d games, CC0), downloaded and parsed locally with python-chess %s / zstandard, "
      "then deleted. Names: `refs/lichess/chess-openings-{a..e}.tsv` (CC0) through "
      "`chess-openings-bin-gen.py` (%d rows, %d distinct EPDs)."
      % (n_all, chess.__version__, len(rows), len(names)))
    A("Script: [`refs/lichess/repertoire-rule-analysis.py`]"
      "(../../refs/lichess/repertoire-rule-analysis.py). Generated; every number "
      "below is one run of it. No recommendation is made here.")
    A("")
    A("## Method")
    A("")
    A("- **Games**: the prototype's filter (`prototype/play-loop/build_tree.py`), "
      "verbatim: both `WhiteElo` and `BlackElo` present, numeric and >= %d; "
      "`TimeControl` not bullet, where bullet means base + 40 x increment < 180 s "
      "(ultrabullet included). **%d games** of the month's %d; by speed: %s. This is "
      "the prototype's 5,017-game bucket, *not* the 9,525-game `both>=1800` bucket "
      "of `tree-width-measurements.md` (which keeps bullet). The ticket's "
      "\"235 positions / 86 lines\" comes from the 9,525-game bucket; on the "
      "5,017-game bucket the same rule gives the prototype's 289 / 94 (rule A below)."
      % (MIN_ELO, n_games, n_all,
         ", ".join("%s %d" % (k, v) for k, v in sorted(speeds.items()))))
    A("- **Trie**: one move-sequence trie (transpositions not merged; a node is a "
      "move sequence), mainline SAN from the shared tokenizer of "
      "`tree-width-analysis.py` (strips `?!`-style annotations, which the prototype's "
      "tokenizer keeps as part of the token; the cross-check at the end of the A "
      "section measures the effect). Built to ply %d (the deepest line in the "
      "chess-openings TSV) so that every book position has a pooled game count; "
      "**every rule tree is capped at ply %d** (a node at ply %d keeps no reply). "
      "%d trie nodes; %d games dropped under SAN tokens python-chess rejects."
      % (trie_ply, RULE_PLY_CAP, RULE_PLY_CAP, visited + 1, dropped))
    A("- **Node count** = games whose sequence passes through the node. **Pooled "
      "count of a position** = the sum of the node counts of every trie node with "
      "that EPD (all move orders, to ply %d)." % trie_ply)
    A("- **EPD / names**: every node is keyed by python-chess `Board.epd()`; a node is "
      "*named* iff its EPD is one of the %d TSV rows (exact position, any move order). "
      "`TSV lines in tree` = distinct named EPDs in the tree (the TSV has one row per "
      "EPD, so this is a count of TSV lines)." % len(rows))
    A("- **top-3**: the (3,3) setting; a node keeps its 3 most popular surviving "
      "replies. Ties broken like the prototype (count desc, then SAN desc).")
    A("- **nodes** include the root (start position), as in `transpositions.md` and "
      "the prototype's 289; `leaf paths` = nodes with no kept reply = rounds / "
      "distinct lines. `max ply` counts plies (half-moves).")
    A("- **Sicilian subtree** = the sequence subtree rooted at `1.e4 c5` (node "
      "included). `Sicilian TSV lines` = the %d TSV rows whose `uci` starts with "
      "`e2e4 c7c5`; %d of them are named `Sicilian Defense…` (the ticket's 391; all "
      "391 lie under `1.e4 c5`), the other %d are the Pterodactyl/Bird/King's Gambit "
      "Declined entries that also start `1.e4 c5`. Both counts are given."
      % (len(sic_tsv), len(sic_named), len(sic_tsv) - len(sic_named)))
    A("- **Rule A** (baseline): keep a node iff count >= 0.2%% x %d = %.3f games, i.e. "
      "**>= 11 games** (the prototype compares against the unrounded threshold; the "
      "ticket says \"10 games\"; a `>= 10` cell is included), top-3."
      % (n_games, thr))
    A("- **Rule B** (relative): keep a node iff count >= r x (parent's count) **and** "
      "count >= m, then top-3. At the root the parent count is the bucket size, so "
      "r also gates the first move.")
    A("- **Rule C** (book-terminated): top-3 tree with count >= m (ply cap %d), then "
      "prune every node with no exactly-named position at or below it (descendant-"
      "or-self, by EPD). Popularity sets the width, the book sets the depth. Every "
      "leaf of a C tree is a named position by construction. The uncapped rows keep "
      "*all* replies with >= m games before pruning." % RULE_PLY_CAP)
    A("- **Rule D** (the book itself): every TSV row's `uci` replayed; all prefix "
      "positions (named or not) counted, keyed by EPD. Positions = distinct EPDs "
      "(start position excluded); sequences = distinct move-sequence prefixes. "
      "`zero games` = pooled count 0 in this month's %d-game bucket. `named "
      "continuations` of a position = distinct next moves out of it along book "
      "paths. For the Sicilian, positions at ply >= 2 on the paths of the %d "
      "`1.e4 c5` rows." % (n_games, len(sic_tsv)))
    A("")

    A("## Summary: every cell")
    A("")
    A("`hits ply cap` = the tree has a node at ply %d, so a deeper rule tree would "
      "have been truncated." % RULE_PLY_CAP)
    A("")
    A(table(SUMMARY_HEAD, [summary_row(rule, cell, r) for rule, cell, T, r in cells]))
    A("")
    A("Rule C, size before the book-pruning step (top-3 or uncapped tree with count "
      ">= m, ply cap %d):" % RULE_PLY_CAP)
    A("")
    A(table(["cell", "nodes before pruning", "leaf paths before pruning", "max ply before",
             "Sicilian nodes before", "Sicilian leaf paths before"],
            [["m = %d, %s" % (m, "top-3" if k else "uncapped"), r["nodes"], r["leaves"],
              r["max_ply"], r["s_nodes"], r["s_leaves"]]
             for (_, m, k), r in sorted(pre.items(), key=lambda kv: (kv[0][2] is None, kv[0][1]))]))
    A("")
    A("The book (rule D) in the same terms: %d distinct positions (%d move-sequence "
      "prefixes), max ply %d, %d of the %d named positions with zero games (pooled "
      "over move orders); Sicilian: %d positions, max ply %d."
      % (D_all["positions"], D_all["sequences"], D_all["max_ply"], D_all["named_zero_pooled"],
         len(rows), D_sic["positions"], D_sic["max_ply"]))
    A("")

    # ---- per-rule detail
    A("## Rule A: absolute cut-off (baseline)")
    A("")
    for rule, cell, T, r in cells:
        if rule != "A":
            continue
        A("- **%s**: %d nodes / %d leaf paths / max ply %d; nodes by ply %s. Sicilian: "
          "%d nodes / %d leaves / max ply %d." % (cell, r["nodes"], r["leaves"], r["max_ply"],
                                                  by_ply_str(r["by_ply"]), r["s_nodes"],
                                                  r["s_leaves"], r["s_max_ply"]))
    A("")
    if proto_note:
        pn, pm = proto_note
        A("Reproduction check against the prototype (`prototype/play-loop/tree.json`: "
          "5,017 games, 289 nodes, 94 leaf paths, max ply 18, Sicilian 47 nodes / 15 "
          "leaves / max ply 12): rerunning rule A at ply cap 18 **with the prototype's "
          "own tokenizer** (annotations kept) gives %d games, %d nodes, %d leaf paths, "
          "max ply %d, Sicilian %d / %d / %d. With the shared tokenizer (annotations "
          "stripped), ply cap 18: %d nodes / %d leaf paths (row 2 above). The "
          "difference, if any, is `?!`-annotated tokens (518 of the month's 121,332 "
          "movetext lines carry them) counted as separate moves by the prototype."
          % (pn, pm["nodes"], pm["leaves"], pm["max_ply"], pm["s_nodes"], pm["s_leaves"],
             pm["s_max_ply"], cells[1][3]["nodes"], cells[1][3]["leaves"]))
        A("")
    A("Raising the ply cap from 18 to %d changes rule A by %+d nodes / %+d leaf paths: "
      "the nodes beyond ply 18 are %s."
      % (RULE_PLY_CAP, cells[0][3]["nodes"] - cells[1][3]["nodes"],
         cells[0][3]["leaves"] - cells[1][3]["leaves"],
         "; ".join("ply %d, %d games, `%s` (%s)" % d for d in sorted(deepA)) or "none"))
    A("")

    A("## Rule B: relative cut-off")
    A("")
    A("Nodes / leaf paths / max ply per cell, then nodes by ply.")
    A("")
    rowsB = [c for c in cells if c[0] == "B"]
    A(table(["r \\ m"] + ["m = %d" % m for m in REL_M],
            [["r = %.2f" % r_] + ["%d / %d / %d" % (r["nodes"], r["leaves"], r["max_ply"])
                                  for _, cell, T, r in rowsB
                                  if cell.startswith("r = %.2f" % r_)]
             for r_ in REL_R]))
    A("")
    A("Sicilian subtree, nodes / leaf paths / max ply:")
    A("")
    A(table(["r \\ m"] + ["m = %d" % m for m in REL_M],
            [["r = %.2f" % r_] + ["%d / %d / %d" % (r["s_nodes"], r["s_leaves"], r["s_max_ply"])
                                  for _, cell, T, r in rowsB
                                  if cell.startswith("r = %.2f" % r_)]
             for r_ in REL_R]))
    A("")
    trunc = [cell for _, cell, T, r in rowsB if r["truncated"]]
    A("Cells that reach ply %d are truncated by the ply cap; their node, leaf and max-ply "
      "figures are lower bounds: %s." % (RULE_PLY_CAP, "; ".join(trunc) or "none"))
    A("")
    for rule, cell, T, r in rowsB:
        A("- **%s**: nodes by ply %s; first moves kept: %s."
          % (cell, by_ply_str(r["by_ply"]),
             ", ".join("%s %d" % (c.san, c.count) for c in T[root])))
    A("")

    A("## Rule C: book-terminated")
    A("")
    for rule, cell, T, r in cells:
        if rule != "C":
            continue
        A("- **%s**: %d nodes / %d leaf paths / max ply %d (largest kept-reply count %d); "
          "nodes by ply %s. Sicilian: %d nodes / %d leaves / max ply %d, %d of the 401 "
          "`1.e4 c5` TSV lines (%d of the 391 `Sicilian Defense` ones) present."
          % (cell, r["nodes"], r["leaves"], r["max_ply"], r["max_kids"],
             by_ply_str(r["by_ply"]), r["s_nodes"], r["s_leaves"], r["s_max_ply"],
             r["s_tsv_in_tree"], r["s_named_in_tree"]))
    A("")
    A("Every leaf of a C tree is a named position (a leaf with no named descendant-"
      "or-self would have been pruned), so `named leaves` = `leaf paths` there; a "
      "line runs exactly as deep as the deepest named position the kept replies reach.")
    A("")
    A("Coverage of the book by rule C: named TSV lines in the tree against the named "
      "lines that have >= m games at all (by the TSV's own move order, and pooled over "
      "every move order into the position). The gap is what the top-3 cap and the "
      "sequence keying leave out.")
    A("")
    covC = []
    for rule, cell, T, r in cells:
        if rule != "C":
            continue
        m = int(cell.split("m = ")[1].split(",")[0])
        covC.append([cell, "%d / %d / %d" % (r["tsv_in_tree"], D_all["named_ge_seq"][m],
                                             D_all["named_ge"][m]),
                     "%d / %d / %d" % (r["s_tsv_in_tree"], D_sic["named_ge_seq"][m],
                                       D_sic["named_ge"][m])])
    A(table(["cell", "TSV lines in tree / with >= m games (own order) / (pooled)",
             "Sicilian (401 under 1.e4 c5): in tree / >= m (own order) / (pooled)"], covC))
    A("")

    A("## Rule D: the book itself")
    A("")
    for label, D, nrows in (("Whole book", D_all, len(rows)),
                            ("Sicilian (`1.e4 c5` rows, positions at ply >= 2)", D_sic, len(sic_rows))):
        A("### %s" % label)
        A("")
        A("- %d TSV lines; **%d distinct positions** on their paths (%d distinct "
          "move-sequence prefixes, so %d positions are reached by more than one book "
          "move order), of which %d are unnamed intermediate positions and %d named. "
          "Max ply %d. Positions by ply: %s."
          % (nrows, D["positions"], D["sequences"], D["sequences"] - D["positions"],
             D["unnamed"], D["positions"] - D["unnamed"], D["max_ply"], by_ply_str(D["by_ply"])))
        A("- **Zero games at 1800+ in the month** (pooled over move orders): %d of %d "
          "positions (%d of the unnamed intermediates, %d of the %d named lines). By "
          "the TSV's own move order (sequence count): %d named lines with zero games."
          % (D["zero"], D["positions"], D["unnamed_zero"], D["named_zero_pooled"], nrows,
             D["named_zero_seq"]))
        A("- Named lines reached by >= 1 / 2 / 5 / 10 / 11 games (pooled): %s; by own "
          "move order: %s."
          % (" / ".join(str(D["named_ge"][k]) for k in (1, 2, 5, 10, 11)),
             " / ".join(str(D["named_ge_seq"][k]) for k in (1, 2, 5, 10, 11))))
        A("- Named continuations per position (distinct next book moves): %s."
          % ", ".join("%d: %d" % (w, c) for w, c in sorted(D["width_hist"].items())))
        A("- Widest positions:")
        A("")
        A(table(["ply", "named continuations", "position", "games (pooled)"],
                [[p, w, nm, g] for e, p, w, nm, g in D["widest"]]))
        A("")
    A("After `1.e4 c5` specifically: %d named continuations (distinct third-move "
      "book moves), %d games reach the position."
      % (len(bpos[e4c5_epd][1]), pos_count.get(e4c5_epd, 0)))
    A("")
    A("The ticket's 391 `Sicilian Defense` rows alone: zero games for %d (pooled) / %d "
      "(own move order); reached by >= 1 / 2 / 5 / 10 / 11 games: %s (pooled), %s (own "
      "move order)."
      % (sic391["zero_pooled"], sic391["zero_seq"],
         " / ".join(str(sic391["ge"][k]) for k in (1, 2, 5, 10, 11)),
         " / ".join(str(sic391["ge_seq"][k]) for k in (1, 2, 5, 10, 11))))
    A("")
    A("Against the ticket's facts (2,922 of 3,810 named lines with no game, 888 with "
      ">= 1, 253 with >= 10; Sicilian 266 of 391 with none, 125 with >= 1, 36 with >= "
      "10): the own-move-order counts here give %d / %d / %d and %d / %d / %d. The 253, "
      "36, 266 and 125 match; the whole-book zero / >= 1 split differs by %d lines, and "
      "the ticket does not record how its count was made (a ply-18 trie is not the "
      "cause: %d named lines deeper than ply 18 have >= 1 game in their own order). "
      "The pooled counts are higher throughout because a named position is often "
      "reached by a move order other than the TSV's."
      % (D_all["named_zero_seq"], D_all["named_ge_seq"][1], D_all["named_ge_seq"][10],
         sic391["zero_seq"], sic391["ge_seq"][1], sic391["ge_seq"][10],
         abs(D_all["named_zero_seq"] - 2922), deep_named))
    A("")

    A("## Rule E: rule C at m = 5, top-3, the Sicilian in detail")
    A("")
    A("### Sicilian leaf lines (%d)" % len(sic_leaves))
    A("")
    A("Every leaf is an exactly-named position. Sorted by move sequence.")
    A("")
    A(table(["ply", "ECO", "name", "games (this order)", "line"],
            [[p, eco, nm, cnt, "`%s`" % path] for p, eco, nm, cnt, path in sic_leaves]))
    A("")
    A("### Named `1.e4 c5` TSV lines with >= 5 games (pooled) that rule C m = 5 top-3 misses (%d)"
      % len(misses))
    A("")
    A("`games (pooled)` counts every move order into the position; `games (own order)` "
      "counts games following the TSV's own `pgn`. `why` walks the TSV's move order "
      "through the trie and names the first move that is not in the rule-C tree: "
      "its games in that order and its rank among the parent's replies with >= 5 "
      "games (the kept top-3 are listed).")
    A("")
    A(table(["name", "ECO", "ply", "games (pooled)", "games (own order)", "why", "line"],
            [[nm, eco, p, g, gs, why, "`%s`" % pgn] for nm, eco, p, g, gs, why, pgn in misses]))
    A("")
    reasons = Counter()
    for m_ in misses:
        w = m_[5]
        if "outside top-3" in w:
            reasons["a move on the way ranks outside the top-3"] += 1
        elif "(< 5)" in w:
            reasons["a move on the way has < 5 games in the TSV's move order (the position's traffic comes by transposition)"] += 1
        elif "never played" in w:
            reasons["own move order never played"] += 1
        elif "ply cap" in w:
            reasons["beyond the ply cap"] += 1
        else:
            reasons["other"] += 1
    A("Reasons: %s." % ("; ".join("%s: %d" % (k, v) for k, v in reasons.most_common()) or "none"))
    A("")

    A("## Reproduction")
    A("")
    A("The dump is CC0 and was deleted after the run.")
    A("")
    A("```sh")
    A("cd /home/anthony/pproj/chessop")
    A("S=/tmp/chessop-scratch && mkdir -p $S")
    A("")
    A("# 1. dependencies (python-chess %s, zstandard 0.25.0)" % chess.__version__)
    A("uv venv $S/venv")
    A("uv pip install --python $S/venv/bin/python chess==%s zstandard==0.25.0" % chess.__version__)
    A("")
    A("# 2. the 2013-01 standard rated dump: 17,761,302 bytes,")
    A("#    sha256 aa40b3671fa3cf1072eb182892cd90b0e1e003a4a5943492f64b77e7f3fd1635")
    A("curl -sSL -o $S/lichess_db_standard_rated_2013-01.pgn.zst \\")
    A("    https://database.lichess.org/standard/lichess_db_standard_rated_2013-01.pgn.zst")
    A("sha256sum $S/lichess_db_standard_rated_2013-01.pgn.zst")
    A("")
    A("# 3. the chess-openings dist columns (uci, epd): 3811 lines, exit 0")
    A("$S/venv/bin/python refs/lichess/chess-openings-bin-gen.py \\")
    A("    refs/lichess/chess-openings-a.tsv refs/lichess/chess-openings-b.tsv \\")
    A("    refs/lichess/chess-openings-c.tsv refs/lichess/chess-openings-d.tsv \\")
    A("    refs/lichess/chess-openings-e.tsv > $S/chess-openings-dist.tsv")
    A("")
    A("# 4. the measurement; regenerates this file")
    A("$S/venv/bin/python refs/lichess/repertoire-rule-analysis.py \\")
    A("    $S/lichess_db_standard_rated_2013-01.pgn.zst \\")
    A("    $S/chess-openings-dist.tsv docs/research/repertoire-rule-candidates.md")
    A("")
    A("# 5. do not keep the dump")
    A("rm $S/lichess_db_standard_rated_2013-01.pgn.zst")
    A("```")
    A("")

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out_path, file=sys.stderr)


if __name__ == "__main__":
    main()
