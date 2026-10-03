#!/usr/bin/env python3
"""Rerun of repertoire-rule-analysis.py on a RECENT Lichess month (ticket 13).

Streams the monthly .pgn.zst dump over HTTP (never stored on disk), decompresses
on the fly, and stops early: as soon as the band 1800-2100 has TARGET_GAMES games
after filters, or MAX_BYTES of compressed data have been read.  Because the dump
is ordered by game time, the prefix is a sample of the first days of the month.

Filters are ADR 0003's (docs/adr/0003-opening-tree-snapshot.md): both players'
ratings inside one 300-wide band (lower bound inclusive), games without a rating
header dropped, games with a BOT title dropped, bullet and ultrabullet excluded
(blitz, rapid, classical and correspondence pooled).  Two bands get a trie:
1800-2100 and 1500-1800 (ply 36, game counts, EPD per node).

Rules measured (all top-3, ply cap 36):
  A. absolute 0.2 % cut-off (the old rule)                             [reference]
  C. book-terminated at floors 0.2 / 0.1 / 0.04 / 0.02 / 0.01 % of the band's games
     (top-3 tree at the floor, pruned to nodes with an exactly-named position
     at or below them), plus C uncapped at 0.02 %
  D. the book itself: named lines with any game / with >= 0.02 %, own order and pooled
  E. band 1800-2100, C at 0.02 % and 0.1 %: Sicilian leaves and Sicilian misses
  W. width variants of C at 0.02 % and 0.04 % (book-pruned): top-3 / top-4 / top-5,
     top-3 plus every further reply with >= 5 / 8 / 10 % of the games reaching the
     parent ("share width"), and uncapped; with kept-reply and discard statistics,
     the kept replies after 1.e4 c5 and 1.e4 c5 2.Nf3, and the transposition table
     per width rule at 0.02 %

Usage:
    python repertoire-rule-analysis-recent.py <dump-url-or-path> <chess-openings-dist.tsv> <out.md>
        [--target-games N] [--max-bytes B]

Reuses tree-width-analysis.py (tokenizer) and repertoire-rule-analysis.py
(trie, rules, book) from the same directory.  Requires python-chess 1.11.2 and
zstandard.  See docs/research/repertoire-rule-candidates-recent.md.
"""

import importlib.util
import io
import math
import os
import resource
import sys
import time
import urllib.request
from collections import Counter

import chess
import zstandard as zstd

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tw = _load("tree_width_analysis", "tree-width-analysis.py")
rra = _load("repertoire_rule_analysis", "repertoire-rule-analysis.py")

TARGET_GAMES = 150_000          # stop when band 1800-2100 has this many games
MAX_BYTES = 4 * 1024 ** 3       # ... or when this much compressed data was read
BANDS = (1800, 1500)            # bands that get a trie (lower bound; width 300)
ALL_BANDS = (0, 1200, 1500, 1800, 2100)   # ADR 0003's five bands, counted only
WIDTH = 3
PLY_CAP = 36                    # trie depth = rule ply cap = deepest book line
OLD_CUTOFF = 0.002              # rule A
FLOORS = (0.002, 0.001, 0.0004, 0.0002, 0.0001)   # rule C
UNCAPPED_FLOOR = 0.0002
E_FLOORS = (0.0002, 0.001)      # section E, band 1800-2100
E_BAND = 1800
WIDTH_FLOORS = (0.0002, 0.0004)     # section W
SHARES = (0.05, 0.08, 0.10)
REPLY_POSITIONS = (("e4", "c5"), ("e4", "c5", "Nf3"))   # section W reply lists (SAN path)
SIC_PREFIX = ("e2e4", "c7c5")
SIC_NAME = "Sicilian Defense"
SPEEDS_OUT = ("UltraBullet", "Bullet")
SPEEDS_IN = ("Blitz", "Rapid", "Classical", "Correspondence")


def pct(f):
    return ("%.4f" % (f * 100)).rstrip("0").rstrip(".") + " %"


# (label, cap, share): the top-`cap` replies clearing the floor are kept (cap None =
# every reply clearing the floor); with `share` set, every further reply whose count
# is >= share x the games reaching the parent (in this move order) is kept as well.
WIDTH_RULES = ([("top-3", 3, None), ("top-4", 4, None), ("top-5", 5, None)]
               + [("top-3 + share %s" % pct(s), 3, s) for s in SHARES]
               + [("UNCAPPED", None, None)])


# --------------------------------------------------------------------------
# Streaming source: HTTP with Range resume, counting compressed bytes
# --------------------------------------------------------------------------

class HttpStream(object):
    """A read(n) file object over an HTTP URL; reconnects with a Range header
    at the current offset if the connection drops.  `.offset` = compressed
    bytes handed to the decompressor."""

    def __init__(self, url, retries=20):
        self.url, self.retries, self.offset = url, retries, 0
        self.resp, self.length = None, None
        self._open()

    def _open(self):
        req = urllib.request.Request(self.url, headers={"User-Agent": "chessop-research/1.0"})
        if self.offset:
            req.add_header("Range", "bytes=%d-" % self.offset)
        self.resp = urllib.request.urlopen(req, timeout=120)
        if self.length is None:
            self.length = int(self.resp.headers.get("Content-Length", "0") or 0)
        elif self.resp.status != 206:
            raise RuntimeError("server ignored Range (status %d)" % self.resp.status)

    def read(self, n=-1):
        for attempt in range(self.retries):
            try:
                data = self.resp.read(n)
            except Exception as exc:      # noqa: BLE001 - any transport error
                print("stream error at %d: %s; reconnecting" % (self.offset, exc), file=sys.stderr)
                data = None
            if data:
                self.offset += len(data)
                return data
            if data == b"" and self.length and self.offset >= self.length:
                return b""                # true end of file
            time.sleep(2 * (attempt + 1))
            self._open()
        raise RuntimeError("gave up reconnecting at offset %d" % self.offset)

    def close(self):
        try:
            self.resp.close()
        except Exception:                 # noqa: BLE001
            pass


