"""The progress ledger (spec §10.1): the repertoire grouped into openings, lines and branches.

Outside a round a position's name is inherited along its **canonical order**: the name of the
nearest exactly-named position that is a prefix of that order, itself included (spec §4 step 9).
Its opening is the family of that name; the positions at ply 0 and 1, and any position with no
named prefix, form the "First moves" group. Openings are listed "First moves" first, then by the
pooled count of their learner positions (the Score's own weighting); an opening unfolds into its
**lines**, one per name its positions inherit, in the same order.

A line unfolds into its **branches**, each a move string from the start to a leaf: one for each
position of the line that no position of the line continues along its canonical order, its
canonical order walked on along the most popular main moves to a leaf. A move is shown as the
learner's (coloured, linked) only where it is played from a learner position of the line reached
by that position's own canonical order, and on the first branch through it only: each learner
position is shown once, in its own line.

A position also has its own page (spec §10.2): its name marked when inherited, its numbers, its
**state word** (the shade of its moves in the ledger, in words) and the number of move orders the
snapshot stores into it, every path from the start over the stored edges.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass

import chess

from chessop.graph import Graph
from chessop.memory import Params, Record, recall
from chessop.repertoire import START, Repertoire, Side, family, to_move
from chessop.score import scores_over

FIRST_MOVES = "First moves"
TARGET = (0.8, 0.9)  # the in-session success rate aimed at (spec §5.4), displayed only


@dataclass(frozen=True)
class Naming:
    """A position's name, exact or inherited, with its ECO and the opening it is grouped in."""

    name: str | None
    eco: str | None
    exact: bool
    family: str


@dataclass(frozen=True)
class Chip:
    """One move of a branch: `epd` is the learner position it is played from, None when the move
    is shown only to lead the string there."""

    text: str
    epd: str | None


# A learner position with its pooled count and the colour to move, the weights of the scores.
LearnerPosition = tuple[str, int, Side]


@dataclass(frozen=True)
class Line:
    """An exactly-named line: the positions inheriting its name, and their branches."""

    name: str | None  # None only for positions with nothing named on their canonical order
    eco: str
    positions: tuple[LearnerPosition, ...]
    branches: tuple[tuple[Chip, ...], ...]


@dataclass(frozen=True)
class Opening:
    """An opening (a family, or the first moves) with its lines."""

    name: str
    eco: str
    positions: tuple[LearnerPosition, ...]
    lines: tuple[Line, ...]


@dataclass(frozen=True)
class Tally:
    """The numbers of a row: the scores (None with nothing of that colour to score) and how
    many positions are known, learning or never passed."""

    score: float | None
    white: float | None
    black: float | None
    known: int
    learning: int
    never: int


def tally(
    positions: Iterable[LearnerPosition],
    record: Callable[[str], Record],
    now: float,
    params: Params,
) -> Tally:
    """The row's numbers at `now` over some learner positions. A position is known when its
    shade is, never passed with no pass at all."""
    positions = tuple(positions)
    known = never = 0
    for epd, _, _ in positions:
        r = record(epd)
        if r.last_pass is None:
            never += 1
        elif shade(r, now, params) == "known":
            known += 1
    got = scores_over(positions, record, now, params)
    sides = {side for _, _, side in positions}
    return Tally(
        got.score if sides else None,
        got.white if "white" in sides else None,
        got.black if "black" in sides else None,
        known,
        len(positions) - known - never,
        never,
    )


def shade(record: Record, now: float, params: Params) -> str:
    """The colour of a learner move by its position's record: `relearn` (red) while a relearning
    pass is owed, `never` (grey) with no pass, else `known` (green) at or above the sure threshold,
    `learning` (yellow) from one half, `fading` (orange) below."""
    if record.relearn:
        return "relearn"
    if record.last_pass is None:
        return "never"
    r = recall(record, now, params)
    return "known" if r >= params.sure else "learning" if r >= 0.5 else "fading"


