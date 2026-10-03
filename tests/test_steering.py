import random
from collections import Counter

import pytest

from chessop.graph import Edge
from chessop.memory import DAY, Params, Record
from chessop.repertoire import START, Repertoire, Settings
from chessop.steering import STALE, Steering, faced_from_log, side_share
from graphs import epd_after, graph_of

P = Params()
NOW = 1_800_000_000.0

# Two move orders reach the Italian, Z: 1.e4 e5 2.Nf3 Nc6 3.Bc4 and 1.e4 e5 2.Bc4 Nc6 3.Nf3.
# Black to move, and so drilled when the learner is Black: 1.e4 (6,000), 2.Nf3 (2,000),
# 2.Bc4 (500), Z (1,000) and 1.d4 (3,000). White to move: the start (10,000), 1...e5 (3,000),
# 2...Nc6 after 2.Nf3 (1,500) and after 2.Bc4 (300). 3...Bc5 and 1...d5 are leaves.
ITALIAN = graph_of(
    {
        "e4": 6000,
        "e4 e5": 3000,
        "e4 e5 Nf3": 2000,
        "e4 e5 Nf3 Nc6": 1500,
        "e4 e5 Nf3 Nc6 Bc4": 1000,
        "e4 e5 Bc4": 500,
        "e4 e5 Bc4 Nc6": 300,
        "e4 e5 Bc4 Nc6 Nf3": 200,
        "e4 e5 Nf3 Nc6 Bc4 Bc5": 800,
        "d4": 3000,
        "d4 d5": 2000,
    },
    {"e4 e5 Nf3 Nc6 Bc4 Bc5": "Italian Game: Giuoco Piano", "d4 d5": "Queen's Pawn Game"},
)
REP = Repertoire(ITALIAN, Settings())
E4, D4, Z = epd_after("e4"), epd_after("d4"), epd_after("e4", "e5", "Nf3", "Nc6", "Bc4")


def edge(*sans: str) -> Edge:
    """The repertoire's main move that plays the last of `sans` after the others."""
    *before, san = sans
    return next(e for e in REP.main_moves(epd_after(*before)) if e.san == san)


def steering(records: dict[str, Record], params: Params = P, **kwargs) -> Steering:
    return Steering(REP, lambda epd: records.get(epd, Record()), params, **kwargs)


KNOWN = Record(passes=1, last_pass=NOW)  # R = 1: need at the floor
HALF = Record(passes=1, last_pass=NOW - 2 * DAY)  # h = 2 days: R = 0.5, need 0.5


def test_mean_need_counts_a_position_two_move_orders_reach_once() -> None:
    need = steering({E4: HALF, Z: KNOWN})
    # 1.e4, 2.Nf3, 2.Bc4 and Z below 1.e4, weighted by pooled count, Z once.
    expected = (6000 * 0.5 + 2000 * 1 + 500 * 1 + 1000 * 0.1) / 9500
    assert need.mean_need(edge("e4"), "black", NOW) == pytest.approx(expected)
    assert need.mean_need(edge("d4"), "black", NOW) == pytest.approx(1.0)


def test_mean_need_below_an_edge_counts_the_learners_colour_only() -> None:
    need = steering({START: KNOWN, E4: HALF, Z: KNOWN})
    # White to move below 1.e4: 1...e5 and the two 2...Nc6 positions, never passed.
    assert need.mean_need(edge("e4"), "white", NOW) == pytest.approx(1.0)
    # Below 3.Bc4, Z for Black; for White nothing but the leaf after 3...Bc5.
    bc4 = edge("e4", "e5", "Nf3", "Nc6", "Bc4")
    assert need.mean_need(bc4, "black", NOW) == pytest.approx(0.1)
    assert need.mean_need(bc4, "white", NOW) == P.floor


def test_mean_need_of_an_empty_set_is_the_floor() -> None:
    need = steering({})
    onto_leaf = edge("e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5")
    assert need.mean_need(onto_leaf, "white", NOW) == P.floor
    assert need.mean_need(onto_leaf, "black", NOW) == P.floor
    assert need.mean_need(edge("d4", "d5"), "white", NOW) == P.floor


def test_mean_need_of_a_stub_is_the_floor() -> None:
    graph = graph_of(
        {"e4": 6000, "e4 e5": 3000, "Nf3": 400},
        {"e4 e5": "King's Pawn Game"},
        unstored=frozenset({"Nf3"}),
    )
    rep = Repertoire(graph, Settings())
    stub = next(e for e in rep.main_moves(START) if e.san == "Nf3")
    assert rep.is_stub(stub)
    assert Steering(rep, lambda epd: Record(), P).mean_need(stub, "black", NOW) == P.floor