class FileStream(object):
    def __init__(self, path):
        self.fh = open(path, "rb")
        self.offset = 0
        self.length = os.path.getsize(path)

    def read(self, n=-1):
        data = self.fh.read(n)
        self.offset += len(data)
        return data

    def close(self):
        self.fh.close()


# --------------------------------------------------------------------------
# Filters (ADR 0003) and streaming parse
# --------------------------------------------------------------------------

def speed_ok(headers):
    """Bullet and ultrabullet out, by the Event header's speed word; if the
    Event has none, by the prototype's estimated-duration rule."""
    ev = headers.get("Event", "")
    for w in SPEEDS_OUT:
        if w in ev:
            return False
    for w in SPEEDS_IN:
        if w in ev:
            return True
    return not rra.is_bullet(headers.get("TimeControl"))


def band_of(headers, drops):
    """Lower bound of the 300-wide band both players are in, or None (the
    reason is counted in `drops`)."""
    we, be = tw.elo(headers, "WhiteElo"), tw.elo(headers, "BlackElo")
    if we is None or be is None:
        drops["no rating"] += 1
        return None
    if headers.get("WhiteTitle") == "BOT" or headers.get("BlackTitle") == "BOT":
        drops["BOT title"] += 1
        return None
    if not speed_ok(headers):
        drops["bullet / ultrabullet"] += 1
        return None
    for lo in ALL_BANDS:
        lo_ = lo if lo else -1
        hi = 1200 if lo == 0 else (10 ** 6 if lo == 2100 else lo + 300)
        if lo_ <= we < hi and lo_ <= be < hi:
            return lo
    drops["players in different bands"] += 1
    return None


def stream_games(src, want):
    """Yield (band, headers, moves) for games `want(headers)` maps to a band;
    other games are skipped without tokenizing their movetext.  Reuses the
    tokenizer of tree-width-analysis.py; the header/movetext state machine is
    that of its iter_games."""
    dctx = zstd.ZstdDecompressor()
    with dctx.stream_reader(src) as reader:
        text = io.TextIOWrapper(reader, encoding="utf-8", errors="replace")
        headers, moves, in_moves, band = {}, [], False, None
        for line in text:
            s = line.strip()
            if not s:
                continue
            if s[0] == "[":
                if in_moves:
                    if band is not None:
                        yield band, headers, moves
                    headers, moves, in_moves, band = {}, [], False, None
                m = tw.HEADER.match(s)
                if m:
                    headers[m.group(1)] = m.group(2)
                continue
            if not in_moves:
                in_moves = True
                band = want(headers)
            if band is None:
                continue
            toks, done = tw.tokenize_movetext(s)
            moves.extend(toks)
            if done:
                yield band, headers, moves
                headers, moves, in_moves, band = {}, [], False, None
        if in_moves and band is not None:
            yield band, headers, moves


def build_tries(src, target, max_bytes):
    roots = {b: rra.Node(None, 0) for b in BANDS}
    st = {"seen": 0, "kept": Counter(), "drops": Counter(), "speeds": Counter(),
          "dates": {}, "all_dates": [None, None], "stop": None}

    def want(headers):
        st["seen"] += 1
        d = headers.get("UTCDate")
        if d:
            d = d + " " + headers.get("UTCTime", "")
            a = st["all_dates"]
            a[0] = d if a[0] is None or d < a[0] else a[0]
            a[1] = d if a[1] is None or d > a[1] else a[1]
        b = band_of(headers, st["drops"])
        if b is not None:
            st["kept"][b] += 1
            if d:
                rng = st["dates"].setdefault(b, [d, d])
                rng[0], rng[1] = min(rng[0], d), max(rng[1], d)
        return b if b in roots else None

    t0 = time.time()
    for band, headers, moves in stream_games(src, want):
        ev = headers.get("Event", "")
        st["speeds"][(band, next((w for w in SPEEDS_OUT + SPEEDS_IN if w in ev), "?"))] += 1
        node = roots[band]
        node.count += 1
        for san in moves[:PLY_CAP]:
            ch = node.kids.get(san)
            if ch is None:
                ch = node.kids[san] = rra.Node(san, node.ply + 1)
            ch.count += 1
            node = ch
        if st["kept"][1800] >= target:
            st["stop"] = "band 1800-2100 reached %d games" % target
            break
        if src.offset >= max_bytes:
            st["stop"] = "%d compressed bytes read" % src.offset
            break
        if st["seen"] >= st.get("next_report", 200000):
            st["next_report"] = st["seen"] + 200000
            print("  %d games seen, kept %s, %.0f MB read, %.0fs"
                  % (st["seen"], dict(st["kept"]), src.offset / 1e6, time.time() - t0),
                  file=sys.stderr)
    st["bytes"] = src.offset
    st["length"] = src.length
    st["parse_s"] = time.time() - t0
    print("stopped: %s; %d games seen, kept %s, %d bytes, %.0fs"
          % (st["stop"], st["seen"], dict(st["kept"]), src.offset, st["parse_s"]),
          file=sys.stderr)
    return roots, st


# --------------------------------------------------------------------------
# Per-band measurement
# --------------------------------------------------------------------------

