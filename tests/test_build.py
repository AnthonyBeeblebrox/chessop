"""`build-snapshot` on a tiny PGN fixture, written game by game and compressed like the dump."""

import io
import json
import random
import subprocess
import sys
from pathlib import Path

import pytest
import zstandard
from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.build import BANDS, Book, build_snapshot, load_book
from chessop.cli import explanations_for, main
from chessop.graph import load_graph
from chessop.repertoire import START
from graphs import epd_after

BOOK_TSV = """eco\tname\tpgn
A40\tQueen's Pawn Game\t1. d4
A45\tIndian Defense\t1. d4 Nf6
E00\tIndian Defense: Normal Variation\t1. d4 Nf6 2. c4 e6
B00\tKing's Pawn Game\t1. e4
B20\tSicilian Defense\t1. e4 c5
"""


def game(
    moves: str,
    white: str | None = "1600",
    black: str | None = "1650",
    event: str = "Rated Blitz game",
    **headers: str,
) -> str:
    tags = {"Event": event, **headers}
    if white is not None:
        tags["WhiteElo"] = white
    if black is not None:
        tags["BlackElo"] = black
    head = "".join(f'[{k} "{v}"]\n' for k, v in tags.items())
    return f"{head}\n{moves} 1-0\n\n"


def dump(*games: str) -> io.BytesIO:
    return io.BytesIO(zstandard.ZstdCompressor().compress("".join(games).encode()))


@pytest.fixture
def book(tmp_path: Path) -> Book:
    (tmp_path / "a.tsv").write_text(BOOK_TSV)
    return load_book(tmp_path)


def build(book: Book, *games: str, **options):
    return build_snapshot(dump(*games), month="2026-08", book=book, **options)


def band(snapshot, name: str = "1500-1800") -> dict:
    return snapshot.meta["band_diagnostics"][name]


def test_filters_keep_rated_non_bullet_human_games_whose_players_share_a_band(
    book: Book,
) -> None:
    snapshot = build(
        book,
        game("1. e4 e5"),
        game("1. e4 e5", white=None),
        game("1. e4 e5", black="?"),
        game("1. e4 e5", WhiteTitle="BOT"),
        game("1. e4 e5", BlackTitle="BOT"),
        game("1. e4 e5", event="Rated Bullet game"),
        game("1. e4 e5", event="Rated UltraBullet game"),
        game("1. e4 e5", white="1190", black="1210"),
        game("1. e4 e5", event="Rated Correspondence game"),
        game("1. e4 e5", event="Rated Classical tournament https://lichess.org/tournament/x"),
    )
    assert snapshot.meta["dropped"] == {
        "rating missing": 2,
        "BOT title": 2,
        "bullet or ultrabullet": 2,
        "players share no band": 1,
    }
    assert band(snapshot)["games"] == 3
    assert snapshot.graphs["1500-1800"].games == 3
    assert snapshot.meta["games_read"] == 10


def test_eight_bands_closed_then_open() -> None:
    assert [name for name, _, _ in BANDS] == [
        "0-1200",
        "1200-1500",
        "1500-1800",
        "1800-2100",
        "2100+",
        "1200+",
        "1500+",
        "1800+",
    ]


def kept(snapshot) -> dict[str, int]:
    """The games kept per band, bands keeping none left out."""
    games = {name: band(snapshot, name)["games"] for name, _, _ in BANDS}
    return {name: n for name, n in games.items() if n}


@pytest.mark.parametrize(
    ("white", "black", "bands"),
    [
        ("1199", "800", ["0-1200"]),
        ("1200", "1499", ["1200-1500", "1200+"]),
        ("1500", "1799", ["1500-1800", "1200+", "1500+"]),
        ("1800", "2099", ["1800-2100", "1200+", "1500+", "1800+"]),
        ("2100", "3000", ["2100+", "1200+", "1500+", "1800+"]),
        ("1499", "1500", ["1200+"]),
        ("1650", "1950", ["1200+", "1500+"]),
        ("1799", "2100", ["1200+", "1500+"]),
        ("1850", "2400", ["1200+", "1500+", "1800+"]),
    ],
)
def test_a_game_feeds_every_band_both_players_fall_in(
    book: Book, white: str, black: str, bands: list[str]
) -> None:
    snapshot = build(book, game("1. e4", white=white, black=black))
    assert kept(snapshot) == dict.fromkeys(bands, 1)
    for name in bands:
        assert epd_after("e4") in snapshot.graphs[name].positions


