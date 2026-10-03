"""Open-ended rating bands (1200+, 1500+, 1800+) against the closed bands 1500-1800 and 1800-2100.

Research script for `docs/research/open-bands.md`. Reuses `chessop.build` (stream, filters, trie,
pooled graph, snapshot writer) and `chessop.repertoire` unchanged; only the sample is a scratch
variant in which one game may count toward several bands.

    .venv/bin/python refs/lichess/open-bands-analysis.py build  WORKDIR   # stream + graphs
    .venv/bin/python refs/lichess/open-bands-analysis.py report WORKDIR   # tables (markdown)

Bands built (name: low inclusive, high exclusive, cap, "after" = only once that band is full):
    1200+, 1500+, 1800+         both players >= the bound, 150,000 games each
    1500-1800, 1800-2100        both players inside the band (as shipped), 150,000 games each
    1500+@300k                  both players >= 1500, 300,000 games (the first 150k are 1500+'s)
    1500+#2                     both >= 1500, the next 150,000 games after 1500+ filled (disjoint)
"""

import gzip
import io
import json
import resource
import sys
import time
from collections import Counter
from pathlib import Path

import zstandard

from chessop import build
from chessop.build import (
    DUMP_URL,
    PLY_CAP,
    Snapshot,
    _band_graph,
    _Counting,
    _Http,
    _Node,
    _Sample,
    load_book,
    write_graph_file,
)
from chessop.graph import BANDS, STORAGE_CUTOFF, load_graph
from chessop.repertoire import START, Repertoire, Settings, to_move