def state_word(record: Record, now: float, params: Params) -> str:
    """The position page's word for a record: its shade in the ledger, in words."""
    word = shade(record, now, params)
    return {"relearn": "relearning", "never": "never passed"}.get(word, word)


def duration(seconds: float) -> str:
    """A span of time as the position page shows it: `40 min`, `5 h`, `2.5 days`."""
    minutes = seconds / 60
    if minutes < 60:
        return f"{max(0, round(minutes))} min"
    if minutes < 48 * 60:
        return f"{round(minutes / 60)} h"
    return f"{minutes / 1440:.1f} days"


def sparkline(values: list[float], width: float, height: float) -> str:
    """SVG polyline points for `values`, scaled to their own range, oldest on the left."""
    if not values:
        return ""
    low, high = min(values), max(values)
    span = high - low or 1.0
    step = width / (len(values) - 1) if len(values) > 1 else 0.0
    return " ".join(
        f"{i * step:.1f},{height - (v - low) / span * height if high > low else height / 2:.1f}"
        for i, v in enumerate(values)
    )


class _Orders:
    """The position each move order from the start reaches, and the SAN of its last move."""

    def __init__(self) -> None:
        self._epd: dict[tuple[str, ...], str] = {(): START}
        self._san: dict[tuple[str, ...], str] = {}

    def epd(self, order: tuple[str, ...]) -> str:
        if order not in self._epd:
            board = chess.Board(f"{self.epd(order[:-1])} 0 1")
            move = chess.Move.from_uci(order[-1])
            self._san[order] = board.san(move)
            board.push(move)
            self._epd[order] = board.epd()
        return self._epd[order]

    def san(self, order: tuple[str, ...]) -> str:
        """The SAN of the order's last move."""
        self.epd(order)
        return self._san[order]


