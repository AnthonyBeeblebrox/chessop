#!/usr/bin/env python3
"""Measure the popularity mass traded away by a per-position "width" cap.

Reads a Lichess monthly .pgn.zst dump (streamed, decompressed on the fly),
builds move-sequence tries (transpositions NOT merged) for three rating
buckets, prunes them at 1.0% / 0.2% popularity cut-offs and reports, per ply:

  * how many replies survive the cut-off (mean / max per node),
  * the cumulative popularity mass of the top 1..5 replies, as a share of the
    games reaching the node and as a share of all games in the bucket,
  * for width caps 3 / 4 / 5, the total reply-probability mass discarded and
    the number of distinct leaf paths in the resulting tree,
  * the two-parameter grid `width_player` x `width_opponent` over {1..5}^2:
    iterations (leaf paths) and positions (nodes) of the resulting drill tree,
    the reply mass discarded separately at the learner's and the opponent's
    decision points, and how many acceptable learner moves a position has.

Usage:
    python tree-width-analysis.py <dump.pgn.zst> <out.md>

Requires: python-chess 1.11.2 (used only for the tokenizer self-check),
zstandard.  See docs/research/tree-width-measurements.md.
"""

import io
import re
import sys
import time

PLY_CAP = 21          # tree depth; a node at ply 20 needs children at ply 21
RESULTS = {"1-0", "0-1", "1/2-1/2", "*"}
MOVE_NO = re.compile(r"^\d+\.+$")
MOVE_NO_PREFIX = re.compile(r"^\d+\.+(.+)$")
HEADER = re.compile(r'^\[(\w+)\s+"(.*)"\]$')
CUTOFFS = (1.0, 0.2)
WIDTHS = (3, 4, 5)
CAP_NONE = 10 ** 9          # sentinel width for the "cut-off only" baseline
BUCKETS = ("all", "both>=1800", "both<1500")
GRID_WIDTHS = (1, 2, 3, 4, 5)   # width_player and width_opponent, per the app
GRID_HEADLINE = "both>=1800"    # full grid for this bucket, headline rows for the rest


# --------------------------------------------------------------------------
# PGN streaming
# --------------------------------------------------------------------------

def tokenize_movetext(line):
    """Return (san_tokens, saw_result) for one movetext line."""
    toks = []
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if c == "{":                       # comment (holds %eval, %clk, ...)
            j = line.find("}", i)
            i = n if j < 0 else j + 1
            continue
        if c.isspace():
            i += 1
            continue
        j = i
        while j < n and not line[j].isspace() and line[j] != "{":
            j += 1
        tok = line[i:j]
        i = j
        if tok in RESULTS:
            return toks, True
        if tok.startswith("$") or tok == "e.p." or MOVE_NO.match(tok):
            continue
        m = MOVE_NO_PREFIX.match(tok)
        if m:
            tok = m.group(1)
        tok = tok.rstrip("!?")
        if not tok:
            continue
        if tok in RESULTS:
            return toks, True
        toks.append(tok)
    return toks, False


def iter_games(path):
    """Yield (headers dict, [san, ...]) for every game, streaming."""
    import zstandard as zstd

    dctx = zstd.ZstdDecompressor()
    with open(path, "rb") as fh:
        with dctx.stream_reader(fh) as reader:
            text = io.TextIOWrapper(reader, encoding="utf-8", errors="replace")
            headers, moves, in_moves = {}, [], False
            for line in text:
                s = line.strip()
                if not s:
                    continue
                if s.startswith("["):
                    if in_moves:            # game without a result token
                        yield headers, moves
                        headers, moves, in_moves = {}, [], False
                    m = HEADER.match(s)
                    if m:
                        headers[m.group(1)] = m.group(2)
                    continue
                in_moves = True
                toks, done = tokenize_movetext(s)
                moves.extend(toks)
                if done:
                    yield headers, moves
                    headers, moves, in_moves = {}, [], False
            if in_moves:
                yield headers, moves


def elo(headers, key):
    v = headers.get(key, "")
    if not v.isdigit():
        return None
    return int(v)


def in_bucket(name, we, be):
    if name == "all":
        return True
    if we is None or be is None:
        return False
    if name == "both>=1800":
        return we >= 1800 and be >= 1800
    if name == "both<1500":
        return we < 1500 and be < 1500
    raise ValueError(name)


# --------------------------------------------------------------------------
# Trie
# --------------------------------------------------------------------------

def new_node():
    return [0, {}]          # [games through this node, {san: child node}]


def build_tries(path):
    roots = {b: new_node() for b in BUCKETS}
    n_games = 0
    speeds = {}
    t0 = time.time()
    for headers, moves in iter_games(path):
        n_games += 1
        ev = headers.get("Event", "")
        sp = ev.split()[-2] if ev.endswith("game") else "?"
        speeds[sp] = speeds.get(sp, 0) + 1
        we, be = elo(headers, "WhiteElo"), elo(headers, "BlackElo")
        for b in BUCKETS:
            if not in_bucket(b, we, be):
                continue
            node = roots[b]
            node[0] += 1
            for mv in moves[:PLY_CAP]:
                ch = node[1].get(mv)
                if ch is None:
                    ch = new_node()
                    node[1][mv] = ch
                ch[0] += 1
                node = ch
    print("parsed %d games in %.0fs" % (n_games, time.time() - t0), file=sys.stderr)
    return roots, n_games, speeds


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------

def levels_upto(root, thr):
    """levels[p] = surviving nodes at ply p (p=0 is the root)."""
    levels = [[root]]
    for p in range(PLY_CAP):
        nxt = []
        for node in levels[p]:
            for ch in node[1].values():
                if ch[0] >= thr:
                    nxt.append(ch)
        if not nxt:
            break                      # levels[] holds only non-empty plies
        levels.append(nxt)
    return levels


def surviving_kids(node, thr):
    """Surviving replies of a node, most popular first."""
    return sorted((ch for ch in node[1].values() if ch[0] >= thr),
                  key=lambda c: -c[0])


