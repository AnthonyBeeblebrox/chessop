"""The Score (spec §6): how well the learner knows the scoped repertoire, as one number.

`Score = sum(count(p) * R(p)) / sum(count(p))` over every learner position `p`, `count` the pooled
snapshot count and `R` the raw recall estimate (0 when never passed; not `1 - need`, so the floor
does not cap it). The White and Black scores are the same sum over one colour's positions. It
falls with time like the estimates under it, so it is always computed at a given moment.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from chessop.memory import Params, Record, recall
from chessop.repertoire import Repertoire, Side


@dataclass(frozen=True)
class Scores:
    """The Score and the two per-colour scores, each a fraction in [0, 1]."""

    score: float
    white: float
    black: float


def scores(
    repertoire: Repertoire, record: Callable[[str], Record], now: float, params: Params
) -> Scores:
    """The scores at `now` with each position's record looked up by `record`."""
    return scores_over(repertoire.learner_counts, record, now, params)


def scores_over(
    learner: Iterable[tuple[str, int, Side]],
    record: Callable[[str], Record],
    now: float,
    params: Params,
) -> Scores:
    """The same sums over some learner positions only, each with its pooled count and colour;
    0 where there is no position to score."""
    recalled = {"white": 0.0, "black": 0.0}
    weight = {"white": 0, "black": 0}
    for epd, count, side in learner:
        weight[side] += count
        r = record(epd)
        if r.last_pass is not None:  # else R = 0: a round end scores thousands, keep it cheap
            recalled[side] += count * recall(r, now, params)

    def mean(sides: tuple[str, ...]) -> float:
        total = sum(weight[s] for s in sides)
        return sum(recalled[s] for s in sides) / total if total else 0.0

    return Scores(mean(("white", "black")), mean(("white",)), mean(("black",)))


def percent(fraction: float) -> float:
    """A score as the pages show it: a percentage with one decimal."""
    return round(100 * fraction, 1)


def change(after: float, before: float) -> float:
    """The change between two scores as shown, so that it adds up with the numbers on the page."""
    return round(percent(after) - percent(before), 1) + 0.0  # never -0.0