def seq_node(root, uci):
    """Walk a uci tuple through the trie; the node reached, or None."""
    nd = root
    for u in uci:
        nxt = None
        for c in nd.kids.values():
            if c.uci == u:
                nxt = c
                break
        if nxt is None:
            return None
        nd = nxt
    return nd


def floor_games(f, n):
    """Smallest integer count clearing the unrounded threshold f * n."""
    return int(math.ceil(f * n - 1e-9))


def select_width(root, m, cap, share, ply_cap):
    """Rule-C width variants (section W).  Replies with >= m games, count desc
    then SAN desc (as rra.select); the top-`cap` are kept, plus, when `share`
    is set, every further one with count >= share x parent.count.  cap None
    keeps every reply clearing the floor.  Same tree shape as rra.select."""
    T = {root: []}
    stack = [root]
    while stack:
        nd = stack.pop()
        if nd.ply >= ply_cap:
            continue
        kids = sorted((c for c in nd.kids.values() if c.count >= m),
                      key=lambda c: (c.count, c.san), reverse=True)
        if cap is not None:
            kids = [c for i, c in enumerate(kids)
                    if i < cap or (share is not None and c.count >= share * nd.count)]
        T[nd] = kids
        for c in kids:
            T[c] = []
            stack.append(c)
    return T


def width_stats(T):
    """Over the internal nodes of T (nodes with >= 1 kept reply, the learner's
    decision points): kept replies mean / max, and the traffic-weighted discard
    (tree-width-measurements.md): sum of games reaching the node minus games
    continuing along kept replies, over the sum of games reaching the nodes."""
    internal = [n for n in T if T[n]]
    reach = sum(n.count for n in internal)
    kept = sum(c.count for n in internal for c in T[n])
    ks = [len(T[n]) for n in internal]
    return {"internal": len(internal),
            "mean_kids": (float(sum(ks)) / len(ks)) if ks else 0.0,
            "max_kids": max(ks) if ks else 0,
            "reach": reach, "kept": kept,
            "discard": (100.0 * (reach - kept) / reach) if reach else 0.0}


def kept_replies(T, root, sans):
    """(games reaching the position in this order, [(san, count)] kept in T)
    for a SAN path; None if the position is not in T."""
    nd = root
    for s in sans:
        nd = nd.kids.get(s)
        if nd is None or nd not in T:
            return None
    return nd.count, [(c.san, c.count) for c in T[nd]]


def why_missed(root, T, uci, m):
    """Walk the book's own move order through the trie and the rule tree and
    name the first move that is not in the tree (generalised from the 2013
    script's section E, with the floor m in games)."""
    nd = root
    for i, u in enumerate(uci):
        nxt = next((c for c in nd.kids.values() if c.uci == u), None)
        if nxt is None:
            return "ply %d: %s never played in this order" % (i + 1, u), "never"
        if nxt not in T:
            sibs = sorted((c for c in nd.kids.values() if c.count >= m),
                          key=lambda c: (c.count, c.san), reverse=True)
            rank = next((k + 1 for k, c in enumerate(sibs) if c is nxt), None)
            if nd.ply >= PLY_CAP:
                return "ply %d: beyond the ply cap" % (i + 1), "cap"
            if nxt.count < m:
                return ("ply %d: %s has %d games in this order (< %d)"
                        % (i + 1, nxt.san, nxt.count, m)), "floor"
            if nd not in T:
                return "ply %d: parent already pruned" % (i + 1), "other"
            if rank is not None and rank > WIDTH:
                return ("ply %d: %s has %d games, rank %d of %d (outside top-3; kept: %s)"
                        % (i + 1, nxt.san, nxt.count, rank, len(sibs),
                           ", ".join("%s %d" % (c.san, c.count) for c in sibs[:WIDTH]))), "top3"
            # kept by popularity, pruned for lack of a named position with >= m
            # games below it in this order: walk on along the book's own order
            # to the first move that falls below the floor or outside the top-3
            head = ("ply %d: %s (%d games, rank %s) pruned, nothing named with >= %d games "
                    "reachable below it in this order; " % (i + 1, nxt.san, nxt.count, rank, m))
            cur = nxt
            for j in range(i + 1, len(uci)):
                nxt2 = next((c for c in cur.kids.values() if c.uci == uci[j]), None)
                if nxt2 is None or nxt2.count < m:
                    return (head + "the book's own order drops below the floor at ply %d: %s has "
                            "%d games in this order (< %d)"
                            % (j + 1, nxt2.san if nxt2 else uci[j], nxt2.count if nxt2 else 0, m)), "floor"
                sibs2 = sorted((c for c in cur.kids.values() if c.count >= m),
                               key=lambda c: (c.count, c.san), reverse=True)
                rank2 = next((k + 1 for k, c in enumerate(sibs2) if c is nxt2), None)
                if rank2 is not None and rank2 > WIDTH:
                    return (head + "ply %d: %s has %d games, rank %d of %d (outside top-3; kept: %s)"
                            % (j + 1, nxt2.san, nxt2.count, rank2, len(sibs2),
                               ", ".join("%s %d" % (c.san, c.count) for c in sibs2[:WIDTH]))), "top3"
                cur = nxt2
            return head + "(unexplained)", "other"
        nd = nxt
    return "?", "other"


