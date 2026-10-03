"""`chessop build-snapshot`: the graph file from a capped prefix of one Lichess dump month, and
the explanation file beside it (`chessop.wikibooks`).

Spec §3.1-3.3, ADR 0003 (with its ticket 22 amendment) and ADR 0006; the reference procedure is
the method section of `docs/research/pooled-repertoire.md`. The dump is streamed through a
zstandard decompressor; a game passing the filters goes into the move-sequence trie of every band
both players fall in (ADR 0003, chessop-public ticket 02 amendment), to the ply cap, until every
band holds its cap of games or the month ends. Per band the trie is then keyed by `Board.epd()`,
pooled by position, cut at the storage cut-off and made acyclic.

Imported only when `build-snapshot` runs: `zstandard` is in the `chessop[build]` extra.
"""

import argparse
import gzip
import hashlib
import io
import json
import re
import sys
import time
import urllib.request
from collections import Counter, deque
from collections.abc import Buffer, Iterable, Iterator
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import BinaryIO

import chess
import zstandard

from chessop import wikibooks
from chessop.explanations import explanations_path
from chessop.graph import BANDS, STORAGE_CUTOFF, Edge, Graph, Position
from chessop.repertoire import START, Repertoire, Settings

BUILD_REVISION = 1  # bump when the procedure changes what a build writes
PLY_CAP = 36
GAMES_PER_BAND = 150_000
DUMP_URL = "https://database.lichess.org/standard/lichess_db_standard_rated_{month}.pgn.zst"
DEFAULT_BOOK = Path(__file__).resolve().parents[2] / "refs" / "lichess"

HEADER = re.compile(r'^\[(\w+)\s+"(.*)"\]$')
COMMENT = re.compile(r"\{[^}]*\}")
MOVE_NUMBER = re.compile(r"^\d+\.+")
RESULTS = frozenset({"1-0", "0-1", "1/2-1/2", "*"})


# The book


@dataclass(frozen=True)
class BookLine:
    eco: str
    name: str
    uci: tuple[str, ...]


@dataclass(frozen=True)
class Book:
    """The named lines of the `chess-openings` TSV files, by the EPD each line ends on."""

    lines: dict[str, BookLine]
    commit: str


def load_book(directory: Path) -> Book:
    """Every `*.tsv` of `directory` (`eco`, `name`, `pgn` columns, more ignored).

    The commit is the `COMMIT` file's content when there is one, else a hash of the files.
    """
    files = sorted(directory.glob("*.tsv"))
    if not files:
        raise FileNotFoundError(f"no book TSV files in {directory}")
    lines: dict[str, BookLine] = {}
    digest = hashlib.sha256()
    for path in files:
        text = path.read_text(encoding="utf-8")
        digest.update(text.encode())
        rows = text.splitlines()
        columns = rows[0].split("\t")
        eco_at, name_at, pgn_at = (columns.index(c) for c in ("eco", "name", "pgn"))
        for row in rows[1:]:
            if not row:
                continue
            cells = row.split("\t")
            board = chess.Board()
            for san in _san_tokens(cells[pgn_at]):
                board.push_san(san)
            line = BookLine(cells[eco_at], cells[name_at], tuple(m.uci() for m in board.move_stack))
            lines.setdefault(board.epd(), line)
    commit_file = directory / "COMMIT"
    if commit_file.exists():
        commit = commit_file.read_text().strip()
    else:
        commit = "sha256-" + digest.hexdigest()[:12]
    return Book(lines, commit)


# Reading the dump


class _Node:
    """One move sequence of a band's trie; `first` is the number of the game that created it."""

    __slots__ = ("count", "first", "kids", "pooled")

    def __init__(self, first: int) -> None:
        self.count = 0
        self.first = first
        self.kids: dict[str, _Node] | None = None
        self.pooled: _Pooled | None = None