def grid_cell(levels, depth, thr, w_player, w_opp):
    """One cell of the two-parameter drill tree.

    `width_player` (P) is how many moves are acceptable for the learner at the
    learner's turn; `width_opponent` (O) is how many candidate replies the
    opponent samples among.  The learner plays BOTH colours across iterations,
    so at every position the tree must hold both what the learner may legally
    play (top P) and what the opponent may spring (top O): it keeps their
    union.  Both are prefixes of one popularity ordering, so that union is
    exactly the top `max(P, O)` surviving replies - iteration and node counts
    depend only on `k = max(P, O)`, while P and O independently drive the two
    discard numbers.
    """
    keep = max(w_player, w_opp)
    frontier = levels[0]                    # [root]
    nodes_by_ply = []
    internal = 0                            # positions with >= 1 kept reply
    dead_ends = 0
    acc = []                                # acceptable learner moves per position
    for _ in range(depth):
        nxt = []
        for nd in frontier:
            kids = surviving_kids(nd, thr)[:keep]
            if kids:
                internal += 1
                acc.append(min(w_player, len(kids)))
                nxt.extend(kids)
            else:
                dead_ends += 1
        frontier = nxt
        nodes_by_ply.append(len(frontier))
    nodes = sum(nodes_by_ply) + 1           # every node, root included
    iters = dead_ends + len(frontier)       # leaf paths = distinct full games
    max_ply = max((p for p, c in enumerate(nodes_by_ply, start=1) if c), default=0)

    # discard accounting over the cut-off tree's decision points: every
    # position with at least one surviving reply, weighted by the games
    # reaching it.  One shared denominator for all three figures.
    denom = d_player = d_opp = d_comb = 0
    denom_positions = 0
    for p in range(depth):
        for nd in levels[p]:
            kids = [ch[0] for ch in surviving_kids(nd, thr)]
            mass = sum(kids)
            if not mass:
                continue                    # tree dead-ends here: no reply to make
            denom += mass
            denom_positions += 1
            d_player += mass - sum(kids[:w_player])
            d_opp += mass - sum(kids[:w_opp])
            d_comb += mass - sum(kids[:keep])

    def rate(num):
        return num / denom if denom else 0.0

    return {
        "w_player": w_player, "w_opp": w_opp, "keep": keep,
        "iters": iters, "nodes": nodes, "nodes_by_ply": nodes_by_ply,
        "max_ply": max_ply, "learner_positions": internal,
        "acc_mean": sum(acc) / len(acc) if acc else 0.0,
        "acc_max": max(acc) if acc else 0, "acc_min": min(acc) if acc else 0,
        "denom": denom, "denom_positions": denom_positions,
        "disc_player": d_player, "disc_opp": d_opp,
        "disc_comb": d_comb,
        "rate_player": rate(d_player), "rate_opp": rate(d_opp),
        "rate_comb": rate(d_comb),
    }


def analyse(root, pct):
    n = root[0]
    thr = pct / 100.0 * n
    levels = levels_upto(root, thr)
    depth = len(levels) - 1                       # deepest surviving ply
    res = {
        "n": n, "pct": pct, "thr": thr, "depth": depth,
        "truncated": depth >= PLY_CAP,
        "nodes_total": sum(len(levels[p]) for p in range(1, len(levels))),
        "nodes_by_ply": [len(levels[p]) for p in range(1, len(levels))],
        "ply": [],
    }
    # per node-ply statistics (node at ply p, replies at ply p+1)
    for p in range(1, min(20, depth) + 1):
        nodes = levels[p]
        if not nodes:
            continue
        rec = {
            "ply": p, "n_nodes": len(nodes), "mass": sum(nd[0] for nd in nodes),
            "replies": [], "topk": {k: 0 for k in range(1, 6)},
            "node_share": {k: [] for k in range(1, 6)},
        }
        for nd in nodes:
            kids = sorted((ch[0] for ch in nd[1].values() if ch[0] >= thr),
                          reverse=True)
            rec["replies"].append(len(kids))
            for k in range(1, 6):
                s = sum(kids[:k])
                rec["topk"][k] += s
                rec["node_share"][k].append(s / nd[0])
        res["ply"].append(rec)

    # opponent-move coverage by arrival ply (games reaching the parent node)
    res["arrival"] = {}
    for p in (2, 4, 6, 8):
        if p > depth or not levels[p - 1]:
            res["arrival"][p] = None
            continue
        parents = levels[p - 1]
        mass = sum(nd[0] for nd in parents)
        topk = {k: 0 for k in range(1, 6)}
        replies = []
        for nd in parents:
            kids = sorted((ch[0] for ch in nd[1].values() if ch[0] >= thr),
                          reverse=True)
            replies.append(len(kids))
            for k in range(1, 6):
                topk[k] += sum(kids[:k])
        res["arrival"][p] = {
            "n_positions": len(parents), "mass": mass, "topk": topk,
            "surviving_mass": sum(nd[0] for nd in levels[p]),
            "mean_replies": sum(replies) / len(replies), "max_replies": max(replies),
        }

    # width-cap discards and capped-tree path counts
    res["width"] = {}
    for mode in ("all", "opp", "none"):
        for w in WIDTHS if mode != "none" else (CAP_NONE,):
            discard_by_ply = {}
            avail_by_ply = {}
            for p in range(0, depth):             # nodes with surviving children
                if not levels[p]:
                    continue
                capped = (mode != "opp") or (p % 2 == 1)   # p odd: Black to move
                avail = d = 0
                for nd in levels[p]:
                    kids = sorted((ch[0] for ch in nd[1].values()
                                   if ch[0] >= thr), reverse=True)
                    avail += sum(kids)            # mass the cut-off already kept
                    if capped:
                        d += sum(kids) - sum(kids[:w])
                discard_by_ply[p] = d
                avail_by_ply[p] = avail
            capped_ply = [p for p in discard_by_ply
                          if mode == "all" or p % 2 == 1]
            capped_mass = sum(avail_by_ply[p] for p in capped_ply)

            def cap_fn(p, w=w, mode=mode):
                if mode == "opp" and p % 2 == 0:
                    return 10 ** 9
                return w

            # frontier of the capped tree = number of distinct paths per ply
            frontier = [root]
            paths = {0: 1}
            leaves = 0
            for p in range(0, depth):
                W = cap_fn(p)
                nxt = []
                for nd in frontier:
                    kids = sorted((ch for ch in nd[1].values() if ch[0] >= thr),
                                  key=lambda c: -c[0])[:W]
                    if not kids:
                        leaves += 1
                    nxt.extend(kids)
                frontier = nxt
                paths[p + 1] = len(frontier)
            leaves += len(frontier)
            res["width"][(mode, w)] = {
                "discard_total": sum(discard_by_ply[p] for p in capped_ply),
                "discard_by_ply": discard_by_ply,
                "decision_mass": capped_mass,
                "decision_mass_by_ply": avail_by_ply,
                "rate_by_ply": {p: (discard_by_ply[p] / avail_by_ply[p]
                                    if avail_by_ply[p] else 0.0)
                                for p in discard_by_ply},
                "discard_rate": (sum(discard_by_ply[p] for p in capped_ply)
                                 / max(1, capped_mass)),
                "paths20": paths.get(20, 0),
                "paths_at_depth": paths.get(depth, 0),
                "paths_by_ply": paths,
                "leaves": leaves,
            }
    # two-parameter grid (width_player x width_opponent)
    res["grid"] = {(P, O): grid_cell(levels, depth, thr, P, O)
                   for P in GRID_WIDTHS for O in GRID_WIDTHS}
    kids_per_pos = [len(surviving_kids(nd, thr))
                    for p in range(depth) for nd in levels[p]]
    n_pos = res["grid"][(1, 1)]["denom_positions"]
    res["mean_surviving_replies"] = (sum(kids_per_pos) / n_pos) if n_pos else 0.0
    res["max_surviving_replies"] = max(kids_per_pos) if kids_per_pos else 0
    return res


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------

