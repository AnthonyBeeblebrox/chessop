"""The memory model (spec §5.1): one record per learner position, and what it predicts.

Half-life `h = clip(h0 * 2^(s - f), h_min, h_max)`; recall estimate `R = 2^(-(now - t_last) / h)`,
0 for a position never passed; need `max(floor, 1 - R)`. A pass is judged at the moment of the
move: a relearning pass when a miss left the mark, a sure pass when `R >= sure`, counted otherwise.
Times are Unix seconds.
"""

from dataclasses import dataclass, replace
from typing import Literal

MINUTE = 60.0
HOUR = 60 * MINUTE
DAY = 24 * HOUR

Verdict = Literal["counted", "sure", "relearning", "miss"]
PassKind = Literal["counted", "sure", "relearning"]


@dataclass(frozen=True)
class Params:
    """The model's parameters at the spec §5.4 defaults."""

    h0: float = DAY
    h_min: float = 15 * MINUTE
    h_max: float = 270 * DAY  # 9 months
    sure: float = 0.9  # also the Known threshold
    floor: float = 0.1
    C: float = 1.0
    alpha: float = 1.0
    forced_rate: float = 0.1
    side_floor: float = 0.2


@dataclass(frozen=True)
class Record:
    """A position record: counted passes, misses, the last pass (None if never) and the mark."""

    passes: int = 0
    misses: int = 0
    last_pass: float | None = None
    relearn: bool = False

    def apply(self, verdict: Verdict, at: float) -> "Record":
        """The record after a pass of the given kind, or a miss, made at time `at`."""
        match verdict:
            case "counted":
                return replace(self, passes=self.passes + 1, last_pass=at)
            case "sure":
                return replace(self, last_pass=at)
            case "relearning":
                return replace(self, relearn=False, last_pass=at)
            case "miss":  # the clock is untouched
                return replace(self, misses=self.misses + 1, relearn=True)


def half_life(record: Record, params: Params) -> float:
    h = params.h0 * 2.0 ** (record.passes - record.misses)
    return min(params.h_max, max(params.h_min, h))


def recall(record: Record, now: float, params: Params) -> float:
    if record.last_pass is None:
        return 0.0
    return 2.0 ** (-(now - record.last_pass) / half_life(record, params))


def need(record: Record, now: float, params: Params) -> float:
    return max(params.floor, 1.0 - recall(record, now, params))


def judge_pass(record: Record, now: float, params: Params) -> PassKind:
    if record.relearn:
        return "relearning"
    if recall(record, now, params) >= params.sure:
        return "sure"
    return "counted"