@dataclass
class _Sample:
    """The games read from the dump, per band a trie of the kept ones."""

    cap: int
    ply_cap: int
    max_games: int | None
    tries: dict[str, _Node] = field(default_factory=lambda: {b: _Node(0) for b, _, _ in BANDS})
    games_read: int = 0
    dropped: Counter[str] = field(default_factory=Counter)
    band_full: Counter[str] = field(default_factory=Counter)
    stopped: str = "end of the month"

    def bands_of(self, headers: dict[str, str]) -> list[str]:
        """The bands the game is kept in, none with the reason counted.

        A game goes into every band both players are in that is not yet full."""
        white, black = headers.get("WhiteElo", ""), headers.get("BlackElo", "")
        if not (white.isdigit() and black.isdigit()):
            self.dropped["rating missing"] += 1
            return []
        if "BOT" in (headers.get("WhiteTitle"), headers.get("BlackTitle")):
            self.dropped["BOT title"] += 1
            return []
        if "Bullet" in headers.get("Event", ""):  # UltraBullet included
            self.dropped["bullet or ultrabullet"] += 1
            return []
        names = _bands(int(white), int(black))
        if not names:
            self.dropped["players share no band"] += 1
        kept = []
        for name in names:
            if self.tries[name].count >= self.cap:
                self.band_full[name] += 1
            else:
                kept.append(name)
        return kept

    def full(self) -> bool:
        return all(root.count >= self.cap for root in self.tries.values())

    def read(self, lines: Iterable[str], progress: bool = False) -> None:
        started, next_report = time.monotonic(), 200_000
        for bands, moves in self._games(lines):
            first = self.games_read
            for band in bands:
                node = self.tries[band]
                node.count += 1
                for san in moves[: self.ply_cap]:
                    if node.kids is None:
                        node.kids = {}
                    child = node.kids.get(san)
                    if child is None:
                        child = node.kids[san] = _Node(first)
                    child.count += 1
                    node = child
            if progress and self.games_read >= next_report:
                next_report += 200_000
                kept = {b: root.count for b, root in self.tries.items()}
                elapsed = time.monotonic() - started
                print(
                    f"  {self.games_read:,} games read, kept {kept}, {elapsed:.0f}s",
                    file=sys.stderr,
                )

    def _games(self, lines: Iterable[str]) -> Iterator[tuple[list[str], list[str]]]:
        """(bands, SAN moves) of every kept game; the movetext of other games is never split."""
        headers: dict[str, str] = {}
        bands: list[str] = []
        moves: list[str] = []
        in_moves = False
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            if line[0] == "[":
                if in_moves:
                    if bands:
                        yield bands, moves
                    headers, bands, moves, in_moves = {}, [], [], False
                if match := HEADER.match(line):
                    headers[match.group(1)] = match.group(2)
                continue
            if not in_moves:
                if self.full():
                    self.stopped = "every band full"
                    return
                if self.max_games is not None and self.games_read >= self.max_games:
                    self.stopped = "max games read"
                    return
                in_moves = True
                self.games_read += 1
                bands = self.bands_of(headers)
            if bands and len(moves) < self.ply_cap:
                moves.extend(_san_tokens(line))
        if in_moves and bands:
            yield bands, moves
        if self.full():
            self.stopped = "every band full"


def _bands(white: int, black: int) -> list[str]:
    """Every band both ratings fall in, lower bounds inclusive."""
    low_player, high_player = sorted((white, black))
    return [name for name, low, high in BANDS if low <= low_player and high_player < high]


def _san_tokens(movetext: str) -> list[str]:
    """The SAN moves of a line of movetext: comments, numbers, NAGs, results and !? dropped."""
    tokens = []
    for token in COMMENT.sub(" ", movetext).split():
        token = MOVE_NUMBER.sub("", token).rstrip("!?")
        if token and token not in RESULTS and not token.startswith("$"):
            tokens.append(token)
    return tokens


class _Reader(io.RawIOBase):
    """A raw stream handing out whatever `_read` returns."""

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: Buffer) -> int:
        view = memoryview(buffer).cast("B")
        data = self._read(len(view))
        view[: len(data)] = data
        return len(data)

    def _read(self, size: int) -> bytes:
        raise NotImplementedError


class _Counting(_Reader):
    """The dump, counting the compressed bytes handed out."""

    def __init__(self, source: BinaryIO) -> None:
        self.source = source
        self.bytes_read = 0

    def _read(self, size: int) -> bytes:
        data = self.source.read(size)
        self.bytes_read += len(data)
        return data