def test_a_game_whose_players_share_no_band_is_dropped(book: Book) -> None:
    snapshot = build(book, game("1. e4", white="1199", black="1200"), game("1. d4"))
    assert snapshot.meta["dropped"] == {"players share no band": 1}
    assert kept(snapshot) == {"1500-1800": 1, "1200+": 1, "1500+": 1}


def test_a_full_band_drops_its_further_games(book: Book) -> None:
    snapshot = build(book, game("1. e4"), game("1. d4"), game("1. c4"), cap=2)
    assert band(snapshot)["games"] == 2
    assert band(snapshot)["dropped_band_full"] == 1
    assert epd_after("c4") not in snapshot.graphs["1500-1800"].positions


def test_a_game_still_feeds_the_bands_that_are_not_full(book: Book) -> None:
    snapshot = build(book, game("1. e4", "1600", "1650"), game("1. d4", "1900", "1950"), cap=1)
    assert kept(snapshot) == {"1500-1800": 1, "1800-2100": 1, "1200+": 1, "1500+": 1, "1800+": 1}
    assert epd_after("d4") in snapshot.graphs["1800+"].positions
    assert epd_after("d4") not in snapshot.graphs["1500+"].positions
    assert band(snapshot, "1500+")["dropped_band_full"] == 1
    assert band(snapshot, "1200+")["dropped_band_full"] == 1
    assert band(snapshot, "1800+")["dropped_band_full"] == 0


def test_reading_stops_when_every_band_is_full(book: Book) -> None:
    elos = ["1000", "1300", "1600", "1900", "2200"]
    games = [game("1. e4", white=elo, black=elo) for elo in elos]
    snapshot = build(book, *games, game("1. d4"), cap=1)
    assert snapshot.meta["games_read"] == 5
    assert snapshot.meta["stopped"] == "every band full"
    assert snapshot.meta["compressed_bytes_read"] > 0


def test_reading_stops_at_the_end_of_the_month_or_at_max_games(book: Book) -> None:
    games = [game("1. e4")] * 4
    assert build(book, *games).meta["stopped"] == "end of the month"
    capped = build(book, *games, max_games=3)
    assert capped.meta["games_read"] == 3
    assert capped.meta["stopped"] == "max games read"
    assert band(capped)["games"] == 3


def test_counts_are_pooled_over_every_move_order(book: Book) -> None:
    snapshot = build(
        book,
        game("1. d4 Nf6 2. c4 e6"),
        game("1. d4 Nf6 2. c4 e6"),
        game("1. c4 e6 2. d4 Nf6"),
    )
    graph = snapshot.graphs["1500-1800"]
    target = graph.positions[epd_after("d4", "Nf6", "c4", "e6")]
    assert target.count == 3
    assert target.canonical == ("d2d4", "g8f6", "c2c4", "e7e6")
    into = [
        (e.san, e.count)
        for p in graph.positions.values()
        for e in p.edges
        if e.child_epd == target.epd
    ]
    assert sorted(into) == [("Nf6", 1), ("e6", 2)]
    assert graph.positions[START].count == 3


def test_an_edge_pools_its_count_over_move_orders_into_its_position(book: Book) -> None:
    snapshot = build(
        book,
        game("1. d4 Nf6 2. c4 e6 3. Nc3"),
        game("1. c4 e6 2. d4 Nf6 3. Nc3"),
    )
    graph = snapshot.graphs["1500-1800"]
    [nc3] = graph.positions[epd_after("d4", "Nf6", "c4", "e6")].edges
    assert (nc3.san, nc3.uci, nc3.count) == ("Nc3", "b1c3", 2)
    assert nc3.child_epd == epd_after("d4", "Nf6", "c4", "e6", "Nc3")