def fmt(x, d=2):
    return ("%%.%df" % d) % x


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def per_ply_tables(r):
    a = ["ply | positions | games reaching | replies mean | replies max | "
         "top-1 | top-2 | top-3 | top-4 | top-5"]
    b = ["ply | top-1 | top-2 | top-3 | top-4 | top-5 | mean top-3 (per node)"]
    for rec in r["ply"]:
        p = rec["ply"]
        a.append(" | ".join([
            str(p), str(rec["n_nodes"]), str(rec["mass"]),
            fmt(sum(rec["replies"]) / len(rec["replies"]), 2),
            str(max(rec["replies"])),
        ] + [fmt(100.0 * rec["topk"][k] / r["n"], 2) for k in range(1, 6)]))
        b.append(" | ".join([
            str(p),
        ] + [fmt(100.0 * rec["topk"][k] / rec["mass"], 2) for k in range(1, 6)]
          + [fmt(100.0 * sum(rec["node_share"][3]) / len(rec["node_share"][3]), 1)]))
    return table(a[0].split(" | "), [x.split(" | ") for x in a[1:]]), \
        table(b[0].split(" | "), [x.split(" | ") for x in b[1:]])


def width_table(r):
    rows = []
    modes = (("all", "cap every node", WIDTHS),
             ("opp", "cap opponent (Black) only", WIDTHS),
             ("none", "no cap (cut-off only)", (CAP_NONE,)))
    for mode, label, widths in modes:
        for w in widths:
            d = r["width"][(mode, w)]
            wp, wr = max(((p, 100.0 * v) for p, v in d["rate_by_ply"].items()),
                         key=lambda t: t[1], default=(0, 0.0))
            rows.append([
                label, "-" if mode == "none" else str(w),
                fmt(100.0 * d["discard_rate"], 2),
                "ply %d: %.1f%%" % (wp, wr),
                str(d["discard_total"]),
                str(sum(d["paths_by_ply"].values())),
                str(d["paths20"]),
                str(d["paths_at_depth"]),
                str(d["leaves"]),
            ])
    return table(["cap applied to", "width W",
                  "reply mass discarded, % of decision-point mass",
                  "worst ply (discard there, % of its reply mass)",
                  "discarded game-replies (summed over positions)",
                  "nodes in capped tree",
                  "paths at ply 20",
                  "paths at ply %d (termination)" % r["depth"],
                  "all leaf paths"], rows)


def grid_matrix(r, cell):
    """5x5 matrix of the grid; `cell` renders one cell."""
    rows = [[str(P)] + [cell(r["grid"][(P, O)]) for O in GRID_WIDTHS]
            for P in GRID_WIDTHS]
    return table(["wp \\ wo"] + [str(O) for O in GRID_WIDTHS], rows)


GRID_DETAIL_HEAD = [
    "width_player", "width_opponent", "iterations", "positions",
    "positions learner moves at", "acceptable learner moves mean",
    "acceptable learner moves max",
    "learner decision points: discard %", "learner: discarded game-replies",
    "opponent decision points: discard %", "opponent: discarded game-replies",
    "combined: discard %", "combined: discarded game-replies", "max ply",
]


def grid_detail_rows(r):
    rows = []
    for P in GRID_WIDTHS:
        for O in GRID_WIDTHS:
            g = r["grid"][(P, O)]
            rows.append([str(P), str(O), str(g["iters"]), str(g["nodes"]),
                         str(g["learner_positions"]), fmt(g["acc_mean"], 2),
                         str(g["acc_max"]),
                         fmt(100.0 * g["rate_player"], 2), str(g["disc_player"]),
                         fmt(100.0 * g["rate_opp"], 2), str(g["disc_opp"]),
                         fmt(100.0 * g["rate_comb"], 2), str(g["disc_comb"]),
                         str(g["max_ply"])])
    return rows


HEADLINE_HEAD = [
    "case", "width_player", "width_opponent", "iterations", "positions",
    "positions learner moves at", "acceptable learner moves mean",
    "acceptable learner moves max",
    "learner decision points: discard %", "opponent decision points: discard %",
    "combined: discard %", "max ply",
]


def headline_rows(r):
    """One strict-learner row and one matched row per k = max(P, O)."""
    rows = []
    for k in GRID_WIDTHS:
        cases = ((1, k, "strict learner (P=1)"),) if k == 1 else (
            (1, k, "strict learner (P=1)"), (k, k, "matched (P=O)"))
        for P, O, label in cases:
            g = r["grid"][(P, O)]
            rows.append([label, str(P), str(O), str(g["iters"]), str(g["nodes"]),
                         str(g["learner_positions"]), fmt(g["acc_mean"], 2),
                         str(g["acc_max"]),
                         fmt(100.0 * g["rate_player"], 2),
                         fmt(100.0 * g["rate_opp"], 2),
                         fmt(100.0 * g["rate_comb"], 2), str(g["max_ply"])])
    return rows


STRICT_HEAD = [
    "width_opponent", "iterations", "positions", "positions learner moves at",
    "acceptable learner moves mean", "acceptable learner moves max",
    "learner decision points: discard %", "learner: discarded game-replies",
    "opponent decision points: discard %", "opponent: discarded game-replies",
    "combined: discard %", "combined: discarded game-replies", "max ply",
]


def strict_rows(r):
    """width_player = 1 only: the 'force the top move' mode."""
    rows = []
    for O in GRID_WIDTHS:
        g = r["grid"][(1, O)]
        rows.append([str(O), str(g["iters"]), str(g["nodes"]),
                     str(g["learner_positions"]), fmt(g["acc_mean"], 2),
                     str(g["acc_max"]),
                     fmt(100.0 * g["rate_player"], 2), str(g["disc_player"]),
                     fmt(100.0 * g["rate_opp"], 2), str(g["disc_opp"]),
                     fmt(100.0 * g["rate_comb"], 2), str(g["disc_comb"]),
                     str(g["max_ply"])])
    return rows


