from dataclasses import replace

from chessop.graph import FIXTURE_SNAPSHOT, Graph, load_graph
from chessop.repertoire import START, Repertoire, Settings
from graphs import epd_after, graph_of


def sans(edges) -> list[str]:
    return [e.san for e in edges]


def wide_start(**settings) -> Repertoire:
    """Seven first moves, each ending on a named position; Nc3 and Nf3 tie on count."""
    counts = {"e4": 4000, "d4": 3000, "c4": 900, "Nf3": 600, "Nc3": 600, "b3": 450, "g3": 1}
    graph = graph_of(counts, {line: line for line in counts})
    return Repertoire(graph, Settings(**settings))


def test_main_moves_are_the_top_k_by_count_plus_every_share_move() -> None:
    # k = 3; share 5 % of 10,000 = 500: Nf3 and Nc3 hold it, b3 does not.
    assert sans(wide_start().main_moves(START)) == ["e4", "d4", "c4", "Nf3", "Nc3"]


def test_the_width_that_counts_is_the_larger_of_the_two() -> None:
    assert sans(wide_start(width_player=1, width_opponent=4, share=0.5).main_moves(START)) == [
        "e4",
        "d4",
        "c4",
        "Nf3",
    ]
    assert sans(wide_start(width_player=2, width_opponent=1, share=0.5).main_moves(START)) == [
        "e4",
        "d4",
    ]


def test_ties_on_count_rank_by_san_descending() -> None:
    top4 = wide_start(width_player=4, width_opponent=4, share=0.5).main_moves(START)
    assert sans(top4) == ["e4", "d4", "c4", "Nf3"]


def test_an_edge_below_the_popularity_floor_is_never_a_main_move() -> None:
    # Floor 0.02 % of 10,000 games = 2: g3 (1 game) fails even inside the top-k.
    rep = wide_start(width_player=7, width_opponent=7)
    assert "g3" not in sans(rep.main_moves(START))
    assert "b3" in sans(rep.main_moves(START))
    rep = wide_start(width_player=7, width_opponent=7, popularity_floor=0.05)
    assert sans(rep.main_moves(START)) == ["e4", "d4", "c4", "Nf3", "Nc3"]


def test_the_share_is_of_the_positions_pooled_count_not_of_its_stored_edges() -> None:
    counts = {"e4": 600, "e4 c5": 300, "e4 e5": 200, "e4 e6": 60, "e4 d5": 40}
    names = {line: line for line in counts}
    graph = graph_of(counts, names, position_counts={"e4": 1000})
    rep = Repertoire(graph, Settings())
    # 40 is 5 % of the 800 stored after e4, but 4 % of the 1000 games reaching it.
    assert sans(rep.main_moves(epd_after("e4"))) == ["c5", "e5", "e6"]
    graph = graph_of(counts, names, position_counts={"e4": 800})
    assert sans(Repertoire(graph, Settings()).main_moves(epd_after("e4"))) == [
        "c5",
        "e5",
        "e6",
        "d5",
    ]


def unnamed_tail() -> Graph:
    """1.e4 is named below (the Sicilian); 1.d4 leads only to unnamed positions."""
    counts = {"e4": 6000, "e4 c5": 3000, "d4": 3000, "d4 d5": 1500, "d4 d5 c4": 700}
    return graph_of(counts, {"e4 c5": "Sicilian Defense"})


def test_unnamed_positions_are_kept_as_deep_as_their_moves_clear_the_floor() -> None:
    rep = Repertoire(unnamed_tail(), Settings())
    assert rep.positions == {
        START,
        epd_after("e4"),
        epd_after("e4", "c5"),
        epd_after("d4"),
        epd_after("d4", "d5"),
        epd_after("d4", "d5", "c4"),
    }
    d4 = next(e for e in rep.main_moves(START) if e.san == "d4")
    assert not rep.is_stub(d4)
    assert sans(rep.drawable(START)) == ["e4", "d4"]


def test_a_leaf_need_not_be_named() -> None:
    rep = Repertoire(unnamed_tail(), Settings())
    queens_gambit = epd_after("d4", "d5", "c4")
    assert rep.is_leaf(queens_gambit)
    assert rep.graph.positions[queens_gambit].name is None
    assert rep.is_learner_position(epd_after("d4", "d5"), "white")