def test_the_canonical_order_ties_go_to_the_order_seen_first(book: Book) -> None:
    snapshot = build(book, game("1. c4 e6 2. d4 Nf6"), game("1. d4 Nf6 2. c4 e6"))
    target = snapshot.graphs["1500-1800"].positions[epd_after("d4", "Nf6", "c4", "e6")]
    assert target.canonical == ("c2c4", "e7e6", "d2d4", "g8f6")


def test_exactly_named_positions_carry_the_book_name_and_line(book: Book) -> None:
    snapshot = build(book, game("1. c4 e6 2. d4 Nf6 3. Nc3"), game("1. e4 e5"))
    graph = snapshot.graphs["1500-1800"]
    named = graph.positions[epd_after("d4", "Nf6", "c4", "e6")]
    assert (named.name, named.eco) == ("Indian Defense: Normal Variation", "E00")
    assert named.book_line == ("d2d4", "g8f6", "c2c4", "e7e6")
    assert named.canonical == ("c2c4", "e7e6", "d2d4", "g8f6")
    after = graph.positions[epd_after("d4", "Nf6", "c4", "e6", "Nc3")]
    assert (after.name, after.eco, after.book_line) == (None, None, None)
    assert graph.positions[epd_after("e4")].name == "King's Pawn Game"


def test_positions_and_edges_below_the_storage_cut_off_are_not_stored(book: Book) -> None:
    # 5 games, cut-off 0.3: count >= 1.5, unrounded, so one game is not enough.
    snapshot = build(
        book,
        game("1. e4 e5"),
        game("1. e4 e5"),
        game("1. e4 c5"),
        game("1. d4 d5"),
        game("1. d4 d5"),
        cutoff=0.3,
    )
    graph = snapshot.graphs["1500-1800"]
    assert set(graph.positions) == {
        START,
        epd_after("e4"),
        epd_after("e4", "e5"),
        epd_after("d4"),
        epd_after("d4", "d5"),
    }
    assert [e.san for e in graph.positions[epd_after("e4")].edges] == ["e5"]
    assert band(snapshot)["positions"] == 5
    assert band(snapshot)["edges"] == 4


def test_the_walk_stops_at_the_ply_cap(book: Book) -> None:
    snapshot = build(book, game("1. e4 e5 2. Nf3 Nc6"), ply_cap=3)
    graph = snapshot.graphs["1500-1800"]
    assert epd_after("e4", "e5", "Nf3") in graph.positions
    assert epd_after("e4", "e5", "Nf3", "Nc6") not in graph.positions
    assert snapshot.meta["ply_cap"] == 3


def test_a_rejected_san_drops_the_rest_of_the_game_and_is_counted(book: Book) -> None:
    snapshot = build(book, game("1. e4 e5 2. Ke3 Nc6"), game("1. e4 e5 2. Nf3"))
    graph = snapshot.graphs["1500-1800"]
    assert graph.positions[epd_after("e4", "e5")].count == 2
    assert [e.san for e in graph.positions[epd_after("e4", "e5")].edges] == ["Nf3"]
    assert band(snapshot)["dropped_rejected_san"] == 1
    assert band(snapshot)["games"] == 2


def test_an_edge_closing_a_cycle_is_dropped_and_counted(book: Book) -> None:
    # A knight shuffle returns to the start: the edge back closes a cycle, the shorter path wins.
    snapshot = build(book, game("1. Nf3 Nf6 2. Ng1 Ng8 3. e4"), game("1. e4"))
    graph = snapshot.graphs["1500-1800"]
    back = epd_after("Nf3", "Nf6", "Ng1")
    assert graph.positions[START].count == 3
    assert graph.positions[back].edges == ()
    assert [e.san for e in graph.positions[START].edges] == ["e4", "Nf3"]
    assert graph.positions[epd_after("e4")].count == 2
    assert band(snapshot)["dropped_cycle_edges"] == 1


def test_diffuse_traffic_counts_what_no_single_move_order_clears(book: Book) -> None:
    # 4 games, cut-off 0.5: count >= 2. The Indian position is reached by two orders of 1 each.
    snapshot = build(
        book,
        game("1. d4 Nf6 2. c4 e6 3. Nc3"),
        game("1. c4 e6 2. d4 Nf6 3. Nc3"),
        game("1. e4 c5"),
        game("1. e4 c5"),
        cutoff=0.5,
    )
    diagnostics = band(snapshot)
    # Diffuse: the Indian position and the one after Nc3, and the Nc3 edge.
    assert diagnostics["diffuse_positions"] == 2
    assert diagnostics["diffuse_edges"] == 1


