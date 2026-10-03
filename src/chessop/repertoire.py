"""The repertoire at load (spec §4): the part of the graph the rounds are drilled over.

At every position the **main moves** are, among the edges whose pooled count clears the popularity
floor, the top `max(P, O)` by count plus every edge holding at least the share of the position's
pooled count. Opting a family out removes the positions whose exact name is in it; then only what
the start reaches over main moves is kept; the two repeat until stable. There is no named-position
prune (ADR 0005, ticket 24 amendment): a branch runs until no move at its end clears the
popularity floor, so a leaf need not be named. A main move onto a position that is not kept is a
**stub**: the learner may play it, the opponent never draws it. A **leaf** is a kept position with
no kept main move.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Literal

import chess

from chessop.graph import DEFAULT_BAND, Edge, Graph, Position

Side = Literal["white", "black"]

START = chess.Board().epd()


@dataclass(frozen=True)
class Settings:
    """The settings the repertoire is built from; in-memory defaults until settings persist."""

    band: str = DEFAULT_BAND
    width_player: int = 2
    width_opponent: int = 3
    popularity_floor: float = 0.0002  # a share of the band's games
    share: float = 0.05  # of the pooled games reaching the position
    opted_out: frozenset[str] = field(default=frozenset())  # opening families


def family(name: str) -> str:
    """The opening a book name belongs to: "Sicilian Defense: Najdorf" is the Sicilian Defense."""
    return name.split(":", 1)[0]


def to_move(epd: str) -> Side:
    return "white" if epd.split()[1] == "w" else "black"


class Repertoire:
    def __init__(self, graph: Graph, settings: Settings) -> None:
        self.graph = graph
        self.settings = settings
        k = max(settings.width_player, settings.width_opponent)
        popularity_floor = settings.popularity_floor * graph.games
        self._main: dict[str, tuple[Edge, ...]] = {}
        self._share: dict[str, frozenset[Edge]] = {}
        for epd, position in graph.positions.items():
            ranked = sorted(
                (e for e in position.edges if e.count >= popularity_floor),
                key=lambda e: (e.count, e.san),
                reverse=True,
            )
            share = frozenset(e for e in ranked if e.count >= settings.share * position.count)
            self._main[epd] = tuple(e for i, e in enumerate(ranked) if i < k or e in share)
            self._share[epd] = share
        self.positions: frozenset[str] = _scope(graph, self._main, settings.opted_out)
        # Where the learner holding the side to move is drilled: every kept position but the leaves.
        self.learner_positions: frozenset[str] = frozenset(
            epd for epd in self.positions if not self.is_leaf(epd)
        )
        # Each learner position with its pooled count and colour, the weights of the aggregates.
        self.learner_counts: tuple[tuple[str, int, Side], ...] = tuple(
            (epd, graph.positions[epd].count, to_move(epd)) for epd in self.learner_positions
        )

    def position(self, epd: str) -> Position | None:
        """The kept position at `epd`, None when it is unreachable, opted out or never stored."""
        return self.graph.positions[epd] if epd in self.positions else None

    def main_moves(self, epd: str) -> tuple[Edge, ...]:
        """The position's main moves, stubs included, by count then SAN descending."""
        return self._main[epd]

    def is_stub(self, edge: Edge) -> bool:
        return edge.child_epd not in self.positions

    def accepted(self, epd: str) -> tuple[Edge, ...]:
        """The learner's accepted set: the top-P main moves plus the share moves, stubs included."""
        return self._widest(epd, self.settings.width_player)

    def drawable(self, epd: str) -> tuple[Edge, ...]:
        """The opponent's drawable set: the top-O main moves plus the share moves, minus stubs."""
        return tuple(
            e for e in self._widest(epd, self.settings.width_opponent) if not self.is_stub(e)
        )

    def is_leaf(self, epd: str) -> bool:
        return all(self.is_stub(e) for e in self._main[epd])

    def is_learner_position(self, epd: str, side: Side) -> bool:
        """A kept position the learner is to move at that is not a leaf: one that is drilled."""
        return epd in self.positions and to_move(epd) == side and not self.is_leaf(epd)

    def _widest(self, epd: str, width: int) -> tuple[Edge, ...]:
        share = self._share[epd]
        return tuple(e for i, e in enumerate(self._main[epd]) if i < width or e in share)


def _scope(
    graph: Graph, main: dict[str, tuple[Edge, ...]], opted_out: frozenset[str]
) -> frozenset[str]:
    """The kept positions: opt-out, then reachability from the start, repeated until stable."""
    kept = frozenset(graph.positions)
    while True:
        scoped = frozenset(
            epd
            for epd in kept
            if (name := graph.positions[epd].name) is None or family(name) not in opted_out
        )
        reached = _reachable(main, scoped)
        if reached == kept:
            return kept
        kept = reached


def _children(main: dict[str, tuple[Edge, ...]], kept: frozenset[str], epd: str) -> Iterator[str]:
    return (e.child_epd for e in main[epd] if e.child_epd in kept)


def _reachable(main: dict[str, tuple[Edge, ...]], kept: frozenset[str]) -> frozenset[str]:
    if START not in kept:
        return frozenset()
    seen, todo = {START}, [START]
    while todo:
        for child in _children(main, kept, todo.pop()):
            if child not in seen:
                seen.add(child)
                todo.append(child)
    return frozenset(seen)