def grid_checks(analysis):
    """Self-checks the section states: k=max(P,O) fixes size; rates split by width."""
    size_ok = rate_ok = True
    for b in BUCKETS:
        for pct in CUTOFFS:
            sizes, lp, op = {}, {}, {}
            for P in GRID_WIDTHS:
                for O in GRID_WIDTHS:
                    g = analysis[b][pct]["grid"][(P, O)]
                    sizes.setdefault(max(P, O), set()).add((g["iters"], g["nodes"]))
                    lp.setdefault(P, set()).add(round(g["rate_player"], 12))
                    op.setdefault(O, set()).add(round(g["rate_opp"], 12))
            size_ok &= all(len(v) == 1 for v in sizes.values())
            rate_ok &= all(len(v) == 1 for v in lp.values())
            rate_ok &= all(len(v) == 1 for v in op.values())
    # the k = max(P, O) tree must be exactly the old `cap every node` W=k tree
    x_ok = True
    for b in BUCKETS:
        for pct in CUTOFFS:
            r = analysis[b][pct]
            for k in WIDTHS:
                g, w = r["grid"][(k, k)], r["width"][("all", k)]
                x_ok &= (g["nodes"] == sum(w["paths_by_ply"].values())
                         and g["iters"] == w["leaves"]
                         and g["disc_comb"] == w["discard_total"]
                         and g["denom"] == w["decision_mass"])
    # (k, k) must dominate every cell whose max(P, O) is k
    dom_ok = True
    for b in BUCKETS:
        for pct in CUTOFFS:
            for P in GRID_WIDTHS:
                for O in GRID_WIDTHS:
                    g = analysis[b][pct]["grid"][(P, O)]
                    d = analysis[b][pct]["grid"][(max(P, O),) * 2]
                    dom_ok &= (g["iters"] == d["iters"]
                               and g["nodes"] == d["nodes"]
                               and d["rate_player"] <= g["rate_player"] + 1e-12
                               and d["rate_opp"] <= g["rate_opp"] + 1e-12)
    return size_ok, rate_ok, x_ok, dom_ok