def test_diagnostics_report_the_repertoire_at_the_default_load_rule(book: Book) -> None:
    snapshot = build(
        book,
        game("1. d4 Nf6 2. c4 e6"),
        game("1. d4 Nf6 2. c4 e6"),
        game("1. e4 c5 2. Nf3"),
        game("1. e4 c5 2. Nc3"),
        game("1. e4 e5"),
    )
    # No named-position prune: the unnamed 2.Nf3, 2.Nc3 and 1...e5 are leaves of their own.
    assert band(snapshot)["repertoire"] == {
        "positions": 10,
        "edges": 9,
        "branches": 4,
        "leaves": 4,
        "max_depth": 4,
        "book_lines_covered": 5,
    }


def test_metadata_and_the_version_string(book: Book) -> None:
    snapshot = build(book, game("1. e4"), cap=7)
    meta = snapshot.meta
    bands = "0-1200,1200-1500,1500-1800,1800-2100,2100+,1200+,1500+,1800+"
    assert meta["version"] == f"2026-08/{bands}/{book.commit}/{meta['build_revision']}"
    assert meta["month"] == "2026-08"
    assert meta["bands"] == [name for name, _, _ in BANDS]
    assert meta["book_commit"] == book.commit
    assert meta["storage_cutoff"] == 0.0002
    assert meta["ply_cap"] == 36
    assert meta["games_per_band"] == 7
    assert snapshot.graphs["1500-1800"].version == meta["version"]


def test_the_book_commit_is_the_commit_file_when_there_is_one(tmp_path: Path) -> None:
    (tmp_path / "a.tsv").write_text(BOOK_TSV)
    hashed = load_book(tmp_path).commit
    (tmp_path / "COMMIT").write_text("abc1234\n")
    assert load_book(tmp_path).commit == "abc1234"
    assert hashed != "abc1234" and "/" not in hashed


def test_the_repo_copy_of_the_book_loads_every_line() -> None:
    book = load_book(Path(__file__).parents[1] / "refs" / "lichess")
    assert len(book.lines) == 3810


def test_build_snapshot_writes_a_graph_file_the_server_drills(tmp_path: Path) -> None:
    (tmp_path / "book").mkdir()
    (tmp_path / "book" / "a.tsv").write_text(BOOK_TSV)
    source = tmp_path / "month.pgn.zst"
    source.write_bytes(
        dump(
            *[game("1. d4 Nf6 2. c4 e6")] * 3,
            *[game("1. e4 c5 2. Nf3")] * 3,
            game("1. d4 d5"),
        ).getvalue()
    )
    out = tmp_path / "snapshot.graph.json.gz"
    wikitext = tmp_path / "pages.json"
    wikitext.write_text(
        json.dumps({"Chess Opening Theory/1. e4/1...c5": {"wikitext": "== x ==\nThe Sicilian."}})
    )
    main(
        [
            "build-snapshot",
            "--month",
            "2026-08",
            "--dump",
            str(source),
            "--book",
            str(tmp_path / "book"),
            "--out",
            str(out),
            "--wikitext",
            str(wikitext),
        ]
    )
    graph = load_graph(out, "1500-1800")
    assert graph.games == 7
    assert graph.version.startswith("2026-08/")
    explanations = explanations_for(out, graph.version)
    assert explanations is not None
    page = explanations.page_at(epd_after("e4", "c5"))
    assert page is not None and page.lead == "The Sicilian."
    with (
        TestClient(create_app(graph, rng=random.Random(1), explanations=explanations)) as client,
        client.websocket_connect("/ws") as ws,
    ):
        assert ws.receive_json()["type"] == "round"


def test_the_server_never_imports_the_build_module_or_zstandard() -> None:
    code = (
        "import sys, chessop, chessop.cli, chessop.app;"
        "print('chessop.build' in sys.modules, 'zstandard' in sys.modules)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.split() == ["False", "False"]
