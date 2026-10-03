"""One round: the learner against the opponent over the repertoire, as socket protocol messages.

The learner's side and the opponent's replies are drawn by need (`steering`). A learner move is a
pass when it is in the accepted set, a miss otherwise. The round ends on a miss, or as a success
when a move lands on a stub or a leaf (or on a position where the opponent has nothing to draw).
The main moves leave the server only in `round_over`, revealed at the position the round's last
move was played from. Now and then a learner turn sets aside the main move the learner knows
best (forced exploration), announced on the message that brings the turn; playing it ends the
round as `forced`, neither a pass nor a miss, its position's record untouched and no Score change
shown. `round_over` carries the Explanation of the position where the round ended.

Each pass or miss is judged against the learner's record at the moment of the move and applied to
the store when the round ends, in one commit; a round that never ends writes nothing. The Score
travels on every `round`, with its change since the last round played on a socket's first; its
change over the round (at the moment the round ends) on `round_over`.
"""

import random
import time
from typing import Any, Literal

import chess

from chessop.clock import Clock
from chessop.explanations import Explanations
from chessop.graph import Edge
from chessop.memory import Params, Record, Verdict, judge_pass, recall
from chessop.repertoire import START, Repertoire, Side, to_move
from chessop.score import change, percent, scores
from chessop.steering import Steering
from chessop.store import LearnerStore, Outcome, RoundEnd

Message = dict[str, Any]

ILLEGAL: Message = {"type": "error", "text": "illegal"}


def dests(board: chess.Board) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for m in board.legal_moves:
        out.setdefault(chess.square_name(m.from_square), []).append(chess.square_name(m.to_square))
    return out


def _move_json(board: chess.Board, move: chess.Move) -> Message:
    return {"san": board.san(move), "uci": move.uci()}