class Ledger:
    """The fixed shape of the ledger over one repertoire: names, openings, lines and branches.

    Built from the repertoire with no opening opted out, so that opted-out openings stay listed.
    """

    def __init__(self, repertoire: Repertoire) -> None:
        self.repertoire = repertoire
        self._orders = _Orders()
        self._naming: dict[str, Naming] = {}
        self._orders_into: dict[str, int] = {}
        self._parents: dict[str, list[str]] | None = None
        self.openings: tuple[Opening, ...] = self._openings()

    def moves(self, epd: str) -> str:
        """The position's canonical order as `1.e4 c5 2.Nf3`."""
        order = self.repertoire.graph.positions[epd].canonical
        sans = [self._orders.san(order[: ply + 1]) for ply in range(len(order))]
        return " ".join(numbered(ply, san) for ply, san in enumerate(sans))

    def naming(self, epd: str) -> Naming:
        """The position's name inherited along its canonical order, and its opening."""
        if epd not in self._naming:
            self._naming[epd] = _naming(self.repertoire.graph, self._orders, epd)
        return self._naming[epd]

    def move_orders(self, epd: str) -> int:
        """How many move orders from the start reach the position over the stored edges."""
        graph = self.repertoire.graph
        if self._parents is None:
            parents: dict[str, list[str]] = defaultdict(list)
            for position in graph.positions.values():
                for edge in position.edges:
                    if edge.child_epd in graph.positions:
                        parents[edge.child_epd].append(edge.epd)
            self._parents = parents  # whole at once: learners sharing the ledger read it
        if epd not in self._orders_into:  # the graph is a DAG, its depth bounded by the ply cap
            self._orders_into[epd] = (
                1 if epd == START else sum(self.move_orders(p) for p in self._parents[epd])
            )
        return self._orders_into[epd]

    def _openings(self) -> tuple[Opening, ...]:
        rep = self.repertoire
        lines: dict[str, dict[str | None, list[str]]] = defaultdict(lambda: defaultdict(list))
        for epd in sorted(rep.positions, key=self._order):
            naming = self.naming(epd)
            lines[naming.family][naming.name].append(epd)
        openings = []
        for name, by_line in lines.items():
            shaped = sorted(
                (self._line(line, epds) for line, epds in by_line.items()),
                key=lambda line: (-_weight(line.positions), line.name or ""),
            )
            openings.append(
                Opening(
                    name,
                    _eco_range(self.naming(e).eco for epds in by_line.values() for e in epds),
                    tuple(p for line in shaped for p in line.positions),
                    tuple(shaped),
                )
            )
        openings.sort(key=lambda o: (o.name != FIRST_MOVES, -_weight(o.positions), o.name))
        return tuple(openings)

    def _line(self, name: str | None, epds: list[str]) -> Line:
        rep, graph = self.repertoire, self.repertoire.graph
        members = set(epds)
        ends = []
        for epd in epds:
            canonical = graph.positions[epd].canonical
            continued = any(
                graph.positions[e.child_epd].canonical == (*canonical, e.uci)
                for e in rep.main_moves(epd)
                if e.child_epd in members
            )
            if not continued:
                ends.append(self._to_leaf(epd, canonical))
        ends.sort(key=self._order_key)
        shown: set[str] = set()
        return Line(
            name,
            _eco_range(self.naming(e).eco for e in epds),
            tuple(
                (e, graph.positions[e].count, to_move(e))
                for e in epds
                if e in rep.learner_positions
            ),
            tuple(self._branch(order, members, shown) for order in ends),
        )

    def _to_leaf(self, epd: str, order: tuple[str, ...]) -> tuple[str, ...]:
        """`order` (reaching `epd`) walked on along the most popular main move to a leaf, or to a
        stub, which ends a round the same way."""
        rep = self.repertoire
        while not rep.is_leaf(epd):
            edge = rep.main_moves(epd)[0]
            order = (*order, edge.uci)
            if rep.is_stub(edge):
                break
            epd = edge.child_epd
        return order

    def _branch(
        self, order: tuple[str, ...], members: set[str], shown: set[str]
    ) -> tuple[Chip, ...]:
        """The chips of one branch; a learner position already `shown` is not shown again."""
        rep, graph = self.repertoire, self.repertoire.graph
        chips = []
        for ply in range(len(order)):
            epd = self._orders.epd(order[:ply])
            san = self._orders.san(order[: ply + 1])
            text = numbered(ply, san)
            mine = (
                epd in members
                and epd not in shown
                and epd in rep.learner_positions
                and graph.positions[epd].canonical == order[:ply]
            )
            if mine:
                shown.add(epd)
            chips.append(Chip(text, epd if mine else None))
        return tuple(chips)

    def _order(self, epd: str) -> tuple[tuple[int, str], ...]:
        return self._order_key(self.repertoire.graph.positions[epd].canonical)

    def _order_key(self, order: tuple[str, ...]) -> tuple[tuple[int, str], ...]:
        """Canonical orders sorted move by move, the most popular position first."""
        positions = self.repertoire.graph.positions
        return tuple(
            (-(p.count if (p := positions.get(self._orders.epd(order[:ply]))) else 0), uci)
            for ply, uci in enumerate(order, 1)
        )


def _weight(positions: tuple[LearnerPosition, ...]) -> int:
    return sum(count for _, count, _ in positions)


def numbered(ply: int, san: str) -> str:
    """A move as a move string shows it: `1.e4` for White, `c5` for Black."""
    return f"{ply // 2 + 1}.{san}" if ply % 2 == 0 else san


def _eco_range(ecos: Iterable[str | None]) -> str:
    known = sorted({eco for eco in ecos if eco})
    if not known:
        return ""
    return known[0] if len(known) == 1 else f"{known[0]}\N{EN DASH}{known[-1]}"


def _naming(graph: Graph, orders: _Orders, epd: str) -> Naming:
    canonical = graph.positions[epd].canonical
    for ply in range(len(canonical), -1, -1):
        named = graph.positions.get(orders.epd(canonical[:ply]))
        if named is not None and named.name is not None:
            group = family(named.name) if len(canonical) >= 2 else FIRST_MOVES
            return Naming(named.name, named.eco, ply == len(canonical), group)
    return Naming(None, None, exact=False, family=FIRST_MOVES)