def measure_band(band, root, n_games, rows, names, sic_rows, sic_tsv, sic_named, want_E):
    t0 = time.time()
    n_nodes_raw = len(rra.all_nodes(root))
    visited, dropped = rra.key_trie(root)
    nodes = rra.all_nodes(root)
    pos_count = Counter()
    for nd in nodes:
        pos_count[nd.epd] += nd.count
    seq_count = {}
    for eco, name, pgn, uci, epd in rows:
        nd = seq_node(root, uci)
        seq_count[uci] = nd.count if nd is not None else 0
    print("band %d: %d trie nodes (%d before keying), %d games dropped, keyed in %.0fs"
          % (band, len(nodes), n_nodes_raw, dropped, time.time() - t0), file=sys.stderr)

    def M(T):
        return rra.measure(T, root, names, sic_tsv, sic_named, PLY_CAP)

    cells = []      # (rule, label, f, m, T, measure, pre-measure or None)
    m = floor_games(OLD_CUTOFF, n_games)
    T = rra.select(root, lambda c, p, m=m: c.count >= m, WIDTH, PLY_CAP)
    cells.append(("A", "old rule: count >= %s, top-3" % pct(OLD_CUTOFF), OLD_CUTOFF, m, T, M(T), None))
    for f in FLOORS:
        m = floor_games(f, n_games)
        T0 = rra.select(root, lambda c, p, m=m: c.count >= m, WIDTH, PLY_CAP)
        T = rra.prune_to_named(T0, root, names)
        cells.append(("C", "f = %s, top-3, book-pruned" % pct(f), f, m, T, M(T), M(T0)))
    m = floor_games(UNCAPPED_FLOOR, n_games)
    T0 = rra.select(root, lambda c, p, m=m: c.count >= m, None, PLY_CAP)
    T = rra.prune_to_named(T0, root, names)
    cells.append(("C", "f = %s, UNCAPPED, book-pruned" % pct(UNCAPPED_FLOOR), UNCAPPED_FLOOR,
                  m, T, M(T), M(T0)))

    # D: the book against this band's traffic
    def ge(rows_, k, pooled):
        if pooled:
            return sum(1 for r in rows_ if pos_count.get(r[4], 0) >= k)
        return sum(1 for r in rows_ if seq_count.get(r[3], 0) >= k)
    sic391 = [r for r in rows if r[1].startswith(SIC_NAME)]
    D = {}
    for label, rows_ in (("all", rows), ("sic401", sic_rows), ("sic391", sic391)):
        D[label] = {"n": len(rows_),
                    "ge1": (ge(rows_, 1, False), ge(rows_, 1, True)),
                    "floors": {f: (ge(rows_, floor_games(f, n_games), False),
                                   ge(rows_, floor_games(f, n_games), True)) for f in FLOORS}}

    # transposition-only misses at the uncapped floor: pooled >= m, absent from the
    # uncapped tree by EPD (so no single move order clears the floor)
    m = floor_games(UNCAPPED_FLOOR, n_games)
    T_unc = cells[-1][4]
    T_top = [c for c in cells if c[0] == "C" and c[2] == UNCAPPED_FLOOR and "UNCAPPED" not in c[1]][0][4]
    unc_epds = {n.epd for n in T_unc}
    top_epds = {n.epd for n in T_top}
    trans = {}
    for label, rows_ in (("all", rows), ("sic401", sic_rows)):
        withm = [r for r in rows_ if pos_count.get(r[4], 0) >= m]
        trans[label] = {
            "with_m": len(withm),
            "in_top3": sum(1 for r in withm if r[4] in top_epds),
            "width_only": sum(1 for r in withm if r[4] in unc_epds and r[4] not in top_epds),
            "trans_only": sum(1 for r in withm if r[4] not in unc_epds),
            "trans_examples": sorted(
                [(pos_count[r[4]], seq_count.get(r[3], 0), r[1], r[0], len(r[3]), r[2])
                 for r in withm if r[4] not in unc_epds], reverse=True)[:12],
        }

    # W: width variants of rule C (book-pruned) at WIDTH_FLOORS; the transposition
    # split at the uncapped floor reuses unc_epds (the 0.02 % uncapped tree)
    W = []
    for f in WIDTH_FLOORS:
        m = floor_games(f, n_games)
        for label, cap, share in WIDTH_RULES:
            T0 = select_width(root, m, cap, share, PLY_CAP)
            T = rra.prune_to_named(T0, root, names)
            epds = {n.epd for n in T}
            tr = None
            if f == UNCAPPED_FLOOR:
                tr = {}
                for lab, rows_ in (("all", rows), ("sic401", sic_rows)):
                    withm = [r for r in rows_ if pos_count.get(r[4], 0) >= m]
                    tr[lab] = {"with_m": len(withm),
                               "in_tree": sum(1 for r in withm if r[4] in epds),
                               "width_only": sum(1 for r in withm if r[4] in unc_epds and r[4] not in epds),
                               "trans_only": sum(1 for r in withm if r[4] not in unc_epds)}
            W.append({"label": label, "f": f, "m": m, "cap": cap, "share": share,
                      "r": M(T), "pre": M(T0), "w": width_stats(T), "w0": width_stats(T0),
                      "replies": {p: kept_replies(T, root, p) for p in REPLY_POSITIONS},
                      "trans": tr})

    E = {}
    if want_E:
        for f in E_FLOORS:
            m = floor_games(f, n_games)
            T = [c for c in cells if c[0] == "C" and c[2] == f and "UNCAPPED" not in c[1]][0][4]
            par = rra.parents_of(T, root)
            s = rra.sic_node(T, root)
            leaves = []
            if s is not None:
                for nd in rra.subtree(T, s):
                    if not T[nd]:
                        nm = names.get(nd.epd)
                        leaves.append((nd.ply, nm[0] if nm else "", nm[1] if nm else "(unnamed)",
                                       nd.count, rra.node_path(root, nd, par)))
            leaves.sort(key=lambda t: t[4])
            in_tree = {n.epd for n in T}
            misses = []
            for eco, name, pgn, uci, epd in sic_rows:
                pooled = pos_count.get(epd, 0)
                if pooled < m or epd in in_tree:
                    continue
                why, kind = why_missed(root, T, uci, m)
                misses.append((name, eco, len(uci), pooled, seq_count.get(uci, 0), why, kind, pgn))
            misses.sort(key=lambda t: (-t[3], t[2]))
            # lines with >= 0.02 % pooled missed at this floor, by reason
            m02 = floor_games(UNCAPPED_FLOOR, n_games)
            kinds02 = Counter()
            for eco, name, pgn, uci, epd in sic_rows:
                if pos_count.get(epd, 0) >= m02 and epd not in in_tree:
                    kinds02[why_missed(root, T, uci, m)[1]] += 1
            E[f] = {"m": m, "leaves": leaves, "misses": misses, "kinds02": kinds02,
                    "n02": sum(kinds02.values())}

    e4c5 = chess.Board()
    e4c5.push_uci("e2e4")
    e4c5.push_uci("c7c5")
    return {"band": band, "n_games": n_games, "trie_nodes": len(nodes), "dropped": dropped,
            "cells": cells, "D": D, "trans": trans, "E": E, "W": W,
            "e4c5_games": pos_count.get(e4c5.epd(), 0),
            "first_moves": sorted(((c.count, c.san) for c in root.kids.values()), reverse=True)[:6]}


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