def test_the_memo_is_invalidated_along_every_ancestor_of_a_changed_position() -> None:
    records: dict[str, Record] = {}
    need = steering(records)
    assert need.mean_need(edge("e4"), "black", NOW) == pytest.approx(1.0)
    assert need.mean_need(edge("e4", "e5", "Bc4"), "black", NOW) == pytest.approx(1.0)
    assert need.root_need(NOW)["black"] == pytest.approx(12_500)

    records[Z] = KNOWN
    # Memoised: nothing changes until the change is reported.
    assert need.mean_need(edge("e4"), "black", NOW) == pytest.approx(1.0)
    need.changed([Z])
    assert need.mean_need(edge("e4"), "black", NOW) == pytest.approx((8500 + 100) / 9500)
    assert need.mean_need(edge("e4", "e5", "Bc4"), "black", NOW) == pytest.approx(
        (500 + 100) / 1500
    )
    assert need.root_need(NOW)["black"] == pytest.approx(11_500 + 100)
    assert need.mean_need(edge("d4"), "black", NOW) == pytest.approx(1.0)


def test_a_memo_older_than_the_stale_window_is_recomputed() -> None:
    records = {E4: Record(passes=1, last_pass=NOW)}
    need = steering(records)
    at_start = need.mean_need(edge("e4"), "black", NOW)
    # Two days on, 1.e4's recall has halved; within the window the memo stands.
    later = NOW + 2 * DAY
    assert need.mean_need(edge("e4"), "black", NOW + STALE / 2) == at_start
    assert need.mean_need(edge("e4"), "black", later) == pytest.approx((6000 * 0.5 + 3500) / 9500)


def test_root_need_is_the_count_weighted_need_per_colour() -> None:
    need = steering({START: KNOWN, E4: HALF, Z: KNOWN, epd_after("e4", "e5", "Nf3", "Nc6"): HALF})
    assert need.root_need(NOW) == {
        "white": pytest.approx(10_000 * 0.1 + 3000 + 1500 * 0.5 + 300),
        "black": pytest.approx(6000 * 0.5 + 2000 + 500 + 1000 * 0.1 + 3000),
    }


def test_the_side_share_is_the_white_share_of_need_clipped_to_the_side_floor() -> None:
    assert side_share(3.0, 1.0, 0.2) == pytest.approx(0.75)
    assert side_share(1.0, 9.0, 0.2) == pytest.approx(0.2)
    assert side_share(9.0, 1.0, 0.2) == pytest.approx(0.8)
    assert side_share(0.0, 0.0, 0.2) == 0.5


def test_the_side_floor_is_honoured_in_the_draw() -> None:
    # Every White position known, every Black one never passed: White only at the side floor.
    records = {epd: KNOWN for epd in REP.learner_positions if epd.split()[1] == "w"}
    need = steering(records)
    rng = random.Random(1)
    sides = Counter(need.draw_side(rng, NOW) for _ in range(20_000))
    assert sides["white"] / 20_000 == pytest.approx(0.2, abs=0.015)


def test_the_side_draw_follows_the_root_need() -> None:
    need = steering({})
    rng = random.Random(2)
    sides = Counter(need.draw_side(rng, NOW) for _ in range(20_000))
    assert sides["white"] / 20_000 == pytest.approx(14_800 / (14_800 + 12_500), abs=0.015)


WIDE = graph_of(
    {
        "e4": 6000,
        "e4 c5": 2400,
        "e4 e5": 1800,
        "e4 e6": 600,
        "e4 a6": 300,
        "e4 c5 Nf3": 2000,
        "e4 e5 Nf3": 1500,
        "e4 e6 d4": 500,
    },
    {
        "e4 c5 Nf3": "Sicilian Defense",
        "e4 e5 Nf3": "King's Knight Opening",
        "e4 e6 d4": "French Defense",
    },
    unstored=frozenset({"e4 a6"}),
)
WIDE_REP = Repertoire(WIDE, Settings())


def wide(records: dict[str, Record], params: Params = P, **kwargs) -> Steering:
    return Steering(WIDE_REP, lambda epd: records.get(epd, Record()), params, **kwargs)


def draws(need: Steering, n: int, seed: int = 3) -> Counter[str]:
    rng = random.Random(seed)
    return Counter(need.draw(E4, rng, NOW).san for _ in range(n))


def first_draws(faced: Counter[tuple[str, str]], n: int) -> Counter[str]:
    """The opponent's reply at 1.e4 drawn `n` times, each from the same times faced."""
    rng = random.Random(6)
    return Counter(wide({}, faced=Counter(faced)).draw(E4, rng, NOW).san for _ in range(n))


def test_with_no_history_the_opponent_plays_the_bands_popularity() -> None:
    # 1...a6 is main but a stub: the rest renormalised, 2400 : 1800 : 600, at the default C = 1.
    got = first_draws(Counter(), 30_000)
    for san, count in (("c5", 2400), ("e5", 1800), ("e6", 600)):
        assert got[san] / 30_000 == pytest.approx(count / 4800, abs=0.01)


def test_a_stub_is_never_drawn() -> None:
    assert any(e.san == "a6" and WIDE_REP.is_stub(e) for e in WIDE_REP.main_moves(E4))
    assert "a6" not in draws(wide({}), 5_000)