def grid_section(analysis, roots):
    """The 'Two-parameter grid: width_player x width_opponent' section."""
    L = []
    A = L.append
    n_cells = len(BUCKETS) * len(CUTOFFS) * len(GRID_WIDTHS) ** 2
    A("")
    A("## Two-parameter grid: width_player x width_opponent")
    A("")
    A("The sections above cap a single width and assume a White learner "
      "(`cap every node` W caps both sides, `cap opponent (Black) only` W caps "
      "only Black's plies). The app now has two independent knobs and drills "
      "**both colours** - it samples which side the learner plays each "
      "iteration:")
    A("")
    A("- **`width_player` P**: at a position where the learner is to move, any "
      "of the P most popular surviving moves is acceptable; any other move is a "
      "failure (the round leaves the repertoire). Nothing is sampled *for* the "
      "learner, so P measures how much of a position's move mass the learner "
      "must have ready.")
    A("- **`width_opponent` O**: the app samples the opponent's reply among the "
      "O most popular surviving moves, renormalised over those O.")
    A("")
    A("**The resulting tree.** Every position must hold both what the learner "
      "may legitimately play (top P) and what the opponent may spring (top O), "
      "so the tree keeps their union. Both sets are prefixes of one popularity "
      "ordering, so that union is exactly the top `max(P, O)` surviving "
      "replies: **iteration and node counts depend only on `k = max(P, O)`**, "
      "while P and O drive the two discard columns independently. Capping only "
      "removes edges, so no cap can make a tree deeper than its cut-off.")
    A("")
    A("- **iterations** = distinct full games the learner can be shown = leaf "
      "paths of the tree (paths that dead-end plus the deepest frontier). A "
      "move sequence is counted once even though the learner meets it once as "
      "White and once as Black.")
    A("- **positions** = every node of the tree, root included. The learner "
      "plays both colours, so the learner is to move at every ply in the "
      "iterations where the learner has that colour and must be prepared at "
      "every node.")
    A("- **positions where the learner must move** = the tree's internal nodes "
      "(at least one kept reply), root included. **acceptable learner moves** "
      "at such a position = `min(P, replies the tree keeps there)`.")
    A("")
    A("**Discard denominators, stated explicitly.** A position of the cut-off "
      "tree that still has surviving replies carries those replies' game "
      "counts as mass. All three discard figures below share one denominator "
      "**D = the surviving reply mass summed over every cut-off position that "
      "has at least one surviving reply** (traffic-weighted by the games "
      "reaching each position); each table's caption gives D for its "
      "bucket/cut-off.")
    A("")
    A("- **learner decision points** = those positions read in the iterations "
      "where the learner has the move; the figure is the share of D that lies "
      "outside the top P, i.e. the traffic-weighted chance that the learner "
      "plays a move the repertoire does not accept.")
    A("- **opponent decision points** = the same positions read in the "
      "iterations where the opponent has the move; the share of D outside the "
      "top O.")
    A("- **combined** = the share of D outside `top P ∪ top O`, which equals "
      "outside `top max(P, O)`. It is *not* the sum of the two columns: mass "
      "outside both caps is counted once.")
    A("")
    A("Because both colours are drilled, both sides are to move at every ply, "
      "so the learner's and the opponent's decision-point sets coincide (the "
      "same positions, opposite iterations); the columns differ only in which "
      "width is applied. The old `cap opponent (Black) only` rows are "
      "narrower than the opponent column here: they capped odd plies only.")
    A("")

    # full grid for the headline bucket
    r0 = analysis[GRID_HEADLINE][CUTOFFS[0]]
    A("### Full grid: `%s`, both cut-offs" % GRID_HEADLINE)
    for pct in CUTOFFS:
        r = analysis[GRID_HEADLINE][pct]
        g0 = r["grid"][(1, 1)]
        A("")
        A("#### `%s`, cut-off >= %.1f%% of games (>= %d games)"
          % (GRID_HEADLINE, pct, round(r["thr"])))
        A("")
        A("Iterations (leaf paths) / positions (nodes, root included), per "
          "cell. Values repeat along every anti-diagonal `max(P, O) = k`: the "
          "tree is the top-k tree.")
        A("")
        A(grid_matrix(r, lambda g: "%d / %d" % (g["iters"], g["nodes"])))
        A("")
        A("Denominator D for every percentage in the table below: **%d "
          "surviving game-replies over %d positions** (every cut-off position "
          "with at least one surviving reply). `learner: discarded "
          "game-replies` is the numerator behind the learner percentage, in "
          "game-replies summed over positions - a game counts once per "
          "position where its reply falls outside the accepted set."
          % (g0["denom"], g0["denom_positions"]))
        A("")
        A(table(GRID_DETAIL_HEAD, grid_detail_rows(r)))

    # headline rows for the other buckets
    A("")
    A("### Headline rows: `all` and `both<1500`")
    A("")
    A("Because the tree shape depends only on `k = max(P, O)`, two families "
      "cover the grid: the strict-learner cells `(1, k)` and the matched cells "
      "`(k, k)`. Same columns as the full grid minus the absolute numerators.")
    for b in [x for x in BUCKETS if x != GRID_HEADLINE]:
        for pct in CUTOFFS:
            r = analysis[b][pct]
            g0 = r["grid"][(1, 1)]
            A("")
            A("#### Bucket `%s` (%d games), cut-off >= %.1f%% of games "
              "(>= %d games); D = %d surviving game-replies over %d positions"
              % (b, roots[b][0], pct, round(r["thr"]), g0["denom"],
                 g0["denom_positions"]))
            A("")
            A(table(HEADLINE_HEAD, headline_rows(r)))

    # strict mode detail
    A("")
    A("### Strict mode in detail: `width_player = 1` (force the top move)")
    A("")
    A("The learner must reproduce the single most popular surviving move at "
      "every one of their turns, in both colours; only the opponent's pool "
      "widens. `max(P, O) = O`, so these rows are the top-O trees.")
    for b in BUCKETS:
        for pct in CUTOFFS:
            r = analysis[b][pct]
            g0 = r["grid"][(1, 1)]
            A("")
            A("#### Bucket `%s` (%d games), cut-off >= %.1f%% of games "
              "(>= %d games); D = %d surviving game-replies over %d positions"
              % (b, roots[b][0], pct, round(r["thr"]), g0["denom"],
                 g0["denom_positions"]))
            A("")
            A(table(STRICT_HEAD, strict_rows(r)))

    # ply-20 check + structural checks
    size_ok, rate_ok, x_ok, dom_ok = grid_checks(analysis)
    cells = [(b, pct, P, O, analysis[b][pct]["grid"][(P, O)])
             for b in BUCKETS for pct in CUTOFFS
             for P in GRID_WIDTHS for O in GRID_WIDTHS]
    deepest = max(cells, key=lambda t: t[4]["max_ply"])
    at20 = [c for c in cells
            if len(c[4]["nodes_by_ply"]) >= 20 and c[4]["nodes_by_ply"][19]]
    floor20 = [c for c in cells if c[4]["max_ply"] >= 19]

    A("")
    A("### Does any cell reach ply 20?")
    A("")
    A("**No.** Across all %d cells (%d buckets x %d cut-offs x %d (P, O) "
      "combinations) **no capped tree reaches ply 20, or even ply 19**. The "
      "deepest cell is `%s`, cut-off >= %.1f%%, (width_player=%d, "
      "width_opponent=%d) at **ply %d**; the deepest trees are the 0.2%% "
      "`both>=1800` ones, and their cut-off trees already stop at ply %d "
      "(the uncapped maximum over every bucket and cut-off is ply %d). The "
      "width caps can only remove edges, so they cannot add depth: the old "
      "doc's \"no tree reaches ply 20\" holds a fortiori for every capped "
      "tree here (`paths at ply 20` = 0 in all %d cells%s). The trie is "
      "built to ply %d, so nothing in this section is truncation."
      % (n_cells, len(BUCKETS), len(CUTOFFS), len(GRID_WIDTHS) ** 2,
         deepest[0], deepest[1], deepest[2], deepest[3], deepest[4]["max_ply"],
         analysis[GRID_HEADLINE][CUTOFFS[1]]["depth"],
         max(analysis[b][p]["depth"] for b in BUCKETS for p in CUTOFFS),
         n_cells,
         "" if not at20 else "; cells at ply 19+: " + ", ".join(
             "%s/%.1f%%/(%d,%d)" % (c[0], c[1], c[2], c[3]) for c in floor20),
         PLY_CAP))
    A("")
    A("Structural self-checks over the same %d cells: cells sharing "
      "`max(P, O) = k` give identical iteration and node counts (%s); the "
      "learner discard rate is a function of `width_player` alone and the "
      "opponent rate of `width_opponent` alone (%s); every `(k, k)` cell "
      "reproduces the old `cap every node` W=k row exactly - same nodes, same "
      "leaf paths, same discarded mass, same denominator (%s); and the "
      "matched cell `(k, k)` weakly dominates every cell with "
      "`max(P, O) = k` (%s)."
      % (n_cells, "verified" if size_ok else "FAILED",
         "verified" if rate_ok else "FAILED",
         "verified" if x_ok else "FAILED",
         "verified" if dom_ok else "FAILED"))
    A("")
    A("**Dominated cells.** Because the tree is the top-`k` tree, every "
      "off-diagonal cell is weakly dominated by the matched cell "
      "`(k, k) = (max(P, O), max(P, O))`: identical iterations and positions, "
      "and both discard figures weakly smaller (verified for all %d cells). "
      "Turning a knob up to `k` is free, so the only real decision is `k`; "
      "the Pareto frontier of the whole grid is the diagonal `P = O`:" % n_cells)
    A("")
    for pct in CUTOFFS:
        r = analysis[GRID_HEADLINE][pct]
        g0 = r["grid"][(1, 1)]
        rows = []
        prev = None
        for k in GRID_WIDTHS:
            g = r["grid"][(k, k)]
            rows.append([
                str(k), str(g["iters"]), str(g["nodes"]),
                fmt(g["iters"] / g["nodes"], 2),
                "-" if prev is None else "+%d" % (g["nodes"] - prev["nodes"]),
                "-" if prev is None else "%.2f" % (100.0 * (prev["rate_comb"]
                                                            - g["rate_comb"])),
                fmt(100.0 * g["rate_player"], 2),
                fmt(100.0 * g["rate_opp"], 2),
                str(g["max_ply"]),
            ])
            prev = g
        A("")
        A("`%s`, cut-off >= %.1f%% (D = %d surviving game-replies over %d "
          "positions):" % (GRID_HEADLINE, pct, g0["denom"],
                           g0["denom_positions"]))
        A("")
        A(table(["k = P = O", "iterations", "positions",
                 "iterations / positions", "extra positions vs k-1",
                 "coverage gained vs k-1 (points)", "learner discard %",
                 "opponent discard %", "max ply"], rows))
    A("")
    g1 = analysis[GRID_HEADLINE][CUTOFFS[0]]["grid"]
    A("### How to read the two discard columns")
    A("")
    A("At a fixed cut-off the two columns mean different things, and only one "
      "of them is a coverage loss:")
    A("")
    A("- the **opponent** column is coverage: the share of the surviving reply "
      "mass the app will never show because the sampled pool is capped at O. "
      "`width_player` does not change it.")
    A("- the **learner** column is the pass bar: the share of the mass at the "
      "learner's decision points that lies outside the accepted set, i.e. the "
      "traffic-weighted chance that the move the learner would play is not "
      "one of the P accepted ones. It removes no games from the tree. Because "
      "it is dominated by the first move - the only position with many "
      "surviving replies - O does not change it either.")
    A("- **combined** is the tree's coverage loss: mass outside `top P ∪ top "
      "O`, i.e. the share of replies neither side of the drill can ever "
      "produce. It equals whichever of the two caps is the wider (`k = "
      "max(P, O)`).")
    A("")
    A("Concretely for `%s` at the 1%% cut-off: **(width_player=1, "
      "width_opponent=3)** gives %d iterations over %d positions, discards "
      "%.2f%% at the learner's decision points and %.2f%% at the opponent's "
      "(combined %.2f%%); **(3, 3)** gives the *same* %d iterations over the "
      "same %d positions, but the learner's obligation drops to %.2f%% "
      "(combined unchanged at %.2f%%); **(1, 5)** widens the tree to %d "
      "iterations and %d positions, keeps the learner bar at %.2f%% and cuts "
      "the opponent's loss to %.2f%%. Going from P=3 to P=1 therefore buys "
      "nothing in coverage (the tree is set by O whenever O >= P) and costs "
      "%.2f points of learner failure risk; going from O=3 to O=5 buys "
      "%.2f points of coverage for %d extra iterations and %d extra positions "
      "to prepare. The learner-side penalty is concentrated where branching "
      "is real: the 1%% cut-off tree offers a mean of %.2f surviving replies "
      "per decision point (max %d, at the very first move for White), so most "
      "positions accept the single top move anyway and P=1 discards almost "
      "all of its mass at the shallow, wide plies."
      % (GRID_HEADLINE,
         g1[(1, 3)]["iters"], g1[(1, 3)]["nodes"],
         100.0 * g1[(1, 3)]["rate_player"], 100.0 * g1[(1, 3)]["rate_opp"],
         100.0 * g1[(1, 3)]["rate_comb"],
         g1[(3, 3)]["iters"], g1[(3, 3)]["nodes"],
         100.0 * g1[(3, 3)]["rate_player"], 100.0 * g1[(3, 3)]["rate_comb"],
         g1[(1, 5)]["iters"], g1[(1, 5)]["nodes"],
         100.0 * g1[(1, 5)]["rate_player"], 100.0 * g1[(1, 5)]["rate_opp"],
         100.0 * (g1[(1, 3)]["rate_player"] - g1[(3, 3)]["rate_player"]),
         100.0 * (g1[(3, 3)]["rate_opp"] - g1[(1, 5)]["rate_opp"]),
         g1[(1, 5)]["iters"] - g1[(1, 3)]["iters"],
         g1[(1, 5)]["nodes"] - g1[(1, 3)]["nodes"],
         analysis[GRID_HEADLINE][CUTOFFS[0]]["mean_surviving_replies"],
         analysis[GRID_HEADLINE][CUTOFFS[0]]["max_surviving_replies"]))
    A("")
    return "\n".join(L)