MONTH = "2026-08"
BIG = sys.maxsize
SPECS: dict[str, tuple[int, int, int, str | None]] = {
    "1200+": (1200, BIG, 150_000, None),
    "1500+": (1500, BIG, 150_000, None),
    "1800+": (1800, BIG, 150_000, None),
    "1500-1800": (1500, 1800, 150_000, None),
    "1800-2100": (1800, 2100, 150_000, None),
    "1500+@300k": (1500, BIG, 300_000, None),
    "1500+#2": (1500, BIG, 150_000, "1500+"),
}
if len(sys.argv) > 3:  # a smoke-test run: every cap divided by argv[3]
    SPECS = {b: (lo, hi, cap // int(sys.argv[3]), after) for b, (lo, hi, cap, after) in SPECS.items()}
OPEN = ("1200+", "1500+", "1800+", "1500+@300k", "1500+#2")


def bucket(r: int) -> int:
    """The 300-wide bucket aligned with the shipped band edges (..., 1500, 1800, 2100, 2400, ...)."""
    return 1200 + 300 * ((r - 1200) // 300) if r >= 1200 else 0


def shipped_band(r: int) -> str:
    return next(name for name, low, high in BANDS if low <= r < high)


class MultiSample(_Sample):
    """`_Sample` with one trie per spec, a game going into every band that wants it."""

    def __init__(self, counter: _Counting) -> None:
        super().__init__(cap=0, ply_cap=PLY_CAP, max_games=None, tries={b: _Node(0) for b in SPECS})
        self.counter = counter
        self.filled: dict[str, dict] = {}
        self.stats = {b: {"lower": Counter(), "cross_bucket": 0, "cross_band": 0, "speed": Counter(),
                          "gap": Counter()} for b in OPEN}
        self.first_date: str | None = None
        self.last_date: str | None = None
        self.no_band = 0

    def band_of(self, headers):  # the same filters as `_Sample.band_of`, then every band wanting it
        date = f"{headers.get('UTCDate', '')} {headers.get('UTCTime', '')}"
        self.first_date = self.first_date or date
        self.last_date = date
        white, black = headers.get("WhiteElo", ""), headers.get("BlackElo", "")
        if not (white.isdigit() and black.isdigit()):
            self.dropped["rating missing"] += 1
            return None
        if "BOT" in (headers.get("WhiteTitle"), headers.get("BlackTitle")):
            self.dropped["BOT title"] += 1
            return None
        event = headers.get("Event", "")
        if "Bullet" in event:
            self.dropped["bullet or ultrabullet"] += 1
            return None
        w, b = int(white), int(black)
        lo, hi = min(w, b), max(w, b)
        bands = []
        for name, (low, high, cap, after) in SPECS.items():
            if not (low <= lo and hi < high):
                continue
            if after is not None and self.tries[after].count < SPECS[after][2]:
                continue
            if self.tries[name].count >= cap:
                self.band_full[name] += 1
                continue
            bands.append(name)
            if name in self.stats:
                s = self.stats[name]
                s["lower"][bucket(lo)] += 1
                s["cross_bucket"] += bucket(lo) != bucket(hi)
                s["cross_band"] += shipped_band(lo) != shipped_band(hi)
                s["speed"][event.replace("Rated ", "").split(" ")[0]] += 1
                s["gap"][min((hi - lo) // 100, 5)] += 1
        if not bands:
            self.no_band += 1
            return None
        return tuple(bands)

    def full(self) -> bool:
        return all(root.count >= SPECS[b][2] for b, root in self.tries.items())

    def read(self, lines, progress: bool = False) -> None:
        started, next_report = time.monotonic(), 500_000
        for bands, moves in self._games(lines):
            moves = moves[: self.ply_cap]
            first = self.games_read
            for band in bands:
                node = self.tries[band]
                node.count += 1
                for san in moves:
                    if node.kids is None:
                        node.kids = {}
                    child = node.kids.get(san)
                    if child is None:
                        child = node.kids[san] = _Node(first)
                    child.count += 1
                    node = child
                if self.tries[band].count == SPECS[band][2]:
                    self.filled[band] = {"games_read": self.games_read,
                                         "compressed_bytes": self.counter.bytes_read,
                                         "last_date": self.last_date,
                                         "seconds": round(time.monotonic() - started, 1)}
                    print(f"  band {band} full at {self.filled[band]}", file=sys.stderr)
            if progress and self.games_read >= next_report:
                next_report += 500_000
                kept = {b: r.count for b, r in self.tries.items()}
                print(f"  {self.games_read:,} read, {kept}, {time.monotonic() - started:.0f}s",
                      file=sys.stderr)


def count_nodes(root: _Node) -> int:
    n, todo = 0, [root]
    while todo:
        node = todo.pop()
        n += 1
        if node.kids:
            todo.extend(node.kids.values())
    return n


def rss_mb() -> float:
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) / 1024
    return 0.0


def peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def do_build(work: Path) -> None:
    work.mkdir(parents=True, exist_ok=True)
    book = load_book(build.DEFAULT_BOOK)
    url = DUMP_URL.format(month=MONTH)
    t0 = time.monotonic()
    rss0 = rss_mb()
    http = _Http(url)
    source = _Counting(io.BufferedReader(http))
    reader = zstandard.ZstdDecompressor().stream_reader(io.BufferedReader(source), read_across_frames=True)
    sample = MultiSample(source)
    with io.TextIOWrapper(reader, encoding="utf-8", errors="replace") as lines:
        sample.read(lines, progress=True)
    parse_s = time.monotonic() - t0
    nodes = {b: count_nodes(r) for b, r in sample.tries.items()}
    rss_parsed = rss_mb()
    print(f"parsed in {parse_s:.0f}s, rss {rss_parsed:.0f} MB, nodes {nodes}", file=sys.stderr)
    version = f"{MONTH}/{','.join(SPECS)}/{book.commit}/research"
    graphs, diags, build_s = {}, {}, {}
    for band in list(SPECS):
        root = sample.tries.pop(band)
        t = time.monotonic()
        graphs[band], diags[band] = _band_graph(root, book, STORAGE_CUTOFF, version, band)
        build_s[band] = round(time.monotonic() - t, 1)
        del root
        print(f"  band {band} built in {build_s[band]}s, rss {rss_mb():.0f} MB", file=sys.stderr)
    sizes = {}
    for band, g in graphs.items():
        data = json.dumps(Snapshot({"version": version}, {band: g}).to_json(), separators=(",", ":")).encode()
        sizes[band] = len(gzip.compress(data, mtime=0))
    meta = {"version": version, "month": MONTH, "storage_cutoff": STORAGE_CUTOFF, "ply_cap": PLY_CAP,
            "games_read": sample.games_read, "compressed_bytes_read": source.bytes_read,
            "dump_length": http.length, "stopped": sample.stopped, "dropped": dict(sample.dropped),
            "no_band": sample.no_band, "first_date": sample.first_date, "last_date": sample.last_date}
    write_graph_file(Snapshot(meta, graphs), work / "open-bands.graph.json.gz")
    stats = {
        "meta": meta, "filled": sample.filled, "band_full": dict(sample.band_full),
        "trie_nodes": nodes, "parse_seconds": round(parse_s, 1), "build_seconds": build_s,
        "rss_start_mb": round(rss0), "rss_after_parse_mb": round(rss_parsed), "peak_rss_mb": round(peak_mb()),
        "snapshot_gz_bytes": sizes, "diagnostics": diags,
        "composition": {b: {k: (dict(v) if isinstance(v, Counter) else v) for k, v in s.items()}
                        for b, s in sample.stats.items()},
    }
    (work / "stats.json").write_text(json.dumps(stats, indent=1, default=str))
    print(f"done, peak rss {peak_mb():.0f} MB", file=sys.stderr)


# The report


def side_repertoire(rep: Repertoire, side: str) -> dict:
    """What a learner on `side` walks: accepted moves at their turns, drawable at the opponent's."""
    kids: dict[str, list[str]] = {}
    todo, seen = [START], {START}
    while todo:
        epd = todo.pop()
        moves = rep.accepted(epd) if to_move(epd) == side else rep.drawable(epd)
        kids[epd] = [e.child_epd for e in moves if not rep.is_stub(e)]
        for c in kids[epd]:
            if c not in seen:
                seen.add(c)
                todo.append(c)
    depth: dict[str, int] = {}

    def d(epd: str) -> int:
        if epd not in depth:
            depth[epd] = max((d(c) + 1 for c in kids[epd]), default=0)
        return depth[epd]

    sys.setrecursionlimit(10_000)
    return {"positions": seen, "max_depth": d(START),
            "learner": sum(1 for p in seen if to_move(p) == side and kids[p])}


def shortest_depth(rep: Repertoire) -> dict[str, int]:
    depth, frontier = {START: 0}, [START]
    while frontier:
        nxt = []
        for epd in frontier:
            for e in rep.main_moves(epd):
                if not rep.is_stub(e) and e.child_epd not in depth:
                    depth[e.child_epd] = depth[epd] + 1
                    nxt.append(e.child_epd)
        frontier = nxt
    return depth


def line_of(g, epd: str) -> str:
    import chess
    board, out = chess.Board(), []
    for uci in g.positions[epd].canonical:
        move = chess.Move.from_uci(uci)
        if board.turn == chess.WHITE:
            out.append(f"{board.fullmove_number}.")
        out.append(board.san(move))
        board.push(move)
    return " ".join(out) or "(start)"


def mains(rep: Repertoire, epd: str) -> dict[str, float]:
    total = rep.graph.positions[epd].count
    return {e.san: e.count / total for e in rep.main_moves(epd)}


def fmt_mains(m: dict[str, float]) -> str:
    return ", ".join(f"{s} {v:.0%}" for s, v in m.items()) or "-"


def jac(a: set, b: set) -> str:
    return f"{len(a & b)} shared, {len(a - b)} / {len(b - a)} only-left / only-right, J = {len(a & b) / len(a | b):.2f}"


def compare(reps, left: str, right: str, max_ply: int, min_share: float = 0.01) -> tuple[list[str], dict]:
    """Positions of `left`'s repertoire at shortest depth <= max_ply also in `right`'s whose main-move
    set or top main move differs. Rows only for positions reached by >= min_share of `left`'s games;
    the summary counts every shared position, and the traffic-weighted share of differing ones."""
    a, b = reps[left], reps[right]
    games = a.graph.games
    da = shortest_depth(a)
    rows = []
    n = {"shared": 0, "set_differs": 0, "top_differs": 0, "shared_1pct": 0, "set_differs_1pct": 0,
         "top_differs_1pct": 0}
    w_all = w_set = w_top = 0
    for epd, depth in sorted(da.items(), key=lambda kv: (kv[1], -a.graph.positions[kv[0]].count)):
        if depth > max_ply or epd not in b.positions:
            continue
        count = a.graph.positions[epd].count
        big = count >= min_share * games
        ma, mb = mains(a, epd), mains(b, epd)
        set_diff = set(ma) != set(mb)
        top_diff = next(iter(ma), None) != next(iter(mb), None)
        n["shared"] += 1
        n["shared_1pct"] += big
        n["set_differs"] += set_diff
        n["top_differs"] += top_diff
        n["set_differs_1pct"] += big and set_diff
        n["top_differs_1pct"] += big and top_diff
        w_all += count
        w_set += count * set_diff
        w_top += count * top_diff
        if big and (set_diff or top_diff):
            rows.append(f"| {depth} | `{line_of(a.graph, epd)}` | {count / games:.1%} | {fmt_mains(ma)} |"
                        f" {fmt_mains(mb)} | {'yes' if top_diff else ''} |")
    n["only_left"] = sum(1 for e, d in da.items() if d <= max_ply and e not in b.positions)
    n["only_right"] = sum(1 for e, d in shortest_depth(b).items() if d <= max_ply and e not in a.positions)
    n["traffic_set_differs"] = round(w_set / w_all, 3)
    n["traffic_top_differs"] = round(w_top / w_all, 3)
    return rows, n


def do_report(work: Path) -> None:
    stats = json.loads((work / "stats.json").read_text())
    path = work / "open-bands.graph.json.gz"
    bands = list(SPECS)
    graphs = {b: load_graph(path, b) for b in bands}
    reps = {b: Repertoire(g, Settings(band=b)) for b, g in graphs.items()}
    print("```json")
    print(json.dumps({k: v for k, v in stats.items() if k not in ("diagnostics", "composition")}, indent=1))
    print("```\n")
    print("## Composition\n")
    for b, s in stats["composition"].items():
        n = sum(s["lower"].values())
        print(f"{b}: n={n}, lower buckets " + ", ".join(
            f"{k}: {v / n:.1%}" for k, v in sorted(s["lower"].items(), key=lambda kv: int(kv[0]))),
            f"| cross-bucket {s['cross_bucket'] / n:.1%} | cross shipped band {s['cross_band'] / n:.1%}",
            "| speed " + ", ".join(f"{k} {v / n:.1%}" for k, v in sorted(s["speed"].items())),
            "| gap/100 " + ", ".join(f"{k}: {v / n:.1%}" for k, v in sorted(s["gap"].items())))
    print("\n## Sizes\n")
    print("| band | games | stored positions | stored edges | gz bytes | rep positions | rep max depth |"
          " White positions | White learner pos | White depth | Black positions | Black learner pos | Black depth |")
    sides = {}
    for b in bands:
        d = stats["diagnostics"][b]
        w, k = side_repertoire(reps[b], "white"), side_repertoire(reps[b], "black")
        sides[b] = (w, k)
        r = d["repertoire"]
        print(f"| {b} | {d['games']:,} | {d['positions']:,} | {d['edges']:,} | {stats['snapshot_gz_bytes'][b]:,} |"
              f" {r['positions']:,} | {r['max_depth']} | {len(w['positions']):,} | {w['learner']:,} | {w['max_depth']} |"
              f" {len(k['positions']):,} | {k['learner']:,} | {k['max_depth']} |")
    print("\n## Overlap of repertoire positions\n")
    pairs = [("1500+", "1500-1800"), ("1500+", "1800-2100"), ("1500-1800", "1800-2100"),
             ("1200+", "1500+"), ("1500+", "1800+"), ("1800+", "1800-2100"),
             ("1500+", "1500+@300k"), ("1500+", "1500+#2"), ("1500+@300k", "1500+#2")]
    for x, y in pairs:
        print(f"- {x} vs {y}: all {jac(set(reps[x].positions), set(reps[y].positions))};"
              f" White {jac(sides[x][0]['positions'], sides[y][0]['positions'])};"
              f" Black {jac(sides[x][1]['positions'], sides[y][1]['positions'])}")
    for x, y in [("1500+", "1500-1800"), ("1500+", "1800-2100"), ("1500-1800", "1800-2100"),
                 ("1500+", "1500+@300k"), ("1500+", "1500+#2")]:
        for ply in (8, 36):
            rows, summary = compare(reps, x, y, ply)
            print(f"\n### main moves {x} vs {y}, positions at shortest depth <= {ply} (in {x}): {summary}\n")
            if ply == 8:
                print(f"| ply | line | games reaching (in {x}) | {x} main moves (share) | {y} main moves (share) | top move differs |")
                print("|---|---|---|---|---|---|")
                print("\n".join(rows))


if __name__ == "__main__":
    command, work = sys.argv[1], Path(sys.argv[2])
    do_build(work) if command == "build" else do_report(work)
