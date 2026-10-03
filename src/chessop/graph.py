"""The graph file: one band's positions and edges, loaded into memory at start.

On disk the graph file is JSON, gzip-compressed or not (detected from the first bytes):

    {"meta": {"version": "...", "bands": [...], ...},
     "bands": {"<band>": {"games": N,
                          "positions": [{epd, count, name, eco, canonical, book_line}, ...],
                          "edges": [{epd, uci, san, count, child_epd}, ...]}}}

Positions are keyed by `chess.Board.epd()`. Only exact names are stored.
"""

import gzip
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

PACKAGED_SNAPSHOT = Path(__file__).parent / "data" / "snapshot.graph.json.gz"  # the release build
FIXTURE_SNAPSHOT = Path(__file__).parent / "data" / "fixture.graph.json"  # a hand-made one, tests
DEFAULT_BAND = "1500+"
STORAGE_CUTOFF = 0.0002  # a share of the band's games
# A game is in a band when both players' ratings are; a game is in every band both players are in.
BANDS: tuple[tuple[str, int, int], ...] = (  # name, lowest rating in, lowest rating out
    # The five bands of the first snapshots: four closed, then 2100+, which has no upper bound.
    ("0-1200", 0, 1200),
    ("1200-1500", 1200, 1500),
    ("1500-1800", 1500, 1800),
    ("1800-2100", 1800, 2100),
    ("2100+", 2100, sys.maxsize),
    # The open bands: every player at or above the bound.
    ("1200+", 1200, sys.maxsize),
    ("1500+", 1500, sys.maxsize),
    ("1800+", 1800, sys.maxsize),
)


@dataclass(frozen=True)
class Edge:
    epd: str
    uci: str
    san: str
    count: int
    child_epd: str


@dataclass(frozen=True)
class Position:
    epd: str
    count: int
    name: str | None
    eco: str | None
    canonical: tuple[str, ...]
    book_line: tuple[str, ...] | None
    edges: tuple[Edge, ...] = field(default=())


@dataclass(frozen=True)
class Graph:
    """Every stored position and edge of one band; the repertoire rule narrows it at load."""

    version: str
    band: str
    games: int
    positions: dict[str, Position]
    storage_cutoff: float = STORAGE_CUTOFF  # the least popularity floor the snapshot allows
    bands: tuple[str, ...] = ()  # every band the snapshot holds, this one included


def load_graph(path: Path, band: str = DEFAULT_BAND) -> Graph:
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    doc = json.loads(raw)
    data = doc["bands"][band]
    edges_by_epd: dict[str, list[Edge]] = {}
    for e in data["edges"]:
        edge = Edge(e["epd"], e["uci"], e["san"], e["count"], e["child_epd"])
        edges_by_epd.setdefault(edge.epd, []).append(edge)
    positions = {}
    for p in data["positions"]:
        edges = edges_by_epd.get(p["epd"], [])
        book_line = p.get("book_line")
        positions[p["epd"]] = Position(
            epd=p["epd"],
            count=p["count"],
            name=p.get("name"),
            eco=p.get("eco"),
            canonical=tuple(p.get("canonical", ())),
            book_line=tuple(book_line) if book_line is not None else None,
            edges=tuple(edges),
        )
    meta = doc["meta"]
    return Graph(
        version=meta["version"],
        band=band,
        games=data["games"],
        positions=positions,
        storage_cutoff=meta.get("storage_cutoff", STORAGE_CUTOFF),
        bands=tuple(doc["bands"]),
    )