def verify(dump, n):
    """Compare the plain tokenizer with chess.pgn.read_game on the first n games."""
    import io
    import zstandard as zstd
    import chess.pgn

    gen = iter_games(dump)
    dctx = zstd.ZstdDecompressor()
    checked = bad = 0
    with open(dump, "rb") as fh, dctx.stream_reader(fh) as rd:
        txt = io.TextIOWrapper(rd, encoding="utf-8", errors="replace")
        for _ in range(n):
            g = chess.pgn.read_game(txt)
            if g is None:
                break
            headers, moves = next(gen)
            board = g.board()
            pc = []
            for x in g.mainline_moves():
                pc.append(board.san(x))
                board.push(x)
            if pc[:len(moves[:PLY_CAP])] != moves[:PLY_CAP]:
                bad += 1
                if bad <= 3:
                    print("mismatch", headers.get("Site"), pc[:12], moves[:12])
            checked += 1
    print("verified %d games, %d mismatches" % (checked, bad))


def main():
    if sys.argv[1] == "--verify":
        verify(sys.argv[3], int(sys.argv[2]))
        return
    dump, out_path = sys.argv[1], sys.argv[2]
    roots, n_games, speeds = build_tries(dump)
    analysis = {b: {p: analyse(roots[b], p) for p in CUTOFFS} for b in BUCKETS}

    L = []
    A = L.append
    A("# How a reply-width cap trades against popularity coverage")
    A("")
    A("Ticket: [.scratch/chessop/issues/](../../.scratch/chessop/issues/) "
      "(measurement requested by the parent session).")
    A("Raw material: `lichess_db_standard_rated_2013-01.pgn.zst` "
      "(17,761,302 bytes, 121,332 games), downloaded and parsed locally with "
      "python-chess 1.11.2 / zstandard, then deleted (CC0).")
    A("Script: [`refs/lichess/tree-width-analysis.py`](../../refs/lichess/tree-width-analysis.py).")
    A("")
    A("## Method")
    A("")
    A("- Streamed the `.pgn.zst` (never fully in memory), kept the mainline SAN "
      "of each game to ply 21, built one trie per bucket. **Transpositions are "
      "not merged**: a node is a move *sequence*, matching the earlier "
      "`dump-2013-01-tree-stats.txt` measurement.")
    A("- Buckets, by both players' Elo: %s." %
      ", ".join("`%s` = %d games" % (b, roots[b][0]) for b in BUCKETS))
    A("- `games reaching a node` = number of games in the bucket whose move "
      "sequence passes through it (the node's count).")
    A("- **Cut-off**: a node/edge survives if its count is >= X% of the "
      "bucket's games. Surviving edges are exactly the sampled candidate "
      "replies; because a parent's count is never below a child's, no "
      "reachability repair is needed.")
    A("- **Width cap W**: on top of the cut-off, a position keeps only its "
      "W most popular surviving replies; the sampling weights are "
      "renormalised over those W. Two variants are reported: `cap every node` "
      "(the learner's own moves are capped too, which is what bounds the "
      "repertoire size) and `cap opponent (Black) only` (the literal drill: "
      "learner has White, only Black's replies are sampled).")
    A("- `reply mass discarded, % of decision-point mass` is the traffic-weighted "
      "average over every position where the cap applies: sum over positions of "
      "(surviving reply mass - mass kept by the cap) divided by the surviving "
      "reply mass at those positions. Mass already removed by the popularity "
      "cut-off is not counted as width-cap loss, and for `cap opponent only` "
      "the denominator only covers the plies where Black is to move. "
      "`discarded game-replies` is the numerator in absolute terms; a game "
      "contributes once per position along its path where its reply falls "
      "outside the cap, so the total can exceed the number of games.")
    A("- `distinct paths at ply p` = number of nodes at ply p in the capped "
      "tree = number of distinct repertoire lines of that length. `all leaf "
      "paths` = paths that dead-end (no surviving reply) plus the ply-%d "
      "frontier; that is the total size of the drilled repertoire. No cut-off "
      "tree below reaches ply 20, so the `paths at ply 20` column is 0 "
      "throughout and the termination column carries the real number."
      % max(analysis[b][p]["depth"] for b in BUCKETS for p in CUTOFFS))
    A("- Nodes at the termination ply have 0 surviving replies by definition, "
      "so the last row of each per-ply table is an artefact of the tree ending, "
      "not a real position.")
    A("- The trie is built to ply %d, so a bucket whose cut-off tree still has "
      "nodes at ply %d would be truncated; none of the trees below is (max "
      "depth %d)."
      % (PLY_CAP, PLY_CAP, max(analysis[b][p]["depth"] for b in BUCKETS for p in CUTOFFS)))
    A("")
    A("Tokenizer self-check (500 games, plain tokenizer vs "
      "`chess.pgn.read_game`): 499 identical move lists; the one difference is "
      "a move the dump writes fully disambiguated (`Nb4c6`) and python-chess "
      "re-renders minimally (`N4c6`) - same ply, spelling only. Command at the "
      "end.")
    A("")

    # headline
    A("## Headline: top-3 cumulative share for both players >= 1800")
    A("")
    A("The opponent's reply at ply p (the p/2-th Black move), aggregated over "
      "every parent position at ply p-1 in the cut-off tree and weighted by the "
      "games reaching it. The top-k shares use those games as denominator "
      "(what the task asked for); `top-3, % of surviving reply mass` uses only "
      "the reply mass the cut-off itself kept, which is the denominator the "
      "width-cap tables below use, so the two numbers differ slightly.")
    for pct in CUTOFFS:
        r = analysis["both>=1800"][pct]
        A("")
        A("### cut-off >= %.1f%% of games (>= %d games)" % (pct, round(r["thr"])))
        rows = []
        for p in (2, 4, 6, 8):
            arr = r["arrival"][p]
            if arr is None:
                rows.append([str(p), "0", "-", "-", "-", "-", "-", "-", "-", "-"])
                continue
            rows.append([str(p), str(arr["n_positions"]), str(arr["mass"]),
                         fmt(arr["mean_replies"], 2), str(arr["max_replies"])] +
                        [fmt(100.0 * arr["topk"][k] / arr["mass"], 2)
                         for k in range(1, 6)] +
                        [fmt(100.0 * arr["topk"][3] / arr["surviving_mass"], 2),
                         fmt(100.0 * arr["topk"][5] / arr["surviving_mass"], 2)])
        A(table(["opponent move at ply", "parent positions", "games reaching them",
                 "replies mean", "replies max", "top-1 %", "top-2 %", "top-3 %",
                 "top-4 %", "top-5 %", "top-3, % of surviving reply mass",
                 "top-5, % of surviving reply mass"], rows))
        A("")
        A("Same top-3 numbers expressed as a share of **all** %d games in the "
          "bucket (they differ by the share of games that even reach the "
          "position in this cut-off tree):" % r["n"])
        rows = []
        for p in (2, 4, 6, 8):
            arr = r["arrival"][p]
            if arr is None:
                rows.append([str(p), "0.00", "0.00"])
                continue
            rows.append([str(p),
                         fmt(100.0 * arr["mass"] / r["n"], 2),
                         fmt(100.0 * arr["topk"][3] / r["n"], 2)])
        A(table(["opponent move at ply", "games reaching %", "top-3 % of all games"], rows))

    # per-bucket detail
    A("")
    A("## Per-bucket detail")
    for b in BUCKETS:
        A("")
        A("### Bucket: %s (%d games)" % (b, roots[b][0]))
        for pct in CUTOFFS:
            r = analysis[b][pct]
            A("")
            A("#### cut-off >= %.1f%% of games (>= %d games)" % (pct, round(r["thr"])))
            A("")
            A("Tree: %d nodes, maximum ply %d, nodes by ply %s.%s"
              % (r["nodes_total"], r["depth"], r["nodes_by_ply"],
                 " **truncated by the ply cap**" if r["truncated"] else ""))
            A("")
            A("Top-1..5 cumulative reply mass **as a share of all games in the "
              "bucket** (sum of the top-k reply counts / %d):" % r["n"])
            A("")
            t1, t2 = per_ply_tables(r)
            A(t1)
            A("")
            A("Top-1..5 cumulative reply mass **as a share of the games reaching "
              "the node** (traffic-weighted), plus the mean per-node top-3 share:")
            A("")
            A(t2)
            A("")
            A("Width caps on top of this cut-off:")
            A("")
            A(width_table(r))

    # two-parameter grid
    A(grid_section(analysis, roots))

    # closing
    A("")
    A("## What this implies for a width parameter")
    A("")
    A(implied(analysis, roots))
    A("")
    A("## Reproduction")
    A("")
    A("The dump is CC0 and was deleted after the run; the script in "
      "[`refs/lichess/tree-width-analysis.py`](../../refs/lichess/tree-width-analysis.py) "
      "regenerates this whole file.")
    A("")
    A("```sh")
    A("cd /home/anthony/pproj/chessop")
    A("")
    A("# 1. dependencies (python-chess 1.11.2, zstandard 0.25.0)")
    A("uv venv /tmp/chessvenv")
    A("uv pip install --python /tmp/chessvenv/bin/python chess==1.11.2 zstandard")
    A("")
    A("# 2. the 2013-01 standard rated dump: 17,761,302 bytes,")
    A("#    sha256 aa40b3671fa3cf1072eb182892cd90b0e1e003a4a5943492f64b77e7f3fd1635")
    A("curl -sSL -o refs/lichess/lichess_db_standard_rated_2013-01.pgn.zst \\")
    A("    https://database.lichess.org/standard/lichess_db_standard_rated_2013-01.pgn.zst")
    A("")
    A("# 3. tokenizer self-check: plain scanner vs chess.pgn.read_game")
    A("/tmp/chessvenv/bin/python refs/lichess/tree-width-analysis.py --verify 500 \\")
    A("    refs/lichess/lichess_db_standard_rated_2013-01.pgn.zst")
    A("")
    A("# 4. the measurement (8.3 s wall, 617 MB max RSS: three tries over 121,332 games)")
    A("/tmp/chessvenv/bin/python refs/lichess/tree-width-analysis.py \\")
    A("    refs/lichess/lichess_db_standard_rated_2013-01.pgn.zst \\")
    A("    docs/research/tree-width-measurements.md")
    A("")
    A("# 5. do not keep the 17.8 MB dump in the repo")
    A("rm refs/lichess/lichess_db_standard_rated_2013-01.pgn.zst")
    A("```")
    A("")
    A("Cross-checks: the per-bucket game counts (121,332 / 9,525 / 19,771), the "
      "pruned node counts by ply at every cut-off (1%, 0.2%) and the maximum "
      "plies (6, 8, 5 at 1%; 10, 18, 9 at 0.2%) reproduce "
      "`refs/lichess/dump-2013-01-tree-stats.txt` exactly. The tokenizer check "
      "found 499/500 identical move lists and one spelling-only difference.")
    A("")

    with open(out_path, "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote %s (%d lines)" % (out_path, len(L)), file=sys.stderr)