def test_unnamed_positions_below_the_last_name_are_kept_until_the_popularity_floor_ends_them() -> (
    None
):
    # Popularity floor 0.02 % of 10,000 = 2: 2.Nf3 and 2...d6 clear it, 3.a3 (1 game) does not.
    counts = {"e4": 6000, "e4 c5": 3000, "e4 c5 Nf3": 1500, "e4 c5 Nf3 d6": 900}
    counts |= {"e4 c5 Nf3 d6 a3": 1}
    rep = Repertoire(graph_of(counts, {"e4 c5": "Sicilian Defense"}), Settings())
    deepest = epd_after("e4", "c5", "Nf3", "d6")
    assert deepest in rep.positions
    assert epd_after("e4", "c5", "Nf3", "d6", "a3") not in rep.positions
    assert rep.is_leaf(deepest)
    assert rep.is_learner_position(epd_after("e4", "c5", "Nf3"), "black")


def test_a_main_move_onto_an_unstored_position_is_a_stub() -> None:
    counts = {"e4": 6000, "e4 c5": 3000, "Nf3": 400}
    graph = graph_of(counts, {"e4 c5": "Sicilian Defense"}, unstored=frozenset({"Nf3"}))
    rep = Repertoire(graph, Settings())
    assert sans(rep.accepted(START)) == ["e4", "Nf3"]
    assert sans(rep.drawable(START)) == ["e4"]


def test_the_learner_and_opponent_sets_follow_their_widths_and_share_the_share_moves() -> None:
    # Share 10 % of 10,000 = 1,000: e4 and d4 are share moves, c4 is main by rank alone.
    rep = wide_start(width_player=1, width_opponent=3, share=0.1)
    assert sans(rep.accepted(START)) == ["e4", "d4"]
    assert sans(rep.drawable(START)) == ["e4", "d4", "c4"]
    rep = wide_start(width_player=2, width_opponent=1, share=0.35)
    assert sans(rep.accepted(START)) == ["e4", "d4"]
    assert sans(rep.drawable(START)) == ["e4"]


def test_with_equal_widths_both_sets_are_the_main_moves_less_stubs_for_the_opponent() -> None:
    rep = wide_start()
    assert rep.accepted(START) == rep.main_moves(START) == rep.drawable(START)


def opted(*families: str) -> Repertoire:
    """Two orders into one named position (1.d4 Nf6 2.c4 e6, 1.c4 e6 2.d4 Nf6), and the Sicilian."""
    counts = {
        "e4": 5000,
        "e4 c5": 2500,
        "e4 c5 Nf3": 1500,
        "d4": 3000,
        "d4 Nf6": 1500,
        "d4 Nf6 c4": 800,
        "d4 Nf6 c4 e6": 500,
        "c4": 1500,
        "c4 e6": 400,
        "c4 e6 d4": 300,
        "c4 e6 d4 Nf6": 300,
    }
    names = {
        "e4 c5": "Sicilian Defense",
        "e4 c5 Nf3": "Sicilian Defense: Open",
        "d4 Nf6": "Indian Defense",
        "c4 e6": "English Opening: Agincourt Defense",
        "d4 Nf6 c4 e6": "Indian Defense: Normal Variation",
    }
    return Repertoire(graph_of(counts, names), Settings(opted_out=frozenset(families)))


def test_opting_a_family_out_removes_its_exactly_named_positions_and_what_only_they_reach() -> None:
    rep = opted("Sicilian Defense")
    assert epd_after("e4", "c5") not in rep.positions
    assert epd_after("e4", "c5", "Nf3") not in rep.positions
    assert epd_after("e4") in rep.positions  # unnamed, still reached: now a leaf
    assert rep.is_leaf(epd_after("e4"))
    assert not rep.is_stub(next(e for e in rep.main_moves(START) if e.san == "e4"))


def test_opting_back_in_restores_what_the_opt_out_removed() -> None:
    out = opted("Sicilian Defense")
    back_in = Repertoire(out.graph, replace(out.settings, opted_out=frozenset()))
    assert epd_after("e4", "c5", "Nf3") not in out.positions
    assert epd_after("e4", "c5", "Nf3") in back_in.positions
    assert back_in.positions == opted().positions


