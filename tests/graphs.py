"""Small in-memory graphs for tests, written as SAN lines from the start position."""

import chess

from chessop.graph import DEFAULT_BAND, Edge, Graph, Position


def board_after(*sans: str) -> chess.Board:
    board = chess.Board()
    for san in sans:
        board.push_san(san)
    return board


def epd_after(*sans: str) -> str:
    return board_after(*sans).epd()


def graph_of(
    counts: dict[str, int],
    names: dict[str, str] | None = None,
    *,
    games: int = 10_000,
    unstored: frozenset[str] = frozenset(),
    position_counts: dict[str, int] | None = None,
) -> Graph:
    """A graph whose edges are the last moves of the lines in `counts` ({"e4 c5": 2400, ...}).

    Lines are space-separated SAN from the start position, "" being the start itself. A
    position's count is the count of the edge into it (`games` at the start) unless
    `position_counts` says otherwise; the lines in `unstored` end on a position the graph
    does not store. A position two lines reach takes the first line's count, either's name and
    the first line as its canonical order.
    """
    named = {epd_after(*line.split()): name for line, name in (names or {}).items()}
    pooled = {"": games, **counts, **(position_counts or {})}
    edges: dict[str, list[Edge]] = {}
    for line, count in counts.items():
        *before, san = line.split()
        parent = board_after(*before)
        uci = parent.parse_san(san).uci()
        edges.setdefault(parent.epd(), []).append(
            Edge(parent.epd(), uci, san, count, epd_after(*before, san))
        )
    positions = {}
    for line in ("", *counts):
        if line in unstored:
            continue
        epd = epd_after(*line.split())
        if epd in positions:
            continue
        positions[epd] = Position(
            epd=epd,
            count=pooled[line],
            name=named.get(epd),
            eco=None,
            canonical=tuple(m.uci() for m in board_after(*line.split()).move_stack),
            book_line=None,
            edges=tuple(edges.get(epd, ())),
        )
    return Graph(version="test", band=DEFAULT_BAND, games=games, positions=positions)
