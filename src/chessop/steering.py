"""Steering by need (spec §5.2, §5.3 steps 1 to 3): the side drawn and the opponent's replies.

The **mean need below an edge** is the count-weighted mean need of the learner positions of one
colour reachable from its child over kept main moves, each position once however many move orders
reach it; an empty set (a stub, an edge onto a leaf) has the floor as its mean need. The side is
drawn by each colour's need summed over the whole repertoire, clipped to the side floor. At an
opponent position each drawable edge weighs `pop^alpha * (mean_need + C / sqrt(1 + faced))` and
the reply is drawn in proportion (ADR 0001, ticket 23 amendment). With no history every weight is
`pop * (1 + C)`, the band's own popularity over the drawable set; the bonus, strongest for edges
never faced, favours rarely faced replies in proportion to their popularity. Forced exploration
(step 3) sets aside, now and then, the learner's main move with strictly the lowest mean need.

The sum of needs behind a mean is memoised per position and colour, and each position's need with
it: dropped for a position whose record changed and every ancestor of it, and all recomputed once
older than `STALE`, since needs rise with time alone.

What depends on the repertoire alone is its `Reach`: the learner positions below each position,
their pooled counts and each position's parents. Every learner drilling one repertoire steers over
the same one (public spec §4); a `Steering` holds only what is the learner's.
"""

import math
import random
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from typing import Any

import chess

from chessop.graph import Edge
from chessop.memory import Params, Record, need
from chessop.repertoire import START, Repertoire, Side, to_move

STALE = 60.0  # seconds the memoised needs stand before time alone recomputes them

SIDES: tuple[Side, Side] = ("white", "black")


def side_share(need_white: float, need_black: float, side_floor: float) -> float:
    """The chance the learner plays White: White's share of the need, clipped to the side floor."""
    total = need_white + need_black
    if total == 0:
        return 0.5
    return min(1 - side_floor, max(side_floor, need_white / total))


def faced_from_log(rounds: Iterable[dict[str, Any]]) -> Counter[tuple[str, str]]:
    """How many times the opponent has played each edge, keyed by (EPD, UCI), from the round log."""
    faced: Counter[tuple[str, str]] = Counter()
    for row in rounds:
        board = chess.Board()
        for uci in row["path"]:
            epd = board.epd()
            if to_move(epd) != row["side"]:
                faced[(epd, uci)] += 1
            board.push_uci(uci)
    return faced


class Reach:
    """What steering knows of a repertoire whoever the learner is: each learner position's pooled
    count, each position's parents over kept main moves, and the learner positions of each colour
    at or below a position with their summed counts, worked out as they are first asked for."""

    def __init__(self, repertoire: Repertoire) -> None:
        self.repertoire = repertoire
        self.count = {epd: count for epd, count, _ in repertoire.learner_counts}
        self.parents: dict[str, set[str]] = {}
        self._below: dict[str, dict[Side, frozenset[str]]] = {}
        self._weight: dict[tuple[str, Side], int] = {}
        for epd in repertoire.positions:
            for child in self._kept_children(epd):
                self.parents.setdefault(child, set()).add(epd)

    def below(self, epd: str) -> dict[Side, frozenset[str]]:
        """The learner positions of each colour at or below `epd`: a set, so each is there once."""
        if epd not in self._below:
            below: dict[Side, set[str]] = {side: set() for side in SIDES}
            if epd in self.repertoire.learner_positions:
                below[to_move(epd)].add(epd)
            for child in self._kept_children(epd):
                for side, positions in self.below(child).items():
                    below[side] |= positions
            self._below[epd] = {side: frozenset(below[side]) for side in SIDES}
        return self._below[epd]

    def weight_below(self, epd: str, side: Side) -> int:
        """`sum(count(p))` over `side`'s learner positions at or below `epd`."""
        key = (epd, side)
        if key not in self._weight:
            self._weight[key] = sum(self.count[p] for p in self.below(epd)[side])
        return self._weight[key]

    def _kept_children(self, epd: str) -> Iterable[str]:
        rep = self.repertoire
        return (e.child_epd for e in rep.main_moves(epd) if not rep.is_stub(e))