class _Http(_Reader):
    """The dump over HTTP, reconnecting at the current offset if the connection drops."""

    RETRIES = 20

    def __init__(self, url: str) -> None:
        self.url = url
        self.offset = 0
        self.length: int | None = None
        self.response = self._open()

    def _open(self):
        request = urllib.request.Request(self.url, headers={"User-Agent": "chessop build-snapshot"})
        if self.offset:
            request.add_header("Range", f"bytes={self.offset}-")
        response = urllib.request.urlopen(request, timeout=120)
        if self.length is None:
            self.length = int(response.headers.get("Content-Length") or 0)
        elif response.status != 206:
            raise RuntimeError(f"the server ignored the Range header (status {response.status})")
        return response

    def _read(self, size: int) -> bytes:
        for attempt in range(self.RETRIES):
            try:
                data = self.response.read(size)
                if data:
                    self.offset += len(data)
                    return data
                if not self.length or self.offset >= self.length:
                    return b""
            except OSError as e:
                print(f"stream error at byte {self.offset}: {e}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
            try:
                self.response = self._open()
            except OSError as e:
                print(f"reconnecting at byte {self.offset} failed: {e}", file=sys.stderr)
        raise RuntimeError(f"gave up reconnecting at byte {self.offset}")


# One band's graph


class _Pooled:
    """One position over every move order into it; `best` is its most popular trie node."""

    __slots__ = ("best", "count", "epd", "largest", "stored")

    def __init__(self, epd: str, node: _Node) -> None:
        self.epd = epd
        self.count = 0
        self.largest = 0
        self.best = node
        self.stored = False


@dataclass
class _PooledEdge:
    san: str
    child: str
    count: int = 0
    largest: int = 0


def _band_graph(
    root: _Node, book: Book, cutoff: float, version: str, band: str
) -> tuple[Graph, dict[str, object]]:
    games = root.count
    threshold = cutoff * games
    pooled: dict[str, _Pooled] = {}
    rejected = 0

    def pool(node: _Node, epd: str) -> None:
        position = pooled.get(epd)
        if position is None:
            position = pooled[epd] = _Pooled(epd, node)
        position.count += node.count
        best = position.best
        if node.count > best.count or (node.count == best.count and node.first < best.first):
            position.best = node
        position.largest = max(position.largest, node.count)
        node.pooled = position

    def key(node: _Node, board: chess.Board) -> None:  # recursion depth is the ply cap
        nonlocal rejected
        kids = node.kids or {}
        for san, child in list(kids.items()):
            try:
                board.push_san(san)
            except ValueError:
                rejected += child.count
                del kids[san]
                continue
            pool(child, board.epd())
            key(child, board)
            board.pop()

    board = chess.Board()
    pool(root, board.epd())
    key(root, board)
    for position in pooled.values():
        position.stored = position.count >= threshold

    edges: dict[tuple[str, str], _PooledEdge] = {}
    canonical_san: dict[str, tuple[str, ...]] = {}
    if root.pooled is not None and root.pooled.best is root:
        canonical_san[root.pooled.epd] = ()

    def collect(node: _Node, path: list[str]) -> None:
        parent = node.pooled
        assert parent is not None
        for san, child in (node.kids or {}).items():
            position = child.pooled
            assert position is not None
            path.append(san)
            if parent.stored and position.stored:
                edge = edges.get((parent.epd, san))
                if edge is None:
                    edge = edges[(parent.epd, san)] = _PooledEdge(san, position.epd)
                edge.count += child.count
                edge.largest = max(edge.largest, child.count)
            if position.stored and position.best is child:
                canonical_san[position.epd] = tuple(path)
            collect(child, path)
            path.pop()

    collect(root, [])
    stored = {epd: p for epd, p in pooled.items() if p.stored}
    out: dict[str, list[tuple[str, _PooledEdge]]] = {}
    for (epd, _), edge in edges.items():
        if edge.count >= threshold:
            out.setdefault(epd, []).append((epd, edge))
    for epd_edges in out.values():
        epd_edges.sort(key=lambda pe: (-pe[1].count, pe[1].san))
    kept, dropped_cycles = _acyclic(out, START)

    edges_by_parent: dict[str, list[Edge]] = {}
    for epd, edge in kept:
        uci = chess.Board(f"{epd} 0 1").parse_san(edge.san).uci()
        edges_by_parent.setdefault(epd, []).append(Edge(epd, uci, edge.san, edge.count, edge.child))
    positions = {}
    for epd, p in sorted(stored.items(), key=lambda item: -item[1].count):
        line = book.lines.get(epd)
        positions[epd] = Position(
            epd=epd,
            count=p.count,
            name=line.name if line else None,
            eco=line.eco if line else None,
            canonical=_uci_line(canonical_san[epd]),
            book_line=line.uci if line else None,
            edges=tuple(edges_by_parent.get(epd, ())),
        )
    graph = Graph(version=version, band=band, games=games, positions=positions)
    diagnostics: dict[str, object] = {
        "games": games,
        "dropped_rejected_san": rejected,
        "positions": len(positions),
        "edges": len(kept),
        "dropped_cycle_edges": dropped_cycles,
        "diffuse_positions": sum(p.largest < threshold for p in stored.values()),
        "diffuse_edges": sum(edge.largest < threshold for _, edge in kept),
        "repertoire": repertoire_size(graph),
    }
    return graph, diagnostics


def _uci_line(sans: tuple[str, ...]) -> tuple[str, ...]:
    board = chess.Board()
    return tuple(board.push_san(san).uci() for san in sans)


def _acyclic(
    out: dict[str, list[tuple[str, _PooledEdge]]], start: str
) -> tuple[list[tuple[str, _PooledEdge]], int]:
    """The edges added in BFS order from `start`, each dropped when it closes a cycle.

    Edges of positions the start does not reach come after, most popular position first.
    """
    order, seen, todo = [], {start}, deque([start])
    while todo:
        epd = todo.popleft()
        order.append(epd)
        for _, edge in out.get(epd, ()):
            if edge.child not in seen:
                seen.add(edge.child)
                todo.append(edge.child)
    rest = sorted(
        (epd for epd in out if epd not in seen), key=lambda epd: -max(e.count for _, e in out[epd])
    )
    children: dict[str, list[str]] = {}
    kept, dropped = [], 0
    for epd in order + rest:
        for parent, edge in out.get(epd, ()):
            if _reaches(children, edge.child, parent):
                dropped += 1
                continue
            children.setdefault(parent, []).append(edge.child)
            kept.append((parent, edge))
    return kept, dropped


def _reaches(children: dict[str, list[str]], source: str, target: str) -> bool:
    seen, todo = {source}, [source]
    while todo:
        epd = todo.pop()
        if epd == target:
            return True
        for child in children.get(epd, ()):
            if child not in seen:
                seen.add(child)
                todo.append(child)
    return False


def repertoire_size(graph: Graph) -> dict[str, int]:
    """The size of the repertoire at the default settings (spec §4), for the diagnostics."""
    repertoire = Repertoire(graph, Settings(band=graph.band))
    kids = {
        epd: [e.child_epd for e in repertoire.main_moves(epd) if not repertoire.is_stub(e)]
        for epd in repertoire.positions
    }
    branches: dict[str, int] = {}
    depth: dict[str, int] = {}

    def walk(epd: str) -> None:  # the graph is a DAG, its depth bounded by the ply cap
        if epd in branches:
            return
        for child in kids[epd]:
            walk(child)
        branches[epd] = sum(branches[c] for c in kids[epd]) or 1
        depth[epd] = max((depth[c] + 1 for c in kids[epd]), default=0)

    if START in repertoire.positions:
        walk(START)
    return {
        "positions": len(repertoire.positions),
        "edges": sum(len(k) for k in kids.values()),
        "branches": branches.get(START, 0),
        "leaves": sum(not k for k in kids.values()),
        "max_depth": depth.get(START, 0),
        "book_lines_covered": sum(graph.positions[epd].name is not None for epd in kids),
    }


# The snapshot


@dataclass(frozen=True)
class Snapshot:
    meta: dict[str, object]
    graphs: dict[str, Graph]

    def to_json(self) -> dict[str, object]:
        """The graph file's document, in the layout `chessop.graph` reads."""
        return {
            "meta": self.meta,
            "bands": {
                band: {
                    "games": graph.games,
                    "positions": [
                        {
                            "epd": p.epd,
                            "count": p.count,
                            "name": p.name,
                            "eco": p.eco,
                            "canonical": list(p.canonical),
                            "book_line": list(p.book_line) if p.book_line is not None else None,
                        }
                        for p in graph.positions.values()
                    ],
                    "edges": [
                        {
                            "epd": e.epd,
                            "uci": e.uci,
                            "san": e.san,
                            "count": e.count,
                            "child_epd": e.child_epd,
                        }
                        for p in graph.positions.values()
                        for e in p.edges
                    ],
                }
                for band, graph in self.graphs.items()
            },
        }


def build_snapshot(
    dump: BinaryIO,
    *,
    month: str,
    book: Book,
    cap: int = GAMES_PER_BAND,
    cutoff: float = STORAGE_CUTOFF,
    ply_cap: int = PLY_CAP,
    max_games: int | None = None,
    progress: bool = False,
) -> Snapshot:
    """Every band's graph from the `.pgn.zst` stream `dump`, with the metadata of spec §3.3."""
    source = _Counting(dump)
    reader = zstandard.ZstdDecompressor().stream_reader(
        io.BufferedReader(source), read_across_frames=True
    )
    sample = _Sample(cap=cap, ply_cap=ply_cap, max_games=max_games)
    with io.TextIOWrapper(reader, encoding="utf-8", errors="replace") as lines:
        sample.read(lines, progress)
    bands = [name for name, _, _ in BANDS]
    version = f"{month}/{','.join(bands)}/{book.commit}/{BUILD_REVISION}"
    graphs: dict[str, Graph] = {}
    diagnostics: dict[str, dict[str, object]] = {}
    for band in bands:
        root = sample.tries.pop(band)  # each trie is freed once its band is built
        graphs[band], diagnostics[band] = _band_graph(root, book, cutoff, version, band)
        diagnostics[band]["dropped_band_full"] = sample.band_full[band]
        if progress:
            print(f"  band {band} built", file=sys.stderr)
    meta: dict[str, object] = {
        "version": version,
        "month": month,
        "bands": bands,
        "book_commit": book.commit,
        "build_revision": BUILD_REVISION,
        "storage_cutoff": cutoff,
        "ply_cap": ply_cap,
        "games_per_band": cap,
        "games_read": sample.games_read,
        "compressed_bytes_read": source.bytes_read,
        "stopped": sample.stopped,
        "dropped": dict(sample.dropped),
        "band_diagnostics": diagnostics,
    }
    return Snapshot(meta, graphs)


def write_graph_file(snapshot: Snapshot, path: Path) -> None:
    data = json.dumps(snapshot.to_json(), separators=(",", ":")).encode()
    path.write_bytes(gzip.compress(data, mtime=0))


def report(snapshot: Snapshot) -> str:
    """The diagnostics of spec §3.2 step 5, for the developer to check against spec §4's sizes."""
    meta = snapshot.meta
    out = [
        f"snapshot {meta['version']}",
        f"games read {meta['games_read']:,}, {meta['compressed_bytes_read']:,} compressed bytes"
        f" (stopped: {meta['stopped']})",
        "dropped by the filters: "
        + (", ".join(f"{k} {v:,}" for k, v in meta["dropped"].items()) or "none"),  # ty: ignore[unresolved-attribute]
    ]
    for band, d in meta["band_diagnostics"].items():  # ty: ignore[unresolved-attribute]
        r = d["repertoire"]
        out += [
            f"band {band}: {d['games']:,} games kept, {d['dropped_band_full']:,} dropped as the"
            f" band was full, {d['dropped_rejected_san']:,} cut at a rejected SAN",
            f"  stored {d['positions']:,} positions, {d['edges']:,} edges;"
            f" {d['dropped_cycle_edges']:,} edges dropped closing a cycle;"
            f" diffuse {d['diffuse_positions']:,} positions, {d['diffuse_edges']:,} edges",
            f"  repertoire at the defaults: {r['positions']:,} positions, {r['edges']:,} edges,"
            f" {r['branches']:,} branches, {r['leaves']:,} leaves, {r['max_depth']} plies deep,"
            f" {r['book_lines_covered']:,} book lines covered",
        ]
    return "\n".join(out)


def user_agent(contact: str | None) -> str:
    """`chessop/<version> (<contact>) Python-urllib/<v>`, as the Wikimedia policy asks."""
    meta = metadata.metadata("chessop")
    contact = contact or meta.get("Author-email")
    if not contact:
        raise SystemExit("chessop: pass --contact, Wikibooks refuses a User-Agent without one")
    python = ".".join(map(str, sys.version_info[:2]))
    return f"chessop/{meta['Version']} ({contact}) Python-urllib/{python}"


def main(args: argparse.Namespace) -> None:
    dump_arg = args.dump or DUMP_URL.format(month=args.month)
    book = load_book(args.book or DEFAULT_BOOK)
    out = args.out or Path(f"chessop-{args.month}.graph.json.gz")
    print(f"build-snapshot: reading {dump_arg}", file=sys.stderr)
    remote = re.match(r"https?://", dump_arg)
    with io.BufferedReader(_Http(dump_arg)) if remote else open(dump_arg, "rb") as dump:
        snapshot = build_snapshot(
            dump, month=args.month, book=book, max_games=args.max_games, progress=True
        )
    write_graph_file(snapshot, out)
    print(report(snapshot))
    print(f"wrote {out}")
    if args.wikitext is not None:
        source: wikibooks.Source = wikibooks.SavedPages.read(args.wikitext)
    else:
        source = wikibooks.WikibooksApi(user_agent(args.contact))
    version = str(snapshot.meta["version"])
    explanations = wikibooks.build_explanations(snapshot.graphs, version, source, progress=True)
    explanations_out = explanations_path(out)
    wikibooks.write_explanation_file(explanations, explanations_out)
    print(
        f"explanations: {len(explanations.pages):,} pages for"
        f" {len(explanations.positions):,} positions"
    )
    print(f"wrote {explanations_out}")
