#!/usr/bin/env python3
"""PROTOTYPE (ticket 10): build tree.json from a Lichess monthly dump.

both players >= 1800, bullet excluded, sequence trie to ply 18,
0.2 % cut-off of the bucket's games, top-3 replies kept per node
(the (3,3) setting of ticket 05), named from the chess-openings TSV by EPD.

Usage: python build_tree.py <dump.pgn.zst> <out.json>
"""
import glob, io, json, re, sys, time
import zstandard, chess

MIN_ELO, MAX_PLY, CUTOFF, WIDTH = 1800, 18, 0.002, 3
HEADER = re.compile(r'^\[(\w+)\s+"(.*)"\]$')
MOVE_NO = re.compile(r"^\d+\.+$")
RESULTS = {"1-0", "0-1", "1/2-1/2", "*"}

def is_bullet(tc):
    if not tc or "+" not in tc: return False
    base, inc = tc.split("+")
    return int(base) + 40 * int(inc) < 180

def games(path):
    dctx = zstandard.ZstdDecompressor()
    with open(path, "rb") as fh:
        reader = io.TextIOWrapper(dctx.stream_reader(fh), encoding="utf-8", errors="replace")
        hdr = {}
        for line in reader:
            line = line.strip()
            if not line: continue
            m = HEADER.match(line)
            if m: hdr[m.group(1)] = m.group(2); continue
            # movetext line (this dump keeps a game on one line)
            toks = []
            for t in re.sub(r"\{[^}]*\}", " ", line).split():
                if MOVE_NO.match(t) or t in RESULTS: continue
                t = re.sub(r"^\d+\.+", "", t)
                if t: toks.append(t)
                if len(toks) >= MAX_PLY + 1: break
            yield hdr, toks
            hdr = {}

def main(dump, out):
    t0 = time.time()
    root = {"n": 0, "c": {}}
    total = 0
    for hdr, toks in games(dump):
        try:
            if int(hdr.get("WhiteElo", 0)) < MIN_ELO or int(hdr.get("BlackElo", 0)) < MIN_ELO: continue
        except ValueError: continue
        if is_bullet(hdr.get("TimeControl")): continue
        total += 1
        node = root; node["n"] += 1
        for t in toks[:MAX_PLY]:
            node = node["c"].setdefault(t, {"n": 0, "c": {}})
            node["n"] += 1
    print(f"{total} games in bucket, {time.time()-t0:.0f}s", file=sys.stderr)
    thresh = CUTOFF * total

    # chess-openings TSV: epd -> (eco, name)
    names = {}
    for f in sorted(glob.glob("../../refs/lichess/chess-openings-*.tsv")):
        for line in open(f, encoding="utf-8"):
            eco, name, pgn = line.rstrip("\n").split("\t")
            if eco == "eco": continue
            b = chess.Board()
            try:
                for t in pgn.split():
                    if MOVE_NO.match(t): continue
                    b.push_san(t)
            except ValueError: continue
            names.setdefault(b.epd(), (eco, name))

    nodes = []
    def walk(node, path, board, parent, inherited):
        epd = board.epd()
        eco, name = names.get(epd, inherited)
        nid = len(nodes)
        rec = {"id": nid, "parent": parent, "ply": len(path), "path": path, "san": path[-1] if path else None,
               "count": node["n"], "fen": board.fen(), "epd": epd, "eco": eco, "name": name,
               "named_here": epd in names, "children": []}
        nodes.append(rec)
        kept = sorted(((c["n"], san, c) for san, c in node["c"].items() if c["n"] >= thresh), reverse=True)[:WIDTH]
        mass = sum(n for n, _, _ in kept) or 1
        for n, san, child in kept:
            b2 = board.copy(); mv = b2.push_san(san)
            cid = walk(child, path + [san], b2, nid, (eco, name))
            nodes[cid]["uci"] = mv.uci(); nodes[cid]["pop"] = n / mass
            rec["children"].append(cid)
        return nid
    walk(root, [], chess.Board(), None, ("", "Start position"))
    leaves = sum(1 for n in nodes if not n["children"])
    print(f"{len(nodes)} nodes, {leaves} leaf paths, max ply {max(n['ply'] for n in nodes)}", file=sys.stderr)
    json.dump({"games": total, "cutoff": CUTOFF, "width": WIDTH, "nodes": nodes}, open(out, "w"))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