class Steering:
    """One learner's steering over a repertoire: their records' needs, memoised, and how often
    they faced each edge. `reach` is the repertoire's, shared when given, else its own."""

    def __init__(
        self,
        repertoire: Repertoire,
        record: Callable[[str], Record],
        params: Params,
        faced: Counter[tuple[str, str]] | None = None,
        reach: Reach | None = None,
    ) -> None:
        self.repertoire = repertoire
        self.record = record
        self.params = params
        self.faced: Counter[tuple[str, str]] = faced if faced is not None else Counter()
        self._reach = reach if reach is not None else Reach(repertoire)
        # The memo: each learner position's need and each (position, colour)'s sum of needs, as
        # they stood at `_epoch`.
        self._epoch = -math.inf
        self._needs: dict[str, float] = {}
        self._sums: dict[tuple[str, Side], float] = {}

    def mean_need(self, edge: Edge, side: Side, now: float) -> float:
        """The mean need of `side`'s learner positions below `edge`; the floor if there are none."""
        if self.repertoire.is_stub(edge):
            return self.params.floor
        weight = self._reach.weight_below(edge.child_epd, side)
        return self._sum(edge.child_epd, side, now) / weight if weight else self.params.floor

    def root_need(self, now: float) -> dict[Side, float]:
        """Each colour's count-weighted need summed over its learner positions."""
        return {side: self._sum(START, side, now) for side in SIDES}

    def draw_side(self, rng: random.Random, now: float) -> Side:
        needs = self.root_need(now)
        p_white = side_share(needs["white"], needs["black"], self.params.side_floor)
        return "white" if rng.random() < p_white else "black"

    def draw(
        self, epd: str, rng: random.Random, now: float, among: Sequence[Edge] | None = None
    ) -> Edge:
        """The opponent's reply at `epd`, drawn from `among` (default its drawable set); counted
        as faced."""
        edges = self.repertoire.drawable(epd) if among is None else among
        if len(edges) == 1:
            [drawn] = edges
        else:
            learner: Side = "black" if to_move(epd) == "white" else "white"
            p = self.params
            total = sum(e.count for e in edges)
            weights = [
                (e.count / total) ** p.alpha
                * (self.mean_need(e, learner, now) + p.C / math.sqrt(1 + self.faced[(epd, e.uci)]))
                for e in edges
            ]
            drawn = rng.choices(edges, weights=weights)[0]
        self.faced[(epd, drawn.uci)] += 1
        return drawn

    def set_aside(self, epd: str, side: Side, rng: random.Random, now: float) -> Edge | None:
        """Forced exploration at a learner position: with probability `forced_rate`, the learner's
        main move whose mean need is strictly the lowest, set aside for this turn; None when there
        is nothing to set aside (one such move, a width of one, a tie, a position never seen)."""
        accepted = self.repertoire.accepted(epd)
        if len(accepted) < 2 or self.repertoire.settings.width_player < 2:
            return None
        if self.record(epd) == Record():
            return None
        needs = sorted((self.mean_need(e, side, now), i) for i, e in enumerate(accepted))
        (lowest, i), (second, _) = needs[:2]
        # Drawn last, so a turn with nothing to set aside leaves the rng as it was.
        if lowest < second and rng.random() < self.params.forced_rate:
            return accepted[i]
        return None

    def changed(self, epds: Iterable[str]) -> None:
        """Forget the memoised needs and sums at and above every position whose record changed."""
        todo = [e for e in epds if e in self.repertoire.positions]
        seen = set(todo)
        while todo:
            epd = todo.pop()
            self._needs.pop(epd, None)
            for side in SIDES:
                self._sums.pop((epd, side), None)
            for parent in self._reach.parents.get(epd, ()):
                if parent not in seen:
                    seen.add(parent)
                    todo.append(parent)

    def _sum(self, epd: str, side: Side, now: float) -> float:
        """`sum(count(p) * need(p))` over `side`'s learner positions at or below `epd`."""
        if abs(now - self._epoch) >= STALE:
            self._epoch = now
            self._needs.clear()
            self._sums.clear()
        key = (epd, side)
        if key not in self._sums:
            needs, count, needed = self._needs, self._reach.count, 0.0
            for p in self._reach.below(epd)[side]:
                u = needs.get(p)
                if u is None:
                    u = needs[p] = need(self.record(p), now, self.params)
                needed += count[p] * u
            self._sums[key] = needed
        return self._sums[key]