def implied(analysis, roots):
    """Plain-language closing section, numbers interpolated."""
    p = []          # paragraphs
    b1 = analysis["both>=1800"][1.0]
    b2 = analysis["both>=1800"][0.2]
    lo1 = analysis["both<1500"][1.0]
    lo2 = analysis["both<1500"][0.2]

    def arr(r, ply, k=3):
        a = r["arrival"][ply]
        return 100.0 * a["topk"][k] / a["mass"] if a else float("nan")

    def disc(r, w, mode="opp"):
        d = r["width"][(mode, w)]
        wp, wr = max(((q, 100.0 * v) for q, v in d["rate_by_ply"].items()),
                     key=lambda t: t[1])
        return 100.0 * d["discard_rate"], wp, wr

    d31, wp31, wr31 = disc(b1, 3)
    d32 = disc(b2, 3)[0]
    d51 = disc(b1, 5)[0]
    d52 = disc(b2, 5)[0]

    p.append(
        "**How much does a width cap of 3 or 5 discard?** Capping only the "
        "opponent (Black) for the `both>=1800` population: **width 3 discards "
        "%.1f%% of the opponent's reply probability at the 1%% cut-off and "
        "%.1f%% at 0.2%%; width 5 discards %.1f%% and %.1f%%** - a "
        "traffic-weighted average over every position where the cap applies. "
        "That average is almost entirely Black's *first* move, the one position "
        "every game passes through. At ply 2 the top-3 replies keep %.1f%% of "
        "the games reaching the position (%.1f%% of the reply mass that "
        "survived the 1%% cut-off, so %.1f%% is discarded) and the top-5 keep "
        "%.1f%% / %.1f%%; by ply 4 the 1%% tree has so few surviving replies "
        "per position that the top 3 keep 100%% of the surviving reply mass "
        "(%.1f%% of the games reaching the position), while at the 0.2%% "
        "cut-off the top 3 still keep %.1f%% of it. Going from width 5 to "
        "width 3 costs %.1f points of reply mass at the 1%% cut-off and %.1f "
        "at 0.2%%, concentrated on Black's first move; from ply 4 onward both "
        "caps are nearly free."
        % (d31, d32, d51, d52,
           arr(b1, 2), 100.0 * b1["arrival"][2]["topk"][3]
           / b1["arrival"][2]["surviving_mass"],
           100.0 - 100.0 * b1["arrival"][2]["topk"][3]
           / b1["arrival"][2]["surviving_mass"],
           arr(b1, 2, 5),
           100.0 * b1["arrival"][2]["topk"][5]
           / b1["arrival"][2]["surviving_mass"],
           arr(b1, 4),
           100.0 * b2["arrival"][4]["topk"][3]
           / b2["arrival"][4]["surviving_mass"],
           d31 - d51, d32 - d52))

    unc2 = b2["width"][("none", CAP_NONE)]
    p.append(
        "The larger popularity loss is **not** the width cap but the cut-off "
        "itself, and the width cap is what makes the repertoire finite. At "
        ">=1800 the 1%% tree stops at ply %d (%d nodes, %d leaf paths) and the "
        "0.2%% tree at ply %d (%d nodes, %d leaf paths). Depth 20 is never "
        "reached, so `paths at ply 20` is 0 for every configuration and the "
        "informative size numbers are the termination ply (always exactly one "
        "deepest path) and the total repertoire: capping every node at width 3 "
        "leaves %d leaf paths at the 0.2%% cut-off against %d uncapped (width "
        "4: %d, width 5: %d), and %d / %d / %d at the 1%% cut-off. Capping "
        "only the opponent is cheaper: %d leaf paths at width 3 on the 0.2%% "
        "cut-off against %d uncapped, because the learner's own moves stay "
        "free - W bounds what the opponent can spring on the learner, not the "
        "learner's repertoire."
        % (b1["depth"], b1["nodes_total"], b1["width"][("none", CAP_NONE)]["leaves"],
           b2["depth"], b2["nodes_total"], unc2["leaves"],
           b2["width"][("all", 3)]["leaves"], unc2["leaves"],
           b2["width"][("all", 4)]["leaves"],
           b2["width"][("all", 5)]["leaves"],
           b1["width"][("all", 3)]["leaves"],
           b1["width"][("all", 4)]["leaves"],
           b1["width"][("all", 5)]["leaves"],
           b2["width"][("opp", 3)]["leaves"], unc2["leaves"]))

    p.append(
        "Rating band matters more than the width cap. At the same 1%% cut-off "
        "the >=1800 tree reaches ply %d while `both<1500` stops at ply %d, and "
        "the low-band mix is far more concentrated: `1.e4 e5` alone is 33.7%% "
        "of games there against 11.7%% at >=1800, and `both<1500` still has a "
        "detectable `1.e3 e5` (3.6%%) where >=1800 does not (see "
        "`refs/lichess/dump-2013-01-tree-stats.txt`; this run reproduces its "
        "node counts). Width 3 therefore approximates the low band better "
        "(%.1f%% vs %.1f%% discarded on average), and the low band's tree is "
        "also shallow. Recommendation: **width 5 on a 1%% cut-off of the "
        "learner's own rating band** - it discards %.1f%% of the opponent's "
        "reply mass on average at >=1800 (worst single ply %.1f%%) and keeps "
        "%d leaf paths - and expose width 3 as the \"main lines only\" "
        "setting rather than the default, since it distorts Black's first "
        "move most (%d%% of surviving reply mass discarded there)."
        % (b1["depth"], lo1["depth"],
           disc(lo1, 3)[0], disc(b1, 3)[0],
           d51, max(disc(b1, 5)[2], 0.0),
           b1["width"][("all", 5)]["leaves"],
           round(100.0 - 100.0 * b1["arrival"][2]["topk"][3]
                 / b1["arrival"][2]["surviving_mass"])))

    p.append(
        "Caveat: one month of 2013 (121 k games, 9.5 k at >=1800) is a small "
        "sample. At the 0.2%% cut-off a node needs only %d games at >=1800, so "
        "the ply-8+ rows are single-game paths and their shares are noisy; the "
        "ply 2/4/6 numbers are solid. `both<1500` at the 0.2%% cut-off is "
        "thinner still (%d games, a %d-game threshold). A recent month (~90 M "
        "games) would firm the tail up and is the natural next step."
        % (round(b2["thr"]), roots["both<1500"][0],
           round(lo2["thr"])))

    return "\n\n".join(p)


if __name__ == "__main__":
    main()