def test_the_opponent_steers_away_from_what_the_learner_knows() -> None:
    # White knows the position after 1...c5, the only one below it: drawn at popularity x floor.
    records = {epd_after("e4", "c5"): KNOWN}
    got = draws(wide(records, Params(C=0.0)), 30_000)
    weights = {"c5": 2400 * 0.1, "e5": 1800, "e6": 600}
    total = sum(weights.values())
    for san, w in weights.items():
        assert got[san] / 30_000 == pytest.approx(w / total, abs=0.01)


def test_a_rarely_faced_move_is_favoured_once_the_others_are_faced() -> None:
    # 1...c5 and 1...e5 faced 99 times each (bonus 0.1), 1...e6 never (bonus 1).
    worn = Counter({(E4, "c7c5"): 99, (E4, "e7e5"): 99})
    got = first_draws(worn, 30_000)
    weights = {"c5": 2400 * 1.1, "e5": 1800 * 1.1, "e6": 600 * 2}
    total = sum(weights.values())
    for san, w in weights.items():
        assert got[san] / 30_000 == pytest.approx(w / total, abs=0.01)
    assert got["e6"] / 30_000 > 600 / 4800 + 0.05


def test_every_draw_is_counted_as_faced() -> None:
    need = wide({})
    rng = random.Random(4)
    got = Counter(need.draw(E4, rng, NOW).uci for _ in range(100))
    assert need.faced == Counter({(E4, uci): n for uci, n in got.items()})


def test_a_draw_among_given_edges_draws_only_those() -> None:
    need = wide({})
    among = [e for e in WIDE_REP.drawable(E4) if e.san != "c5"]
    rng = random.Random(5)
    assert {need.draw(E4, rng, NOW, among=among).san for _ in range(500)} == {"e5", "e6"}


def test_faced_is_rebuilt_from_the_round_log_counting_the_opponents_moves_only() -> None:
    log = [
        {"side": "white", "path": ["e2e4", "c7c5", "g1f3"]},
        {"side": "black", "path": ["e2e4", "c7c5", "g1f3"]},
        {"side": "white", "path": ["e2e4", "c7c5"]},
    ]
    assert faced_from_log(log) == Counter(
        {
            (epd_after("e4"), "c7c5"): 2,
            (START, "e2e4"): 1,
            (epd_after("e4", "c5"), "g1f3"): 1,
        }
    )


# Forced exploration. As White at the start, 1.e4 and 1.d4 are accepted; 1...d5 is a leaf, so
# the mean need below 1.d4 is the floor. After 1.e4 e5, 2.Nf3 and 2.Bc4 each lead to one White
# position: 2...Nc6 after 2.Nf3 (1,500) and after 2.Bc4 (300).
ALWAYS = Params(forced_rate=1.0)
E4_E5 = epd_after("e4", "e5")
NF3_NC6, BC4_NC6 = epd_after("e4", "e5", "Nf3", "Nc6"), epd_after("e4", "e5", "Bc4", "Nc6")


def set_aside(records: dict[str, Record], epd: str, params: Params = ALWAYS, **settings) -> str:
    rep = Repertoire(ITALIAN, Settings(**settings))
    need = Steering(rep, lambda p: records.get(p, Record()), params)
    edge = need.set_aside(epd, "white", random.Random(1), NOW)
    return edge.san if edge else ""


def test_the_move_with_strictly_the_lowest_mean_need_is_set_aside() -> None:
    assert set_aside({E4_E5: HALF, NF3_NC6: KNOWN}, E4_E5) == "Nf3"
    assert set_aside({E4_E5: HALF, BC4_NC6: KNOWN}, E4_E5) == "Bc4"


def test_a_move_with_nothing_below_it_is_set_aside_first() -> None:
    assert set_aside({START: HALF}, START) == "d4"


def test_a_tie_for_the_lowest_mean_need_forces_nothing() -> None:
    assert set_aside({E4_E5: HALF}, E4_E5) == ""
    assert set_aside({E4_E5: HALF, NF3_NC6: KNOWN, BC4_NC6: KNOWN}, E4_E5) == ""


def test_a_position_never_seen_forces_nothing() -> None:
    assert set_aside({NF3_NC6: KNOWN}, E4_E5) == ""
    assert set_aside({}, START) == ""


def test_nothing_is_set_aside_when_the_learners_width_is_one() -> None:
    # 1.d4 is 30 % of the games: accepted by share even at width 1.
    assert len(Repertoire(ITALIAN, Settings(width_player=1)).accepted(START)) == 2
    assert set_aside({START: HALF}, START, width_player=1) == ""


def test_nothing_is_set_aside_with_a_single_accepted_move() -> None:
    assert len(REP.accepted(E4)) == 1
    need = Steering(REP, lambda p: HALF, ALWAYS)
    assert need.set_aside(E4, "black", random.Random(1), NOW) is None


def test_a_move_is_set_aside_at_the_forced_rate() -> None:
    need = steering({START: HALF}, Params(forced_rate=0.1))
    rng = random.Random(5)
    got = sum(need.set_aside(START, "white", rng, NOW) is not None for _ in range(20_000))
    assert got / 20_000 == pytest.approx(0.1, abs=0.01)
    assert (
        steering({START: HALF}, Params(forced_rate=0.0)).set_aside(START, "white", rng, NOW) is None
    )