class Round:
    def __init__(
        self,
        repertoire: Repertoire,
        rng: random.Random,
        store: LearnerStore,
        params: Params,
        steering: Steering,
        explanations: Explanations | None = None,
        clock: Clock = time.time,
    ) -> None:
        self.clock = clock
        self.repertoire = repertoire
        self.explanations = explanations
        self.rng = rng
        self.store = store
        self.params = params
        self.steering = steering
        self.started_at = self.clock()
        self.verdicts: dict[str, tuple[Verdict, float]] = {}
        self.before: dict[str, dict[str, Any]] = {}
        self.side: Side = steering.draw_side(rng, self.started_at)
        self.board = chess.Board()
        self.opening: str | None = None
        self.eco: str | None = None
        self.in_flight = True
        self.forced: Edge | None = None
        if self.side == "black":
            # A first move onto a leaf would leave the learner nothing to drill: never drawn.
            openers = [e for e in repertoire.drawable(START) if not repertoire.is_leaf(e.child_epd)]
            if openers:
                self._opponent_draws(openers)
            else:
                self.side = "white"
        self._learner_turn()

    def start_message(self, *, first: bool) -> Message:
        """The `round` message; a socket's `first` round carries the change since the last round
        played (the latest daily score row), which a later round of the same socket does not."""
        now = self.clock()
        score = scores(self.repertoire, self.store.record, now, self.params).score
        last = self.store.latest_daily_score(now) if first else None
        return {
            "type": "round",
            "side": self.side,
            "orientation": self.side,
            **self._position_fields(),
            "score": percent(score),
            "score_since": None
            if last is None
            else {"delta": change(score, last[1]), "day": last[0]},
            "notice": None,
        }

    def move(self, frm: str, to: str) -> list[Message]:
        """Judge a learner move; the messages to send back, in order."""
        if not self.in_flight:
            return [ILLEGAL]
        try:
            # Castling normalised to the king's two-step move; a pawn on the back rank queens.
            move = self.board.find_move(chess.parse_square(frm), chess.parse_square(to))
        except ValueError:
            return [ILLEGAL]

        played_from = self.board.copy(stack=False)
        played = _move_json(self.board, move)
        rep = self.repertoire
        if self.forced is not None and self.forced.uci == move.uci():
            self._record_before(played_from.epd(), self.clock())
            self._push(move)
            return self._end("forced", played, None, reveal=played_from, reveal_played=played)
        edge = next((e for e in rep.accepted(played_from.epd()) if e.uci == move.uci()), None)
        self._judge(played_from.epd(), passed=edge is not None)
        self._push(move)

        if edge is None:
            return self._end("miss", played, None, reveal=played_from, reveal_played=played)
        child = self.board.epd()
        if rep.is_stub(edge) or rep.is_leaf(child) or not rep.drawable(child):
            return self._end("pass", played, None, reveal=played_from, reveal_played=None)

        before_reply = self.board.copy(stack=False)
        reply = self._opponent_draws()
        if rep.is_leaf(self.board.epd()):
            return self._end("pass", played, reply, reveal=before_reply, reveal_played=None)
        self._learner_turn()
        return [self._moved("pass", played, reply)]

    def _learner_turn(self) -> None:
        """Draw whether this learner turn sets a move aside."""
        self.forced = self.steering.set_aside(self.board.epd(), self.side, self.rng, self.clock())

    def _record_before(self, epd: str, now: float) -> Record:
        """Keep the position's record and recall estimate as they stood before the round."""
        record = self.store.record(epd)
        self.before[epd] = {
            "passes": record.passes,
            "misses": record.misses,
            "relearn": record.relearn,
            "last_pass": record.last_pass,
            "R": recall(record, now, self.params),
        }
        return record

    def _judge(self, epd: str, *, passed: bool) -> None:
        now = self.clock()
        record = self._record_before(epd, now)
        verdict = judge_pass(record, now, self.params) if passed else "miss"
        self.verdicts[epd] = (verdict, now)

    def _opponent_draws(self, among: list[Edge] | None = None) -> Message:
        edge = self.steering.draw(self.board.epd(), self.rng, self.clock(), among=among)
        move = chess.Move.from_uci(edge.uci)
        reply = _move_json(self.board, move)
        self._push(move)
        return reply

    def _push(self, move: chess.Move) -> None:
        self.board.push(move)
        position = self.repertoire.position(self.board.epd())
        if position is not None and position.name is not None:
            self.opening, self.eco = position.name, position.eco

    def _position_fields(self, *, over: bool = False) -> Message:
        forced = None if over else self.forced
        return {
            "fen": self.board.fen(),
            "dests": {} if over else dests(self.board),
            "opening": self.opening,
            "eco": self.eco,
            "forced": None if forced is None else forced.san,
            "forced_uci": None if forced is None else forced.uci,
        }

    def _moved(
        self, verdict: str, played: Message, reply: Message | None, *, over: bool = False
    ) -> Message:
        return {
            "type": "moved",
            "verdict": verdict,
            "played": played,
            "reply": reply,
            **self._position_fields(over=over),
        }

    def _end(
        self,
        verdict: Literal["pass", "miss", "forced"],
        played: Message,
        reply: Message | None,
        *,
        reveal: chess.Board,
        reveal_played: Message | None,
    ) -> list[Message]:
        self.in_flight = False
        path = [m.uci() for m in self.board.move_stack]
        # The learner's accepted set at their own position; at the opponent's, what it might draw.
        epd = reveal.epd()
        rep = self.repertoire
        moves = rep.accepted(epd) if to_move(epd) == self.side else rep.drawable(epd)
        main = [{"san": e.san, "uci": e.uci} for e in moves]
        outcome: Outcome = "success" if verdict == "pass" else verdict
        ended_at = self.clock()
        before, after = self.store.commit(
            RoundEnd(
                started_at=self.started_at,
                ended_at=ended_at,
                side=self.side,
                path=path,
                outcome=outcome,
                end_epd=self.board.epd(),
                verdicts=self.verdicts,
                before=self.before,
                snapshot_version=rep.graph.version,
            ),
            lambda record: scores(rep, record, ended_at, self.params),
        )
        self.steering.changed(self.verdicts)
        # Explained where the round ended: the leaf (or stub) on a success, else the learner's
        # position the move was played from, whose main moves are revealed.
        ended_on = path if outcome == "success" else path[:-1]
        explanation = None if self.explanations is None else self.explanations.for_path(ended_on)
        over = {
            "type": "round_over",
            "outcome": outcome,
            "reveal": {
                "epd": reveal.epd(),
                "fen": reveal.fen(),
                "main": main,
                "played": reveal_played,
            },
            "path": path,
            "plies": len(path),
            "opening": self.opening,
            "eco": self.eco,
            "explanation": explanation,
            "score": {
                "value": percent(after.score),
                "delta": None if outcome == "forced" else change(after.score, before.score),
            },
        }
        return [self._moved(verdict, played, reply, over=True), over]
