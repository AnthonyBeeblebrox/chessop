import random
import time
from pathlib import Path

import chess
import pytest

from chessop.graph import DEFAULT_BAND, Edge, Graph, Position
from chessop.memory import Params
from chessop.play import Round
from chessop.repertoire import Repertoire, Settings
from chessop.steering import Steering
from chessop.store import Store


def pawn_graph(depth: int, games: int = 10**8) -> Graph:
    """Three pawn moves at every position down to `depth` plies, 50 : 30 : 20, the deepest
    positions named. Pawn moves never repeat a position, so it is a DAG, with transpositions."""
    edges: dict[str, list[Edge]] = {}
    found: list[tuple[str, int, int]] = []
    todo = [(chess.Board(), games, 0)]
    while todo:
        board, count, ply = todo.pop(0)
        epd = board.epd()
        if epd in edges:
            continue
        edges[epd] = []
        found.append((epd, count, ply))
        if ply == depth:
            continue
        pawn_moves = sorted(
            (m for m in board.legal_moves if board.piece_type_at(m.from_square) == chess.PAWN),
            key=chess.Move.uci,
        )
        for move, share in zip(pawn_moves, (0.5, 0.3, 0.2), strict=False):
            child = board.copy(stack=False)
            child.push(move)
            edges[epd].append(
                Edge(epd, move.uci(), board.san(move), int(count * share), child.epd())
            )
            todo.append((child, int(count * share), ply + 1))
    positions = {
        epd: Position(
            epd, count, "Leaf" if ply == depth else None, None, (), None, tuple(edges[epd])
        )
        for epd, count, ply in found
    }
    return Graph(version="latency", band=DEFAULT_BAND, games=games, positions=positions)


@pytest.mark.slow
def test_a_move_is_handled_under_10_ms_at_p95_on_a_10k_position_band(tmp_path: Path) -> None:
    repertoire = Repertoire(pawn_graph(depth=10), Settings(popularity_floor=0.0))
    assert len(repertoire.positions) > 10_000
    # On disk, so that a round-ending move pays for the real commit.
    store, params, rng = Store.open(tmp_path).implicit(), Params(), random.Random(0)
    steering = Steering(repertoire, store.record, params)
    timings: list[float] = []
    while len(timings) < 2000:
        rnd = Round(repertoire, rng, store, params, steering)
        while rnd.in_flight:
            accepted = [e.uci for e in repertoire.accepted(rnd.board.epd())]
            if rng.random() < 0.1:  # now and then a miss
                uci = next(m.uci() for m in rnd.board.legal_moves if m.uci() not in accepted)
            else:
                uci = rng.choice(accepted)
            started = time.perf_counter()
            rnd.move(uci[:2], uci[2:4])
            timings.append(time.perf_counter() - started)
    timings.sort()
    assert timings[int(0.95 * len(timings))] < 0.010