def test_a_position_named_in_a_kept_family_survives_by_the_orders_still_leading_to_it() -> None:
    rep = opted("Indian Defense")
    shared = epd_after("d4", "Nf6", "c4", "e6")
    assert shared not in rep.positions
    assert epd_after("d4", "Nf6") not in rep.positions
    assert epd_after("d4") in rep.positions  # unnamed, reached from the start
    assert epd_after("c4", "e6") in rep.positions  # English, kept: named itself
    assert epd_after("c4", "e6", "d4") in rep.positions  # unnamed, reached by the English


def test_opt_out_and_reachability_repeat_until_stable() -> None:
    # Opting the English out removes 1.c4 e6 and 2.d4 after it, which only it reached; 1.c4
    # stays, now a leaf, and the shared Indian position stays reachable by 1.d4 Nf6 2.c4 e6.
    rep = opted("English Opening")
    assert epd_after("c4", "e6") not in rep.positions
    assert epd_after("c4", "e6", "d4") not in rep.positions
    assert rep.is_leaf(epd_after("c4"))
    assert epd_after("d4", "Nf6", "c4", "e6") in rep.positions
    rep = opted("English Opening", "Indian Defense", "Sicilian Defense")
    assert rep.positions == {START, epd_after("e4"), epd_after("d4"), epd_after("c4")}


def test_only_positions_the_start_reaches_over_main_moves_are_kept() -> None:
    # 1.b3 is below the floor: the named position after it is stored but unreachable.
    counts = {"e4": 6000, "e4 c5": 3000, "b3": 1, "b3 e5": 1}
    graph = graph_of(counts, {"e4 c5": "Sicilian Defense", "b3 e5": "Nimzo-Larsen Attack"})
    rep = Repertoire(graph, Settings())
    assert rep.positions == {START, epd_after("e4"), epd_after("e4", "c5")}


def test_leaves_have_no_kept_main_move_and_a_learner_to_move_leaf_is_no_learner_position() -> None:
    counts = {"e4": 6000, "e4 c5": 3000, "e4 c5 Nf3": 1500, "e4 c5 a3": 20, "e4 e5": 2000}
    names = {"e4 c5 Nf3": "Sicilian Defense: Open", "e4 e5": "King's Pawn Game"}
    rep = Repertoire(graph_of(counts, names), Settings())
    open_sicilian, e5 = epd_after("e4", "c5", "Nf3"), epd_after("e4", "e5")
    assert rep.is_leaf(open_sicilian) and rep.is_leaf(e5)
    assert not rep.is_leaf(epd_after("e4", "c5"))
    assert rep.is_learner_position(START, "white")
    assert not rep.is_learner_position(START, "black")
    assert rep.is_learner_position(epd_after("e4"), "black")
    assert not rep.is_learner_position(e5, "white")  # White to move, but a leaf
    assert not rep.is_learner_position(open_sicilian, "black")


def test_a_position_with_only_stub_main_moves_is_a_leaf() -> None:
    # Only an edge the build dropped makes a stub now (a cycle, the ply cap): 2.Nf3 is not stored.
    counts = {"e4": 6000, "e4 c5": 3000, "e4 c5 Nf3": 1500}
    graph = graph_of(counts, {"e4 c5": "Sicilian Defense"}, unstored=frozenset({"e4 c5 Nf3"}))
    rep = Repertoire(graph, Settings())
    sicilian = epd_after("e4", "c5")
    assert rep.is_leaf(sicilian)
    assert sans(rep.accepted(sicilian)) == ["Nf3"]
    assert rep.drawable(sicilian) == ()


def test_the_defaults() -> None:
    settings = Settings()
    assert (settings.width_player, settings.width_opponent) == (2, 3)
    assert (settings.popularity_floor, settings.share) == (0.0002, 0.05)
    assert settings.band == "1500+"
    assert settings.opted_out == frozenset()


def test_the_fixture_graph_at_the_defaults() -> None:
    rep = Repertoire(load_graph(FIXTURE_SNAPSHOT), Settings())
    assert sans(rep.accepted(START)) == ["e4", "d4"]
    assert sans(rep.drawable(START)) == ["e4", "d4"]
    assert rep.is_leaf(epd_after("e4", "c5", "Nc3"))
    assert rep.is_leaf(epd_after("e4", "e5", "Nf3", "Nc6", "Bb5"))