table, by_ply_str = rra.table, rra.by_ply_str

SUMMARY_HEAD = [
    "rule", "cell", "floor (games)", "nodes (root incl.)", "lines (leaf paths)", "max ply",
    "largest kept-reply count", "book lines covered (of 3810)",
    "Sicilian nodes", "Sicilian lines", "Sicilian max ply",
    "Sicilian book lines covered (of 401 / 391)", "hits ply cap 36",
]


def summary_rows(R):
    out = []
    for rule, label, f, m, T, r, pre in R["cells"]:
        out.append([rule, label, ">= %d" % m, r["nodes"], r["leaves"], r["max_ply"], r["max_kids"],
                    r["tsv_in_tree"], r["s_nodes"], r["s_leaves"], r["s_max_ply"],
                    "%d / %d" % (r["s_tsv_in_tree"], r["s_named_in_tree"]),
                    "yes" if r["truncated"] else "no"])
    return out


def band_name(b):
    return "2100 and above" if b == 2100 else ("%d-%d" % (b, b + 300) if b else "below 1200")


def write_report(out_path, url, st, results, rows, names, sic_tsv, sic_named, timing):
    L = []
    A = L.append
    fname = url.rsplit("/", 1)[-1]
    month = fname.split("_")[-1].split(".")[0]
    A("# Repertoire size under candidate rules, on a recent month (%s)" % month)
    A("")
    A("Ticket: [`.scratch/chessop/issues/13-repertoire-named-variations.md`]"
      "(../../.scratch/chessop/issues/13-repertoire-named-variations.md). Rerun of "
      "[`repertoire-rule-candidates.md`](repertoire-rule-candidates.md) (2013-01, 5,017 "
      "games at 1800+) on `%s`, with ADR 0003's bands and filters." % fname)
    A("Script: [`refs/lichess/repertoire-rule-analysis-recent.py`]"
      "(../../refs/lichess/repertoire-rule-analysis-recent.py) (imports the 2013 script's "
      "trie, rules and book code and the shared tokenizer). Generated; every number below "
      "is one run of it. No recommendation is made here.")
    A("")
    A("## Method and sample")
    A("")
    A("- **Source**: `%s` (%s bytes, CC0), streamed over HTTP through a zstandard "
      "streaming decompressor and parsed as it arrived; nothing was written to disk. "
      "The dump is ordered by game time, so a prefix is a sample of the **start of the "
      "month**, not of the whole month (here: %s, see the date range below). Reading "
      "stopped when band 1800-2100 had "
      "%s games after filters or after %s compressed bytes, whichever came first: "
      "**stopped because %s**, after **%s compressed bytes** (%.2f %% of the file) "
      "and **%s games seen**."
      % (fname, format(st["length"], ","),
         "a single day" if st["all_dates"][0][:10] == st["all_dates"][1][:10]
         else "%d days" % (int(st["all_dates"][1][8:10]) - int(st["all_dates"][0][8:10]) + 1),
         format(TARGET_GAMES, ","),
         format(MAX_BYTES, ","), st["stop"], format(st["bytes"], ","),
         100.0 * st["bytes"] / st["length"], format(st["seen"], ",")))
    A("- **Date range of the games seen** (`UTCDate UTCTime`): %s to %s. Per band kept: %s."
      % (st["all_dates"][0], st["all_dates"][1],
         "; ".join("%s %s to %s" % (band_name(b), d[0], d[1]) for b, d in sorted(st["dates"].items()))))
    A("- **Filters** (ADR 0003): both `WhiteElo` and `BlackElo` present and numeric; no "
      "`WhiteTitle`/`BlackTitle` of `BOT`; `Event` speed not Bullet or UltraBullet "
      "(Blitz, Rapid, Classical and Correspondence pooled; an Event without a speed word "
      "falls back to the prototype's base + 40 x increment < 180 s rule); both players "
      "inside the same 300-wide band, lower bound inclusive. Games dropped: %s."
      % ", ".join("%s %s" % (k, format(v, ",")) for k, v in st["drops"].most_common()))
    A("- **Games kept per band** (all five bands counted; tries built for two): %s."
      % ", ".join("%s **%s**" % (band_name(b), format(st["kept"][b], ",")) for b in ALL_BANDS))
    A("- **Speeds of the games in the two trie bands**: %s."
      % "; ".join("%s: %s" % (band_name(b), ", ".join("%s %s" % (sp, format(n, ","))
                                                       for (bb, sp), n in sorted(st["speeds"].items()) if bb == b))
                  for b in BANDS))
    A("- **Trie**: one move-sequence trie per band (transpositions not merged), mainline "
      "SAN from the shared tokenizer of `tree-width-analysis.py` (annotations stripped), "
      "built to **ply %d** (the deepest book line) with no thinning: every node was kept "
      "and keyed by python-chess `Board.epd()`. %s. Games dropped under SAN tokens "
      "python-chess rejects: %s. Peak resident memory of the whole run %.1f GB; parse "
      "%.0f s, keying and measuring %.0f s."
      % (PLY_CAP,
         "; ".join("band %s: %s nodes" % (band_name(R["band"]), format(R["trie_nodes"], ","))
                   for R in results),
         ", ".join("%s %d" % (band_name(R["band"]), R["dropped"]) for R in results),
         timing["rss_gb"], st["parse_s"], timing["measure_s"]))
    A("- **Node count**, **pooled count**, **named**, **top-3** (count desc, then SAN desc "
      "ties), **nodes** (root included), **lines** (= leaf paths), **Sicilian subtree** "
      "(sequence subtree under `1.e4 c5`; %d book rows start `e2e4 c7c5`, %d of them named "
      "`Sicilian Defense…`): as in the 2013 document."
      % (len(sic_tsv), len(sic_named)))
    A("- **Floors** are a share of the band's kept games; the threshold is unrounded "
      "(count >= f x N), and the table gives the resulting integer game count. "
      "**Every rule tree is capped at ply %d** (a node at ply %d keeps no reply); "
      "`hits ply cap` flags a tree with a node there." % (PLY_CAP, PLY_CAP))
    A("- **Rule A**: the old rule, count >= 0.2 %%, top-3. **Rule C**: top-3 tree at the "
      "floor, then every node with no exactly-named position at or below it (by EPD) "
      "pruned; the uncapped row keeps every reply clearing the floor before pruning. "
      "**Rule D**: the book's %d rows against the band's traffic, by the row's own move "
      "order (sequence count) and pooled over every move order into the position (EPD)."
      % len(rows))
    A("")

    for R in results:
        b, n = R["band"], R["n_games"]
        A("## Band %s: %s games" % (band_name(b), format(n, ",")))
        A("")
        A("First moves: %s." % ", ".join("%s %s" % (s, format(c, ",")) for c, s in R["first_moves"]))
        A("")
        A("### Summary")
        A("")
        A(table(SUMMARY_HEAD, summary_rows(R)))
        A("")
        A("Rule C, size before the book-pruning step (top-3 or uncapped tree at the floor, ply cap %d):" % PLY_CAP)
        A("")
        A(table(["cell", "nodes before pruning", "lines before pruning", "max ply before",
                 "Sicilian nodes before", "Sicilian lines before"],
                [[label, pre["nodes"], pre["leaves"], pre["max_ply"], pre["s_nodes"], pre["s_leaves"]]
                 for rule, label, f, m, T, r, pre in R["cells"] if pre is not None]))
        A("")
        A("### Per-rule detail")
        A("")
        for rule, label, f, m, T, r, pre in R["cells"]:
            A("- **%s (>= %d games)**: %d nodes / %d lines / max ply %d (largest kept-reply "
              "count %d); book lines covered %d of %d; nodes by ply %s. Sicilian: %d nodes / "
              "%d lines / max ply %d, %d of the 401 `1.e4 c5` book lines (%d of the 391 "
              "`Sicilian Defense` ones) covered."
              % (rule + ", " + label, m, r["nodes"], r["leaves"], r["max_ply"], r["max_kids"],
                 r["tsv_in_tree"], len(rows), by_ply_str(r["by_ply"]), r["s_nodes"],
                 r["s_leaves"], r["s_max_ply"], r["s_tsv_in_tree"], r["s_named_in_tree"]))
        A("")
        A("### Rule C coverage of the book")
        A("")
        A("Book lines in the tree against the book lines with >= floor games at all "
          "(own move order / pooled over move orders).")
        A("")
        D = R["D"]
        A(table(["cell", "floor (games)", "book lines in tree / with >= floor (own order) / (pooled)",
                 "Sicilian 401: in tree / >= floor (own order) / (pooled)"],
                [[label, ">= %d" % m,
                  "%d / %d / %d" % (r["tsv_in_tree"], D["all"]["floors"][f][0], D["all"]["floors"][f][1]),
                  "%d / %d / %d" % (r["s_tsv_in_tree"], D["sic401"]["floors"][f][0], D["sic401"]["floors"][f][1])]
                 for rule, label, f, m, T, r, pre in R["cells"] if rule == "C"]))
        A("")
        A("### Rule D: the book itself")
        A("")
        A("Named book lines with traffic in this band, by the row's own move order and pooled over every move order.")
        A("")
        A(table(["rows", "n", "any game (own order / pooled)"] +
                ["%s = >= %d games (own / pooled)" % (pct(f), floor_games(f, n)) for f in FLOORS],
                [[lab, D[k]["n"], "%d / %d" % D[k]["ge1"]] +
                 ["%d / %d" % D[k]["floors"][f] for f in FLOORS]
                 for k, lab in (("all", "whole book (3810)"), ("sic401", "`1.e4 c5` rows (401)"),
                                ("sic391", "`Sicilian Defense` rows (391)"))]))
        A("")
        A("`1.e4 c5` is reached by %s games (pooled)." % format(R["e4c5_games"], ","))
        A("")
        A("### Transposition-only misses at f = %s (>= %d games)"
          % (pct(UNCAPPED_FLOOR), floor_games(UNCAPPED_FLOOR, n)))
        A("")
        A("Of the named lines with >= floor pooled games: in the top-3 tree; missed by "
          "width only (present in the uncapped tree, absent from the top-3 one); missed "
          "only because the traffic arrives by move orders other than the book's own (no "
          "single move order into the position clears the floor, so the line is absent "
          "even from the uncapped tree).")
        A("")
        tr = R["trans"]
        A(table(["rows", "with >= floor (pooled)", "in top-3 tree", "missed by width only",
                 "missed by transposition only"],
                [[lab, t["with_m"], t["in_top3"], t["width_only"], t["trans_only"]]
                 for k, lab in (("all", "whole book"), ("sic401", "`1.e4 c5` rows"))
                 for t in [tr[k]]]))
        A("")
        if tr["all"]["trans_examples"]:
            A("Largest transposition-only misses (whole book), pooled games / own-order games:")
            A("")
            A(table(["pooled", "own order", "name", "ECO", "ply", "line"],
                    [[p, s, nm, eco, ply, "`%s`" % pgn] for p, s, nm, eco, ply, pgn in tr["all"]["trans_examples"]]))
            A("")

    # ---- E
    R = [R for R in results if R["band"] == E_BAND][0]
    n = R["n_games"]
    A("## Rule E: band %s, rule C top-3, the Sicilian in detail" % band_name(E_BAND))
    A("")
    for f in E_FLOORS:
        E = R["E"][f]
        m = E["m"]
        A("### f = %s (>= %d games): Sicilian leaf lines (%d)" % (pct(f), m, len(E["leaves"])))
        A("")
        A("Every leaf is an exactly-named position. Sorted by move sequence.")
        A("")
        A(table(["ply", "ECO", "name", "games (this order)", "line"],
                [[p, eco, nm, cnt, "`%s`" % path] for p, eco, nm, cnt, path in E["leaves"]]))
        A("")
        A("### f = %s: named `1.e4 c5` book lines with >= %d games (pooled) that top-3 misses (%d)"
          % (pct(f), m, len(E["misses"])))
        A("")
        A("`why` walks the book's own move order through the trie and names the first move "
          "not in the rule-C tree: its games in that order and its rank among the parent's "
          "replies with >= %d games (the kept top-3 are listed)." % m)
        A("")
        A(table(["name", "ECO", "ply", "games (pooled)", "games (own order)", "why", "line"],
                [[nm, eco, p, g, gs, why, "`%s`" % pgn] for nm, eco, p, g, gs, why, kind, pgn in E["misses"]]))
        A("")
        kinds = Counter(mm[6] for mm in E["misses"])
        names_k = {"top3": "a move on the way ranks outside the top-3",
                   "floor": "a move on the way is below the floor in the book's own move order (traffic by transposition)",
                   "never": "own move order never played", "cap": "beyond the ply cap", "other": "other"}
        A("Reasons: %s." % ("; ".join("%s: %d" % (names_k[k], v) for k, v in kinds.most_common()) or "none"))
        if f != UNCAPPED_FLOOR:
            A("")
            A("Against the %s set: %d named `1.e4 c5` lines with >= %d pooled games are not in "
              "this tree; by reason: %s."
              % (pct(UNCAPPED_FLOOR), E["n02"], floor_games(UNCAPPED_FLOOR, n),
                 "; ".join("%s: %d" % (names_k[k], v) for k, v in E["kinds02"].most_common()) or "none"))
        A("")

    # ---- W
    A("## Width variants")
    A("")
    A("Rule C (width-limited tree at the floor, then every node with no exactly-named "
      "position at or below it pruned) under other width rules, at floors %s. "
      "**top-k**: the k most played replies clearing the floor (count desc, SAN desc "
      "ties). **top-3 + share s %%**: the top-3 plus every further reply clearing the "
      "floor whose count is >= s %% of the games reaching the parent position in this "
      "move order (a fourth or later reply survives only as a real share of that "
      "position's traffic). **UNCAPPED**: every reply clearing the floor. The top-3 and "
      "0.02 %% UNCAPPED rows repeat the summary cells above (same trees) for reference. "
      "**Internal nodes** are the tree's nodes with >= 1 kept reply (the learner's "
      "decision points); **kept replies** mean / max are over them; **discard %%** is "
      "the traffic-weighted share of replies at internal nodes outside the kept set "
      "(`tree-width-measurements.md`): the sum over internal nodes of games reaching "
      "the node minus games continuing along kept replies, over the sum of games "
      "reaching internal nodes; it is given for the pruned tree (the cell) and for the "
      "width-limited tree before book-pruning. Ply cap %d throughout; %s."
      % (" and ".join(pct(f) for f in WIDTH_FLOORS), PLY_CAP,
         "no tree below hits it" if not any(c["r"]["truncated"] or c["pre"]["truncated"]
                                            for R in results for c in R["W"])
         else "a band note below flags the trees that hit it"))
    A("")
    W_HEAD = ["cell", "floor (games)", "nodes (root incl.)", "lines (leaf paths)", "max ply",
              "largest kept-reply count", "book lines covered (of 3810)",
              "Sicilian nodes", "Sicilian lines", "Sicilian max ply",
              "Sicilian book lines covered (of 401 / 391)", "internal nodes",
              "kept replies mean", "kept replies max", "discard %", "discard % before pruning"]
    for R in results:
        b, n = R["band"], R["n_games"]
        A("### Band %s: %s games" % (band_name(b), format(n, ",")))
        A("")
        hit = [c["label"] + " at " + pct(c["f"]) for c in R["W"]
               if c["r"]["truncated"] or c["pre"]["truncated"]]
        if hit:
            A("Trees hitting the ply cap (before or after pruning): %s." % ", ".join(hit))
            A("")
        A(table(W_HEAD,
                [[c["label"], "f = %s (>= %d)" % (pct(c["f"]), c["m"]),
                  r["nodes"], r["leaves"], r["max_ply"], r["max_kids"], r["tsv_in_tree"],
                  r["s_nodes"], r["s_leaves"], r["s_max_ply"],
                  "%d / %d" % (r["s_tsv_in_tree"], r["s_named_in_tree"]),
                  w["internal"], "%.2f" % w["mean_kids"], w["max_kids"],
                  "%.1f" % w["discard"], "%.1f" % c["w0"]["discard"]]
                 for c in R["W"] for r in [c["r"]] for w in [c["w"]]]))
        A("")
        A("Size before the book-pruning step (width-limited tree at the floor, ply cap %d):" % PLY_CAP)
        A("")
        A(table(["cell", "floor (games)", "nodes before pruning", "lines before pruning",
                 "max ply before", "Sicilian nodes before", "Sicilian lines before",
                 "internal nodes before", "kept replies mean before", "kept replies max before",
                 "discard % before"],
                [[c["label"], "f = %s (>= %d)" % (pct(c["f"]), c["m"]),
                  p["nodes"], p["leaves"], p["max_ply"], p["s_nodes"], p["s_leaves"],
                  w["internal"], "%.2f" % w["mean_kids"], w["max_kids"], "%.1f" % w["discard"]]
                 for c in R["W"] for p in [c["pre"]] for w in [c["w0"]]]))
        A("")
        A("Book coverage at f = %s (>= %d games), per width rule: of the named lines with "
          ">= floor pooled games, in the (pruned) tree; missed by width only (present in "
          "the uncapped tree at this floor, absent from this one); missed by transposition "
          "only (absent even from the uncapped tree), as in the transposition table above."
          % (pct(UNCAPPED_FLOOR), floor_games(UNCAPPED_FLOOR, n)))
        A("")
        A(table(["width rule", "whole book: with >= floor (pooled)", "in tree", "missed by width only",
                 "missed by transposition only", "`1.e4 c5` rows: with >= floor (pooled)",
                 "in tree", "missed by width only", "missed by transposition only"],
                [[c["label"],
                  t["all"]["with_m"], t["all"]["in_tree"], t["all"]["width_only"], t["all"]["trans_only"],
                  t["sic401"]["with_m"], t["sic401"]["in_tree"], t["sic401"]["width_only"],
                  t["sic401"]["trans_only"]]
                 for c in R["W"] if c["trans"] is not None for t in [c["trans"]]]))
        A("")
    R = [R for R in results if R["band"] == E_BAND][0]
    A("### Band %s: kept replies after `1.e4 c5` and after `1.e4 c5 2.Nf3`" % band_name(E_BAND))
    A("")
    A("Replies kept in the pruned tree of each cell, with their game counts in this move "
      "order; `games` is the number of games reaching the position in this move order "
      "(the share base). `-` marks a position that is not in the tree.")
    A("")
    for p in REPLY_POSITIONS:
        pos = " ".join("%d.%s" % (i // 2 + 1, s) if i % 2 == 0 else s for i, s in enumerate(p))
        rr = [c["replies"][p] for c in R["W"]]
        games = next((g for g in rr if g is not None), (0, []))[0]
        A("After `%s` (%s games in this order):" % (pos, format(games, ",")))
        A("")
        A(table(["floor (games)", "width rule", "kept replies", "kept replies (san count)"],
                [["f = %s (>= %d)" % (pct(c["f"]), c["m"]), c["label"],
                  len(rep[1]) if rep else "-",
                  ", ".join("%s %d" % (s, k) for s, k in rep[1]) if rep else "-"]
                 for c in R["W"] for rep in [c["replies"][p]]]))
        A("")

    A("## Reproduction")
    A("")
    A("Nothing is stored: the dump is streamed and the prefix read is whatever the stop "
      "rule allows, so a rerun on the same URL reads the same prefix and gives the same numbers.")
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
    A("$S/venv/bin/python refs/lichess/repertoire-rule-analysis-recent.py \\")
    A("    %s \\" % url)
    A("    $S/chess-openings-dist.tsv docs/research/repertoire-rule-candidates-recent.md \\")
    A("    --target-games %d --max-bytes %d" % (TARGET_GAMES, MAX_BYTES))
    A("```")
    A("")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out_path, file=sys.stderr)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    target, max_bytes = TARGET_GAMES, MAX_BYTES
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
    sic_rows = [r for r in rows if r[3][:2] == SIC_PREFIX]
    sic_tsv = {r[4] for r in sic_rows}
    sic_named = {r[4] for r in rows if r[1].startswith(SIC_NAME)}

    src = HttpStream(url) if url.startswith("http") else FileStream(url)
    try:
        roots, st = build_tries(src, target, max_bytes)
    finally:
        src.close()
    t0 = time.time()
    results = [measure_band(b, roots[b], st["kept"][b], rows, names, sic_rows, sic_tsv,
                            sic_named, want_E=(b == E_BAND)) for b in BANDS]
    timing = {"measure_s": time.time() - t0,
              "rss_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6}
    write_report(out_path, url, st, results, rows, names, sic_tsv, sic_named, timing)


if __name__ == "__main__":
    main()
